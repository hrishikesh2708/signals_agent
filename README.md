# Signals

LangGraph-based AI agent for [Signals](https://datahash.com) — orchestrating setup, configuration, and data workflows with deterministic control flow and LLM-assisted steps.

Monorepo layout: **`server/`** (Python / LangGraph) and **`client/`** (Next.js + CopilotKit scaffold).

## Overview

This repository hosts a focused LangGraph agent for Signals. It is intended to complement the broader [signals_copilot](../signals_copilot) stack with a lean, graph-first implementation that can be embedded in services, run standalone, or integrated via API.

**Stack**

| Component | Technology |
|-----------|------------|
| Agent runtime | [LangGraph](https://langchain-ai.github.io/langgraph/) |
| Observability | [LangSmith](https://smith.langchain.com) + LangGraph Studio |
| LLM | OpenAI (`gpt-3.5-turbo` by default) |
| Checkpointing | In-memory (Postgres deferred until FastAPI) |

## Prerequisites

| Tool | Notes |
|------|-------|
| Python 3.11+ | Recommended runtime |
| [uv](https://docs.astral.sh/uv/) | Dependency management |
| LangSmith account | Free tier is fine — needed for Studio and traces |

## Getting started

```bash
cd signals   # or your local clone path

# Install server dependencies (including dev tools)
cd server && uv sync --dev

# Configure environment (single root .env for all services)
cd .. && cp .env.example .env
# Set OPENAI_API_KEY and LANGSMITH_API_KEY in .env
```

## LangGraph Studio (primary dev loop)

Start the local dev server from `server/`:

```bash
cd server
uv run langgraph dev --port 2024
```

Open the Studio URL printed in the terminal, e.g.:

```
https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
```

Studio loads the `signals_agent` graph defined in [`server/langgraph.json`](server/langgraph.json). Edit nodes in `server/app/graph/`, save, and re-invoke in Studio — the dev server hot-reloads.

**No Docker or Postgres required for Studio.** Checkpointing is in-memory during local development.

### Studio input (pass state on each invoke)

Paste this into the Studio **Input** panel (adjust as needed):

```json
{
  "messages": [{"role": "human", "content": "hello"}],
  "user_name": "Hrishikesh"
}
```

See [`server/studio_input.example.json`](server/studio_input.example.json) for a copy-paste template.

After the run, open the run’s **State → Output** (or `__end__` in the trace) to see the full merged state: `messages`, `user_name`, `scope`, and `intent`.

### Intent clarify resume (partial intent)

When `intent_clarify` interrupts, resume with **one** of these shapes:

```json
{"signal_type": "offline_conversion"}
```

LangGraph Studio often echoes the interrupt payload back — that also works when `field.selected` or `field.suggested` is set:

```json
{
  "open_question": "signal_type",
  "field": {"selected": "offline_conversion", "suggested": "offline_conversion"}
}
```

Or a bare string (same thread resume):

```json
"offline_conversion"
```

Or for source / channels:

```json
{"source": "salesforce"}
```

```json
{"channels": ["meta_capi", "google_offline_conversions"]}
```

## CLI (multi-turn testing)

Invoke the graph from the command line with in-memory checkpointing:

```bash
cd server

# Single message with user name
uv run python -m app.cli -m "hello" -u "Hrishikesh"

# Or set a default in .env: SIGNALS_DEFAULT_USER_NAME=Hrishikesh
uv run python -m app.cli -m "hello"

# Print full merged state (not just the last reply)
uv run python -m app.cli -m "hello" -u "Hrishikesh" --dump-state

# Multi-turn — reuse the same thread ID across invocations
uv run python -m app.cli -m "hello" -u "Hrishikesh" --thread-id dev-1
uv run python -m app.cli -m "Salesforce to Meta" --thread-id dev-1
```

## Environment variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENAI_API_KEY` | LLM provider API key | — |
| `OPENAI_MODEL` | Model name | `gpt-3.5-turbo` |
| `LANGSMITH_TRACING` | Enable LangSmith traces | `true` |
| `LANGSMITH_API_KEY` | LangSmith API key | — |
| `LANGSMITH_PROJECT` | LangSmith project name | `signals-langraph-agent` |
| `LANGSMITH_ENDPOINT` | LangSmith API endpoint | `https://api.smith.langchain.com` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `SIGNALS_DEFAULT_USER_NAME` | Default `user_name` for CLI invokes | — |

See [`.env.example`](.env.example) for the full template (includes commented placeholders for future Postgres, FastAPI, and client vars).

## Project structure

```
signals/
├── .env                    # gitignored — single env file for all services
├── .env.example
├── .gitignore
├── README.md
├── docker-compose.yml      # skeleton: postgres + server + client
│
├── client/                 # Next.js + CopilotKit (scaffold only)
│   ├── Dockerfile
│   ├── package.json
│   └── src/app/
│
└── server/                 # FastAPI + LangGraph + PostgreSQL (Python tooling)
    ├── Dockerfile
    ├── pyproject.toml
    ├── uv.lock
    ├── langgraph.json
    ├── studio_input.example.json
    ├── tests/
    └── app/
        ├── sources/               # CRM source of truth (YAML + connectors)
        ├── destinations/          # Ad destination source of truth
        ├── internal/              # Shared schema config
        ├── graph/                 # LangGraph orchestration
        ├── config.py
        ├── cli.py                 # LangGraph CLI (local invoke)
        ├── main.py                # FastAPI app
        ├── database.py
        └── routers/
            └── health.py
```

**Rule:** `server/app/sources/`, `server/app/destinations/`, and `server/app/internal/` are source-of-truth packages — config load, id lookup, auth paths, and live API connectors only. All processing on top of that data (scope validation, intent resolution, mention parsing, HITL clarify payloads) lives in `server/app/graph/`.

## Development

```bash
cd server

# Install with dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Lint / format
uv run ruff check .
uv run ruff format .
```

## Docker

[`docker-compose.yml`](docker-compose.yml) runs postgres, server, and client with hot reload:

- **Server:** mounts `server/app/` with `uvicorn --reload`
- **Client:** `next dev` with `src/` / `public` mounted

```bash
docker compose up --build   # first time / after dependency changes
docker compose up           # daily development
```

| Change | Rebuild needed? |
|--------|-----------------|
| `server/app/**` | No — uvicorn reloads |
| `client/src/**`, `client/public/**` | No — Next HMR |
| `server/pyproject.toml` / `client/package.json` | Yes — `docker compose build` |

App: [http://localhost:3000](http://localhost:3000) · API: [http://localhost:8000](http://localhost:8000)

LangGraph Studio (`uv run langgraph dev --port 2024`) stays local and does not use this compose file.

## Postgres checkpointing

FastAPI lifespan uses `AsyncPostgresSaver.from_conn_string` (agent pattern), calls
`setup()`, and compiles `signals_agent` onto `app.state.compiled_graph`. Session IDs are
LangGraph `thread_id`s; see `server/app/graph/checkpoint.py` for `delete_thread`.

## Related projects

| Repository | Description |
|------------|-------------|
| [signals_copilot](../signals_copilot) | Full-stack Signals AI copilot (FastAPI + Next.js + LangGraph) |
| [agent](../agent) | Signals Setup Copilot (LangGraph + CopilotKit) |

## License

Proprietary — Datahash. All rights reserved.
