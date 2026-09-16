"""spaCy-backed text preprocessing.

The spaCy pipeline is expensive to load, so it is cached per model name and
shared by every TextPreprocessor instance (the scorer used to build three
separate pipelines).
"""
import logging
import re
from typing import Dict, List

import spacy

from app.config import settings

logger = logging.getLogger(__name__)

_nlp_cache: Dict[str, "spacy.language.Language"] = {}


def load_spacy_model(model_name: str):
    """Load (and cache) a spaCy model, downloading it once if missing."""
    if model_name in _nlp_cache:
        return _nlp_cache[model_name]

    try:
        nlp = spacy.load(model_name)
    except OSError:
        logger.info("spaCy model '%s' not found — downloading it now.", model_name)
        from spacy.cli import download

        download(model_name)
        nlp = spacy.load(model_name)

    _nlp_cache[model_name] = nlp
    return nlp


class TextPreprocessor:
    """Text cleaning, tokenization and linguistic feature extraction."""

    def __init__(self, spacy_model: str = None):
        self._model_name = spacy_model or settings.SPACY_MODEL

    @property
    def nlp(self):
        return load_spacy_model(self._model_name)

    def preprocess(self, text: str) -> str:
        """Basic cleaning: lowercase, strip URLs/emails, normalize whitespace."""
        text = self.lowercase(text)
        text = self.remove_urls(text)
        text = self.remove_emails(text)
        text = self.normalize_whitespace(text)
        return text

    def lowercase(self, text: str) -> str:
        return text.lower()

    def remove_urls(self, text: str) -> str:
        return re.sub(r"https?://\S+|www\.\S+", "", text)

    def remove_emails(self, text: str) -> str:
        return re.sub(r"\S+@\S+", "", text)

    def remove_punctuation(self, text: str) -> str:
        return re.sub(r"[^\w\s]", "", text)

    def normalize_whitespace(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def tokenize(self, text: str) -> List[str]:
        """Split into word tokens."""
        return [token.text for token in self.nlp(text) if not token.is_space]

    def tokenize_meaningful(self, text: str) -> List[str]:
        """Lemmas without stop words, punctuation or single characters."""
        return [
            token.lemma_.lower()
            for token in self.nlp(text)
            if not token.is_stop
            and not token.is_punct
            and not token.is_space
            and len(token.text) > 1
        ]

    def lemmatize(self, text: str) -> str:
        """Return the text with every token replaced by its lemma."""
        return " ".join(token.lemma_ for token in self.nlp(text) if not token.is_space)

    def get_nouns_and_verbs(self, text: str) -> List[str]:
        """Lemmas of nouns, proper nouns and verbs (content words)."""
        return [
            token.lemma_.lower()
            for token in self.nlp(text)
            if token.pos_ in ("NOUN", "PROPN", "VERB") and not token.is_stop and len(token.text) > 2
        ]

    def get_entities(self, text: str) -> List[Dict]:
        """Named entities with their character offsets."""
        doc = self.nlp(text)
        return [
            {"text": ent.text, "label": ent.label_, "start": ent.start_char, "end": ent.end_char}
            for ent in doc.ents
        ]

    def get_noun_chunks(self, text: str) -> List[str]:
        """Noun phrases (multi-word concepts)."""
        return [chunk.text.lower() for chunk in self.nlp(text).noun_chunks]

    def get_sentences(self, text: str) -> List[str]:
        """Sentence segmentation."""
        return [sent.text.strip() for sent in self.nlp(text).sents if sent.text.strip()]

    def word_count(self, text: str) -> int:
        return len(self.tokenize(text))

    def sentence_count(self, text: str) -> int:
        return len(self.get_sentences(text))


# Backwards-compatible module-level instance
text_preprocessor = TextPreprocessor()
