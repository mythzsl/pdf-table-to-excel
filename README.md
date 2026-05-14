# PDF Table to Excel MVP

English-first MVP for extracting tables from text-based PDFs and exporting them to Excel or CSV.

## What is included

- No-build static frontend in `site/`
- Astro static marketing/tool site in `frontend/`
- FastAPI conversion service in `backend/`
- No accounts, no database, no persistent uploads
- SEO pages, guide articles, sitemap, robots, FAQ and SoftwareApplication schema
- In-memory rate limit: 3 conversions per IP per hour
- Upload limits: 10 MB PDF, 30 pages

## Local setup

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Static frontend, no build required

```bash
cd site
python -m http.server 4321
```

Open `http://localhost:4321/pdf-table-to-excel/`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `PUBLIC_API_BASE_URL=http://localhost:8000` for local frontend testing.

## Deployment

- Recommended low-friction v1: deploy `site/` to Cloudflare Pages with no build command and output directory `/`.
- Optional: deploy `frontend/` to Cloudflare Pages after installing Node dependencies and running the Astro build.
- Deploy `backend/` to Railway using the Dockerfile.
- Set CORS allowed origins in the backend with `ALLOWED_ORIGINS=https://yourdomain.com`.
- In `site/pdf-table-to-excel/index.html`, replace `data-api-base="http://localhost:8000"` with `data-api-base="https://api.yourdomain.com"` before production deploy.
- If using Astro, set `PUBLIC_API_BASE_URL=https://api.yourdomain.com` in Cloudflare Pages.

## Cost guardrails

The MVP intentionally avoids OCR at launch. OCR table extraction can be added later behind quotas or paid usage because per-page API pricing scales quickly.
