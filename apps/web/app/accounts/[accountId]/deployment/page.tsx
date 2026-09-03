import Link from "next/link";
import { notFound } from "next/navigation";

import { DeploymentWorkspace } from "@/components/DeploymentWorkspace";
import { ApiError, apiGet } from "@/lib/api";
import type { Account, DeploymentWorkspace as DeploymentWorkspaceData } from "@/lib/types";
import { getInitials } from "@/lib/workflow";

export const dynamic = "force-dynamic";

export default async function DeploymentPage({
  params,
}: {
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  let account: Account;
  let workspace: DeploymentWorkspaceData;
  try {
    [account, workspace] = await Promise.all([
      apiGet<Account>(`/accounts/${accountId}`),
      apiGet<DeploymentWorkspaceData>(`/accounts/${accountId}/deployment`),
    ]);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  const planKey = workspace.plan
    ? [workspace.plan.id, workspace.plan.updated_at, workspace.plan.status].join(":")
    : "no-plan";

  return (
    <div className="page accountPage deploymentPage">
      {account.archived_at ? <div className="archiveBanner">This account is archived. Deployment planning remains read-only until restored.</div> : null}
      <header className="accountHeader researchHeader">
        <div className="accountIdentity"><span className="accountAvatar large">{getInitials(account.name)}</span><div><span className="eyebrow">Production readiness workspace</span><h1>{account.name}</h1><p>Assign owners, capture launch controls, clear readiness checks, and complete the final workflow gate.</p></div></div>
        <Link className="button secondary" href={`/accounts/${account.id}`}>Back to overview</Link>
      </header>

      <nav className="accountTabs" aria-label="Account sections">
        <Link href={`/accounts/${account.id}`}>Overview</Link><Link href={`/accounts/${account.id}/research`}>Research</Link><Link href={`/accounts/${account.id}/discovery`}>Discovery</Link><Link href={`/accounts/${account.id}/solutions`}>Solutions</Link><Link href={`/accounts/${account.id}/poc`}>POC</Link><Link href={`/accounts/${account.id}/poc`}>Evaluation</Link><Link href={`/accounts/${account.id}/business-case`}>Business Case</Link><Link href={`/accounts/${account.id}/deployment`} className="active">Deployment</Link><Link href={`/accounts/${account.id}/activity`}>Activity</Link>
      </nav>

      <section className="deploymentHero panel"><div><span className="eyebrow">Phase 7 · Deployment</span><h2>Make production readiness explicit</h2><p>Approved business case → operating plan → owner-and-evidence checks → final human completion.</p></div><div className="deploymentEnvironment"><span>Approved environment</span><strong>{workspace.recommended_environment?.replaceAll("_", " ") ?? "Pending"}</strong></div></section>

      <DeploymentWorkspace key={planKey} accountId={account.id} initialWorkspace={workspace} archived={Boolean(account.archived_at)} />
    </div>
  );
}
