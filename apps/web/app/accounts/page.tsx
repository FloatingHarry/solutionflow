import Link from "next/link";

import { ApiError, apiGet } from "@/lib/api";
import type { AccountList } from "@/lib/types";
import { getInitials, stageLabels } from "@/lib/workflow";


export const dynamic = "force-dynamic";

function formatUpdated(value: string): string {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
}

export default async function AccountsPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const { q = "" } = await searchParams;
  let data: AccountList | null = null;
  let error: string | null = null;
  try {
    data = await apiGet<AccountList>(`/accounts${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  } catch (requestError) {
    error = requestError instanceof ApiError ? requestError.message : "Unable to load accounts.";
  }

  return (
    <div className="page accountsPage">
      <header className="pageHeader">
        <div>
          <span className="eyebrow">Enterprise workspace</span>
          <h1>Accounts</h1>
          <p>Move every customer from evidence to a documented decision.</p>
        </div>
        <Link href="/accounts/new" className="button primary">+ New account</Link>
      </header>

      <div className="toolbar">
        <form className="searchForm" action="/accounts">
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></svg>
          <input name="q" defaultValue={q} placeholder="Search company, industry or region" aria-label="Search accounts" />
        </form>
        <span className="resultCount">{data ? `${data.total} account${data.total === 1 ? "" : "s"}` : "—"}</span>
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
          {data.items.map((account) => (
            <Link href={`/accounts/${account.id}`} className="accountCard" key={account.id}>
              <div className="accountCardTop">
                <span className="accountAvatar">{getInitials(account.name)}</span>
                <div className="accountCardBadges">{account.is_demo ? <span className="demoBadge">Demo</span> : null}<span className="stageBadge">{stageLabels[account.current_stage]}</span></div>
              </div>
              <div className="accountCardBody">
                <h2>{account.name}</h2>
                <p>{[account.industry, account.region].filter(Boolean).join(" · ") || "Profile details pending"}</p>
              </div>
              <div className="accountCardFooter">
                <span>Updated {formatUpdated(account.updated_at)}</span>
                <span aria-hidden="true">→</span>
              </div>
            </Link>
          ))}
        </section>
      ) : null}
    </div>
  );
}
