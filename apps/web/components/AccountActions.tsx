"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";


interface AccountActionsProps {
  accountId: string;
  archived: boolean;
}

export function AccountActions({ accountId, archived }: AccountActionsProps) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function toggleArchive() {
    const action = archived ? "restore" : "archive";
    if (!archived && !window.confirm("Archive this account? Its history will be preserved.")) return;
    setBusy(true);
    const response = await fetch(`/api/backend/accounts/${accountId}/${action}`, { method: "POST" });
    setBusy(false);
    if (response.ok) {
      router.refresh();
    }
  }

  return (
    <div className="headerActions">
      {!archived ? <Link href={`/accounts/${accountId}/edit`} className="button secondary">Edit account</Link> : null}
      <button className={archived ? "button primary" : "button dangerGhost"} onClick={toggleArchive} disabled={busy}>
        {busy ? "Working…" : archived ? "Restore" : "Archive"}
      </button>
    </div>
  );
}
