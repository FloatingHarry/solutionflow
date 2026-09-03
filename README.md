# SolutionFlow

SolutionFlow is an enterprise account workflow for turning customer evidence into a traceable solution, POC, evaluation, business case, and production-readiness decision. Phases 1 through 7 now cover the complete MVP: workflow foundations, source-backed research, customer discovery, explainable solution matching, bounded POC design, metric evaluation, scenario economics, deployment planning, system evaluation, and explicit human approval gates.

The product direction and later phases are defined in [`enterprise_solution_copilot_plan.md`](./enterprise_solution_copilot_plan.md).

## Implemented capabilities

- Create, view, search, edit, archive, and restore accounts.
- Initialize every account with eight ordered workflow stages.
- Start, block, resume, and complete the current stage with a required reason.
- Prevent users from skipping incomplete stages.
- Record account and workflow changes in an account-level activity timeline.
- Keep profile notes visually separate from verified evidence.
- Start asynchronous company research from an account workspace.
- Run a deterministic simulation that uses account inputs only and is visibly labeled as simulated.
- Optionally run live OpenAI web research with structured output and traceable source URLs.
- Store sources, evidence excerpts, profile claims, confidence, inference state, and verification state as first-class records.
- Require a human approve/reject decision before the Research workflow stage completes.
- Retry failed or rejected research while preserving run history.
- Generate opportunity hypotheses from human-approved research claims without presenting them as customer facts.
- Create and review hypotheses, manage discovery questions, and record named customer answers.
- Require customer answers before a hypothesis can become a confirmed need.
- Preserve the full Research Evidence → Hypothesis → Question → Answer → Confirmed Need chain.
- Require a final human Discovery review before advancing the workflow to Solution.
- Seed four clearly labeled demo solution patterns: Enterprise Knowledge Assistant, Customer Service Copilot, Sales / Account Copilot, and Document Intelligence.
- Rank solution patterns against confirmed needs with a deterministic score, matched terms, and human-readable rationale.
- Generate editable solution proposals with architecture, data, tool, deployment, security, risk, impact, and POC metric sections.
- Preserve Solution Proposal → Confirmed Need → Customer Answer → Hypothesis → Evidence traceability.
- Require a human accept/reject/revise decision before advancing the workflow to POC.
- Generate an editable POC plan from the accepted solution with objective, business problem, scope, data, architecture, timeline, holdout dataset, risks, and expected output.
- Seed solution-specific success metrics with target operators and lock those targets after human POC approval.
- Record actual metric values and calculate deterministic `pass` / `fail` results for both greater-than and less-than thresholds.
- Require complete metric results and an auditable rationale before a human can choose Proceed, Iterate, or Reject.
- Preserve decision history, reopen blocked evaluation after new measurements, and advance Proceed decisions to Business Case.
- Generate an editable ROI scenario from the accepted solution and approved POC while labeling every result as an estimate rather than a realized outcome.
- Calculate current and estimated monthly cost, monthly and annual savings, first-year ROI, and payback period from explicit assumptions.
- Compare SaaS/API, EU cloud, and private/on-premise deployment options across cost, implementation, privacy, scalability, maintenance, latency, and compliance.
- Generate an editable final account brief that carries forward customer context, confirmed needs, the accepted solution, POC evidence, scenario economics, risks, and next steps.
- Require a final human Business Case decision before completing the stage and advancing an approved account to Deployment.
- Generate an editable deployment operating plan from the approved business case.
- Track security, privacy, procurement, integration, operations, and governance readiness with named owners, evidence notes, and blocker-aware workflow state.
- Require all six readiness checks and human completion notes before completing Deployment.
- Seed five clearly labeled synthetic demo accounts that complete all eight workflow stages and retain the complete evidence-to-decision graph.
- Run and persist 35 deterministic system-evaluation tasks across research grounding, citation correctness, evidence completeness, hypothesis relevance, solution relevance, unsupported-claim control, and task completion.
- Expose a versioned REST API with OpenAPI documentation.

CRM integrations, billing, complex permissions, actual cloud provisioning, live-model benchmark datasets, production compliance certification, and enterprise SSO are not implemented.

## Architecture

```text
Browser
   |
Next.js workspace (apps/web)
   |
FastAPI domain API (apps/api)
   |-- Research provider: mock or OpenAI Responses API + web search
   |
PostgreSQL
```

Next.js owns presentation and browser interaction. FastAPI is the only business-logic boundary. PostgreSQL owns workflow, research evidence, and audit history. Research providers return a common typed artifact model and never write directly to the database.

See [the architecture diagram and system boundaries](./docs/architecture.md) for the runtime, evidence lineage, evaluation boundary, and deployment boundary.

## Repository

```text
apps/
  api/
    app/
      api/                 HTTP route composition
      core/                settings
      db/                  SQLAlchemy session and base
      modules/accounts/    account, workflow, and activity domain
      modules/research/    research jobs, providers, evidence, and review
      modules/discovery/   hypotheses, questions, answers, needs, and review
      modules/solutions/   demo catalog, matching, proposals, and review
      modules/poc/         POC plans, evaluation metrics, and decisions
      modules/business_case/ ROI scenarios, deployment trade-offs, briefs, and review
      modules/deployment/  operating plans, readiness checks, and completion gate
      modules/evaluation/  demo portfolio and deterministic system regression
    migrations/            Alembic migrations
    tests/                 API and domain integration tests
  web/
    app/                   Next.js routes and API proxy
    components/            workspace UI
    lib/                   API and workflow types/helpers
compose.yaml               local PostgreSQL
```

The `glm/` directory contains prior report assets and is intentionally not part of the runtime application.

## Prerequisites

- Node.js 20.9 or newer
- Python 3.11 or newer
- Docker Desktop or another PostgreSQL 16-compatible service

## Local setup

From the repository root:

```powershell
Copy-Item .env.example .env
npm install
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "apps/api[dev]"
docker compose up -d
```

Apply the database migration:

```powershell
Set-Location apps/api
..\..\.venv\Scripts\python.exe -m alembic upgrade head
Set-Location ../..
```

Run the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn --app-dir apps/api app.main:app --reload
```

Run the web application in a second terminal:

```powershell
npm run dev:web
```

Open [http://localhost:3000](http://localhost:3000). FastAPI documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

The defaults use PostgreSQL on port `5433` so they do not conflict with a conventional local PostgreSQL installation on `5432`.

### Research configuration

The safe default is local simulation:

```dotenv
RESEARCH_PROVIDER=mock
RESEARCH_RUN_INLINE=false
```

Simulation mode only turns the account fields into cited claims. It does not make requests or present generated details as public facts.

To enable live web research, paste a project API key into the already prepared local `.env` template:

```dotenv
# Keep the value server-side and do not commit this file.
OPENAI_API_KEY=
OPENAI_RESEARCH_MODEL=gpt-5.4-mini
```

Restart FastAPI after adding the key. Then select **Live web research · OpenAI** in the Research workspace, or set `RESEARCH_PROVIDER=openai`. Live mode uses the OpenAI Responses API web-search tool and only persists claims that match a returned source URL. Keep the human approval gate in place before using research in customer-facing work. Phase 3's research-to-hypothesis template remains deterministic and does not require the key.

### Demo portfolio and system evaluation

Open [http://localhost:3000/evaluation](http://localhost:3000/evaluation), initialize the demo portfolio, and run the regression evaluation. The operation is idempotent: it creates at most five named demo accounts and may record multiple evaluation runs.

The demo portfolio is synthetic. Its reserved `.example` websites, customer answers, POC results, ROI scenarios, and deployment evidence must not be presented as real company or customer data. The 35-task suite validates product state and lineage without making an OpenAI call.

## Verification

Backend:

```powershell
Set-Location apps/api
..\..\.venv\Scripts\python.exe -m pytest
..\..\.venv\Scripts\python.exe -m ruff check app tests migrations
```

Frontend:

```powershell
npm run lint:web
npm run typecheck:web
npm run test:web
npm run build:web
```

Validate the PostgreSQL migration without connecting to a database:

```powershell
Set-Location apps/api
..\..\.venv\Scripts\python.exe -m alembic upgrade head --sql
```

## Data model

### `accounts`

Stores company profile information, the current workflow stage, archive state, and an optimistic version counter.

### `account_stage_states`

Stores one row per account and stage. Stages are ordered as:

```text
research -> opportunity -> discovery -> solution -> poc -> evaluation -> business_case -> deployment
```

Stage state is one of `not_started`, `in_progress`, `blocked`, or `completed`.

### `activity_events`

Stores actor, event type, affected entity, summary, timestamp, and non-relational event metadata. Account and workflow updates write their state change and activity event in the same database transaction.

### Research evidence tables

- `research_runs` stores provider, lifecycle, retry lineage, errors, and review decisions.
- `sources` stores URLs or account inputs with publisher, retrieval time, excerpts, and official-source state.
- `evidence` stores the excerpt and verification state supporting a claim.
- `company_profiles` stores the run-level research brief and simulation flag.
- `profile_claims` stores sectioned claims, confidence, inference, and human-review state.
- `claim_evidence` keeps the many-to-many citation relationship between claims and evidence.

### Discovery tables

- `opportunity_hypotheses` stores research-grounded or manual hypotheses plus review status.
- `hypothesis_evidence` links each hypothesis back to its supporting research evidence.
- `discovery_questions` stores ordered customer interview questions and their rationale.
- `customer_answers` stores the response, respondent, role, and interview time.
- `confirmed_needs` stores customer-validated needs, impact, constraints, and success metrics.
- `confirmed_need_answers` keeps the supporting-answer lineage for each confirmed need.
- `discovery_reviews` stores the final approve/revise decision and notes.

### Solution tables

- `solution_templates` stores the four simulated catalog patterns and their structured metadata.
- `solution_matches` stores deterministic match scores, rationale, and matched terms per confirmed need.
- `solution_proposals` stores the editable account proposal and human review state.
- `solution_proposal_needs` keeps the many-to-many lineage from proposals to confirmed needs.

### POC and evaluation tables

- `poc_plans` stores the experiment scope, required data, architecture, timeline, evaluation dataset, expected output, risks, and human review state.
- `poc_metrics` stores the target operator/value, unit, actual result, notes, and calculated pass/fail state for every success metric.
- `poc_decisions` stores the append-only Proceed, Iterate, or Reject history and required rationale.

### Business case tables

- `business_cases` stores editable ROI assumptions, calculated scenario outputs, the selected deployment option, and the final human review state.
- `deployment_assessments` stores the three deployment-option comparisons and their deterministic planning ratings.
- `account_briefs` stores the editable evidence-to-decision summary, key risks, and deployment handoff steps.

### Deployment tables

- `deployment_plans` stores the approved environment, rollout, integration, governance, monitoring, rollback, support, owner, target date, readiness score, and final completion record.
- `deployment_checklist_items` stores the six owner-and-evidence readiness checks. A blocked item blocks the Deployment workflow.

### System evaluation tables

- `system_evaluation_runs` stores the versioned methodology, aggregate scores, latency, cost, and deterministic/live boundary.
- `system_evaluation_tasks` stores every account-level expected state, actual state, score, pass/fail result, and measurement note.

## API

```text
GET    /api/v1/health
GET    /api/v1/ready
GET    /api/v1/accounts
POST   /api/v1/accounts
GET    /api/v1/accounts/{account_id}
PATCH  /api/v1/accounts/{account_id}
POST   /api/v1/accounts/{account_id}/archive
POST   /api/v1/accounts/{account_id}/restore
GET    /api/v1/accounts/{account_id}/workflow
POST   /api/v1/accounts/{account_id}/workflow/transitions
GET    /api/v1/accounts/{account_id}/activities
GET    /api/v1/accounts/{account_id}/research
POST   /api/v1/accounts/{account_id}/research-runs
GET    /api/v1/research-runs/{run_id}
POST   /api/v1/research-runs/{run_id}/retry
POST   /api/v1/research-runs/{run_id}/review
GET    /api/v1/accounts/{account_id}/discovery
POST   /api/v1/accounts/{account_id}/discovery/generate
POST   /api/v1/accounts/{account_id}/opportunity-hypotheses
POST   /api/v1/opportunity-hypotheses/{hypothesis_id}/review
POST   /api/v1/opportunity-hypotheses/{hypothesis_id}/questions
PATCH  /api/v1/discovery-questions/{question_id}
DELETE /api/v1/discovery-questions/{question_id}
POST   /api/v1/discovery-questions/{question_id}/answers
PATCH  /api/v1/customer-answers/{answer_id}
POST   /api/v1/opportunity-hypotheses/{hypothesis_id}/confirm
POST   /api/v1/accounts/{account_id}/discovery/review
GET    /api/v1/solutions/catalog
GET    /api/v1/accounts/{account_id}/solutions
POST   /api/v1/accounts/{account_id}/solutions/matches
POST   /api/v1/accounts/{account_id}/solution-proposals
PATCH  /api/v1/solution-proposals/{proposal_id}
POST   /api/v1/solution-proposals/{proposal_id}/review
GET    /api/v1/accounts/{account_id}/poc
POST   /api/v1/accounts/{account_id}/poc-plans/generate
PATCH  /api/v1/poc-plans/{plan_id}
POST   /api/v1/poc-plans/{plan_id}/review
PATCH  /api/v1/poc-metrics/{metric_id}
POST   /api/v1/poc-plans/{plan_id}/decision
GET    /api/v1/accounts/{account_id}/business-case
POST   /api/v1/accounts/{account_id}/business-cases/generate
PATCH  /api/v1/business-cases/{case_id}/scenario
PATCH  /api/v1/business-cases/{case_id}/deployment
PATCH  /api/v1/account-briefs/{brief_id}
POST   /api/v1/business-cases/{case_id}/review
GET    /api/v1/accounts/{account_id}/deployment
POST   /api/v1/accounts/{account_id}/deployment-plans/generate
PATCH  /api/v1/deployment-plans/{plan_id}
PATCH  /api/v1/deployment-checklist-items/{item_id}
POST   /api/v1/deployment-plans/{plan_id}/complete
GET    /api/v1/system-evaluation
POST   /api/v1/demo-accounts/seed
POST   /api/v1/system-evaluations/run
```

## MVP status

Phase 7 completes the planned MVP. Subsequent work should focus on production hardening: authentication and authorization, real connectors, live-model evaluations, observability, rate limits, backup and recovery, CI/CD, infrastructure provisioning, and security review.
