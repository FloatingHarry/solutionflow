from dataclasses import dataclass, field

from app.modules.research.enums import (
    EvidenceConfidence,
    EvidenceVerification,
    ProfileSection,
    SourceType,
)


class ResearchProviderError(Exception):
    pass


class ResearchProviderConfigurationError(ResearchProviderError):
    pass


@dataclass(frozen=True)
class ResearchInput:
    account_name: str
    website: str | None
    industry: str | None
    region: str | None
    notes: str | None


@dataclass(frozen=True)
class SourceArtifact:
    key: str
    title: str
    source_type: SourceType
    url: str | None = None
    publisher: str | None = None
    content_excerpt: str | None = None
    is_official: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceArtifact:
    source_key: str
    supporting_text: str
    confidence: EvidenceConfidence
    verification_status: EvidenceVerification
    locator: str | None = None


@dataclass(frozen=True)
class ClaimArtifact:
    section: ProfileSection
    statement: str
    confidence: EvidenceConfidence
    evidence: tuple[EvidenceArtifact, ...]
    is_inference: bool = False


@dataclass(frozen=True)
class ResearchResult:
    summary: str
    sources: tuple[SourceArtifact, ...]
    claims: tuple[ClaimArtifact, ...]
    is_simulated: bool
    provider_response_id: str | None = None
    query_plan: dict = field(default_factory=dict)


class ResearchProvider:
    def research(self, research_input: ResearchInput) -> ResearchResult:
        raise NotImplementedError
