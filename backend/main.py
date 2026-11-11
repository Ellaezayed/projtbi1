import os
from datetime import date
from pathlib import Path
from typing import Annotated, Literal

import pandas as pd
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from dataset import DatasetError, SnapshotCache
from metrics import Snapshot, page

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

app = FastAPI(title="Sephora Business Insight")
cache = SnapshotCache()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")],
    allow_methods=["GET"],
    allow_headers=[],
)

def dataset_directory() -> Path | None:
    configured = os.getenv("SEPHORA_DATASET_DIR", "").strip()
    if not configured:
        return None
    path = Path(configured).expanduser()
    return path if path.is_absolute() else BACKEND_DIR / path

@app.get("/health")
def health() -> dict[str, str | bool]:
    directory = dataset_directory()
    return {
        "status": "ok",
        "dataset_directory_exists": directory is not None and directory.is_dir(),
    }


def current_snapshot() -> Snapshot:
    directory = dataset_directory()
    if directory is None:
        raise HTTPException(503, "Set SEPHORA_DATASET_DIR to the local CSV directory.")
    try:
        return cache.get(directory)
    except DatasetError as exc:
        raise HTTPException(503, str(exc)) from exc


Data = Annotated[Snapshot, Depends(current_snapshot)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]
Rating = Annotated[int | None, Query(ge=1, le=5)]
ProductSort = Literal[
    "product_name", "price_usd", "catalog_rating",
    "observed_average_rating", "observed_review_count", "loves_count",
]


@app.get("/api/overview")
def overview(data: Data) -> dict:
    return data.overview


@app.get("/api/categories")
def categories(data: Data) -> list[dict]:
    return data.categories


@app.get("/api/products")
def products(
    data: Data,
    limit: Limit = 25,
    offset: Offset = 0,
    q: Annotated[str | None, Query(max_length=120)] = None,
    category: Annotated[str | None, Query(max_length=120)] = None,
    min_catalog_rating: Annotated[float | None, Query(ge=1, le=5)] = None,
    min_observed_ratings: Annotated[int, Query(ge=0)] = 0,
    sort: ProductSort = "product_name",
    order: Literal["asc", "desc"] = "asc",
) -> dict:
    rows = data.products
    if q and q.strip():
        search = q.strip()
        rows = rows[
            rows["product_name"].str.contains(search, case=False, regex=False, na=False)
            | rows["brand_name"].str.contains(search, case=False, regex=False, na=False)
        ]
    if category is not None:
        rows = rows[rows["primary_category"] == category]
    if min_catalog_rating is not None:
        rows = rows[rows["catalog_rating"] >= min_catalog_rating]
    if min_observed_ratings:
        rows = rows[rows["observed_rating_count"] >= min_observed_ratings]
    rows = rows.sort_values([sort, "product_id"], ascending=[order == "asc", True])
    return page(rows, limit, offset)


@app.get("/api/reviews/summary")
def reviews_summary(data: Data) -> dict:
    return data.review_summary


@app.get("/api/reviews")
def reviews(
    data: Data,
    limit: Limit = 25,
    offset: Offset = 0,
    product_id: Annotated[str | None, Query(max_length=120)] = None,
    category: Annotated[str | None, Query(max_length=120)] = None,
    rating: Rating = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "date_from must be on or before date_to.")
    rows = data.reviews
    if product_id is not None:
        rows = rows[rows["product_id"] == product_id]
    if category is not None:
        rows = rows[rows["primary_category"] == category]
    if rating is not None:
        rows = rows[rows["rating"] == rating]
    if date_from or date_to:
        days = rows["submission_time"].dt.normalize()
        keep = days.notna()
        if date_from:
            keep &= days >= pd.Timestamp(date_from)
        if date_to:
            keep &= days <= pd.Timestamp(date_to)
        rows = rows[keep]
    return page(rows, limit, offset)
