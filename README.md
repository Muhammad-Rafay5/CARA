# CARA — Cost-Aware Autonomous Research & Report Agent

CARA is an autonomous research agent that takes a question, plans the research, picks the cheapest LLM that can do the job, gathers evidence with tools, verifies it, and returns a **source-grounded report with citations** — all under hard token, call, and time budgets.

It is built on **FastAPI** (backend API), **LangGraph** (agent workflow), and **Streamlit** (UI).

---

## Table of Contents
1. [Key Features](#key-features)
2. [How It Works](#how-it-works)
3. [Architecture & Project Structure](#architecture--project-structure)
4. [Quick Start](#quick-start)
5. [Configuration](#configuration)
6. [API Reference](#api-reference)
7. [Running with Docker](#running-with-docker)
8. [Testing & Quality](#testing--quality)
9. [Scripts](#scripts)
10. [Security](#security)
11. [Deployment](#deployment)
12. [Troubleshooting](#troubleshooting)
13. [License](#license)

---

## Key Features

- **Cost-aware model routing** — each task is classified by complexity and routed to a suitable model; simple tasks never hit expensive models.
- **Provider fallback chain** — Groq → Gemini → OpenRouter → Ollama. Only **one** provider key is needed; Ollama runs fully offline.
- **Hard budget guardrails** — caps on research iterations, model calls, tool calls, tokens, execution time, and provider retries.
- **Tool use** — web search, URL reader, document search, GitHub search, calculator.
- **Evidence-first research** — structured evidence with source-quality scoring, citation tracking, and contradiction detection.
- **Two-stage verification** — evidence is verified before writing; the final report is verified after.
- **Targeted failure recovery** — failures are classified and recovered (retry, fallback, partial report) without restarting the whole workflow; circuit breakers protect flaky providers.
- **Caching** — repeated queries are served from cache and skip the model entirely.
- **Observability** — structured logging (structlog), request IDs, metrics, and tracing hooks.
- **Hardened API** — rate limiting, session tokens, global error handling, SSRF-safe URL reader.

---

## How It Works

The agent is a LangGraph state machine (`app/agent/graph.py`):

```
START → analyze_task ──(cache hit)──────────────────────────────► finalize → END
            │
            ▼
       select_model → check_budget → create_plan
                                         │
                                         ▼
                              ┌─► execute_research ─┐  (loops over plan steps)
                              │          │          │
                              │          ▼          │
                              │   collect_evidence  │
                              │          │
                              │   evaluate_evidence
                              │          │
                              │    verify_research
                              │      │        │
                              │    PASS     FAIL
                              │      │        ▼
                              │      │  classify_failure → recover
                              └──────┼────────────┘  (retry research, or partial report)
                                     ▼
                              generate_report → final_verification → finalize → END
```

| Node | Responsibility |
| :--- | :--- |
| `analyze_task` | Classify complexity, check cache |
| `select_model` | Choose provider/model for the task |
| `check_budget` | Enforce hard stop limits |
| `create_plan` | Build the research plan |
| `execute_research` | Run tools step by step |
| `collect_evidence` / `evaluate_evidence` | Structure evidence, score sources, find contradictions |
| `verify_research` | Stage 1 verification gate |
| `classify_failure` / `recover` | Diagnose and recover without a full restart |
| `generate_report` | Write the cited report |
| `final_verification` | Stage 2 report verification |
| `finalize` | Persist result, record metrics |

---

## Architecture & Project Structure

```
cost-aware-research-agent/
├── app/
│   ├── main.py            # FastAPI app factory & lifespan
│   ├── agent/             # LangGraph graph, nodes/, routing/, state
│   ├── api/               # routes/ (health, research, metrics), middleware/
│   ├── config/            # settings (env-driven), model & tool configs
│   ├── core/              # interfaces, types, constants, exceptions
│   ├── models/            # provider adapters (groq, gemini, openrouter, ollama),
│   │                      #   registry, selector, fallback, health, usage
│   ├── optimization/      # budget manager, cost/usage/token tracking, cache, context optimizer
│   ├── recovery/          # failure classifier, retry policy, circuit breaker, manager
│   ├── research/          # planner, researcher, evidence, citations, contradictions, source quality
│   ├── verification/      # claim checker, source checker, quality score, verifier
│   ├── tools/             # web_search, url_reader, document_search, github_search, calculator
│   ├── services/          # research, report, model, health services
│   ├── schemas/           # Pydantic request/response/state schemas
│   ├── storage/           # database, repositories, sessions
│   ├── observability/     # logging, metrics, tracing
│   └── prompts/, utils/
├── frontend/streamlit_app.py   # Streamlit dashboard
├── scripts/                    # evaluate_agent, ingest, seed_data, security_audit
├── tests/                      # unit/, integration/, evaluation/, fixtures/
├── data/                       # cache/, documents/, evaluations/ (runtime data)
├── Dockerfile, docker-compose.yml
├── pyproject.toml, requirements.txt, requirements-dev.txt, uv.lock
└── .env.example
```

---

## Quick Start

### Prerequisites
- **Python 3.11+** (3.12/3.13 work too)
- [`uv`](https://github.com/astral-sh/uv) (recommended) or `pip`
- At least **one** LLM provider key (or a local [Ollama](https://ollama.com/download) install)

| Provider | Role | Cost | Get a key |
| :--- | :--- | :--- | :--- |
| Groq | Fast, default for simple/standard tasks | Free tier | [console.groq.com/keys](https://console.groq.com/keys) |
| Google Gemini | Large context, complex synthesis | Free tier | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| OpenRouter | Third-tier fallback | Pay-as-you-go / free models | [openrouter.ai/keys](https://openrouter.ai/keys) |
| Ollama | Offline local inference | Free | [ollama.com/download](https://ollama.com/download) |

### Install & run

```bash
git clone <your-repo-url>
cd cost-aware-research-agent

# 1. Configure
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
# edit .env and add at least one API key

# 2. Install
uv sync                       # or: pip install -e .

# 3. Start the backend (http://localhost:8000)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. In a second terminal, start the UI (http://localhost:8501)
uv run streamlit run frontend/streamlit_app.py --server.port 8501
```

Interactive API docs are served at `http://localhost:8000/docs`.

---

## Configuration

All settings are environment variables (loaded from `.env`). See `.env.example`.

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `development` | Runtime environment |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | Backend bind address |
| `SECRET_KEY` | — | **Change in production** |
| `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY` | — | Provider keys (need at least one) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama endpoint |
| `MAX_RESEARCH_ITERATIONS` | `3` | Max research/recovery loops |
| `MAX_MODEL_CALLS` | `10` | Max LLM calls per request |
| `MAX_TOOL_CALLS` | `20` | Max tool calls per request |
| `MAX_TOKENS` | `15000` | Token budget per request |
| `MAX_EXECUTION_TIME` | `120` | Seconds before hard stop |
| `MAX_PROVIDER_RETRIES` | `2` | Retries per provider before fallback |
| `ALLOWED_DOCUMENT_DIR` | `data/documents` | Sandbox for document search |
| `URL_READER_TIMEOUT` / `URL_READER_MAX_BYTES` | `15` / `1048576` | URL reader limits |
| `DATABASE_URL` | `sqlite:///./data/cara.db` | Storage |
| `REDIS_URL` | `redis://localhost:6379/0` | Cache (optional) |
| `RATE_LIMIT_MAX_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` | `10` / `60` | Per-client rate limit |
| `SESSION_TOKEN_TTL_HOURS` | `24` | Session lifetime |

> Never commit `.env`. It is git-ignored; only `.env.example` is tracked.

---

## API Reference

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Liveness probe |
| `GET` | `/ready` | Readiness probe (provider configuration status) |
| `POST` | `/api/v1/research` | Run a research task and return the verified report |
| `GET` | `/api/v1/research/{request_id}` | Fetch a previous result (404 if unknown) |
| `GET` | `/api/v1/metrics` | Token usage, cost, and request counters |

Responses use a common envelope: `{ "success", "data", "message", "request_id" }`.

Example (see `/docs` for the exact `ResearchRequest` schema):

```bash
curl -X POST http://localhost:8000/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{"query": "Compare LangGraph and CrewAI for production agents"}'
```

---

## Running with Docker

```bash
cp .env.example .env     # add your keys
docker compose up --build
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:8501`

The image is multi-stage, runs as a non-root user, has built-in health checks, and `docker-compose.yml` sets CPU/memory limits. Data persists in the `cara-data` volume.

---

## Testing & Quality

```bash
pip install -r requirements-dev.txt     # or: uv sync

pytest                         # all tests
pytest tests/unit              # fast unit tests
pytest tests/integration       # graph, fallback, tools, verification loop
pytest tests/evaluation        # reliability, cost efficiency, research quality

ruff check .                   # lint
mypy app                       # type check (strict)
```

---

## Scripts

| Script | Purpose |
| :--- | :--- |
| `scripts/evaluate_agent.py` | Evaluate agent quality/cost |
| `scripts/ingest.py` | Ingest documents into `data/documents` |
| `scripts/seed_data.py` | Seed sample data |
| `scripts/security_audit.py` | Check prompt-injection handling, SSRF filtering, log secret-scrubbing, no `eval`/`exec` |

Run with e.g. `python scripts/security_audit.py`.

---

## Security

- **SSRF protection** in the URL reader (blocks internal and cloud-metadata addresses) with timeouts and size caps.
- **Prompt-injection hygiene** — fetched content is treated as untrusted data.
- **Secret scrubbing** in structured logs.
- **No arbitrary code execution** (the calculator avoids `eval`/`exec`).
- **Document sandbox** — document search is restricted to `ALLOWED_DOCUMENT_DIR`.
- **Rate limiting & session tokens** on the API; non-root container.

---

## Deployment

CARA runs anywhere Docker does: Railway/Render, AWS (ECS Fargate / App Runner), Azure, or a VPS (DigitalOcean/Hetzner) with `docker compose`. Set provider keys and a strong `SECRET_KEY` as secrets/environment variables, set `ENVIRONMENT=production`, and point health checks at `/health` and `/ready`.

---

## Troubleshooting

| Symptom | Fix |
| :--- | :--- |
| `/ready` reports `degraded` | No provider key set — add at least one to `.env` |
| Requests stop early | A budget limit was hit — raise `MAX_*` values |
| `429` responses | Rate limit — raise `RATE_LIMIT_MAX_REQUESTS` |
| UI can't reach backend | Check `CARA_BACKEND_URL` (Docker uses `http://backend:8000`) |
| Ollama not used | Make sure `ollama serve` is running at `OLLAMA_BASE_URL` |

---

## License

See [LICENSE](LICENSE).
