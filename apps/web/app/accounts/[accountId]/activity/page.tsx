import Link from "next/link";
import { notFound } from "next/navigation";

import { ActivityTimeline } from "@/components/ActivityTimeline";
import { ApiError, apiGet } from "@/lib/api";
import type { Account, ActivityList } from "@/lib/types";


export const dynamic = "force-dynamic";

export default async function ActivityPage({ params }: { params: Promise<{ accountId: string }> }) {
  const { accountId } = await params;
  let account: Account;
  let activities: ActivityList;
  try {
    [account, activities] = await Promise.all([
      apiGet<Account>(`/accounts/${accountId}`),
      apiGet<ActivityList>(`/accounts/${accountId}/activities`),
    ]);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  return (
    <div className="page narrowPage">
      <header className="pageHeader">
        <div><span className="eyebrow">Audit trail · {account.name}</span><h1>Activity</h1><p>Every material workflow change is retained with its actor, reason and timestamp.</p></div>
        <Link href={`/accounts/${account.id}`} className="button secondary">Back to overview</Link>
      </header>
      <section className="panel fullActivityPanel">
        <div className="panelHeading"><div><span className="eyebrow">{activities.total} events</span><h2>Complete timeline</h2></div></div>
        <ActivityTimeline activities={activities.items} />
      </section>
    </div>
  );
}

