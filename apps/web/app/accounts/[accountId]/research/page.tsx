import Link from "next/link";
import { notFound } from "next/navigation";

import { ResearchActions } from "@/components/ResearchActions";
import { ApiError, apiGet } from "@/lib/api";
import type {
  Account,
  EvidenceConfidence,
  ProfileClaim,
  ProfileSection,
  ResearchStatus,
  ResearchWorkspace,
} from "@/lib/types";
import { getInitials } from "@/lib/workflow";

export const dynamic = "force-dynamic";

const sectionLabels: Record<ProfileSection, string> = {
  company_overview: "Company overview",
  products_services: "Products & services",
  market_geography: "Markets & geography",
  customers: "Customers",
  recent_developments: "Recent developments",
  financial_operating_signals: "Financial & operating signals",
  ai_digital_initiatives: "AI & digital initiatives",
  potential_strategic_priorities: "Potential strategic priorities",
};

const statusLabels: Record<ResearchStatus, string> = {
  queued: "Queued",
  running: "Running",
  needs_review: "Needs review",
  completed: "Approved",
  failed: "Failed",
  rejected: "Rejected",
};

const confidenceLabels: Record<EvidenceConfidence, string> = {
  low: "Low confidence",
  medium: "Medium confidence",
  high: "High confidence",
};

function formatDate(value: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function groupClaims(claims: ProfileClaim[]) {
  return claims.reduce<Partial<Record<ProfileSection, ProfileClaim[]>>>((groups, claim) => {
    groups[claim.section] = [...(groups[claim.section] ?? []), claim];
    return groups;
  }, {});
}

export default async function ResearchPage({
  params,
}: {
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  let account: Account;
  let workspace: ResearchWorkspace;
  try {
    [account, workspace] = await Promise.all([
      apiGet<Account>(`/accounts/${accountId}`),
      apiGet<ResearchWorkspace>(`/accounts/${accountId}/research`),
    ]);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  const latest = workspace.latest_run;
  const profile = workspace.profile;
  const grouped = profile ? groupClaims(profile.claims) : {};

  return (
    <div className="page accountPage researchPage">
      {account.archived_at ? (
        <div className="archiveBanner">This account is archived. Research remains read-only until restored.</div>
      ) : null}

      <header className="accountHeader researchHeader">
        <div className="accountIdentity">
          <span className="accountAvatar large">{getInitials(account.name)}</span>
          <div>
            <span className="eyebrow">Evidence workspace</span>
            <h1>{account.name}</h1>
            <p>Source-backed company research with an explicit human approval gate.</p>
          </div>
        </div>
        <Link className="button secondary" href={`/accounts/${account.id}`}>Back to overview</Link>
      </header>

      <nav className="accountTabs" aria-label="Account sections">
        <Link href={`/accounts/${account.id}`}>Overview</Link>
        <Link href={`/accounts/${account.id}/research`} className="active">Research</Link>
        <Link href={`/accounts/${account.id}/discovery`}>Discovery</Link><Link href={`/accounts/${account.id}/solutions`}>Solutions</Link><Link href={`/accounts/${account.id}/poc`}>POC</Link><Link href={`/accounts/${account.id}/poc`}>Evaluation</Link><Link href={`/accounts/${account.id}/business-case`}>Business Case</Link><Link href={`/accounts/${account.id}/deployment`}>Deployment</Link>
        <Link href={`/accounts/${account.id}/activity`}>Activity</Link>
      </nav>

      <section className="researchHero panel">
        <div>
          <span className="eyebrow">Phase 2 · Research</span>
          <h2>{latest ? "Research run" : "Build an evidence-backed company profile"}</h2>
          <p>
            {latest
              ? `Provider: ${latest.provider === "mock" ? "Simulation" : "OpenAI web research"} · Created ${formatDate(latest.created_at)}`
              : "Start with a safe simulation using account inputs, or enable live web research with an API key."}
          </p>
        </div>
        {latest ? <span className={`researchStatus ${latest.status}`}>{statusLabels[latest.status]}</span> : null}
        {!profile || latest?.status === "queued" || latest?.status === "running" ? (
          <ResearchActions
            accountId={account.id}
            runId={latest?.id ?? null}
            status={latest?.status ?? null}
            configuredProvider={workspace.configured_provider}
            liveResearchAvailable={workspace.live_research_available}
            archived={Boolean(account.archived_at)}
          />
        ) : null}
      </section>

      {!latest ? (
        <section className="researchEmpty">
          <div className="emptyGlyph">⌕</div>
          <h2>No research run yet</h2>
          <p>Each accepted claim will keep its source, excerpt, retrieval time, confidence, and verification state.</p>
        </section>
      ) : null}

      {latest?.error_message ? (
        <div className="researchError"><strong>Run failed</strong><p>{latest.error_message}</p></div>
      ) : null}

      {profile && latest ? (
        <>
          {profile.is_simulated ? (
            <div className="simulationBanner">
              <strong>Simulation — not public web research</strong>
              <span>This result contains only account-provided fields. It is safe for workflow testing but must not be treated as externally verified company intelligence.</span>
            </div>
          ) : null}

          <div className="researchGrid">
            <main className="researchMain">
              <section className="panel profileSummary">
                <div className="panelHeading"><div><span className="eyebrow">Research brief</span><h2>Company profile</h2></div></div>
                <p>{profile.summary}</p>
              </section>

              {Object.entries(grouped).map(([section, claims]) => (
                <section className="panel claimSection" key={section}>
                  <div className="panelHeading">
                    <div><span className="eyebrow">Evidence-backed claims</span><h2>{sectionLabels[section as ProfileSection]}</h2></div>
                    <span>{claims?.length ?? 0} claim{claims?.length === 1 ? "" : "s"}</span>
                  </div>
                  <div className="claimList">
                    {claims?.map((claim) => (
                      <article className="claimCard" key={claim.id}>
                        <div className="claimMeta">
                          <span className={`confidence ${claim.confidence}`}>{confidenceLabels[claim.confidence]}</span>
                          {claim.is_inference ? <span className="inferenceBadge">Inference</span> : null}
                          <span>{claim.review_status.replaceAll("_", " ")}</span>
                        </div>
                        <p className="claimStatement">{claim.statement}</p>
                        <div className="citationList">
                          {claim.citations.map((citation) => (
                            <details className="citationCard" key={citation.evidence_id}>
                              <summary>
                                <span>↗</span>
                                <strong>{citation.source_title}</strong>
                                <small>{citation.verification_status.replaceAll("_", " ")}</small>
                              </summary>
                              <blockquote>{citation.supporting_text}</blockquote>
                              <div className="citationFooter">
                                <span>{citation.locator || citation.publisher || "Source excerpt"}</span>
                                {citation.source_url ? (
                                  <a href={citation.source_url} target="_blank" rel="noreferrer">Open source ↗</a>
                                ) : null}
                              </div>
                            </details>
                          ))}
                        </div>
                      </article>
                    ))}
                  </div>
                </section>
              ))}
            </main>

            <aside className="researchAside">
              <section className="panel reviewPanel">
                <div className="panelHeading"><div><span className="eyebrow">Human gate</span><h2>Review decision</h2></div></div>
                <div className="reviewBody">
                  <p>Check whether claims match their excerpts and whether the sources are strong enough for customer-facing work.</p>
                  <ResearchActions
                    accountId={account.id}
                    runId={latest.id}
                    status={latest.status}
                    configuredProvider={workspace.configured_provider}
                    liveResearchAvailable={workspace.live_research_available}
                    archived={Boolean(account.archived_at)}
                  />
                  {latest.review_notes ? <blockquote>{latest.review_notes}</blockquote> : null}
                </div>
              </section>

              <section className="panel sourcePanel">
                <div className="panelHeading"><div><span className="eyebrow">Traceability</span><h2>Sources</h2></div><span>{workspace.sources.length}</span></div>
                <div className="sourceList">
                  {workspace.sources.map((source) => (
                    <article key={source.id}>
                      <div><span className="sourceType">{source.source_type.replaceAll("_", " ")}</span>{source.is_official ? <span className="officialBadge">Official</span> : null}</div>
                      <strong>{source.title}</strong>
                      <p>{source.publisher || "Account input"} · Retrieved {formatDate(source.retrieved_at)}</p>
                      {source.url ? <a href={source.url} target="_blank" rel="noreferrer">Visit source ↗</a> : null}
                    </article>
                  ))}
                </div>
              </section>

              <section className="panel runHistoryPanel">
                <div className="panelHeading"><div><span className="eyebrow">Auditability</span><h2>Run history</h2></div></div>
                <ol>
                  {workspace.run_history.map((run) => (
                    <li key={run.id}>
                      <div><strong>{statusLabels[run.status]}</strong><span>{run.provider}</span></div>
                      <time>{formatDate(run.created_at)}</time>
                    </li>
                  ))}
                </ol>
              </section>
            </aside>
          </div>
        </>
      ) : null}
    </div>
  );
}
