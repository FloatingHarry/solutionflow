import { notFound } from "next/navigation";

import { AccountForm } from "@/components/AccountForm";
import { ApiError, apiGet } from "@/lib/api";
import type { Account } from "@/lib/types";


export const dynamic = "force-dynamic";

export default async function EditAccountPage({ params }: { params: Promise<{ accountId: string }> }) {
  const { accountId } = await params;
  let account: Account;
  try {
    account = await apiGet<Account>(`/accounts/${accountId}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  return (
    <div className="page narrowPage">
      <header className="pageHeader formPageHeader">
        <div><span className="eyebrow">Account profile</span><h1>Edit {account.name}</h1><p>Changes are recorded in the account activity trail.</p></div>
      </header>
      <AccountForm account={account} />
    </div>
  );
}

