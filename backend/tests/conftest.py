import pandas as pd
import pytest


@pytest.fixture
def sample_metrics() -> pd.DataFrame:
    """Small hand-checked frame. Scoring tests must never touch the network."""
    return pd.DataFrame(
        [
            {"iata": "LAX", "hub_tier": "large", "enplanement_volume": 26_239_010,
             "pax_per_departure": 127.5, "departures_per_runway": 51_659,
             "freight_share": 0.031, "runway_pressure": 0.22},
            {"iata": "BOS", "hub_tier": "large", "enplanement_volume": 21_000_000,
             "pax_per_departure": 110.0, "departures_per_runway": 33_000,
             "freight_share": 0.010, "runway_pressure": 0.15},
            {"iata": "SNA", "hub_tier": "medium", "enplanement_volume": 5_800_000,
             "pax_per_departure": 98.0, "departures_per_runway": 59_000,
             "freight_share": 0.002, "runway_pressure": 0.05},
        ]
    ).set_index("iata")
