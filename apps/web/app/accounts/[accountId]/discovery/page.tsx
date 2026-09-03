import Link from "next/link";
import { notFound } from "next/navigation";

import { DiscoveryWorkspace } from "@/components/DiscoveryWorkspace";
import { ApiError, apiGet } from "@/lib/api";
import type { Account, DiscoveryWorkspace as DiscoveryWorkspaceData } from "@/lib/types";
import { getInitials } from "@/lib/workflow";

export const dynamic = "force-dynamic";

export default async function DiscoveryPage({
  params,
}: {
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  let account: Account;
  let workspace: DiscoveryWorkspaceData;
  try {
    [account, workspace] = await Promise.all([
      apiGet<Account>(`/accounts/${accountId}`),
      apiGet<DiscoveryWorkspaceData>(`/accounts/${accountId}/discovery`),
    ]);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  return (
    <div className="page accountPage discoveryPage">
      {account.archived_at ? (
        <div className="archiveBanner">
          This account is archived. Discovery evidence remains read-only until restored.
        </div>
      ) : null}

      <header className="accountHeader researchHeader">
        <div className="accountIdentity">
          <span className="accountAvatar large">{getInitials(account.name)}</span>
          <div>
            <span className="eyebrow">Opportunity & discovery</span>
            <h1>{account.name}</h1>
            <p>Turn research signals into customer-validated, measurable needs.</p>
          </div>
        </div>
        <Link className="button secondary" href={`/accounts/${account.id}`}>
          Back to overview
        </Link>
      </header>

      <nav className="accountTabs" aria-label="Account sections">
        <Link href={`/accounts/${account.id}`}>Overview</Link>
        <Link href={`/accounts/${account.id}/research`}>Research</Link>
        <Link href={`/accounts/${account.id}/discovery`} className="active">Discovery</Link>
        <Link href={`/accounts/${account.id}/solutions`}>Solutions</Link><Link href={`/accounts/${account.id}/poc`}>POC</Link><Link href={`/accounts/${account.id}/poc`}>Evaluation</Link><Link href={`/accounts/${account.id}/business-case`}>Business Case</Link><Link href={`/accounts/${account.id}/deployment`}>Deployment</Link>
        <Link href={`/accounts/${account.id}/activity`}>Activity</Link>
      </nav>

      <section className="discoveryHero panel">
        <div>
          <span className="eyebrow">Phase 3 · Opportunity & discovery</span>
          <h2>Keep the chain of evidence intact</h2>
          <p>Research evidence → opportunity hypothesis → interview question → customer answer → confirmed need.</p>
        </div>
        <div className="discoveryGateBadge">
          <span>Workflow stage</span>
          <strong>{workspace.current_stage.replaceAll("_", " ")}</strong>
        </div>
      </section>

      <DiscoveryWorkspace
        accountId={account.id}
        initialWorkspace={workspace}
        archived={Boolean(account.archived_at)}
      />
    </div>
  );
}
