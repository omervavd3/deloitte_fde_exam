from dataclasses import dataclass
from typing import Any

from langchain_openai import ChatOpenAI
from psycopg_pool import AsyncConnectionPool


@dataclass
class Deps:
    """Dependencies bound into nodes when the graph is built."""

    provider: Any
    pool: AsyncConnectionPool
    llm: ChatOpenAI
