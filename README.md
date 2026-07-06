# Signals LangGraph Agent

LangGraph-based AI agent for [Signals](https://datahash.com) — orchestrating setup, configuration, and data workflows with deterministic control flow and LLM-assisted steps.

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
cd signals_langraph_agent

# Install dependencies (including dev tools)
uv sync --dev

# Configure environment
cp .env.example .env
# Set OPENAI_API_KEY and LANGSMITH_API_KEY in .env
```

## LangGraph Studio (primary dev loop)

Start the local dev server:

```bash
uv run langgraph dev --port 2024
```

Open the Studio URL printed in the terminal, e.g.:

```
https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
```

Studio loads the `signals_agent` graph defined in [`langgraph.json`](langgraph.json). Edit nodes in `app/graph/`, save, and re-invoke in Studio — the dev server hot-reloads.

**No Docker or Postgres required for Studio.** Checkpointing is in-memory during local development.

### Studio input (pass state on each invoke)

Paste this into the Studio **Input** panel (adjust as needed):

```json
{
  "messages": [{"role": "human", "content": "hello"}],
  "user_name": "Hrishikesh"
}
```

See [`studio_input.example.json`](studio_input.example.json) for a copy-paste template.

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
# Single message with user name
uv run python -m app.main -m "hello" -u "Hrishikesh"

# Or set a default in .env: SIGNALS_DEFAULT_USER_NAME=Hrishikesh
uv run python -m app.main -m "hello"

# Print full merged state (not just the last reply)
uv run python -m app.main -m "hello" -u "Hrishikesh" --dump-state

# Multi-turn — reuse the same thread ID across invocations
uv run python -m app.main -m "hello" -u "Hrishikesh" --thread-id dev-1
uv run python -m app.main -m "Salesforce to Meta" --thread-id dev-1
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

See [`.env.example`](.env.example) for the full template.

## Project structure

```
signals_langraph_agent/
├── app/
│   ├── sources/               # CRM source of truth (YAML + connectors per provider)
│   │   ├── config/            # *.yaml — CRM connector definitions
│   │   └── connectors/        # OAuth + describe_object per provider
│   ├── destinations/          # Ad destination source of truth (YAML + connectors)
│   │   ├── config/            # *.yaml — ad platform connector definitions
│   │   └── connectors/        # OAuth stubs per platform
│   ├── internal/              # Shared schema config (signal types, canonical fields)
│   │   └── config/            # signal_types.yaml, canonical.yaml
│   ├── graph/                 # LangGraph orchestration + all processing on SSOT data
│   │   ├── state.py           # SignalsState, intent/scope TypedDicts
│   │   ├── prompts.py         # LLM prompts
│   │   ├── handlers.py        # LLM calls + prompt catalog lines
│   │   ├── validators.py      # scope/intent/clarify validation and resolution
│   │   ├── validators_helpers.py  # lookup index + mention parsing (validators only)
│   │   ├── routers.py
│   │   ├── nodes.py
│   │   ├── llm.py
│   │   └── graph.py
│   ├── config.py
│   └── main.py
├── tests/
├── langgraph.json
├── pyproject.toml
└── README.md
```

**Rule:** `app/sources/`, `app/destinations/`, and `app/internal/` are source-of-truth packages — config load, id lookup, auth paths, and live API connectors only. All processing on top of that data (scope validation, intent resolution, mention parsing, HITL clarify payloads) lives in `app/graph/`.

## Development

```bash
# Install with dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Lint / format
uv run ruff check .
uv run ruff format .
```

## Adding Postgres checkpointing later

Postgres is deferred until FastAPI integration. When ready:

1. Add `langgraph-checkpoint-postgres` and `psycopg[binary]` to dependencies
2. Add `docker-compose.yml` with a Postgres 16 service
3. Add `app/graph/checkpoint.py` with `AsyncPostgresSaver`
4. Wire `build_graph(checkpointer=postgres_saver)` in a FastAPI `lifespan` hook

The graph nodes, state schema, and topology stay the same — only the checkpointer changes.

## Related projects

| Repository | Description |
|------------|-------------|
| [signals_copilot](../signals_copilot) | Full-stack Signals AI copilot (FastAPI + Next.js + LangGraph) |
| [agent](../agent) | Signals Setup Copilot (LangGraph + CopilotKit) |

## License

Proprietary — Datahash. All rights reserved.
