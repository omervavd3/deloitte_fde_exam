import json
from pathlib import Path
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.scoring.profiles import DEFAULT_PROFILES

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


async def init_schema(pool: AsyncConnectionPool) -> None:
    # Executed one statement at a time: prepared statements reject multi-command SQL.
    statements = [s.strip() for s in SCHEMA_PATH.read_text().split(";") if s.strip()]
    async with pool.connection() as conn:
        for statement in statements:
            await conn.execute(statement)


async def seed_profiles(pool: AsyncConnectionPool) -> None:
    async with pool.connection() as conn:
        for name, weights in DEFAULT_PROFILES.items():
            await conn.execute(
                """
                INSERT INTO weight_profiles (name, label, weights, is_builtin)
                VALUES (%s, %s, %s, true)
                ON CONFLICT (name) DO NOTHING
                """,
                (name, name.replace("_", " ").title(), json.dumps(weights)),
            )


async def list_conversations(pool: AsyncConnectionPool) -> list[dict[str, Any]]:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations"
            " ORDER BY updated_at DESC LIMIT 100",
        )
        cur.row_factory = dict_row
        return await cur.fetchall()


async def create_conversation(pool: AsyncConnectionPool, conv_id: UUID, title: str) -> None:
    async with pool.connection() as conn:
        await conn.execute(
            "INSERT INTO conversations (id, title) VALUES (%s, %s)"
            " ON CONFLICT (id) DO NOTHING",
            (conv_id, title),
        )


async def touch_conversation(pool: AsyncConnectionPool, conv_id: UUID) -> None:
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE conversations SET updated_at = now() WHERE id = %s", (conv_id,)
        )


async def list_profiles(pool: AsyncConnectionPool) -> list[dict[str, Any]]:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT name, label, description, weights, is_builtin, updated_at"
            " FROM weight_profiles ORDER BY is_builtin DESC, name"
        )
        cur.row_factory = dict_row
        return await cur.fetchall()


async def get_profile(pool: AsyncConnectionPool, name: str) -> dict[str, Any] | None:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT name, label, description, weights, is_builtin, updated_at"
            " FROM weight_profiles WHERE name = %s",
            (name,),
        )
        cur.row_factory = dict_row
        return await cur.fetchone()
