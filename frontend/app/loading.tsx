export default function Loading() {
  return (
    <div role="status" aria-live="polite">
      <h1>Executive overview</h1>
      <p className="loading-label">Loading catalog and review metrics…</p>
      <div aria-hidden="true">
        <div className="metrics">{Array.from({ length: 4 }, (_, index) => (
          <div className="panel skeleton skeleton-card" key={index} />
        ))}</div>
        <div className="chart-grid">
          <div className="panel skeleton skeleton-chart" />
          <div className="panel skeleton skeleton-chart" />
        </div>
      </div>
    </div>
  );
}
