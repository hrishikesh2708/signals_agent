"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager

from copilotkit import CopilotKitRemoteEndpoint, LangGraphAGUIAgent
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import configure_logging, settings
from app.graph.checkpoint import postgres_conn_string
from app.graph.graph import build_graph
from app.routers import auth, copilotkit, health, projects, sessions

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    conn_string = postgres_conn_string(settings.database_url)
    async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
        await checkpointer.setup()
        compiled_graph = build_graph(checkpointer=checkpointer)
        ck_agent = LangGraphAGUIAgent(
            name="signals_agent",
            graph=compiled_graph,
            description="Signals setup agent",
        )
        app.state.checkpointer = checkpointer
        app.state.compiled_graph = compiled_graph
        app.state.langgraph_agent = ck_agent
        app.state.copilotkit_sdk = CopilotKitRemoteEndpoint(agents=[ck_agent])
        logger.info("Postgres checkpointer ready; signals_agent graph compiled")
        yield
    app.state.checkpointer = None
    app.state.compiled_graph = None
    app.state.langgraph_agent = None
    app.state.copilotkit_sdk = None


app = FastAPI(title="Signals API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1/auth")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(copilotkit.router, prefix="/api/v1/copilotkit", tags=["agent"])
