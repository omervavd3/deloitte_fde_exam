"""Resolves the weight set for a request.

Order: explicit overrides > named profile from Postgres > fallback profile.
The resolved weights are returned for logging on every answer.
"""

from psycopg_pool import AsyncConnectionPool

from app.db import repository
from app.scoring.profiles import FALLBACK_PROFILE


def _normalize(weights: dict[str, float]) -> dict[str, float]:
    total = sum(w for w in weights.values() if w > 0)
    if total <= 0:
        raise ValueError("weights must sum to more than zero")
    return {k: round(w / total, 4) for k, w in weights.items()}


async def resolve_weights(
    pool: AsyncConnectionPool,
    profile_name: str | None,
    overrides: dict[str, float] | None,
) -> tuple[str, dict[str, float], bool]:
    """Returns (profile_name, weights, overridden)."""
    name = profile_name or FALLBACK_PROFILE
    row = await repository.get_profile(pool, name)

    if row is None:
        name = FALLBACK_PROFILE
        row = await repository.get_profile(pool, name)
    if row is None:
        raise RuntimeError(f"fallback profile {FALLBACK_PROFILE} is missing")

    weights = dict(row["weights"])
    if overrides:
        weights.update(overrides)
        return name, _normalize(weights), True
    return name, weights, False


async def profile_catalog(pool: AsyncConnectionPool) -> list[dict]:
    """Name + description pairs, injected into the intent prompt."""
    rows = await repository.list_profiles(pool)
    return [{"name": r["name"], "description": r["description"]} for r in rows]
