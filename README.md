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

After the run, open the run’s **State → Output** (or `__end__` in the trace) to see the full merged state: `messages`, `user_name`, and `scope`.

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
│   ├── graph/
│   │   ├── state.py       # AgentState (MessagesState)
│   │   ├── nodes.py       # Graph nodes
│   │   └── graph.py       # build_studio_graph + build_graph
│   ├── config.py          # Settings via pydantic-settings
│   └── main.py            # CLI entrypoint
├── tests/
├── langgraph.json         # Studio config
├── pyproject.toml
├── .env.example
└── README.md
```

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
