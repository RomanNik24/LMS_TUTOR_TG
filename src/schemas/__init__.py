"""Export all schemas."""

from src.schemas.auth import TelegramAuthRequest, LinkAuthRequest, MeResponse, InvitationCreateResponse
from src.schemas.user import (
    SubjectResponse, ExamTypeResponse,
    StudentCreateRequest, StudentUpdateRequest, StudentResponse, StudentCardOwnerResponse,
    StaffCreateRequest, StaffUpdateRequest, StaffResponse,
)
from src.schemas.schedule import (
    ScheduleTemplateCreateRequest, ScheduleTemplateUpdateRequest, ScheduleTemplateResponse,
    LessonCreateRequest, LessonRescheduleRequest, LessonCancelRequest, LessonCompleteRequest,
    LessonParticipantResponse, LessonResponse,
)
from src.schemas.homework import (
    HomeworkMaterialResponse, HomeworkCreateRequest, HomeworkResponse,
    HomeworkAssignmentResponse, AssignmentSubmitRequest, AssignmentGradeRequest,
    AssignmentReturnRequest, AssignmentExtendRequest,
)
from src.schemas.exam import MockExamResultCreateRequest, MockExamResultUpdateRequest, MockExamResultResponse
from src.schemas.catalog import CatalogItemCreateRequest, CatalogItemUpdateRequest, CatalogItemResponse
from src.schemas.common import PaginatedResponse, ErrorDetail, ErrorResponse

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