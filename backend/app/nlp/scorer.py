"""Advanced Exam Scorer - orchestrates all NLP components."""
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from app.nlp.tokenizer import TextPreprocessor
from app.nlp.keyword_extractor import KeywordExtractor
from app.nlp.similarity import SemanticSimilarity
from app.nlp.grammar_checker import GrammarChecker
from app.config import settings


@dataclass
class ScoringResult:
    """Complete scoring result container."""
    keyword_score: float = 0.0
    similarity_score: float = 0.0
    grammar_score: float = 0.0
    completeness_score: float = 0.0
    total_score: float = 0.0
    feedback: str = ""
    found_keywords: List[str] = field(default_factory=list)
    missing_keywords: List[str] = field(default_factory=list)
    grammar_issues: int = 0
    grammar_suggestions: List[str] = field(default_factory=list)
    similarity_details: Dict[str, float] = field(default_factory=dict)
    keyword_match_ratio: float = 0.0


class ExamScorer:
    """Advanced NLP-powered exam answer scorer.

    Scoring weights:
    - Keyword matching: 30%
    - Semantic similarity: 40%
    - Grammar quality: 15%
    - Completeness: 15%
    """

    def __init__(self):
        self.preprocessor = TextPreprocessor()
        self.keyword_extractor = KeywordExtractor()
        self.similarity = SemanticSimilarity()
        self.grammar_checker = GrammarChecker()
        self.keyword_weight = settings.KEYWORD_WEIGHT
        self.similarity_weight = settings.SIMILARITY_WEIGHT
        self.grammar_weight = settings.GRAMMAR_WEIGHT
        self.completeness_weight = settings.COMPLETENESS_WEIGHT

    def calculate_keyword_score(
        self, model_answer: str, student_answer: str
    ) -> Dict[str, any]:
        """Score based on keyword matching."""
        model_keywords = self.keyword_extractor.extract_from_model_answer(model_answer)

        if not model_keywords:
            return {"score": 1.0, "found": [], "missing": [], "ratio": 1.0}

        result = self.keyword_extractor.check_keywords_in_answer(model_keywords, student_answer)

        return {
            "score": result["match_ratio"],
            "found": result["found"],
            "missing": result["missing"],
            "ratio": result["match_ratio"],
        }

    def calculate_similarity_score(
        self, model_answer: str, student_answer: str
    ) -> Dict[str, any]:
        """Score based on semantic similarity."""
        sim_results = self.similarity.calculate_similarity(model_answer, student_answer)

        return {
            "score": sim_results["weighted_average"],
            "details": sim_results,
        }

    def calculate_grammar_score(self, student_answer: str) -> Dict[str, any]:
        """Score based on grammar quality."""
        score = self.grammar_checker.calculate_grammar_score(student_answer)
        error_count = self.grammar_checker.count_errors(student_answer)
        suggestions = self.grammar_checker.get_suggestions(student_answer)

        return {
            "score": score,
            "error_count": error_count,
            "suggestions": suggestions,
        }

    def calculate_completeness_score(
        self, model_answer: str, student_answer: str
    ) -> float:
        """Score based on how complete the answer is compared to model."""
        model_sentences = self.preprocessor.get_sentences(model_answer)
        student_sentences = self.preprocessor.get_sentences(student_answer)

        if not model_sentences:
            return 1.0

        # Check how many model sentence concepts are covered
        coverage_scores = []
        for model_sent in model_sentences:
            model_concepts = set(self.preprocessor.get_nouns_and_verbs(model_sent))
            if not model_concepts:
                continue

            best_coverage = 0.0
            for student_sent in student_sentences:
                student_concepts = set(self.preprocessor.get_nouns_and_verbs(student_sent))
                if not student_concepts:
                    continue
                overlap = model_concepts & student_concepts
                coverage = len(overlap) / len(model_concepts)
                best_coverage = max(best_coverage, coverage)

            coverage_scores.append(best_coverage)

        if not coverage_scores:
            return 0.5

        # Average coverage across model sentences
        avg_coverage = sum(coverage_scores) / len(coverage_scores)

        # Bonus for reasonable answer length
        model_len = len(model_answer.split())
        student_len = len(student_answer.split())
        length_ratio = min(student_len / max(model_len, 1), 1.5) / 1.5

        # Combine
        score = (avg_coverage * 0.7) + (length_ratio * 0.3)
        return round(min(1.0, score), 4)

    def generate_feedback(
        self,
        keyword_result: Dict,
        similarity_result: Dict,
        grammar_result: Dict,
        completeness_score: float,
        total_score: float,
        total_marks: float,
    ) -> str:
        """Generate detailed human-readable feedback."""
        feedback_parts = []
        pct = (total_score / max(total_marks, 1)) * 100

        # Overall assessment
        if pct >= 90:
            feedback_parts.append("🌟 Excellent answer! Outstanding work.")
        elif pct >= 75:
            feedback_parts.append("✅ Very good answer! Well done.")
        elif pct >= 60:
            feedback_parts.append("👍 Good answer, but there's room for improvement.")
        elif pct >= 40:
            feedback_parts.append("📚 Fair answer. Review the key concepts below.")
        else:
            feedback_parts.append("⚠️ Needs significant improvement. Study the topic more carefully.")

        # Keyword feedback
        missing = keyword_result.get("missing", [])
        if missing:
            feedback_parts.append(f"Missing key terms: {', '.join(missing[:5])}")

        # Similarity feedback
        sim_score = similarity_result.get("score", 0)
        if sim_score >= 0.7:
            feedback_parts.append("Your answer captures the main concepts well.")
        elif sim_score >= 0.4:
            feedback_parts.append("Your answer partially addresses the question. Try to cover more key points.")
        else:
            feedback_parts.append("Your answer diverges significantly from the expected response. Focus on the core concepts.")

        # Grammar feedback
        grammar_errors = grammar_result.get("error_count", 0)
        if grammar_errors > 0:
            feedback_parts.append(f"Found {grammar_errors} grammar issue(s).")
            suggestions = grammar_result.get("suggestions", [])
            if suggestions:
                feedback_parts.append(f"Suggestions: {'; '.join(suggestions[:2])}")

        # Completeness feedback
        if completeness_score >= 0.8:
            feedback_parts.append("Your answer covers the topic comprehensively.")
        elif completeness_score >= 0.5:
            feedback_parts.append("Your answer covers some key points but misses others.")
        else:
            feedback_parts.append("Your answer is incomplete. Try to address all aspects of the question.")

        return " ".join(feedback_parts)

    def score_answer(
        self,
        student_answer: str,
        model_answer: str,
        total_marks: float = 20.0,
        keywords: list = None,
        question_marks: float = None,
        weights: dict = None,
    ) -> ScoringResult:
        """Main scoring method - orchestrates all NLP components.

        Args:
            weights: Optional dict with keyword_weight, similarity_weight,
                     grammar_weight, completeness_weight (0.0-1.0 each).
                     If provided, overrides the instance defaults.
        """
        if question_marks is not None:
            total_marks = question_marks

        # Use provided weights or fall back to instance defaults
        kw = weights["keyword_weight"] if weights else self.keyword_weight
        sw = weights["similarity_weight"] if weights else self.similarity_weight
        gw = weights["grammar_weight"] if weights else self.grammar_weight
        cw = weights["completeness_weight"] if weights else self.completeness_weight

        # 1. Keyword analysis
        keyword_result = self.calculate_keyword_score(model_answer, student_answer)

        # 2. Similarity analysis
        similarity_result = self.calculate_similarity_score(model_answer, student_answer)

        # 3. Grammar analysis
        grammar_result = self.calculate_grammar_score(student_answer)

        # 4. Completeness analysis
        completeness_score = self.calculate_completeness_score(model_answer, student_answer)

        # 5. Calculate weighted total
        weighted = (
            keyword_result["score"] * kw
            + similarity_result["score"] * sw
            + grammar_result["score"] * gw
            + completeness_score * cw
        )

        total_score = round(weighted * total_marks, 2)

        # Minimum relevance check: completely irrelevant answers get 0
        # If keyword match is very low AND similarity is low, answer is irrelevant
        if keyword_result["score"] < 0.15 and similarity_result["score"] < 0.15:
            total_score = 0.0
        # Short answers (less than 5 words) with no keyword match = 0
        elif len(student_answer.strip().split()) < 5 and keyword_result["score"] < 0.2:
            total_score = 0.0

        # 6. Generate feedback
        feedback = self.generate_feedback(
            keyword_result, similarity_result, grammar_result,
            completeness_score, total_score, total_marks
        )

        return ScoringResult(
            keyword_score=round(keyword_result["score"], 4),
            similarity_score=round(similarity_result["score"], 4),
            grammar_score=round(grammar_result["score"], 4),
            completeness_score=round(completeness_score, 4),
            total_score=total_score,
            feedback=feedback,
            found_keywords=keyword_result.get("found", []),
            missing_keywords=keyword_result.get("missing", []),
            grammar_issues=grammar_result.get("error_count", 0),
            grammar_suggestions=grammar_result.get("suggestions", []),
            similarity_details=similarity_result.get("details", {}),
            keyword_match_ratio=keyword_result.get("ratio", 0.0),
        )


# Singleton
exam_scorer = ExamScorer()


def get_scorer() -> ExamScorer:
    """Get the singleton ExamScorer instance."""
    return exam_scorer
