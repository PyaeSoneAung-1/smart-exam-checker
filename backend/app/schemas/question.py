from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class QuestionCreate(BaseModel):
    exam_id: int
    question_text: str = Field(..., min_length=5)
    model_answer: str = Field(..., min_length=5)
    marks: float = Field(..., gt=0)
    keywords: Optional[List[str]] = []


class QuestionUpdate(BaseModel):
    question_text: Optional[str] = Field(None, min_length=5)
    model_answer: Optional[str] = Field(None, min_length=5)
    marks: Optional[float] = Field(None, gt=0)
    keywords: Optional[List[str]] = None


class QuestionResponse(BaseModel):
    id: int
    exam_id: int
    question_text: str
    model_answer: str
    marks: float
    keywords: Optional[List[str]]
    created_at: datetime

    model_config = {"from_attributes": True}
