"""Advanced Semantic Similarity using multiple methods."""
from typing import List, Dict, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from app.nlp.tokenizer import TextPreprocessor


class SemanticSimilarity:
    """Multi-method semantic similarity calculator."""

    def __init__(self):
        self.preprocessor = TextPreprocessor()
        self._tfidf = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))

    def tfidf_cosine_similarity(self, text1: str, text2: str) -> float:
        """TF-IDF based cosine similarity."""
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

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        return len(intersection) / len(union) if union else 0.0

    def spacy_similarity(self, text1: str, text2: str) -> float:
        """spaCy word vector similarity."""
        try:
            doc1 = self.preprocessor.nlp(text1)
            doc2 = self.preprocessor.nlp(text2)
            if doc1.has_vector and doc2.has_vector:
                return float(max(0.0, min(1.0, doc1.similarity(doc2))))
            return 0.0
        except Exception:
            return 0.0

    def ngram_overlap(self, text1: str, text2: str, n: int = 2) -> float:
        """N-gram overlap ratio."""
        tokens1 = self.preprocessor.tokenize_meaningful(text1)
        tokens2 = self.preprocessor.tokenize_meaningful(text2)

        if len(tokens1) < n or len(tokens2) < n:
            return 0.0

        ngrams1 = set(tuple(tokens1[i:i+n]) for i in range(len(tokens1)-n+1))
        ngrams2 = set(tuple(tokens2[i:i+n]) for i in range(len(tokens2)-n+1))

        if not ngrams1 or not ngrams2:
            return 0.0

        intersection = ngrams1 & ngrams2
        union = ngrams1 | ngrams2
        return len(intersection) / len(union) if union else 0.0

    def entity_overlap(self, text1: str, text2: str) -> float:
        """Named entity overlap between two texts."""
        ents1 = set(e["text"].lower() for e in self.preprocessor.get_entities(text1))
        ents2 = set(e["text"].lower() for e in self.preprocessor.get_entities(text2))

        if not ents1 and not ents2:
            return 1.0  # Both have no entities, neutral
        if not ents1 or not ents2:
            return 0.0

        intersection = ents1 & ents2
        union = ents1 | ents2
        return len(intersection) / len(union) if union else 0.0

    def concept_coverage(self, text1: str, text2: str) -> float:
        """How much of text1's concepts are covered in text2."""
        nouns1 = set(self.preprocessor.get_nouns_and_verbs(text1))
        nouns2 = set(self.preprocessor.get_nouns_and_verbs(text2))

        if not nouns1:
            return 0.0

        covered = nouns1 & nouns2
        return len(covered) / len(nouns1)

    def calculate_similarity(self, text1: str, text2: str) -> Dict[str, float]:
        """Calculate similarity using all methods."""
        results = {
            "tfidf_cosine": self.tfidf_cosine_similarity(text1, text2),
            "word_overlap": self.word_overlap_similarity(text1, text2),
            "spacy_vectors": self.spacy_similarity(text1, text2),
            "bigram_overlap": self.ngram_overlap(text1, text2, n=2),
            "entity_overlap": self.entity_overlap(text1, text2),
            "concept_coverage": self.concept_coverage(text1, text2),
        }

        # Weighted average
        weights = {
            "tfidf_cosine": 0.30,
            "word_overlap": 0.20,
            "spacy_vectors": 0.25,
            "bigram_overlap": 0.10,
            "entity_overlap": 0.05,
            "concept_coverage": 0.10,
        }

        weighted_sum = sum(results[k] * weights[k] for k in weights)
        results["weighted_average"] = round(weighted_sum, 4)

        return results


# Singleton
semantic_similarity = SemanticSimilarity()
