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
    raise HTTPException(501, "not implemented")


@router.put("/profiles/{name}")
async def update_profile(
    request: Request, name: str, payload: WeightProfileUpdate
) -> WeightProfile:
    raise HTTPException(501, "not implemented")


@router.delete("/profiles/{name}", status_code=204)
async def delete_profile(request: Request, name: str) -> None:
    raise HTTPException(501, "not implemented")
