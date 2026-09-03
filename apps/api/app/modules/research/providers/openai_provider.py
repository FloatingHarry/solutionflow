import json
from urllib.parse import urlparse

from openai import OpenAI

from app.modules.research.enums import (
    EvidenceConfidence,
    EvidenceVerification,
    ProfileSection,
    SourceType,
)
from app.modules.research.providers.base import (
    ClaimArtifact,
    EvidenceArtifact,
    ResearchInput,
    ResearchProvider,
    ResearchProviderConfigurationError,
    ResearchProviderError,
    ResearchResult,
    SourceArtifact,
)

PROFILE_SECTIONS = [section.value for section in ProfileSection]
CONFIDENCE_VALUES = [confidence.value for confidence in EvidenceConfidence]

RESEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "queries": {"type": "array", "items": {"type": "string"}},
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "section": {"type": "string", "enum": PROFILE_SECTIONS},
                    "statement": {"type": "string"},
                    "confidence": {"type": "string", "enum": CONFIDENCE_VALUES},
                    "is_inference": {"type": "boolean"},
                    "citations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string"},
                                "supporting_text": {"type": "string"},
                                "locator": {"type": ["string", "null"]},
                            },
                            "required": ["url", "supporting_text", "locator"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": [
                    "section",
                    "statement",
                    "confidence",
                    "is_inference",
                    "citations",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "queries", "claims"],
    "additionalProperties": False,
}


def normalized_host(url: str | None) -> str | None:
    if not url:
        return None
    host = urlparse(url).hostname
    if not host:
        return None
    return host.removeprefix("www.").lower()


def is_official_source(source_url: str, company_url: str | None) -> bool:
    source_host = normalized_host(source_url)
    company_host = normalized_host(company_url)
    if not source_host or not company_host:
        return False
    return source_host == company_host or source_host.endswith(f".{company_host}")


class OpenAIResearchProvider(ResearchProvider):
    def __init__(self, *, api_key: str | None, model: str) -> None:
        if not api_key:
            raise ResearchProviderConfigurationError(
                "OPENAI_API_KEY is required when RESEARCH_PROVIDER=openai"
            )
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def research(self, research_input: ResearchInput) -> ResearchResult:
        prompt = f"""
Research this company for an enterprise B2B solution consultant.

Company: {research_input.account_name}
Website: {research_input.website or "Unknown"}
Industry: {research_input.industry or "Unknown"}
Region: {research_input.region or "Unknown"}

Use web search. Prefer the company website, official reports, regulators, and reputable news.
Every factual claim must include at least one citation URL returned by web search and a short
supporting excerpt. Separate inference from fact. Do not invent customers, financials, products,
or initiatives. Omit unsupported sections. Treat account notes as context, not public evidence.
""".strip()

        try:
            response = self.client.responses.create(
                model=self.model,
                tools=[{"type": "web_search"}],
                include=["web_search_call.action.sources"],
                input=prompt,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "company_research",
                        "strict": True,
                        "schema": RESEARCH_SCHEMA,
                    }
                },
                max_tool_calls=8,
                store=False,
            )
        except Exception as exc:
            raise ResearchProviderError(f"OpenAI research failed: {exc}") from exc

        try:
            payload = json.loads(response.output_text)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ResearchProviderError("OpenAI returned an invalid research payload") from exc

        raw_response = response.model_dump(mode="json")
        source_records: dict[str, dict] = {}
        for item in raw_response.get("output", []):
            if item.get("type") == "web_search_call":
                for source in (item.get("action") or {}).get("sources", []):
                    url = source.get("url")
                    if url:
                        source_records[url] = source
            if item.get("type") == "message":
                for content in item.get("content", []):
                    for annotation in content.get("annotations", []):
                        if annotation.get("type") == "url_citation" and annotation.get("url"):
                            source_records.setdefault(annotation["url"], annotation)

        if not source_records:
            raise ResearchProviderError("Web research returned no traceable sources")

        sources = tuple(
            SourceArtifact(
                key=url,
                title=record.get("title") or normalized_host(url) or "Web source",
                source_type=(
                    SourceType.COMPANY_WEBSITE
                    if is_official_source(url, research_input.website)
                    else SourceType.WEB
                ),
                url=url,
                publisher=normalized_host(url),
                is_official=is_official_source(url, research_input.website),
                metadata={"openai_web_search": True},
            )
            for url, record in source_records.items()
        )

        claims: list[ClaimArtifact] = []
        for claim in payload.get("claims", []):
            citations: list[EvidenceArtifact] = []
            for citation in claim.get("citations", []):
                url = citation.get("url")
                supporting_text = (citation.get("supporting_text") or "").strip()
                if not url or url not in source_records or not supporting_text:
                    continue
                citations.append(
                    EvidenceArtifact(
                        source_key=url,
                        supporting_text=supporting_text[:1200],
                        confidence=EvidenceConfidence(claim["confidence"]),
                        verification_status=EvidenceVerification.AI_EXTRACTED,
                        locator=citation.get("locator"),
                    )
                )
            if not citations:
                continue
            claims.append(
                ClaimArtifact(
                    section=ProfileSection(claim["section"]),
                    statement=claim["statement"].strip(),
                    confidence=EvidenceConfidence(claim["confidence"]),
                    evidence=tuple(citations),
                    is_inference=claim["is_inference"],
                )
            )

        if not claims:
            raise ResearchProviderError("Web research returned no claims with matching citations")

        return ResearchResult(
            summary=payload["summary"].strip(),
            sources=sources,
            claims=tuple(claims),
            is_simulated=False,
            provider_response_id=response.id,
            query_plan={"mode": "live_web", "queries": payload.get("queries", [])},
        )
