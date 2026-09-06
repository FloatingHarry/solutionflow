from enum import StrEnum


class KnowledgeScope(StrEnum):
    ACCOUNT = "account"
    ENTERPRISE = "enterprise"


class DocumentStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class Confidentiality(StrEnum):
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class EmbeddingProvider(StrEnum):
    LOCAL_HASH = "local_hash"
    OPENAI = "openai"


class AnswerProvider(StrEnum):
    GUIDED = "guided"
    OPENAI = "openai"


class EvidenceCandidateStatus(StrEnum):
    RETRIEVED = "retrieved"
    REVIEWED = "reviewed"
    REJECTED = "rejected"
