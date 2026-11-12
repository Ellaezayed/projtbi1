# Sephora Business Insight

Sephora Business Insight is a dashboard for analyzing the Sephora product catalog and customer reviews. The executive overview shows catalog coverage, star ratings, recommendation rates, review activity, and the products with the most observed reviews. See [DATASET.md](DATASET.md) for the dataset schema, join checks, and metric definitions.

The application architecture is **Next.js → FastAPI → Pandas → local CSV files**. The API reads review shards in chunks, removes duplicate business records, and joins reviews to the catalog by product ID. It caches one processed snapshot in memory per server process and refreshes it when a source file changes. The first analytics request loads the snapshot.

## Local setup (Windows PowerShell)

Install Node.js 20.9+ (Node 22 recommended), Python 3.12, and Git. Run from the project directory. Python runtime dependencies are version-pinned, including transitive dependencies, and the frontend uses its npm lockfile.

**Backend terminal**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
notepad backend/.env
```

Set `SEPHORA_DATASET_DIR` to the directory containing `product_info.csv` and the five review files listed in [DATASET.md](DATASET.md). Quote paths with spaces. Forward slashes work on Windows. The dashboard requires no AI API key. Restart the backend after editing its environment file.

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

**Frontend terminal**

```powershell
cd frontend
npm ci
npm run dev -- --hostname localhost
```

If FastAPI runs on a different origin, copy `frontend/.env.example` to `frontend/.env.local` and set `SEPHORA_API_URL` before starting Next.js.

## Verify

- Open [the executive overview](http://localhost:3000) and check that the KPI cards and charts load.
- Run `Invoke-RestMethod http://127.0.0.1:8000/health`. Expect `status: ok` and `dataset_directory_exists: True` with a configured directory.
- Run `Invoke-RestMethod http://127.0.0.1:8000/api/overview` and compare counts with the audit. The supplied archive should yield 8,494 products and 1,094,187 observed reviews after deduplication.
- From the project root, run `.\.venv\Scripts\python.exe -m unittest discover -s backend -v` to test the cleaning and cache refresh logic.
- In `frontend`, run `npm run typecheck` and `npm run build` after stopping the dev server.

Framework references: [Next.js installation](https://nextjs.org/docs/app/getting-started/installation), [FastAPI with Uvicorn](https://fastapi.tiangolo.com/deployment/manually/).

## Analytics API

Open [FastAPI's interactive API reference](http://127.0.0.1:8000/docs) to run requests.

| GET endpoint | Response |
| --- | --- |
| `/api/overview` | Catalog coverage, observed review metrics, price summaries, and data quality counts |
| `/api/categories` | Product and observed review counts, listed price, and review-weighted rating by primary category |
| `/api/products` | Paginated products with search, category, rating thresholds, and sorting |
| `/api/reviews/summary` | Star distribution, recommendation response and rate, text coverage, and monthly review counts |
| `/api/reviews` | Authorized raw review access with pagination and product, category, rating, and date filters |

The dashboard uses the public overview, categories, products, and review summary routes. Raw review access is disabled until the server has a `RAW_REVIEW_API_TOKEN`. Generate a random value, for example with `python -c "import secrets; print(secrets.token_urlsafe(32))"`, and store it in the backend environment. Send it in the HTTPS `Authorization: Bearer …` header from authorized clients only. An optional separate `LIMITED_API_TOKEN` is recognized as a credential without raw review permission. Keep both tokens out of frontend settings, request URLs, and logs. A missing or invalid bearer token returns 401 when raw access is enabled. An authenticated limited token returns 403.

Set `FRONTEND_ORIGIN` to a comma-separated list of exact HTTP(S) origins. The default allows the local dashboard. The API limits analytics to 120 requests per client and 600 total per process per 60-second window, with lower limits of 30 per client and 120 total for raw reviews. It returns 429 with `Retry-After` when a quota is exhausted and 503 when all 16 analytics request slots are busy. Before a public deployment, enforce shared quotas at the gateway for multiple workers, trust forwarding headers only from your proxy, use TLS, and disable or redact access logs that could retain sensitive URLs. Use `--no-proxy-headers` when running Uvicorn directly without a trusted proxy.

List responses contain `total`, `limit`, `offset`, and `items`. The API returns missing values as JSON `null`. Observed average ratings count each valid review once. Recommendation rates divide positive responses by known responses and range from zero to one. Review listing responses omit reviewer IDs. Missing or incompatible source files produce HTTP 503 on analytics routes.

## Public repository safety

Keep credentials in backend environment variables. The frontend API origin is a server-side setting and carries no credentials. Use the checked-in `.env.example` files to see the available settings and set real values only in local ignored environment files.

After cloning, enable the repository's pre-commit and pre-push checks and run an initial scan from the project root:

```powershell
git config core.hooksPath .githooks
python scripts/check_public_repo.py
```

The hooks require Python on PATH. Set `SEPHORA_PYTHON` to the Python executable if needed. The checks inspect the Git index, reachable commit history, and any additional commit tips being pushed. They block private files and common credential patterns without printing the matched values. Review the staged diff alongside the scan, since pattern matching cannot identify every secret. Push only after the scan passes and the repository owner approves.

In the restricted Windows workspace, Git for Windows could not start its hook shell (exit code 66). If this happens, run `python scripts/check_public_repo.py` directly after staging, then run it again against the final commit before pushing the current branch. The direct command checks the staged files and all locally reachable commits, including the current branch tip.

Keep original datasets and processed caches local. Include CSVs in the public repository only after verifying that the dataset license permits redistribution and obtaining approval. A dataset being available for download does not establish redistribution rights.

Any future AI requests must go through FastAPI. Before exposing AI routes publicly, require authentication, per-user rate limits, request size and concurrency limits, and enforceable usage or spending caps.

The GitHub Actions workflow scans tracked files and history, audits the pinned Python and npm dependency sets, runs the API tests, and builds the dashboard. It uses read-only permissions and needs no credentials or CSVs.
