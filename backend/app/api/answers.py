from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.settings import get_scoring_weights
from app.core.deps import get_current_student, get_current_teacher, get_current_user
from app.database import get_db
from app.models.answer import Score, StudentAnswer
from app.models.exam import Exam
from app.models.question import Question
from app.models.subject import Subject
from app.models.user import User, UserRole
from app.nlp.scorer import exam_scorer
from app.schemas.answer import (
    AnswerResponse,
    AnswerSubmit,
    ExamSubmission,
    ScoreOverride,
    ScoreResponse,
)
from app.utils.pagination import PaginationParams, get_pagination_params, paginate_query
from app.utils.time import utcnow
from app.websocket import manager

router = APIRouter(prefix="/answers", tags=["Answers"])


def _score_answer(answer: StudentAnswer, question: Question, db: Session) -> Score:
    """Score a student answer using the NLP engine and save the score."""
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


def _load_submittable_question(db: Session, question_id: int) -> Question:
    """Return the question if it can currently be answered, else raise."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    exam = db.query(Exam).filter(Exam.id == question.exam_id).first()
    if not exam or not exam.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam is not active")

    availability_error = exam.availability_error()
    if availability_error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=availability_error)

    return question


def _existing_answer(db: Session, question_id: int, student_id: int) -> Optional[StudentAnswer]:
    return (
        db.query(StudentAnswer)
        .filter(
            StudentAnswer.question_id == question_id,
            StudentAnswer.student_id == student_id,
        )
        .first()
    )


def _answer_response(answer: StudentAnswer) -> AnswerResponse:
    return AnswerResponse(
        id=answer.id,
        question_id=answer.question_id,
        student_id=answer.student_id,
        answer_text=answer.answer_text,
        submitted_at=answer.submitted_at,
        score=ScoreResponse.model_validate(answer.score) if answer.score else None,
    )


@router.post("/submit", response_model=AnswerResponse, status_code=status.HTTP_201_CREATED)
def submit_answer(
    answer_data: AnswerSubmit,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """Submit an answer to a single question and get it auto-graded."""
    question = _load_submittable_question(db, answer_data.question_id)

    if _existing_answer(db, question.id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted an answer for this question",
        )

    answer = StudentAnswer(
        question_id=question.id,
        student_id=current_user.id,
        answer_text=answer_data.answer_text,
    )
    db.add(answer)
    db.flush()

    score = _score_answer(answer, question, db)

    try:
        db.commit()
    except IntegrityError:
        # The unique constraint won the race against a concurrent submission.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted an answer for this question",
        ) from None

    db.refresh(answer)

    background_tasks.add_task(
        manager.notify_grade_ready,
        current_user.id,
        question.exam_id,
        score.total_score,
        float(question.marks),
    )

    return _answer_response(answer)


@router.post("/submit-exam", response_model=List[AnswerResponse], status_code=status.HTTP_201_CREATED)
def submit_exam(
    submission: ExamSubmission,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """Submit a whole exam at once — all answers are validated first, graded,
    and saved in a single transaction."""
    if not submission.answers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No answers provided")

    seen: set = set()
    questions = []
    for answer_data in submission.answers:
        if answer_data.question_id in seen:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate answer for question {answer_data.question_id}",
            )
        seen.add(answer_data.question_id)

        question = _load_submittable_question(db, answer_data.question_id)
        if _existing_answer(db, question.id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Already submitted answer for question {question.id}",
            )
        questions.append((question, answer_data.answer_text))

    responses = []
    scored: list = []
    for question, answer_text in questions:
        answer = StudentAnswer(
            question_id=question.id,
            student_id=current_user.id,
            answer_text=answer_text,
        )
        db.add(answer)
        db.flush()
        score = _score_answer(answer, question, db)
        responses.append(answer)
        scored.append((answer, score, question))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="One of these questions already has an answer from you",
        ) from None

    for answer, _, _ in scored:
        db.refresh(answer)

    exam_id = questions[0][0].exam_id if questions else None
    if exam_id is not None:
        background_tasks.add_task(
            manager.notify_batch_graded,
            current_user.id,
            exam_id,
            [
                {"question_id": q.id, "score": s.total_score, "marks": float(q.marks)}
                for _, s, q in scored
            ],
        )

    return [_answer_response(a) for a in responses]


@router.get("/", response_model=dict)
def get_all_answers(
    exam_id: int = None,
    question_id: int = None,
    student_id: int = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List answers with optional filters.

    Students only ever see their own answers; teachers only see answers from
    exams in the subjects they teach; admins see everything.
    """
    query = db.query(StudentAnswer).options(
        joinedload(StudentAnswer.score),
        joinedload(StudentAnswer.student),
        joinedload(StudentAnswer.question),
    )

    if current_user.role == UserRole.STUDENT:
        query = query.filter(StudentAnswer.student_id == current_user.id)
    elif student_id:
        query = query.filter(StudentAnswer.student_id == student_id)

    if exam_id:
        question_ids = [q.id for q in db.query(Question).filter(Question.exam_id == exam_id).all()]
        query = query.filter(StudentAnswer.question_id.in_(question_ids))

    if question_id:
        query = query.filter(StudentAnswer.question_id == question_id)

    # Teachers can only see answers for their subjects' exams
    if current_user.role == UserRole.TEACHER:
        teacher_subject_ids = [
            s.id for s in db.query(Subject).filter(Subject.teacher_id == current_user.id).all()
        ]
        if teacher_subject_ids:
            teacher_exam_ids = [
                e.id for e in db.query(Exam).filter(Exam.subject_id.in_(teacher_subject_ids)).all()
            ]
            teacher_question_ids = [
                q.id for q in db.query(Question).filter(Question.exam_id.in_(teacher_exam_ids)).all()
            ]
            query = query.filter(StudentAnswer.question_id.in_(teacher_question_ids))
        else:
            query = query.filter(StudentAnswer.id == -1)

    query = query.order_by(StudentAnswer.submitted_at.desc())
    result = paginate_query(query, db, pagination)
    result.items = [_answer_response(a).model_dump() for a in result.items]
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
    result.items = [_answer_response(a).model_dump() for a in result.items]
    return result.model_dump()


def _require_teacher_owns_question(question_id: int, current_user: User, db: Session) -> None:
    """Teachers may only touch answers from their own subjects."""
    if current_user.role == UserRole.ADMIN:
        return
    subject_id = (
        db.query(Exam.subject_id)
        .join(Question, Question.exam_id == Exam.id)
        .filter(Question.id == question_id)
        .scalar()
    )
    owns = (
        db.query(Subject.id)
        .filter(Subject.id == subject_id, Subject.teacher_id == current_user.id)
        .first()
    )
    if not owns:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access answers for this exam",
        )


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

    _require_teacher_owns_question(question.id, current_user, db)

    query = (
        db.query(StudentAnswer)
        .options(joinedload(StudentAnswer.score), joinedload(StudentAnswer.student))
        .filter(StudentAnswer.question_id == question_id)
        .order_by(StudentAnswer.submitted_at.desc())
    )

    result = paginate_query(query, db, pagination)
    result.items = [_answer_response(a).model_dump() for a in result.items]
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

    _require_teacher_owns_question(answer.question_id, current_user, db)

    score = db.query(Score).filter(Score.answer_id == answer_id).first()
    if not score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score not found for this answer"
        )

    score.total_score = override_data.total_score
    score.is_overridden = True
    score.overridden_by = current_user.id
    score.overridden_at = utcnow()

    if override_data.feedback:
        score.feedback = override_data.feedback

    db.commit()
    db.refresh(score)
    return score
