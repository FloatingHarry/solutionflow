from enum import StrEnum


class StageName(StrEnum):
    RESEARCH = "research"
    OPPORTUNITY = "opportunity"
    DISCOVERY = "discovery"
    SOLUTION = "solution"
    POC = "poc"
    EVALUATION = "evaluation"
    BUSINESS_CASE = "business_case"
    DEPLOYMENT = "deployment"


STAGE_ORDER = list(StageName)


class StageStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class ActorType(StrEnum):
    SYSTEM = "system"
    USER = "user"
