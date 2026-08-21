"""Class Intelligence Report — analyzes all students' performance patterns."""
import re
import statistics
from typing import Dict, List, Tuple
from collections import Counter, defaultdict


class ClassIntelligence:
    """Analyze exam results to find patterns, weak areas, and recommendations."""

    def analyze(self, exam_data: List[Dict]) -> Dict:
        """Analyze an entire exam's student answers.
        
        exam_data: list of dicts with keys:
            - student_name, student_id, question_id, question_text,
            - answer_text, model_answer, score, total_marks
        """
        if not exam_data:
            return {"error": "No data to analyze"}

        # Group by question
        by_question = defaultdict(list)
        for entry in exam_data:
            by_question[entry["question_id"]].append(entry)

        # Group by student
        by_student = defaultdict(list)
        for entry in exam_data:
            by_student[entry["student_id"]].append(entry)

        # Analyze per-question
        question_analysis = []
        for qid, entries in by_question.items():
            qa = self._analyze_question(qid, entries)
            question_analysis.append(qa)

        # Analyze per-student
        student_analysis = []
        for sid, entries in by_student.items():
            sa = self._analyze_student(sid, entries)
            student_analysis.append(sa)

        # Overall class insights
        insights = self._generate_insights(question_analysis, student_analysis, exam_data)

        # Identify struggling students
        at_risk = [s for s in student_analysis if s["percentage"] < 40]

        # Identify common mistakes
        common_mistakes = self._find_common_mistakes(exam_data)

        # Topic mastery map
        topic_mastery = self._analyze_topic_mastery(question_analysis)

        return {
            "summary": {
                "total_students": len(by_student),
                "total_questions": len(by_question),
                "class_average": round(
                    statistics.mean([s["percentage"] for s in student_analysis]), 1
                ) if student_analysis else 0,
                "highest_score": max([s["percentage"] for s in student_analysis], default=0),
                "lowest_score": min([s["percentage"] for s in student_analysis], default=0),
                "pass_rate": round(
                    sum(1 for s in student_analysis if s["percentage"] >= 40) / max(len(student_analysis), 1) * 100, 1
                ),
            },
            "question_analysis": question_analysis,
            "student_rankings": sorted(student_analysis, key=lambda x: x["percentage"], reverse=True),
            "at_risk_students": at_risk,
            "common_mistakes": common_mistakes,
            "topic_mastery": topic_mastery,
            "insights": insights,
            "recommendations": self._generate_recommendations(question_analysis, student_analysis, at_risk),
        }

    def _analyze_question(self, qid: int, entries: List[Dict]) -> Dict:
        """Analyze performance on a single question."""
        scores = [e["score"] for e in entries if e.get("score") is not None]
        total_marks = entries[0].get("total_marks", 10) if entries else 10
        question_text = entries[0].get("question_text", "") if entries else ""

        if not scores:
            return {
                "question_id": qid,
                "question_text": question_text,
                "average_score": 0,
                "average_percentage": 0,
                "difficulty": "unknown",
                "discrimination": 0,
            }

        avg = statistics.mean(scores)
        avg_pct = avg / total_marks * 100 if total_marks > 0 else 0

        # Difficulty classification
        if avg_pct < 30:
            difficulty = "Very Hard"
        elif avg_pct < 50:
            difficulty = "Hard"
        elif avg_pct < 70:
            difficulty = "Medium"
        elif avg_pct < 85:
            difficulty = "Easy"
        else:
            difficulty = "Very Easy"

        # Discrimination index (how well the question separates strong/weak students)
        sorted_scores = sorted(zip([e["student_id"] for e in entries], scores), key=lambda x: x[1])
        n = len(sorted_scores)
        if n >= 4:
            top_group = sorted_scores[int(n * 0.7):]
            bottom_group = sorted_scores[:int(n * 0.3)]
            top_avg = statistics.mean([s for _, s in top_group]) if top_group else 0
            bottom_avg = statistics.mean([s for _, s in bottom_group]) if bottom_group else 0
            discrimination = (top_avg - bottom_avg) / total_marks if total_marks > 0 else 0
        else:
            discrimination = 0

        # Common keywords in answers
        all_words = []
        for e in entries:
            if e.get("answer_text"):
                words = re.findall(r'\b[a-z]{4,}\b', e["answer_text"].lower())
                all_words.extend(words)
        stop_words = {"the", "that", "this", "with", "from", "have", "been", "were", "they",
                      "their", "about", "would", "could", "should", "which", "when", "what",
                      "also", "more", "than", "some", "such", "into", "only", "other", "most"}
        word_freq = Counter(w for w in all_words if w not in stop_words)
        top_keywords = [w for w, _ in word_freq.most_common(5)]

        # Model answer keyword coverage
        model_answer = entries[0].get("model_answer", "") if entries else ""
        model_keywords = set()
        if model_answer:
            model_keywords = set(re.findall(r'\b[a-z]{4,}\b', model_answer.lower())) - stop_words

        avg_keyword_coverage = 0
        if model_keywords:
            coverages = []
            for e in entries:
                if e.get("answer_text"):
                    ans_words = set(re.findall(r'\b[a-z]{4,}\b', e["answer_text"].lower()))
                    coverage = len(ans_words & model_keywords) / len(model_keywords)
                    coverages.append(coverage)
            avg_keyword_coverage = statistics.mean(coverages) if coverages else 0

        return {
            "question_id": qid,
            "question_text": question_text[:100],
            "average_score": round(avg, 2),
            "average_percentage": round(avg_pct, 1),
            "difficulty": difficulty,
            "discrimination": round(discrimination, 2),
            "top_keywords": top_keywords,
            "keyword_coverage": round(avg_keyword_coverage * 100, 1),
            "student_count": len(entries),
        }

    def _analyze_student(self, sid: int, entries: List[Dict]) -> Dict:
        """Analyze a single student's performance."""
        student_name = entries[0].get("student_name", f"Student #{sid}") if entries else f"Student #{sid}"
        scores = [e["score"] for e in entries if e.get("score") is not None]
        total_marks = sum(e.get("total_marks", 10) for e in entries)
        actual_total = sum(scores)
        percentage = actual_total / total_marks * 100 if total_marks > 0 else 0

        # Find weakest and strongest areas
        per_q = []
        for e in entries:
            if e.get("score") is not None and e.get("total_marks"):
                per_q.append({
                    "question_id": e["question_id"],
                    "score": e["score"],
                    "max": e["total_marks"],
                    "pct": e["score"] / e["total_marks"] * 100,
                })

        weakest = sorted(per_q, key=lambda x: x["pct"])[:2] if per_q else []
        strongest = sorted(per_q, key=lambda x: x["pct"], reverse=True)[:2] if per_q else []

        # Answer quality analysis
        all_answers = [e.get("answer_text", "") for e in entries if e.get("answer_text")]
        avg_length = statistics.mean([len(a.split()) for a in all_answers]) if all_answers else 0

        return {
            "student_id": sid,
            "student_name": student_name,
            "total_score": round(actual_total, 2),
            "total_marks": total_marks,
            "percentage": round(percentage, 1),
            "grade": self._letter_grade(percentage),
            "weakest_questions": weakest,
            "strongest_questions": strongest,
            "avg_answer_length": round(avg_length),
            "status": "Pass" if percentage >= 40 else "Fail",
        }

    def _find_common_mistakes(self, exam_data: List[Dict]) -> List[Dict]:
        """Find common mistakes across all students."""
        mistakes = []

        # Group by question
        by_question = defaultdict(list)
        for entry in exam_data:
            by_question[entry["question_id"]].append(entry)

        for qid, entries in by_question.items():
            model_answer = entries[0].get("model_answer", "") if entries else ""
            if not model_answer:
                continue

            model_words = set(re.findall(r'\b[a-z]{4,}\b', model_answer.lower()))
            stop_words = {"the", "that", "this", "with", "from", "have", "been", "were", "they",
                          "their", "about", "would", "could", "should", "which", "when", "what"}
            model_keywords = model_words - stop_words

            if not model_keywords:
                continue

            # Find keywords that most students missed
            missed_count = Counter()
            total_students = len(entries)
            for e in entries:
                if e.get("answer_text"):
                    ans_words = set(re.findall(r'\b[a-z]{4,}\b', e["answer_text"].lower()))
                    missed = model_keywords - ans_words
                    for w in missed:
                        missed_count[w] += 1

            # Keywords missed by >50% of students
            for keyword, count in missed_count.most_common(5):
                if count > total_students * 0.3:
                    mistakes.append({
                        "question_id": qid,
                        "keyword": keyword,
                        "students_missed": count,
                        "total_students": total_students,
                        "miss_rate": round(count / total_students * 100, 1),
                    })

        return sorted(mistakes, key=lambda x: x["miss_rate"], reverse=True)[:10]

    def _analyze_topic_mastery(self, question_analysis: List[Dict]) -> List[Dict]:
        """Analyze topic mastery levels."""
        topics = []
        for qa in question_analysis:
            pct = qa["average_percentage"]
            if pct >= 80:
                mastery = "Mastered"
            elif pct >= 60:
                mastery = "Proficient"
            elif pct >= 40:
                mastery = "Developing"
            else:
                mastery = "Needs Attention"

            topics.append({
                "question_id": qa["question_id"],
                "topic": qa["question_text"],
                "average": qa["average_percentage"],
                "mastery": mastery,
                "difficulty": qa["difficulty"],
            })
        return sorted(topics, key=lambda x: x["average"])

    def _generate_insights(self, questions: List, students: List, exam_data: List) -> List[str]:
        """Generate actionable insights."""
        insights = []

        if not students:
            return ["Insufficient data for analysis."]

        # Class performance insight
        avg = statistics.mean([s["percentage"] for s in students])
        if avg >= 70:
            insights.append(f"Class average is strong at {avg:.1f}%. Students demonstrate good understanding.")
        elif avg >= 50:
            insights.append(f"Class average is {avg:.1f}%. Some areas need reinforcement.")
        else:
            insights.append(f"Class average is low at {avg:.1f}%. Significant review of core concepts recommended.")

        # Hardest question
        if questions:
            hardest = min(questions, key=lambda x: x["average_percentage"])
            insights.append(
                f"Question {hardest['question_id']} was the hardest ({hardest['average_percentage']:.1f}% avg). "
                f"Students struggled with: {', '.join(hardest.get('top_keywords', [])[:3])}"
            )

        # Easiest question
            easiest = max(questions, key=lambda x: x["average_percentage"])
            insights.append(
                f"Question {easiest['question_id']} was the easiest ({easiest['average_percentage']:.1f}% avg)."
            )

        # Pass/fail distribution
        pass_count = sum(1 for s in students if s["percentage"] >= 40)
        fail_count = len(students) - pass_count
        insights.append(f"Pass rate: {pass_count}/{len(students)} ({pass_count/max(len(students),1)*100:.0f}%)")

        # Answer length insight
        avg_len = statistics.mean([s["avg_answer_length"] for s in students])
        if avg_len < 20:
            insights.append("Students are writing very short answers. Encourage more detailed responses.")

        return insights

    def _generate_recommendations(self, questions: List, students: List, at_risk: List) -> List[str]:
        """Generate specific recommendations for teachers."""
        recs = []

        # At-risk students
        if at_risk:
            names = [s["student_name"] for s in at_risk[:3]]
            recs.append(f"At-risk students needing immediate attention: {', '.join(names)}")

        # Hard questions needing re-teaching
        hard_qs = [q for q in questions if q["average_percentage"] < 40]
        if hard_qs:
            q_ids = [str(q["question_id"]) for q in hard_qs]
            recs.append(f"Questions {', '.join(q_ids)} scored below 40%. Consider re-teaching these topics.")

        # Low keyword coverage
        low_coverage = [q for q in questions if q.get("keyword_coverage", 100) < 40]
        if low_coverage:
            recs.append("Some questions have low keyword coverage. Provide clearer model answers for better self-study.")

        # General recommendations
        if not recs:
            recs.append("Class performance is satisfactory. Continue with current teaching approach.")

        return recs

    def _letter_grade(self, pct: float) -> str:
        if pct >= 90: return "A+"
        if pct >= 80: return "A"
        if pct >= 70: return "B"
        if pct >= 60: return "C"
        if pct >= 50: return "D"
        return "F"
