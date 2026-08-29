"""Per-airport score composition: what actually moved each number.

`app.scoring.explain` says how to read a ranking; this says how one row reached
the score it did. Deterministic, so narrate restates these figures rather than
deriving them - which is what stops "driven by strong passenger numbers" from
standing in for an attribution.

Points are percentile times weight, so "37.8 points" is meaningless alone. It is
legible only against `max_points`: the 40 a 40%-weighted metric can contribute.
"""

from dataclasses import dataclass, field

from app.config import get_settings
from app.scoring.explain import NEAR_TIE_POINTS
from app.scoring.score import ScoreResult

# A weighted metric below this national percentile is holding a score back
# rather than building it.
WEAK_PERCENTILE_BELOW = 50.0

# Metrics whose points differ by less than this did not separate two adjacent
# rows in any meaningful way.
DECIDING_POINTS = 0.5

# How many metrics to name as separating one row from the next.
MAX_DECIDING_METRICS = 3

# Rows to attribute. A ranking can run to every airport in a state, and nobody
# asks why the fortieth placed where it did. The rest appear in `scores`.
MAX_ATTRIBUTED_ROWS = get_settings().max_attributed_rows


@dataclass
class Component:
    """One weighted metric's contribution to one airport's score."""

    metric: str
    value: float | None
    percentile: float
    weight: float
    points: float
    # weight * 100: the ceiling these points are read against. Carried because
    # narrate may not multiply it out for itself.
    max_points: float


@dataclass
class Separation:
    """How an airport stands against the next one down."""

    iata: str
    gap: float
    # Signed, so a negative entry marks a metric the airport trails on while
    # still leading overall - the reversal is the interesting half.
    differs_by: list[dict[str, float]] = field(default_factory=list)


@dataclass
class ScoreDrivers:
    iata: str
    score: float
    components: list[Component] = field(default_factory=list)
    carried_by: str | None = None
    held_back_by: str | None = None
    # Exactly one is ever set. A gap the Ties note calls unresolvable gets
    # `level_with`, so there is no "ahead_of" for narrate to reach for.
    ahead_of: Separation | None = None
    level_with: Separation | None = None


def _components(result: ScoreResult, row: dict) -> list[Component]:
    """Every metric that carried weight for this airport, strongest first."""
    iata = row["iata"]
    points = result.breakdown.get(iata, {})
    percentiles = result.percentiles.get(iata, {})
    values = row.get("metrics") or {}

    components = [
        Component(
            metric=metric,
            value=values.get(metric),
            percentile=percentiles[metric],
            weight=weight,
            # One decimal, like the score itself; a national percentile does not
            # resolve finely enough to justify two.
            points=round(points.get(metric, 0.0), 1),
            max_points=round(weight * 100, 1),
        )
        for metric, weight in result.effective_weights.get(iata, {}).items()
        if metric in percentiles
    ]
    return sorted(components, key=lambda c: -c.points)


def _separation(upper: dict, lower: dict, result: ScoreResult) -> Separation:
    """The per-metric points difference between two adjacent rows."""
    above = result.breakdown.get(upper["iata"], {})
    below = result.breakdown.get(lower["iata"], {})

    differences = [
        {
            "metric": metric,
            "points_ahead": round(above.get(metric, 0.0) - below.get(metric, 0.0), 2),
        }
        for metric in sorted(set(above) | set(below))
    ]
    deciding = sorted(differences, key=lambda d: -abs(d["points_ahead"]))

    return Separation(
        iata=lower["iata"],
        gap=round(upper["score"] - lower["score"], 1),
        differs_by=[
            d for d in deciding if abs(d["points_ahead"]) >= DECIDING_POINTS
        ][:MAX_DECIDING_METRICS],
    )


def score_drivers(result: ScoreResult, scores: list[dict]) -> list[ScoreDrivers]:
    """Composition of the leading scores, in the order they are shown.

    `ahead_of` still reaches the row below the cut, so the last attributed row
    is compared against a real neighbour rather than nothing.
    """
    drivers = []
    for position, row in enumerate(scores[:MAX_ATTRIBUTED_ROWS]):
        components = _components(result, row)
        weakest = min(components, key=lambda c: c.percentile) if components else None
        following = scores[position + 1] if position + 1 < len(scores) else None

        # Same threshold as the Ties note, imported rather than repeated: the
        # two drifting apart would let the payload contradict the caveat.
        separation = _separation(row, following, result) if following else None
        resolved = separation is not None and separation.gap >= NEAR_TIE_POINTS

        drivers.append(
            ScoreDrivers(
                iata=row["iata"],
                score=row["score"],
                components=components,
                carried_by=components[0].metric if components else None,
                held_back_by=(
                    weakest.metric
                    if weakest and weakest.percentile < WEAK_PERCENTILE_BELOW
                    else None
                ),
                ahead_of=separation if resolved else None,
                level_with=None if resolved else separation,
            )
        )
    return drivers
