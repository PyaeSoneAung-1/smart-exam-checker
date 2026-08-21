from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.exam import Exam
from app.models.subject import Subject
from app.models.question import Question
from app.schemas.question import QuestionCreate, QuestionUpdate, QuestionResponse
from app.core.deps import get_current_user, get_current_teacher
from app.utils.pagination import get_pagination_params, paginate_query, PaginationParams

router = APIRouter(prefix="/questions", tags=["Questions"])


@router.post("/", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
def create_question(
    question_data: QuestionCreate,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Create a new question with model answer and keywords (teacher/admin only)."""
    exam = db.query(Exam).filter(Exam.id == question_data.exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    subject = db.query(Subject).filter(Subject.id == exam.subject_id).first()
    if subject.teacher_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add questions to this exam",
        )

    question = Question(
        exam_id=question_data.exam_id,
        question_text=question_data.question_text,
        model_answer=question_data.model_answer,
        marks=question_data.marks,
        keywords=question_data.keywords or [],
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.get("/", response_model=dict)
def list_questions(
    exam_id: int = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List questions. Students only see questions from active exams; teachers see own; admin sees all."""
    query = db.query(Question)

    if exam_id:
        query = query.filter(Question.exam_id == exam_id)

    # Student: only see questions from active exams
    if current_user.role == UserRole.STUDENT:
        active_exam_ids = [e.id for e in db.query(Exam).filter(Exam.is_active == True).all()]
        if active_exam_ids:
            query = query.filter(Question.exam_id.in_(active_exam_ids))
        else:
            query = query.filter(Question.id == -1)  # no active exams → empty

    # Teacher: only see questions from own subjects' exams
    elif current_user.role == UserRole.TEACHER:
        teacher_subject_ids = [s.id for s in db.query(Subject).filter(Subject.teacher_id == current_user.id).all()]
        if teacher_subject_ids:
            teacher_exam_ids = [e.id for e in db.query(Exam).filter(Exam.subject_id.in_(teacher_subject_ids)).all()]
            if teacher_exam_ids:
                query = query.filter(Question.exam_id.in_(teacher_exam_ids))
            else:
                query = query.filter(Question.id == -1)
        else:
            query = query.filter(Question.id == -1)

    query = query.order_by(Question.created_at.desc())
    result = paginate_query(query, db, pagination)
    result.items = [QuestionResponse.model_validate(q).model_dump() for q in result.items]
    return result.model_dump()


@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific question. Students can only see questions from active exams."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    # Student: only active exam questions
    if current_user.role == UserRole.STUDENT:
        exam = db.query(Exam).filter(Exam.id == question.exam_id).first()
        if not exam or not exam.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    return question


@router.put("/{question_id}", response_model=QuestionResponse)
def update_question(
    question_id: int,
    question_data: QuestionUpdate,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Update a question (teacher who owns the subject or admin)."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    exam = db.query(Exam).filter(Exam.id == question.exam_id).first()
    subject = db.query(Subject).filter(Subject.id == exam.subject_id).first()

    if subject.teacher_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this question",
        )

    update_data = question_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(question, field, value)

    db.commit()
    db.refresh(question)
    return question


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    question_id: int,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Delete a question."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    exam = db.query(Exam).filter(Exam.id == question.exam_id).first()
    subject = db.query(Subject).filter(Subject.id == exam.subject_id).first()

    if subject.teacher_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this question",
        )

    db.delete(question)
    db.commit()
