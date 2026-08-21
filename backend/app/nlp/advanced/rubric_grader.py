"""Smart Grading Rubric — evaluates answers on 5 criteria with detailed feedback."""
import re
from typing import Dict, List


class RubricGrader:
    """Grade student answers on 5 criteria (0-20 each, total 100).
    
    Criteria:
    1. Relevance (0-20): Does the answer address the question?
    2. Depth (0-20): How thorough and detailed is the answer?
    3. Clarity (0-20): Is the writing clear, grammatical, well-structured?
    4. Critical Thinking (0-20): Does the answer show analysis/originality?
    5. Structure (0-20): Is the answer well-organized with logical flow?
    """

    HEDGE_WORDS = {"however", "although", "nevertheless", "conversely", "whereas",
                   "on the other hand", "in contrast", "despite", "nonetheless"}
    ANALYSIS_WORDS = {"because", "therefore", "thus", "consequently", "as a result",
                      "this means", "this suggests", "this implies", "this indicates",
                      "the reason", "the effect", "the impact", "the significance"}
    EXAMPLE_WORDS = {"for example", "for instance", "such as", "specifically",
                     "in particular", "to illustrate", "e.g.", "namely"}
    STRUCTURE_MARKERS = {"firstly", "secondly", "thirdly", "finally", "in conclusion",
                         "to summarize", "in summary", "first", "second", "third",
                         "moreover", "furthermore", "additionally", "also"}

    def grade(self, student_answer: str, model_answer: str, question: str,
              total_marks: float = 10.0) -> Dict:
        """Grade an answer and return detailed rubric scores."""
        if not student_answer or not student_answer.strip():
            return self._empty_result(total_marks)

        sa = student_answer.strip()
        ma = model_answer.strip() if model_answer else ""
        q = question.strip() if question else ""

        # Score each criterion
        relevance = self._score_relevance(sa, ma, q)
        depth = self._score_depth(sa, ma)
        clarity = self._score_clarity(sa)
        thinking = self._score_critical_thinking(sa)
        structure = self._score_structure(sa)

        # Generate feedback per criterion
        feedback = {
            "relevance": self._feedback_relevance(sa, ma, relevance),
            "depth": self._feedback_depth(sa, ma, depth),
            "clarity": self._feedback_clarity(sa, clarity),
            "critical_thinking": self._feedback_thinking(sa, thinking),
            "structure": self._feedback_structure(sa, structure),
        }

        # Calculate weighted total (each criterion 0-20, total 0-100)
        raw_total = relevance + depth + clarity + thinking + structure
        # Scale to question marks
        scaled_total = raw_total / 100.0 * total_marks

        return {
            "criteria": {
                "relevance": {"score": round(relevance, 1), "max": 20, "feedback": feedback["relevance"]},
                "depth": {"score": round(depth, 1), "max": 20, "feedback": feedback["depth"]},
                "clarity": {"score": round(clarity, 1), "max": 20, "feedback": feedback["clarity"]},
                "critical_thinking": {"score": round(thinking, 1), "max": 20, "feedback": feedback["critical_thinking"]},
                "structure": {"score": round(structure, 1), "max": 20, "feedback": feedback["structure"]},
            },
            "raw_total": round(raw_total, 1),
            "scaled_total": round(scaled_total, 2),
            "total_marks": total_marks,
            "overall_feedback": self._overall_feedback(raw_total, feedback),
            "grade_letter": self._letter_grade(raw_total),
        }

    # ── Scoring Methods ──────────────────────────────────────

    def _score_relevance(self, sa: str, ma: str, q: str) -> float:
        """Score how relevant the answer is to the question."""
        sa_words = set(sa.lower().split())
        ma_words = set(ma.lower().split()) if ma else set()
        q_words = set(q.lower().split()) if q else set()

        # Remove common stop words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                      "being", "have", "has", "had", "do", "does", "did", "will",
                      "would", "could", "should", "may", "might", "can", "shall",
                      "of", "in", "to", "for", "with", "on", "at", "from", "by",
                      "about", "as", "into", "through", "during", "before", "after",
                      "and", "but", "or", "not", "this", "that", "these", "those",
                      "it", "its", "they", "them", "their", "we", "our", "you", "your"}

        sa_content = sa_words - stop_words
        ma_content = ma_words - stop_words
        q_content = q_words - stop_words

        score = 0.0

        # Question keyword coverage
        if q_content:
            q_overlap = len(sa_content & q_content) / len(q_content)
            score += q_overlap * 8

        # Model answer keyword coverage
        if ma_content:
            ma_overlap = len(sa_content & ma_content) / len(ma_content)
            score += ma_overlap * 10

        # Length adequacy (too short = probably not relevant enough)
        word_count = len(sa.split())
        if word_count >= 50:
            score += 2
        elif word_count >= 30:
            score += 1
        elif word_count < 10:
            score -= 3

        return max(0, min(20, score))

    def _score_depth(self, sa: str, ma: str) -> float:
        """Score how thorough and detailed the answer is."""
        sa_lower = sa.lower()
        word_count = len(sa.split())

        score = 0.0

        # Length-based depth (longer = more detailed, up to a point)
        if word_count >= 100:
            score += 8
        elif word_count >= 60:
            score += 6
        elif word_count >= 30:
            score += 4
        elif word_count >= 15:
            score += 2

        # Specific details (numbers, examples, definitions)
        examples = sum(1 for w in self.EXAMPLE_WORDS if w in sa_lower)
        score += min(4, examples * 1.5)

        # Definitions and explanations
        definition_markers = ["is defined as", "refers to", "means", "is a", "is the",
                              "can be described", "is known as", "is characterized"]
        definitions = sum(1 for d in definition_markers if d in sa_lower)
        score += min(3, definitions * 1.5)

        # Supporting evidence
        evidence_markers = ["research", "study", "evidence", "data", "statistics",
                            "according to", "findings", "results show"]
        evidence = sum(1 for e in evidence_markers if e in sa_lower)
        score += min(3, evidence * 1.5)

        # Comparison with model answer length
        if ma:
            ma_len = len(ma.split())
            if ma_len > 0:
                ratio = min(1.0, word_count / ma_len)
                score += ratio * 2

        return max(0, min(20, score))

    def _score_clarity(self, sa: str) -> float:
        """Score writing clarity and grammar."""
        sentences = re.split(r'[.!?]+', sa)
        sentences = [s.strip() for s in sentences if s.strip()]
        words = sa.split()

        score = 10.0  # Start at baseline

        # Average sentence length (10-25 words is ideal)
        if sentences:
            avg_len = len(words) / len(sentences)
            if 10 <= avg_len <= 25:
                score += 4
            elif 8 <= avg_len <= 30:
                score += 2
            elif avg_len > 40:
                score -= 3  # Very long sentences = unclear

        # Sentence variety (different lengths = better writing)
        if len(sentences) >= 3:
            lengths = [len(s.split()) for s in sentences]
            mean_len = sum(lengths) / len(lengths)
            variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
            if variance > 10:
                score += 3  # Good variety
            elif variance > 5:
                score += 1

        # Check for common grammar issues
        grammar_issues = 0
        if re.search(r'\bi\b', sa) and not re.search(r'\bI\b', sa):
            # Lowercase "i" instead of "I"
            grammar_issues += 1
        if re.search(r'\s{2,}', sa):
            grammar_issues += 1  # Double spaces
        if not sa[0].isupper():
            grammar_issues += 1  # Not capitalized

        score -= grammar_issues * 1.5

        # Paragraphs (if multi-line)
        paragraphs = [p.strip() for p in sa.split('\n') if p.strip()]
        if len(paragraphs) >= 2:
            score += 2

        # Starts with capital, ends with punctuation
        if sa and sa[0].isupper():
            score += 0.5
        if sa and sa[-1] in '.!?':
            score += 0.5

        return max(0, min(20, score))

    def _score_critical_thinking(self, sa: str) -> float:
        """Score analysis, originality, and critical thinking."""
        sa_lower = sa.lower()

        score = 0.0

        # Analysis language
        analysis_count = sum(1 for w in self.ANALYSIS_WORDS if w in sa_lower)
        score += min(6, analysis_count * 1.5)

        # Hedging/nuance (shows balanced thinking)
        hedge_count = sum(1 for w in self.HEDGE_WORDS if w in sa_lower)
        score += min(4, hedge_count * 2)

        # Comparison/contrast
        compare_words = ["compared to", "unlike", "similar to", "in contrast",
                         "while", "whereas", "both", "differ from"]
        compare_count = sum(1 for w in compare_words if w in sa_lower)
        score += min(4, compare_count * 2)

        # Cause-effect reasoning
        cause_effect = ["leads to", "results in", "causes", "affects", "influences",
                        "contributes to", "impacts", "stems from", "arises from"]
        cause_count = sum(1 for w in cause_effect if w in sa_lower)
        score += min(3, cause_count * 1.5)

        # Evaluation language
        eval_words = ["effective", "significant", "important", "crucial", "essential",
                      "beneficial", "harmful", "advantage", "disadvantage", "strength", "weakness"]
        eval_count = sum(1 for w in eval_words if w in sa_lower)
        score += min(3, eval_count * 1)

        return max(0, min(20, score))

    def _score_structure(self, sa: str) -> float:
        """Score organization and logical flow."""
        sa_lower = sa.lower()
        sentences = re.split(r'[.!?]+', sa)
        sentences = [s.strip() for s in sentences if s.strip()]

        score = 0.0

        # Has introduction (first sentence sets context)
        if sentences:
            first = sentences[0].lower()
            intro_markers = ["the", "this", "in", "when", "as", "business",
                             "communication", "effective", "non-verbal"]
            if any(first.startswith(m) for m in intro_markers):
                score += 3

        # Has conclusion
        if sentences and len(sentences) >= 3:
            last = sentences[-1].lower()
            conclusion_markers = ["in summary", "in conclusion", "overall", "therefore",
                                  "thus", "in essence", "to summarize", "finally"]
            if any(last.startswith(m) for m in conclusion_markers):
                score += 4
            elif any(m in last for m in conclusion_markers):
                score += 3

        # Transition words (logical flow)
        transition_count = sum(1 for m in self.STRUCTURE_MARKERS if m in sa_lower)
        score += min(5, transition_count * 1.2)

        # Numbered/ordered points
        ordered = sum(1 for s in sentences if re.match(r'^\s*(first|second|third|1\.|2\.|3\.)',
                                                        s.strip().lower()))
        score += min(4, ordered * 1.5)

        # Paragraph structure
        paragraphs = [p.strip() for p in sa.split('\n') if p.strip()]
        if len(paragraphs) >= 3:
            score += 4
        elif len(paragraphs) >= 2:
            score += 2

        return max(0, min(20, score))

    # ── Feedback Generation ──────────────────────────────────

    def _feedback_relevance(self, sa: str, ma: str, score: float) -> str:
        if score >= 16:
            return "Excellent relevance. The answer directly addresses the question with comprehensive coverage of key points."
        elif score >= 12:
            return "Good relevance. Most key points are addressed, but some aspects could be explored further."
        elif score >= 8:
            return "Moderate relevance. The answer partially addresses the question but misses several important points."
        else:
            return "Low relevance. The answer does not adequately address the question. Focus on the specific topic asked."

    def _feedback_depth(self, sa: str, ma: str, score: float) -> str:
        if score >= 16:
            return "Excellent depth with detailed explanations, examples, and supporting evidence."
        elif score >= 12:
            return "Good depth. The answer covers the topic well but could include more specific examples or evidence."
        elif score >= 8:
            return "Moderate depth. The answer is somewhat superficial. Add more details, examples, and explanations."
        else:
            return "Insufficient depth. The answer is too brief. Expand with detailed explanations and concrete examples."

    def _feedback_clarity(self, sa: str, score: float) -> str:
        if score >= 16:
            return "Excellent clarity. Well-written with proper grammar, varied sentence structure, and clear expression."
        elif score >= 12:
            return "Good clarity. Generally well-written with minor areas for improvement in expression."
        elif score >= 8:
            return "Moderate clarity. Some sentences are unclear or grammatically awkward. Review sentence structure."
        else:
            return "Poor clarity. Multiple grammar issues and unclear expressions. Focus on writing complete, clear sentences."

    def _feedback_thinking(self, sa: str, score: float) -> str:
        if score >= 16:
            return "Strong critical thinking. Shows analysis, evaluation, and original insights."
        elif score >= 12:
            return "Good analytical thinking. Includes some analysis and reasoning. Could explore cause-effect more."
        elif score >= 8:
            return "Basic thinking shown. Mostly descriptive. Add more analysis, comparisons, and evaluations."
        else:
            return "Limited critical thinking. The answer is purely descriptive. Analyze why, how, and what impact."

    def _feedback_structure(self, sa: str, score: float) -> str:
        if score >= 16:
            return "Well-structured answer with clear introduction, logical flow, and strong conclusion."
        elif score >= 12:
            return "Good structure. Has a logical flow but could benefit from a clearer introduction or conclusion."
        elif score >= 8:
            return "Basic structure. The answer lacks clear organization. Use paragraphs and transition words."
        else:
            return "Poor structure. The answer needs a clear beginning, middle, and end. Organize ideas logically."

    def _overall_feedback(self, total: float, feedback: dict) -> str:
        if total >= 80:
            return "Outstanding answer! Demonstrates comprehensive understanding with excellent writing and critical analysis."
        elif total >= 65:
            return "Good answer with solid understanding. Minor improvements possible in depth and analysis."
        elif total >= 50:
            return "Adequate answer meeting basic requirements. Work on providing more detailed analysis and clearer writing."
        elif total >= 35:
            return "Below average. The answer needs improvement in multiple areas. Review the topic and practice writing structured responses."
        else:
            return "Needs significant improvement. The answer does not demonstrate sufficient understanding. Please review course materials."

    def _letter_grade(self, total: float) -> str:
        if total >= 90: return "A+"
        if total >= 80: return "A"
        if total >= 70: return "B"
        if total >= 60: return "C"
        if total >= 50: return "D"
        return "F"

    def _empty_result(self, total_marks: float) -> Dict:
        return {
            "criteria": {
                "relevance": {"score": 0, "max": 20, "feedback": "No answer provided."},
                "depth": {"score": 0, "max": 20, "feedback": "No answer provided."},
                "clarity": {"score": 0, "max": 20, "feedback": "No answer provided."},
                "critical_thinking": {"score": 0, "max": 20, "feedback": "No answer provided."},
                "structure": {"score": 0, "max": 20, "feedback": "No answer provided."},
            },
            "raw_total": 0,
            "scaled_total": 0,
            "total_marks": total_marks,
            "overall_feedback": "No answer submitted.",
            "grade_letter": "F",
        }
