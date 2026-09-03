import type { Activity } from "@/lib/types";


function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function ActivityTimeline({ activities, compact = false }: { activities: Activity[]; compact?: boolean }) {
  if (activities.length === 0) {
    return <div className="emptyInline">No activity has been recorded.</div>;
  }

  const visible = compact ? activities.slice(0, 5) : activities;
  return (
    <div className="timeline">
      {visible.map((activity) => (
        <article className="timelineItem" key={activity.id}>
          <span className="timelineDot" />
          <div className="timelineContent">
            <div>
              <strong>{activity.summary}</strong>
              <time dateTime={activity.created_at}>{formatDate(activity.created_at)}</time>
            </div>
            <p>{activity.event_type.replaceAll(".", " · ")}</p>
            {typeof activity.metadata.reason === "string" ? (
              <blockquote>{activity.metadata.reason}</blockquote>
            ) : null}
          </div>
        </article>
      ))}
    </div>
  );
}

