"""Tests for NLP engine components."""
import pytest
from app.nlp.tokenizer import TextPreprocessor
from app.nlp.keyword_extractor import KeywordExtractor
from app.nlp.similarity import SemanticSimilarity
from app.nlp.grammar_checker import GrammarChecker
from app.nlp.scorer import ExamScorer


class TestTextPreprocessor:
    """Test the spaCy-based text preprocessor."""

    def test_lowercase(self):
        tp = TextPreprocessor()
        assert tp.lowercase("Hello World") == "hello world"

    def test_remove_urls(self):
        tp = TextPreprocessor()
        result = tp.remove_urls("Visit https://example.com for more")
        assert "https" not in result
        assert "Visit" in result

    def test_normalize_whitespace(self):
        tp = TextPreprocessor()
        assert tp.normalize_whitespace("hello   world") == "hello world"

    def test_tokenize(self):
        tp = TextPreprocessor()
        tokens = tp.tokenize("The quick brown fox")
        assert len(tokens) >= 4

    def test_tokenize_meaningful(self):
        tp = TextPreprocessor()
        tokens = tp.tokenize_meaningful("The quick brown fox jumps over the lazy dog")
        # Should filter stopwords
        assert "the" not in [t.lower() for t in tokens]
        assert len(tokens) >= 4

    def test_lemmatize(self):
        tp = TextPreprocessor()
        result = tp.lemmatize("The cats are running quickly")
        assert "cat" in result.lower()

    def test_get_nouns_and_verbs(self):
        tp = TextPreprocessor()
        result = tp.get_nouns_and_verbs("Python programming language is powerful")
        assert len(result) >= 2

    def test_get_sentences(self):
        tp = TextPreprocessor()
        sents = tp.get_sentences("First sentence. Second sentence. Third one.")
        assert len(sents) >= 2

    def test_get_entities(self):
        tp = TextPreprocessor()
        ents = tp.get_entities("Apple Inc. is based in California")
        assert len(ents) >= 1


class TestKeywordExtractor:
    """Test keyword extraction strategies."""

    def test_extract_tfidf_keywords(self):
        ke = KeywordExtractor()
        kws = ke.extract_tfidf_keywords(
            "Python is a popular programming language used for web development and data science"
        )
        assert len(kws) >= 1
        assert all(isinstance(k, tuple) and len(k) == 2 for k in kws)

    def test_extract_spacy_keywords(self):
        ke = KeywordExtractor()
        kws = ke.extract_spacy_keywords(
            "Albert Einstein developed the theory of relativity in physics"
        )
        assert len(kws) >= 1

    def test_extract_from_model_answer(self):
        ke = KeywordExtractor()
        kws = ke.extract_from_model_answer(
            "Photosynthesis is the process by which plants convert sunlight into energy using chlorophyll"
        )
        assert len(kws) >= 2
        assert any("photosynthesis" in k.lower() or "plant" in k.lower() or "sunlight" in k.lower() for k in kws)

    def test_check_keywords_in_answer(self):
        ke = KeywordExtractor()
        result = ke.check_keywords_in_answer(
            ["photosynthesis", "sunlight", "chlorophyll"],
            "Photosynthesis uses sunlight and chlorophyll to produce energy"
        )
        assert result["found_count"] >= 2
        assert result["match_ratio"] > 0.5

    def test_check_keywords_missing(self):
        ke = KeywordExtractor()
        result = ke.check_keywords_in_answer(
            ["quantum", "entanglement", "superposition"],
            "Photosynthesis uses sunlight for energy"
        )
        assert result["found_count"] < result["total_count"]


class TestSemanticSimilarity:
    """Test semantic similarity calculations."""

    def test_tfidf_cosine_similar(self):
        ss = SemanticSimilarity()
        sim = ss.tfidf_cosine_similarity(
            "Python is a programming language",
            "Python programming language for coding"
        )
        assert 0.0 <= sim <= 1.0
        assert sim > 0.3  # Should be somewhat similar

    def test_tfidf_cosine_different(self):
        ss = SemanticSimilarity()
        sim = ss.tfidf_cosine_similarity(
            "Python is a programming language",
            "The cat sat on the mat"
        )
        assert sim < 0.5

    def test_word_overlap_similarity(self):
        ss = SemanticSimilarity()
        sim = ss.word_overlap_similarity(
            "machine learning algorithms",
            "learning machine models"
        )
        assert sim > 0.15  # Jaccard with 3 tokens each, some overlap

    def test_spacy_similarity(self):
        ss = SemanticSimilarity()
        sim = ss.spacy_similarity(
            "The dog chased the cat",
            "A dog was chasing a cat"
        )
        assert 0.0 <= sim <= 1.0
        assert sim > 0.3

    def test_calculate_similarity_all_methods(self):
        ss = SemanticSimilarity()
        result = ss.calculate_similarity(
            "Variables represent unknown values in algebra",
            "In algebra, variables stand for unknown quantities"
        )
        assert "tfidf_cosine" in result
        assert "word_overlap" in result
        assert "spacy_vectors" in result
        assert "weighted_average" in result
        assert 0.0 <= result["weighted_average"] <= 1.0


class TestGrammarChecker:
    """Test grammar checking."""

    def test_clean_text_high_score(self):
        gc = GrammarChecker()
        score = gc.calculate_grammar_score(
            "The quick brown fox jumps over the lazy dog. This is a well-written sentence."
        )
        assert score >= 0.8

    def test_empty_text_zero_score(self):
        gc = GrammarChecker()
        assert gc.calculate_grammar_score("") == 0.0

    def test_detect_capitalization_error(self):
        gc = GrammarChecker()
        issues = gc.check_grammar("i am going to the store")
        # Should detect lowercase 'i'
        assert any("capital" in iss["message"].lower() or "CAPITALIZATION" in iss.get("category", "") for iss in issues)

    def test_count_errors(self):
        gc = GrammarChecker()
        count = gc.count_errors("i thinks theire going to the store")
        assert count >= 1

    def test_get_suggestions(self):
        gc = GrammarChecker()
        suggestions = gc.get_suggestions("i thinks theire going to the store")
        assert len(suggestions) >= 1

    def test_calculate_grammar_score(self):
        gc = GrammarChecker()
        score = gc.calculate_grammar_score("This is a well written sentence with proper grammar.")
        assert 0.0 <= score <= 1.0


class TestExamScorer:
    """Test the full scoring pipeline."""

    def test_score_perfect_answer(self):
        scorer = ExamScorer()
        result = scorer.score_answer(
            student_answer="Variables are symbols that represent unknown values in algebraic expressions and equations.",
            model_answer="Variables are symbols that represent unknown values in algebraic expressions and equations.",
            total_marks=10.0,
        )
        assert result.total_score >= 7.0  # Should score high
        assert result.keyword_score >= 0.5
        assert result.similarity_score >= 0.5

    def test_score_poor_answer(self):
        scorer = ExamScorer()
        result = scorer.score_answer(
            student_answer="I don't know.",
            model_answer="Variables are symbols that represent unknown values in algebraic expressions and equations.",
            total_marks=10.0,
        )
        assert result.total_score < 5.0  # Should score low

    def test_score_empty_answer(self):
        scorer = ExamScorer()
        result = scorer.score_answer(
            student_answer="",
            model_answer="Variables represent unknown values.",
            total_marks=10.0,
        )
        assert result.total_score < 3.0

    def test_feedback_generated(self):
        scorer = ExamScorer()
        result = scorer.score_answer(
            student_answer="Variables are symbols for unknowns in equations.",
            model_answer="Variables are symbols that represent unknown values in algebraic expressions and equations.",
            total_marks=10.0,
        )
        assert len(result.feedback) > 0

    def test_score_range(self):
        scorer = ExamScorer()
        result = scorer.score_answer(
            student_answer="Variables are symbols that represent unknown values in algebraic expressions and equations.",
            model_answer="Variables are symbols that represent unknown values in algebraic expressions and equations.",
            total_marks=20.0,
        )
        assert 0.0 <= result.total_score <= 20.0
        assert 0.0 <= result.keyword_score <= 1.0
        assert 0.0 <= result.similarity_score <= 1.0
        assert 0.0 <= result.grammar_score <= 1.0
        assert 0.0 <= result.completeness_score <= 1.0
