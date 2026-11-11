import { loadOverview, type Category, type RankedProduct, type ReviewSummary } from "./overview-data";
import { Retry } from "./retry";
import { TrendChart } from "./trend-chart";

const integer = new Intl.NumberFormat("en-US");
const percent = new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 1 });
const date = new Intl.DateTimeFormat("en-US", {
  month: "short", day: "numeric", year: "numeric", timeZone: "UTC",
});

function Metric({ label, value, detail, symbol }: {
  label: string; value: string; detail: string; symbol: string;
}) {
  return (
    <article className="panel metric">
      <span className="metric-icon" aria-hidden="true">{symbol}</span>
      <h2>{label}</h2>
      <p className="metric-value">{value}</p>
      <p className="metric-detail">{detail}</p>
    </article>
  );
}

function RatingDistribution({ summary }: { summary: ReviewSummary }) {
  return (
    <section className="panel ratings" aria-labelledby="ratings-title">
      <div className="panel-heading">
        <div><h2 id="ratings-title">Rating distribution</h2><p>Share of rated reviews</p></div>
      </div>
      {summary.rated_review_count > 0 ? (
        <ul className="rating-list">
          {summary.rating_distribution.toReversed().map(({ rating, review_count }) => {
            const share = review_count / summary.rated_review_count;
            return (
              <li key={rating}>
                <span className="stars">{rating} <span aria-label="stars">★</span></span>
                <span className="rating-track" aria-hidden="true">
                  <span style={{ width: `${share * 100}%` }} />
                </span>
                <span title={`${integer.format(review_count)} reviews`}>{percent.format(share)}</span>
              </li>
            );
          })}
        </ul>
      ) : <p className="empty-copy">No star ratings are available.</p>}
    </section>
  );
}

function CategoryMix({ rows }: { rows: Category[] }) {
  const categories = [...rows].sort((a, b) => b.product_count - a.product_count);
  const total = categories.reduce((sum, row) => sum + row.product_count, 0);
  return (
    <section className="panel category-panel" aria-labelledby="category-title">
      <div className="panel-heading">
        <div><h2 id="category-title">Catalog by category</h2><p>Products by primary category</p></div>
      </div>
      {total > 0 ? (
        <ul className="category-list">
          {categories.map(({ primary_category, product_count }) => (
            <li key={primary_category ?? "__unclassified"}>
              <div><span>{primary_category ?? "Unclassified"}</span><strong>{integer.format(product_count)}</strong></div>
              <span className="category-track" aria-hidden="true">
                <span style={{ width: `${product_count / total * 100}%` }} />
              </span>
            </li>
          ))}
        </ul>
      ) : <p className="empty-copy">No products are available.</p>}
    </section>
  );
}

function TopProducts({ rows }: { rows: RankedProduct[] }) {
  return (
    <section id="products" className="panel products" aria-labelledby="products-title">
      <div className="panel-heading">
        <div><h2 id="products-title">Most reviewed products</h2><p>Ranked by reviews in the dataset</p></div>
      </div>
      {rows.length ? (
        <div className="table-scroll" role="region" aria-label="Most reviewed products table" tabIndex={0}>
          <table>
            <thead><tr><th scope="col">Product</th><th scope="col">Category</th><th scope="col">Reviews</th><th scope="col">Rating</th></tr></thead>
            <tbody>{rows.map((product) => (
              <tr key={product.product_id}>
                <th scope="row"><strong>{product.product_name}</strong><small>{product.brand_name}</small></th>
                <td>{product.primary_category ?? "—"}</td>
                <td>{integer.format(product.observed_review_count)}</td>
                <td>{product.observed_average_rating?.toFixed(2) ?? "—"}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      ) : <p className="empty-copy">No ranked products are available.</p>}
    </section>
  );
}

export default async function Home() {
  const data = await loadOverview().catch(() => null);
  if (!data) {
    return (
      <>
        <h1>Executive overview</h1>
        <section className="panel unavailable" aria-labelledby="unavailable-title">
          <h2 id="unavailable-title">Analytics unavailable</h2>
          <p>Check that FastAPI is running and SEPHORA_DATASET_DIR points to the six CSV files.</p>
          <Retry />
        </section>
      </>
    );
  }
  const { overview, categories, reviews, products } = data;
  const years = new Map<string, number>();
  for (const { month, review_count } of reviews.monthly_trend) {
    const year = month.slice(0, 4);
    years.set(year, (years.get(year) ?? 0) + review_count);
  }
  const points = Array.from(years, ([year, count]) => ({ year, reviews: count }));
  const first = reviews.earliest_review_date;
  const last = reviews.latest_review_date;

  return (
    <>
      <div className="overview-heading">
        <div><h1>Executive overview</h1><p>Catalog performance and customer feedback from the Sephora dataset.</p></div>
        {first && last && <span className="date-range">{date.format(new Date(first))} – {date.format(new Date(last))}</span>}
      </div>

      <div className="metrics" aria-label="Key performance indicators">
        <Metric label="Catalog products" value={integer.format(overview.product_count)}
          detail={`${integer.format(overview.brand_count)} brands`} symbol="▤" />
        <Metric label="Observed reviews" value={integer.format(overview.observed_review_count)}
          detail={`Across ${integer.format(overview.products_with_observed_reviews)} products`} symbol="◷" />
        <Metric label="Average review rating" value={overview.observed_average_rating?.toFixed(2) ?? "—"}
          detail={`Out of 5 · ${integer.format(reviews.rated_review_count)} ratings`} symbol="★" />
        <Metric label="Recommendation rate"
          value={reviews.recommendation_rate === null ? "—" : percent.format(reviews.recommendation_rate)}
          detail={`${integer.format(reviews.recommendation_response_count)} known responses`} symbol="✓" />
      </div>

      <div className="chart-grid">
        <TrendChart points={points} />
        <RatingDistribution summary={reviews} />
      </div>
      <div className="detail-grid">
        <TopProducts rows={products} />
        <CategoryMix rows={categories} />
      </div>
    </>
  );
}
