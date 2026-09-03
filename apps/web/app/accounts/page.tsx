import Link from "next/link";

import { ApiError, apiGet } from "@/lib/api";
import type { AccountList } from "@/lib/types";
import { getInitials, stageLabels } from "@/lib/workflow";


export const dynamic = "force-dynamic";

function formatUpdated(value: string): string {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
}

const stageOrder = ["research", "opportunity", "discovery", "solution", "poc", "evaluation", "business_case", "deployment"] as const;

export default async function AccountsPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const { q = "" } = await searchParams;
  let data: AccountList | null = null;
  let error: string | null = null;
  try {
    data = await apiGet<AccountList>(`/accounts${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  } catch (requestError) {
    error = requestError instanceof ApiError ? requestError.message : "Unable to load accounts.";
  }

  const realAccounts = data?.items.filter((account) => !account.is_demo).length ?? 0;
  const demoAccounts = data?.items.filter((account) => account.is_demo).length ?? 0;
  const deploymentAccounts = data?.items.filter((account) => account.current_stage === "deployment").length ?? 0;

  return (
    <div className="page accountsPage">
      <header className="pageHeader portfolioHeader">
        <div className="portfolioTitle">
          <span className="eyebrow"><i /> Enterprise command center</span>
          <h1>Opportunity<br /><em>intelligence.</em></h1>
          <p>Every signal, decision, and customer outcome—connected in one accountable workspace.</p>
        </div>
        <div className="portfolioHeaderActions">
          <span className="liveWorkspace"><i /> Workspace live</span>
          <Link href="/accounts/new" className="button primary"><span>+</span> New account</Link>
        </div>
      </header>

      <section className="portfolioOverview" aria-label="Portfolio overview">
        <div className="portfolioLead">
          <span>Portfolio signal</span>
          <strong>{data?.total ?? 0}</strong>
          <p>active account workspaces</p>
        </div>
        <div><span>Live accounts</span><strong>{realAccounts.toString().padStart(2, "0")}</strong><small>Customer-owned context</small></div>
        <div><span>Demo journeys</span><strong>{demoAccounts.toString().padStart(2, "0")}</strong><small>Complete synthetic flows</small></div>
        <div><span>At deployment</span><strong>{deploymentAccounts.toString().padStart(2, "0")}</strong><small>Final readiness stage</small></div>
        <div className="portfolioOrbit" aria-hidden="true"><i /><i /><i /><span>SF</span></div>
      </section>

      <div className="toolbar">
        <form className="searchForm" action="/accounts">
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></svg>
          <input name="q" defaultValue={q} placeholder="Search company, industry or region" aria-label="Search accounts" />
        </form>
        <span className="resultCount"><i />{data ? `${data.total} account${data.total === 1 ? "" : "s"}` : "—"}</span>
      </div>

      {error ? (
        <section className="setupState">
          <span className="setupIcon">!</span>
          <h2>Workspace API is offline</h2>
          <p>{error}</p>
          <code>docker compose up -d && uvicorn --app-dir apps/api app.main:app --reload</code>
        </section>
      ) : null}

      {!error && data?.items.length === 0 ? (
        <section className="emptyState">
          <span className="emptyGlyph">◎</span>
          <h2>{q ? "No matching accounts" : "Build your first account workspace"}</h2>
          <p>{q ? "Try a different company, industry or region." : "Create an account to establish its workflow and audit trail."}</p>
          {!q ? <Link href="/accounts/new" className="button primary">Create account</Link> : null}
        </section>
      ) : null}

      {data && data.items.length > 0 ? (
        <section className="accountGrid">
          {data.items.map((account, index) => {
            const stagePosition = stageOrder.indexOf(account.current_stage) + 1;
            const stageProgress = Math.round((stagePosition / stageOrder.length) * 100);
            return (
            <Link href={`/accounts/${account.id}`} className="accountCard" data-stage={account.current_stage} key={account.id}>
              <span className="accountSequence">{String(index + 1).padStart(2, "0")}</span>
              <div className="accountCardTop">
                <span className="accountAvatar">{getInitials(account.name)}</span>
                <div className="accountCardBadges">{account.is_demo ? <span className="demoBadge">Demo</span> : null}<span className="stageBadge">{stageLabels[account.current_stage]}</span></div>
              </div>
              <div className="accountCardBody">
                <h2>{account.name}</h2>
                <p>{[account.industry, account.region].filter(Boolean).join(" · ") || "Profile details pending"}</p>
              </div>
              <div className="accountCardFooter">
                <div><span>Stage {stagePosition} of {stageOrder.length}</span><div className="accountCardProgress"><i style={{ width: `${stageProgress}%` }} /></div></div>
                <span className="accountCardArrow" aria-hidden="true">↗</span>
              </div>
              <small className="accountUpdated">Updated {formatUpdated(account.updated_at)}</small>
            </Link>
          );})}
        </section>
      ) : null}
    </div>
  );
}
