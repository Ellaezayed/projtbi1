"""Compute BI metrics using the cleaned review rows and catalog snapshot."""
from dataclasses import dataclass
import json

import pandas as pd

from dataset import Dataset


def records(frame: pd.DataFrame) -> list[dict]:
    return json.loads(frame.to_json(orient="records", date_format="iso", double_precision=12))


@dataclass(frozen=True)
class Snapshot:
    products: pd.DataFrame
    reviews: pd.DataFrame
    overview: dict
    categories: list[dict]
    review_summary: dict


def average(values: pd.Series) -> float | None:
    return float(values.mean()) if values.count() else None


def build_snapshot(data: Dataset) -> Snapshot:
    reviews = data.reviews
    per_product = reviews.groupby("product_id", observed=True).agg(
        observed_review_count=("rating", "size"),
        observed_rating_count=("rating", "count"),
        observed_average_rating=("rating", "mean"),
    )
    products = data.products.join(per_product, on="product_id", validate="one_to_one")
    count_fields = ["observed_review_count", "observed_rating_count"]
    products[count_fields] = products[count_fields].fillna(0).astype("int64")

    category_groups = products.groupby("primary_category", dropna=False)
    categories = category_groups.agg(
        product_count=("product_id", "size"),
        average_listed_price_usd=("price_usd", "mean"),
        observed_review_count=("observed_review_count", "sum"),
    )
    category_ratings = reviews.groupby("primary_category", observed=True, dropna=False)["rating"].mean()
    categories["observed_average_rating"] = category_ratings
    categories = categories.reset_index().sort_values("primary_category", na_position="last")

    rating_counts = reviews["rating"].value_counts()
    recommendation = reviews["is_recommended"]
    known = int(recommendation.count())
    recommended = int(recommendation.eq(1).sum())
    dated = reviews["submission_time"].dropna()
    months = dated.dt.to_period("M").value_counts().sort_index()
    price = products["price_usd"].dropna()
    overview = {
        "product_count": len(products),
        "brand_count": int(products["brand_name"].nunique()),
        "products_with_observed_reviews": len(per_product),
        "catalog_rated_product_count": int(products["catalog_rating"].count()),
        "average_catalog_product_rating": average(products["catalog_rating"]),
        "average_listed_price_usd": average(price),
        "median_listed_price_usd": float(price.median()) if len(price) else None,
        "observed_review_count": len(reviews),
        "observed_average_rating": average(reviews["rating"]),
        "quality": {
            "source_review_count": data.source_review_count,
            "duplicate_review_count": data.duplicate_count,
            "unmatched_review_count": data.unmatched_count,
            "invalid_rating_count": data.invalid_rating_count,
            "invalid_date_count": data.invalid_date_count,
            "invalid_recommendation_count": data.invalid_recommendation_count,
        },
    }
    review_summary = {
        "observed_review_count": len(reviews),
        "rated_review_count": int(reviews["rating"].count()),
        "observed_average_rating": average(reviews["rating"]),
        "rating_distribution": [
            {"rating": stars, "review_count": int(rating_counts.get(stars, 0))}
            for stars in range(1, 6)
        ],
        "recommendation_response_count": known,
        "recommended_count": recommended,
        "recommendation_rate": recommended / known if known else None,
        "text_review_count": int(reviews["review_text"].count()),
        "dated_review_count": len(dated),
        "earliest_review_date": dated.min().date().isoformat() if len(dated) else None,
        "latest_review_date": dated.max().date().isoformat() if len(dated) else None,
        "monthly_trend": [
            {"month": str(month), "review_count": int(count)} for month, count in months.items()
        ],
    }
    return Snapshot(products, reviews, overview, records(categories), review_summary)


def page(frame: pd.DataFrame, limit: int, offset: int) -> dict:
    return {"total": len(frame), "limit": limit, "offset": offset,
            "items": records(frame.iloc[offset:offset + limit])}
