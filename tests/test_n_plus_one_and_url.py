"""Регрессия: N+1 в ДЗ, обход LessonService в /students/{id}/lessons, кодирование URL БД."""

from datetime import datetime

import pytest
from sqlalchemy import event as sa_event

from src.core.config import Settings
from src.db.models import HomeworkStatusEnum, RoleEnum
from src.repositories import HomeworkRepository, UserRepository
from src.services.homework import HomeworkService


def _count_queries(session_maker):
    """Счётчик SQL-запросов через SQLAlchemy event 'before_cursor_execute'."""
    counter = {"n": 0}
    return counter


# ───────────────── URL-кодирование пароля ─────────────────


class TestDatabaseUrlEncoding:
    def test_special_chars_in_password_are_quoted(self):
        s = Settings(
            db_user="rep@tutor",
            db_password="p@ss/w#rd%",
            db_host="db.internal",
            db_port=5432,
            db_name="lms",
        )
        url = s.build_database_url()
        assert url.startswith("postgresql+asyncpg://")
        # спецсимволы закодированы — разбор URL не ломается
        assert "p%40ss%2Fw%23rd%25" in url
        assert "rep%40tutor" in url
        # хост и порт остались на своих местах (не «съедены» символом @ из пароля)
        assert "@db.internal:5432/lms" in url

    def test_roundtrip_parse(self):
        from urllib.parse import unquote, urlparse

        s = Settings(db_user="admin", db_password="pa@ss/word")
        parsed = urlparse(s.database_url)
        assert unquote(parsed.username) == "admin"
        assert unquote(parsed.password) == "pa@ss/word"
        assert parsed.hostname == s.db_host

    def test_plain_password_unchanged(self):
        s = Settings(db_password="postgres")
        assert ":postgres@" in s.build_database_url()

    def test_explicit_database_url_not_rewritten(self):
        s = Settings(db_url="sqlite+aiosqlite:///x.db")
        assert s.database_url == "sqlite+aiosqlite:///x.db"


# ───────────────── N+1: ДЗ ученика ─────────────────


@pytest.fixture
async def seeded(make_client):
    """Клиент + админ + ученик с 3 уроками и 3 ДЗ; счётчик запросов."""
    client, session_maker = make_client
    from src.api.dependencies import get_current_user
    from src.services.auth import AuthService

    auth = AuthService()
    async with session_maker() as session:
        urepo = UserRepository()
        admin = await urepo.create(
            session=session, role=RoleEnum.admin, login="admin",
            password_hash=auth.get_password_hash("a"),
        )
        student = await urepo.create(
            session=session, role=RoleEnum.student, login="pete",
            password_hash=auth.get_password_hash("s"), balance=5,
        )
        from src.repositories import LessonRepository
        lrepo = LessonRepository()
        hrepo = HomeworkRepository()
        for i in range(3):
            lesson = await lrepo.create(
                session=session, student_id=student.id, subject="math",
                start_time=datetime(2026, 10, 5, 10 + i),
                end_time=datetime(2026, 10, 5, 11 + i),
            )
            await hrepo.create(
                session=session, lesson_id=lesson.id, description=f"hw{i}",
                deadline=datetime(2026, 10, 6), status=HomeworkStatusEnum.pending,
            )
        await session.commit()

    app = client._transport.app  # type: ignore[attr-defined]

    async def as_admin():
        return admin

    app.dependency_overrides[get_current_user] = as_admin
    client.session_maker = session_maker  # type: ignore[attr-defined]
    client.test_app = app  # type: ignore[attr-defined]
    yield client


class TestNoNPlusOne:
    async def test_service_get_hw_is_single_query(self, seeded):
        """Сервисная выборка ДЗ — ровно 1 SQL-запрос при 3 уроках/3 ДЗ."""
        counter = {"n": 0}

        sm = seeded.session_maker
        engine = sm.kw["bind"]

        captured: list[str] = []

        @sa_event.listens_for(engine.sync_engine, "before_cursor_execute")
        def _inc(conn, cursor, statement, params, context, executemany):
            captured.append(statement)

        sid = await self._student_id(seeded)
        # Замеряем строго вызов сервиса: до него в другой сессии выполнялся
        # get_by_login (поиск student_id), который тоже попал бы в счётчик.
        captured.clear()
        try:
            async with sm() as session:
                hws = await HomeworkService().get_student_homeworks(session, sid)
        finally:
            sa_event.remove(engine.sync_engine, "before_cursor_execute", _inc)

        assert len(hws) == 3
        # ровно 1 SELECT на данные; +1 COMMIT — не запрос выборки
        selects = [q for q in captured if q.strip().upper().startswith("SELECT")]
        assert len(selects) == 1, f"ожидался 1 SELECT, получено {len(selects)} (N+1?)"

    async def test_endpoint_students_homeworks_few_queries(self, seeded):
        """/students/{id}/homeworks — константное число запросов (без N+1).

        При 3 уроках старый код делал 1 + 3(DЗ по каждому уроку) + 1(user).
        Теперь — фиксированные 2 запроса на данные независимо от числа уроков.
        """
        counter = {"n": 0}
        sm = seeded.session_maker
        engine = sm.kw["bind"]

        @sa_event.listens_for(engine.sync_engine, "before_cursor_execute")
        def _inc(conn, cursor, statement, params, context, executemany):
            counter["n"] += 1

        sid = await self._student_id(seeded)
        try:
            resp = await seeded.get(f"/students/{sid}/homeworks")
        finally:
            sa_event.remove(engine.sync_engine, "before_cursor_execute", _inc)

        assert resp.status_code == 200
        assert len(resp.json()) == 3
        # user-check в require_student_or_admin + JOIN-выборка ДЗ = 2;
        # с N+1 было бы >= 5 и росло бы с числом уроков
        assert counter["n"] <= 2, f"запросов слишком много ({counter['n']}) — похоже на N+1"

    async def test_endpoint_homeworks_by_student(self, seeded):
        sid = await self._student_id(seeded)
        resp = await seeded.get(f"/homeworks/{sid}")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 3
        # student_id корректно подтянут из урока (через JOIN, без доп. запросов)
        assert all(h["student_id"] == sid for h in body)

    async def test_unknown_student_404(self, seeded):
        """JOIN-выборка сама по себе вернула бы 200 [] — эндпоинт обязан
        проверить существование ученика и отдать 404."""
        resp = await seeded.get("/students/999/homeworks")
        assert resp.status_code == 404

    @staticmethod
    async def _student_id(client):
        async with client.session_maker() as session:
            u = await UserRepository().get_by_login(session, "pete")
            assert u is not None
            return u.id


# ─────────── /students/{id}/lessons: только через LessonService ───────────


class TestStudentsCreateLessonViaService:
    @pytest.fixture(autouse=True)
    def _admin(self, seeded):
        """Эндпоинт /students/{id}/lessons доступен только админу (require_admin)."""
        from src.api.dependencies import get_current_user

        async def as_admin():
            async with seeded.session_maker() as session:
                u = await UserRepository().get_by_login(session, "admin")
                assert u is not None
                return u

        seeded.test_app.dependency_overrides[get_current_user] = as_admin
        return seeded

    async def test_overlap_rejected_409(self, _admin):
        """Дублирующий слот теперь отклоняется (раньше эндпоинт писал в обход сервиса)."""
        seeded = _admin
        sid = await self._student_id(seeded)
        payload = {
            "subject": "math",
            "start_time": "2026-10-05T10:00:00",  # пересекается с seeded-уроком
            "end_time": "2026-10-05T10:30:00",
        }
        resp = await seeded.post(f"/students/{sid}/lessons", json=payload)
        assert resp.status_code == 409, resp.text

    async def test_end_before_start_rejected_422(self, _admin):
        seeded = _admin
        sid = await self._student_id(seeded)
        payload = {
            "subject": "math",
            "start_time": "2026-10-10T12:00:00",
            "end_time": "2026-10-10T11:00:00",
        }
        resp = await seeded.post(f"/students/{sid}/lessons", json=payload)
        assert resp.status_code == 422, resp.text

    async def test_unknown_student_404(self, _admin):
        seeded = _admin
        resp = await seeded.post("/students/999/lessons", json={
            "subject": "math",
            "start_time": "2026-11-01T10:00:00",
            "end_time": "2026-11-01T11:00:00",
        })
        assert resp.status_code == 404

    async def test_valid_lesson_created(self, _admin):
        seeded = _admin
        sid = await self._student_id(seeded)
        resp = await seeded.post(f"/students/{sid}/lessons", json={
            "subject": "informatics",
            "start_time": "2026-11-01T15:00:00",
            "end_time": "2026-11-01T16:00:00",
            "video_url": "https://meet.example/x",
        })
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "scheduled"
        assert body["video_url"] == "https://meet.example/x"

    @staticmethod
    async def _student_id(client):
        async with client.session_maker() as session:
            u = await UserRepository().get_by_login(session, "pete")
            assert u is not None
            return u.id
