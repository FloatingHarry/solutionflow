"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import type { Account, ApiErrorPayload } from "@/lib/types";


interface AccountFormProps {
  account?: Account;
}

export function AccountForm({ account }: AccountFormProps) {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const editing = Boolean(account);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(
      ["name", "website", "industry", "region", "notes"].map((key) => [
        key,
        String(form.get(key) ?? "").trim() || null,
      ]),
    );

    try {
      const response = await fetch(
        editing ? `/api/backend/accounts/${account?.id}` : "/api/backend/accounts",
        {
          method: editing ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      const data = (await response.json()) as Account & ApiErrorPayload;
      if (!response.ok) {
        const detail = Array.isArray(data.detail)
          ? data.detail.map((item) => item.msg).filter(Boolean).join("; ")
          : data.detail;
        throw new Error(detail || "Unable to save this account.");
      }
      router.push(`/accounts/${data.id}`);
      router.refresh();
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "Unable to save.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="accountForm" onSubmit={handleSubmit}>
      <div className="formSectionHeading">
        <div>
          <span className="eyebrow">Account profile</span>
          <h2>Company details</h2>
        </div>
        <p>Start with facts you already know. The Research workspace can turn them into a traceable, reviewable profile.</p>
      </div>

      <div className="field fullWidth">
        <label htmlFor="name">Company name <span>*</span></label>
        <input id="name" name="name" required maxLength={200} defaultValue={account?.name ?? ""} placeholder="Example Retail UK" />
      </div>

      <div className="field fullWidth">
        <label htmlFor="website">Website</label>
        <input id="website" name="website" maxLength={500} defaultValue={account?.website ?? ""} placeholder="https://example.com" inputMode="url" />
      </div>

      <div className="formGrid">
        <div className="field">
          <label htmlFor="industry">Industry</label>
          <input id="industry" name="industry" maxLength={120} defaultValue={account?.industry ?? ""} placeholder="Retail" />
        </div>
        <div className="field">
          <label htmlFor="region">Region</label>
          <input id="region" name="region" maxLength={120} defaultValue={account?.region ?? ""} placeholder="United Kingdom" />
        </div>
      </div>

      <div className="field fullWidth">
        <label htmlFor="notes">Notes</label>
        <textarea id="notes" name="notes" maxLength={10000} defaultValue={account?.notes ?? ""} placeholder="Context for the account team, upcoming meeting, known constraints…" rows={6} />
        <small>Internal context only. This is not treated as verified customer evidence.</small>
      </div>

      {error ? <div className="formError" role="alert">{error}</div> : null}

      <div className="formActions">
        <button type="button" className="button secondary" onClick={() => router.back()} disabled={submitting}>Cancel</button>
        <button type="submit" className="button primary" disabled={submitting}>
          {submitting ? "Saving…" : editing ? "Save changes" : "Create account"}
        </button>
      </div>
    </form>
  );
}
