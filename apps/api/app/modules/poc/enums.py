from enum import StrEnum


class PocPlanStatus(StrEnum):
    DRAFT = "draft"
    NEEDS_REVISION = "needs_revision"
    APPROVED = "approved"
    REJECTED = "rejected"


class PocReviewDecision(StrEnum):
    APPROVE = "approve"
    NEEDS_REVISION = "needs_revision"
    REJECT = "reject"


class MetricOperator(StrEnum):
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN_OR_EQUAL = "lte"


class MetricResultStatus(StrEnum):
    PENDING = "pending"
    PASS = "pass"
    FAIL = "fail"


class PocDecisionType(StrEnum):
    PROCEED = "proceed"
    ITERATE = "iterate"
    REJECT = "reject"
