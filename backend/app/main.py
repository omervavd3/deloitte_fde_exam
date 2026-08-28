import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from app.agent.graph import build_graph
from app.api import airports, chat, conversations, health, profiles
from app.config import get_settings
from app.data.live_provider import LiveProvider
from app.db import repository

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def _configure_langsmith(settings) -> None:
    if not settings.langsmith_tracing or not settings.langsmith_api_key:
        os.environ["LANGSMITH_TRACING"] = "false"
        return
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    log.info("langsmith tracing enabled: project=%s", settings.langsmith_project)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    _configure_langsmith(settings)

    provider = LiveProvider(settings)
    await provider.warm()
    app.state.provider = provider

    async with AsyncConnectionPool(
        conninfo=settings.database_url,
        max_size=20,
        open=False,
        kwargs={"autocommit": True, "prepare_threshold": 0},
    ) as pool:
        await pool.wait()
        app.state.pool = pool

        await repository.init_schema(pool)
        await repository.seed_profiles(pool)

        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()

        app.state.graph = build_graph(checkpointer)
        log.info("startup complete")
        yield


app = FastAPI(title="Airport Investment Intelligence Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(airports.router, prefix="/api", tags=["airports"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(conversations.router, prefix="/api", tags=["conversations"])
app.include_router(profiles.router, prefix="/api", tags=["profiles"])
