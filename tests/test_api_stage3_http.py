"""HTTP-тесты Этапа 3: эндпоинты личного кабинета /me/*.

Проверяют (docs/01, п.4.1 и docs/06 — правила для агентов):
- карточки уроков с привязанными ДЗ (без student_id в URL — IDOR исключён);
- отчёты: сводка, оценки ДЗ, история пробников;
- загрузку файлов решений (POST /me/uploads) с валидацией типа/размера;
- RBAC: без токена — 401.
Фикстура ``make_client`` из conftest.py поднимает SQLite in-memory.
"""

from datetime import datetime, timedelta

import pytest

from src.api.dependencies import get_current_user
from src.db.models import (
    Homework,
    HomeworkStatusEnum,
    Lesson,
    LessonStatusEnum,
    MockExam,
    RoleEnum,
    User,
)
from src.services.auth import AuthService


@pytest.fixture
async def me_client(make_client):
    """Клиент с залогиненным учеником и наполненной БД."""
    client, session_maker = make_client

    auth = AuthService()
    async with session_maker() as session:
        student = User(
            role=RoleEnum.student, login="pete",
            password_hash=auth.get_password_hash("secret"),
            balance=5, lesson_price=1000, telegram_id=111,
        )
        admin = User(
            role=RoleEnum.admin, login="admin",
            password_hash=auth.get_password_hash("admin-pass"),
        )
        session.add_all([student, admin])
        await session.flush()

        now = datetime.utcnow()
        l1 = Lesson(student_id=student.id, subject="Информатика",
                    start_time=now + timedelta(days=1),
                    end_time=now + timedelta(days=1, hours=1),
                    status=LessonStatusEnum.scheduled,
                    video_url="https://meet.example/1", board_url="https://board.example/1")
        l2 = Lesson(student_id=student.id, subject="Математика",
                    start_time=now - timedelta(days=2),
                    end_time=now - timedelta(days=2, hours=-1),
                    status=LessonStatusEnum.completed)
        session.add_all([l1, l2])
        await session.flush()

        session.add_all([
            Homework(lesson_id=l1.id, description="Составить блок-схему",
                     deadline=now + timedelta(days=2),
                     status=HomeworkStatusEnum.pending),
            Homework(lesson_id=l2.id, description="Решить №14",
                     deadline=now - timedelta(days=1),
                     status=HomeworkStatusEnum.graded, score="4"),
            MockExam(student_id=student.id, subject="informatics",
                     date=(now - timedelta(days=3)).date(),
                     primary_score=18, grade=5),
        ])
        await session.commit()
        sid = student.id

    async def as_student():
        async with session_maker() as s:
            from src.db.models import User
            return await s.get(User, sid)

    client.app = client._transport.app  # type: ignore[attr-defined]
    client.app.dependency_overrides[get_current_user] = as_student
    client.student_id = sid  # type: ignore[attr-defined]
    yield client


class TestMeProfile:
    async def test_requires_auth(self, make_client):
        client, _ = make_client
        resp = await client.get("/me")
        assert resp.status_code == 401

    async def test_me_returns_own_profile(self, me_client):
        resp = await me_client.get("/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["login"] == "pete"
        assert data["balance"] == 5
        assert data["id"] == me_client.student_id

    async def test_change_password_too_short_rejected(self, me_client):
        resp = await me_client.post("/me/password", json={"new_password": "123"})
        assert resp.status_code == 422

    async def test_change_password_ok(self, me_client):
        resp = await me_client.post("/me/password", json={"new_password": "newsecret"})
        assert resp.status_code == 204


class TestMeLessonCards:
    async def test_cards_include_homeworks_and_links(self, me_client):
        resp = await me_client.get("/me/lessons")
        assert resp.status_code == 200
        cards = resp.json()
        assert len(cards) == 2
        upcoming = [c for c in cards if c["lesson"]["subject"] == "Информатика"][0]
        assert upcoming["lesson"]["video_url"] == "https://meet.example/1"
        assert upcoming["lesson"]["board_url"] == "https://board.example/1"
        assert len(upcoming["homeworks"]) == 1
        hw = upcoming["homeworks"][0]
        assert hw["description"] == "Составить блок-схему"
        assert hw["status"] == "pending"
        # student_id в DTO берётся из урока (в модели ДЗ его нет)
        assert hw["student_id"] == me_client.student_id

    async def test_upcoming_only_filters_past(self, me_client):
        resp = await me_client.get("/me/lessons?upcoming_only=true")
        cards = resp.json()
        assert [c["lesson"]["subject"] for c in cards] == ["Информатика"]


class TestMeReports:
    async def test_summary(self, me_client):
        resp = await me_client.get("/me/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert data["homeworks_total"] == 2
        assert data["homeworks_graded"] == 1
        assert data["homeworks_avg_score"] == 4.0
        assert data["mock_exams_count"] == 1
        assert data["mock_exams_avg_grade"] == 5.0

    async def test_homework_scores_list(self, me_client):
        resp = await me_client.get("/me/reports/homework-scores")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2
        graded = [i for i in items if i["score"]]
        assert graded[0]["score"] == "4"

    async def test_mock_exam_history(self, me_client):
        resp = await me_client.get("/me/reports/mock-exams")
        assert resp.status_code == 200
        exams = resp.json()
        assert len(exams) == 1
        assert exams[0]["primary_score"] == 18
        assert exams[0]["grade"] == 5


class TestMeUploads:
    async def test_upload_ok(self, me_client):
        resp = await me_client.post(
            "/me/uploads",
            files={"file": ("solution.png", b"\x89PNG fake bytes", "image/png")},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["file_url"].startswith(f"/uploads/{me_client.student_id}/")
        assert body["size"] > 0

    async def test_upload_bad_extension_rejected(self, me_client):
        resp = await me_client.post(
            "/me/uploads",
            files={"file": ("malware.exe", b"MZ...", "application/octet-stream")},
        )
        assert resp.status_code == 422

    async def test_upload_empty_rejected(self, me_client):
        resp = await me_client.post(
            "/me/uploads",
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        assert resp.status_code == 422

    async def test_uploaded_file_is_served(self, me_client):
        resp = await me_client.post(
            "/me/uploads",
            files={"file": ("hw.txt", b"my solution text", "text/plain")},
        )
        url = resp.json()["file_url"]
        served = await me_client.get(url)
        assert served.status_code == 200
        assert served.content == b"my solution text"
