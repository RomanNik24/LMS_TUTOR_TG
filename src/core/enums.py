"""Enumeration types."""

from enum import Enum


class UserRole(str, Enum):
    OWNER = "owner"
    MANAGER = "manager"
    STUDENT = "student"


class LessonStatus(str, Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AttendanceStatus(str, Enum):
    PENDING = "pending"
    ATTENDED = "attended"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"


class HomeworkKind(str, Enum):
    REGULAR = "regular"
    MOCK_EXAM = "mock_exam"


class HomeworkStatus(str, Enum):
    ASSIGNED = "assigned"
    SUBMITTED = "submitted"
    NEEDS_REVISION = "needs_revision"
    GRADED = "graded"
    EXPIRED = "expired"


class ExamKind(str, Enum):
    OGE = "oge"
    EGE = "ege"


class ExamResultKind(str, Enum):
    GRADE_2_5 = "grade_2_5"
    TEST_100 = "test_100"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class AuthTokenPurpose(str, Enum):
    INVITE = "invite"
    WEB_LOGIN = "web_login"


class FileRole(str, Enum):
    STUDENT_SOLUTION = "student_solution"
    TEACHER_REVIEW = "teacher_review"
    HOMEWORK_MATERIAL = "homework_material"