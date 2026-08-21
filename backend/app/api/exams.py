from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.user import User, UserRole
from app.models.subject import Subject
from app.models.exam import Exam
from app.schemas.exam import ExamCreate, ExamUpdate, ExamResponse, ExamDetailResponse, QuestionBrief
from app.core.deps import get_current_user, get_current_teacher, get_current_student
from app.utils.pagination import get_pagination_params, paginate_query, PaginationParams

router = APIRouter(prefix="/exams", tags=["Exams"])


@router.post("/", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(
    exam_data: ExamCreate,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Create a new exam (teacher/admin only)."""
    # Verify subject exists and user has access
    subject = db.query(Subject).filter(Subject.id == exam_data.subject_id).first()
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    if subject.teacher_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create exams for this subject",
        )

    exam = Exam(
        subject_id=exam_data.subject_id,
        title=exam_data.title,
        description=exam_data.description,
        total_marks=exam_data.total_marks,
        time_limit_minutes=exam_data.time_limit_minutes,
        is_active=exam_data.is_active,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


@router.get("/", response_model=dict)
def list_exams(
    subject_id: int = None,
    is_active: bool = None,
    search: str = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List exams. Students see only active exams; teachers see their own."""
    query = db.query(Exam).options(joinedload(Exam.subject))

    # Teacher: only see exams for their own subjects
    if current_user.role == UserRole.TEACHER:
        teacher_subject_ids = [s.id for s in db.query(Subject).filter(Subject.teacher_id == current_user.id).all()]
        if teacher_subject_ids:
            query = query.filter(Exam.subject_id.in_(teacher_subject_ids))
        else:
            # Teacher has no subjects - return empty
            query = query.filter(Exam.id == -1)

    if subject_id:
        query = query.filter(Exam.subject_id == subject_id)

    if is_active is not None:
        query = query.filter(Exam.is_active == is_active)
    elif current_user.role == UserRole.STUDENT:
        query = query.filter(Exam.is_active == True)

    if search:
        query = query.filter(Exam.title.ilike(f"%{search}%"))

    query = query.order_by(Exam.created_at.desc())
    result = paginate_query(query, db, pagination)
    # Include subject info in response
    items = []
    for e in result.items:
        item = ExamResponse.model_validate(e).model_dump()
        if e.subject:
            item["subject"] = {
                "id": e.subject.id,
                "name": e.subject.name,
                "teacher_id": e.subject.teacher_id,
            }
        items.append(item)
    result.items = items
    return result.model_dump()


@router.get("/{exam_id}", response_model=ExamDetailResponse)
def get_exam(
    exam_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get exam details with questions."""
    exam = (
        db.query(Exam)
        .options(joinedload(Exam.questions))
        .filter(Exam.id == exam_id)
        .first()
    )
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    if current_user.role == UserRole.STUDENT and not exam.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This exam is not currently active",
        )

    return ExamDetailResponse(
        id=exam.id,
        subject_id=exam.subject_id,
        title=exam.title,
        description=exam.description,
        total_marks=exam.total_marks,
        time_limit_minutes=exam.time_limit_minutes,
        is_active=exam.is_active,
        created_at=exam.created_at,
        questions=[
            QuestionBrief(id=q.id, question_text=q.question_text, marks=q.marks)
            for q in exam.questions
        ],
    )


@router.put("/{exam_id}", response_model=ExamResponse)
def update_exam(
    exam_id: int,
    exam_data: ExamUpdate,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Update an exam (teacher who owns the subject or admin)."""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    subject = db.query(Subject).filter(Subject.id == exam.subject_id).first()
    if subject.teacher_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this exam",
        )

    update_data = exam_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(exam, field, value)

    db.commit()
    db.refresh(exam)
    return exam


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(
    exam_id: int,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Delete an exam."""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    subject = db.query(Subject).filter(Subject.id == exam.subject_id).first()
    if subject.teacher_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this exam",
        )

    db.delete(exam)
    db.commit()
