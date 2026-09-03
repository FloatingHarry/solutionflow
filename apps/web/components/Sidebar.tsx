"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";


function AccountsIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 20V8l8-4 8 4v12M8 20v-6h8v6M8 10h.01M12 10h.01M16 10h.01" />
    </svg>
  );
}

function ActivityIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 12h4l2-5 4 10 2-5h4" />
    </svg>
  );
}

function EvaluationIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 19V9M10 19V5M16 19v-7M22 19V3M2 19h22" />
    </svg>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const accountsActive = pathname.startsWith("/accounts");
  const evaluationActive = pathname.startsWith("/evaluation");

  return (
    <aside className="sidebar">
      <Link href="/accounts" className="brand" aria-label="SolutionFlow home">
        <span className="brandMark">S</span>
        <span>
          <strong>SolutionFlow</strong>
          <small>Enterprise Copilot</small>
        </span>
      </Link>

      <nav className="primaryNav" aria-label="Primary navigation">
        <p className="navLabel">Workspace</p>
        <Link href="/accounts" className={accountsActive ? "navItem active" : "navItem"}>
          <AccountsIcon />
          Accounts
        </Link>
        <Link href="/evaluation" className={evaluationActive ? "navItem active" : "navItem"}>
          <EvaluationIcon />
          System evaluation
        </Link>
        <span className="navItem disabled" aria-disabled="true">
          <ActivityIcon />
          Solution catalog
          <small>Later</small>
        </span>
      </nav>

      <div className="sidebarFooter">
        <span className="environmentDot" />
        <span>
          <strong>Development</strong>
          <small>Phase 7 · MVP complete</small>
        </span>
      </div>
    </aside>
  );
}
