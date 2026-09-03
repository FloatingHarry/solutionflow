export const stageOrder = [
  "research",
  "opportunity",
  "discovery",
  "solution",
  "poc",
  "evaluation",
  "business_case",
  "deployment",
] as const;

export type StageName = (typeof stageOrder)[number];
export type StageStatus = "not_started" | "in_progress" | "blocked" | "completed";

export interface Account {
  id: string;
  name: string;
  website: string | null;
  industry: string | null;
  region: string | null;
  notes: string | null;
  is_demo: boolean;
  current_stage: StageName;
  archived_at: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface AccountList {
  items: Account[];
  total: number;
  limit: number;
  offset: number;
}

export interface StageState {
  stage: StageName;
  status: StageStatus;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string;
}

export interface Workflow {
  account_id: string;
  current_stage: StageName;
  stages: StageState[];
}

export interface Activity {
  id: string;
  account_id: string;
  actor_type: "system" | "user";
  event_type: string;
  entity_type: string;
  entity_id: string | null;
  summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ActivityList {
  items: Activity[];
  total: number;
}

export interface ApiErrorPayload {
  detail?: string | Array<{ msg?: string }>;
}

export type ResearchStatus =
  | "queued"
  | "running"
  | "needs_review"
  | "completed"
  | "failed"
  | "rejected";

export type ResearchProvider = "mock" | "openai";
export type EvidenceConfidence = "low" | "medium" | "high";
export type EvidenceVerification = "direct_input" | "ai_extracted" | "verified";
export type ClaimReviewStatus = "ai_generated" | "human_reviewed" | "human_rejected";
export type ProfileSection =
  | "company_overview"
  | "products_services"
  | "market_geography"
  | "customers"
  | "recent_developments"
  | "financial_operating_signals"
  | "ai_digital_initiatives"
  | "potential_strategic_priorities";

export interface ResearchRun {
  id: string;
  account_id: string;
  retry_of_id: string | null;
  status: ResearchStatus;
  provider: ResearchProvider;
  provider_response_id: string | null;
  query_plan: Record<string, unknown>;
  error_message: string | null;
  review_notes: string | null;
  started_at: string | null;
  finished_at: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResearchSource {
  id: string;
  source_type: string;
  title: string;
  url: string | null;
  publisher: string | null;
  published_at: string | null;
  retrieved_at: string;
  content_excerpt: string | null;
  is_official: boolean;
  metadata: Record<string, unknown>;
}

export interface Citation {
  evidence_id: string;
  source_id: string;
  source_title: string;
  source_url: string | null;
  publisher: string | null;
  supporting_text: string;
  locator: string | null;
  confidence: EvidenceConfidence;
  verification_status: EvidenceVerification;
  retrieved_at: string;
}

export interface ProfileClaim {
  id: string;
  section: ProfileSection;
  statement: string;
  confidence: EvidenceConfidence;
  is_inference: boolean;
  review_status: ClaimReviewStatus;
  citations: Citation[];
}

export interface CompanyProfile {
  id: string;
  research_run_id: string;
  summary: string;
  is_simulated: boolean;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
  claims: ProfileClaim[];
}

export interface ResearchWorkspace {
  account_id: string;
  configured_provider: ResearchProvider;
  live_research_available: boolean;
  latest_run: ResearchRun | null;
  run_history: ResearchRun[];
  profile: CompanyProfile | null;
  sources: ResearchSource[];
}

export type HypothesisStatus =
  | "ai_suggested"
  | "user_accepted"
  | "user_rejected"
  | "need_validation"
  | "confirmed";

export type HypothesisOrigin = "manual" | "research_template";

export interface CustomerAnswer {
  id: string;
  question_id: string;
  answer_text: string;
  respondent_name: string | null;
  respondent_role: string | null;
  answered_at: string;
  created_at: string;
  updated_at: string;
}

export interface DiscoveryQuestion {
  id: string;
  hypothesis_id: string;
  question: string;
  rationale: string | null;
  position: number;
  created_at: string;
  updated_at: string;
  answers: CustomerAnswer[];
}

export interface ConfirmedNeed {
  id: string;
  hypothesis_id: string;
  title: string;
  description: string;
  business_impact: string | null;
  success_metric: string;
  constraints: string | null;
  confirmed_at: string;
  supporting_answer_ids: string[];
}

export interface OpportunityHypothesis {
  id: string;
  account_id: string;
  source_claim_id: string | null;
  title: string;
  description: string;
  confidence: EvidenceConfidence;
  business_area: string | null;
  potential_impact: string | null;
  status: HypothesisStatus;
  origin: HypothesisOrigin;
  review_notes: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
  evidence: Citation[];
  questions: DiscoveryQuestion[];
  confirmed_need: ConfirmedNeed | null;
}

export interface DiscoveryReview {
  id: string;
  account_id: string;
  decision: "approve" | "reject";
  notes: string;
  created_at: string;
}

export interface DiscoveryWorkspace {
  account_id: string;
  current_stage: StageName;
  research_approved: boolean;
  hypotheses: OpportunityHypothesis[];
  confirmed_needs: ConfirmedNeed[];
  reviews: DiscoveryReview[];
}

export type DeploymentOption = "saas_api" | "eu_cloud" | "private_on_premise";
export type SolutionProposalStatus = "draft" | "needs_revision" | "accepted" | "rejected";

export interface SolutionNeedSummary {
  id: string;
  title: string;
  description: string;
  business_impact: string | null;
  success_metric: string;
  constraints: string | null;
  confirmed_at: string;
}

export interface SolutionTemplate {
  id: string;
  slug: string;
  name: string;
  description: string;
  target_pain_points: string[];
  target_industries: string[];
  required_data: string[];
  architecture: string;
  deployment_options: DeploymentOption[];
  success_metrics: string[];
  known_limitations: string[];
  estimated_cost_model: string;
  example_use_cases: string[];
  is_simulated: boolean;
  version: number;
}

export interface SolutionMatch {
  id: string;
  confirmed_need_id: string;
  score: number;
  rationale: string;
  matched_terms: string[];
  created_at: string;
  template: SolutionTemplate;
}

export interface SolutionProposal {
  id: string;
  account_id: string;
  title: string;
  executive_summary: string;
  why_fit: string;
  architecture: string;
  required_data: string[];
  model_tool_requirements: string[];
  deployment_option: DeploymentOption;
  security_considerations: string[];
  risks: string[];
  expected_business_impact: string;
  success_metrics: string[];
  status: SolutionProposalStatus;
  review_notes: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
  template: SolutionTemplate;
  derived_needs: SolutionNeedSummary[];
}

export interface SolutionWorkspace {
  account_id: string;
  current_stage: StageName;
  discovery_approved: boolean;
  catalog_is_simulated: boolean;
  catalog: SolutionTemplate[];
  confirmed_needs: SolutionNeedSummary[];
  matches: SolutionMatch[];
  proposals: SolutionProposal[];
}

export type PocPlanStatus = "draft" | "needs_revision" | "approved" | "rejected";
export type MetricOperator = "gte" | "lte";
export type MetricResultStatus = "pending" | "pass" | "fail";
export type PocDecisionType = "proceed" | "iterate" | "reject";

export interface PocMetric {
  id: string;
  metric_key: string;
  name: string;
  target_operator: MetricOperator;
  target_value: number;
  unit: string;
  actual_value: number | null;
  result_status: MetricResultStatus;
  notes: string | null;
  position: number;
  created_at: string;
  updated_at: string;
}

export interface PocDecision {
  id: string;
  decision: PocDecisionType;
  rationale: string;
  created_at: string;
}

export interface PocPlan {
  id: string;
  account_id: string;
  objective: string;
  business_problem: string;
  scope: string;
  required_data: string[];
  architecture: string;
  timeline_days: number;
  evaluation_dataset: string;
  expected_output: string;
  risks: string[];
  status: PocPlanStatus;
  review_notes: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
  solution_proposal: SolutionProposal;
  metrics: PocMetric[];
  decisions: PocDecision[];
}

export interface PocWorkspace {
  account_id: string;
  current_stage: StageName;
  poc_stage_status: StageStatus;
  evaluation_stage_status: StageStatus;
  accepted_solution: SolutionProposal | null;
  plan: PocPlan | null;
}

export type BusinessCaseStatus = "draft" | "needs_revision" | "approved" | "rejected";
export type AssessmentRating = "low" | "medium" | "high";
export type CurrencyCode = "EUR" | "USD" | "GBP" | "CNY";

export interface DeploymentAssessment {
  id: string;
  option: DeploymentOption;
  cost: AssessmentRating;
  implementation_difficulty: AssessmentRating;
  data_privacy: AssessmentRating;
  scalability: AssessmentRating;
  maintenance: AssessmentRating;
  latency: AssessmentRating;
  compliance: AssessmentRating;
  notes: string[];
  position: number;
}

export interface AccountBrief {
  id: string;
  executive_summary: string;
  customer_context: string;
  confirmed_needs_summary: string;
  solution_summary: string;
  poc_summary: string;
  roi_summary: string;
  deployment_summary: string;
  key_risks: string[];
  next_steps: string[];
  created_at: string;
  updated_at: string;
}

export interface BusinessCase {
  id: string;
  account_id: string;
  currency: CurrencyCode;
  number_employees: number;
  average_hourly_cost: number;
  current_time_per_task_minutes: number;
  tasks_per_employee_per_month: number;
  expected_time_reduction_percent: number;
  monthly_ai_cost: number;
  implementation_cost: number;
  current_monthly_cost: number;
  estimated_new_labor_cost: number;
  estimated_new_total_cost: number;
  monthly_savings: number;
  annual_savings: number;
  estimated_first_year_roi_percent: number | null;
  payback_period_months: number | null;
  recommended_deployment: DeploymentOption;
  deployment_rationale: string;
  assumptions: string[];
  scenario_is_estimate: boolean;
  status: BusinessCaseStatus;
  review_notes: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
  deployment_assessments: DeploymentAssessment[];
  brief: AccountBrief;
  poc_plan: PocPlan;
}

export interface BusinessCaseWorkspace {
  account_id: string;
  current_stage: StageName;
  business_case_stage_status: StageStatus;
  deployment_stage_status: StageStatus;
  evaluation_completed: boolean;
  case: BusinessCase | null;
}

export type DeploymentPlanStatus = "in_progress" | "blocked" | "completed";
export type DeploymentChecklistStatus = "pending" | "blocked" | "completed";

export interface DeploymentChecklistItem {
  id: string;
  category: string;
  title: string;
  owner: string | null;
  status: DeploymentChecklistStatus;
  evidence_notes: string | null;
  position: number;
  completed_at: string | null;
  updated_at: string;
}

export interface DeploymentPlan {
  id: string;
  account_id: string;
  business_case_id: string;
  environment: DeploymentOption;
  owner: string;
  target_launch_date: string | null;
  rollout_strategy: string;
  integration_plan: string;
  data_governance_plan: string;
  monitoring_plan: string;
  rollback_plan: string;
  support_model: string;
  status: DeploymentPlanStatus;
  readiness_score: number;
  completion_notes: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  checklist_items: DeploymentChecklistItem[];
}

export interface DeploymentWorkspace {
  account_id: string;
  current_stage: StageName;
  deployment_stage_status: StageStatus;
  business_case_approved: boolean;
  recommended_environment: DeploymentOption | null;
  plan: DeploymentPlan | null;
}

export interface EvaluationTask {
  id: string;
  account_id: string;
  category: string;
  label: string;
  expected: string;
  actual: string;
  passed: boolean;
  score: number;
  latency_ms: number;
  estimated_cost_usd: number;
  notes: string;
  position: number;
}

export interface EvaluationMetricSummary {
  category: string;
  label: string;
  passed: number;
  total: number;
  score: number;
}

export interface SystemEvaluationRun {
  id: string;
  name: string;
  methodology: string;
  dataset_version: string;
  is_deterministic: boolean;
  demo_account_count: number;
  total_tasks: number;
  passed_tasks: number;
  pass_rate: number;
  hallucination_rate: number;
  citation_correctness: number;
  task_completion_rate: number;
  mean_latency_ms: number;
  estimated_cost_usd: number;
  created_at: string;
  completed_at: string;
  metrics: EvaluationMetricSummary[];
  tasks: EvaluationTask[];
}

export interface DemoAccountSummary {
  id: string;
  name: string;
  industry: string | null;
  region: string | null;
  current_stage: StageName;
  deployment_status: StageStatus;
  deployment_plan_status: DeploymentPlanStatus | null;
  workflow_completion: number;
}

export interface SystemEvaluationWorkspace {
  required_demo_accounts: number;
  required_task_minimum: number;
  methodology_note: string;
  demo_accounts: DemoAccountSummary[];
  latest_run: SystemEvaluationRun | null;
}

export type AgentProvider = "guided" | "openai";
export type AgentRunStatus =
  | "completed"
  | "awaiting_approval"
  | "action_completed"
  | "rejected"
  | "failed";
export type AgentActionStatus = "none" | "pending" | "executed" | "rejected" | "failed";

export interface AgentAction {
  key: string;
  title: string;
  description: string;
  reason: string;
  target_path: string | null;
  requires_approval: boolean;
  status: AgentActionStatus;
  result: Record<string, unknown>;
}

export interface AgentRun {
  id: string;
  account_id: string;
  goal: string;
  status: AgentRunStatus;
  provider: AgentProvider;
  model: string | null;
  provider_response_id: string | null;
  stage_snapshot: string;
  summary: string;
  observations: string[];
  plan: string[];
  question: string | null;
  trace: Array<Record<string, unknown>>;
  action: AgentAction | null;
  approval_note: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface AgentWorkspace {
  account_id: string;
  live_agent_available: boolean;
  mode: AgentProvider;
  model: string | null;
  capabilities: string[];
  starter_prompts: string[];
  runs: AgentRun[];
}
