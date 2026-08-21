from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AnswerSubmit(BaseModel):
    question_id: int
    answer_text: str = Field(..., min_length=1)


class ExamSubmission(BaseModel):
    answers: List[AnswerSubmit]


class AnswerResponse(BaseModel):
    id: int
    question_id: int
    student_id: int
    answer_text: str
    submitted_at: datetime
    score: Optional["ScoreResponse"] = None

    model_config = {"from_attributes": True}


class ScoreResponse(BaseModel):
    id: int
    answer_id: int
    keyword_score: float
    similarity_score: float
    grammar_score: float
    completeness_score: float
    total_score: float
    feedback: Optional[str]
    is_overridden: bool
    overridden_by: Optional[int]
    overridden_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ScoreOverride(BaseModel):
    total_score: float = Field(..., ge=0)
    feedback: Optional[str] = None


# Fix forward references
AnswerResponse.model_rebuild()
