# Dataset audit

Pandas read the original catalog and all five review shards in 40,000-row chunks. Source files were left unchanged. Counts below are before deduplication. Duplicate counts track repeated rows across chunks and files using Pandas row fingerprints, excluding the exported index.

| File | Rows | Raw columns | Duplicate rows |
| --- | ---: | ---: | ---: |
| `product_info.csv` | 8,494 | 27 | 0 |
| `reviews_0-250.csv` | 602,130 | 19 | 108 |
| `reviews_1250-end.csv` | 49,977 | 19 | 0 |
| `reviews_250-500.csv` | 206,725 | 19 | 42 |
| `reviews_500-750.csv` | 116,262 | 19 | 69 |
| `reviews_750-1250.csv` | 119,317 | 19 | 5 |

The 8,494 catalog IDs are unique and non-null. All 1,094,411 review rows match a catalog ID. Join reviews to products on `product_id` (many to one), keeping the catalog as the source for categories and listed prices. Do not join on names or treat author IDs as review IDs. Reviews span August 28, 2008 to March 21, 2023, with no missing or unparseable submission dates. No populated ratings in either table fall outside 1–5. Removing 224 duplicate rows would leave 1,094,187 reviews.

## Catalog schema and missing values

| Column | Parsed type | Missing |
| --- | --- | ---: |
| `product_id` | str | 0 |
| `product_name` | str | 0 |
| `brand_id` | int64 | 0 |
| `brand_name` | str | 0 |
| `loves_count` | int64 | 0 |
| `rating` | float64 | 278 |
| `reviews` | float64 | 278 |
| `size` | str | 1,631 |
| `variation_type` | str | 1,444 |
| `variation_value` | str | 1,598 |
| `variation_desc` | str | 7,244 |
| `ingredients` | str | 945 |
| `price_usd` | float64 | 0 |
| `value_price_usd` | float64 | 8,043 |
| `sale_price_usd` | float64 | 8,224 |
| `limited_edition` | int64 | 0 |
| `new` | int64 | 0 |
| `online_only` | int64 | 0 |
| `out_of_stock` | int64 | 0 |
| `sephora_exclusive` | int64 | 0 |
| `highlights` | str | 2,207 |
| `primary_category` | str | 0 |
| `secondary_category` | str | 8 |
| `tertiary_category` | str | 990 |
| `child_count` | int64 | 0 |
| `child_max_price` | float64 | 5,740 |
| `child_min_price` | float64 | 5,740 |

`rating` and `reviews` are catalog summary fields; `loves_count` is a catalog popularity indicator. Prices are listed USD values. Category columns form a hierarchy. Variant fields and child counts describe catalog options; snapshot flags describe listings.

## Review schema and missing values

All shards have the same business columns and inferred types. The nineteenth raw column, `Unnamed: 0`, is an exported row index and is excluded below.

| Column | Parsed type | 0-250 | 1250-end | 250-500 | 500-750 | 750-1250 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `author_id` | string | 0 | 0 | 0 | 0 | 0 |
| `rating` | int64 | 0 | 0 | 0 | 0 | 0 |
| `is_recommended` | float64 | 117,486 | 3,817 | 25,986 | 11,803 | 8,896 |
| `helpfulness` | float64 | 331,832 | 13,455 | 107,874 | 56,424 | 52,007 |
| `total_feedback_count` | int64 | 0 | 0 | 0 | 0 | 0 |
| `total_neg_feedback_count` | int64 | 0 | 0 | 0 | 0 | 0 |
| `total_pos_feedback_count` | int64 | 0 | 0 | 0 | 0 | 0 |
| `submission_time` | str | 0 | 0 | 0 | 0 | 0 |
| `review_text` | str | 999 | 59 | 172 | 125 | 89 |
| `review_title` | str | 167,011 | 14,378 | 59,728 | 33,981 | 35,556 |
| `skin_tone` | str | 106,056 | 7,201 | 26,799 | 15,235 | 15,248 |
| `eye_color` | str | 138,488 | 6,260 | 33,774 | 16,443 | 14,663 |
| `skin_type` | str | 74,683 | 3,631 | 16,749 | 8,889 | 7,605 |
| `hair_color` | str | 141,081 | 8,851 | 36,544 | 19,735 | 20,557 |
| `product_id` | string | 0 | 0 | 0 | 0 | 0 |
| `product_name` | str | 0 | 0 | 0 | 0 | 0 |
| `brand_name` | str | 0 | 0 | 0 | 0 | 0 |
| `price_usd` | float64 | 0 | 0 | 0 | 0 | 0 |

`author_id` identifies a source reviewer; it is stored as a string. `rating` is the submitted star score; `is_recommended` records the recommendation response. Feedback counts and helpfulness describe review votes. Text and title are potential sentiment inputs. Appearance and skin fields are optional reviewer attributes. Review-side product name, brand and USD price are supplied with the review; the data does not establish them as transaction facts.

## BI metrics and limits

Only 2,351 of the 8,494 catalog products (27.7%) appear in the review shards. A product absent from the shards has no observed reviews in this archive; its catalog review count may still be populated. The review-side product names, brands, and prices agree with the catalog on every review row. Nonmissing recommendation values are all 0 or 1.

There are 167,988 missing recommendation responses and 1,444 missing review bodies before deduplication. The catalog is missing rating and review count for 278 products, and sale price for 8,224.

- Catalog: product and brand counts, category mix, listed price distributions, catalog loves, and ranked products with minimum rating counts.
- Reviews: observed review counts, rating distributions and averages, recommendation share among known responses, monthly review trends, review coverage by product, and product/category comparisons.
- Report catalog rating/count separately from statistics computed over review rows. The archive is historical and coverage can vary. Reviews and loves do not establish demand, units sold, revenue, margin, conversion, purchase prices, inventory history, or market share.
- A missing recommendation is unknown; a missing sale price is not zero. Exclude missing values from applicable denominators and report coverage. Review ratings are not AI sentiment. Only actually classified text can contribute to future sentiment percentages.

## Recommended next step

Read the five shards with explicit types, drop the export index, retain source provenance separately, parse dates, deduplicate on business fields, and validate a many-to-one merge with a unique catalog key. Preserve products with no observed reviews in catalog metrics. Define review-weighted and product-weighted averages separately. Cache normalized local data keyed by the source file fingerprints and project only needed columns for aggregation. Page review results and keep reviewer IDs and raw text out of committed artifacts.
