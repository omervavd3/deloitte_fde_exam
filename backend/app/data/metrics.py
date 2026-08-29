"""Derives scored metrics from raw source frames.

Documented assumptions, all overridable:

PAX_WEIGHT_LB           average passenger + baggage weight, used to put freight
                        (pounds) and passengers (a count) on one scale.
RUNWAY_DEPARTURE_CEILING practical annual departures a single runway sustains.
                        A planning heuristic, not a measured capacity.
RUNWAY_OPERATIONS_CEILING the same ceiling counted in both directions, since a
                        runway serves arrivals and departures alike.
HUB_THRESHOLDS          FAA hub classes are defined as a share of total US
                        enplanements. Derived here rather than read from the
                        FAA ACAIS file, so it is a proxy for the official tier.
MAIL_SHARE_MIN_LB       combined mail + freight below which the mail ratio is
                        noise. Port Alsworth moves 10,408 lb of mail against
                        154 lb of freight; scored raw it outranks Bethel, which
                        moves 17.3M lb. Scoring percentiles globally so a tiny
                        denominator would beat a national mail hub.

Note what none of this measures: delay. Every airfield metric here is an annual
average against an assumed ceiling, which is capacity utilization, not
congestion - peak-hour demand is where congestion actually lives, and no source
in this pipeline carries a departure time. Reading `airfield_saturation` as
"congested" overstates what the data supports.
"""

import numpy as np
import pandas as pd

PAX_WEIGHT_LB = 200
RUNWAY_DEPARTURE_CEILING = 120_000
RUNWAY_OPERATIONS_CEILING = RUNWAY_DEPARTURE_CEILING * 2
MAIL_SHARE_MIN_LB = 100_000
HUB_THRESHOLDS = {"large": 0.01, "medium": 0.0025, "small": 0.0005}


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator.divide(denominator.replace(0, np.nan))


def usable_runways(df: pd.DataFrame) -> pd.Series:
    """Runways that can take scheduled jets, falling back to every runway.

    An airport whose longest runway is under the air carrier threshold still
    flies the traffic T-100 reports for it, so dividing by zero usable runways
    would drop it from every airfield metric. Its own runway count is the
    honest denominator there.
    """
    if "air_carrier_runway_count" not in df.columns:
        return df["runway_count"]
    counted = pd.to_numeric(df["air_carrier_runway_count"], errors="coerce")
    return counted.where(counted > 0).fillna(df["runway_count"])


def classify_hub(enplanements: pd.Series) -> pd.Series:
    share = enplanements / enplanements.sum()
    return pd.cut(
        share,
        bins=[-np.inf, HUB_THRESHOLDS["small"], HUB_THRESHOLDS["medium"],
              HUB_THRESHOLDS["large"], np.inf],
        labels=["nonhub", "small", "medium", "large"],
    ).astype(str)


def build(
    t100: pd.DataFrame,
    airports: pd.DataFrame,
    runways: pd.DataFrame,
    segment: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """`segment` is the optional T-100 Segment roll-up: purely additive columns.

    Left-joined, so airports it does not cover keep every existing metric and
    simply carry NaN for the new ones. Nothing here feeds the five scored
    metrics - adding the file must not move an existing score.
    """
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

    # Mail against all cargo. Zero mail beside real freight is a true zero, not
    # missing data; only a total too small to form a stable ratio becomes NaN.
    cargo_lb = df["mail"] + df["freight"]
    df["mail_share"] = (
        df["mail"] / cargo_lb.replace(0, np.nan)
    ).where(cargo_lb >= MAIL_SHARE_MIN_LB)

    # The corrected pair. `departures_per_runway` and `runway_pressure` count
    # one direction and divide by every strip on the field; these count both
    # directions and divide by runways scheduled service can actually use.
    # Kept alongside rather than replacing them so no existing profile moves.
    df["usable_runway_count"] = usable_runways(df)
    # Missing arrivals leaves the metric NaN rather than silently halving it:
    # scoring renormalizes around a NaN, but would rank a wrong number happily.
    operations = df["departures"] + df.get("arrivals", np.nan)
    df["operations_per_runway"] = _safe_divide(operations, df["usable_runway_count"])
    df["airfield_saturation"] = (
        df["operations_per_runway"] / RUNWAY_OPERATIONS_CEILING
    ).clip(0, 1)

    df = df[df["enplanements"] > 0].copy()
    df["hub_tier"] = classify_hub(df["enplanement_volume"])

    df = df.set_index("iata").sort_values("enplanement_volume", ascending=False)

    if segment is not None and not segment.empty:
        new = [c for c in segment.columns if c not in df.columns]
        df = df.join(segment[new], how="left")

        if "completion_rate" in df.columns:
            # Inverted at the data layer because scoring has no "lower is
            # better": it percentiles every metric and rewards the high end.
            # Score completion_rate raw and the winners are tiny fields that
            # fly everything they schedule because they schedule almost
            # nothing. Clipped because extra sections push completion above 1.
            df["schedule_shortfall"] = (1 - df["completion_rate"]).clip(0, 1)

    return df
