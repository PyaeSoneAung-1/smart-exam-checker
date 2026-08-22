from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional
from app.database import Base


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    total_marks = Column(Float, nullable=False, default=0.0)
    time_limit_minutes = Column(Integer, nullable=True)
    # Availability window: students may only take the exam between these
    # datetimes (naive UTC, matching the rest of the app). Null = no bound.
    available_from = Column(DateTime, nullable=True)
    available_until = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    subject = relationship("Subject", back_populates="exams")
    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan")

    def availability_error(self, now: Optional[datetime] = None) -> Optional[str]:
        """Return a human-readable message if the exam is outside its
        availability window at the given time (defaults to now), else None."""
        now = now or datetime.utcnow()
        if self.available_from and now < self.available_from:
            return (
                "This exam opens on "
                f"{self.available_from.strftime('%Y-%m-%d %H:%M')}."
            )
        if self.available_until and now > self.available_until:
            return (
                "This exam closed on "
                f"{self.available_until.strftime('%Y-%m-%d %H:%M')}."
            )
        return None

    def is_open(self, now: Optional[datetime] = None) -> bool:
        """True when the exam is inside its availability window."""
        return self.availability_error(now) is None

    def __repr__(self):
        return f"<Exam(id={self.id}, title={self.title})>"
