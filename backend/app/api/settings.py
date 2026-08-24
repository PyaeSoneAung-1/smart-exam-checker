"""Settings API — read/write app configuration stored in DB."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
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

    Weights only change how the four component scores are combined into the
    total — the component scores (keyword / similarity / grammar / completeness)
    do NOT depend on the weights. So instead of re-running the full NLP
    pipeline (grammar check, vector similarity, spaCy parsing — the slow part),
    we recompute the weighted total directly from the stored components.
    This makes rescoring near-instant no matter how many answers exist.
    """
    if current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admin can rescore answers")

    from app.nlp.scorer import exam_scorer

    # Get current weights from DB (each 0.0–1.0)
    weights = get_scoring_weights(db)
    kw_w = weights["keyword_weight"]
    sw_w = weights["similarity_weight"]
    gw_w = weights["grammar_weight"]
    cw_w = weights["completeness_weight"]

    # Fetch all scores with their answers and questions (single query, no N+1)
    scores = (
        db.query(Score)
        .options(joinedload(Score.answer).joinedload(StudentAnswer.question))
        .all()
    )
    if not scores:
        return {"rescored": 0, "errors": 0, "total": 0, "weights_used": {}}

    # Keyword extraction depends only on the model answer — extract once per
    # question and reuse for every student answer to that question.
    keyword_cache: dict = {}
    keyword_extractor = exam_scorer.keyword_extractor

    rescored = 0
    errors = 0

    for score in scores:
        try:
            answer = score.answer
            question = answer.question if answer else None
            if not answer or not question:
                errors += 1
                continue

            k = score.keyword_score or 0.0
            s = score.similarity_score or 0.0
            g = score.grammar_score or 0.0
            c = score.completeness_score or 0.0
            marks = float(question.marks)

            weighted = k * kw_w + s * sw_w + g * gw_w + c * cw_w
            total = round(weighted * marks, 2)

            # Keep the original scorer's zero-out rules
            if k < 0.15 and s < 0.15:
                total = 0.0
            elif len(answer.answer_text.strip().split()) < 5 and k < 0.2:
                total = 0.0

            # Fast feedback regeneration: assessment band from the new total,
            # missing key terms from the cached per-question extraction, and
            # similarity / completeness statements from stored components.
            if question.id not in keyword_cache:
                keyword_cache[question.id] = keyword_extractor.extract_from_model_answer(
                    question.model_answer
                )
            model_keywords = keyword_cache[question.id]
            if model_keywords:
                missing = keyword_extractor.check_keywords_in_answer(
                    model_keywords, answer.answer_text
                )["missing"]
            else:
                missing = []

            score.total_score = total
            score.feedback = exam_scorer.generate_feedback(
                keyword_result={"missing": missing},
                similarity_result={"score": s},
                grammar_result={"error_count": 0, "suggestions": []},
                completeness_score=c,
                total_score=total,
                total_marks=marks,
            )
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
