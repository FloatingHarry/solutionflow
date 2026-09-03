import { describe, expect, it } from "vitest";

import type { StageState } from "@/lib/types";
import { getInitials, getWorkflowProgress } from "@/lib/workflow";


function stage(status: StageState["status"]): StageState {
  return {
    stage: "research",
    status,
    started_at: null,
    completed_at: null,
    updated_at: "2026-09-01T00:00:00Z",
  };
}

describe("workflow helpers", () => {
  it("calculates completed-stage progress", () => {
    expect(getWorkflowProgress([stage("completed"), stage("not_started")])).toBe(50);
    expect(getWorkflowProgress([])).toBe(0);
  });

  it("creates compact account initials", () => {
    expect(getInitials("Example Retail UK")).toBe("ER");
    expect(getInitials("GLM")).toBe("GL");
  });
});

