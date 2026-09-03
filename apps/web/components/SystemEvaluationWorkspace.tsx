"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import type { SystemEvaluationWorkspace as Workspace } from "@/lib/types";


function formatTime(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function SystemEvaluationWorkspace({ initialWorkspace }: { initialWorkspace: Workspace }) {
  const router = useRouter();
  const [workspace, setWorkspace] = useState(initialWorkspace);
  const [busy, setBusy] = useState<"seed" | "run" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const run = workspace.latest_run;

  async function mutate(path: string, action: "seed" | "run") {
    setBusy(action);
    setError(null);
    try {
      const response = await fetch(`/api/backend${path}`, { method: "POST" });
      const payload = (await response.json()) as Workspace & { detail?: string };
      if (!response.ok) throw new Error(payload.detail || "Unable to update evaluation.");
      setWorkspace(payload);
      router.refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update evaluation.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <section className="evaluationHero panel">
        <div><span className="eyebrow">Phase 7 · System quality</span><h2>Evaluate the workflow, not just the output</h2><p>Five synthetic accounts · 35 stored-data assertions · repeatable and auditable.</p></div>
        <div className="evaluationActions">
          <button className="button secondary" disabled={busy !== null || workspace.demo_accounts.length >= workspace.required_demo_accounts} onClick={() => mutate("/demo-accounts/seed", "seed")}>{busy === "seed" ? "Building portfolio…" : workspace.demo_accounts.length >= workspace.required_demo_accounts ? "Demo portfolio ready" : "Initialize demo portfolio"}</button>
          <button className="button primary" disabled={busy !== null} onClick={() => mutate("/system-evaluations/run", "run")}>{busy === "run" ? "Running 35 checks…" : "Run regression evaluation"}</button>
        </div>
      </section>

      <div className="evaluationBoundary"><strong>Evaluation boundary</strong><p>{workspace.methodology_note}</p></div>
      {error ? <p className="inlineError" role="alert">{error}</p> : null}

      <section className="evaluationKpis">
        <div><span>Demo accounts</span><strong>{workspace.demo_accounts.length}/{workspace.required_demo_accounts}</strong><small>Synthetic, full workflow</small></div>
        <div><span>Tasks</span><strong>{run?.total_tasks ?? 0}</strong><small>Minimum {workspace.required_task_minimum}</small></div>
        <div><span>Pass rate</span><strong>{run ? `${run.pass_rate}%` : "—"}</strong><small>{run ? `${run.passed_tasks}/${run.total_tasks} passed` : "Run required"}</small></div>
        <div><span>Unsupported claims</span><strong>{run ? `${run.hallucination_rate}%` : "—"}</strong><small>Stored claim coverage</small></div>
        <div><span>Check latency</span><strong>{run ? `${run.mean_latency_ms} ms` : "—"}</strong><small>Database assertions</small></div>
        <div><span>Model cost</span><strong>{run ? `$${run.estimated_cost_usd.toFixed(2)}` : "—"}</strong><small>No model calls</small></div>
      </section>

      <div className="evaluationGrid">
        <main className="evaluationMain">
          <section className="panel evaluationMetricsCard">
            <header className="evaluationSectionHeader"><div><span className="eyebrow">Regression scorecard</span><h2>Seven quality dimensions</h2><p>{run ? `${run.name} · ${formatTime(run.completed_at)}` : "Run the evaluation to produce a persisted scorecard."}</p></div>{run ? <span className="evaluationDataset">{run.dataset_version}</span> : null}</header>
            {run ? <div className="evaluationMetricList">{run.metrics.map((metric) => <article key={metric.category}><div><span className={metric.score === 100 ? "evaluationPass" : "evaluationFail"}>{metric.score === 100 ? "PASS" : "FAIL"}</span><h3>{metric.label}</h3></div><strong>{metric.score}%</strong><small>{metric.passed}/{metric.total} accounts</small><div className="evaluationBar"><i style={{ width: `${metric.score}%` }} /></div></article>)}</div> : <div className="evaluationEmpty"><p>No evaluation run has been recorded.</p></div>}
          </section>

          {run ? <section className="panel evaluationTaskCard"><header className="evaluationSectionHeader"><div><span className="eyebrow">Task evidence</span><h2>All {run.total_tasks} assertions</h2><p>Each row records expected state, actual state, latency, and pass/fail.</p></div></header><div className="evaluationTaskTable"><div className="evaluationTaskHeader"><span>Account / check</span><span>Expected</span><span>Actual</span><span>Result</span></div>{run.tasks.map((task) => { const account = workspace.demo_accounts.find((item) => item.id === task.account_id); return <article key={task.id}><div><strong>{account?.name ?? "Demo account"}</strong><small>{task.label}</small></div><p>{task.expected}</p><p>{task.actual}</p><span className={`metricResult ${task.passed ? "pass" : "fail"}`}>{task.passed ? "pass" : "fail"}</span></article>; })}</div></section> : null}
        </main>

        <aside className="evaluationAside">
          <section className="panel demoPortfolioCard">
            <header><span className="eyebrow">Demo portfolio</span><h2>Five completed journeys</h2><p>Names, websites, answers, and results are synthetic fixtures.</p></header>
            <div>{workspace.demo_accounts.map((account) => <Link href={`/accounts/${account.id}`} key={account.id}><span className="demoMonogram">{account.name.split(" ").slice(0, 2).map((part) => part[0]).join("")}</span><div><strong>{account.name}</strong><small>{account.industry} · {account.region}</small></div><em>{account.workflow_completion}%</em></Link>)}</div>
          </section>
          <section className="panel evaluationNotes"><span className="eyebrow">Interpretation</span><h3>What 100% means here</h3><ul><li>The seeded data graph satisfies every current assertion.</li><li>Citations and lineage exist in the database.</li><li>Human gates and workflow completion are intact.</li><li>It is not a live-model factual-accuracy benchmark.</li></ul></section>
        </aside>
      </div>
    </>
  );
}
