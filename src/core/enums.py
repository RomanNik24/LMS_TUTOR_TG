"""Enumeration types."""

from enum import StrEnum


class UserRole(StrEnum):
    OWNER = "owner"
    MANAGER = "manager"
    STUDENT = "student"


class LessonStatus(StrEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AttendanceStatus(StrEnum):
    PENDING = "pending"
    ATTENDED = "attended"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"


class HomeworkKind(StrEnum):
    REGULAR = "regular"
    MOCK_EXAM = "mock_exam"


class HomeworkStatus(StrEnum):
    ASSIGNED = "assigned"
    SUBMITTED = "submitted"
    NEEDS_REVISION = "needs_revision"
    GRADED = "graded"
    EXPIRED = "expired"


class ExamKind(StrEnum):
    OGE = "oge"
    EGE = "ege"


class ExamResultKind(StrEnum):
    GRADE_2_5 = "grade_2_5"
    TEST_100 = "test_100"


class NotificationStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class AuthTokenPurpose(StrEnum):
    INVITE = "invite"
    WEB_LOGIN = "web_login"


class FileRole(StrEnum):
    STUDENT_SOLUTION = "student_solution"
    TEACHER_REVIEW = "teacher_review"
    HOMEWORK_MATERIAL = "homework_material"
