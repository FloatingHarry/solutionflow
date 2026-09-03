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

function CatalogIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 4h5v5H5zM14 4h5v5h-5zM5 14h5v5H5zM14 14h5v5h-5z" />
    </svg>
  );
}

function BrandGlyph() {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <path d="M7 9.5 16 4l9 5.5v8L16 23l-9-5.5z" />
      <path d="m7 17.5 9 5.5 9-5.5V23l-9 5-9-5z" />
      <path d="M16 12v11" />
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
        <span className="brandMark"><BrandGlyph /></span>
        <span className="brandCopy">
          <strong>SolutionFlow</strong>
          <small>Enterprise intelligence</small>
        </span>
        <span className="brandEdition">01</span>
      </Link>

      <nav className="primaryNav" aria-label="Primary navigation">
        <div className="navGroupHeading"><p className="navLabel">Command center</p><span>2 spaces</span></div>
        <Link href="/accounts" className={accountsActive ? "navItem active" : "navItem"}>
          <AccountsIcon />
          <span className="navItemCopy"><strong>Accounts</strong><small>Opportunity pipeline</small></span>
          <span className="navIndicator" />
        </Link>
        <Link href="/evaluation" className={evaluationActive ? "navItem active" : "navItem"}>
          <EvaluationIcon />
          <span className="navItemCopy"><strong>System evaluation</strong><small>Quality & regression</small></span>
          <span className="navIndicator" />
        </Link>
        <span className="navItem disabled" aria-disabled="true">
          <CatalogIcon />
          <span className="navItemCopy"><strong>Solution catalog</strong><small>Reusable patterns</small></span>
          <span className="navSoon">Soon</span>
        </span>
      </nav>

      <div className="sidebarPulseCard">
        <div className="pulseGlyph"><ActivityIcon /></div>
        <div><span>Decision engine</span><strong>Evidence-linked</strong></div>
        <i aria-hidden="true" />
      </div>

      <div className="sidebarFooter">
        <span className="environmentDot" />
        <span>
          <strong>Workspace online</strong>
          <small>MVP · 8 stages operational</small>
        </span>
        <span className="environmentCode">DEV</span>
      </div>
    </aside>
  );
}
