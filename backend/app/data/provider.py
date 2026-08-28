from typing import Any, Protocol

import pandas as pd


class MetricsProvider(Protocol):
    """Seam between data acquisition and scoring.

    LiveProvider fetches from public APIs. A SnapshotProvider reading a
    prebuilt parquet can replace it without touching scoring or the graph.
    """

    async def warm(self) -> None: ...

    def get_metrics(self) -> pd.DataFrame:
        """One row per airport, indexed by IATA code."""
        ...

    def provenance(self) -> dict[str, Any]:
        """Source names, as-of dates and row counts, for the UI and /health."""
        ...
