"""Keyword extraction and matching against a model answer.

Two strategies are combined: TF-IDF term scores and spaCy POS/NER analysis.
Only meaningful single words and clean two-word noun phrases are kept, so junk
fragments (e.g. "acts barrier") no longer end up as graded keywords.
"""
from typing import Dict, List, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer

from app.nlp.tokenizer import TextPreprocessor

# Terms that carry no meaning as a keyword
_STOPWORD_FRAGMENTS = {
    "the", "and", "for", "that", "this", "with", "from", "are", "was", "were",
    "its", "their", "there", "then", "than", "has", "have", "had", "been",
    "being", "will", "would", "can", "could", "should", "not", "but", "you",
    "your", "they", "them", "which", "when", "where", "what", "who", "how",
    "also", "such", "into", "other", "each", "some", "more", "most", "very",
}

# Verbs that make a two-word phrase a fragment rather than a concept
_VERB_POS = {"VERB", "AUX"}


class KeywordExtractor:
    """Multi-strategy keyword extraction."""

    def __init__(self):
        self.preprocessor = TextPreprocessor()
        self._vectorizer = TfidfVectorizer(
            max_features=200,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
        )

    def extract_tfidf_keywords(self, text: str, top_n: int = 15) -> List[Tuple[str, float]]:
        """Top TF-IDF terms (their score reflects within-text importance)."""
        try:
            tfidf_matrix = self._vectorizer.fit_transform([text])
            feature_names = self._vectorizer.get_feature_names_out()
            scores = tfidf_matrix.toarray()[0]
            keyword_scores = sorted(
                zip(feature_names, scores, strict=False), key=lambda item: item[1], reverse=True
            )
            return [(kw, float(score)) for kw, score in keyword_scores[:top_n] if score > 0]
        except Exception:
            return []

    def extract_spacy_keywords(self, text: str) -> List[str]:
        """Keywords from NER entities, single nouns and clean noun phrases."""
        doc = self.preprocessor.nlp(text)
        keywords = set()

        for ent in doc.ents:
            keywords.add(ent.text.lower().strip())

        for token in doc:
            if token.pos_ in ("NOUN", "PROPN") and not token.is_stop and len(token.text) > 2:
                keywords.add(token.lemma_.lower())

        for chunk in doc.noun_chunks:
            tokens = [t for t in chunk if not t.is_punct and not t.is_space]
            # Keep only 2-word phrases made of content words (no verbs/stop words)
            if len(tokens) != 2:
                continue
            if any(t.pos_ in _VERB_POS or t.is_stop for t in tokens):
                continue
            phrase = " ".join(t.lemma_.lower() for t in tokens).strip()
            if all(len(word) > 2 for word in phrase.split()):
                keywords.add(phrase)

        return list(keywords)

    def extract_key_concepts(self, text: str) -> List[Dict]:
        """Key concepts with importance scores and the method that found them."""
        concepts: List[Dict] = []

        for keyword, score in self.extract_tfidf_keywords(text):
            concepts.append({"term": keyword, "score": score, "method": "tfidf"})

        for keyword in self.extract_spacy_keywords(text):
            if not any(concept["term"] == keyword for concept in concepts):
                concepts.append({"term": keyword, "score": 0.5, "method": "spacy"})

        concepts.sort(key=lambda item: item["score"], reverse=True)
        return concepts

    def extract_from_model_answer(self, model_answer: str) -> List[str]:
        """Important keywords of a teacher's model answer (max 20)."""
        tfidf_keywords = [kw for kw, _ in self.extract_tfidf_keywords(model_answer, top_n=10)]
        spacy_keywords = self.extract_spacy_keywords(model_answer)
        nouns_verbs = self.preprocessor.get_nouns_and_verbs(model_answer)

        merged = list(dict.fromkeys(tfidf_keywords + spacy_keywords + nouns_verbs))

        filtered = []
        for keyword in merged:
            keyword = keyword.strip().lower()
            if len(keyword) <= 2:
                continue
            words = keyword.split()
            if any(word in _STOPWORD_FRAGMENTS or len(word) <= 2 for word in words):
                continue
            filtered.append(keyword)

        return filtered[:20]

    def check_keywords_in_answer(
        self, model_keywords: List[str], student_answer: str
    ) -> Dict:
        """Which model keywords appear in the student answer.

        A multi-word keyword counts as found only when *all* of its words are
        present (exact, lemma or token match) — a single shared word is not
        evidence that the student covered the concept.
        """
        student_lower = student_answer.lower()
        student_tokens = {token.lower() for token in self.preprocessor.tokenize(student_answer)}
        student_lemmas = set(self.preprocessor.tokenize_meaningful(student_answer))
        student_lemmas_text = self.preprocessor.lemmatize(student_answer).lower()

        found, missing = [], []
        for keyword in model_keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in student_lower or keyword_lower in student_lemmas_text:
                found.append(keyword)
                continue

            keyword_tokens = set(keyword_lower.split())
            if keyword_tokens and keyword_tokens.issubset(student_tokens | student_lemmas):
                found.append(keyword)
                continue

            missing.append(keyword)

        total = len(model_keywords)
        return {
            "found": found,
            "missing": missing,
            "found_count": len(found),
            "total_count": total,
            "match_ratio": len(found) / total if total else 0.0,
        }


# Backwards-compatible module-level instance
keyword_extractor = KeywordExtractor()
