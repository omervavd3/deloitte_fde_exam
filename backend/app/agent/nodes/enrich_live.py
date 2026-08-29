import asyncio

from app.agent.deps import Deps
from app.agent.state import AgentState
from app.config import get_settings
from app.data.sources import faa_nas, opensky

MAX_LIVE_LOOKUPS = get_settings().max_live_lookups


async def enrich_live(deps: Deps, state: AgentState) -> dict:
    """Live FAA/OpenSky lookups. Advisory only, never feeds the score. Fail-soft."""
    focus = (state.get("focus") or [])[:MAX_LIVE_LOOKUPS]
    if not focus:
        return {"live_conditions": []}

    metrics = deps.provider.get_metrics()
    delays, *traffic = await asyncio.gather(
        faa_nas.fetch_delays(),
        *[
            opensky.count_traffic(
                float(metrics.loc[code, "latitude_deg"]),
                float(metrics.loc[code, "longitude_deg"]),
            )
            for code in focus
        ],
    )

    delayed = delays.get("airports", {})
    conditions = []
    for code, counts in zip(focus, traffic):
        entry = {"iata": code}
        if code in delayed and delayed[code]:
            entry["delay_reason"] = delayed[code][0].get("reason") or "delay reported"
        if counts:
            entry["aircraft_in_area"] = counts["aircraft_in_area"]
        if len(entry) > 1:
            conditions.append(entry)

    return {"live_conditions": conditions}
