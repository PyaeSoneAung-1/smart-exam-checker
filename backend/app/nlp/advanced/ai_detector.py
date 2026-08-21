"""AI-Generated Text Detection using perplexity, burstiness, and multi-signal analysis.
Improved version with higher sensitivity for detecting ChatGPT/AI-generated content."""
import re
import math
import statistics
from collections import Counter
from typing import Dict, List


class AIDetector:
    def __init__(self, threshold: float = 0.45):
        self.threshold = threshold

    # ── AI phrase patterns (expanded) ───────────────────────────────
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
        # Additional ChatGPT patterns
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

        words = text.lower().split()
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

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

        # Weighted combination — rebalanced for higher sensitivity
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

        # Apply 1.5x boost, cap at 1.0
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

    # ── Signal calculations ─────────────────────────────────────────

    def _calc_perplexity(self, words: list) -> float:
        if len(words) < 3:
            return 100.0
        bigrams = [(words[i], words[i + 1]) for i in range(len(words) - 1)]
        bigram_counts = Counter(bigrams)
        total = len(bigrams)
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

    def _calc_vocab_richness(self, words: list) -> float:
        if not words:
            return 0.0
        return len(set(words)) / len(words)

    def _calc_ai_phrase_score(self, text_lower: str) -> tuple:
        """Return (score 0-1, list of found phrases)."""
        found = []
        for phrase in self.AI_PHRASES:
            if phrase in text_lower:
                found.append(phrase)
        # Each phrase adds 0.06, cap at 1.0 — more phrases = higher score
        score = min(1.0, len(found) * 0.06)
        # If 3+ phrases found, give a bonus
        if len(found) >= 3:
            score = min(1.0, score + 0.15)
        if len(found) >= 5:
            score = min(1.0, score + 0.10)
        return score, found

    def _calc_starter_score(self, sentences: list) -> float:
        """Proportion of sentences starting with AI-style starters."""
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

    def _calc_formal_ratio(self, sentences: list) -> float:
        """Ratio of sentences containing formal connectors."""
        if not sentences:
            return 0.0
        formal_count = 0
        for s in sentences:
            s_lower = s.lower()
            for conn in self.FORMAL_CONNECTORS:
                if conn in s_lower:
                    formal_count += 1
                    break
        return formal_count / len(sentences)

    def _calc_sentence_uniformity(self, sentences: list) -> float:
        """Low coefficient of variation = AI-like uniformity. Returns 0-1 score."""
        if len(sentences) < 2:
            return 0.0
        lengths = [len(s.split()) for s in sentences]
        mean = statistics.mean(lengths)
        if mean == 0:
            return 0.0
        stdev = statistics.stdev(lengths) if len(lengths) > 1 else 0
        cv = stdev / mean
        # CV of 0 → perfectly uniform → score 1.0; CV ≥ 1.0 → score 0.0
        return max(0.0, min(1.0, 1.0 - cv))

    def _calc_repetition_score(self, words: list) -> float:
        """Bigram repetition ratio — higher = more repetitive = more AI-like."""
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
        """AI text often has well-structured paragraphs with topic sentences."""
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        if len(paragraphs) < 2:
            return 0.0
        # Check if paragraphs are similar in length (AI-like)
        lengths = [len(p.split()) for p in paragraphs]
        if not lengths:
            return 0.0
        mean = statistics.mean(lengths)
        if mean == 0:
            return 0.0
        stdev = statistics.stdev(lengths) if len(lengths) > 1 else 0
        cv = stdev / mean if mean > 0 else 0
        # Uniform paragraph lengths = AI-like
        return max(0.0, min(1.0, 1.0 - cv))

    def _calc_list_patterns(self, text: str) -> float:
        """AI often uses numbered/bullet lists."""
        lines = text.split('\n')
        list_lines = sum(1 for l in lines if re.match(r'^\s*[\d]+[\.\)]\s|^\s*[-*•]\s', l.strip()))
        if len(lines) < 3:
            return 0.0
        return min(1.0, list_lines / len(lines) * 2)

    def _calc_hedging_language(self, text_lower: str) -> float:
        """AI often uses hedging language."""
        hedges = [
            "it's important to note", "it is important to note",
            "keep in mind", "it's worth noting", "it is worth noting",
            "it should be noted", "please note", "bear in mind",
            "it's crucial to understand", "it is crucial to understand",
        ]
        count = sum(1 for h in hedges if h in text_lower)
        return min(1.0, count * 0.25)

    def _normalize_perplexity(self, perplexity: float) -> float:
        """Map perplexity to 0-1 signal (low perplexity → high score)."""
        # Typical range: 10-500. Lower = more predictable = more AI-like.
        if perplexity <= 10:
            return 1.0
        if perplexity >= 200:
            return 0.0
        return 1.0 - (perplexity - 10) / 190
