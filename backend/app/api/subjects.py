from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User, UserRole
from app.models.subject import Subject
from app.models.exam import Exam
from app.models.question import Question
from app.models.answer import StudentAnswer, Score
from app.schemas.subject import SubjectCreate, SubjectUpdate, SubjectResponse
from app.core.deps import get_current_user, get_current_teacher, get_current_admin
from typing import Optional
from app.utils.pagination import get_pagination_params, paginate_query, PaginationParams

router = APIRouter(prefix="/subjects", tags=["Subjects"])


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_subject(
    subject_data: SubjectCreate,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Create a new subject (teacher/admin). Teacher becomes the owner automatically."""
    existing = db.query(Subject).filter(Subject.name == subject_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subject with this name already exists",
        )

    # Admin can assign any teacher; teacher always owns their own subject
    teacher_id = subject_data.teacher_id if (subject_data.teacher_id and current_user.role == UserRole.ADMIN) else current_user.id

    subject = Subject(
        name=subject_data.name,
        description=subject_data.description,
        teacher_id=teacher_id,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return _build_subject_response(subject, db)


@router.get("/", response_model=dict)
def list_subjects(
    search: str = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List subjects with stats. Teachers see own subjects; admin sees all; students see all active."""
    query = db.query(Subject)

    # Teacher: only see own subjects
    if current_user.role == UserRole.TEACHER:
        query = query.filter(Subject.teacher_id == current_user.id)

    if search:
        query = query.filter(Subject.name.ilike(f"%{search}%"))

    query = query.order_by(Subject.created_at.desc())
    result = paginate_query(query, db, pagination)
    result.items = [_build_subject_response(s, db) for s in result.items]
    return result.model_dump()


@router.get("/{subject_id}", response_model=dict)
def get_subject(
    subject_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific subject by ID with stats."""
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return _build_subject_response(subject, db)


@router.put("/{subject_id}", response_model=dict)
def update_subject(
    subject_id: int,
    subject_data: SubjectUpdate,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Update a subject. Teacher can update own subject; admin can update any."""
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    # Only the owning teacher or admin can update
    if subject.teacher_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this subject",
        )

    update_data = subject_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subject, field, value)

    db.commit()
    db.refresh(subject)
    return _build_subject_response(subject, db)


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(
    subject_id: int,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Delete a subject. Teacher can delete own subject; admin can delete any."""
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    if subject.teacher_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this subject",
        )

    db.delete(subject)
    db.commit()


def _build_subject_response(subject: Subject, db: Session) -> dict:
    """Build subject response with teacher_name, exam_count, total_students."""
    # Get teacher name
    teacher_name = subject.teacher.name if subject.teacher else None

    # Count exams
    exam_count = db.query(Exam).filter(Exam.subject_id == subject.id).count()

    # Count unique students who answered questions in this subject's exams
    exam_ids = [e.id for e in db.query(Exam).filter(Exam.subject_id == subject.id).all()]
    total_students = 0
    if exam_ids:
        question_ids = [q.id for q in db.query(Question).filter(Question.exam_id.in_(exam_ids)).all()]
        if question_ids:
            total_students = (
                db.query(StudentAnswer.student_id)
                .filter(StudentAnswer.question_id.in_(question_ids))
                .distinct()
                .count()
            )

    return {
        "id": subject.id,
        "name": subject.name,
        "description": subject.description,
        "teacher_id": subject.teacher_id,
        "teacher_name": teacher_name,
        "exam_count": exam_count,
        "total_students": total_students,
        "created_at": subject.created_at.isoformat() if subject.created_at else None,
    }
