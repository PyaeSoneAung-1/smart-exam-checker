"""Per-account login lockout.

After ``LOGIN_MAX_FAILED_ATTEMPTS`` (default 5) wrong passwords the account is
locked for ``LOGIN_LOCKOUT_MINUTES`` (default 15) — on top of the per-IP rate
limit — and is cleared by a successful sign-in or an admin unlock.
"""
from datetime import timedelta

from app.config import settings
from app.models.user import User
from app.utils.time import utcnow


def _login(client, email: str, password: str):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _wrong_attempts(client, email: str, count: int):
    """Fire ``count`` bad passwords and return the last response."""
    response = None
    for _ in range(count):
        response = _login(client, email, "not-the-password")
    return response


class TestLoginLockout:
    def test_lockout_config_defaults(self):
        assert settings.LOGIN_LOCKOUT_ENABLED is True
        assert settings.LOGIN_MAX_FAILED_ATTEMPTS == 5
        assert settings.LOGIN_LOCKOUT_MINUTES == 15

    def test_wrong_passwords_are_rejected_below_the_limit(self, client, test_student):
        response = _wrong_attempts(client, test_student.email, settings.LOGIN_MAX_FAILED_ATTEMPTS - 1)
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password"

        # The account is not locked yet, so the right password still works.
        assert _login(client, test_student.email, "student123").status_code == 200

    def test_account_locks_on_the_last_allowed_attempt(self, client, test_student, db):
        assert _wrong_attempts(
            client, test_student.email, settings.LOGIN_MAX_FAILED_ATTEMPTS - 1
        ).status_code == 401

        response = _wrong_attempts(client, test_student.email, 1)
        assert response.status_code == 423
        assert "locked" in response.json()["detail"].lower()

        db.expire_all()
        locked = db.query(User).filter(User.id == test_student.id).first()
        assert locked.is_locked is True
        assert locked.locked_until > utcnow()

    def test_locked_account_rejects_the_correct_password(self, client, test_student):
        _wrong_attempts(client, test_student.email, settings.LOGIN_MAX_FAILED_ATTEMPTS)
        assert _login(client, test_student.email, "student123").status_code == 423

    def test_lock_message_reports_the_waiting_time(self, client, test_student):
        _wrong_attempts(client, test_student.email, settings.LOGIN_MAX_FAILED_ATTEMPTS)
        detail = _login(client, test_student.email, "student123").json()["detail"]
        assert f"{settings.LOGIN_LOCKOUT_MINUTES} minute" in detail

    def test_successful_login_resets_the_counter(self, client, test_student, db):
        _wrong_attempts(client, test_student.email, settings.LOGIN_MAX_FAILED_ATTEMPTS - 1)
        assert _login(client, test_student.email, "student123").status_code == 200

        db.expire_all()
        user = db.query(User).filter(User.id == test_student.id).first()
        assert user.failed_login_attempts == 0
        assert user.locked_until is None

        # A fresh run of bad passwords must not lock the account early.
        assert _wrong_attempts(
            client, test_student.email, settings.LOGIN_MAX_FAILED_ATTEMPTS - 1
        ).status_code == 401

    def test_expired_lock_is_forgotten(self, client, test_student, db):
        _wrong_attempts(client, test_student.email, settings.LOGIN_MAX_FAILED_ATTEMPTS)

        user = db.query(User).filter(User.id == test_student.id).first()
        user.locked_until = utcnow() - timedelta(minutes=1)
        db.commit()

        assert _login(client, test_student.email, "student123").status_code == 200

    def test_unknown_email_never_locks_and_does_not_reveal_existence(self, client, test_student):
        unknown = _wrong_attempts(client, "nobody@test.com", settings.LOGIN_MAX_FAILED_ATTEMPTS + 3)
        known = _wrong_attempts(client, test_student.email, 1)

        # Same status and same body for both, so accounts cannot be enumerated.
        assert unknown.status_code == 401
        assert unknown.json() == known.json()

    def test_deactivated_account_is_not_locked(self, client, test_student, db):
        user = db.query(User).filter(User.id == test_student.id).first()
        user.is_active = False
        db.commit()

        # Wrong passwords on a deactivated account must not lock it (403 wins).
        assert _wrong_attempts(
            client, test_student.email, settings.LOGIN_MAX_FAILED_ATTEMPTS + 1
        ).status_code == 401


class TestAdminUnlock:
    def test_admin_can_unlock_a_locked_account(self, client, test_student, auth_admin_headers):
        _wrong_attempts(client, test_student.email, settings.LOGIN_MAX_FAILED_ATTEMPTS)
        assert _login(client, test_student.email, "student123").status_code == 423

        response = client.post(
            f"/api/users/{test_student.id}/unlock", headers=auth_admin_headers
        )
        assert response.status_code == 200
        assert response.json()["is_locked"] is False

        assert _login(client, test_student.email, "student123").status_code == 200

    def test_unlock_requires_admin(self, client, test_student, auth_student_headers, auth_teacher_headers):
        assert client.post(
            f"/api/users/{test_student.id}/unlock", headers=auth_student_headers
        ).status_code == 403
        assert client.post(
            f"/api/users/{test_student.id}/unlock", headers=auth_teacher_headers
        ).status_code == 403
        assert client.post(f"/api/users/{test_student.id}/unlock").status_code == 401

    def test_unlock_unknown_user_is_404(self, client, auth_admin_headers):
        assert client.post("/api/users/999999/unlock", headers=auth_admin_headers).status_code == 404

    def test_locked_flag_is_exposed_to_admins(self, client, test_student, auth_admin_headers):
        before = client.get("/api/users/", headers=auth_admin_headers).json()["items"]
        assert [u for u in before if u["id"] == test_student.id][0]["is_locked"] is False

        _wrong_attempts(client, test_student.email, settings.LOGIN_MAX_FAILED_ATTEMPTS)

        after = client.get("/api/users/", headers=auth_admin_headers).json()["items"]
        assert [u for u in after if u["id"] == test_student.id][0]["is_locked"] is True
