"""AI-Generated Text Detection.

Two modes:

1. **Language-model mode (primary)** — when PyTorch + a causal language model
   (default ``distilgpt2``) are installed, detection uses real signals:
     * *Perplexity*: average negative log-likelihood of the text under the
       language model. AI-generated text is statistically predictable, so it
       has low perplexity.
     * *Burstiness*: variation of sentence-level perplexity. AI text is
       unusually uniform; human writing varies sentence to sentence.
   These are the same core signals used by GPTZero-style detectors.

2. **Heuristic fallback** — if the model is not available (torch missing,
   model not downloaded, low memory), detection degrades gracefully to the
   original phrase-list / style heuristic so the API never breaks.

The response shape is identical in both modes so the frontend is unchanged.
"""
import logging
import os
import re
import statistics
import threading
from typing import Dict, List, Optional, Tuple

from app.config import settings

logger = logging.getLogger(__name__)

# ── Lazy language-model singleton ─────────────────────────────────────
_lm_lock = threading.Lock()
_lm = None          # (tokenizer, model) once loaded
_lm_failed = False  # set True after a failed attempt so we don't retry hot


def _get_lm() -> Optional[Tuple]:
    """Lazily load the causal language model. Returns (tokenizer, model) or None."""
    global _lm, _lm_failed
    if _lm is not None or _lm_failed:
        return _lm
    if not settings.AI_LM_ENABLED:
        logger.info("AI_LM_ENABLED=false — using heuristic AI detection.")
        _lm_failed = True
        return None
    with _lm_lock:
        if _lm is not None or _lm_failed:
            return _lm
        try:
            if "HF_HOME" in os.environ:
                os.environ.setdefault("TRANSFORMERS_CACHE",
                                      os.path.join(os.environ["HF_HOME"], "hub"))
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            model_name = settings.AI_MODEL
            logger.info(f"Loading AI-detection language model: {model_name}")
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float32,
                low_cpu_mem_usage=True,
            )
            model.eval()
            _lm = (tokenizer, model)
            logger.info("AI-detection language model ready.")
        except Exception as e:  # noqa: BLE001 — any failure → fallback mode
            logger.warning(f"AI language model unavailable, using heuristics: {e}")
            _lm_failed = True
            _lm = None
    return _lm


def _ppl_of_text(tokenizer, model, text: str) -> Optional[float]:
    """Return model perplexity of a text, or None if too short for a stable estimate."""
    import torch
    ids = tokenizer(text, return_tensors="pt", truncation=True,
                    max_length=settings.AI_MAX_TOKENS)["input_ids"]
    if ids.shape[1] < 3:
        return None
    with torch.no_grad():
        loss = model(ids, labels=ids).loss
    return float(torch.exp(loss).item())


# ── Public detector ───────────────────────────────────────────────────

class AIDetector:
    def __init__(self, threshold: float = 0.45):
        self.threshold = threshold

    # ── Public API ──────────────────────────────────────────────────

    def detect(self, text: str) -> Dict:
        if not text or len(text.strip()) < 20:
            return {
                "ai_probability": 0.0,
                "perplexity": 0.0,
                "burstiness": 0.0,
                "vocabulary_richness": 0.0,
                "flagged": False,
                "ai_phrases_found": [],
                "formal_ratio": 0.0,
                "sentence_uniformity": 0.0,
            }

        lm = _get_lm()
        if lm is not None:
            try:
                return self._detect_with_lm(lm, text)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"LM AI detection failed, using heuristics: {e}")
        return self._detect_heuristic(text)

    # ── Language-model mode ─────────────────────────────────────────

    def _detect_with_lm(self, lm, text: str) -> Dict:
        tokenizer, model = lm
        words = text.lower().split()
        sentences = self._split_sentences(text)

        whole_ppl = _ppl_of_text(tokenizer, model, text)
        sentence_ppls = []
        for s in sentences:
            p = _ppl_of_text(tokenizer, model, s)
            if p is not None:
                sentence_ppls.append(p)

        # Burstiness = coefficient of variation of sentence-level perplexity.
        # (Fall back to sentence-length variation if per-sentence PPL fails.)
        burstiness = 0.5
        if len(sentence_ppls) >= 2 and statistics.mean(sentence_ppls) > 0:
            burstiness = min(1.0, statistics.stdev(sentence_ppls) / statistics.mean(sentence_ppls))
        elif len(sentences) >= 2:
            lengths = [len(s.split()) for s in sentences]
            mean = statistics.mean(lengths)
            burstiness = min(1.0, statistics.stdev(lengths) / mean) if mean > 0 else 0.5

        vocab_richness = self._calc_vocab_richness(words)
        phrase_score, ai_phrases_found = self._calc_ai_phrase_score(text.lower())

        if whole_ppl is None:
            # Text too short for a stable LM estimate — lean on heuristics
            prob = min(1.0, phrase_score * 0.6 + (1.0 - burstiness) * 0.3)
            perplexity = 0.0
        else:
            ppl_signal = self._normalize_ppl(whole_ppl)
            # Low burstiness (uniform sentences) = AI-like → high signal.
            burst_signal = self._normalize_burstiness(burstiness)
            # Primary: perplexity + burstiness (GPTZero-style).
            # Small phrase bonus catches obvious ChatGPT phrasing even at mid-PPL.
            prob = (ppl_signal * 0.65
                    + burst_signal * 0.30
                    + phrase_score * 0.05)
            perplexity = round(whole_ppl, 2)

        ai_probability = min(1.0, max(0.0, prob))
        return {
            "ai_probability": round(ai_probability, 4),
            "perplexity": perplexity,
            "burstiness": round(burstiness, 4),
            "vocabulary_richness": round(vocab_richness, 4),
            "flagged": ai_probability >= self.threshold,
            "ai_phrases_found": ai_phrases_found,
            "formal_ratio": round(self._calc_formal_ratio(sentences), 4),
            "sentence_uniformity": round(self._calc_sentence_uniformity(sentences), 4),
        }

    @staticmethod
    def _normalize_ppl(ppl: float) -> float:
        """Map perplexity to a 0-1 AI signal (lower PPL → higher signal).

        Calibrated on distilgpt2 (Aug 2026): AI-written text typically scores
        ~18-45 PPL, student prose ~40-90+, so the strong-AI band ends at 25
        and the signal decays to zero by 60. Classic/very regular prose (e.g.
        Dickens) scores low PPL too — a known limitation of all PPL detectors.
        """
        if ppl <= 25:
            return 1.0
        if ppl >= 60:
            return 0.0
        return 1.0 - (ppl - 25) / 35

    @staticmethod
    def _normalize_burstiness(cv: float) -> float:
        """Map burstiness CV to 0-1 (low CV = uniform = AI-like → high signal)."""
        if cv <= 0.3:
            return 1.0
        if cv >= 1.0:
            return 0.0
        return 1.0 - (cv - 0.3) / 0.7

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        parts = re.split(r'[.!?]+', text)
        return [s.strip() for s in parts if s.strip()]

    # ── Heuristic fallback mode (original implementation) ───────────

    def _detect_heuristic(self, text: str) -> Dict:
        words = text.lower().split()
        sentences = self._split_sentences(text)

        perplexity = self._calc_perplexity(words)
        burstiness = self._calc_burstiness(sentences)
        vocab_richness = self._calc_vocab_richness(words)
        ai_phrase_score, ai_phrases_found = self._calc_ai_phrase_score(text.lower())
        starter_score = self._calc_starter_score(sentences)
        formal_ratio = self._calc_formal_ratio(sentences)
        sentence_uniformity = self._calc_sentence_uniformity(sentences)
        repetition_score = self._calc_repetition_score(words)
        paragraph_score = self._calc_paragraph_structure(text)
        list_pattern_score = self._calc_list_patterns(text)
        hedging_score = self._calc_hedging_language(text.lower())

        ai_score = (
            self._normalize_perplexity(perplexity) * 0.10
            + (1.0 - burstiness) * 0.08
            + (1.0 - vocab_richness) * 0.08
            + ai_phrase_score * 0.30
            + starter_score * 0.10
            + formal_ratio * 0.08
            + sentence_uniformity * 0.08
            + repetition_score * 0.08
            + paragraph_score * 0.05
            + list_pattern_score * 0.03
            + hedging_score * 0.02
        )
        ai_probability = min(1.0, ai_score * 1.5)

        return {
            "ai_probability": round(ai_probability, 4),
            "perplexity": round(perplexity, 2),
            "burstiness": round(burstiness, 4),
            "vocabulary_richness": round(vocab_richness, 4),
            "flagged": ai_probability >= self.threshold,
            "ai_phrases_found": ai_phrases_found,
            "formal_ratio": round(formal_ratio, 4),
            "sentence_uniformity": round(sentence_uniformity, 4),
        }

    # ── Shared signal helpers ───────────────────────────────────────

    @staticmethod
    def _calc_vocab_richness(words: list) -> float:
        if not words:
            return 0.0
        return len(set(words)) / len(words)

    def _calc_ai_phrase_score(self, text_lower: str) -> tuple:
        found = [p for p in self.AI_PHRASES if p in text_lower]
        score = min(1.0, len(found) * 0.06)
        if len(found) >= 3:
            score = min(1.0, score + 0.15)
        if len(found) >= 5:
            score = min(1.0, score + 0.10)
        return score, found

    def _calc_formal_ratio(self, sentences: list) -> float:
        if not sentences:
            return 0.0
        count = 0
        for s in sentences:
            s_lower = s.lower()
            for conn in self.FORMAL_CONNECTORS:
                if conn in s_lower:
                    count += 1
                    break
        return count / len(sentences)

    def _calc_sentence_uniformity(self, sentences: list) -> float:
        if len(sentences) < 2:
            return 0.0
        lengths = [len(s.split()) for s in sentences]
        mean = statistics.mean(lengths)
        if mean == 0:
            return 0.0
        stdev = statistics.stdev(lengths) if len(lengths) > 1 else 0
        cv = stdev / mean
        return max(0.0, min(1.0, 1.0 - cv))

    # ── Heuristic-only helpers ──────────────────────────────────────

    def _calc_perplexity(self, words: list) -> float:
        if len(words) < 3:
            return 100.0
        from collections import Counter
        bigrams = [(words[i], words[i + 1]) for i in range(len(words) - 1)]
        bigram_counts = Counter(bigrams)
        total = len(bigrams)
        import math
        log_prob = sum(
            math.log2(bigram_counts[bg] / total)
            for bg in bigrams
            if bigram_counts[bg] > 0
        )
        avg_log = log_prob / max(len(bigrams), 1)
        return 2 ** (-avg_log)

    def _calc_burstiness(self, sentences: list) -> float:
        if len(sentences) < 2:
            return 0.5
        lengths = [len(s.split()) for s in sentences]
        mean = statistics.mean(lengths)
        if mean == 0:
            return 0.0
        stdev = statistics.stdev(lengths) if len(lengths) > 1 else 0
        return min(1.0, stdev / mean)

    def _calc_starter_score(self, sentences: list) -> float:
        if not sentences:
            return 0.0
        count = 0
        for s in sentences:
            s_lower = s.strip().lower()
            for starter in self.AI_SENTENCE_STARTERS:
                if s_lower.startswith(starter):
                    count += 1
                    break
        return min(1.0, count / max(len(sentences), 1) * 3)

    def _calc_repetition_score(self, words: list) -> float:
        from collections import Counter
        if len(words) < 4:
            return 0.0
        bigrams = [(words[i], words[i + 1]) for i in range(len(words) - 1)]
        bigram_counts = Counter(bigrams)
        repeated = sum(1 for c in bigram_counts.values() if c > 1)
        total_unique = len(bigram_counts)
        if total_unique == 0:
            return 0.0
        return min(1.0, repeated / total_unique * 2)

    def _calc_paragraph_structure(self, text: str) -> float:
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        if len(paragraphs) < 2:
            return 0.0
        lengths = [len(p.split()) for p in paragraphs]
        mean = statistics.mean(lengths)
        if mean == 0:
            return 0.0
        stdev = statistics.stdev(lengths) if len(lengths) > 1 else 0
        cv = stdev / mean if mean > 0 else 0
        return max(0.0, min(1.0, 1.0 - cv))

    def _calc_list_patterns(self, text: str) -> float:
        lines = text.split('\n')
        list_lines = sum(1 for l in lines if re.match(r'^\s*[\d]+[\.\)]\s|^\s*[-*•]\s', l.strip()))
        if len(lines) < 3:
            return 0.0
        return min(1.0, list_lines / len(lines) * 2)

    def _calc_hedging_language(self, text_lower: str) -> float:
        hedges = [
            "it's important to note", "it is important to note",
            "keep in mind", "it's worth noting", "it is worth noting",
            "it should be noted", "please note", "bear in mind",
            "it's crucial to understand", "it is crucial to understand",
        ]
        count = sum(1 for h in hedges if h in text_lower)
        return min(1.0, count * 0.25)

    def _normalize_perplexity(self, perplexity: float) -> float:
        if perplexity <= 10:
            return 1.0
        if perplexity >= 200:
            return 0.0
        return 1.0 - (perplexity - 10) / 190

    # ── Phrase lists (shared) ───────────────────────────────────────

    AI_PHRASES: List[str] = [
        # Classic ChatGPT phrases
        "delve into", "tapestry", "paradigm", "holistic approach",
        "multifaceted", "comprehensive", "it is important to note",
        "in conclusion", "furthermore", "moreover", "additionally",
        "consequently", "nevertheless", "notwithstanding", "pivotal",
        "intricate", "nuanced", "leveraging", "streamlining", "synergy",
        "ecosystem", "landscape", "framework", "methodology", "robust",
        "scalable", "innovative", "groundbreaking", "cutting-edge",
        "transformative", "revolutionize", "game-changer", "best practices",
        "deep dive", "at the end of the day", "in terms of",
        "with regard to", "it should be noted", "as a matter of fact",
        "in light of", "by virtue of", "in the realm of", "underscores",
        "underscoring", "highlights the importance", "plays a crucial role",
        "shedding light", "on the other hand", "last but not least",
        "it goes without saying", "as we can see", "in summary",
        "it's worth noting", "it is worth noting", "in essence",
        "to summarize", "in the context of", "from a perspective",
        "plays a vital role", "serves as", "serves as a",
        "it's important to understand", "it is important to understand",
        "this highlights", "this underscores", "this demonstrates",
        "in particular", "specifically", "notably", "significantly",
        "it's crucial", "it is crucial", "fundamental",
        "a wide range of", "a variety of", "a plethora of",
        "shed light on", "shedding light on", "take into account",
        "it's essential", "it is essential", "keep in mind",
        "on the contrary", "as previously mentioned", "as noted",
        "in other words", "to put it simply", "to illustrate",
        "for instance", "for example", "such as",
        "one of the most", "the most important", "the primary",
        "overall", "in general", "generally speaking",
        "it can be argued", "it could be argued",
        "this suggests", "this implies", "this indicates",
        "in recent years", "in today's world", "in modern society",
        "has become increasingly", "is becoming increasingly",
        "the fact that", "the reality is", "the truth is",
        "it should be emphasized", "it must be noted",
        "arguably", "essentially", "fundamentally",
        "comprehensive understanding", "comprehensive analysis",
        "effective way", "effective method", "effective approach",
        "important factor", "key factor", "significant impact",
        "plays an important role", "plays a significant role",
        "wide range", "broad range", "vast majority",
    ]

    AI_SENTENCE_STARTERS: List[str] = [
        "additionally,", "furthermore,", "moreover,", "consequently,",
        "nevertheless,", "notably,", "importantly,", "significantly,",
        "however,", "indeed,", "ultimately,", "essentially,",
        "specifically,", "particularly,", "interestingly,",
        "arguably,", "fundamentally,", "overall,",
    ]

    FORMAL_CONNECTORS: List[str] = [
        "furthermore", "moreover", "additionally", "consequently",
        "nevertheless", "notwithstanding", "hence", "therefore",
        "thus", "accordingly", "subsequently", "whereas", "whereby",
        "notably", "significantly", "conversely", "alternatively",
        "in addition", "as a result", "due to", "in order to",
        "in contrast", "on the other hand", "similarly",
        "as mentioned", "as noted", "as previously",
    ]
