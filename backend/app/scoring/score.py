"""Deterministic scoring. No LLM, no I/O, no network.

Every user-visible number originates here.

Percentiles are computed over the full airport universe before any subset is
applied, so a score means the same thing in every query. Ranking within a
filtered set would make BOS "100th percentile" simply for being the only large
hub in New England.

Normalization is global by default. Ranking within hub tier is available via
`peer_group_col`, but it must not be the default: a nonhub's percentile among
nonhubs is not comparable to a large hub's percentile among large hubs, so a
mixed-tier ranking would put small regional airports above major hubs.
"""

from dataclasses import dataclass, field

import pandas as pd

from app.scoring.normalize import coverage, percentile_within_group

# Any airport scored on less than the full metric set is flagged. Only a
# handful lack runway data, so this stays quiet in practice.
COVERAGE_WARN_BELOW = 1.0


@dataclass
class ScoreResult:
    ranked: pd.DataFrame
    breakdown: dict[str, dict[str, float]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    # How the score was reached, not just what it was. A percentile is only
    # interpretable against the population it was taken over, and a
    # renormalized row was ranked on a different blend than its neighbours -
    # neither is recoverable from `ranked` alone, so both are recorded here.
    universe_size: int = 0
    missing: dict[str, list[str]] = field(default_factory=dict)
    effective_weights: dict[str, dict[str, float]] = field(default_factory=dict)


GLOBAL_GROUP = "__all__"


def score_airports(
    metrics: pd.DataFrame,
    weights: dict[str, float],
    peer_group_col: str | None = None,
    subset: list[str] | None = None,
) -> ScoreResult:
    """Normalize within peer group, apply weights, rank.

    Airports missing a metric are scored on what they have, with the weights
    renormalized over the available ones. Scores stay on a 0-100 scale and the
    per-component points always sum to the score.
    """
    active = {m: w for m, w in weights.items() if w > 0 and m in metrics.columns}
    if not active:
        raise ValueError("no usable metrics in weights")

    df = metrics.copy()
    group_col = peer_group_col
    if group_col is None:
        group_col = GLOBAL_GROUP
        df[GLOBAL_GROUP] = GLOBAL_GROUP

    pct = pd.DataFrame(index=df.index)
    for metric in active:
        pct[metric] = percentile_within_group(df, metric, group_col)

    weight_row = pct.notna() * pd.Series(active)
    total_weight = weight_row.sum(axis=1)

    # The weights actually applied per airport. Equal to `active` wherever the
    # row is complete, and scaled up over the present metrics wherever it is
    # not - which is the whole reason a thin row is not comparable to a full one.
    applied = weight_row.div(total_weight, axis=0)

    points = pct.fillna(0.0) * applied
    df["score"] = points.sum(axis=1)
    df["coverage"] = coverage(df, list(active))

    # Every airport the percentiles were taken over, recorded before the subset
    # narrows the frame: it is the population a score is a standing within.
    universe_size = len(df)

    if subset is not None:
        df = df.loc[df.index.intersection(subset)]
        points = points.loc[df.index]

    df = df[df["score"].notna()].sort_values("score", ascending=False)
    df["rank"] = range(1, len(df) + 1)

    breakdown = {
        iata: {m: round(v, 2) for m, v in row.items() if v > 0}
        for iata, row in points.loc[df.index].round(2).iterrows()
    }

    absent = pct.loc[df.index].isna()
    missing = {
        iata: [m for m in active if row[m]]
        for iata, row in absent.iterrows()
        if row.any()
    }
    effective_weights = {
        iata: {m: round(w, 4) for m, w in row.items() if w > 0}
        for iata, row in applied.loc[df.index].iterrows()
    }

    warnings = [
        _thin_row_warning(iata, missing[iata], effective_weights[iata], active)
        for iata, row in df.iterrows()
        if row.coverage < COVERAGE_WARN_BELOW and iata in missing
    ]

    return ScoreResult(
        ranked=df,
        breakdown=breakdown,
        warnings=warnings,
        universe_size=universe_size,
        missing=missing,
        effective_weights=effective_weights,
    )


def _thin_row_warning(
    iata: str,
    absent: list[str],
    applied: dict[str, float],
    active: dict[str, float],
) -> str:
    """Name the gap and the blend it forced, not just a coverage percentage.

    "scored on 67% of inputs" tells a reader the score is weaker; it does not
    tell them the row was ranked on a different thesis than the rows above it,
    which is the part that changes how the ranking should be read.
    """
    reweighted = ", ".join(
        f"{m} {active[m]:.0%}->{applied[m]:.0%}" for m in sorted(applied)
    )
    return (
        f"{iata}: no {', '.join(sorted(absent))}"
        f" - scored on {len(applied)} of {len(active)} metrics,"
        f" reweighted to {reweighted}"
    )
