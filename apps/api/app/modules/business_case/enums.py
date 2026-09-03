from enum import StrEnum


class BusinessCaseStatus(StrEnum):
    DRAFT = "draft"
    NEEDS_REVISION = "needs_revision"
    APPROVED = "approved"
    REJECTED = "rejected"


class BusinessCaseReviewDecision(StrEnum):
    APPROVE = "approve"
    NEEDS_REVISION = "needs_revision"
    REJECT = "reject"


class AssessmentRating(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
