"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { stageOrder } from "@/lib/types";
import type {
  DeploymentOption,
  SolutionMatch,
  SolutionProposal,
  SolutionProposalStatus,
  SolutionWorkspace as SolutionWorkspaceData,
} from "@/lib/types";

interface SolutionWorkspaceProps {
  accountId: string;
  initialWorkspace: SolutionWorkspaceData;
  archived: boolean;
}

const deploymentLabels: Record<DeploymentOption, string> = {
  saas_api: "SaaS / API",
  eu_cloud: "EU cloud",
  private_on_premise: "Private / on-premise",
};

const proposalStatusLabels: Record<SolutionProposalStatus, string> = {
  draft: "Draft",
  needs_revision: "Needs revision",
  accepted: "Accepted",
  rejected: "Rejected",
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

export function SolutionWorkspace({
  accountId,
  initialWorkspace,
  archived,
}: SolutionWorkspaceProps) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deploymentByMatch, setDeploymentByMatch] = useState<Record<string, DeploymentOption>>({});
  const [reviewNotes, setReviewNotes] = useState<Record<string, string>>({});
  const [editingProposal, setEditingProposal] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState({
    title: "",
    executive_summary: "",
    why_fit: "",
    expected_business_impact: "",
  });
  const solutionClosed =
    stageOrder.indexOf(initialWorkspace.current_stage) > stageOrder.indexOf("solution");

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

  async function generateMatches() {
    await mutate("matches", `/accounts/${accountId}/solutions/matches`, { top_per_need: 3 });
  }

  async function createProposal(match: SolutionMatch) {
    const deployment =
      deploymentByMatch[match.id] ?? match.template.deployment_options[0];
    await mutate(`proposal-${match.id}`, `/accounts/${accountId}/solution-proposals`, {
      solution_template_id: match.template.id,
      need_ids: [match.confirmed_need_id],
      deployment_option: deployment,
    });
  }

  function beginEdit(proposal: SolutionProposal) {
    setEditingProposal(proposal.id);
    setEditDraft({
      title: proposal.title,
      executive_summary: proposal.executive_summary,
      why_fit: proposal.why_fit,
      expected_business_impact: proposal.expected_business_impact,
    });
  }

  async function saveProposal(proposalId: string) {
    const saved = await mutate(
      `edit-${proposalId}`,
      `/solution-proposals/${proposalId}`,
      editDraft,
      "PATCH",
    );
    if (saved) setEditingProposal(null);
  }

  async function reviewProposal(
    proposal: SolutionProposal,
    decision: "accept" | "reject" | "needs_revision",
  ) {
    await mutate(`review-${proposal.id}`, `/solution-proposals/${proposal.id}/review`, {
      decision,
      notes: reviewNotes[proposal.id]?.trim() || "Solution proposal reviewed by a human.",
    });
  }

  return (
    <>
      <section className="solutionMetrics">
        <div><span>Catalog patterns</span><strong>{initialWorkspace.catalog.length}</strong></div>
        <div><span>Confirmed needs</span><strong>{initialWorkspace.confirmed_needs.length}</strong></div>
        <div><span>Matches</span><strong>{initialWorkspace.matches.length}</strong></div>
        <div><span>Proposals</span><strong>{initialWorkspace.proposals.length}</strong></div>
      </section>

      <div className="simulationBanner solutionSimulation">
        <strong>Demo / simulated solution catalog</strong>
        <span>These four catalog entries are product patterns for workflow validation. They are not vendor quotes, production commitments, or verified pricing.</span>
      </div>

      {!initialWorkspace.discovery_approved ? (
        <div className="discoveryPrerequisite">
          <strong>Discovery approval required</strong>
          <p>Confirm a customer need and approve Discovery before matching solution patterns.</p>
        </div>
      ) : null}

      {error ? <div className="researchError" role="alert"><strong>Could not save</strong><p>{error}</p></div> : null}

      <div className="solutionGrid">
        <main className="solutionMain">
          <section className="panel solutionMatchHeader">
            <div>
              <span className="eyebrow">Need-to-solution matching</span>
              <h2>Rank catalog patterns</h2>
              <p>Matching is deterministic and explainable. Scores suggest what to inspect; they do not approve a solution.</p>
            </div>
            <button
              className="button primary"
              disabled={archived || solutionClosed || !initialWorkspace.discovery_approved || busy !== null}
              onClick={generateMatches}
            >
              {busy === "matches" ? "Matching…" : initialWorkspace.matches.length ? "Refresh matches" : "Generate matches"}
            </button>
          </section>

          {!initialWorkspace.matches.length ? (
            <section className="researchEmpty solutionEmpty">
              <div className="emptyGlyph">⌁</div>
              <h2>No solution matches yet</h2>
              <p>Use confirmed customer needs to rank the simulated catalog and inspect the rationale.</p>
            </section>
          ) : (
            <section className="matchSection">
              <div className="sectionHeadingPlain">
                <span className="eyebrow">Ranked recommendations</span>
                <h2>Matches requiring human judgment</h2>
              </div>
              <div className="matchList">
                {initialWorkspace.matches.map((match, index) => {
                  const need = initialWorkspace.confirmed_needs.find(
                    (item) => item.id === match.confirmed_need_id,
                  );
                  return (
                    <article className="panel solutionMatchCard" key={match.id}>
                      <div className="matchScore">
                        <strong>{match.score}</strong><span>/ 100</span>
                      </div>
                      <div className="matchBody">
                        <div className="matchBadges"><span>Rank {index + 1}</span><span>{match.template.slug.replaceAll("-", " ")}</span></div>
                        <h3>{match.template.name}</h3>
                        <p>{match.template.description}</p>
                        <div className="matchNeed"><span>Mapped need</span><strong>{need?.title ?? "Confirmed need"}</strong></div>
                        <blockquote>{match.rationale}</blockquote>
                        {match.matched_terms.length ? <div className="termList">{match.matched_terms.map((term) => <span key={term}>{term}</span>)}</div> : null}
                      </div>
                      <div className="matchActions">
                        <label>
                          Deployment
                          <select
                            aria-label={`Deployment for ${match.template.name}`}
                            value={deploymentByMatch[match.id] ?? match.template.deployment_options[0]}
                            onChange={(event) => setDeploymentByMatch({
                              ...deploymentByMatch,
                              [match.id]: event.target.value as DeploymentOption,
                            })}
                          >
                            {match.template.deployment_options.map((option) => (
                              <option value={option} key={option}>{deploymentLabels[option]}</option>
                            ))}
                          </select>
                        </label>
                        <button
                          className="button primary"
                          disabled={archived || solutionClosed || busy !== null}
                          onClick={() => createProposal(match)}
                        >
                          Build proposal
                        </button>
                      </div>
                    </article>
                  );
                })}
              </div>
            </section>
          )}

          {initialWorkspace.proposals.length ? (
            <section className="proposalSection">
              <div className="sectionHeadingPlain">
                <span className="eyebrow">Human-owned deliverable</span>
                <h2>Solution proposals</h2>
              </div>
              <div className="proposalList">
                {initialWorkspace.proposals.map((proposal) => (
                  <article className="panel proposalCard" key={proposal.id}>
                    <header className="proposalHeader">
                      <div>
                        <div className="proposalBadges">
                          <span className={`proposalStatus ${proposal.status}`}>{proposalStatusLabels[proposal.status]}</span>
                          <span>{deploymentLabels[proposal.deployment_option]}</span>
                          <span>Derived from {proposal.derived_needs.length} need{proposal.derived_needs.length === 1 ? "" : "s"}</span>
                        </div>
                        <h2>{proposal.title}</h2>
                        <p>{proposal.executive_summary}</p>
                      </div>
                      {!solutionClosed && !archived && ["draft", "needs_revision"].includes(proposal.status) ? (
                        <button className="button secondary" onClick={() => beginEdit(proposal)}>Edit proposal</button>
                      ) : null}
                    </header>

                    {editingProposal === proposal.id ? (
                      <div className="proposalEditor twoColumnForm">
                        <label className="fullField">Title<input value={editDraft.title} onChange={(event) => setEditDraft({ ...editDraft, title: event.target.value })} /></label>
                        <label className="fullField">Executive summary<textarea rows={3} value={editDraft.executive_summary} onChange={(event) => setEditDraft({ ...editDraft, executive_summary: event.target.value })} /></label>
                        <label className="fullField">Why this fits<textarea rows={3} value={editDraft.why_fit} onChange={(event) => setEditDraft({ ...editDraft, why_fit: event.target.value })} /></label>
                        <label className="fullField">Expected impact<textarea rows={2} value={editDraft.expected_business_impact} onChange={(event) => setEditDraft({ ...editDraft, expected_business_impact: event.target.value })} /></label>
                        <div className="formActions fullField"><button className="button secondary" onClick={() => setEditingProposal(null)}>Cancel</button><button className="button primary" disabled={busy !== null} onClick={() => saveProposal(proposal.id)}>Save proposal</button></div>
                      </div>
                    ) : (
                      <div className="proposalBody">
                        <section className="proposalNarrative">
                          <div><span>Why this solution</span><p>{proposal.why_fit}</p></div>
                          <div><span>Expected business impact</span><p>{proposal.expected_business_impact}</p></div>
                          <div><span>Architecture</span><p className="architectureFlow">{proposal.architecture}</p></div>
                        </section>
                        <section className="proposalDetails">
                          <div><span>Required data</span><ul>{proposal.required_data.map((item) => <li key={item}>{item}</li>)}</ul></div>
                          <div><span>Models & tools</span><ul>{proposal.model_tool_requirements.map((item) => <li key={item}>{item}</li>)}</ul></div>
                          <div><span>Security & compliance</span><ul>{proposal.security_considerations.map((item) => <li key={item}>{item}</li>)}</ul></div>
                          <div><span>Risks & limitations</span><ul>{proposal.risks.map((item) => <li key={item}>{item}</li>)}</ul></div>
                          <div className="successMetricBox"><span>POC success metrics</span><ul>{proposal.success_metrics.map((item) => <li key={item}>{item}</li>)}</ul></div>
                        </section>
                      </div>
                    )}

                    <div className="proposalTrace">
                      <span>Traceability</span>
                      {proposal.derived_needs.map((need) => (
                        <Link href={`/accounts/${accountId}/discovery`} key={need.id}>
                          Solution → {need.title} → customer answer → hypothesis → evidence ↗
                        </Link>
                      ))}
                    </div>

                    {!solutionClosed && !archived && ["draft", "needs_revision"].includes(proposal.status) ? (
                      <div className="proposalReview">
                        <input
                          aria-label={`Review notes for ${proposal.title}`}
                          value={reviewNotes[proposal.id] ?? proposal.review_notes ?? ""}
                          onChange={(event) => setReviewNotes({ ...reviewNotes, [proposal.id]: event.target.value })}
                          placeholder="Human review notes"
                        />
                        <div>
                          <button className="button dangerGhost" disabled={busy !== null} onClick={() => reviewProposal(proposal, "reject")}>Reject</button>
                          <button className="button secondary" disabled={busy !== null} onClick={() => reviewProposal(proposal, "needs_revision")}>Needs revision</button>
                          <button className="button primary" disabled={busy !== null} onClick={() => reviewProposal(proposal, "accept")}>Accept solution</button>
                        </div>
                      </div>
                    ) : proposal.review_notes ? <blockquote className="proposalReviewNote">{proposal.review_notes}</blockquote> : null}
                  </article>
                ))}
              </div>
            </section>
          ) : null}
        </main>

        <aside className="solutionAside">
          <section className="panel confirmedNeedPanel">
            <div className="panelHeading"><div><span className="eyebrow">Source of truth</span><h2>Confirmed needs</h2></div></div>
            <div className="solutionNeedList">
              {initialWorkspace.confirmed_needs.map((need) => (
                <article key={need.id}>
                  <strong>{need.title}</strong>
                  <p>{need.description}</p>
                  <div><span>Success metric</span>{need.success_metric}</div>
                  {need.constraints ? <div><span>Constraints</span>{need.constraints}</div> : null}
                </article>
              ))}
              {!initialWorkspace.confirmed_needs.length ? <p className="emptyInline">No confirmed customer needs.</p> : null}
            </div>
          </section>

          <section className="panel catalogPanel">
            <div className="panelHeading"><div><span className="eyebrow">Internal knowledge base</span><h2>Demo catalog</h2></div><span>{initialWorkspace.catalog.length}</span></div>
            <div className="catalogList">
              {initialWorkspace.catalog.map((template) => (
                <details key={template.id}>
                  <summary><span>{template.name.slice(0, 2).toUpperCase()}</span><strong>{template.name}</strong></summary>
                  <p>{template.description}</p>
                  <div><strong>Target pains</strong><ul>{template.target_pain_points.map((item) => <li key={item}>{item}</li>)}</ul></div>
                  <div><strong>Example uses</strong><ul>{template.example_use_cases.map((item) => <li key={item}>{item}</li>)}</ul></div>
                  <small>{template.estimated_cost_model}</small>
                </details>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </>
  );
}
