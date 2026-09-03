"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import type {
  MetricOperator,
  PocDecisionType,
  PocMetric,
  PocPlan,
  PocWorkspace as PocWorkspaceData,
} from "@/lib/types";
import { statusLabels } from "@/lib/workflow";

interface PocWorkspaceProps {
  accountId: string;
  initialWorkspace: PocWorkspaceData;
  archived: boolean;
}

const planStatusLabels = {
  draft: "Draft",
  needs_revision: "Needs revision",
  approved: "Approved",
  rejected: "Rejected",
};

const decisionLabels: Record<PocDecisionType, string> = {
  proceed: "Proceed",
  iterate: "Iterate",
  reject: "Reject",
};

function apiDetail(payload: unknown) {
  if (!payload || typeof payload !== "object" || !("detail" in payload)) return null;
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (item && typeof item === "object" && "msg" in item ? String(item.msg) : ""))
      .filter(Boolean)
      .join(" ");
  }
  return null;
}

function targetLabel(metric: PocMetric) {
  return `${metric.target_operator === "gte" ? "≥" : "≤"} ${metric.target_value} ${metric.unit}`;
}

function createPlanDraft(plan: PocPlan | null) {
  return {
    objective: plan?.objective ?? "",
    business_problem: plan?.business_problem ?? "",
    scope: plan?.scope ?? "",
    timeline_days: plan?.timeline_days ?? 14,
    evaluation_dataset: plan?.evaluation_dataset ?? "",
    expected_output: plan?.expected_output ?? "",
    architecture: plan?.architecture ?? "",
  };
}

export function PocWorkspace({ accountId, initialWorkspace, archived }: PocWorkspaceProps) {
  const router = useRouter();
  const plan = initialWorkspace.plan;
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [planDraft, setPlanDraft] = useState(() => createPlanDraft(plan));
  const [reviewNotes, setReviewNotes] = useState(plan?.review_notes ?? "");
  const [metricValues, setMetricValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      (plan?.metrics ?? []).map((metric) => [
        metric.id,
        metric.actual_value === null ? "" : String(metric.actual_value),
      ]),
    ),
  );
  const [targetValues, setTargetValues] = useState<Record<string, string>>(() =>
    Object.fromEntries((plan?.metrics ?? []).map((metric) => [metric.id, String(metric.target_value)])),
  );
  const [decisionReason, setDecisionReason] = useState("");

  const measuredCount = plan?.metrics.filter((metric) => metric.actual_value !== null).length ?? 0;
  const passCount = plan?.metrics.filter((metric) => metric.result_status === "pass").length ?? 0;
  const allMeasured = Boolean(plan?.metrics.length) && measuredCount === plan?.metrics.length;
  const allPassed = Boolean(plan?.metrics.length) && passCount === plan?.metrics.length;
  const evaluationClosed = initialWorkspace.evaluation_stage_status === "completed";
  const planEditable = Boolean(
    plan && ["draft", "needs_revision"].includes(plan.status) && !archived,
  );

  async function mutate(
    key: string,
    path: string,
    body: Record<string, unknown>,
    method = "POST",
  ) {
    setBusy(key);
    setError(null);
    try {
      const response = await fetch(`/api/backend${path}`, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(apiDetail(payload) || "Unable to save this change.");
      router.refresh();
      return true;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save this change.");
      return false;
    } finally {
      setBusy(null);
    }
  }

  async function generatePlan() {
    await mutate("generate", `/accounts/${accountId}/poc-plans/generate`, {});
  }

  async function savePlan() {
    if (!plan) return;
    const saved = await mutate("save-plan", `/poc-plans/${plan.id}`, planDraft, "PATCH");
    if (saved) setEditing(false);
  }

  async function reviewPlan(decision: "approve" | "needs_revision" | "reject") {
    if (!plan) return;
    await mutate(`review-${decision}`, `/poc-plans/${plan.id}/review`, {
      decision,
      notes: reviewNotes.trim() || "POC scope, data, architecture, and metrics reviewed by a human.",
    });
  }

  async function saveMetricTarget(metric: PocMetric, operator: MetricOperator) {
    const value = Number(targetValues[metric.id]);
    if (!Number.isFinite(value)) {
      setError(`Enter a valid target for ${metric.name}.`);
      return;
    }
    await mutate(
      `target-${metric.id}`,
      `/poc-metrics/${metric.id}`,
      { target_operator: operator, target_value: value },
      "PATCH",
    );
  }

  async function saveMetricResult(metric: PocMetric) {
    const value = Number(metricValues[metric.id]);
    if (!metricValues[metric.id]?.trim() || !Number.isFinite(value)) {
      setError(`Enter a valid actual value for ${metric.name}.`);
      return;
    }
    await mutate(
      `metric-${metric.id}`,
      `/poc-metrics/${metric.id}`,
      { actual_value: value, notes: "Recorded from the approved POC evaluation dataset." },
      "PATCH",
    );
  }

  async function decide(decision: PocDecisionType) {
    if (!plan) return;
    if (decisionReason.trim().length < 2) {
      setError("Add a decision reason so the evaluation remains auditable.");
      return;
    }
    await mutate(`decision-${decision}`, `/poc-plans/${plan.id}/decision`, {
      decision,
      rationale: decisionReason.trim(),
    });
  }

  const metricSummary = useMemo(
    () => [
      { label: "Metrics", value: plan?.metrics.length ?? 0 },
      { label: "Measured", value: measuredCount },
      { label: "Passed", value: passCount },
      { label: "Decisions", value: plan?.decisions.length ?? 0 },
    ],
    [measuredCount, passCount, plan],
  );

  return (
    <>
      <section className="pocMetrics">
        {metricSummary.map((item) => (
          <div key={item.label}><span>{item.label}</span><strong>{item.value}</strong></div>
        ))}
      </section>

      {error ? (
        <div className="researchError" role="alert"><strong>Could not save</strong><p>{error}</p></div>
      ) : null}

      {!initialWorkspace.accepted_solution ? (
        <section className="researchEmpty pocEmpty">
          <div className="emptyGlyph">◇</div>
          <h2>Accepted solution required</h2>
          <p>Approve a traceable solution proposal before defining the POC and evaluation gate.</p>
          <Link className="button secondary" href={`/accounts/${accountId}/solutions`}>Open solutions</Link>
        </section>
      ) : (
        <section className="panel pocSourceCard">
          <div>
            <span className="eyebrow">Accepted solution · source of truth</span>
            <h2>{initialWorkspace.accepted_solution.title}</h2>
            <p>{initialWorkspace.accepted_solution.executive_summary}</p>
          </div>
          <div className="pocSourceMeta">
            <span>{initialWorkspace.accepted_solution.template.name}</span>
            <span>{initialWorkspace.accepted_solution.deployment_option.replaceAll("_", " ")}</span>
            <span>{initialWorkspace.accepted_solution.derived_needs.length} confirmed need</span>
          </div>
          <Link href={`/accounts/${accountId}/solutions`}>
            POC → accepted proposal → confirmed need → customer evidence ↗
          </Link>
        </section>
      )}

      {initialWorkspace.accepted_solution && !plan ? (
        <section className="panel pocGenerateCard">
          <div>
            <span className="eyebrow">POC design</span>
            <h2>Turn the accepted solution into a testable plan</h2>
            <p>Generate a two-week draft with scope, data, architecture, risks, holdout dataset, and measurable success gates.</p>
          </div>
          <button className="button primary" disabled={archived || busy !== null} onClick={generatePlan}>
            {busy === "generate" ? "Generating…" : "Generate POC plan"}
          </button>
        </section>
      ) : null}

      {plan ? (
        <div className="pocGrid">
          <main className="pocMain">
            <section className="panel pocPlanCard">
              <header className="pocSectionHeader">
                <div>
                  <div className="pocBadges">
                    <span className={`pocStatus ${plan.status}`}>{planStatusLabels[plan.status]}</span>
                    <span>{plan.timeline_days} days</span>
                    <span>Human approval required</span>
                  </div>
                  <h2>POC plan</h2>
                  <p>A constrained experiment—not a production promise.</p>
                </div>
                {planEditable && !editing ? (
                  <button className="button secondary" onClick={() => setEditing(true)}>Edit plan</button>
                ) : null}
              </header>

              {editing ? (
                <div className="pocPlanEditor twoColumnForm">
                  <label className="fullField">Objective<textarea rows={3} value={planDraft.objective} onChange={(event) => setPlanDraft({ ...planDraft, objective: event.target.value })} /></label>
                  <label className="fullField">Business problem<textarea rows={3} value={planDraft.business_problem} onChange={(event) => setPlanDraft({ ...planDraft, business_problem: event.target.value })} /></label>
                  <label className="fullField">Scope<textarea rows={3} value={planDraft.scope} onChange={(event) => setPlanDraft({ ...planDraft, scope: event.target.value })} /></label>
                  <label>Timeline (days)<input type="number" min="1" max="365" value={planDraft.timeline_days} onChange={(event) => setPlanDraft({ ...planDraft, timeline_days: Number(event.target.value) })} /></label>
                  <label>Architecture<input value={planDraft.architecture} onChange={(event) => setPlanDraft({ ...planDraft, architecture: event.target.value })} /></label>
                  <label className="fullField">Evaluation dataset<textarea rows={3} value={planDraft.evaluation_dataset} onChange={(event) => setPlanDraft({ ...planDraft, evaluation_dataset: event.target.value })} /></label>
                  <label className="fullField">Expected output<textarea rows={3} value={planDraft.expected_output} onChange={(event) => setPlanDraft({ ...planDraft, expected_output: event.target.value })} /></label>
                  <div className="formActions fullField">
                    <button className="button secondary" onClick={() => setEditing(false)}>Cancel</button>
                    <button className="button primary" disabled={busy !== null} onClick={savePlan}>Save plan</button>
                  </div>
                </div>
              ) : (
                <div className="pocPlanBody">
                  <article><span>POC objective</span><p>{plan.objective}</p></article>
                  <article><span>Business problem</span><p>{plan.business_problem}</p></article>
                  <article className="wide"><span>Scope</span><p>{plan.scope}</p></article>
                  <article className="wide"><span>Architecture</span><p className="architectureFlow">{plan.architecture}</p></article>
                  <article><span>Evaluation dataset</span><p>{plan.evaluation_dataset}</p></article>
                  <article><span>Expected output</span><p>{plan.expected_output}</p></article>
                  <article><span>Required data</span><ul>{plan.required_data.map((item) => <li key={item}>{item}</li>)}</ul></article>
                  <article><span>Risks</span><ul>{plan.risks.map((item) => <li key={item}>{item}</li>)}</ul></article>
                </div>
              )}

              {planEditable ? (
                <div className="pocReviewGate">
                  <div><span className="eyebrow">Human gate</span><strong>Approve the plan before recording results</strong></div>
                  <textarea rows={2} value={reviewNotes} onChange={(event) => setReviewNotes(event.target.value)} placeholder="What scope, data, and metrics were verified?" />
                  <div>
                    <button className="button dangerGhost" disabled={busy !== null} onClick={() => reviewPlan("reject")}>Reject</button>
                    <button className="button secondary" disabled={busy !== null} onClick={() => reviewPlan("needs_revision")}>Needs revision</button>
                    <button className="button primary" disabled={busy !== null} onClick={() => reviewPlan("approve")}>Approve POC plan</button>
                  </div>
                </div>
              ) : plan.review_notes ? <blockquote className="pocReviewNote">{plan.review_notes}</blockquote> : null}
            </section>

            <section className="panel evaluationCard">
              <header className="pocSectionHeader evaluationHeader">
                <div>
                  <span className="eyebrow">Evaluation scorecard</span>
                  <h2>Target versus actual</h2>
                  <p>Each result is compared automatically; the final decision remains human-owned.</p>
                </div>
                <span className={`stageStatusPill ${initialWorkspace.evaluation_stage_status}`}>
                  {statusLabels[initialWorkspace.evaluation_stage_status]}
                </span>
              </header>
              <div className="metricTable" role="table" aria-label="POC evaluation metrics">
                <div className="metricTableHeader" role="row">
                  <span>Metric</span><span>Target</span><span>Actual</span><span>Result</span><span>Action</span>
                </div>
                {plan.metrics.map((metric) => (
                  <div className="metricRow" role="row" key={metric.id}>
                    <div><strong>{metric.name}</strong><small>{metric.metric_key.replaceAll("_", " ")}</small></div>
                    {planEditable ? (
                      <div className="targetEditor">
                        <select aria-label={`Operator for ${metric.name}`} defaultValue={metric.target_operator} id={`operator-${metric.id}`}>
                          <option value="gte">≥</option><option value="lte">≤</option>
                        </select>
                        <input aria-label={`Target for ${metric.name}`} type="number" step="any" value={targetValues[metric.id] ?? ""} onChange={(event) => setTargetValues({ ...targetValues, [metric.id]: event.target.value })} />
                        <span>{metric.unit}</span>
                      </div>
                    ) : <strong className="metricTarget">{targetLabel(metric)}</strong>}
                    <div className="actualEditor">
                      <input
                        aria-label={`Actual for ${metric.name}`}
                        type="number"
                        step="any"
                        value={metricValues[metric.id] ?? ""}
                        onChange={(event) => setMetricValues({ ...metricValues, [metric.id]: event.target.value })}
                        placeholder="—"
                        disabled={plan.status !== "approved" || evaluationClosed || archived}
                      />
                      <span>{metric.unit}</span>
                    </div>
                    <span className={`metricResult ${metric.result_status}`}>{metric.result_status}</span>
                    {planEditable ? (
                      <button
                        className="button secondary compact"
                        disabled={busy !== null}
                        onClick={() => {
                          const select = document.getElementById(`operator-${metric.id}`) as HTMLSelectElement;
                          void saveMetricTarget(metric, select.value as MetricOperator);
                        }}
                      >Save target</button>
                    ) : (
                      <button className="button secondary compact" disabled={plan.status !== "approved" || evaluationClosed || archived || busy !== null} onClick={() => saveMetricResult(metric)}>
                        {metric.actual_value === null ? "Record" : "Update"}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </section>

            {plan.status === "approved" ? (
              <section className="panel decisionCard">
                <header className="pocSectionHeader">
                  <div><span className="eyebrow">Final human decision</span><h2>Proceed, iterate, or reject</h2><p>All actual values are required. Failed metrics do not silently block a human override; the rationale records that judgment.</p></div>
                  <div className={`decisionReadiness ${allPassed ? "ready" : ""}`}><strong>{passCount}/{plan.metrics.length}</strong><span>targets passed</span></div>
                </header>
                {!evaluationClosed ? (
                  <div className="decisionControls">
                    <textarea rows={3} value={decisionReason} onChange={(event) => setDecisionReason(event.target.value)} placeholder="Decision rationale (required)" />
                    <div>
                      <button className="button dangerGhost" disabled={!allMeasured || busy !== null || archived} onClick={() => decide("reject")}>Reject</button>
                      <button className="button secondary" disabled={!allMeasured || busy !== null || archived} onClick={() => decide("iterate")}>Iterate</button>
                      <button className="button primary" disabled={!allMeasured || busy !== null || archived} onClick={() => decide("proceed")}>Proceed</button>
                    </div>
                    {!allMeasured ? <small>Record all {plan.metrics.length} metric results to unlock the decision gate.</small> : null}
                  </div>
                ) : <div className="decisionComplete"><strong>Evaluation complete</strong><p>The account is ready for the Business Case stage.</p></div>}
                {plan.decisions.length ? (
                  <div className="decisionHistory">
                    <span>Decision history</span>
                    {plan.decisions.map((decision) => (
                      <article key={decision.id}>
                        <strong className={decision.decision}>{decisionLabels[decision.decision]}</strong>
                        <p>{decision.rationale}</p>
                        <time>{new Date(decision.created_at).toLocaleString()}</time>
                      </article>
                    ))}
                  </div>
                ) : null}
              </section>
            ) : null}
          </main>

          <aside className="pocAside">
            <section className="panel pocStagePanel">
              <div><span>POC stage</span><strong>{statusLabels[initialWorkspace.poc_stage_status]}</strong></div>
              <i />
              <div><span>Evaluation</span><strong>{statusLabels[initialWorkspace.evaluation_stage_status]}</strong></div>
            </section>
            <section className="panel pocGuardrailPanel">
              <span className="eyebrow">Decision guardrails</span>
              <h3>What this gate protects</h3>
              <ul>
                <li>Scope and dataset are approved before testing.</li>
                <li>Targets lock when the POC plan is approved.</li>
                <li>Every decision requires complete actuals and a reason.</li>
                <li>Iterate preserves history and reopens evaluation.</li>
              </ul>
            </section>
          </aside>
        </div>
      ) : null}
    </>
  );
}
