# Local Business Lead Agent (MVP)

A lead-research + human-approved cold-outreach tool: find local businesses without a decent website, score them as prospects, draft a factual outreach email, and send only after approval.

Pipeline: Google Places search -> website quality check -> AI lead scoring -> AI email draft -> your approval -> send -> track replies.

## Install

pip install -r requirements.txt
cp .env.example .env

Edit .env with your GOOGLE_PLACES_API_KEY, ANTHROPIC_API_KEY, and SMTP settings.

## Run

uvicorn app.main:app --host 0.0.0.0 --port 8000

Open the app in your browser to use the dashboard.
