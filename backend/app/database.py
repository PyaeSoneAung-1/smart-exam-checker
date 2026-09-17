import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs = {"pool_pre_ping": True}
if not _is_sqlite:
    _engine_kwargs.update(pool_size=10, max_overflow=20)

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

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


# Columns added after the first release. `create_all` creates missing tables
# but never alters existing ones, so these are applied idempotently at startup
# for databases created by an older version. New deployments get them from the
# models (and from `alembic upgrade head`).
_ADDED_COLUMNS = {
    "exams": [
        ("available_from", "ALTER TABLE exams ADD COLUMN available_from {ts}"),
        ("available_until", "ALTER TABLE exams ADD COLUMN available_until {ts}"),
    ],
    "users": [
        ("token_version", "ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0"),
        (
            "failed_login_attempts",
            "ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER NOT NULL DEFAULT 0",
        ),
        ("locked_until", "ALTER TABLE users ADD COLUMN locked_until {ts}"),
    ],
}

# Uniqueness enforced with an index so it can be added to existing tables.
_ADDED_INDEXES = [
    (
        "student_answers",
        "uq_answer_question_student",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_answer_question_student "
        "ON student_answers (question_id, student_id)",
    ),
]


def ensure_schema_upgrades() -> None:
    """Apply lightweight, idempotent schema upgrades to an existing database."""
    timestamp_type = "TIMESTAMP" if engine.dialect.name == "postgresql" else "DATETIME"
    inspector = inspect(engine)

    for table, columns in _ADDED_COLUMNS.items():
        if not inspector.has_table(table):
            continue
        existing = {c["name"] for c in inspector.get_columns(table)}
        for column_name, ddl in columns:
            if column_name in existing:
                continue
            try:
                with engine.begin() as conn:
                    conn.execute(text(ddl.format(ts=timestamp_type)))
                logger.info("Schema upgrade: added %s.%s", table, column_name)
            except Exception:  # pragma: no cover - dialect differences
                logger.exception("Could not add %s.%s", table, column_name)

    for table, index_name, ddl in _ADDED_INDEXES:
        if not inspector.has_table(table):
            continue
        try:
            with engine.begin() as conn:
                conn.execute(text(ddl))
        except Exception:
            # Pre-existing duplicate rows block the index; report and continue
            # rather than refusing to start.
            logger.warning(
                "Could not create unique index %s (existing duplicate rows?). "
                "Remove duplicates and restart to enforce it.",
                index_name,
            )
