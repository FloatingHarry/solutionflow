import Link from "next/link";
import { notFound } from "next/navigation";

import { SolutionWorkspace } from "@/components/SolutionWorkspace";
import { ApiError, apiGet } from "@/lib/api";
import type { Account, SolutionWorkspace as SolutionWorkspaceData } from "@/lib/types";
import { getInitials, stageLabels } from "@/lib/workflow";

export const dynamic = "force-dynamic";

export default async function SolutionsPage({
  params,
}: {
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  let account: Account;
  let workspace: SolutionWorkspaceData;
  try {
    [account, workspace] = await Promise.all([
      apiGet<Account>(`/accounts/${accountId}`),
      apiGet<SolutionWorkspaceData>(`/accounts/${accountId}/solutions`),
    ]);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  return (
    <div className="page accountPage solutionsPage">
      {account.archived_at ? (
        <div className="archiveBanner">
          This account is archived. Solution work remains read-only until restored.
        </div>
      ) : null}

      <header className="accountHeader researchHeader">
        <div className="accountIdentity">
          <span className="accountAvatar large">{getInitials(account.name)}</span>
          <div>
            <span className="eyebrow">Solution intelligence</span>
            <h1>{account.name}</h1>
            <p>Match confirmed needs to explainable solution patterns and human-owned proposals.</p>
          </div>
        </div>
        <Link className="button secondary" href={`/accounts/${account.id}`}>
          Back to overview
        </Link>
      </header>

      <nav className="accountTabs" aria-label="Account sections">
        <Link href={`/accounts/${account.id}`}>Overview</Link>
        <Link href={`/accounts/${account.id}/research`}>Research</Link>
        <Link href={`/accounts/${account.id}/discovery`}>Discovery</Link>
        <Link href={`/accounts/${account.id}/solutions`} className="active">Solutions</Link>
        <Link href={`/accounts/${account.id}/poc`}>POC</Link><Link href={`/accounts/${account.id}/poc`}>Evaluation</Link><Link href={`/accounts/${account.id}/business-case`}>Business Case</Link><Link href={`/accounts/${account.id}/deployment`}>Deployment</Link>
        <Link href={`/accounts/${account.id}/activity`}>Activity</Link>
      </nav>

      <section className="solutionHero panel">
        <div>
          <span className="eyebrow">Phase 4 · Solution knowledge & matching</span>
          <h2>Design from confirmed evidence</h2>
          <p>Confirmed need → ranked catalog match → editable proposal → human acceptance → POC.</p>
        </div>
        <div className="discoveryGateBadge">
          <span>Workflow stage</span>
          <strong>{stageLabels[workspace.current_stage]}</strong>
        </div>
      </section>

      <SolutionWorkspace
        accountId={account.id}
        initialWorkspace={workspace}
        archived={Boolean(account.archived_at)}
      />
    </div>
  );
}
