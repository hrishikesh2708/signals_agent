# Signals LangGraph Agent

LangGraph-based AI agent for [Signals](https://datahash.com) — orchestrating setup, configuration, and data workflows with deterministic control flow and LLM-assisted steps.

## Overview

This repository hosts a focused LangGraph agent for Signals. It is intended to complement the broader [signals_copilot](../signals_copilot) stack with a lean, graph-first implementation that can be embedded in services, run standalone, or integrated via API.

**Planned stack**

| Component | Technology |
|-----------|------------|
| Agent runtime | [LangGraph](https://langchain-ai.github.io/langgraph/) |
| API (optional) | FastAPI |
| LLM | OpenAI (configurable) |
| Persistence | PostgreSQL checkpointing (optional) |

## Prerequisites

| Tool | Notes |
|------|-------|
| Python 3.11+ | Recommended runtime |
| [uv](https://docs.astral.sh/uv/) or pip | Dependency management |
| Docker | Optional, for local Postgres |

## Getting started

> The project is in early setup. Commands below reflect the intended layout once source is added.

```bash
git clone git@github.com:hrishikesh2708/signals_agent.git
cd signals_agent

# Create a virtual environment and install dependencies (once pyproject.toml exists)
uv sync
# or: python -m venv .venv && source .venv/bin/activate && pip install -e .

# Copy environment template (once .env.example exists)
cp .env.example .env
# Set OPENAI_API_KEY and any Signals / OAuth credentials

# Run the agent or API server (once entrypoints exist)
uv run python -m app.main
```

## Environment variables

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | LLM provider API key |
| `DATABASE_URL` | PostgreSQL connection string (for graph checkpointing) |
| `LOG_LEVEL` | Logging verbosity (`INFO`, `DEBUG`, etc.) |

Additional variables will be documented in `.env.example` as the project grows.

## Project structure

```
signals_langraph_agent/
├── app/
│   ├── graph/          # LangGraph nodes, edges, and state
│   ├── tools/          # Agent tools (API calls, validators, etc.)
│   ├── config.py       # Settings via pydantic-settings
│   └── main.py         # CLI or FastAPI entrypoint
├── tests/
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

# Lint / format (once configured)
uv run ruff check .
uv run ruff format .
```

## Related projects

| Repository | Description |
|------------|-------------|
| [signals_copilot](../signals_copilot) | Full-stack Signals AI copilot (FastAPI + Next.js + LangGraph) |
| [agent](../agent) | Signals Setup Copilot (LangGraph + CopilotKit) |

## License

Proprietary — Datahash. All rights reserved.
