"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { stageOrder } from "@/lib/types";
import type {
  DiscoveryQuestion,
  DiscoveryWorkspace as DiscoveryWorkspaceData,
  HypothesisStatus,
  OpportunityHypothesis,
} from "@/lib/types";

interface DiscoveryWorkspaceProps {
  accountId: string;
  initialWorkspace: DiscoveryWorkspaceData;
  archived: boolean;
}

const statusLabels: Record<HypothesisStatus, string> = {
  ai_suggested: "AI suggested",
  user_accepted: "Accepted",
  user_rejected: "Rejected",
  need_validation: "Needs validation",
  confirmed: "Confirmed need",
};

function totalAnswers(hypothesis: OpportunityHypothesis) {
  return hypothesis.questions.reduce((count, question) => count + question.answers.length, 0);
}

function apiDetail(payload: unknown) {
  if (!payload || typeof payload !== "object" || !("detail" in payload)) return null;
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (item && typeof item === "object" && "msg" in item ? String(item.msg) : ""))
      .filter(Boolean)
      .join(" ");
  }
  return null;
}

export function DiscoveryWorkspace({
  accountId,
  initialWorkspace,
  archived,
}: DiscoveryWorkspaceProps) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [manualOpen, setManualOpen] = useState(false);
  const [manual, setManual] = useState({
    title: "",
    description: "",
    business_area: "",
    potential_impact: "",
    confidence: "medium",
  });
  const [reviewNotes, setReviewNotes] = useState<Record<string, string>>({});
  const [questionHypothesis, setQuestionHypothesis] = useState<string | null>(null);
  const [newQuestion, setNewQuestion] = useState({ question: "", rationale: "" });
  const [editingQuestion, setEditingQuestion] = useState<string | null>(null);
  const [questionDraft, setQuestionDraft] = useState({ question: "", rationale: "" });
  const [answerQuestion, setAnswerQuestion] = useState<string | null>(null);
  const [answerDraft, setAnswerDraft] = useState({
    answer_text: "",
    respondent_name: "",
    respondent_role: "",
  });
  const [confirmHypothesis, setConfirmHypothesis] = useState<string | null>(null);
  const [needDraft, setNeedDraft] = useState({
    title: "",
    description: "",
    business_impact: "",
    success_metric: "",
    constraints: "",
  });
  const [discoveryNotes, setDiscoveryNotes] = useState("");

  const answerCount = useMemo(
    () => initialWorkspace.hypotheses.reduce((count, hypothesis) => count + totalAnswers(hypothesis), 0),
    [initialWorkspace.hypotheses],
  );
  const discoveryClosed =
    stageOrder.indexOf(initialWorkspace.current_stage) > stageOrder.indexOf("discovery");

  async function mutate(
    key: string,
    path: string,
    body?: Record<string, unknown>,
    method = "POST",
  ) {
    setBusy(key);
    setError(null);
    try {
      const response = await fetch(`/api/backend${path}`, {
        method,
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      const payload = response.status === 204 ? null : (await response.json());
      if (!response.ok) throw new Error(apiDetail(payload) || "Unable to save this change.");
      router.refresh();
      return true;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save this change.");
      return false;
    } finally {
      setBusy(null);
    }
  }

  async function generateHypotheses() {
    await mutate("generate", `/accounts/${accountId}/discovery/generate`, { max_hypotheses: 3 });
  }

  async function createManualHypothesis() {
    const saved = await mutate("manual", `/accounts/${accountId}/opportunity-hypotheses`, {
      ...manual,
      business_area: manual.business_area || null,
      potential_impact: manual.potential_impact || null,
      evidence_ids: [],
    });
    if (saved) {
      setManualOpen(false);
      setManual({
        title: "",
        description: "",
        business_area: "",
        potential_impact: "",
        confidence: "medium",
      });
    }
  }

  async function reviewHypothesis(
    hypothesis: OpportunityHypothesis,
    decision: "accept" | "reject" | "need_validation",
  ) {
    await mutate(`review-${hypothesis.id}`, `/opportunity-hypotheses/${hypothesis.id}/review`, {
      decision,
      notes: reviewNotes[hypothesis.id]?.trim() || "Reviewed in the discovery workspace.",
    });
  }

  async function addQuestion(hypothesisId: string) {
    const saved = await mutate(`question-${hypothesisId}`, `/opportunity-hypotheses/${hypothesisId}/questions`, {
      question: newQuestion.question,
      rationale: newQuestion.rationale || null,
    });
    if (saved) {
      setQuestionHypothesis(null);
      setNewQuestion({ question: "", rationale: "" });
    }
  }

  function beginEditQuestion(question: DiscoveryQuestion) {
    setEditingQuestion(question.id);
    setQuestionDraft({ question: question.question, rationale: question.rationale ?? "" });
  }

  async function updateQuestion(questionId: string) {
    const saved = await mutate(`edit-${questionId}`, `/discovery-questions/${questionId}`, {
      question: questionDraft.question,
      rationale: questionDraft.rationale || null,
    }, "PATCH");
    if (saved) setEditingQuestion(null);
  }

  async function deleteQuestion(questionId: string) {
    await mutate(`delete-${questionId}`, `/discovery-questions/${questionId}`, undefined, "DELETE");
  }

  async function recordAnswer(questionId: string) {
    const saved = await mutate(`answer-${questionId}`, `/discovery-questions/${questionId}/answers`, {
      answer_text: answerDraft.answer_text,
      respondent_name: answerDraft.respondent_name || null,
      respondent_role: answerDraft.respondent_role || null,
    });
    if (saved) {
      setAnswerQuestion(null);
      setAnswerDraft({ answer_text: "", respondent_name: "", respondent_role: "" });
    }
  }

  function beginConfirm(hypothesis: OpportunityHypothesis) {
    setConfirmHypothesis(hypothesis.id);
    setNeedDraft({
      title: hypothesis.title,
      description: hypothesis.description,
      business_impact: hypothesis.potential_impact ?? "",
      success_metric: "",
      constraints: "",
    });
  }

  async function confirmNeed(hypothesis: OpportunityHypothesis) {
    const answerIds = hypothesis.questions.flatMap((question) =>
      question.answers.map((answer) => answer.id),
    );
    const saved = await mutate(`confirm-${hypothesis.id}`, `/opportunity-hypotheses/${hypothesis.id}/confirm`, {
      ...needDraft,
      business_impact: needDraft.business_impact || null,
      constraints: needDraft.constraints || null,
      answer_ids: answerIds,
    });
    if (saved) setConfirmHypothesis(null);
  }

  async function reviewDiscovery(decision: "approve" | "reject") {
    await mutate(`discovery-${decision}`, `/accounts/${accountId}/discovery/review`, {
      decision,
      notes: discoveryNotes.trim() || "Discovery evidence reviewed by a human.",
    });
  }

  return (
    <>
      <section className="discoveryMetrics">
        <div><span>Hypotheses</span><strong>{initialWorkspace.hypotheses.length}</strong></div>
        <div><span>Customer answers</span><strong>{answerCount}</strong></div>
        <div><span>Confirmed needs</span><strong>{initialWorkspace.confirmed_needs.length}</strong></div>
        <div><span>Current gate</span><strong>{initialWorkspace.current_stage.replaceAll("_", " ")}</strong></div>
      </section>

      {!initialWorkspace.research_approved ? (
        <div className="discoveryPrerequisite">
          <strong>Research approval required</strong>
          <p>Approve the evidence-backed research profile before creating opportunity hypotheses.</p>
        </div>
      ) : null}

      {error ? <div className="researchError" role="alert"><strong>Could not save</strong><p>{error}</p></div> : null}

      <div className="discoveryGrid">
        <main className="discoveryMain">
          <section className="panel discoveryToolbar">
            <div>
              <span className="eyebrow">Opportunity pipeline</span>
              <h2>Hypotheses to validate</h2>
              <p>Generated drafts are grounded in approved research and remain hypotheses until customers answer.</p>
            </div>
            <div className="discoveryToolbarActions">
              <button
                className="button secondary"
                disabled={archived || discoveryClosed || !initialWorkspace.research_approved || busy !== null}
                onClick={() => setManualOpen((open) => !open)}
              >
                Add manually
              </button>
              <button
                className="button primary"
                disabled={archived || discoveryClosed || !initialWorkspace.research_approved || busy !== null}
                onClick={generateHypotheses}
              >
                {busy === "generate" ? "Generating…" : "Generate from research"}
              </button>
            </div>
          </section>

          {manualOpen ? (
            <section className="panel discoveryForm">
              <div className="panelHeading"><div><span className="eyebrow">Manual input</span><h2>New hypothesis</h2></div></div>
              <div className="discoveryFormBody twoColumnForm">
                <label>Title<input value={manual.title} onChange={(event) => setManual({ ...manual, title: event.target.value })} /></label>
                <label>Business area<input value={manual.business_area} onChange={(event) => setManual({ ...manual, business_area: event.target.value })} /></label>
                <label className="fullField">Description<textarea value={manual.description} onChange={(event) => setManual({ ...manual, description: event.target.value })} rows={3} /></label>
                <label>Confidence<select value={manual.confidence} onChange={(event) => setManual({ ...manual, confidence: event.target.value })}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></label>
                <label>Potential impact<input value={manual.potential_impact} onChange={(event) => setManual({ ...manual, potential_impact: event.target.value })} /></label>
                <div className="formActions fullField"><button className="button secondary" onClick={() => setManualOpen(false)}>Cancel</button><button className="button primary" disabled={busy !== null} onClick={createManualHypothesis}>Save hypothesis</button></div>
              </div>
            </section>
          ) : null}

          {!initialWorkspace.hypotheses.length ? (
            <section className="researchEmpty discoveryEmpty">
              <div className="emptyGlyph">◇</div>
              <h2>No opportunity hypotheses yet</h2>
              <p>Generate research-grounded drafts, then decide which ones deserve customer discovery.</p>
            </section>
          ) : null}

          {initialWorkspace.hypotheses.map((hypothesis, index) => (
            <article className="panel hypothesisCard" key={hypothesis.id}>
              <header className="hypothesisHeader">
                <div className="hypothesisIndex">H{String(index + 1).padStart(2, "0")}</div>
                <div>
                  <div className="hypothesisBadges">
                    <span className={`hypothesisStatus ${hypothesis.status}`}>{statusLabels[hypothesis.status]}</span>
                    <span>{hypothesis.origin.replaceAll("_", " ")}</span>
                    <span>{hypothesis.confidence} confidence</span>
                  </div>
                  <h2>{hypothesis.title}</h2>
                  <p>{hypothesis.description}</p>
                </div>
              </header>

              <div className="traceabilityRow">
                <div><span>Research evidence</span><strong>{hypothesis.evidence.length}</strong></div>
                <i>→</i><div><span>Questions</span><strong>{hypothesis.questions.length}</strong></div>
                <i>→</i><div><span>Answers</span><strong>{totalAnswers(hypothesis)}</strong></div>
                <i>→</i><div><span>Confirmed need</span><strong>{hypothesis.confirmed_need ? "Yes" : "Pending"}</strong></div>
              </div>

              {hypothesis.evidence.length ? (
                <details className="hypothesisEvidence">
                  <summary>View supporting research evidence</summary>
                  {hypothesis.evidence.map((citation) => (
                    <blockquote key={citation.evidence_id}>
                      <strong>{citation.source_title}</strong>
                      <span>{citation.supporting_text}</span>
                    </blockquote>
                  ))}
                </details>
              ) : null}

              {!archived && !discoveryClosed && hypothesis.status !== "confirmed" ? (
                <div className="hypothesisReview">
                  <input
                    aria-label={`Review notes for ${hypothesis.title}`}
                    value={reviewNotes[hypothesis.id] ?? hypothesis.review_notes ?? ""}
                    onChange={(event) => setReviewNotes({ ...reviewNotes, [hypothesis.id]: event.target.value })}
                    placeholder="Review notes"
                  />
                  <div>
                    <button className="button dangerGhost" disabled={busy !== null} onClick={() => reviewHypothesis(hypothesis, "reject")}>Reject</button>
                    <button className="button secondary" disabled={busy !== null} onClick={() => reviewHypothesis(hypothesis, "need_validation")}>Needs validation</button>
                    <button className="button primary" disabled={busy !== null} onClick={() => reviewHypothesis(hypothesis, "accept")}>Accept for discovery</button>
                  </div>
                </div>
              ) : null}

              <section className="questionSection">
                <div className="sectionTitleRow">
                  <div><span className="eyebrow">Customer discovery</span><h3>Interview questions & answers</h3></div>
                  {!archived && !discoveryClosed && hypothesis.status !== "user_rejected" && hypothesis.status !== "confirmed" ? (
                    <button className="textButton" onClick={() => setQuestionHypothesis(hypothesis.id)}>+ Add question</button>
                  ) : null}
                </div>

                {questionHypothesis === hypothesis.id ? (
                  <div className="inlineEditor">
                    <label>Question<textarea value={newQuestion.question} onChange={(event) => setNewQuestion({ ...newQuestion, question: event.target.value })} rows={2} /></label>
                    <label>Why ask this?<input value={newQuestion.rationale} onChange={(event) => setNewQuestion({ ...newQuestion, rationale: event.target.value })} /></label>
                    <div><button className="button secondary" onClick={() => setQuestionHypothesis(null)}>Cancel</button><button className="button primary" disabled={busy !== null} onClick={() => addQuestion(hypothesis.id)}>Add question</button></div>
                  </div>
                ) : null}

                <div className="questionList">
                  {hypothesis.questions.map((question, questionIndex) => (
                    <article className="questionCard" key={question.id}>
                      {editingQuestion === question.id ? (
                        <div className="inlineEditor compactEditor">
                          <label>Question<textarea value={questionDraft.question} onChange={(event) => setQuestionDraft({ ...questionDraft, question: event.target.value })} rows={2} /></label>
                          <label>Rationale<input value={questionDraft.rationale} onChange={(event) => setQuestionDraft({ ...questionDraft, rationale: event.target.value })} /></label>
                          <div><button className="button secondary" onClick={() => setEditingQuestion(null)}>Cancel</button><button className="button primary" disabled={busy !== null} onClick={() => updateQuestion(question.id)}>Save</button></div>
                        </div>
                      ) : (
                        <>
                          <div className="questionHeading">
                            <span>Q{questionIndex + 1}</span>
                            <div><strong>{question.question}</strong>{question.rationale ? <p>{question.rationale}</p> : null}</div>
                            {!archived && !discoveryClosed && !question.answers.length && hypothesis.status !== "confirmed" ? (
                              <div className="questionActions"><button onClick={() => beginEditQuestion(question)}>Edit</button><button onClick={() => deleteQuestion(question.id)}>Delete</button></div>
                            ) : null}
                          </div>
                          {question.answers.map((answer) => (
                            <blockquote className="customerAnswer" key={answer.id}>
                              <p>{answer.answer_text}</p>
                              <footer>{[answer.respondent_name, answer.respondent_role].filter(Boolean).join(" · ") || "Customer response"}</footer>
                            </blockquote>
                          ))}
                          {!archived && !discoveryClosed && hypothesis.status === "user_accepted" ? (
                            answerQuestion === question.id ? (
                              <div className="inlineEditor answerEditor">
                                <label>Customer answer<textarea value={answerDraft.answer_text} onChange={(event) => setAnswerDraft({ ...answerDraft, answer_text: event.target.value })} rows={3} /></label>
                                <div className="inlineFields"><label>Respondent<input value={answerDraft.respondent_name} onChange={(event) => setAnswerDraft({ ...answerDraft, respondent_name: event.target.value })} /></label><label>Role<input value={answerDraft.respondent_role} onChange={(event) => setAnswerDraft({ ...answerDraft, respondent_role: event.target.value })} /></label></div>
                                <div><button className="button secondary" onClick={() => setAnswerQuestion(null)}>Cancel</button><button className="button primary" disabled={busy !== null} onClick={() => recordAnswer(question.id)}>Record answer</button></div>
                              </div>
                            ) : <button className="textButton answerButton" onClick={() => setAnswerQuestion(question.id)}>+ Record customer answer</button>
                          ) : null}
                        </>
                      )}
                    </article>
                  ))}
                </div>
              </section>

              {hypothesis.status === "user_accepted" && totalAnswers(hypothesis) > 0 && !archived && !discoveryClosed ? (
                confirmHypothesis === hypothesis.id ? (
                  <div className="confirmNeedForm">
                    <div><span className="eyebrow">Human confirmation</span><h3>Convert to confirmed need</h3></div>
                    <div className="twoColumnForm">
                      <label>Need title<input value={needDraft.title} onChange={(event) => setNeedDraft({ ...needDraft, title: event.target.value })} /></label>
                      <label>Success metric<input value={needDraft.success_metric} onChange={(event) => setNeedDraft({ ...needDraft, success_metric: event.target.value })} /></label>
                      <label className="fullField">Confirmed description<textarea value={needDraft.description} onChange={(event) => setNeedDraft({ ...needDraft, description: event.target.value })} rows={3} /></label>
                      <label>Business impact<input value={needDraft.business_impact} onChange={(event) => setNeedDraft({ ...needDraft, business_impact: event.target.value })} /></label>
                      <label>Constraints<input value={needDraft.constraints} onChange={(event) => setNeedDraft({ ...needDraft, constraints: event.target.value })} /></label>
                      <div className="formActions fullField"><button className="button secondary" onClick={() => setConfirmHypothesis(null)}>Cancel</button><button className="button primary" disabled={busy !== null} onClick={() => confirmNeed(hypothesis)}>Confirm customer need</button></div>
                    </div>
                  </div>
                ) : <div className="confirmPrompt"><div><strong>Customer evidence recorded</strong><p>Turn this accepted hypothesis into a confirmed, measurable need.</p></div><button className="button primary" onClick={() => beginConfirm(hypothesis)}>Confirm need</button></div>
              ) : null}

              {hypothesis.confirmed_need ? (
                <section className="confirmedNeed">
                  <span className="eyebrow">Confirmed customer need</span>
                  <h3>{hypothesis.confirmed_need.title}</h3>
                  <p>{hypothesis.confirmed_need.description}</p>
                  <dl><div><dt>Success metric</dt><dd>{hypothesis.confirmed_need.success_metric}</dd></div>{hypothesis.confirmed_need.business_impact ? <div><dt>Business impact</dt><dd>{hypothesis.confirmed_need.business_impact}</dd></div> : null}{hypothesis.confirmed_need.constraints ? <div><dt>Constraints</dt><dd>{hypothesis.confirmed_need.constraints}</dd></div> : null}</dl>
                </section>
              ) : null}
            </article>
          ))}
        </main>

        <aside className="discoveryAside">
          <section className="panel reviewPanel stickyReview">
            <div className="panelHeading"><div><span className="eyebrow">Human gate</span><h2>Discovery review</h2></div></div>
            <div className="reviewBody">
              <p>Approve only when customer answers support at least one measurable confirmed need.</p>
              {initialWorkspace.current_stage === "discovery" && !archived ? (
                <div className="reviewControls">
                  <label>Review notes<textarea value={discoveryNotes} onChange={(event) => setDiscoveryNotes(event.target.value)} rows={4} placeholder="What was verified?" /></label>
                  <div className="reviewButtons">
                    <button className="button dangerGhost" disabled={busy !== null} onClick={() => reviewDiscovery("reject")}>Needs revision</button>
                    <button className="button primary" disabled={busy !== null || !initialWorkspace.confirmed_needs.length} onClick={() => reviewDiscovery("approve")}>Approve discovery</button>
                  </div>
                </div>
              ) : initialWorkspace.current_stage === "solution" || initialWorkspace.reviews.at(0)?.decision === "approve" ? (
                <p className="approvedNote">Discovery approved. The workflow is ready for solution design.</p>
              ) : <p className="approvedNote mutedApproval">Accept a hypothesis to start customer discovery.</p>}
              {initialWorkspace.reviews[0] ? <blockquote>{initialWorkspace.reviews[0].notes}</blockquote> : null}
            </div>
          </section>

          <section className="panel discoveryRules">
            <div className="panelHeading"><div><span className="eyebrow">Evidence rules</span><h2>Guardrails</h2></div></div>
            <ol><li>Research claims must be human approved.</li><li>Hypotheses are not customer facts.</li><li>Confirmed needs require customer answers.</li><li>Solution design starts after review approval.</li></ol>
          </section>
        </aside>
      </div>
    </>
  );
}
