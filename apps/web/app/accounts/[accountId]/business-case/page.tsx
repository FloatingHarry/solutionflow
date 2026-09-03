import Link from "next/link";
import { notFound } from "next/navigation";

import { BusinessCaseWorkspace } from "@/components/BusinessCaseWorkspace";
import { ApiError, apiGet } from "@/lib/api";
import type { Account, BusinessCaseWorkspace as BusinessCaseWorkspaceData } from "@/lib/types";
import { getInitials, stageLabels } from "@/lib/workflow";

export const dynamic = "force-dynamic";

export default async function BusinessCasePage({
  params,
}: {
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  let account: Account;
  let workspace: BusinessCaseWorkspaceData;
  try {
    [account, workspace] = await Promise.all([
      apiGet<Account>(`/accounts/${accountId}`),
      apiGet<BusinessCaseWorkspaceData>(`/accounts/${accountId}/business-case`),
    ]);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  const caseData = workspace.case;
  const workspaceKey = caseData
    ? [caseData.id, caseData.updated_at, caseData.status, caseData.brief.updated_at].join(":")
    : "no-case";

  return (
    <div className="page accountPage businessCasePage">
      {account.archived_at ? <div className="archiveBanner">This account is archived. Business case evidence remains read-only until restored.</div> : null}
      <header className="accountHeader researchHeader">
        <div className="accountIdentity"><span className="accountAvatar large">{getInitials(account.name)}</span><div><span className="eyebrow">Commercial decision workspace</span><h1>{account.name}</h1><p>Model scenario economics, compare deployment options, and approve the final evidence-based brief.</p></div></div>
        <Link className="button secondary" href={`/accounts/${account.id}`}>Back to overview</Link>
      </header>

      <nav className="accountTabs" aria-label="Account sections">
        <Link href={`/accounts/${account.id}`}>Overview</Link><Link href={`/accounts/${account.id}/research`}>Research</Link><Link href={`/accounts/${account.id}/discovery`}>Discovery</Link><Link href={`/accounts/${account.id}/solutions`}>Solutions</Link><Link href={`/accounts/${account.id}/poc`}>POC</Link><Link href={`/accounts/${account.id}/poc`}>Evaluation</Link><Link href={`/accounts/${account.id}/business-case`} className="active">Business Case</Link><Link href={`/accounts/${account.id}/deployment`}>Deployment</Link><Link href={`/accounts/${account.id}/activity`}>Activity</Link>
      </nav>

      <section className="businessHero panel"><div><span className="eyebrow">Phase 6 · ROI, deployment & final brief</span><h2>Convert evidence into an approval package</h2><p>POC result → editable scenario → deployment trade-offs → final brief → human approval.</p></div><div className="discoveryGateBadge"><span>Workflow stage</span><strong>{stageLabels[workspace.current_stage]}</strong></div></section>

      <BusinessCaseWorkspace key={workspaceKey} accountId={account.id} initialWorkspace={workspace} archived={Boolean(account.archived_at)} />
    </div>
  );
}
