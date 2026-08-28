"""OpenSky live aircraft states. Anonymous access works; rate limited.

Used as a live congestion indicator only. Never feeds the score.
"""

import logging

import httpx

log = logging.getLogger(__name__)

STATES_URL = "https://opensky-network.org/api/states/all"

ON_GROUND_INDEX = 8


async def count_traffic(
    lat: float, lon: float, radius_deg: float = 0.75, timeout: float = 8.0
) -> dict | None:
    """Aircraft currently within a bounding box around an airport."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(STATES_URL, params={
                "lamin": lat - radius_deg,
                "lamax": lat + radius_deg,
                "lomin": lon - radius_deg,
                "lomax": lon + radius_deg,
            })
            response.raise_for_status()
            states = response.json().get("states") or []
    except Exception as exc:
        log.warning("OpenSky unavailable: %s", exc)
        return None

    return {
        "aircraft_in_area": len(states),
        "on_ground": sum(1 for s in states if len(s) > ON_GROUND_INDEX and s[ON_GROUND_INDEX]),
    }
