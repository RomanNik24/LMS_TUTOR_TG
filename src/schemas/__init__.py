"""Export all schemas."""

from src.schemas.auth import (
    InvitationCreateResponse,
    LinkAuthRequest,
    MeResponse,
    TelegramAuthRequest,
)
from src.schemas.catalog import (
    CatalogItemCreateRequest,
    CatalogItemResponse,
    CatalogItemUpdateRequest,
)
from src.schemas.common import ErrorDetail, ErrorResponse, PaginatedResponse
from src.schemas.exam import (
    MockExamResultCreateRequest,
    MockExamResultResponse,
    MockExamResultUpdateRequest,
)
from src.schemas.homework import (
    AssignmentExtendRequest,
    AssignmentGradeRequest,
    AssignmentReturnRequest,
    AssignmentSubmitRequest,
    HomeworkAssignmentResponse,
    HomeworkCreateRequest,
    HomeworkMaterialResponse,
    HomeworkResponse,
)
from src.schemas.schedule import (
    LessonCancelRequest,
    LessonCompleteRequest,
    LessonCreateRequest,
    LessonParticipantResponse,
    LessonRescheduleRequest,
    LessonResponse,
    ScheduleTemplateCreateRequest,
    ScheduleTemplateResponse,
    ScheduleTemplateUpdateRequest,
)
from src.schemas.user import (
    ExamTypeResponse,
    StaffCreateRequest,
    StaffResponse,
    StaffUpdateRequest,
    StudentCardOwnerResponse,
    StudentCreateRequest,
    StudentResponse,
    StudentUpdateRequest,
    SubjectResponse,
)

__all__ = [
    "TelegramAuthRequest", "LinkAuthRequest", "MeResponse", "InvitationCreateResponse",
    "SubjectResponse", "ExamTypeResponse",
    "StudentCreateRequest", "StudentUpdateRequest", "StudentResponse", "StudentCardOwnerResponse",
    "StaffCreateRequest", "StaffUpdateRequest", "StaffResponse",
    "ScheduleTemplateCreateRequest", "ScheduleTemplateUpdateRequest", "ScheduleTemplateResponse",
    "LessonCreateRequest", "LessonRescheduleRequest", "LessonCancelRequest", "LessonCompleteRequest",
    "LessonParticipantResponse", "LessonResponse",
    "HomeworkMaterialResponse", "HomeworkCreateRequest", "HomeworkResponse",
    "HomeworkAssignmentResponse", "AssignmentSubmitRequest", "AssignmentGradeRequest",
    "AssignmentReturnRequest", "AssignmentExtendRequest",
    "MockExamResultCreateRequest", "MockExamResultUpdateRequest", "MockExamResultResponse",
    "CatalogItemCreateRequest", "CatalogItemUpdateRequest", "CatalogItemResponse",
    "PaginatedResponse", "ErrorDetail", "ErrorResponse",
]
