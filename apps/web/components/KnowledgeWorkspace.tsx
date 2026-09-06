"use client";

import { FormEvent, useMemo, useState } from "react";

import type {
  ApiErrorPayload,
  EvidenceCandidateStatus,
  KnowledgeDocument,
  KnowledgeDocumentStatus,
  KnowledgeEvidenceCandidate,
  KnowledgeQuery,
  KnowledgeScope,
  KnowledgeWorkspace as KnowledgeWorkspaceData,
} from "@/lib/types";


interface KnowledgeWorkspaceProps {
  initialWorkspace: KnowledgeWorkspaceData;
  accountName: string;
  accountRegion: string | null;
  accountIndustry: string | null;
  readOnly?: boolean;
}

function getErrorMessage(payload: ApiErrorPayload, fallback: string) {
  if (typeof payload.detail === "string") return payload.detail;
  if (Array.isArray(payload.detail)) {
    return payload.detail.map((item) => item.msg).filter(Boolean).join(", ") || fallback;
  }
  return fallback;
}

function KnowledgeGlyph() {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <path d="M7 6.5h12a4 4 0 0 1 4 4v15H11a4 4 0 0 1-4-4z" />
      <path d="M11 6.5v19M15 12h5M15 16h5M15 20h4" />
    </svg>
  );
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function locator(citation: KnowledgeEvidenceCandidate) {
  if (citation.page_number) return `p.${citation.page_number}`;
  if (citation.section) return `§ ${citation.section}`;
  return "chunk source";
}

function scopeLabel(scope: KnowledgeScope) {
  return scope === "account" ? "Account private" : "Enterprise shared";
}

export function KnowledgeWorkspace({
  initialWorkspace,
  accountName,
  accountRegion,
  accountIndustry,
  readOnly = false,
}: KnowledgeWorkspaceProps) {
  const [workspace, setWorkspace] = useState(initialWorkspace);
  const [documentScope, setDocumentScope] = useState<KnowledgeScope>("account");
  const [visibleScope, setVisibleScope] = useState<"all" | KnowledgeScope>("all");
  const [question, setQuestion] = useState("");
  const [searchScope, setSearchScope] = useState<"both" | KnowledgeScope>("both");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadKey, setUploadKey] = useState(0);
  const latestQuery = workspace.recent_queries[0] ?? null;
  const activeDocuments = workspace.documents.filter((document) => document.status === "active");
  const accountCount = activeDocuments.filter((document) => document.knowledge_scope === "account").length;
  const enterpriseCount = activeDocuments.filter((document) => document.knowledge_scope === "enterprise").length;
  const filteredDocuments = useMemo(
    () => workspace.documents.filter((document) => visibleScope === "all" || document.knowledge_scope === visibleScope),
    [visibleScope, workspace.documents],
  );

  async function refreshWorkspace() {
    const response = await fetch(`/api/backend/accounts/${workspace.account_id}/knowledge`, {
      cache: "no-store",
    });
    const payload = (await response.json()) as KnowledgeWorkspaceData & ApiErrorPayload;
    if (!response.ok) throw new Error(getErrorMessage(payload, "Unable to refresh knowledge."));
    setWorkspace(payload);
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || readOnly) return;
    const form = event.currentTarget;
    const formData = new FormData(form);
    setBusy("upload");
    setError(null);
    try {
      const response = await fetch(`/api/backend/accounts/${workspace.account_id}/knowledge/documents`, {
        method: "POST",
        body: formData,
      });
      const payload = (await response.json()) as KnowledgeDocument & ApiErrorPayload;
      if (!response.ok) throw new Error(getErrorMessage(payload, "Unable to ingest this document."));
      form.reset();
      setUploadKey((value) => value + 1);
      await refreshWorkspace();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to ingest this document.");
    } finally {
      setBusy(null);
    }
  }

  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (question.trim().length < 2 || busy || readOnly) return;
    setBusy("ask");
    setError(null);
    const scopes: KnowledgeScope[] = searchScope === "both" ? ["account", "enterprise"] : [searchScope];
    try {
      const response = await fetch(`/api/backend/accounts/${workspace.account_id}/knowledge/answers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: question.trim(), scopes, filters: {}, top_k: 6 }),
      });
      const payload = (await response.json()) as KnowledgeQuery & ApiErrorPayload;
      if (!response.ok) throw new Error(getErrorMessage(payload, "Knowledge retrieval failed."));
      setWorkspace((current) => ({
        ...current,
        answer_provider: payload.provider,
        recent_queries: [payload, ...current.recent_queries.filter((item) => item.id !== payload.id)],
      }));
      setQuestion("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Knowledge retrieval failed.");
    } finally {
      setBusy(null);
    }
  }

  async function changeDocumentStatus(document: KnowledgeDocument, status: KnowledgeDocumentStatus) {
    if (busy || readOnly) return;
    setBusy(document.id);
    setError(null);
    try {
      const response = await fetch(
        `/api/backend/accounts/${workspace.account_id}/knowledge/documents/${document.id}/status`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status }),
        },
      );
      const payload = (await response.json()) as KnowledgeDocument & ApiErrorPayload;
      if (!response.ok) throw new Error(getErrorMessage(payload, "Unable to change document status."));
      await refreshWorkspace();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to change document status.");
    } finally {
      setBusy(null);
    }
  }

  async function reviewEvidence(candidate: KnowledgeEvidenceCandidate, status: EvidenceCandidateStatus) {
    if (busy || readOnly || status === "retrieved") return;
    setBusy(candidate.id);
    setError(null);
    try {
      const response = await fetch(
        `/api/backend/accounts/${workspace.account_id}/knowledge/evidence-candidates/${candidate.id}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status }),
        },
      );
      const payload = (await response.json()) as { id: string; status: EvidenceCandidateStatus; detail?: string };
      if (!response.ok) throw new Error(payload.detail || "Unable to review evidence.");
      setWorkspace((current) => ({
        ...current,
        recent_queries: current.recent_queries.map((query) => ({
          ...query,
          citations: query.citations.map((item) => item.id === candidate.id ? { ...item, status: payload.status } : item),
        })),
      }));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to review evidence.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="knowledgeWorkspace">
      <section className="knowledgeHero">
        <div className="knowledgeHeroCopy">
          <span className="knowledgeGlyph"><KnowledgeGlyph /></span>
          <div>
            <span className="eyebrow"><i /> Phase 9 · Knowledge-grounded Agent</span>
            <h2>One evidence layer. Two trust boundaries.</h2>
            <p>
              {accountName} can retrieve its private customer context alongside shared enterprise playbooks—without mixing another account&apos;s data or skipping human confirmation.
            </p>
          </div>
        </div>
        <div className="knowledgeScopeMap" aria-label="Knowledge access map">
          <div><span>ACCOUNT</span><strong>{accountCount}</strong><small>private active docs</small></div>
          <i>+</i>
          <div><span>ENTERPRISE</span><strong>{enterpriseCount}</strong><small>shared active docs</small></div>
          <b>→</b>
          <div className="knowledgeScopeAgent"><span>AGENT</span><strong>{workspace.embedding_provider === "openai" ? "Dense" : "Local"}</strong><small>hybrid retrieval</small></div>
        </div>
      </section>

      <section className="knowledgeStats">
        <div><span>Accessible scope</span><strong>Account + Enterprise</strong><small>Other accounts excluded</small></div>
        <div><span>Index</span><strong>Vector + keyword</strong><small>Metadata reranking</small></div>
        <div><span>Answer mode</span><strong>{workspace.answer_provider === "openai" ? "OpenAI grounded" : "Guided evidence"}</strong><small>{workspace.live_answer_available ? "Live model available" : "No API key required"}</small></div>
        <div><span>Business boundary</span><strong>Candidate only</strong><small>Never auto-confirms needs</small></div>
      </section>

      <div className="knowledgeMainGrid">
        <section className="knowledgeAskPanel">
          <div className="knowledgePanelHeading">
            <div><span className="eyebrow">Grounded retrieval</span><h3>Ask across authorized knowledge</h3></div>
            <span className="knowledgeLiveSignal"><i /> Audited</span>
          </div>
          <form className="knowledgeAskForm" onSubmit={ask}>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Example: Which deployment model fits this UK SaaS customer, and what evidence supports it?"
              disabled={readOnly || Boolean(busy)}
              rows={3}
            />
            <div>
              <label>
                Search boundary
                <select value={searchScope} onChange={(event) => setSearchScope(event.target.value as "both" | KnowledgeScope)} disabled={Boolean(busy)}>
                  <option value="both">Account + Enterprise</option>
                  <option value="account">Account only</option>
                  <option value="enterprise">Enterprise only</option>
                </select>
              </label>
              <button type="submit" disabled={readOnly || Boolean(busy) || question.trim().length < 2}>
                <span>{busy === "ask" ? "Retrieving…" : "Retrieve & answer"}</span><i>↗</i>
              </button>
            </div>
          </form>

          {latestQuery ? (
            <article className="knowledgeAnswer">
              <header>
                <div><span>Latest grounded response</span><strong>{latestQuery.provider === "openai" ? latestQuery.model : "Deterministic evidence view"}</strong></div>
                <em>{latestQuery.citations.length} citations</em>
              </header>
              <h4>{latestQuery.question}</h4>
              <p>{latestQuery.answer}</p>
              <div className="knowledgeBoundaryNotice">
                <strong>Evidence boundary</strong>
                <span>Retrieved chunks remain Evidence Candidates. Review does not create a Claim, Hypothesis, or Confirmed Need.</span>
              </div>
            </article>
          ) : (
            <div className="knowledgeEmptyAnswer">
              <KnowledgeGlyph />
              <strong>Start with a business question.</strong>
              <span>The answer will expose every source, locator, version, and retrieval score.</span>
            </div>
          )}
        </section>

        <aside className="knowledgeUploadPanel">
          <div className="knowledgePanelHeading">
            <div><span className="eyebrow">Ingestion</span><h3>Add a versioned source</h3></div>
          </div>
          <div className="knowledgeScopeSwitch">
            <button className={documentScope === "account" ? "active" : ""} type="button" onClick={() => setDocumentScope("account")}>Account private</button>
            <button className={documentScope === "enterprise" ? "active" : ""} type="button" onClick={() => setDocumentScope("enterprise")}>Enterprise shared</button>
          </div>
          <form className="knowledgeUploadForm" onSubmit={upload} key={`${uploadKey}-${documentScope}`}>
            <input type="hidden" name="knowledge_scope" value={documentScope} />
            <label className="knowledgeFileDrop">
              <input name="file" type="file" accept={workspace.accepted_extensions.join(",")} required disabled={readOnly || Boolean(busy)} />
              <span><KnowledgeGlyph /></span>
              <strong>Choose PDF, DOCX or Markdown</strong>
              <small>Up to {workspace.max_upload_mb} MB · text is parsed server-side</small>
            </label>
            <div className="knowledgeFormGrid">
              <label>Document type<input name="document_type" defaultValue={documentScope === "account" ? "discovery_notes" : "solution_playbook"} maxLength={80} required /></label>
              <label>Confidentiality<select name="confidentiality" defaultValue={documentScope === "account" ? "confidential" : "internal"}><option value="internal">Internal</option><option value="confidential">Confidential</option><option value="restricted">Restricted</option></select></label>
              <label>Industry<input name="industry" defaultValue={accountIndustry ?? ""} maxLength={120} /></label>
              <label>Region<input name="region" defaultValue={accountRegion ?? ""} maxLength={120} /></label>
              <label>Product<input name="product" placeholder="Optional" maxLength={160} /></label>
              <label>Deployment mode<input name="deployment_mode" placeholder="Optional" maxLength={120} /></label>
            </div>
            <button className="knowledgeIngestButton" type="submit" disabled={readOnly || Boolean(busy)}>{busy === "upload" ? "Parsing & indexing…" : `Ingest into ${scopeLabel(documentScope)}`}<span>→</span></button>
          </form>
        </aside>
      </div>

      {error ? <p className="formError knowledgeError">{error}</p> : null}

      {latestQuery?.citations.length ? (
        <section className="knowledgeEvidenceSection">
          <div className="knowledgeSectionHeading">
            <div><span className="eyebrow">Referenced evidence</span><h3>Source-level grounding</h3></div>
            <p>Vector + keyword candidates → metadata filter → deterministic rerank → top-k evidence</p>
          </div>
          <div className="knowledgeCitationGrid">
            {latestQuery.citations.map((citation, index) => (
              <article key={citation.id} className="knowledgeCitationCard" data-scope={citation.knowledge_scope}>
                <header>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <div><strong>{citation.document_title}</strong><small>{citation.source_file} · v{citation.document_version} · {locator(citation)}</small></div>
                  <em>{scopeLabel(citation.knowledge_scope)}</em>
                </header>
                <blockquote>{citation.excerpt}</blockquote>
                <footer>
                  <div><span>Rerank</span><strong>{citation.rerank_score.toFixed(3)}</strong></div>
                  <code>{citation.citation_id}</code>
                  {citation.status === "retrieved" ? (
                    <div className="knowledgeReviewActions">
                      <button disabled={Boolean(busy) || readOnly} onClick={() => reviewEvidence(citation, "reviewed")}>Review</button>
                      <button disabled={Boolean(busy) || readOnly} onClick={() => reviewEvidence(citation, "rejected")}>Reject</button>
                    </div>
                  ) : <b data-status={citation.status}>{citation.status}</b>}
                </footer>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <section className="knowledgeLibrary">
        <div className="knowledgeSectionHeading">
          <div><span className="eyebrow">Knowledge library</span><h3>Versions, metadata & access</h3></div>
          <div className="knowledgeLibraryFilters">
            {(["all", "account", "enterprise"] as const).map((scope) => <button key={scope} className={visibleScope === scope ? "active" : ""} onClick={() => setVisibleScope(scope)}>{scope}</button>)}
          </div>
        </div>
        {filteredDocuments.length ? (
          <div className="knowledgeDocumentTable">
            <div className="knowledgeDocumentRow heading"><span>Source</span><span>Namespace</span><span>Metadata</span><span>Index</span><span>Status</span></div>
            {filteredDocuments.map((document) => (
              <div className="knowledgeDocumentRow" key={document.id}>
                <div><strong>{document.title}</strong><small>{document.source_file} · {formatBytes(document.size_bytes)}</small></div>
                <div><em data-scope={document.knowledge_scope}>{scopeLabel(document.knowledge_scope)}</em><small>{document.confidentiality}</small></div>
                <div><strong>{document.document_type.replaceAll("_", " ")}</strong><small>{[document.industry, document.region, document.product, document.deployment_mode].filter(Boolean).join(" · ") || "General"}</small></div>
                <div><strong>v{document.version} · {document.chunk_count} chunks</strong><small>{document.page_count ? `${document.page_count} pages · ` : ""}{document.embedding_model}</small></div>
                <div className="knowledgeDocumentStatus"><span data-status={document.status}>{document.status}</span>{document.status === "active" ? <button disabled={Boolean(busy) || readOnly} onClick={() => changeDocumentStatus(document, "archived")}>Archive</button> : <button disabled={Boolean(busy) || readOnly} onClick={() => changeDocumentStatus(document, "active")}>Activate</button>}</div>
              </div>
            ))}
          </div>
        ) : <div className="knowledgeLibraryEmpty">No documents in this namespace yet.</div>}
      </section>
    </div>
  );
}
