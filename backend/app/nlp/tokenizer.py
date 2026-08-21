"""Advanced Text Preprocessor using spaCy."""
import re
import string
from typing import List, Set, Optional
import spacy


class TextPreprocessor:
    """Advanced text preprocessing with spaCy NLP pipeline."""

    def __init__(self, spacy_model: str = "en_core_web_sm"):
        self._model_name = spacy_model
        self._nlp = None

    @property
    def nlp(self):
        if self._nlp is None:
            try:
                self._nlp = spacy.load(self._model_name)
            except OSError:
                from spacy.cli import download
                download(self._model_name)
                self._nlp = spacy.load(self._model_name)
        return self._nlp

    def preprocess(self, text: str) -> str:
        """Full preprocessing pipeline."""
        text = self.lowercase(text)
        text = self.remove_urls(text)
        text = self.remove_emails(text)
        text = self.normalize_whitespace(text)
        return text

    def lowercase(self, text: str) -> str:
        return text.lower().strip()

    def remove_urls(self, text: str) -> str:
        return re.sub(r'https?://\S+|www\.\S+', '', text)

    def remove_emails(self, text: str) -> str:
        return re.sub(r'\S+@\S+', '', text)

    def remove_punctuation(self, text: str) -> str:
        return text.translate(str.maketrans('', '', string.punctuation))

    def normalize_whitespace(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

    def tokenize(self, text: str) -> List[str]:
        """Tokenize using spaCy (smarter than split)."""
        doc = self.nlp(self.preprocess(text))
        return [token.text for token in doc if not token.is_space]

    def tokenize_meaningful(self, text: str) -> List[str]:
        """Tokenize keeping only meaningful tokens (no stopwords, punctuation, spaces)."""
        doc = self.nlp(self.preprocess(text))
        return [
            token.lemma_ for token in doc
            if not token.is_stop and not token.is_punct and not token.is_space and len(token.text) > 1
        ]

    def lemmatize(self, text: str) -> str:
        """Lemmatize all tokens."""
        doc = self.nlp(self.preprocess(text))
        return ' '.join(token.lemma_ for token in doc if not token.is_space)

    def get_nouns_and_verbs(self, text: str) -> List[str]:
        """Extract nouns and verbs (key concepts)."""
        doc = self.nlp(self.preprocess(text))
        return [
            token.lemma_ for token in doc
            if token.pos_ in ('NOUN', 'VERB', 'PROPN')
            and not token.is_stop and len(token.text) > 2
        ]

    def get_entities(self, text: str) -> List[dict]:
        """Extract named entities."""
        doc = self.nlp(text)
        return [
            {"text": ent.text, "label": ent.label_, "start": ent.start_char, "end": ent.end_char}
            for ent in doc.ents
        ]

    def get_noun_chunks(self, text: str) -> List[str]:
        """Extract noun chunks (phrases)."""
        doc = self.nlp(self.preprocess(text))
        return [chunk.text for chunk in doc.noun_chunks]

    def get_sentences(self, text: str) -> List[str]:
        """Split into sentences using spaCy."""
        doc = self.nlp(text)
        return [sent.text.strip() for sent in doc.sents]

    def word_count(self, text: str) -> int:
        return len(self.tokenize(text))

    def sentence_count(self, text: str) -> int:
        return len(self.get_sentences(text))


# Singleton
text_preprocessor = TextPreprocessor()
