import Link from "next/link";
import { notFound } from "next/navigation";

import { KnowledgeWorkspace } from "@/components/KnowledgeWorkspace";
import { ApiError, apiGet } from "@/lib/api";
import type { Account, KnowledgeWorkspace as KnowledgeWorkspaceData } from "@/lib/types";
import { getInitials, stageLabels } from "@/lib/workflow";


export const dynamic = "force-dynamic";

export default async function KnowledgePage({ params }: { params: Promise<{ accountId: string }> }) {
  const { accountId } = await params;
  let account: Account;
  let workspace: KnowledgeWorkspaceData;
  try {
    [account, workspace] = await Promise.all([
      apiGet<Account>(`/accounts/${accountId}`),
      apiGet<KnowledgeWorkspaceData>(`/accounts/${accountId}/knowledge`),
    ]);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  return (
    <div className="page accountPage knowledgePage">
      {account.archived_at ? <div className="archiveBanner">This account is archived. Existing knowledge, answers, and citations remain readable until restored.</div> : null}
      <header className="accountHeader accountWorkspaceHeader">
        <div className="accountIdentity">
          <span className="accountAvatar large">{getInitials(account.name)}</span>
          <div><span className="eyebrow"><i /> Unified knowledge workspace</span><h1>{account.name}</h1><p>{[account.industry, account.region].filter(Boolean).join(" · ") || "Profile details pending"}</p></div>
        </div>
        <div className="accountHeaderControls"><div className="activeStageSignal"><span>Workflow context</span><strong>{stageLabels[account.current_stage]}</strong><i /></div></div>
      </header>

      <nav className="accountTabs" aria-label="Account sections">
        <Link href={`/accounts/${account.id}`}>Overview</Link><Link href={`/accounts/${account.id}/knowledge`} className="active">Knowledge</Link><Link href={`/accounts/${account.id}/research`}>Research</Link><Link href={`/accounts/${account.id}/discovery`}>Discovery</Link><Link href={`/accounts/${account.id}/solutions`}>Solutions</Link><Link href={`/accounts/${account.id}/poc`}>POC</Link><Link href={`/accounts/${account.id}/business-case`}>Business Case</Link><Link href={`/accounts/${account.id}/deployment`}>Deployment</Link><Link href={`/accounts/${account.id}/activity`}>Activity</Link>
      </nav>

      <KnowledgeWorkspace
        initialWorkspace={workspace}
        accountName={account.name}
        accountRegion={account.region}
        accountIndustry={account.industry}
        readOnly={Boolean(account.archived_at)}
      />
    </div>
  );
}
