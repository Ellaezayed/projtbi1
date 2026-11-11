import csv
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from dataset import PRODUCT_TYPES, REVIEW_TYPES, DatasetError, SnapshotCache, source_files
from metrics import page


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class SnapshotTests(unittest.TestCase):
    def test_cleanup_metrics_pagination_and_cache_refresh(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            catalog, first, second, *rest = source_files(root)
            product = {"product_id": "P1", "primary_category": "Skincare", "price_usd": 20}
            no_reviews = {"product_id": "P2", "primary_category": "Makeup", "price_usd": 30}
            write_csv(catalog, PRODUCT_TYPES, [product, no_reviews])
            review = {"product_id": "P1", "author_id": "0001", "rating": 5,
                      "is_recommended": 1, "submission_time": "2023-01-02", "review_text": " Test "}
            invalid = {**review, "rating": 9, "is_recommended": 2,
                       "submission_time": "invalid", "review_text": " "}
            write_csv(first, ["Unnamed: 0", *REVIEW_TYPES], [
                {"Unnamed: 0": 1, **review}, {"Unnamed: 0": 2, **review}, invalid,
            ])
            write_csv(second, REVIEW_TYPES, [review, {**review, "product_id": "unknown"}])
            for file in rest:
                write_csv(file, REVIEW_TYPES, [])
            cache = SnapshotCache()
            snapshot = cache.get(root)
            self.assertIs(snapshot, cache.get(root))
            self.assertEqual(snapshot.overview["observed_review_count"], 2)
            self.assertEqual(snapshot.overview["observed_average_rating"], 5)
            self.assertEqual(snapshot.overview["average_listed_price_usd"], 25)
            self.assertEqual(snapshot.overview["quality"], {
                "source_review_count": 5, "duplicate_review_count": 2,
                "unmatched_review_count": 1, "invalid_rating_count": 1,
                "invalid_date_count": 1, "invalid_recommendation_count": 1,
            })
            self.assertEqual(snapshot.review_summary["recommendation_response_count"], 1)
            self.assertEqual(snapshot.review_summary["recommendation_rate"], 1)
            self.assertEqual(snapshot.review_summary["text_review_count"], 1)
            self.assertEqual(snapshot.review_summary["monthly_trend"], [
                {"month": "2023-01", "review_count": 1},
            ])
            missing = page(snapshot.reviews, 1, 1)["items"][0]
            self.assertIsNone(missing["rating"])
            self.assertIsNone(missing["submission_time"])
            self.assertNotIn("author_id", missing)
            uncovered = snapshot.products.loc[snapshot.products["product_id"] == "P2"].iloc[0]
            self.assertEqual(uncovered["observed_review_count"], 0)
            write_csv(second, REVIEW_TYPES, [{**review, "product_id": "P2"}])
            # Force a different fingerprint even on coarse timestamp filesystems.
            stat = second.stat()
            os.utime(second, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
            refreshed = cache.get(root)
            self.assertIsNot(refreshed, snapshot)
            self.assertEqual(refreshed.overview["products_with_observed_reviews"], 2)
            catalog.unlink()
            with self.assertRaises(DatasetError):
                cache.get(root)


if __name__ == "__main__":
    unittest.main()
