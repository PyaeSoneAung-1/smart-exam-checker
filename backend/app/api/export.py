import csv
import io
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.user import User, UserRole
from app.models.question import Question
from app.models.answer import StudentAnswer, Score
from app.models.exam import Exam
from app.models.subject import Subject
from app.core.deps import get_current_teacher

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/results/{exam_id}")
def export_results_csv(
    exam_id: int,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Export exam results as CSV file (teacher only)."""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    subject = db.query(Subject).filter(Subject.id == exam.subject_id).first()
    if subject.teacher_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to export results for this exam",
        )

    # Get all questions for this exam
    questions = db.query(Question).filter(Question.exam_id == exam_id).order_by(Question.id).all()
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No questions found for this exam",
        )

    question_ids = [q.id for q in questions]

    # Get all answers with scores
    answers = (
        db.query(StudentAnswer)
        .options(joinedload(StudentAnswer.score), joinedload(StudentAnswer.student))
        .filter(StudentAnswer.question_id.in_(question_ids))
        .all()
    )

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    header = ["Student ID", "Student Name", "Student Email"]
    for q in questions:
        header.extend([
            f"Q{q.id} Answer",
            f"Q{q.id} Score",
            f"Q{q.id} Keyword Score",
            f"Q{q.id} Similarity Score",
            f"Q{q.id} Grammar Score",
            f"Q{q.id} Completeness Score",
            f"Q{q.id} Feedback",
            f"Q{q.id} Overridden",
        ])
    header.extend(["Total Score", "Max Possible Score", "Percentage"])
    writer.writerow(header)

    # Group answers by student
    student_answers = {}
    for answer in answers:
        sid = answer.student_id
        if sid not in student_answers:
            student_answers[sid] = {"student": answer.student, "answers": {}}
        student_answers[sid]["answers"][answer.question_id] = answer

    # Data rows
    max_possible = sum(q.marks for q in questions)
    for student_id, data in student_answers.items():
        student = data["student"]
        row = [student_id, student.name, student.email]

        total_score = 0.0
        for q in questions:
            answer = data["answers"].get(q.id)
            if answer:
                row.append(answer.answer_text[:100])  # Truncate for CSV
                if answer.score:
                    row.append(answer.score.total_score)
                    row.append(answer.score.keyword_score)
                    row.append(answer.score.similarity_score)
                    row.append(answer.score.grammar_score)
                    row.append(answer.score.completeness_score)
                    row.append(answer.score.feedback or "")
                    row.append("Yes" if answer.score.is_overridden else "No")
                    total_score += answer.score.total_score
                else:
                    row.extend(["N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"])
            else:
                row.extend(["Not Submitted", 0, 0, 0, 0, 0, "", "N/A"])

        row.append(round(total_score, 2))
        row.append(max_possible)
        percentage = round((total_score / max_possible * 100), 2) if max_possible > 0 else 0
        row.append(f"{percentage}%")

        writer.writerow(row)

    output.seek(0)

    filename = f"exam_{exam_id}_results.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
