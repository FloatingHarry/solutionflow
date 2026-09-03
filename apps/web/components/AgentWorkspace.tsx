"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";

import type { AgentRun, AgentWorkspace as AgentWorkspaceData, ApiErrorPayload } from "@/lib/types";


interface AgentWorkspaceProps {
  accountName: string;
  initialWorkspace: AgentWorkspaceData;
  readOnly?: boolean;
}

function AgentGlyph() {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <path d="M6 16h5l2.6-6 4.7 12 2.5-6H26" />
      <circle cx="16" cy="16" r="13" />
    </svg>
  );
}

function getErrorMessage(payload: ApiErrorPayload, fallback: string) {
  if (typeof payload.detail === "string") return payload.detail;
  if (Array.isArray(payload.detail)) {
    return payload.detail.map((item) => item.msg).filter(Boolean).join(", ") || fallback;
  }
  return fallback;
}

function formatStage(stage: string) {
  return stage.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function AgentWorkspace({ accountName, initialWorkspace, readOnly = false }: AgentWorkspaceProps) {
  const router = useRouter();
  const [workspace, setWorkspace] = useState(initialWorkspace);
  const [goal, setGoal] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const latestRun = workspace.runs[0] ?? null;
  const recentRuns = useMemo(() => workspace.runs.slice(1, 4), [workspace.runs]);

  async function requestAgent(requestedGoal: string) {
    const cleanGoal = requestedGoal.trim();
    if (cleanGoal.length < 3 || busy || readOnly) return;
    setBusy("run");
    setError(null);
    try {
      const response = await fetch(`/api/backend/accounts/${workspace.account_id}/agent/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal: cleanGoal }),
      });
      const payload = (await response.json()) as AgentRun & ApiErrorPayload;
      if (!response.ok) throw new Error(getErrorMessage(payload, "The agent could not create a plan."));
      setWorkspace((current) => ({ ...current, mode: payload.provider, model: payload.model, runs: [payload, ...current.runs] }));
      setGoal("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "The agent could not create a plan.");
    } finally {
      setBusy(null);
    }
  }

  async function submitGoal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await requestAgent(goal);
  }

  async function decide(run: AgentRun, decision: "approve" | "reject") {
    if (busy || readOnly) return;
    setBusy(decision);
    setError(null);
    try {
      const response = await fetch(`/api/backend/agent-runs/${run.id}/${decision}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const payload = (await response.json()) as AgentRun & ApiErrorPayload;
      if (!response.ok) throw new Error(getErrorMessage(payload, `Unable to ${decision} this action.`));
      setWorkspace((current) => ({
        ...current,
        runs: current.runs.map((item) => item.id === payload.id ? payload : item),
      }));
      router.refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : `Unable to ${decision} this action.`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="agentWorkspace" id="account-agent" aria-labelledby="agent-title">
      <header className="agentWorkspaceHeader">
        <div className="agentIdentity">
          <span className="agentGlyph"><AgentGlyph /></span>
          <div>
            <span className="eyebrow"><i /> Account Agent</span>
            <h2 id="agent-title">Turn a goal into the next safe move.</h2>
            <p>The agent reads {accountName}&apos;s state, selects tools, and pauses before every record-changing action.</p>
          </div>
        </div>
        <div className={`agentMode ${workspace.mode}`}>
          <i />
          <span>{workspace.mode === "openai" ? "OpenAI live agent" : "Guided agent preview"}</span>
          <strong>{workspace.model ?? "No API key required"}</strong>
        </div>
      </header>

      <div className="agentCanvas">
        <div className="agentConversation">
          {latestRun ? (
            <>
              <div className="agentUserMessage">
                <span>You</span>
                <p>{latestRun.goal}</p>
              </div>
              <article className="agentResponse" data-status={latestRun.status}>
                <div className="agentResponseTopline">
                  <span className="agentMiniGlyph"><AgentGlyph /></span>
                  <div><strong>SolutionFlow Agent</strong><small>{formatStage(latestRun.stage_snapshot)} · {latestRun.provider === "openai" ? "Live reasoning" : "Deterministic guidance"}</small></div>
                  <em>{latestRun.status.replaceAll("_", " ")}</em>
                </div>
                <p className="agentSummary">{latestRun.summary}</p>

                <div className="agentEvidenceGrid">
                  <div>
                    <span className="agentSectionLabel">Observed</span>
                    <ul>{latestRun.observations.map((item) => <li key={item}>{item}</li>)}</ul>
                  </div>
                  <div>
                    <span className="agentSectionLabel">Execution plan</span>
                    <ol>{latestRun.plan.map((item, index) => <li key={item}><span>{String(index + 1).padStart(2, "0")}</span>{item}</li>)}</ol>
                  </div>
                </div>

                {latestRun.action ? (
                  <div className="agentActionCard" data-action-status={latestRun.action.status}>
                    <div className="agentActionNumber">NEXT</div>
                    <div className="agentActionCopy">
                      <span>{latestRun.action.requires_approval ? "Approval required" : "Recommended handoff"}</span>
                      <h3>{latestRun.action.title}</h3>
                      <p>{latestRun.action.description}</p>
                      <small>{latestRun.action.reason}</small>
                    </div>
                    <div className="agentActionControls">
                      {latestRun.action.status === "pending" ? (
                        <>
                          <button className="button agentApprove" disabled={Boolean(busy)} onClick={() => decide(latestRun, "approve")}>{busy === "approve" ? "Executing…" : "Approve & execute"}</button>
                          <button className="button subtle" disabled={Boolean(busy)} onClick={() => decide(latestRun, "reject")}>Reject</button>
                        </>
                      ) : latestRun.action.target_path ? (
                        <button className="button agentOpen" onClick={() => router.push(latestRun.action!.target_path!)}>Open workspace <span>↗</span></button>
                      ) : null}
                    </div>
                  </div>
                ) : null}

                <div className="agentTrace">
                  <span>Tool trace</span>
                  {latestRun.trace.map((item, index) => <i key={`${String(item.tool)}-${index}`}>{String(item.tool ?? "workflow check").replaceAll("_", " ")}</i>)}
                  <strong>{latestRun.trace.length} checks</strong>
                </div>
                {latestRun.error_message ? <p className="agentFallbackNote">{latestRun.error_message}</p> : null}
              </article>
            </>
          ) : (
            <div className="agentEmptyState">
              <span className="agentEmptyOrbit"><AgentGlyph /></span>
              <span className="eyebrow">Goal-driven workspace</span>
              <h3>Tell me the outcome—not the form to fill.</h3>
              <p>I will inspect the account, locate the active gate, and prepare one controlled next action.</p>
            </div>
          )}

          <form className="agentComposer" onSubmit={submitGoal}>
            <label htmlFor="agent-goal">What outcome should the agent move toward?</label>
            <div>
              <textarea id="agent-goal" value={goal} onChange={(event) => setGoal(event.target.value)} placeholder="Example: Prepare this account for a credible POC without skipping human review." disabled={readOnly || Boolean(busy)} rows={2} />
              <button type="submit" disabled={readOnly || Boolean(busy) || goal.trim().length < 3} aria-label="Run Account Agent"><span>{busy === "run" ? "Working" : "Run agent"}</span><i>→</i></button>
            </div>
          </form>
          {error ? <p className="formError agentError">{error}</p> : null}
          {readOnly ? <p className="agentReadOnly">Restore this account before starting another agent run.</p> : null}
        </div>

        <aside className="agentSideRail">
          <div className="agentStarterBlock">
            <span className="agentSectionLabel">Start with an outcome</span>
            {workspace.starter_prompts.map((prompt) => (
              <button key={prompt} disabled={readOnly || Boolean(busy)} onClick={() => requestAgent(prompt)}>{prompt}<span>↗</span></button>
            ))}
          </div>
          <div className="agentBoundaryBlock">
            <span className="agentSectionLabel">Operating boundary</span>
            <ul>{workspace.capabilities.slice(0, 4).map((capability) => <li key={capability}><i />{capability}</li>)}</ul>
          </div>
          {recentRuns.length ? (
            <div className="agentHistoryBlock">
              <span className="agentSectionLabel">Recent runs</span>
              {recentRuns.map((run) => <div key={run.id}><span>{formatStage(run.stage_snapshot)}</span><p>{run.goal}</p><small>{run.status.replaceAll("_", " ")}</small></div>)}
            </div>
          ) : null}
        </aside>
      </div>
    </section>
  );
}
