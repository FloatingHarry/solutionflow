import type { StageName, StageState } from "@/lib/types";

export const stageLabels: Record<StageName, string> = {
  research: "Research",
  opportunity: "Opportunity",
  discovery: "Discovery",
  solution: "Solution",
  poc: "POC",
  evaluation: "Evaluation",
  business_case: "Business case",
  deployment: "Deployment",
};

export const statusLabels = {
  not_started: "Not started",
  in_progress: "In progress",
  blocked: "Blocked",
  completed: "Completed",
} as const;

export function getWorkflowProgress(stages: StageState[]): number {
  if (stages.length === 0) return 0;
  const completed = stages.filter((stage) => stage.status === "completed").length;
  return Math.round((completed / stages.length) * 100);
}

export function getInitials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "—";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return `${words[0][0]}${words[1][0]}`.toUpperCase();
}

