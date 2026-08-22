import csv
import io
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.user import User, UserRole
from app.models.question import Question
from app.models.answer import StudentAnswer
from app.models.exam import Exam
from app.models.subject import Subject
from app.core.deps import get_current_teacher
from app.export_service import generate_excel_export

router = APIRouter(prefix="/export", tags=["Export"])

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _collect_results(exam_id: int, db: Session):
    """Load an exam's questions and per-student answers (with scores).

    Returns (exam, questions, student_rows, max_possible) where student_rows is a
    list of dicts: {"student_id", "name", "email", "answers": {question_id: answer},
    "total_score": float}.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    questions = (
        db.query(Question)
        .filter(Question.exam_id == exam_id)
        .order_by(Question.id)
        .all()
    )
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No questions found for this exam",
        )

    question_ids = [q.id for q in questions]

    answers = (
        db.query(StudentAnswer)
        .options(joinedload(StudentAnswer.score), joinedload(StudentAnswer.student))
        .filter(StudentAnswer.question_id.in_(question_ids))
        .all()
    )

    # Group answers by student
    student_map = {}
    for answer in answers:
        sid = answer.student_id
        if sid not in student_map:
            student_map[sid] = {
                "student_id": sid,
                "name": answer.student.name if answer.student else "Unknown",
                "email": answer.student.email if answer.student else "",
                "answers": {},
                "total_score": 0.0,
            }
        student_map[sid]["answers"][answer.question_id] = answer
        if answer.score:
            student_map[sid]["total_score"] += answer.score.total_score

    student_rows = [
        {
            "student_id": data["student_id"],
            "name": data["name"],
            "email": data["email"],
            "answers": data["answers"],
            "total_score": round(data["total_score"], 2),
        }
        for data in student_map.values()
    ]
    max_possible = sum(q.marks for q in questions)

    return exam, questions, student_rows, max_possible


def _authorize_teacher(exam: Exam, current_user: User, db: Session) -> None:
    """Ensure the current teacher owns the exam's subject (or is admin)."""
    subject = db.query(Subject).filter(Subject.id == exam.subject_id).first()
    if subject.teacher_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to export results for this exam",
        )


def _detail_headers(questions: List[Question]) -> List[str]:
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
    return header


def _detail_rows(questions: List[Question], student_rows: List[dict], max_possible: float) -> List[List]:
    rows = []
    for data in student_rows:
        row = [data["student_id"], data["name"], data["email"]]
        for q in questions:
            answer = data["answers"].get(q.id)
            if answer:
                row.append(answer.answer_text[:100])  # Truncate for spreadsheet cells
                if answer.score:
                    row.append(answer.score.total_score)
                    row.append(answer.score.keyword_score)
                    row.append(answer.score.similarity_score)
                    row.append(answer.score.grammar_score)
                    row.append(answer.score.completeness_score)
                    row.append(answer.score.feedback or "")
                    row.append("Yes" if answer.score.is_overridden else "No")
                else:
                    row.extend(["N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"])
            else:
                row.extend(["Not Submitted", 0, 0, 0, 0, 0, "", "N/A"])
        row.append(data["total_score"])
        row.append(max_possible)
        percentage = round((data["total_score"] / max_possible * 100), 2) if max_possible > 0 else 0
        row.append(f"{percentage}%")
        rows.append(row)
    return rows


@router.get("/results/{exam_id}")
def export_results_csv(
    exam_id: int,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Export exam results as CSV file (teacher only)."""
    exam, questions, student_rows, max_possible = _collect_results(exam_id, db)
    _authorize_teacher(exam, current_user, db)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(_detail_headers(questions))
    for row in _detail_rows(questions, student_rows, max_possible):
        writer.writerow(row)

    output.seek(0)

    filename = f"exam_{exam_id}_results.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/results/{exam_id}/xlsx")
def export_results_xlsx(
    exam_id: int,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Export exam results as a real Excel (.xlsx) workbook (teacher only).

    Contains a "Summary" sheet (per-student totals) and a "Detailed Results"
    sheet (per-question breakdown) — Unicode-safe, so Burmese text exports
    cleanly.
    """
    exam, questions, student_rows, max_possible = _collect_results(exam_id, db)
    _authorize_teacher(exam, current_user, db)

    summary_headers = ["Student ID", "Student Name", "Student Email", "Total Score", "Max Possible Score", "Percentage"]
    summary_rows = [
        [
            data["student_id"],
            data["name"],
            data["email"],
            data["total_score"],
            max_possible,
            f"{round((data['total_score'] / max_possible * 100), 2) if max_possible > 0 else 0}%",
        ]
        for data in student_rows
    ]

    content = generate_excel_export(
        summary_headers=summary_headers,
        summary_rows=summary_rows,
        detail_headers=_detail_headers(questions),
        detail_rows=_detail_rows(questions, student_rows, max_possible),
        exam_title=exam.title,
    )

    filename = f"exam_{exam_id}_results.xlsx"
    return StreamingResponse(
        iter([content]),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
