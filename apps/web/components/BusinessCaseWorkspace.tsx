"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import type {
  AccountBrief,
  BusinessCase,
  BusinessCaseWorkspace as BusinessCaseWorkspaceData,
  CurrencyCode,
  DeploymentOption,
} from "@/lib/types";
import { statusLabels } from "@/lib/workflow";

interface BusinessCaseWorkspaceProps {
  accountId: string;
  initialWorkspace: BusinessCaseWorkspaceData;
  archived: boolean;
}

const caseStatusLabels = {
  draft: "Draft",
  needs_revision: "Needs revision",
  approved: "Approved",
  rejected: "Rejected",
};

const deploymentLabels: Record<DeploymentOption, string> = {
  saas_api: "SaaS / API",
  eu_cloud: "EU cloud",
  private_on_premise: "Private / on-premise",
};

const dimensionLabels = [
  ["cost", "Cost"],
  ["implementation_difficulty", "Implementation"],
  ["data_privacy", "Data privacy"],
  ["scalability", "Scalability"],
  ["maintenance", "Maintenance"],
  ["latency", "Latency"],
  ["compliance", "Compliance"],
] as const;

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

function money(value: number, currency: CurrencyCode) {
  return new Intl.NumberFormat("en", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

function createScenarioDraft(caseData: BusinessCase | null) {
  return {
    currency: caseData?.currency ?? "EUR",
    number_employees: String(caseData?.number_employees ?? 25),
    average_hourly_cost: String(caseData?.average_hourly_cost ?? 45),
    current_time_per_task_minutes: String(caseData?.current_time_per_task_minutes ?? 45),
    tasks_per_employee_per_month: String(caseData?.tasks_per_employee_per_month ?? 20),
    expected_time_reduction_percent: String(caseData?.expected_time_reduction_percent ?? 50),
    monthly_ai_cost: String(caseData?.monthly_ai_cost ?? 2800),
    implementation_cost: String(caseData?.implementation_cost ?? 45000),
  };
}

function createBriefDraft(brief: AccountBrief | null) {
  return {
    executive_summary: brief?.executive_summary ?? "",
    customer_context: brief?.customer_context ?? "",
    confirmed_needs_summary: brief?.confirmed_needs_summary ?? "",
    solution_summary: brief?.solution_summary ?? "",
    poc_summary: brief?.poc_summary ?? "",
    roi_summary: brief?.roi_summary ?? "",
    deployment_summary: brief?.deployment_summary ?? "",
    key_risks: brief?.key_risks.join("\n") ?? "",
    next_steps: brief?.next_steps.join("\n") ?? "",
  };
}

export function BusinessCaseWorkspace({
  accountId,
  initialWorkspace,
  archived,
}: BusinessCaseWorkspaceProps) {
  const router = useRouter();
  const caseData = initialWorkspace.case;
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scenarioDraft, setScenarioDraft] = useState(() => createScenarioDraft(caseData));
  const [deploymentOption, setDeploymentOption] = useState<DeploymentOption>(
    caseData?.recommended_deployment ?? "eu_cloud",
  );
  const [deploymentRationale, setDeploymentRationale] = useState(
    caseData?.deployment_rationale ?? "",
  );
  const [editingBrief, setEditingBrief] = useState(false);
  const [briefDraft, setBriefDraft] = useState(() => createBriefDraft(caseData?.brief ?? null));
  const [reviewNotes, setReviewNotes] = useState(caseData?.review_notes ?? "");

  const editable = Boolean(
    caseData && ["draft", "needs_revision"].includes(caseData.status) && !archived,
  );
  const passCount = caseData?.poc_plan.metrics.filter((metric) => metric.result_status === "pass").length ?? 0;

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

  async function generateCase() {
    await mutate("generate", `/accounts/${accountId}/business-cases/generate`, {});
  }

  async function recalculate() {
    if (!caseData) return;
    const numericFields = Object.entries(scenarioDraft)
      .filter(([key]) => key !== "currency")
      .map(([key, value]) => [key, Number(value)]);
    if (numericFields.some(([, value]) => !Number.isFinite(value))) {
      setError("Every scenario input must be a valid number.");
      return;
    }
    await mutate(
      "scenario",
      `/business-cases/${caseData.id}/scenario`,
      { currency: scenarioDraft.currency, ...Object.fromEntries(numericFields) },
      "PATCH",
    );
  }

  async function saveDeployment() {
    if (!caseData) return;
    await mutate(
      "deployment",
      `/business-cases/${caseData.id}/deployment`,
      {
        recommended_deployment: deploymentOption,
        deployment_rationale: deploymentRationale,
      },
      "PATCH",
    );
  }

  async function saveBrief() {
    if (!caseData) return;
    const saved = await mutate(
      "brief",
      `/account-briefs/${caseData.brief.id}`,
      {
        ...briefDraft,
        key_risks: briefDraft.key_risks.split("\n").map((item) => item.trim()).filter(Boolean),
        next_steps: briefDraft.next_steps.split("\n").map((item) => item.trim()).filter(Boolean),
      },
      "PATCH",
    );
    if (saved) setEditingBrief(false);
  }

  async function review(decision: "approve" | "needs_revision" | "reject") {
    if (!caseData) return;
    await mutate(`review-${decision}`, `/business-cases/${caseData.id}/review`, {
      decision,
      notes: reviewNotes.trim() || "Scenario assumptions, deployment trade-offs, and final brief reviewed by a human.",
    });
  }

  const metricCards = useMemo(() => {
    if (!caseData) return [];
    return [
      { label: "Current monthly cost", value: money(caseData.current_monthly_cost, caseData.currency) },
      { label: "Estimated new cost", value: money(caseData.estimated_new_total_cost, caseData.currency) },
      { label: "Annual savings", value: money(caseData.annual_savings, caseData.currency) },
      { label: "First-year ROI", value: caseData.estimated_first_year_roi_percent === null ? "—" : `${caseData.estimated_first_year_roi_percent.toFixed(1)}%` },
      { label: "Payback", value: caseData.payback_period_months === null ? "—" : `${caseData.payback_period_months.toFixed(1)} mo` },
    ];
  }, [caseData]);

  return (
    <>
      <div className="scenarioBanner">
        <strong>Scenario Estimate</strong>
        <span>Every ROI value below is an editable planning assumption—not a verified or realized customer result.</span>
      </div>

      {error ? <div className="researchError" role="alert"><strong>Could not save</strong><p>{error}</p></div> : null}

      {!initialWorkspace.evaluation_completed ? (
        <section className="researchEmpty businessEmpty">
          <div className="emptyGlyph">⌁</div>
          <h2>Completed evaluation required</h2>
          <p>Record a Proceed decision in the POC workspace before modeling the business case.</p>
          <Link className="button secondary" href={`/accounts/${accountId}/poc`}>Open POC & evaluation</Link>
        </section>
      ) : null}

      {initialWorkspace.evaluation_completed && !caseData ? (
        <section className="panel businessGenerateCard">
          <div>
            <span className="eyebrow">Business decision package</span>
            <h2>Build the scenario, deployment comparison, and final brief</h2>
            <p>Start from the approved solution and completed POC. All financial assumptions remain editable and visibly estimated.</p>
          </div>
          <button className="button primary" disabled={archived || busy !== null} onClick={generateCase}>
            {busy === "generate" ? "Generating…" : "Generate business case"}
          </button>
        </section>
      ) : null}

      {caseData ? (
        <>
          <section className="businessMetrics">
            {metricCards.map((item) => <div key={item.label}><span>{item.label}</span><strong>{item.value}</strong></div>)}
          </section>

          <div className="businessGrid">
            <main className="businessMain">
              <section className="panel roiCard">
                <header className="businessSectionHeader">
                  <div><span className="eyebrow">Scenario-based ROI calculator</span><h2>Economics under explicit assumptions</h2><p>Tasks per month is modeled per participating employee. Recalculate before review.</p></div>
                  <span className={`caseStatus ${caseData.status}`}>{caseStatusLabels[caseData.status]}</span>
                </header>
                <div className="roiForm">
                  <label>Currency<select value={scenarioDraft.currency} disabled={!editable} onChange={(event) => setScenarioDraft({ ...scenarioDraft, currency: event.target.value as CurrencyCode })}><option>EUR</option><option>USD</option><option>GBP</option><option>CNY</option></select></label>
                  <label>Participating employees<input type="number" min="1" value={scenarioDraft.number_employees} disabled={!editable} onChange={(event) => setScenarioDraft({ ...scenarioDraft, number_employees: event.target.value })} /></label>
                  <label>Average hourly cost<input type="number" min="0" step="any" value={scenarioDraft.average_hourly_cost} disabled={!editable} onChange={(event) => setScenarioDraft({ ...scenarioDraft, average_hourly_cost: event.target.value })} /></label>
                  <label>Current minutes per task<input type="number" min="0.1" step="any" value={scenarioDraft.current_time_per_task_minutes} disabled={!editable} onChange={(event) => setScenarioDraft({ ...scenarioDraft, current_time_per_task_minutes: event.target.value })} /></label>
                  <label>Tasks / employee / month<input type="number" min="0.1" step="any" value={scenarioDraft.tasks_per_employee_per_month} disabled={!editable} onChange={(event) => setScenarioDraft({ ...scenarioDraft, tasks_per_employee_per_month: event.target.value })} /></label>
                  <label>Expected time reduction (%)<input type="number" min="0" max="100" step="any" value={scenarioDraft.expected_time_reduction_percent} disabled={!editable} onChange={(event) => setScenarioDraft({ ...scenarioDraft, expected_time_reduction_percent: event.target.value })} /></label>
                  <label>Monthly AI / infrastructure cost<input type="number" min="0" step="any" value={scenarioDraft.monthly_ai_cost} disabled={!editable} onChange={(event) => setScenarioDraft({ ...scenarioDraft, monthly_ai_cost: event.target.value })} /></label>
                  <label>One-time implementation cost<input type="number" min="0" step="any" value={scenarioDraft.implementation_cost} disabled={!editable} onChange={(event) => setScenarioDraft({ ...scenarioDraft, implementation_cost: event.target.value })} /></label>
                </div>
                <div className="roiFormula">
                  <div><span>Gross labor savings</span><strong>{money(caseData.current_monthly_cost - caseData.estimated_new_labor_cost, caseData.currency)}</strong></div>
                  <span>−</span><div><span>AI operating cost</span><strong>{money(caseData.monthly_ai_cost, caseData.currency)}</strong></div>
                  <span>=</span><div><span>Net monthly savings</span><strong>{money(caseData.monthly_savings, caseData.currency)}</strong></div>
                </div>
                {editable ? <div className="businessCardActions"><button className="button primary" disabled={busy !== null} onClick={recalculate}>Recalculate scenario</button></div> : null}
              </section>

              <section className="panel deploymentCard">
                <header className="businessSectionHeader"><div><span className="eyebrow">Deployment trade-off analysis</span><h2>Compare the operating model</h2><p>Ratings are deterministic planning guidance and require security, compliance, and procurement validation.</p></div></header>
                <div className="deploymentComparison">
                  {caseData.deployment_assessments.map((assessment) => (
                    <article className={assessment.option === caseData.recommended_deployment ? "recommended" : ""} key={assessment.id}>
                      <div className="deploymentTitle"><span>{assessment.option === caseData.recommended_deployment ? "Recommended" : "Option"}</span><h3>{deploymentLabels[assessment.option]}</h3></div>
                      <dl>{dimensionLabels.map(([key, label]) => <div key={key}><dt>{label}</dt><dd className={`rating ${assessment[key]}`}>{assessment[key]}</dd></div>)}</dl>
                      <ul>{assessment.notes.map((note) => <li key={note}>{note}</li>)}</ul>
                    </article>
                  ))}
                </div>
                <div className="deploymentRecommendation">
                  <label>Recommended option<select value={deploymentOption} disabled={!editable} onChange={(event) => setDeploymentOption(event.target.value as DeploymentOption)}>{Object.entries(deploymentLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
                  <label>Recommendation rationale<textarea rows={3} value={deploymentRationale} disabled={!editable} onChange={(event) => setDeploymentRationale(event.target.value)} /></label>
                  {editable ? <button className="button primary" disabled={busy !== null} onClick={saveDeployment}>Save recommendation</button> : null}
                </div>
              </section>

              <section className="panel accountBriefCard">
                <header className="businessSectionHeader"><div><span className="eyebrow">Final account brief</span><h2>Evidence-to-decision summary</h2><p>A structured handoff for finance, security, procurement, and deployment owners.</p></div>{editable && !editingBrief ? <button className="button secondary" onClick={() => setEditingBrief(true)}>Edit brief</button> : null}</header>
                {editingBrief ? (
                  <div className="briefEditor">
                    <label>Executive summary<textarea rows={4} value={briefDraft.executive_summary} onChange={(event) => setBriefDraft({ ...briefDraft, executive_summary: event.target.value })} /></label>
                    <label>Customer context<textarea rows={3} value={briefDraft.customer_context} onChange={(event) => setBriefDraft({ ...briefDraft, customer_context: event.target.value })} /></label>
                    <label>Confirmed needs<textarea rows={3} value={briefDraft.confirmed_needs_summary} onChange={(event) => setBriefDraft({ ...briefDraft, confirmed_needs_summary: event.target.value })} /></label>
                    <label>Solution summary<textarea rows={3} value={briefDraft.solution_summary} onChange={(event) => setBriefDraft({ ...briefDraft, solution_summary: event.target.value })} /></label>
                    <label>POC summary<textarea rows={3} value={briefDraft.poc_summary} onChange={(event) => setBriefDraft({ ...briefDraft, poc_summary: event.target.value })} /></label>
                    <label>ROI summary<textarea rows={4} value={briefDraft.roi_summary} onChange={(event) => setBriefDraft({ ...briefDraft, roi_summary: event.target.value })} /></label>
                    <label>Deployment summary<textarea rows={3} value={briefDraft.deployment_summary} onChange={(event) => setBriefDraft({ ...briefDraft, deployment_summary: event.target.value })} /></label>
                    <label>Key risks (one per line)<textarea rows={5} value={briefDraft.key_risks} onChange={(event) => setBriefDraft({ ...briefDraft, key_risks: event.target.value })} /></label>
                    <label>Next steps (one per line)<textarea rows={5} value={briefDraft.next_steps} onChange={(event) => setBriefDraft({ ...briefDraft, next_steps: event.target.value })} /></label>
                    <div className="formActions"><button className="button secondary" onClick={() => setEditingBrief(false)}>Cancel</button><button className="button primary" disabled={busy !== null} onClick={saveBrief}>Save brief</button></div>
                  </div>
                ) : (
                  <div className="briefBody">
                    <article className="briefLead"><span>Executive summary</span><p>{caseData.brief.executive_summary}</p></article>
                    <article><span>Customer context</span><p>{caseData.brief.customer_context}</p></article>
                    <article><span>Confirmed needs</span><p>{caseData.brief.confirmed_needs_summary}</p></article>
                    <article><span>Accepted solution</span><p>{caseData.brief.solution_summary}</p></article>
                    <article><span>POC outcome</span><p>{caseData.brief.poc_summary}</p></article>
                    <article className="briefEstimate"><span>Scenario ROI</span><p>{caseData.brief.roi_summary}</p></article>
                    <article><span>Deployment recommendation</span><p>{caseData.brief.deployment_summary}</p></article>
                    <article><span>Key risks</span><ul>{caseData.brief.key_risks.map((item) => <li key={item}>{item}</li>)}</ul></article>
                    <article><span>Next steps</span><ol>{caseData.brief.next_steps.map((item) => <li key={item}>{item}</li>)}</ol></article>
                  </div>
                )}
                <div className="businessTrace"><span>Traceability</span><Link href={`/accounts/${accountId}/poc`}>Brief → ROI & deployment → Proceed decision → POC metrics ↗</Link><Link href={`/accounts/${accountId}/solutions`}>POC → accepted solution → confirmed needs → customer evidence ↗</Link></div>
              </section>

              {editable ? (
                <section className="panel businessReviewGate">
                  <div><span className="eyebrow">Final human gate</span><h2>Approve before Deployment</h2><p>Confirm scenario assumptions, deployment trade-offs, the evidence chain, risks, and ownership.</p></div>
                  <textarea rows={3} value={reviewNotes} onChange={(event) => setReviewNotes(event.target.value)} placeholder="What was validated, by whom, and what remains conditional?" />
                  <div><button className="button dangerGhost" disabled={busy !== null} onClick={() => review("reject")}>Reject</button><button className="button secondary" disabled={busy !== null} onClick={() => review("needs_revision")}>Needs revision</button><button className="button primary" disabled={busy !== null} onClick={() => review("approve")}>Approve business case</button></div>
                </section>
              ) : caseData.review_notes ? <blockquote className="businessReviewNote">{caseData.review_notes}</blockquote> : null}
            </main>

            <aside className="businessAside">
              <section className="panel businessStagePanel"><div><span>Business case</span><strong>{statusLabels[initialWorkspace.business_case_stage_status]}</strong></div><i /><div><span>Deployment</span><strong>{statusLabels[initialWorkspace.deployment_stage_status]}</strong></div></section>
              <section className="panel businessSourcePanel"><span className="eyebrow">Evidence inputs</span><h3>Decision package</h3><dl><div><dt>Accepted solution</dt><dd>{caseData.poc_plan.solution_proposal.template.name}</dd></div><div><dt>POC metrics passed</dt><dd>{passCount}/{caseData.poc_plan.metrics.length}</dd></div><div><dt>POC decision</dt><dd>{caseData.poc_plan.decisions[0]?.decision ?? "—"}</dd></div><div><dt>Confirmed needs</dt><dd>{caseData.poc_plan.solution_proposal.derived_needs.length}</dd></div></dl></section>
              <section className="panel assumptionsPanel"><span className="eyebrow">Scenario assumptions</span><h3>Validate with owners</h3><ul>{caseData.assumptions.map((item) => <li key={item}>{item}</li>)}</ul></section>
            </aside>
          </div>
        </>
      ) : null}
    </>
  );
}
