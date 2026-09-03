from enum import StrEnum


class AgentProvider(StrEnum):
    GUIDED = "guided"
    OPENAI = "openai"


class AgentRunStatus(StrEnum):
    COMPLETED = "completed"
    AWAITING_APPROVAL = "awaiting_approval"
    ACTION_COMPLETED = "action_completed"
    REJECTED = "rejected"
    FAILED = "failed"


class AgentActionStatus(StrEnum):
    NONE = "none"
    PENDING = "pending"
    EXECUTED = "executed"
    REJECTED = "rejected"
    FAILED = "failed"
