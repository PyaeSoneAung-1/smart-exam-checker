from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time import utcnow


class StudentAnswer(Base):
    __tablename__ = "student_answers"
    # One answer per student per question — enforced by the database so
    # concurrent submissions can never create duplicates.
    __table_args__ = (
        UniqueConstraint("question_id", "student_id", name="uq_answer_question_student"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    answer_text = Column(Text, nullable=False)
    submitted_at = Column(DateTime, default=utcnow, nullable=False)

    question = relationship("Question", back_populates="answers")
    student = relationship("User", foreign_keys=[student_id])
    score = relationship("Score", back_populates="answer", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<StudentAnswer(id={self.id}, student_id={self.student_id})>"


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    answer_id = Column(Integer, ForeignKey("student_answers.id", ondelete="CASCADE"), nullable=False, unique=True)
    keyword_score = Column(Float, nullable=False, default=0.0)
    similarity_score = Column(Float, nullable=False, default=0.0)
    grammar_score = Column(Float, nullable=False, default=0.0)
    completeness_score = Column(Float, nullable=False, default=0.0)
    total_score = Column(Float, nullable=False, default=0.0)
    feedback = Column(Text, nullable=True)
    is_overridden = Column(Boolean, default=False, nullable=False)
    overridden_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    overridden_at = Column(DateTime, nullable=True)

    answer = relationship("StudentAnswer", back_populates="score")
    overrider = relationship("User", foreign_keys=[overridden_by])

    def __repr__(self):
        return f"<Score(id={self.id}, total={self.total_score})>"
