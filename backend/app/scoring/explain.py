"""Plain-English statements about how a ranking was produced.

Deterministic, like the scores themselves. `narrate` may restate these but
never authors them: a caveat the model is free to paraphrase is a caveat it is
free to drop, and these are exactly the ones a reader needs in order not to
over-read a ranking.

Each note answers a question the numbers cannot answer about themselves:

  Normalization  what population a score is a standing within. Percentiles are
                 taken over the national frame before any subset is applied
                 (see app.scoring.score), so "93.9" is not a rank within the
                 rows on screen - the single most likely misreading.
  Ties           where the scale has run out of resolution. Percentile scoring
                 compresses hard at the top; a 0.3 gap between two airports
                 near the ceiling is not an ordering.
  Coverage       which rows were ranked on a different blend than their
                 neighbours, because a weighted metric was missing for them.
  Not measured   what a high score cannot mean, given what the pipeline holds.
"""

from dataclasses import dataclass

from app.scoring.score import ScoreResult

# Two scores closer than this are one band. Percentile ranks are integers over
# the airport count before weighting, so sub-point gaps near the ceiling are
# separation the input data does not actually support.
NEAR_TIE_POINTS = 1.0

# Metrics derived from annual totals against an assumed runway ceiling. None of
# the sources carry a departure time, so none of these can speak to peak hour.
AIRFIELD_METRICS = {
    "departures_per_runway",
    "runway_pressure",
    "operations_per_runway",
    "airfield_saturation",
}


@dataclass
class MethodNote:
    topic: str
    detail: str


def _normalization(result: ScoreResult, shown: int) -> MethodNote:
    # The clause only earns its place when a subset was actually taken; on an
    # unfiltered query the population and the table are the same rows.
    narrowed = (
        f", before the {shown} shown here were selected"
        if shown < result.universe_size
        else ""
    )
    return MethodNote(
        "Normalization",
        f"Each metric is converted to a percentile rank across all "
        f"{result.universe_size:,} airports with reported traffic nationwide"
        f"{narrowed}. A score is national standing on the weighted blend - not "
        f"a position within this list, and not a percentage of anything "
        f"physical.",
    )


def _ties(scores: list[dict]) -> MethodNote | None:
    """The leading cluster, when the top rows are closer than the scale resolves."""
    if len(scores) < 2:
        return None

    cluster = [scores[0]]
    for previous, current in zip(scores, scores[1:]):
        if previous["score"] - current["score"] > NEAR_TIE_POINTS:
            break
        cluster.append(current)

    if len(cluster) < 2:
        return None

    named = [f"{s['iata']} ({s['score']})" for s in cluster]
    listed = " and ".join([", ".join(named[:-1]), named[-1]])
    return MethodNote(
        "Ties",
        f"{listed} fall within {NEAR_TIE_POINTS:g} point of each other. "
        f"Percentile scoring compresses at the top: once airports sit near the "
        f"national ceiling on every weighted metric, the remaining gap is "
        f"smaller than the method can resolve. Read them as one band rather "
        f"than as an order.",
    )


def _coverage(result: ScoreResult, scores: list[dict]) -> MethodNote | None:
    """Which shown rows were ranked on a reduced metric set, and on what."""
    thin = [s["iata"] for s in scores if s["iata"] in result.missing]
    if not thin:
        return None

    absent = sorted({m for iata in thin for m in result.missing[iata]})
    subject = "airport has" if len(thin) == 1 else "airports have"
    return MethodNote(
        "Coverage",
        f"{len(thin)} of the {len(scores)} {subject} no "
        f"{', '.join(absent)}: {', '.join(thin)}. The remaining weights were "
        f"scaled up to fill the gap, so those rows were ranked on a different "
        f"blend than the rest of the table and are not strictly comparable to "
        f"it. The per-airport warnings give the blend each one actually got.",
    )


def _unmeasured(weights: dict[str, float]) -> list[MethodNote]:
    """What a high score cannot mean, given the columns that exist."""
    notes = [
        MethodNote(
            "Not measured",
            "No metric here describes installed capacity - gates, terminal "
            "floor area, stands or runway slots. The ranking is demand "
            "pressure only: it does not know what has already been built, so "
            "an airport that just opened a new concourse still scores high.",
        )
    ]
    if AIRFIELD_METRICS & {m for m, w in weights.items() if w > 0}:
        notes.append(
            MethodNote(
                "Not measured",
                "The airfield metrics are annual totals against an assumed "
                "planning ceiling. No source in this pipeline carries a "
                "departure time, so nothing here reflects peak-hour demand or "
                "measured delay - this is capacity utilization, not congestion.",
            )
        )
    return notes


def method_notes(
    result: ScoreResult, weights: dict[str, float], scores: list[dict]
) -> list[MethodNote]:
    """Every caveat this particular ranking needs, in reading order.

    `scores` is the rendered subset, so the notes describe what is on screen
    rather than what was computed and then discarded.
    """
    if not scores:
        return []

    notes = [_normalization(result, len(scores))]
    for note in (_ties(scores), _coverage(result, scores)):
        if note:
            notes.append(note)
    return notes + _unmeasured(weights)
