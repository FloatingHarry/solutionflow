from enum import StrEnum


class HypothesisStatus(StrEnum):
    AI_SUGGESTED = "ai_suggested"
    USER_ACCEPTED = "user_accepted"
    USER_REJECTED = "user_rejected"
    NEED_VALIDATION = "need_validation"
    CONFIRMED = "confirmed"


class HypothesisOrigin(StrEnum):
    MANUAL = "manual"
    RESEARCH_TEMPLATE = "research_template"


class HypothesisReviewDecision(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    NEED_VALIDATION = "need_validation"
