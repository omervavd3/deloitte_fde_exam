"""OpenSky live aircraft states. Anonymous access works; rate limited.

Used as a live congestion indicator only. Never feeds the score.
"""

STATES_URL = "https://opensky-network.org/api/states/all"


async def count_traffic(
    lat: float, lon: float, radius_deg: float = 0.75, timeout: float = 8.0
) -> dict | None:
    """Aircraft currently within a bounding box around an airport."""
    raise NotImplementedError
