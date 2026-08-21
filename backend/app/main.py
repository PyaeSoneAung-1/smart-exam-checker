from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import os

from app.config import settings
from app.database import engine, Base, SessionLocal

# Import all models
from app.models import User, UserRole, Subject, Exam, Question, StudentAnswer, Score

# Import routers
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.subjects import router as subjects_router
from app.api.exams import router as exams_router
from app.api.questions import router as questions_router
from app.api.answers import router as answers_router
from app.api.dashboard import router as dashboard_router
from app.api.export import router as export_router
from app.api.advanced_nlp import router as advanced_nlp_router
from app.api.settings import router as settings_router

# Seed module
from app.seed import seed_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Smart Exam Answer Checker API...")

    # Create tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified.")

    # Seed data
    try:
        seed_data()
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        import traceback
        traceback.print_exc()

    # Try to load optional production modules
    try:
        from app.health import router as health_router
        app.include_router(health_router)
        logger.info("Health checks loaded.")
    except Exception:
        pass

    try:
        from app.websocket import router as ws_router
        app.include_router(ws_router)
        logger.info("WebSocket loaded.")
    except Exception:
        pass

    try:
        from app.file_upload import router as upload_router
        app.include_router(upload_router)
        logger.info("File upload loaded.")
    except Exception:
        pass

    try:
        from app.middleware import SecurityHeadersMiddleware, RequestLoggingMiddleware
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(RequestLoggingMiddleware)
        logger.info("Middleware loaded.")
    except Exception:
        pass

    logger.info("Application startup complete.")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Smart Exam Answer Checker - AI-powered grading using NLP",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
prefix = settings.API_V1_PREFIX
app.include_router(auth_router, prefix=prefix)
app.include_router(users_router, prefix=prefix)
app.include_router(subjects_router, prefix=prefix)
app.include_router(exams_router, prefix=prefix)
app.include_router(questions_router, prefix=prefix)
app.include_router(answers_router, prefix=prefix)
app.include_router(dashboard_router, prefix=prefix)
app.include_router(export_router, prefix=prefix)
app.include_router(advanced_nlp_router, prefix=prefix + "/nlp", tags=["Advanced NLP"])
app.include_router(settings_router, prefix=prefix)


@app.get("/")
def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Mount static files for uploads
uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
