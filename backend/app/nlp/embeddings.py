"""Shared sentence-embedding model.

`all-MiniLM-L6-v2` (configurable via SENTENCE_TRANSFORMER_MODEL) is loaded once
per process on first use and reused by both the answer-similarity scorer and the
plagiarism detector. Every function degrades gracefully to `None` when the
optional dependencies are not installed, so callers can fall back to lexical or
spaCy-based measures.
"""
import logging
import threading
from typing import List, Optional

from app.config import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_model = None
_load_failed = False


def get_embedder():
    """Return the shared SentenceTransformer, or None when unavailable."""
    global _model, _load_failed

    if _model is not None:
        return _model
    if _load_failed:
        return None

    with _lock:
        if _model is not None:
            return _model
        if _load_failed:
            return None
        try:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(settings.SENTENCE_TRANSFORMER_MODEL)
            logger.info("Sentence-embedding model loaded: %s", settings.SENTENCE_TRANSFORMER_MODEL)
        except Exception as exc:  # optional dependency / model download failure
            _load_failed = True
            logger.info(
                "Sentence embeddings unavailable (%s: %s) — falling back to lexical similarity.",
                type(exc).__name__,
                exc,
            )
            return None
    return _model


def encode(texts: List[str]) -> Optional[List[List[float]]]:
    """Encode a batch of texts into normalized embeddings, or None."""
    model = get_embedder()
    if model is None:
        return None
    try:
        vectors = model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False
        )
        return vectors
    except Exception:
        logger.exception("Embedding computation failed")
        return None


def pair_similarity(text1: str, text2: str) -> Optional[float]:
    """Cosine similarity between two texts, or None when unavailable."""
    import numpy as np

    vectors = encode([text1, text2])
    if vectors is None:
        return None
    try:
        return float(max(0.0, min(1.0, np.dot(vectors[0], vectors[1]))))
    except Exception:
        logger.exception("Embedding similarity failed")
        return None
