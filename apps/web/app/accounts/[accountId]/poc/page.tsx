import Link from "next/link";
import { notFound } from "next/navigation";

import { PocWorkspace } from "@/components/PocWorkspace";
import { ApiError, apiGet } from "@/lib/api";
import type { Account, PocWorkspace as PocWorkspaceData } from "@/lib/types";
import { getInitials, stageLabels } from "@/lib/workflow";

export const dynamic = "force-dynamic";

export default async function PocPage({
  params,
}: {
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  let account: Account;
  let workspace: PocWorkspaceData;
  try {
    [account, workspace] = await Promise.all([
      apiGet<Account>(`/accounts/${accountId}`),
      apiGet<PocWorkspaceData>(`/accounts/${accountId}/poc`),
    ]);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  const evaluationActive = ["evaluation", "business_case", "deployment"].includes(
    workspace.current_stage,
  );

  return (
    <div className="page accountPage pocPage">
      {account.archived_at ? (
        <div className="archiveBanner">This account is archived. POC and evaluation evidence remain read-only until restored.</div>
      ) : null}

      <header className="accountHeader researchHeader">
        <div className="accountIdentity">
          <span className="accountAvatar large">{getInitials(account.name)}</span>
          <div>
            <span className="eyebrow">Experiment & decision workspace</span>
            <h1>{account.name}</h1>
            <p>Define a bounded POC, compare targets with actuals, and record a human decision.</p>
          </div>
        </div>
        <Link className="button secondary" href={`/accounts/${account.id}`}>Back to overview</Link>
      </header>

      <nav className="accountTabs" aria-label="Account sections">
        <Link href={`/accounts/${account.id}`}>Overview</Link>
        <Link href={`/accounts/${account.id}/research`}>Research</Link>
        <Link href={`/accounts/${account.id}/discovery`}>Discovery</Link>
        <Link href={`/accounts/${account.id}/solutions`}>Solutions</Link>
        <Link href={`/accounts/${account.id}/poc`} className={!evaluationActive ? "active" : undefined}>POC</Link>
        <Link href={`/accounts/${account.id}/poc`} className={evaluationActive ? "active" : undefined}>Evaluation</Link>
        <Link href={`/accounts/${account.id}/business-case`}>Business Case</Link>
        <Link href={`/accounts/${account.id}/deployment`}>Deployment</Link>
        <Link href={`/accounts/${account.id}/activity`}>Activity</Link>
      </nav>

      <section className="pocHero panel">
        <div>
          <span className="eyebrow">Phase 5 · POC, evaluation & decision</span>
          <h2>Make the solution prove itself</h2>
          <p>Accepted proposal → approved experiment → target vs actual → Proceed / Iterate / Reject.</p>
        </div>
        <div className="discoveryGateBadge"><span>Workflow stage</span><strong>{stageLabels[workspace.current_stage]}</strong></div>
      </section>

      <PocWorkspace
        key={workspace.plan ? [
          workspace.plan.id,
          workspace.plan.updated_at,
          workspace.plan.status,
          ...workspace.plan.metrics.map((metric) => metric.updated_at),
          workspace.plan.decisions.length,
        ].join(":") : "no-plan"}
        accountId={account.id}
        initialWorkspace={workspace}
        archived={Boolean(account.archived_at)}
      />
    </div>
  );
}
