"""Settings API — read/write app configuration stored in DB."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.settings import AppSetting
from app.models.answer import StudentAnswer, Score
from app.models.question import Question

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["Settings"])


class SettingResponse(BaseModel):
    key: str
    value: str


class SettingUpdate(BaseModel):
    value: str


class ThresholdsUpdate(BaseModel):
    plagiarism: Optional[int] = None
    low_score: Optional[int] = None
    pass_percentage: Optional[int] = None


class WeightsUpdate(BaseModel):
    keyword_weight: Optional[float] = None
    similarity_weight: Optional[float] = None
    grammar_weight: Optional[float] = None
    completeness_weight: Optional[float] = None


DEFAULTS = {
    "pass_percentage": "40",
    "plagiarism": "60",
    "low_score": "30",
    "keyword_weight": "30",
    "similarity_weight": "40",
    "grammar_weight": "15",
    "completeness_weight": "15",
}


def get_setting(db: Session, key: str) -> str:
    """Get a setting value, return default if not found."""
    setting = db.query(AppSetting).filter(AppSetting.key == key).first()
    if setting:
        return setting.value
    return DEFAULTS.get(key, "")


@router.get("")
def get_all_settings(db: Session = Depends(get_db)):
    """Get all settings with defaults."""
    result = {}
    for key, default in DEFAULTS.items():
        result[key] = get_setting(db, key)
    return result


@router.get("/{key}")
def get_setting_by_key(key: str, db: Session = Depends(get_db)):
    """Get a single setting value."""
    value = get_setting(db, key)
    if not value and key not in DEFAULTS:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    return {"key": key, "value": value}


# IMPORTANT: /weights must be defined BEFORE /{key} to avoid route conflict
@router.put("/weights")
def update_weights(
    body: WeightsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update scoring weights (admin only). Weights are percentages that should sum to 100."""
    if current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admin can update settings")

    updated = {}
    for field, value in body.model_dump(exclude_none=True).items():
        setting = db.query(AppSetting).filter(AppSetting.key == field).first()
        if setting:
            setting.value = str(value)
        else:
            setting = AppSetting(key=field, value=str(value))
            db.add(setting)
        updated[field] = str(value)
    db.commit()
    return updated


@router.put("/{key}")
def update_setting(
    key: str,
    body: SettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a setting (admin only)."""
    if current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admin can update settings")

    setting = db.query(AppSetting).filter(AppSetting.key == key).first()
    if setting:
        setting.value = body.value
    else:
        setting = AppSetting(key=key, value=body.value)
        db.add(setting)
    db.commit()
    return {"key": key, "value": body.value}


@router.put("")
def update_thresholds(
    body: ThresholdsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update multiple threshold settings at once (admin only)."""
    if current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admin can update settings")

    updated = {}
    for field, value in body.model_dump(exclude_none=True).items():
        setting = db.query(AppSetting).filter(AppSetting.key == field).first()
        if setting:
            setting.value = str(value)
        else:
            setting = AppSetting(key=field, value=str(value))
            db.add(setting)
        updated[field] = str(value)
    db.commit()
    return updated


def get_scoring_weights(db: Session) -> dict:
    """Read current scoring weights from DB, with defaults as fallback."""
    kw = float(get_setting(db, "keyword_weight") or DEFAULTS["keyword_weight"])
    sw = float(get_setting(db, "similarity_weight") or DEFAULTS["similarity_weight"])
    gw = float(get_setting(db, "grammar_weight") or DEFAULTS["grammar_weight"])
    cw = float(get_setting(db, "completeness_weight") or DEFAULTS["completeness_weight"])
    return {
        "keyword_weight": kw / 100.0,
        "similarity_weight": sw / 100.0,
        "grammar_weight": gw / 100.0,
        "completeness_weight": cw / 100.0,
    }


@router.post("/rescore")
def rescore_all_answers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-score ALL existing answers using current weights from DB (admin only).

    This re-runs the NLP scoring pipeline on every submitted answer,
    applying the current scoring weights. Use this after changing weights
    to update existing scores.
    """
    if current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admin can rescore answers")

    from app.nlp.scorer import exam_scorer

    # Get current weights from DB
    weights = get_scoring_weights(db)

    # Fetch all scores with their answers and questions
    scores = db.query(Score).all()
    if not scores:
        return {"rescored": 0, "message": "No answers to rescore"}

    rescored = 0
    errors = 0

    for score in scores:
        try:
            # Get the student answer
            answer = db.query(StudentAnswer).filter(StudentAnswer.id == score.answer_id).first()
            if not answer:
                errors += 1
                continue

            # Get the question for model answer and marks
            question = db.query(Question).filter(Question.id == answer.question_id).first()
            if not question:
                errors += 1
                continue

            # Re-score with current weights
            result = exam_scorer.score_answer(
                student_answer=answer.answer_text,
                model_answer=question.model_answer,
                total_marks=float(question.marks),
                weights=weights,
            )

            # Update the score record
            score.keyword_score = round(result.keyword_score, 4)
            score.similarity_score = round(result.similarity_score, 4)
            score.grammar_score = round(result.grammar_score, 4)
            score.completeness_score = round(result.completeness_score, 4)
            score.total_score = result.total_score
            score.feedback = result.feedback
            rescored += 1

        except Exception as e:
            logger.error(f"Error rescoring answer {score.answer_id}: {e}")
            errors += 1

    db.commit()

    return {
        "rescored": rescored,
        "errors": errors,
        "total": len(scores),
        "weights_used": {
            "keyword": f"{weights['keyword_weight'] * 100:.0f}%",
            "similarity": f"{weights['similarity_weight'] * 100:.0f}%",
            "grammar": f"{weights['grammar_weight'] * 100:.0f}%",
            "completeness": f"{weights['completeness_weight'] * 100:.0f}%",
        },
    }
