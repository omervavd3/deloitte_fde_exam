from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from app.scoring.profiles import METRICS
from app.services.region_service import REGIONS, resolve_region

router = APIRouter()

RAW_COLS = ["year", "enplanements", "passengers", "departures", "arrivals",
            "freight", "mail"]

DISPLAY_COLS = ["name", "municipality", "iso_region", "type", "hub_tier",
                "latitude_deg", "longitude_deg",
                "runway_count", "air_carrier_runway_count", "usable_runway_count",
                "longest_runway_ft", *METRICS, *RAW_COLS]


def _records(df, limit: int) -> list[dict[str, Any]]:
    out = df.head(limit).reset_index()
    cols = ["iata"] + [c for c in DISPLAY_COLS if c in out.columns]
    return out[cols].round(4).to_dict("records")


@router.get("/regions")
async def list_regions() -> dict[str, list[str]]:
    return REGIONS


@router.get("/airports")
async def list_airports(
    request: Request,
    limit: int = Query(25, ge=1, le=500),
    region: str | None = None,
    hub_tier: str | None = None,
    sort_by: str = "enplanement_volume",
) -> dict[str, Any]:
    """Raw fetched metrics. No scoring applied."""
    df = request.app.state.provider.get_metrics()

    if region:
        codes = resolve_region(region)
        if codes is None:
            raise HTTPException(404, f"unknown region: {region}")
        df = df[df["iso_region"].isin(codes)]

    if hub_tier:
        df = df[df["hub_tier"] == hub_tier]

    if sort_by not in df.columns:
        raise HTTPException(400, f"unknown sort_by: {sort_by}")

    df = df.sort_values(sort_by, ascending=False)
    return {"count": int(len(df)), "airports": _records(df, limit)}


@router.get("/airports/{iata}")
async def get_airport(request: Request, iata: str) -> dict[str, Any]:
    df = request.app.state.provider.get_metrics()
    code = iata.upper()
    if code not in df.index:
        raise HTTPException(404, f"no data for {code}")
    return _records(df.loc[[code]], 1)[0]
