"""Tests for answer submission endpoints."""
import pytest


class TestSubmitAnswer:
    """POST /api/answers/submit"""

    def test_submit_answer_success(self, client, auth_student_headers, test_question, test_exam):
        resp = client.post("/api/answers/submit", json={
            "question_id": test_question.id,
            "answer_text": "Variables are symbols that represent unknown values in algebraic expressions and equations.",
        }, headers=auth_student_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["question_id"] == test_question.id
        assert data["student_id"] is not None
        assert data["score"] is not None
        assert data["score"]["total_score"] >= 0
        assert "keyword_score" in data["score"]
        assert "similarity_score" in data["score"]
        assert "feedback" in data["score"]

    def test_submit_answer_no_auth(self, client, test_question):
        resp = client.post("/api/answers/submit", json={
            "question_id": test_question.id,
            "answer_text": "Some answer",
        })
        assert resp.status_code == 401

    def test_submit_answer_question_not_found(self, client, auth_student_headers):
        resp = client.post("/api/answers/submit", json={
            "question_id": 9999,
            "answer_text": "Some answer for nonexistent question",
        }, headers=auth_student_headers)
        assert resp.status_code == 404

    def test_submit_answer_duplicate(self, client, auth_student_headers, test_question):
        # First submission
        client.post("/api/answers/submit", json={
            "question_id": test_question.id,
            "answer_text": "First answer about variables in algebra",
        }, headers=auth_student_headers)
        # Duplicate
        resp = client.post("/api/answers/submit", json={
            "question_id": test_question.id,
            "answer_text": "Second attempt",
        }, headers=auth_student_headers)
        assert resp.status_code == 400
        assert "already submitted" in resp.json()["detail"].lower()

    def test_submit_answer_empty_text(self, client, auth_student_headers, test_question):
        resp = client.post("/api/answers/submit", json={
            "question_id": test_question.id,
            "answer_text": "",
        }, headers=auth_student_headers)
        assert resp.status_code == 422

    def test_submit_answer_scoring(self, client, auth_student_headers, test_question):
        """Verify the auto-grading returns a valid score structure."""
        resp = client.post("/api/answers/submit", json={
            "question_id": test_question.id,
            "answer_text": "Variables are symbols for unknown values in algebraic equations and expressions. They help solve mathematical problems.",
        }, headers=auth_student_headers)
        assert resp.status_code == 201
        score = resp.json()["score"]
        assert 0.0 <= score["keyword_score"] <= 1.0
        assert 0.0 <= score["similarity_score"] <= 1.0
        assert 0.0 <= score["grammar_score"] <= 1.0
        assert 0.0 <= score["completeness_score"] <= 1.0
        assert score["total_score"] >= 0
        assert len(score["feedback"]) > 0


class TestSubmitExam:
    """POST /api/answers/submit-exam"""

    def test_submit_exam_batch(self, client, auth_student_headers, test_exam, test_question, db):
        from app.models.question import Question
        # Add a second question
        q2 = Question(
            exam_id=test_exam.id,
            question_text="What is the order of operations in mathematics?",
            model_answer="The order of operations is PEMDAS: Parentheses, Exponents, Multiplication, Division, Addition, Subtraction.",
            marks=10.0,
            keywords=["PEMDAS", "parentheses", "exponents", "multiplication"],
        )
        db.add(q2)
        db.commit()
        db.refresh(q2)

        resp = client.post("/api/answers/submit-exam", json={
            "answers": [
                {"question_id": test_question.id, "answer_text": "Variables are symbols for unknown values in algebraic equations."},
                {"question_id": q2.id, "answer_text": "PEMDAS stands for Parentheses Exponents Multiplication Division Addition Subtraction."},
            ]
        }, headers=auth_student_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert len(data) == 2
        for answer in data:
            assert answer["score"] is not None
            assert answer["score"]["total_score"] >= 0

    def test_submit_exam_empty(self, client, auth_student_headers):
        resp = client.post("/api/answers/submit-exam", json={
            "answers": []
        }, headers=auth_student_headers)
        assert resp.status_code == 400


class TestGetMyAnswers:
    """GET /api/answers/my-answers"""

    def test_get_my_answers(self, client, auth_student_headers, test_question):
        # Submit first
        client.post("/api/answers/submit", json={
            "question_id": test_question.id,
            "answer_text": "Variables are symbols representing unknowns in algebra.",
        }, headers=auth_student_headers)

        resp = client.get("/api/answers/my-answers", headers=auth_student_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_get_my_answers_no_auth(self, client):
        resp = client.get("/api/answers/my-answers")
        assert resp.status_code == 401


class TestOverrideScore:
    """PUT /api/answers/score/{answer_id}/override"""

    def test_override_score_as_teacher(self, client, auth_student_headers, auth_teacher_headers, test_question):
        # Student submits
        submit_resp = client.post("/api/answers/submit", json={
            "question_id": test_question.id,
            "answer_text": "Variables are symbols representing unknown values in algebraic math.",
        }, headers=auth_student_headers)
        answer_id = submit_resp.json()["id"]

        # Teacher overrides
        resp = client.put(f"/api/answers/score/{answer_id}/override", json={
            "total_score": 8.5,
            "feedback": "Good answer, manually adjusted.",
        }, headers=auth_teacher_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_score"] == 8.5
        assert data["is_overridden"] is True

    def test_override_score_as_student_forbidden(self, client, auth_student_headers, test_question):
        submit_resp = client.post("/api/answers/submit", json={
            "question_id": test_question.id,
            "answer_text": "Variables represent unknowns in algebra.",
        }, headers=auth_student_headers)
        answer_id = submit_resp.json()["id"]

        resp = client.put(f"/api/answers/score/{answer_id}/override", json={
            "total_score": 10.0,
        }, headers=auth_student_headers)
        assert resp.status_code == 403
