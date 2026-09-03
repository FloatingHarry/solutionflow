from enum import StrEnum


class DeploymentOption(StrEnum):
    SAAS_API = "saas_api"
    EU_CLOUD = "eu_cloud"
    PRIVATE_ON_PREMISE = "private_on_premise"


class SolutionProposalStatus(StrEnum):
    DRAFT = "draft"
    NEEDS_REVISION = "needs_revision"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class SolutionReviewDecision(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    NEEDS_REVISION = "needs_revision"
