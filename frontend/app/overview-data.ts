export type Overview = {
  product_count: number;
  brand_count: number;
  products_with_observed_reviews: number;
  observed_review_count: number;
  observed_average_rating: number | null;
};

export type Category = {
  primary_category: string | null;
  product_count: number;
  observed_review_count: number;
  observed_average_rating: number | null;
};

export type ReviewSummary = {
  recommendation_response_count: number;
  recommendation_rate: number | null;
  earliest_review_date: string | null;
  latest_review_date: string | null;
  rating_distribution: { rating: number; review_count: number }[];
  monthly_trend: { month: string; review_count: number }[];
  rated_review_count: number;
};

export type RankedProduct = {
  product_id: string;
  product_name: string;
  brand_name: string;
  primary_category: string | null;
  observed_review_count: number;
  observed_average_rating: number | null;
};

async function get<T>(path: string): Promise<T> {
  const origin = process.env.SEPHORA_API_URL || "http://127.0.0.1:8000";
  const response = await fetch(new URL(path, origin), {
    cache: "no-store",
    signal: AbortSignal.timeout(120_000),
  });
  if (!response.ok) throw new Error(`Analytics request failed with HTTP ${response.status}`);
  return response.json() as Promise<T>;
}

export async function loadOverview() {
  const [overview, categories, reviews, products] = await Promise.all([
    get<Overview>("/api/overview"),
    get<Category[]>("/api/categories"),
    get<ReviewSummary>("/api/reviews/summary"),
    get<{ items: RankedProduct[] }>("/api/products?sort=observed_review_count&order=desc&limit=5"),
  ]);
  return { overview, categories, reviews, products: products.items };
}
