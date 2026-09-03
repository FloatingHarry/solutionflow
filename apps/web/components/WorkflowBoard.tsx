"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import type { StageName, StageStatus, Workflow } from "@/lib/types";
import { getWorkflowProgress, stageLabels, statusLabels } from "@/lib/workflow";


interface WorkflowBoardProps {
  accountId: string;
  initialWorkflow: Workflow;
  readOnly?: boolean;
  managedStages?: StageName[];
}

export function WorkflowBoard({
  accountId,
  initialWorkflow,
  readOnly = false,
  managedStages = [],
}: WorkflowBoardProps) {
  const router = useRouter();
  const [workflow, setWorkflow] = useState(initialWorkflow);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const progress = useMemo(() => getWorkflowProgress(workflow.stages), [workflow.stages]);
  const current = workflow.stages.find((stage) => stage.stage === workflow.current_stage);
  const currentIsManaged = current ? managedStages.includes(current.stage) : false;
  const managedWorkspace = current?.stage === "research"
    ? {
        href: `/accounts/${accountId}/research`,
        label: "Open research workspace",
        description: "Approve cited research before moving into opportunity discovery.",
      }
    : current?.stage === "solution"
      ? {
          href: `/accounts/${accountId}/solutions`,
          label: "Open solutions workspace",
          description: "Match confirmed needs and approve a traceable solution proposal.",
        }
      : current?.stage === "poc" || current?.stage === "evaluation"
        ? {
            href: `/accounts/${accountId}/poc`,
            label: "Open POC & evaluation",
            description: "Approve a bounded POC, record actual metrics, and make a human decision.",
          }
        : current?.stage === "business_case"
          ? {
              href: `/accounts/${accountId}/business-case`,
              label: "Open business case",
              description: "Validate scenario ROI, deployment trade-offs, and the final account brief.",
            }
          : current?.stage === "deployment"
            ? {
                href: `/accounts/${accountId}/deployment`,
                label: "Open deployment workspace",
                description: "Assign owners, clear production-readiness checks, and complete the final gate.",
              }
          : {
          href: `/accounts/${accountId}/discovery`,
          label: "Open discovery workspace",
          description: "Validate hypotheses with customer answers and a human approval gate.",
            };

  async function transition(stage: StageName, status: StageStatus) {
    if (reason.trim().length < 2) {
      setError("Add a short reason so the transition remains auditable.");
      return;
    }
    setBusy(true);
    setError(null);
    const response = await fetch(`/api/backend/accounts/${accountId}/workflow/transitions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stage, status, reason: reason.trim() }),
    });
    const payload = (await response.json()) as Workflow & { detail?: string };
    setBusy(false);
    if (!response.ok) {
      setError(payload.detail || "Unable to update the workflow.");
      return;
    }
    setWorkflow(payload);
    setReason("");
    router.refresh();
  }

  return (
    <section className="panel workflowPanel">
      <div className="panelHeading workflowHeading">
        <div>
          <span className="eyebrow">Account workflow</span>
          <h2>Evidence to decision</h2>
        </div>
        <div className="progressValue"><strong>{progress}%</strong><span>complete</span></div>
      </div>
      <div className="progressTrack" aria-label={`${progress}% complete`}>
        <span style={{ width: `${progress}%` }} />
      </div>
      <div className="stageRail">
        {workflow.stages.map((stage, index) => (
          <div className={`stageItem ${stage.status}`} key={stage.stage}>
            <div className="stageMarker">
              {stage.status === "completed" ? "✓" : String(index + 1).padStart(2, "0")}
            </div>
            <div>
              <strong>{stageLabels[stage.stage]}</strong>
              <span>{statusLabels[stage.status]}</span>
            </div>
          </div>
        ))}
      </div>

      {!readOnly && current?.status !== "completed" && currentIsManaged ? (
        <div className="transitionBox managedTransition">
          <div>
            <span className="eyebrow">Current stage</span>
            <h3>{current ? stageLabels[current.stage] : "Workflow complete"}</h3>
          </div>
          <div>
            <p>{managedWorkspace.description}</p>
            <Link className="button primary" href={managedWorkspace.href}>
              {managedWorkspace.label}
            </Link>
          </div>
        </div>
      ) : null}

      {!readOnly && current?.status !== "completed" && !currentIsManaged ? (
        <div className="transitionBox">
          <div>
            <span className="eyebrow">Current stage</span>
            <h3>{current ? stageLabels[current.stage] : "Workflow complete"}</h3>
          </div>
          <div className="transitionControls">
            <input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Reason for this update" maxLength={500} />
            <div className="transitionActions">
              {current?.status === "not_started" ? (
                <button className="button primary" disabled={busy} onClick={() => transition(current.stage, "in_progress")}>Start stage</button>
              ) : null}
              {current?.status === "in_progress" ? (
                <>
                  <button className="button secondary" disabled={busy} onClick={() => transition(current.stage, "blocked")}>Mark blocked</button>
                  <button className="button primary" disabled={busy} onClick={() => transition(current.stage, "completed")}>Complete stage</button>
                </>
              ) : null}
              {current?.status === "blocked" ? (
                <>
                  <button className="button secondary" disabled={busy} onClick={() => transition(current.stage, "in_progress")}>Resume</button>
                  <button className="button primary" disabled={busy} onClick={() => transition(current.stage, "completed")}>Complete stage</button>
                </>
              ) : null}
            </div>
          </div>
          {error ? <p className="inlineError" role="alert">{error}</p> : null}
        </div>
      ) : null}
    </section>
  );
}
