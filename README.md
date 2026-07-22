# OVAX Singapore Company Law AI — MVP 0.1

A small, runnable retrieval-based legal information assistant for testing the OVAX concept before adding automated legal-data collection.

## What this first version does

- Runs as a FastAPI web application.
- Includes a simple browser chat interface.
- Searches a small curated dataset about Singapore company law.
- Returns official source links from ACRA and Singapore Statutes Online.
- Uses OpenAI only when `OPENAI_API_KEY` is configured.
- Continues to work in deterministic local-retrieval mode without an API key.
- Includes health checks and automated tests.

## Important limitation

The included records are **curated summaries for technical testing**, not a complete legal database. Do not treat them as authoritative legal advice or as a substitute for checking the current legislation.

Automated crawling is intentionally not included in version 0.1. The ingestion and retrieval pipeline should be validated before collecting a larger volume of documents.

## Run with Docker

```bash

cp .env.example .env
docker compose up --build
```

Open:

- App: http://localhost:8000
- API documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

## Run without Docker

Python 3.11 

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

## Optional OpenAI mode

Edit `.env`:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-mini
```

Never commit `.env` to GitHub.

When the key is absent or an external request fails, the API automatically returns a local retrieval result.

## Run tests

```bash
pytest -q
```

## API example

```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Does a Singapore company need a resident director?","top_k":3}'
```

## GitHub upload commands

Create an empty GitHub repository named `ovax-singapore-legal-ai`, then run:

```bash
git init
git add .
git commit -m "Initial runnable Singapore company law AI MVP"
git branch -M main
git push -u origin main
```

## Recommended next milestone

Version 0.2 (waiting)

1. Add an administrator-approved source registry.
2. Download only explicitly approved official pages.
3. Save retrieval date, document identifier, effective date and amendment status.
4. Parse legislation by Part, Division, section and subsection.
5. Store content hashes so changes can be detected.
6. Require human review before new material becomes searchable.
7. Build a fixed evaluation set of at least 50 legal questions.

Do not add broad autonomous crawling until source rights, site rules, data quality and update validation have been reviewed.
