from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.database import get_db
from app.models.user import User, UserRole
from app.models.question import Question
from app.models.answer import StudentAnswer, Score
from app.models.exam import Exam
from app.models.subject import Subject
from app.schemas.answer import AnswerSubmit, AnswerResponse, ScoreResponse, ScoreOverride, ExamSubmission
from app.core.deps import get_current_user, get_current_student, get_current_teacher
from app.nlp.scorer import exam_scorer
from app.api.settings import get_scoring_weights
from app.utils.pagination import get_pagination_params, paginate_query, PaginationParams

router = APIRouter(prefix="/answers", tags=["Answers"])


def _score_answer(answer: StudentAnswer, question: Question, db: Session) -> Score:
    """Score a student answer using the NLP engine and save the score."""
    # Read current scoring weights from DB
    weights = get_scoring_weights(db)

    result = exam_scorer.score_answer(
        student_answer=answer.answer_text,
        model_answer=question.model_answer,
        total_marks=float(question.marks),
        weights=weights,
    )

    score = Score(
        answer_id=answer.id,
        keyword_score=round(result.keyword_score, 4),
        similarity_score=round(result.similarity_score, 4),
        grammar_score=round(result.grammar_score, 4),
        completeness_score=round(result.completeness_score, 4),
        total_score=result.total_score,
        feedback=result.feedback,
    )
    db.add(score)
    return score


@router.post("/submit", response_model=AnswerResponse, status_code=status.HTTP_201_CREATED)
def submit_answer(
    answer_data: AnswerSubmit,
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """Submit an answer to a single question and get it auto-graded."""
    question = db.query(Question).filter(Question.id == answer_data.question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    exam = db.query(Exam).filter(Exam.id == question.exam_id).first()
    if not exam or not exam.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam is not active")

    availability_error = exam.availability_error()
    if availability_error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=availability_error)

    existing = (
        db.query(StudentAnswer)
        .filter(
            StudentAnswer.question_id == answer_data.question_id,
            StudentAnswer.student_id == current_user.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have already submitted an answer for this question")

    answer = StudentAnswer(
        question_id=answer_data.question_id,
        student_id=current_user.id,
        answer_text=answer_data.answer_text,
    )
    db.add(answer)
    db.flush()

    score = _score_answer(answer, question, db)
    db.commit()
    db.refresh(answer)

    return AnswerResponse(
        id=answer.id,
        question_id=answer.question_id,
        student_id=answer.student_id,
        answer_text=answer.answer_text,
        submitted_at=answer.submitted_at,
        score=ScoreResponse.model_validate(score),
    )


@router.post("/submit-exam", response_model=List[AnswerResponse], status_code=status.HTTP_201_CREATED)
def submit_exam(
    submission: ExamSubmission,
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """Submit all answers for an exam at once."""
    if not submission.answers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No answers provided")

    responses = []
    for answer_data in submission.answers:
        question = db.query(Question).filter(Question.id == answer_data.question_id).first()
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Question {answer_data.question_id} not found")

        exam = db.query(Exam).filter(Exam.id == question.exam_id).first()
        if not exam or not exam.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Exam for question {answer_data.question_id} is not active")

        availability_error = exam.availability_error()
        if availability_error:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=availability_error)

        existing = (
            db.query(StudentAnswer)
            .filter(
                StudentAnswer.question_id == answer_data.question_id,
                StudentAnswer.student_id == current_user.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Already submitted answer for question {answer_data.question_id}")

        answer = StudentAnswer(
            question_id=answer_data.question_id,
            student_id=current_user.id,
            answer_text=answer_data.answer_text,
        )
        db.add(answer)
        db.flush()

        score = _score_answer(answer, question, db)
        responses.append((answer, score))

    db.commit()

    return [
        AnswerResponse(
            id=a.id,
            question_id=a.question_id,
            student_id=a.student_id,
            answer_text=a.answer_text,
            submitted_at=a.submitted_at,
            score=ScoreResponse.model_validate(s),
        )
        for a, s in responses
    ]


@router.get("/", response_model=dict)
def get_all_answers(
    exam_id: int = None,
    question_id: int = None,
    student_id: int = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all answers with optional filters. Teachers see only their subjects' answers."""
    query = db.query(StudentAnswer).options(
        joinedload(StudentAnswer.score),
        joinedload(StudentAnswer.student),
        joinedload(StudentAnswer.question),
    )

    # Filter by exam if provided
    if exam_id:
        question_ids = [q.id for q in db.query(Question).filter(Question.exam_id == exam_id).all()]
        query = query.filter(StudentAnswer.question_id.in_(question_ids))

    if question_id:
        query = query.filter(StudentAnswer.question_id == question_id)

    if student_id:
        query = query.filter(StudentAnswer.student_id == student_id)

    # Teachers can only see answers for their subjects' exams
    if current_user.role == UserRole.TEACHER:
        teacher_subject_ids = [s.id for s in db.query(Subject).filter(Subject.teacher_id == current_user.id).all()]
        if teacher_subject_ids:
            teacher_exam_ids = [e.id for e in db.query(Exam).filter(Exam.subject_id.in_(teacher_subject_ids)).all()]
            teacher_question_ids = [q.id for q in db.query(Question).filter(Question.exam_id.in_(teacher_exam_ids)).all()]
            query = query.filter(StudentAnswer.question_id.in_(teacher_question_ids))
        else:
            query = query.filter(StudentAnswer.id == -1)

    query = query.order_by(StudentAnswer.submitted_at.desc())
    result = paginate_query(query, db, pagination)
    result.items = [
        AnswerResponse(
            id=a.id,
            question_id=a.question_id,
            student_id=a.student_id,
            answer_text=a.answer_text,
            submitted_at=a.submitted_at,
            score=ScoreResponse.model_validate(a.score) if a.score else None,
        ).model_dump()
        for a in result.items
    ]
    return result.model_dump()


@router.get("/my-answers", response_model=dict)
def get_my_answers(
    exam_id: int = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """Get all answers submitted by the current student."""
    query = (
        db.query(StudentAnswer)
        .options(joinedload(StudentAnswer.score))
        .filter(StudentAnswer.student_id == current_user.id)
    )

    if exam_id:
        question_ids = [q.id for q in db.query(Question).filter(Question.exam_id == exam_id).all()]
        query = query.filter(StudentAnswer.question_id.in_(question_ids))

    query = query.order_by(StudentAnswer.submitted_at.desc())
    result = paginate_query(query, db, pagination)
    result.items = [
        AnswerResponse(
            id=a.id,
            question_id=a.question_id,
            student_id=a.student_id,
            answer_text=a.answer_text,
            submitted_at=a.submitted_at,
            score=ScoreResponse.model_validate(a.score) if a.score else None,
        ).model_dump()
        for a in result.items
    ]
    return result.model_dump()


@router.get("/question/{question_id}", response_model=dict)
def get_question_answers(
    question_id: int,
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Get all student answers for a specific question (teacher only)."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    query = (
        db.query(StudentAnswer)
        .options(joinedload(StudentAnswer.score), joinedload(StudentAnswer.student))
        .filter(StudentAnswer.question_id == question_id)
        .order_by(StudentAnswer.submitted_at.desc())
    )

    result = paginate_query(query, db, pagination)
    result.items = [
        AnswerResponse(
            id=a.id,
            question_id=a.question_id,
            student_id=a.student_id,
            answer_text=a.answer_text,
            submitted_at=a.submitted_at,
            score=ScoreResponse.model_validate(a.score) if a.score else None,
        ).model_dump()
        for a in result.items
    ]
    return result.model_dump()


@router.put("/score/{answer_id}/override", response_model=ScoreResponse)
def override_score(
    answer_id: int,
    override_data: ScoreOverride,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Override the auto-generated score for an answer (teacher only)."""
    answer = db.query(StudentAnswer).filter(StudentAnswer.id == answer_id).first()
    if not answer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")

    score = db.query(Score).filter(Score.answer_id == answer_id).first()
    if not score:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Score not found for this answer")

    score.total_score = override_data.total_score
    score.is_overridden = True
    score.overridden_by = current_user.id
    from datetime import datetime
    score.overridden_at = datetime.utcnow()

    if override_data.feedback:
        score.feedback = override_data.feedback

    db.commit()
    db.refresh(score)
    return score
