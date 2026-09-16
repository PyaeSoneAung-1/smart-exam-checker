"""Multi-method semantic similarity between a model answer and a student answer.

Six signals are combined with fixed weights. The semantic signal uses sentence
embeddings (`app.nlp.embeddings`); when those are unavailable it falls back to
spaCy's tensor-based `Doc.similarity`, which is only a rough proxy.
"""
import warnings
from typing import Dict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.nlp import embeddings
from app.nlp.tokenizer import TextPreprocessor


class SemanticSimilarity:
    """Multi-method similarity calculator (weights sum to 1.0)."""

    WEIGHTS = {
        "tfidf_cosine": 0.30,
        "word_overlap": 0.20,
        "embedding_similarity": 0.25,
        "bigram_overlap": 0.10,
        "entity_overlap": 0.05,
        "concept_coverage": 0.10,
    }

    def __init__(self):
        self.preprocessor = TextPreprocessor()
        self._tfidf = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))

    def tfidf_cosine_similarity(self, text1: str, text2: str) -> float:
        """TF-IDF cosine similarity."""
        try:
            matrix = self._tfidf.fit_transform([text1, text2])
            sim = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
            return float(max(0.0, min(1.0, sim)))
        except Exception:
            return 0.0

    def word_overlap_similarity(self, text1: str, text2: str) -> float:
        """Jaccard similarity on meaningful words."""
        tokens1 = set(self.preprocessor.tokenize_meaningful(text1))
        tokens2 = set(self.preprocessor.tokenize_meaningful(text2))

        if not tokens1 or not tokens2:
            return 0.0

        union = tokens1 | tokens2
        return len(tokens1 & tokens2) / len(union) if union else 0.0

    def embedding_similarity(self, text1: str, text2: str) -> float:
        """Sentence-embedding cosine similarity (spaCy fallback, else 0.0)."""
        similarity = embeddings.pair_similarity(text1, text2)
        if similarity is not None:
            return similarity
        return self._spacy_similarity(text1, text2)

    def _spacy_similarity(self, text1: str, text2: str) -> float:
        """Fallback: spaCy `Doc.similarity` (tagger/parser tensors)."""
        try:
            doc1 = self.preprocessor.nlp(text1)
            doc2 = self.preprocessor.nlp(text2)
            if not doc1.has_vector or not doc2.has_vector:
                return 0.0
            with warnings.catch_warnings():
                # spaCy warns that small models have no real word vectors; the
                # caller already knows this is a fallback.
                warnings.simplefilter("ignore", UserWarning)
                return float(max(0.0, min(1.0, doc1.similarity(doc2))))
        except Exception:
            return 0.0

    def ngram_overlap(self, text1: str, text2: str, n: int = 2) -> float:
        """Jaccard similarity over word n-grams."""
        tokens1 = self.preprocessor.tokenize_meaningful(text1)
        tokens2 = self.preprocessor.tokenize_meaningful(text2)

        if len(tokens1) < n or len(tokens2) < n:
            return 0.0

        ngrams1 = {tuple(tokens1[i:i + n]) for i in range(len(tokens1) - n + 1)}
        ngrams2 = {tuple(tokens2[i:i + n]) for i in range(len(tokens2) - n + 1)}

        union = ngrams1 | ngrams2
        return len(ngrams1 & ngrams2) / len(union) if union else 0.0

    def entity_overlap(self, text1: str, text2: str) -> float:
        """Named-entity overlap; uninformative when neither text has entities."""
        ents1 = {e["text"].lower() for e in self.preprocessor.get_entities(text1)}
        ents2 = {e["text"].lower() for e in self.preprocessor.get_entities(text2)}

        if not ents1 and not ents2:
            # Neutral value (not 1.0): two texts without entities must not be
            # rewarded for "agreeing".
            return 0.5
        if not ents1 or not ents2:
            return 0.0

        union = ents1 | ents2
        return len(ents1 & ents2) / len(union) if union else 0.0

    def concept_coverage(self, text1: str, text2: str) -> float:
        """How much of text1's content words appear in text2."""
        nouns1 = set(self.preprocessor.get_nouns_and_verbs(text1))
        nouns2 = set(self.preprocessor.get_nouns_and_verbs(text2))

        if not nouns1:
            return 0.0

        return len(nouns1 & nouns2) / len(nouns1)

    def calculate_similarity(self, text1: str, text2: str) -> Dict[str, float]:
        """Compute every signal plus their weighted average."""
        results = {
            "tfidf_cosine": self.tfidf_cosine_similarity(text1, text2),
            "word_overlap": self.word_overlap_similarity(text1, text2),
            "embedding_similarity": self.embedding_similarity(text1, text2),
            "bigram_overlap": self.ngram_overlap(text1, text2, n=2),
            "entity_overlap": self.entity_overlap(text1, text2),
            "concept_coverage": self.concept_coverage(text1, text2),
        }

        weighted_sum = sum(results[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
        results["weighted_average"] = round(float(np.clip(weighted_sum, 0.0, 1.0)), 4)
        return results


# Backwards-compatible module-level instance
semantic_similarity = SemanticSimilarity()
