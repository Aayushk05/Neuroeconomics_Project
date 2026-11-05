# Happiness-adjusted salary — Arm A

Discrete choice experiment on how tech workers and students trade salary against non-pay job features. Neuroeconomics course project, Prajna Penmetsa and Aayush Khatanhar; presentation 10 November 2026.

| Folder | What's in it |
| --- | --- |
| `survey/` | Survey wording (`survey_copy.md`), the frozen 24-pair design and the two attention-check pairs |
| `app/` | The survey web app: Flask + SQLite back end, plain HTML/JS front end |
| `analysis/` | Estimation pipeline for the exported data, and a simulator that checks it recovers known preferences |

## Setup

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
```

## Run the survey locally

```bash
.venv/bin/python app/server.py
```

Open http://localhost:5050, or http://localhost:5050/?pilot=1 for pilot runs (exported separately). Before the pilot, fill in the placeholders in `public/static/config.js`; unfilled ones show up highlighted.

For local development, responses are stored only on final submit in
`app/data/survey.sqlite3` (git-ignored). In production, set `DATABASE_URL` and
responses are stored in Neon Postgres. Export local data as the CSVs the pipeline reads:

```bash
.venv/bin/python app/export.py          # -> exports/choices_long.csv, participants.csv, *_pilot.csv
```

## Analyse

```bash
.venv/bin/python analysis/pipeline.py exports/choices_long.csv --bootstrap 499
.venv/bin/python analysis/simulate.py --reps 200     # bias, CI coverage and power on simulated data
```

## Test

```bash
.venv/bin/python -m pytest app analysis
```

## Deploy to Vercel with Neon

1. Create a Neon project and connect it to the Vercel project. Add the connection
   string to the Vercel environment as `DATABASE_URL` for Production, Preview, and
   Development. The app creates its tables automatically on first request.
2. Add a long random `EXPORT_TOKEN` environment variable. It protects the
   `/api/export.zip` download endpoint; do not put it in `config.js` or commit it.
3. Import the Git repository in Vercel. No build or output-directory setting is
   needed. Vercel detects the Flask application in `app/server.py`; `public/` is
   served through Vercel's CDN, and `vercel.json` bundles the two survey-design CSVs.
4. Before collecting real responses, use a Preview deployment to submit both a
   pilot and a standard response, then download and inspect the protected export.

`DATABASE_URL` is mandatory on Vercel. The SQLite fallback is for local development
and tests only; it must never be used to collect production responses.

To download production data, send an `Authorization: Bearer <EXPORT_TOKEN>` header
to `https://your-domain/api/export.zip`.
