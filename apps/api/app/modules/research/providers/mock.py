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
    ResearchResult,
    SourceArtifact,
)


class MockResearchProvider(ResearchProvider):
    """Deterministic provider that never presents generated content as public research."""

    def research(self, research_input: ResearchInput) -> ResearchResult:
        source_key = "account-input"
        input_lines = [f"Company name: {research_input.account_name}"]
        if research_input.website:
            input_lines.append(f"Website: {research_input.website}")
        if research_input.industry:
            input_lines.append(f"Industry: {research_input.industry}")
        if research_input.region:
            input_lines.append(f"Region: {research_input.region}")
        if research_input.notes:
            input_lines.append(f"Internal notes: {research_input.notes}")

        source = SourceArtifact(
            key=source_key,
            title="Account-provided profile",
            source_type=SourceType.ACCOUNT_INPUT,
            url=research_input.website,
            publisher="SolutionFlow user input",
            content_excerpt="\n".join(input_lines),
            is_official=False,
            metadata={"simulation": True},
        )

        claims: list[ClaimArtifact] = [
            ClaimArtifact(
                section=ProfileSection.COMPANY_OVERVIEW,
                statement=(
                    f"{research_input.account_name} is the company named in this account workspace."
                ),
                confidence=EvidenceConfidence.HIGH,
                evidence=(
                    EvidenceArtifact(
                        source_key=source_key,
                        supporting_text=f"Company name: {research_input.account_name}",
                        confidence=EvidenceConfidence.HIGH,
                        verification_status=EvidenceVerification.DIRECT_INPUT,
                        locator="Account profile · Company name",
                    ),
                ),
            )
        ]

        if research_input.industry:
            claims.append(
                ClaimArtifact(
                    section=ProfileSection.PRODUCTS_SERVICES,
                    statement=f"The account is categorized under {research_input.industry}.",
                    confidence=EvidenceConfidence.MEDIUM,
                    evidence=(
                        EvidenceArtifact(
                            source_key=source_key,
                            supporting_text=f"Industry: {research_input.industry}",
                            confidence=EvidenceConfidence.MEDIUM,
                            verification_status=EvidenceVerification.DIRECT_INPUT,
                            locator="Account profile · Industry",
                        ),
                    ),
                )
            )

        if research_input.region:
            claims.append(
                ClaimArtifact(
                    section=ProfileSection.MARKET_GEOGRAPHY,
                    statement=f"The account is associated with {research_input.region}.",
                    confidence=EvidenceConfidence.MEDIUM,
                    evidence=(
                        EvidenceArtifact(
                            source_key=source_key,
                            supporting_text=f"Region: {research_input.region}",
                            confidence=EvidenceConfidence.MEDIUM,
                            verification_status=EvidenceVerification.DIRECT_INPUT,
                            locator="Account profile · Region",
                        ),
                    ),
                )
            )

        if research_input.notes:
            claims.append(
                ClaimArtifact(
                    section=ProfileSection.POTENTIAL_STRATEGIC_PRIORITIES,
                    statement=(
                        "Internal account notes provide a possible research direction that still "
                        "requires external validation."
                    ),
                    confidence=EvidenceConfidence.LOW,
                    is_inference=True,
                    evidence=(
                        EvidenceArtifact(
                            source_key=source_key,
                            supporting_text=f"Internal notes: {research_input.notes}",
                            confidence=EvidenceConfidence.LOW,
                            verification_status=EvidenceVerification.DIRECT_INPUT,
                            locator="Account profile · Internal notes",
                        ),
                    ),
                )
            )

        return ResearchResult(
            summary=(
                "Simulation result generated only from account-provided fields. Configure an "
                "OpenAI API key and select the OpenAI provider to run live web research."
            ),
            sources=(source,),
            claims=tuple(claims),
            is_simulated=True,
            query_plan={
                "mode": "simulation",
                "queries": [f"{research_input.account_name} company profile"],
            },
        )
