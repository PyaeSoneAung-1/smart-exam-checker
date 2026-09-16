"""Health check endpoints for monitoring."""
import logging
import time

import psutil
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/db")
def health_db(db: Session = Depends(get_db)):
    """Check database connectivity."""
    start = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "service": "database",
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
        }
    except Exception:
        # Details go to the server log only — never to an anonymous caller.
        logger.exception("Database health check failed")
        return {"status": "unhealthy", "service": "database"}


@router.get("/nlp")
def health_nlp():
    """Check that the NLP pipeline can load and produce tokens/keywords."""
    try:
        from app.nlp.keyword_extractor import KeywordExtractor
        from app.nlp.tokenizer import TextPreprocessor

        tokens = TextPreprocessor().tokenize_meaningful("The quick brown fox jumps over the lazy dog")
        keywords = KeywordExtractor().extract_tfidf_keywords(
            "Python is a programming language used for data science"
        )
        return {
            "status": "healthy" if (tokens and keywords) else "degraded",
            "service": "nlp",
            "spacy_loaded": bool(tokens),
            "tfidf_loaded": bool(keywords),
        }
    except Exception:
        logger.exception("NLP health check failed")
        return {"status": "unhealthy", "service": "nlp"}


@router.get("/system")
def health_system(current_user: User = Depends(get_current_admin)):
    """System resource usage — admin only (information disclosure risk)."""
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "status": "healthy",
        "service": "system",
        "memory": {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "percent_used": mem.percent,
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent_used": round(disk.percent, 1),
        },
        "cpu_percent": psutil.cpu_percent(interval=0.1),
    }
