from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User, UserRole
from app.models.subject import Subject
from app.models.exam import Exam
from app.models.question import Question
from app.models.answer import StudentAnswer, Score
from app.schemas.dashboard import StudentDashboard, TeacherDashboard, AdminDashboard, StatsResponse, RecentSubmissionResponse
from app.core.deps import get_current_user, get_current_student, get_current_teacher, get_current_admin

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/student", response_model=StudentDashboard)
def student_dashboard(
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """Get dashboard statistics for the current student.

    Stats are aggregated per EXAM (not per question/answer): "Exams Taken"
    counts distinct exams the student answered, and the score metrics are
    each exam's percentage (sum of that exam's question scores / exam marks).
    """
    # Aggregate this student's answers grouped by exam.
    rows = (
        db.query(
            Exam.id,
            Exam.title,
            Exam.total_marks,
            Subject.name,
            func.coalesce(func.sum(Score.total_score), 0.0),
            func.max(StudentAnswer.submitted_at),
        )
        .select_from(StudentAnswer)
        .join(Question, Question.id == StudentAnswer.question_id)
        .join(Exam, Exam.id == Question.exam_id)
        .join(Subject, Subject.id == Exam.subject_id)
        .outerjoin(Score, Score.answer_id == StudentAnswer.id)
        .filter(StudentAnswer.student_id == current_user.id)
        .group_by(Exam.id, Exam.title, Exam.total_marks, Subject.name)
        .all()
    )

    total_exams = len(rows)
    if total_exams == 0:
        return StudentDashboard(
            total_exams_taken=0,
            average_score=0.0,
            highest_score=0.0,
            lowest_score=0.0,
            recent_scores=[],
            subject_scores=[],
        )

    # Build per-exam percentage + subject aggregates.
    exam_entries = []
    subject_totals = {}
    subject_counts = {}
    for _exam_id, title, total_marks, subject_name, student_total, last_submitted in rows:
        pct = (float(student_total) / float(total_marks) * 100.0) if total_marks else 0.0
        exam_entries.append((title, subject_name, pct, last_submitted))
        subject_totals[subject_name] = subject_totals.get(subject_name, 0.0) + pct
        subject_counts[subject_name] = subject_counts.get(subject_name, 0) + 1

    percentages = [e[2] for e in exam_entries]

    recent_scores = [
        StatsResponse(label=title, value=round(pct, 2))
        for title, _subj, pct, _ts in sorted(
            exam_entries, key=lambda x: x[3] or datetime.min, reverse=True
        )[:10]
    ]

    subject_scores = [
        StatsResponse(label=name, value=round(subject_totals[name] / subject_counts[name], 2))
        for name in sorted(subject_totals.keys())
    ]

    return StudentDashboard(
        total_exams_taken=total_exams,
        average_score=round(sum(percentages) / total_exams, 2),
        highest_score=round(max(percentages), 2),
        lowest_score=round(min(percentages), 2),
        recent_scores=recent_scores,
        subject_scores=subject_scores,
    )


@router.get("/teacher", response_model=TeacherDashboard)
def teacher_dashboard(
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Get dashboard statistics for the current teacher."""
    # Count only teacher's subjects
    total_subjects = db.query(Subject).filter(Subject.teacher_id == current_user.id).count()

    # Count exams in teacher's subjects
    subject_ids = [s.id for s in db.query(Subject).filter(Subject.teacher_id == current_user.id).all()]
    total_exams = db.query(Exam).filter(Exam.subject_id.in_(subject_ids)).count() if subject_ids else 0

    # Count students who answered questions in teacher's exams
    total_students = 0
    if subject_ids:
        exam_ids = [e.id for e in db.query(Exam).filter(Exam.subject_id.in_(subject_ids)).all()]
        if exam_ids:
            question_ids = [q.id for q in db.query(Question).filter(Question.exam_id.in_(exam_ids)).all()]
            if question_ids:
                total_students = (
                    db.query(StudentAnswer.student_id)
                    .filter(StudentAnswer.question_id.in_(question_ids))
                    .distinct()
                    .count()
                )

    total_submissions = 0
    avg_score = 0.0
    subject_stats = []
    recent_submissions = []

    if subject_ids:
        exam_ids = [e.id for e in db.query(Exam).filter(Exam.subject_id.in_(subject_ids)).all()]
        if exam_ids:
            question_ids = [q.id for q in db.query(Question).filter(Question.exam_id.in_(exam_ids)).all()]
            if question_ids:
                total_submissions = (
                    db.query(StudentAnswer.student_id)
                    .filter(StudentAnswer.question_id.in_(question_ids))
                    .distinct()
                    .count()
                )

                # Average score
                avg_result = (
                    db.query(func.avg(Score.total_score))
                    .join(StudentAnswer)
                    .filter(StudentAnswer.question_id.in_(question_ids))
                    .scalar()
                )
                avg_score = round(float(avg_result), 2) if avg_result else 0.0

                # Per-subject stats
                subject_query = (
                    db.query(Subject.name, func.avg(Score.total_score).label("avg"))
                    .join(Exam, Exam.subject_id == Subject.id)
                    .join(Question, Question.exam_id == Exam.id)
                    .join(StudentAnswer, StudentAnswer.question_id == Question.id)
                    .join(Score, Score.answer_id == StudentAnswer.id)
                    .filter(Subject.teacher_id == current_user.id)
                    .group_by(Subject.name)
                    .all()
                )
                subject_stats = [
                    StatsResponse(label=name, value=round(float(avg), 2))
                    for name, avg in subject_query
                ]

                # Recent submissions - deduplicate by student, latest 5 unique
                recent = (
                    db.query(Score, StudentAnswer, User)
                    .join(StudentAnswer, Score.answer_id == StudentAnswer.id)
                    .join(User, User.id == StudentAnswer.student_id)
                    .filter(StudentAnswer.question_id.in_(question_ids))
                    .order_by(StudentAnswer.submitted_at.desc())
                    .all()
                )
                seen_students = set()
                recent_submissions = []
                for score, sa, user in recent:
                    if sa.student_id not in seen_students:
                        seen_students.add(sa.student_id)
                        recent_submissions.append(
                            RecentSubmissionResponse(
                                student_id=sa.student_id,
                                student_name=user.name if user else f"Student #{sa.student_id}",
                                question_id=sa.question_id,
                                total_score=score.total_score,
                            )
                        )
                    if len(recent_submissions) >= 5:
                        break

    return TeacherDashboard(
        total_subjects=total_subjects,
        total_exams_created=total_exams,
        total_students=total_students,
        total_submissions=total_submissions,
        average_class_score=avg_score,
        subject_stats=subject_stats,
        recent_submissions=recent_submissions,
    )


@router.get("/admin", response_model=AdminDashboard)
def admin_dashboard(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get system-wide dashboard statistics (admin only)."""
    total_users = db.query(User).count()
    total_students = db.query(User).filter(User.role == UserRole.STUDENT).count()
    total_teachers = db.query(User).filter(User.role == UserRole.TEACHER).count()
    total_subjects = db.query(Subject).count()
    total_exams = db.query(Exam).count()
    total_questions = db.query(Question).count()
    total_submissions = db.query(StudentAnswer).count()

    avg_result = db.query(
        func.avg(Score.total_score / Question.marks * 100)
    ).join(StudentAnswer, Score.answer_id == StudentAnswer.id
    ).join(Question, StudentAnswer.question_id == Question.id
    ).scalar()
    avg_score = round(float(avg_result), 1) if avg_result else 0.0

    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_registrations = db.query(User).filter(User.created_at >= week_ago).count()

    return AdminDashboard(
        total_users=total_users,
        total_students=total_students,
        total_teachers=total_teachers,
        total_subjects=total_subjects,
        total_exams=total_exams,
        total_questions=total_questions,
        total_submissions=total_submissions,
        average_system_score=avg_score,
        recent_registrations=recent_registrations,
    )
