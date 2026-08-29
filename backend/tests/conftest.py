import pandas as pd
import pytest

from app.data.metrics import RUNWAY_DEPARTURE_CEILING, RUNWAY_OPERATIONS_CEILING


@pytest.fixture
def sample_metrics() -> pd.DataFrame:
    """Small hand-checked frame. Scoring tests must never touch the network.

    The ceiling-relative metrics are derived from their inputs rather than
    written by hand, because they are monotone transforms of them: a fixture
    that ranks SNA top on departures_per_runway and bottom on runway_pressure
    describes a frame the pipeline cannot produce, and hides the redundancy
    those two metrics actually have.
    """
    df = pd.DataFrame(
        [
            {"iata": "LAX", "hub_tier": "large", "enplanement_volume": 26_239_010,
             "pax_per_departure": 127.5, "departures_per_runway": 51_659,
             "operations_per_runway": 103_318, "freight_share": 0.031,
             "mail_share": 0.04},
            {"iata": "BOS", "hub_tier": "large", "enplanement_volume": 21_000_000,
             "pax_per_departure": 110.0, "departures_per_runway": 33_000,
             "operations_per_runway": 88_000, "freight_share": 0.010,
             "mail_share": 0.11},
            {"iata": "SNA", "hub_tier": "medium", "enplanement_volume": 5_800_000,
             "pax_per_departure": 98.0, "departures_per_runway": 59_000,
             "operations_per_runway": 118_000, "freight_share": 0.002,
             "mail_share": 0.02},
        ]
    ).set_index("iata")

    df["runway_pressure"] = (
        df["departures_per_runway"] / RUNWAY_DEPARTURE_CEILING
    ).clip(0, 1)
    df["airfield_saturation"] = (
        df["operations_per_runway"] / RUNWAY_OPERATIONS_CEILING
    ).clip(0, 1)
    return df
