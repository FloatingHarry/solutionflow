"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import type {
  DeploymentChecklistItem,
  DeploymentChecklistStatus,
  DeploymentPlan,
  DeploymentWorkspace as DeploymentWorkspaceData,
} from "@/lib/types";
import { stageLabels, statusLabels } from "@/lib/workflow";


const environmentLabels = {
  saas_api: "SaaS / API",
  eu_cloud: "EU cloud",
  private_on_premise: "Private / on-premise",
};

type ItemDraft = Pick<DeploymentChecklistItem, "owner" | "status" | "evidence_notes">;

function planDraft(plan: DeploymentPlan | null) {
  return {
    owner: plan?.owner ?? "",
    target_launch_date: plan?.target_launch_date ?? "",
    rollout_strategy: plan?.rollout_strategy ?? "",
    integration_plan: plan?.integration_plan ?? "",
    data_governance_plan: plan?.data_governance_plan ?? "",
    monitoring_plan: plan?.monitoring_plan ?? "",
    rollback_plan: plan?.rollback_plan ?? "",
    support_model: plan?.support_model ?? "",
  };
}

function checklistDrafts(plan: DeploymentPlan | null): Record<string, ItemDraft> {
  return Object.fromEntries(
    (plan?.checklist_items ?? []).map((item) => [
      item.id,
      { owner: item.owner, status: item.status, evidence_notes: item.evidence_notes },
    ]),
  );
}

export function DeploymentWorkspace({
  accountId,
  initialWorkspace,
  archived,
}: {
  accountId: string;
  initialWorkspace: DeploymentWorkspaceData;
  archived: boolean;
}) {
  const router = useRouter();
  const [plan, setPlan] = useState(initialWorkspace.plan);
  const [draft, setDraft] = useState(() => planDraft(initialWorkspace.plan));
  const [items, setItems] = useState(() => checklistDrafts(initialWorkspace.plan));
  const [completionNotes, setCompletionNotes] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const editable = !archived && plan?.status !== "completed";
  const completedChecks = useMemo(
    () => plan?.checklist_items.filter((item) => item.status === "completed").length ?? 0,
    [plan],
  );

  function applyPlan(next: DeploymentPlan) {
    setPlan(next);
    setDraft(planDraft(next));
    setItems(checklistDrafts(next));
    router.refresh();
  }

  async function request(path: string, method: "POST" | "PATCH", body?: unknown) {
    const response = await fetch(`/api/backend${path}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    const payload = (await response.json()) as DeploymentPlan & { detail?: string };
    if (!response.ok) throw new Error(payload.detail || "Unable to update deployment.");
    return payload;
  }

  async function generate() {
    setBusy("generate");
    setError(null);
    try {
      applyPlan(await request(`/accounts/${accountId}/deployment-plans/generate`, "POST"));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to generate plan.");
    } finally {
      setBusy(null);
    }
  }

  async function savePlan() {
    if (!plan) return;
    setBusy("plan");
    setError(null);
    try {
      applyPlan(await request(`/deployment-plans/${plan.id}`, "PATCH", {
        ...draft,
        target_launch_date: draft.target_launch_date || null,
      }));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to save plan.");
    } finally {
      setBusy(null);
    }
  }

  async function saveItem(itemId: string) {
    const item = items[itemId];
    if (!item) return;
    setBusy(itemId);
    setError(null);
    try {
      applyPlan(await request(`/deployment-checklist-items/${itemId}`, "PATCH", item));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to save check.");
    } finally {
      setBusy(null);
    }
  }

  async function complete() {
    if (!plan || completionNotes.trim().length < 2) {
      setError("Add completion notes so the final deployment gate remains auditable.");
      return;
    }
    setBusy("complete");
    setError(null);
    try {
      applyPlan(await request(`/deployment-plans/${plan.id}/complete`, "POST", {
        notes: completionNotes.trim(),
      }));
      setCompletionNotes("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to complete plan.");
    } finally {
      setBusy(null);
    }
  }

  if (!plan) {
    return (
      <section className="panel deploymentEmpty emptyState">
        <span className="emptyGlyph">↗</span>
        <h2>{initialWorkspace.business_case_approved ? "Build the production handoff" : "Business case approval required"}</h2>
        <p>{initialWorkspace.business_case_approved
          ? "Generate a structured rollout, operating model, and six production-readiness checks from the approved business case."
          : "Approve the Business Case before starting Deployment."}</p>
        {initialWorkspace.business_case_approved && !archived ? <button className="button primary" disabled={busy !== null} onClick={generate}>Generate deployment plan</button> : null}
        {error ? <p className="inlineError" role="alert">{error}</p> : null}
      </section>
    );
  }

  return (
    <>
      <section className="deploymentMetrics">
        <div><span>Readiness</span><strong>{plan.readiness_score}%</strong><small>{completedChecks}/6 checks complete</small></div>
        <div><span>Environment</span><strong>{environmentLabels[plan.environment]}</strong><small>From approved business case</small></div>
        <div><span>Plan status</span><strong>{plan.status.replaceAll("_", " ")}</strong><small>Human-controlled gate</small></div>
        <div><span>Workflow stage</span><strong>{stageLabels[initialWorkspace.current_stage]}</strong><small>{statusLabels[initialWorkspace.deployment_stage_status]}</small></div>
      </section>

      {error ? <p className="inlineError deploymentError" role="alert">{error}</p> : null}

      <div className="deploymentGrid">
        <main className="deploymentMain">
          <section className="panel deploymentPlanCard">
            <header className="deploymentSectionHeader">
              <div><span className="eyebrow">Production operating plan</span><h2>Move from approval to controlled rollout</h2><p>Every field is an accountable plan—not proof that production deployment has occurred.</p></div>
              <span className={`stageStatusPill ${plan.status}`}>{plan.status.replaceAll("_", " ")}</span>
            </header>
            <div className="deploymentPlanForm">
              <label>Deployment owner<input value={draft.owner} disabled={!editable} onChange={(event) => setDraft((current) => ({ ...current, owner: event.target.value }))} /></label>
              <label>Target launch date<input type="date" value={draft.target_launch_date} disabled={!editable} onChange={(event) => setDraft((current) => ({ ...current, target_launch_date: event.target.value }))} /></label>
              <label>Rollout strategy<textarea rows={4} value={draft.rollout_strategy} disabled={!editable} onChange={(event) => setDraft((current) => ({ ...current, rollout_strategy: event.target.value }))} /></label>
              <label>Integration plan<textarea rows={4} value={draft.integration_plan} disabled={!editable} onChange={(event) => setDraft((current) => ({ ...current, integration_plan: event.target.value }))} /></label>
              <label>Data governance plan<textarea rows={4} value={draft.data_governance_plan} disabled={!editable} onChange={(event) => setDraft((current) => ({ ...current, data_governance_plan: event.target.value }))} /></label>
              <label>Monitoring plan<textarea rows={4} value={draft.monitoring_plan} disabled={!editable} onChange={(event) => setDraft((current) => ({ ...current, monitoring_plan: event.target.value }))} /></label>
              <label>Rollback plan<textarea rows={4} value={draft.rollback_plan} disabled={!editable} onChange={(event) => setDraft((current) => ({ ...current, rollback_plan: event.target.value }))} /></label>
              <label>Support model<textarea rows={4} value={draft.support_model} disabled={!editable} onChange={(event) => setDraft((current) => ({ ...current, support_model: event.target.value }))} /></label>
              {editable ? <button className="button primary" disabled={busy !== null} onClick={savePlan}>Save operating plan</button> : null}
            </div>
          </section>

          <section className="panel deploymentChecklistCard">
            <header className="deploymentSectionHeader"><div><span className="eyebrow">Production readiness</span><h2>Owner-and-evidence checklist</h2><p>A blocked check blocks the Deployment workflow until it is cleared.</p></div><strong className="readinessRing">{plan.readiness_score}%</strong></header>
            <div className="deploymentChecklist">
              {plan.checklist_items.map((item) => {
                const itemDraft = items[item.id];
                return (
                  <article className={`deploymentCheck ${item.status}`} key={item.id}>
                    <div className="deploymentCheckTitle"><span>{String(item.position + 1).padStart(2, "0")}</span><div><small>{item.category}</small><h3>{item.title}</h3></div></div>
                    <label>Owner<input value={itemDraft?.owner ?? ""} disabled={!editable} onChange={(event) => setItems((current) => ({ ...current, [item.id]: { ...current[item.id], owner: event.target.value } }))} /></label>
                    <label>Status<select value={itemDraft?.status ?? item.status} disabled={!editable} onChange={(event) => setItems((current) => ({ ...current, [item.id]: { ...current[item.id], status: event.target.value as DeploymentChecklistStatus } }))}><option value="pending">Pending</option><option value="blocked">Blocked</option><option value="completed">Completed</option></select></label>
                    <label className="deploymentEvidence">Evidence / decision note<textarea rows={2} value={itemDraft?.evidence_notes ?? ""} disabled={!editable} onChange={(event) => setItems((current) => ({ ...current, [item.id]: { ...current[item.id], evidence_notes: event.target.value } }))} /></label>
                    {editable ? <button className="button secondary compact" disabled={busy !== null} onClick={() => saveItem(item.id)}>Save check</button> : <span className={`metricResult ${item.status === "completed" ? "pass" : item.status === "blocked" ? "fail" : "pending"}`}>{item.status}</span>}
                  </article>
                );
              })}
            </div>
          </section>
        </main>

        <aside className="deploymentAside">
          <section className="panel deploymentGuardrail">
            <span className="eyebrow">Release guardrail</span><h3>What completion means</h3>
            <ul><li>All six owners recorded evidence.</li><li>Rollback and support paths are explicit.</li><li>The workflow is ready for an authorized production launch.</li><li>It does not claim production traffic or realized ROI.</li></ul>
          </section>
          <section className="panel deploymentGate">
            <span className="eyebrow">Final workflow gate</span><h3>{plan.status === "completed" ? "Deployment plan complete" : "Complete Deployment"}</h3>
            {plan.status === "completed" ? <blockquote>{plan.completion_notes}</blockquote> : <><p>All checks must be completed first.</p><textarea aria-label="Deployment completion notes" rows={5} value={completionNotes} onChange={(event) => setCompletionNotes(event.target.value)} placeholder="Who approved readiness, and what remains conditional?" /><button className="button primary" disabled={busy !== null || plan.readiness_score !== 100} onClick={complete}>Complete deployment stage</button></>}
          </section>
        </aside>
      </div>
    </>
  );
}
