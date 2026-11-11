# Sephora Business Insight

Parts 1 and 2 provide a dataset audit, a branded Next.js starter, and a FastAPI analytics API. See [DATASET.md](DATASET.md) for verified counts, the full schema, join checks, and BI definitions.

The application architecture is **Next.js → FastAPI → Pandas → local CSV files**. The API reads review shards in chunks, removes duplicate business records, and joins reviews to the catalog by product ID. It caches one processed snapshot in memory per server process and refreshes it when a source file changes. The first analytics request loads the snapshot. The frontend displays the starter page until the dashboard is built in Part 3.

## Local setup (Windows PowerShell)

Install Node.js 20.9+ (Node 22 recommended), Python 3.11+, and Git. Run from the project directory.

**Backend terminal**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
notepad backend/.env
```

Set `SEPHORA_DATASET_DIR` to your local dataset directory and save the file. If the path contains spaces, quote it; forward slashes work on Windows. Leave `AI_API_KEY` blank in Part 1. Restart the backend after changing the file.

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

**Frontend terminal**

```powershell
cd frontend
npm install
npm run dev -- --hostname localhost
```

When a lockfile is present, use `npm ci` for repeat installs.

## Verify

- Open [the starter page](http://localhost:3000). It should display “Sephora Business Insight.”
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
| `/api/reviews` | Paginated reviews with product, category, star rating, and inclusive date filters |

List responses contain `total`, `limit`, `offset`, and `items`. The API returns missing values as JSON `null`. Observed average ratings count each valid review once. Recommendation rates divide positive responses by known responses and range from zero to one. Review listing responses omit reviewer IDs. Missing or incompatible source files produce HTTP 503 on analytics routes.

## First GitHub commit

Create an empty GitHub repository. From the project directory, review the files staged before committing. Keep the original CSVs outside the repository.

```powershell
git add .gitignore README.md DATASET.md backend frontend
git diff --cached --name-only
git commit -m "Part 1: Initialize Sephora Business Insight"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```
