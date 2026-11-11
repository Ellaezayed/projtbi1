"""Load a consistent snapshot of the local Sephora CSVs."""
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

import pandas as pd

REVIEW_FILES = (
    "reviews_0-250.csv", "reviews_250-500.csv", "reviews_500-750.csv",
    "reviews_750-1250.csv", "reviews_1250-end.csv",
)
PRODUCT_TYPES = {
    "product_id": "string", "product_name": "string", "brand_name": "string",
    "primary_category": "string", "secondary_category": "string",
    "tertiary_category": "string", "price_usd": "Float64", "sale_price_usd": "Float64",
    "rating": "Float64", "reviews": "Int64", "loves_count": "Int64",
}
REVIEW_TYPES = {
    "author_id": "string", "product_id": "string", "rating": "Int8",
    "is_recommended": "Int8", "helpfulness": "Float64",
    "total_feedback_count": "Int64", "total_neg_feedback_count": "Int64",
    "total_pos_feedback_count": "Int64", "submission_time": "string",
    "review_text": "string", "review_title": "string", "skin_tone": "string",
    "eye_color": "string", "skin_type": "string", "hair_color": "string",
    "product_name": "string", "brand_name": "string", "price_usd": "Float64",
}
REVIEW_FIELDS = (
    "product_id", "rating", "is_recommended", "submission_time",
    "review_title", "review_text", "total_feedback_count",
)
CHUNK_SIZE = 40_000


class DatasetError(Exception):
    """The configured dataset cannot provide a consistent snapshot."""


@dataclass(frozen=True)
class Dataset:
    products: pd.DataFrame
    reviews: pd.DataFrame
    source_review_count: int
    duplicate_count: int
    unmatched_count: int
    invalid_rating_count: int
    invalid_date_count: int
    invalid_recommendation_count: int


def source_files(directory: Path) -> tuple[Path, ...]:
    return tuple(directory / name for name in ("product_info.csv", *REVIEW_FILES))


def fingerprint(files: tuple[Path, ...]) -> tuple:
    return tuple((path, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
                 for path in files for stat in (path.stat(),))


def load_dataset(files: tuple[Path, ...]) -> Dataset:
    products = pd.read_csv(files[0], usecols=list(PRODUCT_TYPES), dtype=PRODUCT_TYPES)
    products["product_id"] = products["product_id"].str.strip()
    if products["product_id"].isna().any() or products["product_id"].eq("").any():
        raise DatasetError("The product catalog contains a missing product ID.")
    if products["product_id"].duplicated().any():
        raise DatasetError("The product catalog contains duplicate product IDs.")
    products = products.rename(columns={"rating": "catalog_rating", "reviews": "catalog_review_count"})
    products["catalog_rating"] = products["catalog_rating"].where(products["catalog_rating"].between(1, 5))
    for column in ("price_usd", "sale_price_usd"):
        products[column] = products[column].where(products[column].ge(0) & products[column].lt(float("inf")))

    seen: set[int] = set()
    batches = []
    raw = unmatched = 0
    for path in files[1:]:
        for chunk in pd.read_csv(path, usecols=list(REVIEW_TYPES), dtype=REVIEW_TYPES, chunksize=CHUNK_SIZE):
            raw += len(chunk)
            # Compare every business column. The export index varies by shard.
            chunk = chunk.drop_duplicates()
            hashes = pd.util.hash_pandas_object(chunk, index=False)
            keep = ~hashes.isin(seen)
            seen.update(hashes[keep])
            chunk = chunk.loc[keep, list(REVIEW_FIELDS)].copy()

            chunk["product_id"] = chunk["product_id"].str.strip()
            matched = chunk["product_id"].isin(products["product_id"])
            unmatched += int((~matched).sum())
            batches.append(chunk.loc[matched])

    # Include repetitions removed inside each chunk in the duplicate count.
    duplicates = raw - unmatched - sum(map(len, batches))
    reviews = pd.concat(batches, ignore_index=True) if batches else pd.DataFrame(columns=REVIEW_FIELDS)
    reviews = reviews.astype({field: REVIEW_TYPES[field] for field in REVIEW_FIELDS})
    rating = reviews["rating"]
    recommendation = reviews["is_recommended"]
    valid_rating = rating.between(1, 5).fillna(False)
    valid_recommendation = recommendation.isin([0, 1])
    invalid_rating = int((rating.notna() & ~valid_rating).sum())
    invalid_recommendation = int((recommendation.notna() & ~valid_recommendation).sum())
    reviews["rating"] = rating.where(valid_rating)
    reviews["is_recommended"] = recommendation.where(valid_recommendation)
    dates = pd.to_datetime(reviews["submission_time"], format="ISO8601", errors="coerce", utc=True)
    invalid_date = int((reviews["submission_time"].notna() & dates.isna()).sum())
    reviews["submission_time"] = dates.dt.tz_convert(None)
    for field in ("review_title", "review_text"):
        reviews[field] = reviews[field].str.strip().replace("", pd.NA)

    reviews = reviews.merge(
        products[["product_id", "primary_category"]], on="product_id", how="left",
        validate="many_to_one", sort=False,
    )
    for field in ("product_id", "primary_category"):
        reviews[field] = reviews[field].astype("category")
    reviews = reviews.sort_values("submission_time", ascending=False, kind="stable", ignore_index=True)
    return Dataset(products, reviews, raw, duplicates, unmatched, invalid_rating, invalid_date,
                   invalid_recommendation)


class SnapshotCache:
    """Reuse one snapshot per server process until a source file changes."""

    def __init__(self):
        self._lock = Lock()
        self._key: tuple | None = None
        self._snapshot = None

    def get(self, directory: Path):
        from metrics import build_snapshot

        files = source_files(directory)
        with self._lock:
            try:
                key = fingerprint(files)
                if self._snapshot is not None and self._key == key:
                    return self._snapshot
                # Release the old cache before loading the new source data.
                self._snapshot = None
                candidate = build_snapshot(load_dataset(files))
                if key != fingerprint(files):
                    raise DatasetError("CSV files changed while loading. Retry the request.")
            except FileNotFoundError as exc:
                raise DatasetError("One or more expected Sephora CSV files are missing.") from exc
            except (OSError, ValueError, pd.errors.ParserError) as exc:
                raise DatasetError("Unable to read the expected Sephora CSV schema.") from exc
            self._key, self._snapshot = key, candidate
            return candidate
