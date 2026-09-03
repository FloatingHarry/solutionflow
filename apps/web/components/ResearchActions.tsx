"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import type { ResearchProvider, ResearchStatus } from "@/lib/types";

interface ResearchActionsProps {
  accountId: string;
  runId: string | null;
  status: ResearchStatus | null;
  configuredProvider: ResearchProvider;
  liveResearchAvailable: boolean;
  archived: boolean;
}

interface ErrorPayload {
  detail?: string;
}

export function ResearchActions({
  accountId,
  runId,
  status,
  configuredProvider,
  liveResearchAvailable,
  archived,
}: ResearchActionsProps) {
  const router = useRouter();
  const [provider, setProvider] = useState<ResearchProvider>(configuredProvider);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status !== "queued" && status !== "running") return;
    const interval = window.setInterval(() => router.refresh(), 2000);
    return () => window.clearInterval(interval);
  }, [router, status]);

  async function mutate(path: string, body?: Record<string, string>) {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
      });
      const payload = (await response.json()) as ErrorPayload;
      if (!response.ok) {
        setError(payload.detail || "Unable to update this research run.");
        return;
      }
      setNotes("");
      router.refresh();
    } catch {
      setError("The API is unavailable. Check the local services and retry.");
    } finally {
      setBusy(false);
    }
  }

  function startResearch() {
    return mutate(`/api/backend/accounts/${accountId}/research-runs`, { provider });
  }

  function review(decision: "approve" | "reject") {
    if (!runId) return;
    if (notes.trim().length < 2) {
      setError("Add a short review note so the decision stays auditable.");
      return;
    }
    return mutate(`/api/backend/research-runs/${runId}/review`, {
      decision,
      notes: notes.trim(),
    });
  }

  if (!runId) {
    return (
      <div className="researchStartControls">
        <label>
          Research mode
          <select
            value={provider}
            onChange={(event) => setProvider(event.target.value as ResearchProvider)}
            disabled={busy || archived}
          >
            <option value="mock">Simulation · account inputs only</option>
            {liveResearchAvailable ? <option value="openai">Live web research · OpenAI</option> : null}
          </select>
        </label>
        <button className="button primary" disabled={busy || archived} onClick={startResearch}>
          {busy ? "Starting…" : "Start research"}
        </button>
        {!liveResearchAvailable ? (
          <small>Set OPENAI_API_KEY to enable live web research. Simulation never invents public facts.</small>
        ) : null}
        {error ? <p className="inlineError" role="alert">{error}</p> : null}
      </div>
    );
  }

  if (status === "queued" || status === "running") {
    return <div className="runPending"><span className="pulseDot" />Research is running. This page refreshes automatically.</div>;
  }

  if (status === "failed" || status === "rejected") {
    return (
      <div className="researchActionStack">
        <button
          className="button primary"
          disabled={busy || archived}
          onClick={() => mutate(`/api/backend/research-runs/${runId}/retry`)}
        >
          {busy ? "Retrying…" : "Retry research"}
        </button>
        {error ? <p className="inlineError" role="alert">{error}</p> : null}
      </div>
    );
  }

  if (status === "needs_review") {
    return (
      <div className="reviewControls">
        <label htmlFor="review-notes">Review notes</label>
        <textarea
          id="review-notes"
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          placeholder="Record what you checked, corrections needed, or approval rationale."
          maxLength={2000}
          rows={4}
          disabled={busy || archived}
        />
        <div className="reviewButtons">
          <button className="button dangerGhost" disabled={busy || archived} onClick={() => review("reject")}>
            Reject &amp; revise
          </button>
          <button className="button primary" disabled={busy || archived} onClick={() => review("approve")}>
            Approve evidence
          </button>
        </div>
        {error ? <p className="inlineError" role="alert">{error}</p> : null}
      </div>
    );
  }

  return <p className="approvedNote">Evidence approved. The workflow has advanced to Opportunity.</p>;
}
