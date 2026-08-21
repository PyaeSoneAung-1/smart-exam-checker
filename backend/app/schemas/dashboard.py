from pydantic import BaseModel
from typing import List, Optional


class StatsResponse(BaseModel):
    label: str
    value: float


class RecentSubmissionResponse(BaseModel):
    student_id: int
    student_name: str
    question_id: int
    total_score: float


class StudentDashboard(BaseModel):
    total_exams_taken: int
    average_score: float
    highest_score: float
    lowest_score: float
    recent_scores: List[StatsResponse] = []
    subject_scores: List[StatsResponse] = []


class TeacherDashboard(BaseModel):
    total_subjects: int
    total_exams_created: int
    total_students: int
    total_submissions: int
    average_class_score: float
    subject_stats: List[StatsResponse] = []
    recent_submissions: List[RecentSubmissionResponse] = []


class AdminDashboard(BaseModel):
    total_users: int
    total_students: int
    total_teachers: int
    total_subjects: int
    total_exams: int
    total_questions: int
    total_submissions: int
    average_system_score: float
    recent_registrations: int
