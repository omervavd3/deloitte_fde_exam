"""Resolves the weight set for a request.

Order: explicit overrides > named profile from Postgres > fallback profile.
The resolved weights are returned for logging on every answer.
"""

from psycopg_pool import AsyncConnectionPool

from app.scoring.profiles import FALLBACK_PROFILE


async def resolve_weights(
    pool: AsyncConnectionPool,
    profile_name: str | None,
    overrides: dict[str, float] | None,
) -> tuple[str, dict[str, float], bool]:
    """Returns (profile_name, weights, overridden)."""
    raise NotImplementedError
