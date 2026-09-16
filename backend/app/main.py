"""FastAPI application entry point.

Routers and middleware are registered at import time so the OpenAPI schema and
security middleware always match what is actually served. The lifespan hook only
prepares the database (tables, light schema upgrades, optional demo seed).
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.advanced_nlp import router as advanced_nlp_router
from app.api.answers import router as answers_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.exams import router as exams_router
from app.api.export import router as export_router
from app.api.questions import router as questions_router
from app.api.settings import router as settings_router
from app.api.subjects import router as subjects_router
from app.api.users import router as users_router
from app.config import settings
from app.database import Base, engine, ensure_schema_upgrades
from app.file_upload import router as upload_router
from app.files import router as files_router
from app.health import router as health_router
from app.limiter import limiter
from app.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware

# Import all models so create_all()/autogenerate see every table
from app.models import Exam, Question, Score, StudentAnswer, Subject, User, UserRole  # noqa: F401
from app.seed import seed_data
from app.websocket import router as ws_router

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s %s", settings.PROJECT_NAME, settings.PROJECT_VERSION)
    logger.info("Environment: %s", settings.ENVIRONMENT)

    Base.metadata.create_all(bind=engine)
    ensure_schema_upgrades()

    if settings.SEED_DEMO_DATA:
        try:
            seed_data()
        except Exception:  # pragma: no cover - startup must not crash on seed issues
            logger.exception("Demo data seeding failed")
    else:
        logger.info("Demo data seeding disabled (SEED_DEMO_DATA=false).")

    logger.info("Startup complete.")
    yield
    logger.info("Shutting down.")


_docs_enabled = bool(settings.ENABLE_DOCS)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Smart Exam Answer Checker — AI-powered grading using NLP",
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

# ── Middleware ──────────────────────────────────────────────
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
if limiter is not None:
    app.state.limiter = limiter
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# ── Routers ─────────────────────────────────────────────────
prefix = settings.API_V1_PREFIX
for router in (
    auth_router,
    users_router,
    subjects_router,
    exams_router,
    questions_router,
    answers_router,
    dashboard_router,
    export_router,
    settings_router,
    files_router,
):
    app.include_router(router, prefix=prefix)

app.include_router(advanced_nlp_router, prefix=prefix + "/nlp", tags=["Advanced NLP"])
app.include_router(health_router)
app.include_router(upload_router)
if settings.WS_ENABLED:
    app.include_router(ws_router)


@app.get("/")
def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "docs": "/docs" if _docs_enabled else None,
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Uploads are private by default (served by /api/files). Only mount the static
# directory when the deployment explicitly opts in.
if settings.UPLOADS_PUBLIC:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
