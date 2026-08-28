from fastapi import APIRouter, HTTPException, Request

from app.db import repository
from app.scoring.profiles import METRICS
from app.schemas.profile import WeightProfile, WeightProfileCreate, WeightProfileUpdate

router = APIRouter()


@router.get("/metrics")
async def list_metrics() -> list[str]:
    """Metric keys the dashboard can build a profile from."""
    return METRICS


@router.get("/profiles")
async def list_profiles(request: Request) -> list[WeightProfile]:
    rows = await repository.list_profiles(request.app.state.pool)
    return [WeightProfile(**r) for r in rows]


@router.post("/profiles", status_code=201)
async def create_profile(request: Request, payload: WeightProfileCreate) -> WeightProfile:
    pool = request.app.state.pool
    if await repository.get_profile(pool, payload.name):
        raise HTTPException(409, f"profile already exists: {payload.name}")
    row = await repository.upsert_profile(
        pool, payload.name, payload.label, payload.description, payload.weights
    )
    return WeightProfile(**row)


@router.put("/profiles/{name}")
async def update_profile(
    request: Request, name: str, payload: WeightProfileUpdate
) -> WeightProfile:
    pool = request.app.state.pool
    existing = await repository.get_profile(pool, name)
    if not existing:
        raise HTTPException(404, f"no such profile: {name}")
    row = await repository.upsert_profile(
        pool, name, payload.label, payload.description, payload.weights,
        is_builtin=existing["is_builtin"],
    )
    return WeightProfile(**row)


@router.delete("/profiles/{name}", status_code=204)
async def delete_profile(request: Request, name: str) -> None:
    pool = request.app.state.pool
    existing = await repository.get_profile(pool, name)
    if not existing:
        raise HTTPException(404, f"no such profile: {name}")
    if existing["is_builtin"]:
        raise HTTPException(400, "built-in profiles cannot be deleted")
    await repository.delete_profile(pool, name)
