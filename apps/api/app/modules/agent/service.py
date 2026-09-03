import json
import uuid
from datetime import UTC, datetime
from typing import Any

from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.accounts import service as accounts_service
from app.modules.accounts.enums import ActorType, StageName, StageStatus
from app.modules.agent.enums import AgentActionStatus, AgentProvider, AgentRunStatus
from app.modules.agent.models import AgentRun
from app.modules.business_case import service as business_case_service
from app.modules.business_case.models import BusinessCase
from app.modules.deployment import service as deployment_service
from app.modules.deployment.models import DeploymentPlan
from app.modules.discovery import service as discovery_service
from app.modules.discovery.models import ConfirmedNeed, OpportunityHypothesis
from app.modules.discovery.schemas import DiscoveryGenerateRequest
from app.modules.poc import service as poc_service
from app.modules.poc.models import PocDecision, PocMetric, PocPlan
from app.modules.research import service as research_service
from app.modules.research.enums import ResearchProviderName
from app.modules.research.models import ResearchRun
from app.modules.research.schemas import ResearchRunCreate
from app.modules.solutions import service as solutions_service
from app.modules.solutions.models import SolutionMatch, SolutionProposal
from app.modules.solutions.schemas import SolutionMatchRequest, SolutionProposalCreate


class AgentRunNotFoundError(Exception):
    pass


class AgentConflictError(Exception):
    pass


class AgentActionError(Exception):
    pass


class ArchivedAccountError(Exception):
    pass


class OpenAIAgentError(Exception):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


STAGE_PATHS = {
    StageName.RESEARCH: "research",
    StageName.OPPORTUNITY: "discovery",
    StageName.DISCOVERY: "discovery",
    StageName.SOLUTION: "solutions",
    StageName.POC: "poc",
    StageName.EVALUATION: "poc",
    StageName.BUSINESS_CASE: "business-case",
    StageName.DEPLOYMENT: "deployment",
}

CAPABILITIES = [
    "Inspect account context and workflow state",
    "Find missing evidence and blocked gates",
    "Prepare the safest next workflow action",
    "Generate stage artifacts after human approval",
    "Preserve every run and tool result in the audit trail",
]

STARTER_PROMPTS = [
    "What should I do next for this account?",
    "Find the most important missing evidence.",
    "Prepare the current stage for review.",
]

ACTION_KEYS = [
    "run_research",
    "open_research_review",
    "monitor_research",
    "generate_hypotheses",
    "open_discovery_interview",
    "open_discovery_review",
    "generate_solution_matches",
    "generate_solution_proposal",
    "open_solution_review",
    "generate_poc_plan",
    "open_poc_review",
    "open_poc_evaluation",
    "generate_business_case",
    "open_business_case_review",
    "generate_deployment_plan",
    "open_deployment_readiness",
    "workflow_complete",
]


def configured_provider() -> AgentProvider:
    requested = settings.agent_provider.strip().lower()
    if requested == AgentProvider.GUIDED.value:
        return AgentProvider.GUIDED
    if requested == AgentProvider.OPENAI.value:
        return AgentProvider.OPENAI if settings.openai_api_key else AgentProvider.GUIDED
    return AgentProvider.OPENAI if settings.openai_api_key else AgentProvider.GUIDED


def get_run_or_raise(session: Session, run_id: uuid.UUID) -> AgentRun:
    run = session.get(AgentRun, run_id)
    if run is None:
        raise AgentRunNotFoundError
    return run


def list_runs(session: Session, account_id: uuid.UUID, limit: int = 12) -> list[AgentRun]:
    accounts_service.get_account_or_raise(session, account_id)
    return list(
        session.scalars(
            select(AgentRun)
            .where(AgentRun.account_id == account_id)
            .order_by(AgentRun.created_at.desc())
            .limit(limit)
        ).all()
    )


def _count(session: Session, model: type, account_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count()).select_from(model).where(model.account_id == account_id)
        )
        or 0
    )


def _latest(session: Session, model: type, account_id: uuid.UUID):
    return session.scalar(
        select(model).where(model.account_id == account_id).order_by(model.created_at.desc())
    )


def _collect_context(session: Session, account_id: uuid.UUID) -> dict[str, Any]:
    account, states = accounts_service.get_workflow(session, account_id)
    state_by_stage = {state.stage: state for state in states}
    completed = sum(state.status == StageStatus.COMPLETED for state in states)

    latest_research = _latest(session, ResearchRun, account_id)
    hypotheses = _count(session, OpportunityHypothesis, account_id)
    confirmed_needs = _count(session, ConfirmedNeed, account_id)
    matches = _count(session, SolutionMatch, account_id)
    proposals = list(
        session.scalars(
            select(SolutionProposal)
            .where(SolutionProposal.account_id == account_id)
            .order_by(SolutionProposal.created_at.desc())
        ).all()
    )
    poc_plan = _latest(session, PocPlan, account_id)
    pending_metrics = 0
    latest_decision = None
    if poc_plan is not None:
        pending_metrics = int(
            session.scalar(
                select(func.count())
                .select_from(PocMetric)
                .where(PocMetric.poc_plan_id == poc_plan.id, PocMetric.actual_value.is_(None))
            )
            or 0
        )
        latest_decision = session.scalar(
            select(PocDecision)
            .where(PocDecision.poc_plan_id == poc_plan.id)
            .order_by(PocDecision.created_at.desc())
        )
    business_case = _latest(session, BusinessCase, account_id)
    deployment = _latest(session, DeploymentPlan, account_id)

    context = {
        "account": {
            "id": str(account.id),
            "name": account.name,
            "website": account.website,
            "industry": account.industry,
            "region": account.region,
            "notes_present": bool(account.notes),
            "archived": account.archived_at is not None,
        },
        "workflow": {
            "current_stage": account.current_stage.value,
            "completed_stages": completed,
            "total_stages": len(states),
            "stages": [
                {"stage": state.stage.value, "status": state.status.value} for state in states
            ],
        },
        "artifacts": {
            "research_status": latest_research.status.value if latest_research else None,
            "hypothesis_count": hypotheses,
            "confirmed_need_count": confirmed_needs,
            "solution_match_count": matches,
            "solution_proposal_statuses": [proposal.status.value for proposal in proposals],
            "poc_plan_status": poc_plan.status.value if poc_plan else None,
            "poc_metrics_missing_results": pending_metrics,
            "poc_decision": latest_decision.decision.value if latest_decision else None,
            "business_case_status": business_case.status.value if business_case else None,
            "deployment_status": deployment.status.value if deployment else None,
            "deployment_readiness": deployment.readiness_score if deployment else None,
        },
    }
    context["next_action"] = _recommended_action(context, state_by_stage)
    return context


def _action(
    account_id: str,
    stage: StageName,
    key: str,
    title: str,
    description: str,
    reason: str,
    *,
    requires_approval: bool,
) -> dict[str, Any]:
    return {
        "key": key,
        "title": title,
        "description": description,
        "reason": reason,
        "target_path": f"/accounts/{account_id}/{STAGE_PATHS[stage]}",
        "requires_approval": requires_approval,
    }


def _recommended_action(
    context: dict[str, Any], state_by_stage: dict[StageName, Any]
) -> dict[str, Any]:
    account_id = context["account"]["id"]
    stage = StageName(context["workflow"]["current_stage"])
    artifacts = context["artifacts"]
    if all(state.status == StageStatus.COMPLETED for state in state_by_stage.values()):
        return {
            "key": "workflow_complete",
            "title": "Workflow complete",
            "description": "All eight controlled stages are complete. Review the audit trail.",
            "reason": "No incomplete workflow stage remains.",
            "target_path": f"/accounts/{account_id}/activity",
            "requires_approval": False,
        }

    if stage == StageName.RESEARCH:
        research_status = artifacts["research_status"]
        if research_status in {"queued", "running"}:
            return _action(
                account_id,
                stage,
                "monitor_research",
                "Monitor active research",
                "Research is still running. Open the workspace to monitor it before deciding.",
                "The current research run must finish before another action is safe.",
                requires_approval=False,
            )
        if research_status == "needs_review":
            return _action(
                account_id,
                stage,
                "open_research_review",
                "Review sourced research",
                "Inspect every claim and citation, then approve or reject the research.",
                "Research exists, but the human evidence gate is still open.",
                requires_approval=False,
            )
        return _action(
            account_id,
            stage,
            "run_research",
            "Run account research",
            "Create a source-backed research run. OpenAI web research is used when configured; "
            "otherwise the result is clearly marked as simulated.",
            "No reviewable research artifact exists for the active stage.",
            requires_approval=True,
        )

    if stage == StageName.OPPORTUNITY:
        if artifacts["hypothesis_count"] == 0:
            return _action(
                account_id,
                stage,
                "generate_hypotheses",
                "Generate opportunity hypotheses",
                "Turn approved research claims into editable, evidence-linked hypotheses and "
                "starter questions.",
                "The research gate is complete, but no opportunity hypotheses exist.",
                requires_approval=True,
            )
        return _action(
            account_id,
            stage,
            "open_discovery_review",
            "Review opportunity hypotheses",
            "Accept, reject, or mark each hypothesis for validation before discovery continues.",
            "Hypotheses exist and require a human decision.",
            requires_approval=False,
        )

    if stage == StageName.DISCOVERY:
        if artifacts["confirmed_need_count"] == 0:
            return _action(
                account_id,
                stage,
                "open_discovery_interview",
                "Capture customer evidence",
                "Record customer answers and confirm at least one need from direct evidence.",
                "The agent must not invent customer facts or confirm needs without an answer.",
                requires_approval=False,
            )
        return _action(
            account_id,
            stage,
            "open_discovery_review",
            "Complete discovery review",
            "Review confirmed needs and approve the discovery package.",
            "Customer evidence exists; the remaining gate is a human review.",
            requires_approval=False,
        )

    if stage == StageName.SOLUTION:
        if artifacts["solution_match_count"] == 0:
            return _action(
                account_id,
                stage,
                "generate_solution_matches",
                "Generate explainable matches",
                "Score catalog patterns against confirmed customer needs and preserve the "
                "rationale.",
                "Discovery is approved, but no solution matches exist.",
                requires_approval=True,
            )
        if not artifacts["solution_proposal_statuses"]:
            return _action(
                account_id,
                stage,
                "generate_solution_proposal",
                "Draft the strongest proposal",
                "Use the highest-ranked match and its linked needs to create an editable proposal.",
                "Matches exist, but no proposal has been prepared.",
                requires_approval=True,
            )
        return _action(
            account_id,
            stage,
            "open_solution_review",
            "Review the solution proposal",
            "Validate architecture, deployment, security, risk, and impact before accepting it.",
            "A proposal exists and requires a human solution decision.",
            requires_approval=False,
        )

    if stage == StageName.POC:
        if artifacts["poc_plan_status"] is None:
            return _action(
                account_id,
                stage,
                "generate_poc_plan",
                "Generate a bounded POC plan",
                "Create scope, timeline, dataset, architecture, risks, and measurable success "
                "criteria from the accepted solution.",
                "An accepted solution exists, but no POC plan has been prepared.",
                requires_approval=True,
            )
        return _action(
            account_id,
            stage,
            "open_poc_review",
            "Review the POC plan",
            "Check the plan boundaries and approve it before recording results.",
            "The POC draft exists and requires human approval.",
            requires_approval=False,
        )

    if stage == StageName.EVALUATION:
        return _action(
            account_id,
            stage,
            "open_poc_evaluation",
            "Record evaluation evidence",
            "Enter actual metric results and make a Proceed, Iterate, or Reject decision.",
            "Evaluation outcomes must come from observed POC evidence, not agent invention.",
            requires_approval=False,
        )

    if stage == StageName.BUSINESS_CASE:
        if artifacts["business_case_status"] is None:
            return _action(
                account_id,
                stage,
                "generate_business_case",
                "Generate the business case",
                "Create an editable ROI scenario, deployment comparison, risks, and account brief "
                "from approved evidence.",
                "A Proceed decision exists, but no business case has been generated.",
                requires_approval=True,
            )
        return _action(
            account_id,
            stage,
            "open_business_case_review",
            "Review scenario assumptions",
            "Validate the estimated inputs and approve or revise the business case.",
            "The scenario is an estimate and requires a human commercial decision.",
            requires_approval=False,
        )

    if artifacts["deployment_status"] is None:
        return _action(
            account_id,
            StageName.DEPLOYMENT,
            "generate_deployment_plan",
            "Generate the operating plan",
            "Create the rollout plan and six owner-and-evidence readiness checks.",
            "The business case is approved, but no deployment plan exists.",
            requires_approval=True,
        )
    return _action(
        account_id,
        StageName.DEPLOYMENT,
        "open_deployment_readiness",
        "Complete readiness evidence",
        "Assign owners, attach evidence, clear blockers, and complete the final human gate.",
        "Production readiness cannot be claimed without accountable owner evidence.",
        requires_approval=False,
    )


def _guided_plan(context: dict[str, Any], goal: str) -> dict[str, Any]:
    account = context["account"]
    workflow = context["workflow"]
    artifacts = context["artifacts"]
    action = context["next_action"]
    profile_fields = [account["website"], account["industry"], account["region"]]
    known_fields = sum(bool(value) for value in profile_fields)
    observations = [
        f"{workflow['completed_stages']} of {workflow['total_stages']} workflow stages "
        "are complete.",
        f"The active stage is {workflow['current_stage'].replace('_', ' ')}.",
        f"{known_fields} of 3 core profile fields are available for planning.",
    ]
    if artifacts["confirmed_need_count"]:
        observations.append(
            f"{artifacts['confirmed_need_count']} customer-confirmed need record(s) are available."
        )
    if artifacts["deployment_readiness"] is not None:
        observations.append(
            f"Deployment readiness is recorded at {artifacts['deployment_readiness']}%."
        )
    return {
        "summary": (
            f"I mapped “{goal}” to the current account state. {action['title']} is the safest "
            "next move; controlled writes remain behind your approval."
        ),
        "observations": observations[:5],
        "plan": [
            "Inspect the account profile, workflow state, and stored stage artifacts.",
            f"Focus on the active {workflow['current_stage'].replace('_', ' ')} gate.",
            action["description"],
            (
                "Pause for your approval before creating records."
                if action["requires_approval"]
                else "Hand the remaining evidence or decision step back to a human."
            ),
        ],
        "question": None,
        "action_key": action["key"],
        "trace": [
            {"tool": "inspect_account", "status": "completed"},
            {"tool": "inspect_workflow", "status": "completed"},
            {"tool": "inspect_stage_artifacts", "status": "completed"},
        ],
    }


LIVE_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "observations": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 5,
        },
        "plan": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 6,
        },
        "question": {"type": ["string", "null"]},
        "action_key": {"type": "string", "enum": ACTION_KEYS},
    },
    "required": ["summary", "observations", "plan", "question", "action_key"],
    "additionalProperties": False,
}

READ_TOOLS = [
    {
        "type": "function",
        "name": "inspect_account",
        "description": "Read the account profile and whether it is archived.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "inspect_workflow",
        "description": "Read all eight workflow stage states and the active stage.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "inspect_stage_artifacts",
        "description": (
            "Read stored research, discovery, solution, POC, business-case, and deployment "
            "artifact summaries."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


class LivePlan(BaseModel):
    summary: str
    observations: list[str]
    plan: list[str]
    question: str | None
    action_key: str


def _openai_plan(context: dict[str, Any], goal: str) -> dict[str, Any]:
    client = OpenAI(api_key=settings.openai_api_key)
    inputs: list[Any] = [
        {
            "role": "developer",
            "content": (
                "You are SolutionFlow's Account Agent. Plan multi-step enterprise solution work "
                "from stored evidence only. First call the three read tools. Never invent customer "
                "facts, approvals, POC results, ROI, or production readiness. Choose one "
                "action_key. "
                "Any record creation is only a proposal: the application will pause for human "
                "approval. Reply in the user's language. Do not reveal hidden reasoning."
            ),
        },
        {
            "role": "user",
            "content": f"Account id: {context['account']['id']}\nGoal: {goal}",
        },
    ]

    trace: list[dict[str, Any]] = []
    provider_response_id = None
    tool_results = {
        "inspect_account": context["account"],
        "inspect_workflow": context["workflow"],
        "inspect_stage_artifacts": {
            **context["artifacts"],
            "allowed_next_action": context["next_action"],
        },
    }
    try:
        for _turn in range(4):
            response = client.responses.create(
                model=settings.openai_agent_model,
                input=inputs,
                tools=READ_TOOLS,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "account_agent_plan",
                        "strict": True,
                        "schema": LIVE_PLAN_SCHEMA,
                    }
                },
                max_output_tokens=1200,
                store=False,
            )
            provider_response_id = response.id
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                plan = LivePlan.model_validate_json(response.output_text)
                return {
                    **plan.model_dump(),
                    "trace": trace,
                    "provider_response_id": provider_response_id,
                }

            inputs.extend(response.output)
            for call in calls:
                if call.name not in tool_results:
                    raise OpenAIAgentError(f"Unknown read tool requested: {call.name}")
                result = tool_results[call.name]
                trace.append(
                    {
                        "tool": call.name,
                        "status": "completed",
                        "result": result,
                    }
                )
                inputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(result),
                    }
                )
    except Exception as exc:
        raise OpenAIAgentError(f"OpenAI agent planning failed: {exc}") from exc
    raise OpenAIAgentError("OpenAI agent exceeded the four-turn planning limit")


def create_run(session: Session, account_id: uuid.UUID, goal: str) -> AgentRun:
    account = accounts_service.get_account_or_raise(session, account_id)
    if account.archived_at is not None:
        raise ArchivedAccountError

    context = _collect_context(session, account_id)
    provider = configured_provider()
    fallback_error = None
    if provider == AgentProvider.OPENAI:
        try:
            plan = _openai_plan(context, goal)
        except OpenAIAgentError as exc:
            fallback_error = str(exc)[:1000]
            provider = AgentProvider.GUIDED
            plan = _guided_plan(context, goal)
    else:
        plan = _guided_plan(context, goal)

    action = context["next_action"]
    if plan.get("action_key") != action["key"]:
        plan.setdefault("trace", []).append(
            {
                "tool": "validate_workflow_boundary",
                "status": "corrected",
                "requested_action": plan.get("action_key"),
                "allowed_action": action["key"],
            }
        )

    awaits_approval = bool(action["requires_approval"])
    now = utc_now()
    run = AgentRun(
        account_id=account_id,
        goal=goal,
        status=(AgentRunStatus.AWAITING_APPROVAL if awaits_approval else AgentRunStatus.COMPLETED),
        provider=provider,
        model=settings.openai_agent_model if provider == AgentProvider.OPENAI else None,
        provider_response_id=plan.get("provider_response_id"),
        stage_snapshot=context["workflow"]["current_stage"],
        summary=str(plan["summary"])[:8000],
        observations=[str(item)[:1000] for item in plan["observations"][:5]],
        plan=[str(item)[:1000] for item in plan["plan"][:6]],
        question=str(plan["question"])[:2000] if plan.get("question") else None,
        trace=plan.get("trace", []),
        action_key=action["key"],
        action_title=action["title"],
        action_description=action["description"],
        action_reason=action["reason"],
        action_target_path=action["target_path"],
        action_requires_approval=awaits_approval,
        action_status=(AgentActionStatus.PENDING if awaits_approval else AgentActionStatus.NONE),
        error_message=(
            f"Live planning was unavailable; guided planning completed instead. {fallback_error}"
            if fallback_error
            else None
        ),
        completed_at=None if awaits_approval else now,
    )
    session.add(run)
    session.flush()
    accounts_service.add_activity(
        session,
        account_id=account_id,
        event_type="agent.run_created",
        entity_type="agent_run",
        entity_id=str(run.id),
        summary=f"Account Agent planned next action: {action['title']}",
        actor_type=ActorType.SYSTEM,
        metadata={
            "goal": goal,
            "provider": provider.value,
            "stage": run.stage_snapshot,
            "action": action["key"],
            "requires_approval": awaits_approval,
        },
    )
    session.commit()
    session.refresh(run)
    return run


def _execute_action(session: Session, run: AgentRun) -> dict[str, Any]:
    account_id = run.account_id
    if run.action_key == "run_research":
        provider = (
            ResearchProviderName.OPENAI if settings.openai_api_key else ResearchProviderName.MOCK
        )
        research_run = research_service.create_research_run(
            session, account_id, ResearchRunCreate(provider=provider)
        )
        research_run = research_service.execute_research(session, research_run.id)
        return {
            "entity_type": "research_run",
            "entity_id": str(research_run.id),
            "status": research_run.status.value,
            "provider": research_run.provider.value,
        }

    if run.action_key == "generate_hypotheses":
        hypotheses = discovery_service.generate_from_research(
            session, account_id, DiscoveryGenerateRequest(max_hypotheses=3)
        )
        return {
            "entity_type": "opportunity_hypothesis",
            "count": len(hypotheses),
            "entity_ids": [str(item.id) for item in hypotheses],
        }

    if run.action_key == "generate_solution_matches":
        matches = solutions_service.generate_matches(
            session, account_id, SolutionMatchRequest(top_per_need=3)
        )
        return {
            "entity_type": "solution_match",
            "count": len(matches),
            "entity_ids": [str(item.id) for item in matches],
        }

    if run.action_key == "generate_solution_proposal":
        _account, _catalog, _needs, matches, _proposals, _approved = (
            solutions_service.get_solution_workspace(session, account_id)
        )
        if not matches:
            raise AgentActionError("Generate solution matches before drafting a proposal")
        top = matches[0]
        need_ids = list(
            dict.fromkeys(
                item.confirmed_need_id
                for item in matches
                if item.solution_template_id == top.solution_template_id
            )
        )
        deployment_option = top.solution_template.deployment_options[0]
        proposal = solutions_service.create_proposal(
            session,
            account_id,
            SolutionProposalCreate(
                solution_template_id=top.solution_template_id,
                need_ids=need_ids,
                deployment_option=deployment_option,
            ),
        )
        return {
            "entity_type": "solution_proposal",
            "entity_id": str(proposal.id),
            "status": proposal.status.value,
            "title": proposal.title,
        }

    if run.action_key == "generate_poc_plan":
        plan = poc_service.generate_plan(session, account_id)
        return {
            "entity_type": "poc_plan",
            "entity_id": str(plan.id),
            "status": plan.status.value,
        }

    if run.action_key == "generate_business_case":
        case = business_case_service.generate_case(session, account_id)
        return {
            "entity_type": "business_case",
            "entity_id": str(case.id),
            "status": case.status.value,
        }

    if run.action_key == "generate_deployment_plan":
        plan = deployment_service.generate_plan(session, account_id)
        return {
            "entity_type": "deployment_plan",
            "entity_id": str(plan.id),
            "status": plan.status.value,
            "readiness_score": plan.readiness_score,
        }

    raise AgentActionError("This recommendation is navigational and has no executable side effect")


def approve_action(session: Session, run_id: uuid.UUID, note: str | None = None) -> AgentRun:
    run = get_run_or_raise(session, run_id)
    account = accounts_service.get_account_or_raise(session, run.account_id)
    if account.archived_at is not None:
        raise ArchivedAccountError
    if (
        run.status != AgentRunStatus.AWAITING_APPROVAL
        or run.action_status != AgentActionStatus.PENDING
    ):
        raise AgentConflictError("This agent action is no longer awaiting approval")

    try:
        result = _execute_action(session, run)
    except Exception as exc:
        session.rollback()
        run = get_run_or_raise(session, run_id)
        run.status = AgentRunStatus.FAILED
        run.action_status = AgentActionStatus.FAILED
        run.error_message = str(exc)[:2000]
        run.updated_at = utc_now()
        run.completed_at = utc_now()
        session.commit()
        raise AgentActionError(str(exc)) from exc

    run = get_run_or_raise(session, run_id)
    run.status = AgentRunStatus.ACTION_COMPLETED
    run.action_status = AgentActionStatus.EXECUTED
    run.action_result = result
    run.approval_note = note
    run.updated_at = utc_now()
    run.completed_at = utc_now()
    accounts_service.add_activity(
        session,
        account_id=run.account_id,
        event_type="agent.action_executed",
        entity_type="agent_run",
        entity_id=str(run.id),
        summary=f"Approved Agent action executed: {run.action_title}",
        actor_type=ActorType.SYSTEM,
        metadata={"action": run.action_key, "result": result, "approval_note": note},
    )
    session.commit()
    session.refresh(run)
    return run


def reject_action(session: Session, run_id: uuid.UUID, note: str | None = None) -> AgentRun:
    run = get_run_or_raise(session, run_id)
    if (
        run.status != AgentRunStatus.AWAITING_APPROVAL
        or run.action_status != AgentActionStatus.PENDING
    ):
        raise AgentConflictError("This agent action is no longer awaiting approval")
    run.status = AgentRunStatus.REJECTED
    run.action_status = AgentActionStatus.REJECTED
    run.approval_note = note
    run.updated_at = utc_now()
    run.completed_at = utc_now()
    accounts_service.add_activity(
        session,
        account_id=run.account_id,
        event_type="agent.action_rejected",
        entity_type="agent_run",
        entity_id=str(run.id),
        summary=f"Agent action rejected: {run.action_title}",
        actor_type=ActorType.SYSTEM,
        metadata={"action": run.action_key, "approval_note": note},
    )
    session.commit()
    session.refresh(run)
    return run
