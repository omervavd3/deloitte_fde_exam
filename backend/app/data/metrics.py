"""Derives scored metrics from raw source frames.

Documented assumptions, all overridable:

PAX_WEIGHT_LB           average passenger + baggage weight, used to put freight
                        (pounds) and passengers (a count) on one scale.
RUNWAY_DEPARTURE_CEILING practical annual departures a single runway sustains.
                        A planning heuristic, not a measured capacity.
HUB_THRESHOLDS          FAA hub classes are defined as a share of total US
                        enplanements. Derived here rather than read from the
                        FAA ACAIS file, so it is a proxy for the official tier.
"""

import numpy as np
import pandas as pd

PAX_WEIGHT_LB = 200
RUNWAY_DEPARTURE_CEILING = 120_000
HUB_THRESHOLDS = {"large": 0.01, "medium": 0.0025, "small": 0.0005}


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator.divide(denominator.replace(0, np.nan))


def classify_hub(enplanements: pd.Series) -> pd.Series:
    share = enplanements / enplanements.sum()
    return pd.cut(
        share,
        bins=[-np.inf, HUB_THRESHOLDS["small"], HUB_THRESHOLDS["medium"],
              HUB_THRESHOLDS["large"], np.inf],
        labels=["nonhub", "small", "medium", "large"],
    ).astype(str)


def build(t100: pd.DataFrame, airports: pd.DataFrame, runways: pd.DataFrame) -> pd.DataFrame:
    df = t100.merge(airports, on="iata", how="inner")
    df = df.merge(runways, on="ident", how="left")

    df["enplanement_volume"] = df["enplanements"]
    df["pax_per_departure"] = _safe_divide(df["passengers"], df["departures"])
    df["departures_per_runway"] = _safe_divide(df["departures"], df["runway_count"])
    df["freight_share"] = _safe_divide(
        df["freight"], df["freight"] + df["passengers"] * PAX_WEIGHT_LB
    )
    df["runway_pressure"] = (
        df["departures_per_runway"] / RUNWAY_DEPARTURE_CEILING
    ).clip(0, 1)

    df = df[df["enplanements"] > 0].copy()
    df["hub_tier"] = classify_hub(df["enplanement_volume"])

    return df.set_index("iata").sort_values("enplanement_volume", ascending=False)
