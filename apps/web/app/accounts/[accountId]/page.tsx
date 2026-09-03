import Link from "next/link";
import { notFound } from "next/navigation";

import { AccountActions } from "@/components/AccountActions";
import { ActivityTimeline } from "@/components/ActivityTimeline";
import { AgentWorkspace } from "@/components/AgentWorkspace";
import { WorkflowBoard } from "@/components/WorkflowBoard";
import { ApiError, apiGet } from "@/lib/api";
import type { Account, ActivityList, AgentWorkspace as AgentWorkspaceData, BusinessCaseWorkspace, DeploymentWorkspace, DiscoveryWorkspace, Workflow } from "@/lib/types";
import { getInitials, stageLabels } from "@/lib/workflow";


export const dynamic = "force-dynamic";

export default async function AccountPage({ params }: { params: Promise<{ accountId: string }> }) {
  const { accountId } = await params;
  let account: Account;
  let workflow: Workflow;
  let activities: ActivityList;
  let discovery: DiscoveryWorkspace;
  let businessCase: BusinessCaseWorkspace;
  let deployment: DeploymentWorkspace;
  let agentWorkspace: AgentWorkspaceData;
  try {
    [account, workflow, activities, discovery, businessCase, deployment, agentWorkspace] = await Promise.all([
      apiGet<Account>(`/accounts/${accountId}`),
      apiGet<Workflow>(`/accounts/${accountId}/workflow`),
      apiGet<ActivityList>(`/accounts/${accountId}/activities`),
      apiGet<DiscoveryWorkspace>(`/accounts/${accountId}/discovery`),
      apiGet<BusinessCaseWorkspace>(`/accounts/${accountId}/business-case`),
      apiGet<DeploymentWorkspace>(`/accounts/${accountId}/deployment`),
      apiGet<AgentWorkspaceData>(`/accounts/${accountId}/agent`),
    ]);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  return (
    <div className="page accountPage">
      {account.archived_at ? <div className="archiveBanner">This account is archived. Its workflow and history remain read-only until restored.</div> : null}
      <header className="accountHeader accountWorkspaceHeader">
        <div className="accountIdentity">
          <span className="accountAvatar large">{getInitials(account.name)}</span>
          <div>
            <span className="eyebrow"><i /> Account workspace {account.is_demo ? "· Synthetic demo" : ""}</span>
            <h1>{account.name}</h1>
            <p>{[account.industry, account.region].filter(Boolean).join(" · ") || "Profile details pending"}</p>
          </div>
        </div>
        <div className="accountHeaderControls">
          <div className="activeStageSignal"><span>Active stage</span><strong>{stageLabels[account.current_stage]}</strong><i /></div>
          <AccountActions accountId={account.id} archived={Boolean(account.archived_at)} />
        </div>
      </header>

      <nav className="accountTabs" aria-label="Account sections">
        <Link href={`/accounts/${account.id}`} className="active">Overview</Link>
        <Link href={`/accounts/${account.id}/research`}>Research</Link><Link href={`/accounts/${account.id}/discovery`}>Discovery</Link><Link href={`/accounts/${account.id}/solutions`}>Solutions</Link><Link href={`/accounts/${account.id}/poc`}>POC</Link><Link href={`/accounts/${account.id}/poc`}>Evaluation</Link><Link href={`/accounts/${account.id}/business-case`}>Business Case</Link><Link href={`/accounts/${account.id}/deployment`}>Deployment</Link>
        <Link href={`/accounts/${account.id}/activity`}>Activity</Link>
      </nav>

      <section className="metricStrip accountMetricStrip">
        <div><span>Current stage</span><strong>{stageLabels[account.current_stage]}</strong></div>
        <div><span>Recorded events</span><strong>{activities.total}</strong></div>
        <div><span>Confirmed needs</span><strong>{discovery.confirmed_needs.length}</strong><small>Customer validated</small></div>
        <div><span>Business case</span><strong>{businessCase.case ? businessCase.case.status.replaceAll("_", " ") : "—"}</strong><small>{businessCase.case ? "Scenario estimate" : "Not generated"}</small></div>
        <div><span>Deployment</span><strong>{deployment.plan ? `${deployment.plan.readiness_score}%` : "—"}</strong><small>{deployment.plan ? deployment.plan.status.replaceAll("_", " ") : "Not planned"}</small></div>
      </section>

      <AgentWorkspace
        accountName={account.name}
        initialWorkspace={agentWorkspace}
        readOnly={Boolean(account.archived_at)}
      />

      <WorkflowBoard
        accountId={account.id}
        initialWorkflow={workflow}
        readOnly={Boolean(account.archived_at)}
        managedStages={["research", "opportunity", "discovery", "solution", "poc", "evaluation", "business_case", "deployment"]}
      />

      <div className="contentGrid">
        <section className="panel profilePanel">
          <div className="panelHeading"><div><span className="eyebrow">Profile</span><h2>Known context</h2></div></div>
          <dl className="profileList">
            <div><dt>Website</dt><dd>{account.website ? <a href={account.website} target="_blank" rel="noreferrer">{account.website}</a> : "Not provided"}</dd></div>
            <div><dt>Industry</dt><dd>{account.industry || "Not provided"}</dd></div>
            <div><dt>Region</dt><dd>{account.region || "Not provided"}</dd></div>
            <div className="notesRow"><dt>Internal notes</dt><dd>{account.notes || "No internal context yet."}</dd></div>
          </dl>
          <div className="evidenceNotice"><strong>Evidence boundary</strong><p>Profile notes are internal context. Open Research to inspect sourced claims, citations, and review status.</p></div>
        </section>

        <section className="panel activityPanel">
          <div className="panelHeading"><div><span className="eyebrow">Audit trail</span><h2>Latest activity</h2></div><Link href={`/accounts/${account.id}/activity`}>View all →</Link></div>
          <ActivityTimeline activities={activities.items} compact />
        </section>
      </div>
    </div>
  );
}
