import { SystemEvaluationWorkspace } from "@/components/SystemEvaluationWorkspace";
import { apiGet } from "@/lib/api";
import type { SystemEvaluationWorkspace as Workspace } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function EvaluationPage() {
  const workspace = await apiGet<Workspace>("/system-evaluation");
  const workspaceKey = workspace.latest_run
    ? `${workspace.latest_run.id}:${workspace.demo_accounts.length}`
    : `no-run:${workspace.demo_accounts.length}`;

  return (
    <div className="page systemEvaluationPage">
      <header className="pageHeader">
        <div><span className="eyebrow">Quality & regression</span><h1>System evaluation</h1><p>Persistent, explainable checks across a complete synthetic enterprise portfolio.</p></div>
      </header>
      <SystemEvaluationWorkspace key={workspaceKey} initialWorkspace={workspace} />
    </div>
  );
}
