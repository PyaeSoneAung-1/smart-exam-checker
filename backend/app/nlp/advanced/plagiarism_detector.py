"""Plagiarism detection across the answers to one question.

Two independent signals are reported per student pair:

* **Lexical** — TF-IDF cosine over word 1–2 grams. This is the *decision*
  signal: only lexical evidence flags a pair, because two answers about the
  same question inevitably share vocabulary and meaning.
* **Semantic** — `all-MiniLM-L6-v2` embedding cosine. Short exam answers to the
  same question routinely reach 0.92+ even when they are written completely
  independently, so a high semantic score is reported as a **review signal**
  (`semantic_review`) for paraphrased copies, not as a flag.

Every pair reports `similarity` (lexical), `tfidf_similarity`,
`semantic_similarity`, `method` and `flagged`.
"""
import logging
import threading
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import settings

logger = logging.getLogger(__name__)

_embedder = None
_embedder_failed = False
_embedder_lock = threading.Lock()


def _get_embedder():
    """Lazily load the shared sentence-embedding model (None when disabled)."""
    global _embedder, _embedder_failed

    if not settings.PLAGIARISM_EMBEDDINGS_ENABLED:
        return None
    if _embedder is not None:
        return _embedder
    if _embedder_failed:
        return None

    with _embedder_lock:
        if _embedder is not None:
            return _embedder
        try:
            from sentence_transformers import SentenceTransformer

            _embedder = SentenceTransformer(settings.SENTENCE_TRANSFORMER_MODEL)
            logger.info("Plagiarism embedding model loaded: %s", settings.SENTENCE_TRANSFORMER_MODEL)
        except Exception as exc:
            _embedder_failed = True
            logger.info(
                "Plagiarism embeddings unavailable (%s) — lexical detection only.",
                type(exc).__name__,
            )
            return None
    return _embedder


class PlagiarismDetector:
    """Compare a set of answers and report lexical + semantic similarity."""

    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold
        self.semantic_review_gate = settings.PLAGIARISM_SEMANTIC_REVIEW_GATE
        self.semantic_corroboration_gate = settings.PLAGIARISM_SEMANTIC_CORROBORATION_GATE

    # ── public API ──────────────────────────────────────────

    def detect(self, answers: List[str]) -> Dict:
        """Return pair-wise similarity for every pair in `answers`."""
        if not answers or len(answers) < 2:
            return self._empty_result()

        valid_answers = [a if a and a.strip() else "empty" for a in answers]

        tfidf_matrix = self._tfidf_matrix(valid_answers)
        tfidf_pairs = (
            cosine_similarity(tfidf_matrix) if tfidf_matrix is not None else None
        )

        semantic_pairs = self._semantic_matrix(valid_answers)

        pairs: List[Dict] = []
        for i in range(len(valid_answers)):
            for j in range(i + 1, len(valid_answers)):
                tfidf_sim = float(tfidf_pairs[i][j]) if tfidf_pairs is not None else 0.0
                semantic_sim = (
                    float(semantic_pairs[i][j]) if semantic_pairs is not None else None
                )
                similarity, method, flagged, semantic_review = self._decide(
                    tfidf_sim, semantic_sim
                )
                pairs.append(
                    {
                        "answer_idx_1": i,
                        "answer_idx_2": j,
                        "similarity": round(tfidf_sim, 4),
                        "tfidf_similarity": round(tfidf_sim, 4),
                        "semantic_similarity": (
                            round(semantic_sim, 4) if semantic_sim is not None else None
                        ),
                        "method": method,
                        "flagged": flagged,
                        "semantic_review": semantic_review,
                    }
                )

        flagged_pairs = [p for p in pairs if p["flagged"]]
        review_pairs = [p for p in pairs if p["semantic_review"] and not p["flagged"]]

        return {
            "pairs": pairs,
            "summary": {
                "total_pairs": len(pairs),
                "flagged_pairs": len(flagged_pairs),
                "review_pairs": len(review_pairs),
                "max_similarity": round(max((p["similarity"] for p in pairs), default=0.0), 4),
                "max_semantic_similarity": round(
                    max((p["semantic_similarity"] or 0.0 for p in pairs), default=0.0), 4
                ),
                "threshold": self.threshold,
                "semantic_enabled": semantic_pairs is not None,
                "flagged_indices": [p["answer_idx_1"] for p in flagged_pairs],
            },
        }

    # ── decision logic ──────────────────────────────────────

    def _decide(
        self, tfidf_sim: float, semantic_sim: Optional[float]
    ) -> Tuple[float, str, bool, bool]:
        """Return (similarity, method, flagged, semantic_review).

        Lexical similarity is the only flagging signal. A high semantic score
        marks the pair for manual review, and corroborated pairs (high on both)
        are labelled explicitly.
        """
        if semantic_sim is None:
            return tfidf_sim, "lexical", tfidf_sim >= self.threshold, False

        flagged = tfidf_sim >= self.threshold
        if flagged and semantic_sim >= self.semantic_corroboration_gate:
            return tfidf_sim, "lexical+semantic", True, False
        if flagged:
            return tfidf_sim, "lexical", True, False
        if semantic_sim >= self.semantic_review_gate:
            # Possible paraphrase — flagged for review only, never auto-flagged.
            return tfidf_sim, "semantic-review", False, True
        return tfidf_sim, "lexical", False, False

    # ── helpers ─────────────────────────────────────────────

    @staticmethod
    def _tfidf_matrix(texts: List[str]):
        try:
            return TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                sublinear_tf=True,
            ).fit_transform(texts)
        except Exception:
            logger.exception("TF-IDF matrix computation failed")
            return None

    def _semantic_matrix(self, texts: List[str]):
        embedder = _get_embedder()
        if embedder is None:
            return None
        try:
            vectors = embedder.encode(
                texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False
            )
            return np.clip(cosine_similarity(vectors), 0.0, 1.0)
        except Exception:
            logger.exception("Semantic similarity computation failed")
            return None

    def _empty_result(self) -> Dict:
        return {
            "pairs": [],
            "summary": {
                "total_pairs": 0,
                "flagged_pairs": 0,
                "review_pairs": 0,
                "max_similarity": 0.0,
                "max_semantic_similarity": 0.0,
                "threshold": self.threshold,
                "semantic_enabled": _get_embedder() is not None,
                "flagged_indices": [],
            },
        }
