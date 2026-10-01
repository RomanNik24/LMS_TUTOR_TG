"""Эндпоинты «Мое» — личный кабинет через токен (без student_id в URL).

Реализует Этап 3 (кабинет ученика из docs/01_project_overview.md, п.4.1):
- карточки уроков с привязанными ДЗ и ссылками (видеосвязь/доска);
- модуль «Отчёты»: сводка + динамика оценок ДЗ и баллов пробников;
- загрузка файлов решений (фото) — file_url для кнопки «Сдать».

Все эндпоинты берут пользователя из JWT (current_user), поэтому IDOR
исключён по построению: данные отдаются только про себя.
"""

import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db_session
from src.api.schemas import (
    HomeworkDetailResponse,
    LessonCardItem,
    LessonResponse,
    MePasswordRequest,
    MockExamResponse,
    ReportSummaryResponse,
    UserResponse,
)
from src.core.config import settings
from src.db.models import Homework, HomeworkStatusEnum, Lesson, User
from src.repositories import HomeworkRepository, LessonRepository, MockExamRepository
from src.services.auth import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me", tags=["Me"])


# ─────────────────────────── профиль ───────────────────────────


@router.get("", response_model=UserResponse)
async def me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Текущий пользователь: id, логин, баланс, цена занятия."""
    return UserResponse.model_validate(current_user)


@router.post("/password", status_code=204)
async def change_password(
    data: MePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Смена пароля (минимум 6 символов — базовая политика)."""
    if len(data.new_password) < 6:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Пароль должен содержать не менее 6 символов",
        )
    auth = AuthService()
    current_user.password_hash = auth.get_password_hash(data.new_password)
    session.add(current_user)
    await session.commit()


# ─────────────────────── карточки уроков ───────────────────────


def _lesson_dto(lesson: Lesson, role: str) -> LessonResponse:
    dto = LessonResponse.model_validate(lesson)
    dto.role = role
    return dto


def _hw_dto(hw, lesson: Lesson) -> HomeworkDetailResponse:
    """ДЗ не хранит student_id — подставляем его из родительского урока."""
    data = {
        "id": hw.id,
        "lesson_id": hw.lesson_id,
        "student_id": lesson.student_id,
        "description": hw.description,
        "deadline": hw.deadline,
        "status": hw.status.value if hasattr(hw.status, "value") else hw.status,
        "student_file_url": hw.student_file_url,
        "score": hw.score,
    }
    return HomeworkDetailResponse.model_validate(data)


@router.get("/lessons", response_model=List[LessonCardItem])
async def my_lesson_cards(
    upcoming_only: bool = False,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> List[LessonCardItem]:
    """Карточки занятий: урок + его ДЗ (docs/01: «В карточке каждого занятия
    содержится информация о привязанном домашнем задании, ссылка на ВКС и доску»).

    upcoming_only=true — только предстоящие (scheduled) уроки.
    """
    lesson_repo = LessonRepository()
    hw_repo = HomeworkRepository()

    if upcoming_only:
        # «Предстоящие» — scheduled-уроки из окна на 60 дней вперёд
        now = datetime.utcnow()
        lessons = [
            l for l in await lesson_repo.get_student_lessons(
                session, current_user.id, after=now - timedelta(days=1)
            )
            if l.status.value == "scheduled" and l.start_time >= now
        ]
    else:
        lessons = await lesson_repo.get_student_lessons(session, current_user.id)
    # Один запрос ДЗ по всем урокам — без N+1
    hw_map = _group_by_lesson(await hw_repo.get_by_lesson_ids(
        session, [l.id for l in lessons]
    ))

    return [
        LessonCardItem(
            lesson=_lesson_dto(l, current_user.role.value),
            homeworks=[_hw_dto(h, l) for h in hw_map.get(l.id, [])],
        )
        for l in lessons
    ]


# ─────────────────────────── отчёты ────────────────────────────


def _group_by_lesson(hws: List[Homework]) -> dict:
    """Сгруппировать плоский список ДЗ по lesson_id (порядок по дедлайну сохранён)."""
    grouped: dict = {}
    for h in hws:
        grouped.setdefault(h.lesson_id, []).append(h)
    return grouped


def _avg_score(scores: List[str]) -> Optional[float]:
    """Среднее по числовым оценкам; нечисловые (например «зачёт») игнорируются."""
    nums: List[float] = []
    for s in scores:
        try:
            nums.append(float(s))
        except (TypeError, ValueError):
            continue
    return round(sum(nums) / len(nums), 2) if nums else None


@router.get("/reports", response_model=ReportSummaryResponse)
async def my_report_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ReportSummaryResponse:
    """Сводка прогресса ученика для экрана «Отчёты»."""
    lesson_repo = LessonRepository()
    hw_repo = HomeworkRepository()
    exam_repo = MockExamRepository()

    completed = await lesson_repo.count_completed_in_period(
        session, datetime(2000, 1, 1), datetime(2100, 1, 1), student_id=current_user.id
    )
    lessons = await lesson_repo.get_student_lessons(session, current_user.id)
    all_hw = await hw_repo.get_by_lesson_ids(
        session, [l.id for l in lessons]
    )
    graded = [h for h in all_hw if h.status == HomeworkStatusEnum.graded]

    exams = await exam_repo.get_student_exams(session, current_user.id)
    grades = [e.grade for e in exams if e.grade is not None]

    return ReportSummaryResponse(
        lessons_completed=completed,
        homeworks_total=len(all_hw),
        homeworks_graded=len(graded),
        homeworks_avg_score=_avg_score([h.score for h in graded if h.score]),
        mock_exams_count=len(exams),
        mock_exams_avg_grade=(
            round(sum(grades) / len(grades), 2) if grades else None
        ),
    )


@router.get("/reports/homework-scores", response_model=List[HomeworkDetailResponse])
async def my_homework_scores(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> List[HomeworkDetailResponse]:
    """Оценки всех ДЗ ученика — для графика среднего балла."""
    lesson_repo = LessonRepository()
    hw_repo = HomeworkRepository()

    lessons = await lesson_repo.get_student_lessons(session, current_user.id)
    by_lesson = {l.id: l for l in lessons}
    hws = await hw_repo.get_by_lesson_ids(session, list(by_lesson))
    return [_hw_dto(h, by_lesson[h.lesson_id]) for h in hws]


@router.get("/reports/mock-exams", response_model=List[MockExamResponse])
async def my_mock_exam_history(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> List[MockExamResponse]:
    """Динамика баллов пробников (хронологически) — для графика отчётов."""
    exam_repo = MockExamRepository()
    exams = await exam_repo.get_student_exams(session, current_user.id)
    return [MockExamResponse.model_validate(e) for e in exams]


# ─────────────────── загрузка файлов ДЗ (заглушка S3) ────────────────────
# docs/02_tech_stack.md предусматривает S3/MinIO; до подключения объектного
# хранилища файлы сохраняются локально и отдаются статикой /uploads/*.
# Путь и ограничения задаются в config (upload_dir, max_upload_mb).


ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf", ".txt", ".docx", ".zip",
}


@router.post("/uploads", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Сохранить файл решения и вернуть file_url для POST /homeworks/{id}/submit.

    Ограничения: размер ≤ settings.max_upload_mb, белый список расширений.
    """
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Тип файла '{ext or 'неизвестен'}' не поддерживается",
        )

    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Файл больше {settings.max_upload_mb} МБ",
        )
    if not content:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Пустой файл")

    upload_root = Path(settings.upload_dir)
    sub = upload_root / str(current_user.id)
    sub.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}{ext}"
    (sub / safe_name).write_bytes(content)

    url = f"/uploads/{current_user.id}/{safe_name}"
    logger.info("user %s uploaded %s (%d bytes)", current_user.id, url, len(content))
    return {"file_url": url, "size": len(content)}
