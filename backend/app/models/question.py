from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    model_answer = Column(Text, nullable=False)
    marks = Column(Float, nullable=False, default=1.0)
    keywords = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    exam = relationship("Exam", back_populates="questions")
    answers = relationship("StudentAnswer", back_populates="question", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Question(id={self.id}, exam_id={self.exam_id})>"
