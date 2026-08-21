"""Health check endpoints for monitoring."""
import time
import logging
import psutil
from fastapi import APIRouter
from sqlalchemy import text
from app.database import SessionLocal
from app.cache import is_redis_available, _get_redis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/db")
def health_db():
    """Check database connectivity."""
    start = time.time()
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "healthy", "service": "database", "latency_ms": round((time.time() - start) * 1000, 2)}
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        return {"status": "unhealthy", "service": "database", "error": str(e)}


@router.get("/cache")
def health_cache():
    """Check Redis connectivity."""
    start = time.time()
    try:
        client = _get_redis()
        if client is None:
            return {"status": "unavailable", "service": "redis", "message": "Redis not configured or unreachable"}
        client.ping()
        return {"status": "healthy", "service": "redis", "latency_ms": round((time.time() - start) * 1000, 2)}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {"status": "unhealthy", "service": "redis", "error": str(e)}


@router.get("/nlp")
def health_nlp():
    """Check if NLP models are loaded and functional."""
    try:
        from app.nlp.tokenizer import TextPreprocessor
        from app.nlp.keyword_extractor import KeywordExtractor
        from app.nlp.similarity import SemanticSimilarity
        from app.nlp.grammar_checker import GrammarChecker

        preprocessor = TextPreprocessor()
        # Quick smoke test
        tokens = preprocessor.tokenize_meaningful("The quick brown fox jumps over the lazy dog")
        nlp_loaded = len(tokens) > 0

        ke = KeywordExtractor()
        kws = ke.extract_tfidf_keywords("Python is a programming language used for data science")
        tfidf_loaded = len(kws) > 0

        return {
            "status": "healthy" if (nlp_loaded and tfidf_loaded) else "degraded",
            "service": "nlp",
            "spacy_loaded": nlp_loaded,
            "tfidf_loaded": tfidf_loaded,
        }
    except Exception as e:
        logger.error(f"NLP health check failed: {e}")
        return {"status": "unhealthy", "service": "nlp", "error": str(e)}


@router.get("/system")
def health_system():
    """Check system resources (disk, memory)."""
    try:
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
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        return {"status": "unhealthy", "service": "system", "error": str(e)}
