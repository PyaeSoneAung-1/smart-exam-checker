"""Pytest fixtures for Smart Exam Answer Checker tests."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.user import User, UserRole
from app.models.subject import Subject
from app.models.exam import Exam
from app.models.question import Question
from app.core.security import get_password_hash, create_access_token


# In-memory SQLite for tests
SQLALCHEMY_TEST_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Provide a test database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """Provide a FastAPI test client with DB override."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_teacher(db):
    """Create and return a test teacher user."""
    user = User(
        name="Test Teacher",
        email="teacher@test.com",
        hashed_password=get_password_hash("teacher123"),
        role=UserRole.TEACHER,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_student(db):
    """Create and return a test student user."""
    user = User(
        name="Test Student",
        email="student@test.com",
        hashed_password=get_password_hash("student123"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_admin(db):
    """Create and return a test admin user."""
    user = User(
        name="Test Admin",
        email="admin@test.com",
        hashed_password=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def teacher_token(test_teacher):
    """JWT token for the test teacher."""
    return create_access_token({"sub": str(test_teacher.id), "role": "teacher"})


@pytest.fixture
def student_token(test_student):
    """JWT token for the test student."""
    return create_access_token({"sub": str(test_student.id), "role": "student"})


@pytest.fixture
def admin_token(test_admin):
    """JWT token for the test admin."""
    return create_access_token({"sub": str(test_admin.id), "role": "admin"})


@pytest.fixture
def auth_teacher_headers(teacher_token):
    """Authorization headers for the test teacher."""
    return {"Authorization": f"Bearer {teacher_token}"}


@pytest.fixture
def auth_student_headers(student_token):
    """Authorization headers for the test student."""
    return {"Authorization": f"Bearer {student_token}"}


@pytest.fixture
def auth_admin_headers(admin_token):
    """Authorization headers for the test admin."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def test_subject(db, test_teacher):
    """Create and return a test subject."""
    subject = Subject(
        name="Mathematics",
        description="Basic Mathematics",
        teacher_id=test_teacher.id,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@pytest.fixture
def test_exam(db, test_subject):
    """Create and return a test exam."""
    exam = Exam(
        subject_id=test_subject.id,
        title="Algebra Midterm",
        description="Midterm exam on algebra",
        total_marks=20.0,
        time_limit_minutes=60,
        is_active=True,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


@pytest.fixture
def test_question(db, test_exam):
    """Create and return a test question."""
    question = Question(
        exam_id=test_exam.id,
        question_text="Explain the concept of variables in algebra.",
        model_answer="Variables are symbols that represent unknown values in algebraic expressions. They allow us to write general formulas and equations.",
        marks=10.0,
        keywords=["variables", "symbols", "unknown", "algebraic", "expressions", "equations"],
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question
