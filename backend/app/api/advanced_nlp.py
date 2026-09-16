"""Advanced NLP API endpoints — plagiarism, AI detection, feedback, rubric, model answer, class intelligence."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_teacher
from app.database import get_db
from app.models.answer import Score, StudentAnswer
from app.models.exam import Exam
from app.models.question import Question
from app.models.subject import Subject
from app.models.user import User, UserRole

router = APIRouter()


def _require_exam_access(db: Session, exam_id: int, current_user: User) -> None:
    """Teachers may only analyse exams in their own subjects (admins: any)."""
    if current_user.role == UserRole.ADMIN:
        return
    subject_id = db.query(Exam.subject_id).filter(Exam.id == exam_id).scalar()
    owns = (
        db.query(Subject.id)
        .filter(Subject.id == subject_id, Subject.teacher_id == current_user.id)
        .first()
    )
    if not owns:
        raise HTTPException(status_code=403, detail="Not authorized for this exam")


def _require_question_access(db: Session, question_id: int, current_user: User) -> None:
    exam_id = db.query(Question.exam_id).filter(Question.id == question_id).scalar()
    if exam_id is None:
        raise HTTPException(status_code=404, detail="Question not found")
    _require_exam_access(db, exam_id, current_user)


def _ai_verdict(probability: float) -> str:
    """Map an AI probability (0-1) to the configured verdict label."""
    if probability >= settings.AI_FLAG_THRESHOLD:
        return "AI Detected"
    if probability >= settings.AI_REVIEW_THRESHOLD:
        return "Uncertain"
    return "Likely Human"


def _require_answer_access(db: Session, answer_id: int, current_user: User) -> StudentAnswer:
    answer = db.query(StudentAnswer).filter(StudentAnswer.id == answer_id).first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    _require_question_access(db, answer.question_id, current_user)
    return answer


# ── Request Schemas ─────────────────────────────────────

class PlagiarismRequest(BaseModel):
    exam_id: int

class AIDetectionRequest(BaseModel):
    text: str

class AIAutoScanRequest(BaseModel):
    exam_id: int

class RubricGradeRequest(BaseModel):
    answer_id: int

class GenerateModelAnswerRequest(BaseModel):
    question_id: int

class ClassReportRequest(BaseModel):
    exam_id: int


# ── Plagiarism Check ────────────────────────────────────

@router.post("/plagiarism-check")
def check_plagiarism(req: PlagiarismRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_teacher)):
    """Check for plagiarism across student answers for an exam (teacher only)."""
    _require_exam_access(db, req.exam_id, current_user)
    questions = db.query(Question).filter(Question.exam_id == req.exam_id).all()
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found for this exam")

    from app.api.settings import get_setting
    threshold_pct = int(get_setting(db, "plagiarism") or "60")
    threshold = threshold_pct / 100.0

    all_results = []
    for q in questions:
        answers = db.query(StudentAnswer).filter(StudentAnswer.question_id == q.id).all()
        if len(answers) < 2:
            continue
        texts = [a.answer_text or "" for a in answers]
        try:
            from app.nlp.advanced.plagiarism_detector import PlagiarismDetector
            detector = PlagiarismDetector(threshold=threshold)
            result = detector.detect(texts)
            for pair in result.get("pairs", []):
                pair["question_id"] = q.id
                pair["question_text"] = q.question_text[:80]
                idx1 = pair["answer_idx_1"]
                idx2 = pair["answer_idx_2"]
                pair["student_1_id"] = answers[idx1].student_id if idx1 < len(answers) else None
                pair["student_2_id"] = answers[idx2].student_id if idx2 < len(answers) else None
            all_results.extend(result.get("pairs", []))
        except Exception:
            continue

    flagged = [r for r in all_results if r.get("flagged")]
    review = [r for r in all_results if r.get("semantic_review")]
    return {
        "pairs": all_results,
        "summary": {
            "total_pairs": len(all_results),
            "flagged_pairs": len(flagged),
            "review_pairs": len(review),
            "max_similarity": round(max([r.get("similarity", 0) for r in all_results], default=0), 4),
            "max_semantic_similarity": round(
                max([r.get("semantic_similarity") or 0 for r in all_results], default=0), 4
            ),
            "threshold": threshold,
            "semantic_enabled": any(r.get("semantic_similarity") is not None for r in all_results),
        },
    }


# ── AI Auto Scan ────────────────────────────────────────

@router.post("/ai-auto-scan")
def ai_auto_scan(req: AIAutoScanRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_teacher)):
    """Scan all student answers for an exam and return AI detection scores (teacher only)."""
    from collections import defaultdict

    _require_exam_access(db, req.exam_id, current_user)

    questions = db.query(Question).filter(Question.exam_id == req.exam_id).all()
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found for this exam")

    question_ids = [q.id for q in questions]
    answers = db.query(StudentAnswer).filter(StudentAnswer.question_id.in_(question_ids)).all()

    if not answers:
        return {"results": [], "summary": {"total": 0, "ai_detected": 0, "uncertain": 0, "human": 0}}

    student_ids = list({a.student_id for a in answers})
    students = db.query(User).filter(User.id.in_(student_ids)).all()
    student_names = {s.id: s.name for s in students}

    try:
        from app.nlp.advanced.ai_detector import AIDetector
        detector = AIDetector()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="AI Detector module not available") from exc

    student_answers = defaultdict(list)
    for a in answers:
        student_answers[a.student_id].append(a)

    results = []
    for sid, ans_list in student_answers.items():
        combined_text = " ".join([a.answer_text or "" for a in ans_list])
        if not combined_text.strip():
            continue
        try:
            detection = detector.detect(combined_text)
            ai_prob = detection.get("ai_probability", 0)
            results.append({
                "student_id": sid,
                "student_name": student_names.get(sid, f"Student #{sid}"),
                "ai_probability": round(ai_prob * 100, 1),
                "perplexity": round(detection.get("perplexity", 0), 2),
                "burstiness": round(detection.get("burstiness", 0) * 100, 1),
                "vocabulary_richness": round(detection.get("vocabulary_richness", 0) * 100, 1),
                "ai_phrases_found": detection.get("ai_phrases_found", []),
                "answer_count": len(ans_list),
                "verdict": _ai_verdict(ai_prob),
            })
        except Exception:
            continue

    results.sort(key=lambda x: x["ai_probability"], reverse=True)

    flag_pct = settings.AI_FLAG_THRESHOLD * 100
    review_pct = settings.AI_REVIEW_THRESHOLD * 100
    ai_count = sum(1 for r in results if r["ai_probability"] >= flag_pct)
    uncertain_count = sum(1 for r in results if review_pct <= r["ai_probability"] < flag_pct)
    human_count = sum(1 for r in results if r["ai_probability"] < review_pct)

    return {
        "results": results,
        "summary": {
            "total": len(results),
            "ai_detected": ai_count,
            "uncertain": uncertain_count,
            "human": human_count,
        }
    }


# ── AI Detection (Single Text) ─────────────────────────

@router.post("/ai-detection")
def detect_ai(req: AIDetectionRequest, current_user: User = Depends(get_current_teacher)):
    """Detect whether a piece of text is AI-generated (teacher only)."""
    try:
        from app.nlp.advanced.ai_detector import AIDetector
        detector = AIDetector()
        result = detector.detect(req.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ── Feedback Generation ────────────────────────────────

@router.get("/feedback/{answer_id}")
def get_feedback(answer_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_teacher)):
    """Generate AI feedback for a student answer (teacher only)."""
    answer = _require_answer_access(db, answer_id, current_user)
    question = db.query(Question).filter(Question.id == answer.question_id).first()
    score = db.query(Score).filter(Score.answer_id == answer_id).first()
    try:
        from app.nlp.advanced.feedback_generator import FeedbackGenerator
        gen = FeedbackGenerator()
        feedback = gen.generate(
            question=question.question_text if question else "",
            model_answer=question.model_answer if question else "",
            student_answer=answer.answer_text or "",
            score=score.total_score if score else 0
        )
        return {"feedback": feedback, "answer_id": answer_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ── Smart Grading Rubric ───────────────────────────────

@router.post("/rubric-grade")
def rubric_grade(req: RubricGradeRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_teacher)):
    """Grade a student answer using the 5-criteria rubric (teacher only)."""
    answer = _require_answer_access(db, req.answer_id, current_user)

    question = db.query(Question).filter(Question.id == answer.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    try:
        from app.nlp.advanced.rubric_grader import RubricGrader
        grader = RubricGrader()
        result = grader.grade(
            student_answer=answer.answer_text or "",
            model_answer=question.model_answer or "",
            question=question.question_text,
            total_marks=float(question.marks),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ── Auto Model Answer Generator ────────────────────────

@router.post("/generate-model-answer")
def generate_model_answer(req: GenerateModelAnswerRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_teacher)):
    """Generate an ideal model answer for a question (teacher only)."""
    _require_question_access(db, req.question_id, current_user)
    question = db.query(Question).filter(Question.id == req.question_id).first()

    exam = db.query(Exam).filter(Exam.id == question.exam_id).first()
    subject = None
    if exam:
        subject = db.query(Subject).filter(Subject.id == exam.subject_id).first()

    try:
        from app.nlp.advanced.model_answer_gen import ModelAnswerGenerator
        gen = ModelAnswerGenerator()
        result = gen.generate(
            question_text=question.question_text,
            subject_name=subject.name if subject else "",
            existing_model_answer=question.model_answer or "",
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ── Class Intelligence Report ──────────────────────────

@router.post("/class-report")
def class_report(req: ClassReportRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_teacher)):
    """Generate a class intelligence report for an exam (teacher only)."""
    _require_exam_access(db, req.exam_id, current_user)
    questions = db.query(Question).filter(Question.exam_id == req.exam_id).all()
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found for this exam")

    question_map = {q.id: q for q in questions}

    # Get all answers with scores
    question_ids = list(question_map.keys())
    answers = db.query(StudentAnswer).filter(StudentAnswer.question_id.in_(question_ids)).all()

    if not answers:
        return {"error": "No student answers found for this exam"}

    # Get student names
    student_ids = list({a.student_id for a in answers})
    students = db.query(User).filter(User.id.in_(student_ids)).all()
    student_names = {s.id: s.name for s in students}

    # Build exam data
    exam_data = []
    for a in answers:
        q = question_map.get(a.question_id)
        score_obj = db.query(Score).filter(Score.answer_id == a.id).first()
        exam_data.append({
            "student_id": a.student_id,
            "student_name": student_names.get(a.student_id, f"Student #{a.student_id}"),
            "question_id": a.question_id,
            "question_text": q.question_text if q else "",
            "answer_text": a.answer_text or "",
            "model_answer": q.model_answer if q else "",
            "score": score_obj.total_score if score_obj else 0,
            "total_marks": float(q.marks) if q else 10,
        })

    try:
        from app.nlp.advanced.class_intelligence import ClassIntelligence
        analyzer = ClassIntelligence()
        result = analyzer.analyze(exam_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
