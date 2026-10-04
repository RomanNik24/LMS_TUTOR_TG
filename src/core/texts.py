"""Bot texts and error messages (Russian)."""

from src.core.enums import LessonStatus, HomeworkStatus, AttendanceStatus


# Bot command descriptions
BOT_COMMANDS_GUEST = {
    "start": "Начать",
    "help": "Помощь",
}

BOT_COMMANDS_STUDENT = {
    **BOT_COMMANDS_GUEST,
    "app": "Открыть приложение",
    "today": "Расписание на сегодня",
    "hw": "Мои домашние задания",
    "web": "Войти в браузере",
    "logout": "Отвязать аккаунт",
}

BOT_COMMANDS_STAFF = {
    **BOT_COMMANDS_GUEST,
    "app": "Открыть Admin App",
    "today": "Сводка на сегодня",
    "hw": "Очередь на проверку",
    "web": "Войти в браузере",
    "logout": "Отвязать аккаунт",
}


# Guest messages
GUEST_WELCOME = (
    "Привет! Это бот репетитора Романа: информатика и математика, ОГЭ и ЕГЭ. "
    "Загляни в каталог услуг или напиши Роману напрямую."
)
CATALOG_EMPTY = "Каталог скоро появится. Напишите преподавателю."


# Student messages
def student_welcome(name: str) -> str:
    return f"Привет, {name}! Расписание и ДЗ — в приложении."


def lesson_reminder_text(subject: str, time_str: str) -> str:
    return f"⏰ Через 30 минут урок: {subject}, {time_str}"


def homework_deadline_text(title: str) -> str:
    return f"📌 Завтра дедлайн по ДЗ «{title}»"


def homework_graded_text(title: str, score: int, max_score: int) -> str:
    return f"✅ ДЗ «{title}» проверено: {score} из {max_score}"


def homework_returned_text(title: str, comment: str) -> str:
    return f"↩ ДЗ «{title}» вернулось на доработку. Комментарий: {comment}"


def homework_assigned_text(title: str, deadline: str) -> str:
    return f"📝 Новое ДЗ: «{title}». Срок: {deadline}"


def lesson_cancelled_text(date_str: str, time_str: str) -> str:
    return f"❌ Урок {date_str}, {time_str} отменён"


def lesson_rescheduled_text(old_date: str, old_time: str, new_date: str, new_time: str) -> str:
    return f"🔁 Урок перенесён: было {old_date}, {old_time}, стало {new_date}, {new_time}"


# Staff messages
def homework_submitted_text(student_name: str, title: str) -> str:
    return f"📥 ДЗ «{title}»: сдал {student_name}"


def homework_expired_text(student_name: str, title: str) -> str:
    return f"🔥 ДЗ «{title}» сгорело у {student_name}"


def lesson_unmarked_text(date_str: str, time_str: str) -> str:
    return f"Урок {date_str}, {time_str} прошёл, отметки нет"


def student_joined_text(name: str) -> str:
    return f"👋 Подключение: {name}"


def morning_digest_header(date_str: str) -> str:
    return f"Сегодня, {date_str}"


# Status display texts
LESSON_STATUS_TEXT = {
    LessonStatus.SCHEDULED: "Запланирован",
    LessonStatus.COMPLETED: "Проведён",
    LessonStatus.CANCELLED: "Отменён",
}

HOMEWORK_STATUS_TEXT = {
    HomeworkStatus.ASSIGNED: "Выдано",
    HomeworkStatus.SUBMITTED: "На проверке",
    HomeworkStatus.NEEDS_REVISION: "На доработку",
    HomeworkStatus.GRADED: "Проверено",
    HomeworkStatus.EXPIRED: "Сгорело",
}

ATTENDANCE_STATUS_TEXT = {
    AttendanceStatus.PENDING: "Не отмечено",
    AttendanceStatus.ATTENDED: "Был",
    AttendanceStatus.NO_SHOW: "Не пришёл",
    AttendanceStatus.CANCELLED: "Отменено",
}


# Error messages
ERROR_UNAUTHENTICATED = "Требуется вход в систему"
ERROR_PERMISSION_DENIED = "Недостаточно прав"
ERROR_NOT_FOUND = "Не найдено"
ERROR_LESSON_OVERLAP = "В это время уже есть урок"
ERROR_HOMEWORK_EXTENSION_LIMIT = "Дедлайн уже переносили 2 раза"
ERROR_SCORE_OUT_OF_RANGE = "Балл вне допустимого диапазона"
ERROR_INVITE_ALREADY_USED = "Приглашение уже использовано"
ERROR_INVITE_EXPIRED = "Приглашение устарело"
ERROR_TELEGRAM_ALREADY_LINKED = "Этот Telegram-аккаунт уже привязан к другому профилю"
ERROR_FILE_TOO_LARGE = "Файл слишком большой (макс. 10 МБ)"
ERROR_UNSUPPORTED_FILE_TYPE = "Неподдерживаемый тип файла"
ERROR_INTERNAL = "Что-то пошло не так. Попробуйте позже"


# UI texts (used by frontend as well)
UI_EMPTY_SCHEDULE = "Пока уроков нет. Роман добавит расписание, и оно появится здесь"
UI_EMPTY_HOMEWORK = "Все ДЗ сделаны. Новые появятся здесь"
UI_EMPTY_REPORTS = "Пока мало данных. Графики появятся после первых проверенных ДЗ"
UI_EMPTY_REVIEW_QUEUE = "Очередь пуста. Всё проверено"
UI_EMPTY_STUDENTS = "Учеников пока нет. Создайте первый профиль"
UI_SUBMIT_BUTTON = "Сдать"
UI_SELF_REPORT_BUTTON = "Сделал"
UI_SELF_REPORT_HINT = "Для устных заданий и задач на других платформах"
UI_DEADLINE_PREFIX = "Сдать до"
UI_OVERDUE = "Срок вышел. Напиши Роману"
UI_EXPIRED = "Срок сдачи закончился, сдать уже нельзя"
UI_NEEDS_REVISION = "Нужно доработать. Комментарий ниже"