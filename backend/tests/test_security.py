"""Regression tests for the authorisation and credential hardening changes."""
import pytest

from app.core.security import create_access_token, get_password_hash
from app.models.answer import StudentAnswer
from app.models.subject import Subject
from app.models.user import User, UserRole


def _answer_for(db, question, student, text="An answer about algebra and variables"):
    answer = StudentAnswer(question_id=question.id, student_id=student.id, answer_text=text)
    db.add(answer)
    db.commit()
    db.refresh(answer)
    return answer


class TestAnswersVisibility:
    def test_student_only_sees_own_answers(
        self, client, db, test_student, test_question, auth_student_headers
    ):
        other = User(
            name="Other Student",
            email="other@test.com",
            hashed_password=get_password_hash("other123"),
            role=UserRole.STUDENT,
            is_active=True,
        )
        db.add(other)
        db.commit()
        db.refresh(other)

        _answer_for(db, test_question, other, "other student's private answer")

        resp = client.get("/api/answers/?size=50", headers=auth_student_headers)
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_student_cannot_request_another_students_answers(
        self, client, db, test_student, test_question, auth_student_headers
    ):
        other = User(
            name="Other Student",
            email="other2@test.com",
            hashed_password=get_password_hash("other123"),
            role=UserRole.STUDENT,
            is_active=True,
        )
        db.add(other)
        db.commit()
        db.refresh(other)
        _answer_for(db, test_question, other)

        resp = client.get(
            f"/api/answers/?student_id={other.id}", headers=auth_student_headers
        )
        assert resp.status_code == 200
        assert resp.json()["items"] == []


class TestModelAnswerConfidentiality:
    def test_student_question_response_hides_model_answer(
        self, client, test_question, auth_student_headers
    ):
        resp = client.get(f"/api/questions/{test_question.id}", headers=auth_student_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "model_answer" not in body
        assert "keywords" not in body
        assert body["question_text"]

    def test_student_question_list_hides_model_answer(
        self, client, test_question, auth_student_headers
    ):
        resp = client.get("/api/questions/?size=50", headers=auth_student_headers)
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert "model_answer" not in item

    def test_teacher_still_sees_model_answer(
        self, client, test_question, auth_teacher_headers
    ):
        resp = client.get(f"/api/questions/{test_question.id}", headers=auth_teacher_headers)
        assert resp.status_code == 200
        assert resp.json()["model_answer"]


class TestAdvancedNlpIsTeacherOnly:
    ENDPOINTS = [
        ("post", "/api/nlp/plagiarism-check", {"exam_id": 1}),
        ("post", "/api/nlp/ai-auto-scan", {"exam_id": 1}),
        ("post", "/api/nlp/ai-detection", {"text": "some text to analyse"}),
        ("get", "/api/nlp/feedback/1", None),
        ("post", "/api/nlp/rubric-grade", {"answer_id": 1}),
        ("post", "/api/nlp/generate-model-answer", {"question_id": 1}),
        ("post", "/api/nlp/class-report", {"exam_id": 1}),
    ]

    @pytest.mark.parametrize("method,path,payload", ENDPOINTS)
    def test_student_gets_403(self, client, auth_student_headers, method, path, payload):
        call = getattr(client, method)
        resp = call(path, json=payload, headers=auth_student_headers) if payload else call(
            path, headers=auth_student_headers
        )
        assert resp.status_code == 403

    @pytest.mark.parametrize("method,path,payload", ENDPOINTS)
    def test_anonymous_gets_401(self, client, method, path, payload):
        call = getattr(client, method)
        resp = call(path, json=payload) if payload else call(path)
        assert resp.status_code == 401

    def test_teacher_cannot_analyse_another_teachers_exam(
        self, client, db, test_exam, test_student, test_question, auth_student_headers
    ):
        stranger = User(
            name="Stranger Teacher",
            email="stranger@test.com",
            hashed_password=get_password_hash("stranger123"),
            role=UserRole.TEACHER,
            is_active=True,
        )
        db.add(stranger)
        db.commit()
        db.refresh(stranger)

        headers = {
            "Authorization": f"Bearer {create_access_token({'sub': str(stranger.id), 'role': 'teacher'})}"
        }
        resp = client.post(
            "/api/nlp/plagiarism-check", json={"exam_id": test_exam.id}, headers=headers
        )
        assert resp.status_code == 403


class TestAnswersOwnership:
    def test_owner_teacher_can_read_question_answers(
        self, client, db, test_question, test_student, auth_teacher_headers
    ):
        _answer_for(db, test_question, test_student)
        resp = client.get(
            f"/api/answers/question/{test_question.id}", headers=auth_teacher_headers
        )
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    def test_other_teacher_cannot_read_question_answers(
        self, client, db, test_question, test_student
    ):
        stranger = User(
            name="Stranger Teacher",
            email="stranger2@test.com",
            hashed_password=get_password_hash("stranger123"),
            role=UserRole.TEACHER,
            is_active=True,
        )
        db.add(stranger)
        db.commit()
        db.refresh(stranger)
        _answer_for(db, test_question, test_student)

        headers = {
            "Authorization": f"Bearer {create_access_token({'sub': str(stranger.id), 'role': 'teacher'})}"
        }
        resp = client.get(f"/api/answers/question/{test_question.id}", headers=headers)
        assert resp.status_code == 403


class TestSettingsAreAuthenticated:
    def test_settings_require_auth(self, client):
        assert client.get("/api/settings").status_code == 401
        assert client.get("/api/settings/pass_percentage").status_code == 401

    def test_settings_available_when_authenticated(self, client, auth_student_headers):
        resp = client.get("/api/settings", headers=auth_student_headers)
        assert resp.status_code == 200
        assert resp.json()["pass_percentage"]


class TestTokenRevocation:
    def test_logout_invalidates_existing_tokens(self, client, auth_student_headers):
        assert client.get("/api/auth/me", headers=auth_student_headers).status_code == 200

        logout = client.post("/api/auth/logout", headers=auth_student_headers)
        assert logout.status_code == 200

        assert client.get("/api/auth/me", headers=auth_student_headers).status_code == 401

    def test_password_change_invalidates_existing_tokens(self, client, auth_student_headers):
        resp = client.put(
            "/api/auth/change-password",
            json={"current_password": "student123", "new_password": "brand-new-password"},
            headers=auth_student_headers,
        )
        assert resp.status_code == 200
        assert client.get("/api/auth/me", headers=auth_student_headers).status_code == 401

    def test_refresh_rejects_revoked_token(self, client, db, test_student):
        refresh = create_access_token  # keep import used
        assert refresh is not None
        from app.core.security import create_refresh_token

        revoked = create_refresh_token({"sub": str(test_student.id), "role": "student", "ver": 0})
        test_student.token_version = 1
        db.commit()

        resp = client.post("/api/auth/refresh", json={"refresh_token": revoked})
        assert resp.status_code == 401


class TestHealthEndpoints:
    def test_system_health_is_admin_only(self, client, auth_student_headers, auth_admin_headers):
        assert client.get("/health/system").status_code == 401
        assert client.get("/health/system", headers=auth_student_headers).status_code == 403
        assert client.get("/health/system", headers=auth_admin_headers).status_code == 200

    def test_health_never_leaks_exception_details(self, client):
        resp = client.get("/health/db")
        assert resp.status_code == 200
        assert "error" not in resp.json()


class TestFileServingIsAuthenticated:
    def test_files_require_a_token(self, client, tmp_path, monkeypatch):
        from app import files

        uploads = tmp_path / "uploads"
        uploads.mkdir()
        (uploads / "secret.txt").write_text("private", encoding="utf-8")
        monkeypatch.setattr(files.settings, "UPLOAD_DIR", str(uploads))

        assert client.get("/api/files/secret.txt").status_code == 401

    def test_authenticated_user_can_read_files(
        self, client, tmp_path, monkeypatch, auth_student_headers
    ):
        from app import files

        uploads = tmp_path / "uploads"
        uploads.mkdir()
        (uploads / "note.txt").write_text("hello", encoding="utf-8")
        monkeypatch.setattr(files.settings, "UPLOAD_DIR", str(uploads))

        resp = client.get("/api/files/note.txt", headers=auth_student_headers)
        assert resp.status_code == 200
        assert resp.text == "hello"

    def test_path_traversal_is_blocked(self, client, tmp_path, monkeypatch, auth_student_headers):
        from app import files

        uploads = tmp_path / "uploads"
        uploads.mkdir()
        (tmp_path / "outside.txt").write_text("nope", encoding="utf-8")
        monkeypatch.setattr(files.settings, "UPLOAD_DIR", str(uploads))

        resp = client.get("/api/files/../outside.txt", headers=auth_student_headers)
        assert resp.status_code in (404, 400)


class TestTeacherScopeStillApplies:
    def test_teacher_sees_only_own_subject_answers(
        self, client, db, test_teacher, test_student, test_question, auth_teacher_headers
    ):
        _answer_for(db, test_question, test_student)
        foreign_subject = Subject(name="Physics", teacher_id=999, description="x")
        db.add(foreign_subject)
        db.commit()

        resp = client.get("/api/answers/?size=50", headers=auth_teacher_headers)
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1
