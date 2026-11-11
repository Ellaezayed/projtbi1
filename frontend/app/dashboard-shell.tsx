import type { ReactNode } from "react";

export function DashboardShell({ children }: { children: ReactNode }) {
  return (
    <div className="workspace">
      <a className="skip" href="#main">Skip to content</a>
      <aside className="sidebar">
        <a className="identity" href="/" aria-label="Sephora Business Insight home">
          <span className="monogram" aria-hidden="true">S</span>
          <span><strong>SEPHORA</strong><small>Business Insight</small></span>
        </a>
        <nav aria-label="Dashboard navigation">
          <a className="current" href="#main" aria-current="page"><span aria-hidden="true">◈</span>Overview</a>
          <a href="#products"><span aria-hidden="true">▤</span>Product Analysis</a>
          <a href="#reviews"><span aria-hidden="true">◷</span>Review Analysis</a>
          <span className="nav-disabled" aria-disabled="true" title="Sentiment analysis is planned for a later part">
            <span aria-hidden="true">◇</span>Sentiment Analysis
          </span>
        </nav>
      </aside>
      <div className="workspace-main">
        <header className="topbar"><span>Sephora Business Insight</span><span className="topbar-label">Analytics workspace</span></header>
        <main id="main" className="dashboard" tabIndex={-1}>{children}</main>
      </div>
    </div>
  );
}
