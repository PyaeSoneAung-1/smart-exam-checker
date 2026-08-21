"""Tests for exam CRUD endpoints."""
import pytest


class TestCreateExam:
    """POST /api/exams/"""

    def test_create_exam_as_teacher(self, client, auth_teacher_headers, test_subject):
        resp = client.post("/api/exams/", json={
            "subject_id": test_subject.id,
            "title": "New Exam",
            "description": "A test exam",
            "total_marks": 100,
            "time_limit_minutes": 90,
        }, headers=auth_teacher_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "New Exam"
        assert data["total_marks"] == 100.0

    def test_create_exam_as_student_forbidden(self, client, auth_student_headers, test_subject):
        resp = client.post("/api/exams/", json={
            "subject_id": test_subject.id,
            "title": "Student Exam",
            "total_marks": 50,
        }, headers=auth_student_headers)
        assert resp.status_code == 403

    def test_create_exam_no_auth(self, client, test_subject):
        resp = client.post("/api/exams/", json={
            "subject_id": test_subject.id,
            "title": "Anon Exam",
            "total_marks": 50,
        })
        assert resp.status_code == 401

    def test_create_exam_invalid_subject(self, client, auth_teacher_headers):
        resp = client.post("/api/exams/", json={
            "subject_id": 9999,
            "title": "No Subject",
            "total_marks": 50,
        }, headers=auth_teacher_headers)
        assert resp.status_code == 404


class TestListExams:
    """GET /api/exams/"""

    def test_list_exams_authenticated(self, client, auth_student_headers, test_exam):
        resp = client.get("/api/exams/", headers=auth_student_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] >= 1

    def test_list_exams_filter_subject(self, client, auth_student_headers, test_exam, test_subject):
        resp = client.get(f"/api/exams/?subject_id={test_subject.id}", headers=auth_student_headers)
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["subject_id"] == test_subject.id

    def test_list_exams_search(self, client, auth_student_headers, test_exam):
        resp = client.get("/api/exams/?search=Algebra", headers=auth_student_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1


class TestGetExam:
    """GET /api/exams/{exam_id}"""

    def test_get_exam_detail(self, client, auth_student_headers, test_exam, test_question):
        resp = client.get(f"/api/exams/{test_exam.id}", headers=auth_student_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Algebra Midterm"
        assert len(data["questions"]) >= 1

    def test_get_exam_not_found(self, client, auth_student_headers):
        resp = client.get("/api/exams/9999", headers=auth_student_headers)
        assert resp.status_code == 404


class TestUpdateExam:
    """PUT /api/exams/{exam_id}"""

    def test_update_exam_as_teacher(self, client, auth_teacher_headers, test_exam):
        resp = client.put(f"/api/exams/{test_exam.id}", json={
            "title": "Updated Algebra Midterm",
            "total_marks": 25,
        }, headers=auth_teacher_headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Algebra Midterm"
        assert resp.json()["total_marks"] == 25.0

    def test_update_exam_as_student_forbidden(self, client, auth_student_headers, test_exam):
        resp = client.put(f"/api/exams/{test_exam.id}", json={
            "title": "Hacked Title",
        }, headers=auth_student_headers)
        assert resp.status_code == 403


class TestDeleteExam:
    """DELETE /api/exams/{exam_id}"""

    def test_delete_exam_as_teacher(self, client, auth_teacher_headers, test_exam):
        resp = client.delete(f"/api/exams/{test_exam.id}", headers=auth_teacher_headers)
        assert resp.status_code == 204

        # Verify deleted
        resp2 = client.get(f"/api/exams/{test_exam.id}", headers=auth_teacher_headers)
        assert resp2.status_code == 404

    def test_delete_exam_as_student_forbidden(self, client, auth_student_headers, test_exam):
        resp = client.delete(f"/api/exams/{test_exam.id}", headers=auth_student_headers)
        assert resp.status_code == 403
