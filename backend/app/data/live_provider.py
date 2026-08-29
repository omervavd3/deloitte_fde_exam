import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from app.config import Settings
from app.data import metrics
from app.data.cache import TTLCache
from app.data.sources import bts_t100, ourairports

log = logging.getLogger(__name__)

WARM_ATTEMPTS = 3
WARM_BACKOFF_SECONDS = 2.0


async def _with_retry(fetch, label: str):
    """Retries a startup fetch so one connect blip cannot fail the whole boot.

    Takes a factory, not a coroutine: a coroutine cannot be awaited twice.
    """
    for attempt in range(1, WARM_ATTEMPTS + 1):
        try:
            return await fetch()
        except Exception as exc:
            if attempt == WARM_ATTEMPTS:
                raise
            log.warning(
                "%s fetch failed (attempt %d/%d), retrying: %s",
                label, attempt, WARM_ATTEMPTS, exc,
            )
            await asyncio.sleep(WARM_BACKOFF_SECONDS * attempt)


class LiveProvider:
    """Warms airport metrics from public APIs at startup and holds them in memory.

    Implements MetricsProvider. Replaceable by a snapshot-backed provider
    without changes to scoring or the graph.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._metrics: pd.DataFrame | None = None
        self._provenance: dict[str, Any] = {}
        self._live_cache = TTLCache(settings.live_cache_ttl_seconds)

    async def warm(self) -> None:
        timeout = self._settings.http_timeout_seconds * 6

        t100, airports, runways = await asyncio.gather(
            _with_retry(lambda: bts_t100.fetch_all(timeout), "BTS T-100"),
            _with_retry(lambda: ourairports.fetch_airports(timeout), "OurAirports airports"),
            _with_retry(lambda: ourairports.fetch_runways(timeout), "OurAirports runways"),
        )
        self._metrics = metrics.build(t100, airports, runways)

        self._provenance = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "airports": int(len(self._metrics)),
            "sources": [
                {"name": "BTS T-100 (ArcGIS)", "url": bts_t100.BASE_URL,
                 "as_of": f"CY{int(t100['year'].max())}", "rows": int(len(t100))},
                {"name": "OurAirports", "url": ourairports.AIRPORTS_URL,
                 "as_of": "nightly", "rows": int(len(airports))},
            ],
            "assumptions": {
                "pax_weight_lb": metrics.PAX_WEIGHT_LB,
                "runway_departure_ceiling": metrics.RUNWAY_DEPARTURE_CEILING,
                "hub_tier": "derived from enplanement share, proxy for FAA ACAIS",
            },
        }
        log.info("warmed %d airports from live APIs", len(self._metrics))

    def get_metrics(self) -> pd.DataFrame:
        if self._metrics is None:
            raise RuntimeError("provider not warmed")
        return self._metrics

    def provenance(self) -> dict[str, Any]:
        return self._provenance
