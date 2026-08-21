"""Tests for authentication endpoints."""
import pytest


class TestRegister:
    """POST /api/auth/register"""

    def test_register_student_success(self, client, auth_admin_headers):
        resp = client.post("/api/auth/register", json={
            "name": "New Student",
            "email": "newstudent@test.com",
            "password": "password123",
            "role": "student",
        }, headers=auth_admin_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newstudent@test.com"
        assert data["role"] == "student"
        assert data["is_active"] is True
        assert "id" in data

    def test_register_teacher_success(self, client, auth_admin_headers):
        resp = client.post("/api/auth/register", json={
            "name": "New Teacher",
            "email": "newteacher@test.com",
            "password": "password123",
            "role": "teacher",
        }, headers=auth_admin_headers)
        assert resp.status_code == 201
        assert resp.json()["role"] == "teacher"

    def test_register_duplicate_email(self, client, test_student, auth_admin_headers):
        resp = client.post("/api/auth/register", json={
            "name": "Dup",
            "email": "student@test.com",
            "password": "password123",
        }, headers=auth_admin_headers)
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"].lower()

    def test_register_short_password(self, client, auth_admin_headers):
        resp = client.post("/api/auth/register", json={
            "name": "Short",
            "email": "short@test.com",
            "password": "ab",
        }, headers=auth_admin_headers)
        assert resp.status_code == 422

    def test_register_invalid_email(self, client, auth_admin_headers):
        resp = client.post("/api/auth/register", json={
            "name": "Bad Email",
            "email": "not-an-email",
            "password": "password123",
        }, headers=auth_admin_headers)
        assert resp.status_code == 422


class TestLogin:
    """POST /api/auth/login"""

    def test_login_success(self, client, test_student):
        resp = client.post("/api/auth/login", json={
            "email": "student@test.com",
            "password": "student123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_student):
        resp = client.post("/api/auth/login", json={
            "email": "student@test.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "nobody@test.com",
            "password": "password123",
        })
        assert resp.status_code == 401

    def test_login_inactive_user(self, client, db, test_student):
        test_student.is_active = False
        db.commit()
        resp = client.post("/api/auth/login", json={
            "email": "student@test.com",
            "password": "student123",
        })
        assert resp.status_code == 403


class TestTokenRefresh:
    """POST /api/auth/refresh"""

    def test_refresh_success(self, client, test_student):
        login_resp = client.post("/api/auth/login", json={
            "email": "student@test.com",
            "password": "student123",
        })
        refresh_token = login_resp.json()["refresh_token"]

        resp = client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_with_access_token_fails(self, client, test_student):
        login_resp = client.post("/api/auth/login", json={
            "email": "student@test.com",
            "password": "student123",
        })
        access_token = login_resp.json()["access_token"]

        resp = client.post("/api/auth/refresh", json={
            "refresh_token": access_token,
        })
        assert resp.status_code == 401

    def test_refresh_invalid_token(self, client):
        resp = client.post("/api/auth/refresh", json={
            "refresh_token": "completely.invalid.token",
        })
        assert resp.status_code == 401


class TestGetMe:
    """GET /api/auth/me"""

    def test_get_me_authenticated(self, client, auth_student_headers, test_student):
        resp = client.get("/api/auth/me", headers=auth_student_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "student@test.com"
        assert data["name"] == "Test Student"

    def test_get_me_no_token(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_get_me_invalid_token(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"})
        assert resp.status_code == 401
