"""HTTP-тесты эндпоинтов Этапа 1 (FastAPI + SQLite in-memory).

Проверяют: RBAC (401/403), сценарий урока целиком, дашборд и списание баланса.
Фикстура ``client`` из conftest.py переопределяет get_db_session на in-memory БД.
"""

from datetime import datetime, timedelta

import pytest

from src.api.dependencies import get_current_user
from src.db.models import RoleEnum, User
from src.repositories import UserRepository
from src.services.auth import AuthService


@pytest.fixture
async def api_client(make_client):
    """Клиент + сид пользователей; возвращает (client, admin, student)."""
    client, session_maker = make_client

    auth = AuthService()
    async with session_maker() as session:
        repo = UserRepository()
        admin = await repo.create(
            session=session, role=RoleEnum.admin, login="admin",
            password_hash=auth.get_password_hash("admin-pass"),
        )
        student = await repo.create(
            session=session, role=RoleEnum.student, login="pete",
            password_hash=auth.get_password_hash("secret"),
            balance=2, lesson_price=1000,
        )
        await session.commit()

    # «Логин» в тестах: подменяем зависимость get_current_user нужным юзером
    app = client._transport.app  # type: ignore[attr-defined]

    async def as_admin():
        return admin

    async def as_student():
        return student

    client.admin_id = admin.id  # type: ignore[attr-defined]
    client.student_id = student.id  # type: ignore[attr-defined]
    client.as_admin = as_admin  # type: ignore[attr-defined]
    client.as_student = as_student  # type: ignore[attr-defined]
    client.app = app  # type: ignore[attr-defined]
    yield client


def _login_as(client, who):
    """Установить текущего пользователя для последующих запросов."""
    dep = client.as_admin if who == "admin" else client.as_student
    client.app.dependency_overrides[get_current_user] = dep


class TestRBAC:
    async def test_lessons_require_auth(self, api_client):
        resp = await api_client.post("/lessons/1", json={
            "subject": "math",
            "start_time": "2026-10-05T10:00:00",
            "end_time": "2026-10-05T11:00:00",
        })
        assert resp.status_code == 401

    async def test_student_cannot_create_lesson(self, api_client):
        _login_as(api_client, "student")
        resp = await api_client.post(f"/lessons/{api_client.student_id}", json={
            "subject": "math",
            "start_time": "2026-10-05T10:00:00",
            "end_time": "2026-10-05T11:00:00",
        })
        assert resp.status_code == 403

    async def test_dashboard_forbidden_for_student(self, api_client):
        _login_as(api_client, "student")
        resp = await api_client.get("/admin/dashboard")
        assert resp.status_code == 403


class TestLessonFlow:
    async def test_full_cycle_via_http(self, api_client):
        c = api_client
        _login_as(c, "admin")
        start = datetime(2026, 10, 5, 10, 0)

        # создать урок
        resp = await c.post(f"/lessons/{c.student_id}", json={
            "subject": "informatics",
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(hours=1)).isoformat(),
            "video_url": "https://telemost.example/abc",
        })
        assert resp.status_code == 201, resp.text
        lesson_id = resp.json()["id"]
        assert resp.json()["status"] == "scheduled"

        # конфликтующий урок -> 409
        resp = await c.post(f"/lessons/{c.student_id}", json={
            "subject": "math",
            "start_time": (start + timedelta(minutes=30)).isoformat(),
            "end_time": (start + timedelta(minutes=90)).isoformat(),
        })
        assert resp.status_code == 409

        # выдать ДЗ
        resp = await c.post("/homeworks/", json={
            "lesson_id": lesson_id,
            "description": "№12",
            "deadline": (start + timedelta(days=1)).isoformat(),
        })
        assert resp.status_code == 201, resp.text
        hw_id = resp.json()["id"]

        # ученик сдаёт
        _login_as(c, "student")
        resp = await c.post(f"/homeworks/{hw_id}/submit", json={"file_url": "https://s3/x.jpg"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "submitted"

        # админ оценивает
        _login_as(c, "admin")
        resp = await c.post(f"/homeworks/{hw_id}/grade", json={"score": "26/27"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "graded"

        # пробник с автоконвертацией 18 -> 5
        resp = await c.post(f"/mock-exams/{c.student_id}", json={
            "subject": "informatics", "primary_score": 18,
            "exam_date": "2026-10-04",
        })
        assert resp.status_code == 201
        assert resp.json()["grade"] == 5

        # провести урок -> баланс 2 -> 1
        resp = await c.post(f"/lessons/{lesson_id}/complete")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

        # повторное проведение -> 422
        resp = await c.post(f"/lessons/{lesson_id}/complete")
        assert resp.status_code == 422

        # дашборд: урок уже completed, должников нет (баланс 1)
        resp = await c.get("/admin/dashboard")
        assert resp.status_code == 200
        body = resp.json()
        assert body["debtors"] == []

        # статистика по ученику
        resp = await c.get("/admin/progress")
        rows = {r["student_id"]: r for r in resp.json()}
        assert rows[c.student_id]["lessons_completed"] == 1
        assert rows[c.student_id]["balance"] == 1
        assert rows[c.student_id]["mock_exams_avg_grade"] == 5.0

    async def test_mock_exam_history_visible_to_student(self, api_client):
        c = api_client
        _login_as(c, "admin")
        await c.post(f"/mock-exams/{c.student_id}", json={
            "subject": "informatics", "primary_score": 13, "exam_date": "2026-10-01",
        })
        _login_as(c, "student")
        resp = await c.get(f"/mock-exams/{c.student_id}")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["grade"] == 4  # 13 баллов -> 4 (порог docs/04: 12-16)

    async def test_student_cannot_see_other_student(self, api_client):
        c = api_client
        _login_as(c, "student")
        resp = await c.get("/mock-exams/999")
        assert resp.status_code == 403

    async def test_balance_adjust_and_debtor_flag(self, api_client):
        c = api_client
        _login_as(c, "admin")
        resp = await c.post(f"/admin/{c.student_id}/balance", json={"delta": -4})
        assert resp.status_code == 200
        assert resp.json()["balance"] == -2
        resp = await c.get("/admin/dashboard")
        assert c.student_id in resp.json()["debtors"]
