import uuid

DEMO_SOLUTION_CATALOG = [
    {
        "id": uuid.UUID("10000000-0000-4000-8000-000000000001"),
        "slug": "enterprise-knowledge-assistant",
        "name": "Enterprise Knowledge Assistant",
        "description": (
            "A retrieval-augmented assistant for finding and answering questions from "
            "approved internal knowledge with citations."
        ),
        "target_pain_points": [
            "slow internal knowledge retrieval",
            "fragmented policy and procedure documents",
            "inconsistent answers without citations",
        ],
        "target_industries": ["cross-industry", "professional services", "regulated industries"],
        "required_data": [
            "approved internal documents",
            "document access-control metadata",
            "representative employee questions",
        ],
        "architecture": (
            "Document ingestion → access-aware indexing → hybrid retrieval → grounded generation "
            "→ citation and feedback layer"
        ),
        "deployment_options": ["saas_api", "eu_cloud", "private_on_premise"],
        "success_metrics": [
            "task success rate",
            "citation accuracy",
            "median time to answer",
        ],
        "known_limitations": [
            "answer quality depends on source freshness",
            "document permissions must be mapped correctly",
        ],
        "estimated_cost_model": "Usage-based inference plus indexed document volume.",
        "example_use_cases": [
            "policy assistant",
            "technical support knowledge search",
            "employee onboarding Q&A",
        ],
        "match_keywords": [
            "knowledge",
            "policy",
            "search",
            "retrieval",
            "documents",
            "citations",
            "answer",
        ],
    },
    {
        "id": uuid.UUID("10000000-0000-4000-8000-000000000002"),
        "slug": "customer-service-copilot",
        "name": "Customer Service Copilot",
        "description": (
            "An agent-assist workspace that summarizes customer context, recommends responses, "
            "and guides service workflows."
        ),
        "target_pain_points": [
            "high support handling time",
            "inconsistent service responses",
            "manual escalation and agent handoffs",
        ],
        "target_industries": ["retail", "telecommunications", "financial services"],
        "required_data": [
            "resolved support conversations",
            "service knowledge articles",
            "ticket and escalation metadata",
        ],
        "architecture": (
            "CRM and ticket context → intent and summary services → grounded response assistant "
            "→ agent approval → service analytics"
        ),
        "deployment_options": ["saas_api", "eu_cloud"],
        "success_metrics": [
            "average handling time",
            "first-contact resolution",
            "agent acceptance rate",
        ],
        "known_limitations": [
            "customer-facing messages require agent approval",
            "CRM integration effort varies by platform",
        ],
        "estimated_cost_model": "Per assisted conversation plus integration and monitoring costs.",
        "example_use_cases": [
            "ticket summarization",
            "next-best response",
            "escalation guidance",
        ],
        "match_keywords": [
            "customer",
            "support",
            "service",
            "agent",
            "ticket",
            "response",
            "escalation",
        ],
    },
    {
        "id": uuid.UUID("10000000-0000-4000-8000-000000000003"),
        "slug": "sales-account-copilot",
        "name": "Sales / Account Copilot",
        "description": (
            "A research and preparation assistant for account teams that structures evidence, "
            "stakeholder context, and opportunity plans."
        ),
        "target_pain_points": [
            "slow account research and meeting preparation",
            "fragmented stakeholder and opportunity context",
            "manual proposal preparation",
        ],
        "target_industries": ["B2B technology", "professional services", "industrial sales"],
        "required_data": [
            "account and opportunity records",
            "approved product materials",
            "meeting notes and research sources",
        ],
        "architecture": (
            "CRM and research connectors → account evidence graph → planning copilot → "
            "human-approved account brief and proposal workspace"
        ),
        "deployment_options": ["saas_api", "eu_cloud"],
        "success_metrics": [
            "research preparation time",
            "evidence coverage",
            "seller adoption rate",
        ],
        "known_limitations": [
            "recommendations depend on CRM data quality",
            "copilot must not autonomously contact customers",
        ],
        "estimated_cost_model": "Per account workspace plus connector and research usage.",
        "example_use_cases": [
            "account brief generation",
            "meeting preparation",
            "opportunity plan drafting",
        ],
        "match_keywords": [
            "sales",
            "account",
            "research",
            "meeting",
            "stakeholder",
            "proposal",
            "crm",
        ],
    },
    {
        "id": uuid.UUID("10000000-0000-4000-8000-000000000004"),
        "slug": "document-intelligence",
        "name": "Document Intelligence",
        "description": (
            "A human-in-the-loop document processing service for extraction, classification, "
            "validation, and workflow automation."
        ),
        "target_pain_points": [
            "manual document and spreadsheet handoffs",
            "slow data extraction and validation",
            "repetitive routing and back-office workflows",
        ],
        "target_industries": ["logistics", "insurance", "financial operations", "manufacturing"],
        "required_data": [
            "representative document samples",
            "target extraction schema",
            "exception and validation rules",
        ],
        "architecture": (
            "Secure intake → OCR and layout parsing → structured extraction → business-rule "
            "validation → human exception queue → downstream system export"
        ),
        "deployment_options": ["saas_api", "eu_cloud", "private_on_premise"],
        "success_metrics": [
            "field extraction accuracy",
            "straight-through processing rate",
            "processing lead time",
        ],
        "known_limitations": [
            "new layouts require evaluation samples",
            "low-confidence fields require human review",
        ],
        "estimated_cost_model": "Per processed page plus exception-review and hosting costs.",
        "example_use_cases": [
            "invoice and order extraction",
            "shipping document processing",
            "spreadsheet-to-system workflow automation",
        ],
        "match_keywords": [
            "document",
            "spreadsheet",
            "handoff",
            "extraction",
            "routing",
            "workflow",
            "manual",
        ],
    },
]
