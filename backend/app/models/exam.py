from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    total_marks = Column(Float, nullable=False, default=0.0)
    time_limit_minutes = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    subject = relationship("Subject", back_populates="exams")
    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Exam(id={self.id}, title={self.title})>"
