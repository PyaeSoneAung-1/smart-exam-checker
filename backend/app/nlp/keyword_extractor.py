"""Advanced Keyword Extraction using TF-IDF, RAKE, and spaCy NER."""
from typing import List, Dict, Set, Tuple
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

from app.nlp.tokenizer import TextPreprocessor


class KeywordExtractor:
    """Multi-strategy keyword extraction."""

    def __init__(self):
        self.preprocessor = TextPreprocessor()
        self._vectorizer = TfidfVectorizer(
            max_features=200,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1,
        )

    def extract_tfidf_keywords(self, text: str, top_n: int = 15) -> List[Tuple[str, float]]:
        """Extract keywords using TF-IDF scoring."""
        try:
            tfidf_matrix = self._vectorizer.fit_transform([text])
            feature_names = self._vectorizer.get_feature_names_out()
            scores = tfidf_matrix.toarray()[0]
            keyword_scores = list(zip(feature_names, scores))
            keyword_scores.sort(key=lambda x: x[1], reverse=True)
            return [(kw, float(score)) for kw, score in keyword_scores[:top_n] if score > 0]
        except Exception:
            return []

    def extract_spacy_keywords(self, text: str) -> List[str]:
        """Extract keywords using spaCy POS tagging and NER."""
        doc = self.preprocessor.nlp(text)
        keywords = set()

        # Named entities
        for ent in doc.ents:
            keywords.add(ent.text.lower())

        # Nouns and proper nouns
        for token in doc:
            if token.pos_ in ('NOUN', 'PROPN') and not token.is_stop and len(token.text) > 2:
                keywords.add(token.lemma_.lower())

        # Noun chunks (multi-word)
        for chunk in doc.noun_chunks:
            clean = chunk.text.lower().strip()
            if len(clean.split()) >= 2:
                keywords.add(clean)

        return list(keywords)

    def extract_key_concepts(self, text: str) -> List[Dict[str, any]]:
        """Extract key concepts with importance scores."""
        concepts = []

        # TF-IDF keywords
        tfidf_kws = self.extract_tfidf_keywords(text)
        for kw, score in tfidf_kws:
            concepts.append({"term": kw, "score": score, "method": "tfidf"})

        # spaCy keywords
        spacy_kws = self.extract_spacy_keywords(text)
        for kw in spacy_kws:
            if not any(c["term"] == kw for c in concepts):
                concepts.append({"term": kw, "score": 0.5, "method": "spacy"})

        # Sort by score
        concepts.sort(key=lambda x: x["score"], reverse=True)
        return concepts

    def extract_from_model_answer(self, model_answer: str) -> List[str]:
        """Extract important keywords from teacher's model answer."""
        # Combine multiple extraction methods
        tfidf_kws = [kw for kw, _ in self.extract_tfidf_keywords(model_answer, top_n=10)]
        spacy_kws = self.extract_spacy_keywords(model_answer)
        nouns_verbs = self.preprocessor.get_nouns_and_verbs(model_answer)
        noun_chunks = self.preprocessor.get_noun_chunks(model_answer)

        # Merge and deduplicate
        all_keywords = list(dict.fromkeys(tfidf_kws + spacy_kws + nouns_verbs + noun_chunks))

        # Filter: keep meaningful terms only
        filtered = []
        for kw in all_keywords:
            kw = kw.strip().lower()
            if len(kw) > 2 and kw not in ('the', 'and', 'for', 'that', 'this', 'with', 'from', 'are', 'was', 'were'):
                filtered.append(kw)

        return filtered[:20]

    def check_keywords_in_answer(
        self, model_keywords: List[str], student_answer: str
    ) -> Dict[str, any]:
        """Check which model keywords appear in student answer."""
        student_lower = student_answer.lower()
        student_tokens = set(self.preprocessor.tokenize_meaningful(student_answer))
        student_lemmas = self.preprocessor.lemmatize(student_answer).lower()

        found = []
        missing = []

        for kw in model_keywords:
            kw_lower = kw.lower()
            # Exact match
            if kw_lower in student_lower:
                found.append(kw)
                continue
            # Lemma match
            if kw_lower in student_lemmas:
                found.append(kw)
                continue
            # Token overlap (for multi-word keywords)
            kw_tokens = set(kw_lower.split())
            if kw_tokens.issubset(student_tokens):
                found.append(kw)
                continue
            # Partial match (any word of keyword in student)
            if any(t in student_tokens for t in kw_tokens):
                found.append(kw)
                continue
            missing.append(kw)

        return {
            "found": found,
            "missing": missing,
            "found_count": len(found),
            "total_count": len(model_keywords),
            "match_ratio": len(found) / max(len(model_keywords), 1),
        }


# Singleton
keyword_extractor = KeywordExtractor()
