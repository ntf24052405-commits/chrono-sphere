# Chrono-Sphere · CA Deadline Radar (live)

Tracks Indian tax, GST, company-law and regulator deadlines (and every extension) from public news,
ranked by CA-firm priority. Works on any phone or laptop in India — just open the site.

## Publish (one command)
Windows: `powershell -ExecutionPolicy Bypass -File setup.ps1`
Mac / Linux / Git Bash: `bash setup.sh`

It creates the GitHub repo, turns on GitHub Pages and starts the sync. Your link: `https://<you>.github.io/chrono-sphere/`

## How the live sync works
- `.github/workflows/sync.yml` runs about every 15 minutes (GitHub may delay it a few minutes), free on public repos.
- `scripts/fetch_feeds.py` pulls Google News India searches + TaxGuru + your original CA Live Update page into `data/feed.json`.
- The site reads `data/feed.json` and re-checks it every 5 minutes while the page is open.
- Every deadline has a **🔎 Reference** button: exact news sources, the official site to confirm on, and a live news search.

Add or remove news topics in the `TOPICS` list in `scripts/fetch_feeds.py`.
Dates are read from headlines automatically — always confirm on the official notification.
