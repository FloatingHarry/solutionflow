import time
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.accounts import service as accounts_service
from app.modules.accounts.enums import STAGE_ORDER, StageName, StageStatus
from app.modules.accounts.models import Account, AccountStageState
from app.modules.accounts.schemas import AccountCreate
from app.modules.business_case import service as business_case_service
from app.modules.business_case.enums import BusinessCaseReviewDecision
from app.modules.business_case.schemas import BusinessCaseReviewRequest
from app.modules.deployment import service as deployment_service
from app.modules.deployment.enums import ChecklistItemStatus
from app.modules.deployment.models import DeploymentPlan
from app.modules.deployment.schemas import (
    DeploymentChecklistUpdate,
    DeploymentCompleteRequest,
)
from app.modules.discovery import service as discovery_service
from app.modules.discovery.enums import HypothesisReviewDecision, HypothesisStatus
from app.modules.discovery.models import OpportunityHypothesis
from app.modules.discovery.schemas import (
    ConfirmedNeedCreate,
    CustomerAnswerCreate,
    DiscoveryGenerateRequest,
    DiscoveryReviewRequest,
    HypothesisReviewRequest,
)
from app.modules.evaluation.demo_data import DEMO_SCENARIOS
from app.modules.evaluation.models import SystemEvaluationRun, SystemEvaluationTask
from app.modules.poc import service as poc_service
from app.modules.poc.enums import MetricOperator, PocDecisionType, PocReviewDecision
from app.modules.poc.schemas import PocDecisionCreate, PocMetricUpdate, PocReviewRequest
from app.modules.research import service as research_service
from app.modules.research.enums import (
    ClaimReviewStatus,
    ResearchProviderName,
    ResearchStatus,
    ReviewDecision,
)
from app.modules.research.models import CompanyProfile, ProfileClaim, ResearchRun
from app.modules.research.schemas import ResearchReviewRequest, ResearchRunCreate
from app.modules.solutions import service as solutions_service
from app.modules.solutions.enums import (
    DeploymentOption,
    SolutionProposalStatus,
    SolutionReviewDecision,
)
from app.modules.solutions.models import SolutionProposal
from app.modules.solutions.schemas import (
    SolutionMatchRequest,
    SolutionProposalCreate,
    SolutionReviewRequest,
)

METHODOLOGY = (
    "A deterministic regression suite evaluates 35 traceability and workflow checks across five "
    "synthetic demo accounts. It validates stored evidence, citations, human gates, solution "
    "lineage, unsupported-claim controls, and end-to-end completion. It does not claim live model "
    "quality or real customer outcomes."
)

CATEGORY_LABELS = {
    "research_factual_accuracy": "Research factual accuracy",
    "citation_correctness": "Citation correctness",
    "evidence_completeness": "Evidence completeness",
    "hypothesis_relevance": "Hypothesis relevance",
    "solution_relevance": "Solution relevance",
    "hallucination_rate": "Unsupported-claim control",
    "task_completion": "Task completion",
}


def utc_now() -> datetime:
    return datetime.now(UTC)


def _seed_one(session: Session, scenario: dict[str, str]) -> Account:
    account = accounts_service.create_account(
        session,
        AccountCreate(
            name=scenario["name"],
            website=scenario["website"],
            industry=scenario["industry"],
            region=scenario["region"],
            notes=scenario["notes"],
        ),
    )
    account.is_demo = True
    session.commit()

    research = research_service.create_research_run(
        session,
        account.id,
        ResearchRunCreate(provider=ResearchProviderName.MOCK),
    )
    research_service.execute_research(session, research.id)
    research_service.review_research_run(
        session,
        research.id,
        ResearchReviewRequest(
            decision=ReviewDecision.APPROVE,
            notes="Synthetic demo inputs and evidence boundaries reviewed.",
        ),
    )

    hypothesis = discovery_service.generate_from_research(
        session, account.id, DiscoveryGenerateRequest(max_hypotheses=1)
    )[0]
    hypothesis = discovery_service.review_hypothesis(
        session,
        hypothesis.id,
        HypothesisReviewRequest(
            decision=HypothesisReviewDecision.ACCEPT,
            notes="Validate this synthetic opportunity with the demo customer response.",
        ),
    )
    answer = discovery_service.create_answer(
        session,
        hypothesis.questions[0].id,
        CustomerAnswerCreate(
            answer_text=scenario["answer"],
            respondent_name="Demo Process Owner",
            respondent_role="Operations Lead",
        ),
    )
    session.expire_all()
    need = discovery_service.confirm_need(
        session,
        hypothesis.id,
        ConfirmedNeedCreate(
            title=scenario["need_title"],
            description=scenario["need_description"],
            business_impact=scenario["business_impact"],
            success_metric=scenario["success_metric"],
            constraints=scenario["constraints"],
            answer_ids=[answer.id],
        ),
    )
    discovery_service.review_discovery(
        session,
        account.id,
        DiscoveryReviewRequest(
            decision=ReviewDecision.APPROVE,
            notes="Synthetic customer answer, confirmed need, and success metric reviewed.",
        ),
    )

    matches = solutions_service.generate_matches(
        session, account.id, SolutionMatchRequest(top_per_need=4)
    )
    selected = next(
        item for item in matches if item.solution_template.slug == scenario["template_slug"]
    )
    proposal = solutions_service.create_proposal(
        session,
        account.id,
        SolutionProposalCreate(
            solution_template_id=selected.solution_template_id,
            need_ids=[need.id],
            deployment_option=DeploymentOption(scenario["deployment"]),
        ),
    )
    solutions_service.review_proposal(
        session,
        proposal.id,
        SolutionReviewRequest(
            decision=SolutionReviewDecision.ACCEPT,
            notes="Need mapping, architecture, deployment boundary, risks, and metrics reviewed.",
        ),
    )

    poc = poc_service.generate_plan(session, account.id)
    poc = poc_service.review_plan(
        session,
        poc.id,
        PocReviewRequest(
            decision=PocReviewDecision.APPROVE,
            notes="Synthetic POC scope, holdout set, and success thresholds reviewed.",
        ),
    )
    for metric in poc.metrics:
        if metric.target_operator == MetricOperator.GREATER_THAN_OR_EQUAL:
            actual = metric.target_value + (4 if metric.unit == "%" else 0.5)
        else:
            actual = max(0.01, metric.target_value * 0.8)
        poc_service.update_metric(
            session,
            metric.id,
            PocMetricUpdate(
                actual_value=round(actual, 2),
                notes="Deterministic passing value for the synthetic regression portfolio.",
            ),
        )
    poc_service.create_decision(
        session,
        poc.id,
        PocDecisionCreate(
            decision=PocDecisionType.PROCEED,
            rationale="All approved synthetic POC thresholds passed.",
        ),
    )

    case = business_case_service.generate_case(session, account.id)
    business_case_service.review_case(
        session,
        case.id,
        BusinessCaseReviewRequest(
            decision=BusinessCaseReviewDecision.APPROVE,
            notes="Scenario assumptions and deployment trade-offs reviewed for demo use.",
        ),
    )
    deployment = deployment_service.generate_plan(session, account.id)
    for item in deployment.checklist_items:
        deployment_service.update_checklist_item(
            session,
            item.id,
            DeploymentChecklistUpdate(
                owner="Demo Delivery Team",
                status=ChecklistItemStatus.COMPLETED,
                evidence_notes="Synthetic readiness evidence recorded for regression coverage.",
            ),
        )
    deployment_service.complete_plan(
        session,
        deployment.id,
        DeploymentCompleteRequest(
            notes="Synthetic deployment readiness checklist completed for the demo portfolio."
        ),
    )
    return accounts_service.get_account_or_raise(session, account.id)


def seed_demo_accounts(session: Session) -> list[Account]:
    existing = {
        account.name: account
        for account in session.scalars(select(Account).where(Account.is_demo.is_(True))).all()
    }
    for scenario in DEMO_SCENARIOS:
        if scenario["name"] not in existing:
            account = _seed_one(session, scenario)
            existing[account.name] = account
    return [existing[scenario["name"]] for scenario in DEMO_SCENARIOS]


def list_demo_summaries(session: Session) -> list[dict]:
    accounts = list(
        session.scalars(
            select(Account).where(Account.is_demo.is_(True)).order_by(Account.name)
        ).all()
    )
    summaries = []
    for account in accounts:
        stages = list(
            session.scalars(
                select(AccountStageState).where(AccountStageState.account_id == account.id)
            ).all()
        )
        deployment_stage = next(stage for stage in stages if stage.stage == StageName.DEPLOYMENT)
        plan = session.scalar(
            select(DeploymentPlan).where(DeploymentPlan.account_id == account.id)
        )
        completed = sum(stage.status == StageStatus.COMPLETED for stage in stages)
        summaries.append(
            {
                "id": account.id,
                "name": account.name,
                "industry": account.industry,
                "region": account.region,
                "current_stage": account.current_stage,
                "deployment_status": deployment_stage.status,
                "deployment_plan_status": plan.status if plan else None,
                "workflow_completion": round(completed / len(STAGE_ORDER) * 100),
            }
        )
    return summaries


def _task(
    *,
    account: Account,
    category: str,
    expected: str,
    actual: str,
    passed: bool,
    latency_ms: float,
    position: int,
) -> SystemEvaluationTask:
    return SystemEvaluationTask(
        account_id=account.id,
        category=category,
        label=CATEGORY_LABELS[category],
        expected=expected,
        actual=actual,
        passed=passed,
        score=100 if passed else 0,
        latency_ms=latency_ms,
        estimated_cost_usd=0,
        notes="Deterministic database and lineage assertion; no model call was made.",
        position=position,
    )


def _evaluate_account(session: Session, account: Account, start_position: int):
    started = time.perf_counter()
    research = session.scalar(
        select(ResearchRun)
        .where(ResearchRun.account_id == account.id, ResearchRun.status == ResearchStatus.COMPLETED)
        .options(
            selectinload(ResearchRun.profile)
            .selectinload(CompanyProfile.claims)
            .selectinload(ProfileClaim.evidence_items)
        )
        .order_by(ResearchRun.created_at.desc())
    )
    claims = research.profile.claims if research and research.profile else []
    hypotheses = list(
        session.scalars(
            select(OpportunityHypothesis)
            .where(OpportunityHypothesis.account_id == account.id)
            .options(
                selectinload(OpportunityHypothesis.evidence_items),
                selectinload(OpportunityHypothesis.confirmed_need),
            )
        ).all()
    )
    proposal = session.scalar(
        select(SolutionProposal)
        .where(
            SolutionProposal.account_id == account.id,
            SolutionProposal.status == SolutionProposalStatus.ACCEPTED,
        )
        .options(selectinload(SolutionProposal.derived_needs))
    )
    stages = list(
        session.scalars(
            select(AccountStageState).where(AccountStageState.account_id == account.id)
        ).all()
    )
    latency = max(0.01, round((time.perf_counter() - started) * 1000 / 7, 2))
    unsupported = [claim for claim in claims if not claim.evidence_items]
    checks = [
        (
            "research_factual_accuracy",
            "All demo research claims are human-reviewed and grounded in supplied inputs",
            f"{len(claims)} reviewed claims",
            bool(claims)
            and all(claim.review_status == ClaimReviewStatus.HUMAN_REVIEWED for claim in claims),
        ),
        (
            "citation_correctness",
            "Every research claim has at least one citation",
            f"{sum(bool(claim.evidence_items) for claim in claims)}/{len(claims)} cited claims",
            bool(claims) and all(claim.evidence_items for claim in claims),
        ),
        (
            "evidence_completeness",
            "Every hypothesis retains evidence and a confirmed need",
            f"{len(hypotheses)} traced hypotheses",
            bool(hypotheses)
            and all(item.evidence_items and item.confirmed_need for item in hypotheses),
        ),
        (
            "hypothesis_relevance",
            "The reviewed hypothesis becomes a measurable confirmed need",
            f"{sum(item.status == HypothesisStatus.CONFIRMED for item in hypotheses)} confirmed",
            bool(hypotheses)
            and all(item.status == HypothesisStatus.CONFIRMED for item in hypotheses),
        ),
        (
            "solution_relevance",
            "An accepted solution is linked to the confirmed need",
            f"{len(proposal.derived_needs) if proposal else 0} linked needs",
            bool(proposal and proposal.derived_needs),
        ),
        (
            "hallucination_rate",
            "No stored demo claim lacks supporting evidence",
            f"{len(unsupported)} unsupported claims",
            not unsupported,
        ),
        (
            "task_completion",
            "All eight workflow stages are complete",
            f"{sum(stage.status == StageStatus.COMPLETED for stage in stages)}/8 stages complete",
            len(stages) == len(STAGE_ORDER)
            and all(stage.status == StageStatus.COMPLETED for stage in stages),
        ),
    ]
    return [
        _task(
            account=account,
            category=category,
            expected=expected,
            actual=actual,
            passed=passed,
            latency_ms=latency,
            position=start_position + offset,
        )
        for offset, (category, expected, actual, passed) in enumerate(checks)
    ]


def run_system_evaluation(session: Session) -> SystemEvaluationRun:
    accounts = seed_demo_accounts(session)
    run = SystemEvaluationRun(
        name=f"SolutionFlow deterministic regression · {utc_now().date().isoformat()}",
        methodology=METHODOLOGY,
        dataset_version="synthetic-demo-portfolio-v1",
        is_deterministic=True,
        demo_account_count=len(accounts),
        total_tasks=0,
        passed_tasks=0,
        pass_rate=0,
        hallucination_rate=0,
        citation_correctness=0,
        task_completion_rate=0,
        mean_latency_ms=0,
        estimated_cost_usd=0,
    )
    for index, account in enumerate(accounts):
        run.tasks.extend(_evaluate_account(session, account, index * 7))
    run.total_tasks = len(run.tasks)
    run.passed_tasks = sum(task.passed for task in run.tasks)
    run.pass_rate = round(run.passed_tasks / run.total_tasks * 100, 2)
    hallucination_tasks = [task for task in run.tasks if task.category == "hallucination_rate"]
    run.hallucination_rate = round(
        sum(not task.passed for task in hallucination_tasks) / len(hallucination_tasks) * 100,
        2,
    )
    citation_tasks = [task for task in run.tasks if task.category == "citation_correctness"]
    run.citation_correctness = round(
        sum(task.passed for task in citation_tasks) / len(citation_tasks) * 100, 2
    )
    completion_tasks = [task for task in run.tasks if task.category == "task_completion"]
    run.task_completion_rate = round(
        sum(task.passed for task in completion_tasks) / len(completion_tasks) * 100, 2
    )
    run.mean_latency_ms = round(
        sum(task.latency_ms for task in run.tasks) / len(run.tasks), 2
    )
    run.estimated_cost_usd = round(sum(task.estimated_cost_usd for task in run.tasks), 4)
    run.completed_at = utc_now()
    session.add(run)
    session.commit()
    return get_run_or_raise(session, run.id)


def get_run_or_raise(session: Session, run_id) -> SystemEvaluationRun:
    run = session.scalar(
        select(SystemEvaluationRun)
        .where(SystemEvaluationRun.id == run_id)
        .options(selectinload(SystemEvaluationRun.tasks))
    )
    if run is None:
        raise ValueError("System evaluation run not found")
    return run


def latest_run(session: Session) -> SystemEvaluationRun | None:
    return session.scalar(
        select(SystemEvaluationRun)
        .options(selectinload(SystemEvaluationRun.tasks))
        .order_by(SystemEvaluationRun.created_at.desc())
    )


def metric_summaries(run: SystemEvaluationRun) -> list[dict]:
    grouped: dict[str, list[SystemEvaluationTask]] = defaultdict(list)
    for task in run.tasks:
        grouped[task.category].append(task)
    return [
        {
            "category": category,
            "label": CATEGORY_LABELS[category],
            "passed": sum(task.passed for task in tasks),
            "total": len(tasks),
            "score": round(sum(task.score for task in tasks) / len(tasks), 2),
        }
        for category, tasks in grouped.items()
    ]
