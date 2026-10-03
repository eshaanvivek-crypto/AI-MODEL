# AI-MODEL Research Assistant MVP

Runnable FastAPI MVP that accepts a research question, plans web searches, retrieves sources, extracts evidence, drafts a cited report, and validates citations.

## Features

- Explicit workflow stages:
  1. Question intake
  2. Query planning
  3. Search
  4. Source retrieval
  5. Text extraction
  6. Evidence/claim extraction
  7. Report generation
  8. Citation validation
- Configurable providers via environment variables
- Guardrails for URL safety, timeouts, result limits, and prompt-injection resistance
- Backend API (`/health`, `/api/research`) with schemas
- Simple web UI at `/`
- Tests with mocks (no live API keys or internet required)

## Setup

1. Copy env file:

```bash
cp .env.example .env
```

2. (Optional) Set provider keys in `.env`:

- `OPENAI_API_KEY` for `LLM_PROVIDER=openai`
- `SERPAPI_API_KEY` for `SEARCH_PROVIDER=serpapi`

If keys are missing, app returns a setup warning and uses limited behavior where possible.

3. Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. Run app:

```bash
uvicorn app.main:app --reload
```

Open http://localhost:8000

## API

### `GET /health`
Returns basic health status.

### `POST /api/research`
Request:

```json
{
  "question": "Compare sodium-ion vs lithium-ion battery readiness",
  "max_queries": 3,
  "max_sources": 5
}
```

Response includes:
- `report`
- `sources` with title, URL, publisher/domain, retrieval date
- `stages`
- `warnings`
- `setup_error` if configuration is incomplete

## Tests

```bash
pytest
```

## Docker

```bash
docker compose up --build
```

## Security and guardrails

- Treats webpage content as untrusted data
- Does not execute webpage instructions
- Performs no external write actions
- URL safety checks block localhost/private networks
- Enforces timeouts and source/result limits
- Labels uncertainty when evidence is weak
