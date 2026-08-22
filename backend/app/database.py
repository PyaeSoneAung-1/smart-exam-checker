from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema_upgrades() -> None:
    """Idempotently add new nullable columns to existing tables.

    `Base.metadata.create_all` only creates missing tables; it never alters
    existing ones. For databases created before a model change, add the new
    columns here so the app keeps working without manual migrations.
    """
    from sqlalchemy import inspect, text

    timestamp_type = "TIMESTAMP" if engine.dialect.name == "postgresql" else "DATETIME"
    inspector = inspect(engine)
    upgrades = {
        "exams": [
            ("available_from", f"ALTER TABLE exams ADD COLUMN available_from {timestamp_type}"),
            ("available_until", f"ALTER TABLE exams ADD COLUMN available_until {timestamp_type}"),
        ],
    }
    for table, columns in upgrades.items():
        if not inspector.has_table(table):
            continue
        existing = {c["name"] for c in inspector.get_columns(table)}
        with engine.begin() as conn:
            for col_name, ddl in columns:
                if col_name not in existing:
                    conn.execute(text(ddl))
