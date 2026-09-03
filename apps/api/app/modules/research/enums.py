from enum import StrEnum


class ResearchStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    NEEDS_REVIEW = "needs_review"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class ResearchProviderName(StrEnum):
    MOCK = "mock"
    OPENAI = "openai"


class SourceType(StrEnum):
    ACCOUNT_INPUT = "account_input"
    COMPANY_WEBSITE = "company_website"
    ANNUAL_REPORT = "annual_report"
    NEWS = "news"
    WEB = "web"
    OTHER = "other"


class EvidenceConfidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EvidenceVerification(StrEnum):
    DIRECT_INPUT = "direct_input"
    AI_EXTRACTED = "ai_extracted"
    VERIFIED = "verified"


class ClaimReviewStatus(StrEnum):
    AI_GENERATED = "ai_generated"
    HUMAN_REVIEWED = "human_reviewed"
    HUMAN_REJECTED = "human_rejected"


class ProfileSection(StrEnum):
    COMPANY_OVERVIEW = "company_overview"
    PRODUCTS_SERVICES = "products_services"
    MARKET_GEOGRAPHY = "market_geography"
    CUSTOMERS = "customers"
    RECENT_DEVELOPMENTS = "recent_developments"
    FINANCIAL_OPERATING_SIGNALS = "financial_operating_signals"
    AI_DIGITAL_INITIATIVES = "ai_digital_initiatives"
    POTENTIAL_STRATEGIC_PRIORITIES = "potential_strategic_priorities"


class ReviewDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
