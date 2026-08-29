"""What each scored metric measures, in the terms a reader would ask for.

A profile's weights carry a key and a number, so narrate can say "load_factor
(30%)" but not what load factor is. This is that missing half. Every metric is
written so that higher means more investment need.

The only copy: the agent reads it through `glossary_for`, the dashboard over
/api/metrics through `metric_catalog`, so the two cannot disagree.
"""

from dataclasses import asdict, dataclass

from app.scoring.profiles import METRICS, REDUNDANT_METRIC_PAIRS


@dataclass(frozen=True)
class MetricMeaning:
    label: str
    formula: str
    means: str
    # From the optional T-100 Segment extract, so NaN everywhere until that file
    # is loaded. The dashboard flags it.
    needs_segment: bool = False


GLOSSARY: dict[str, MetricMeaning] = {
    "pax_per_departure": MetricMeaning(
        label="Passengers per departure",
        formula="Passengers divided by departures performed.",
        means=(
            "How full and how large the average departing aircraft is. High "
            "values mean each flight pushes more people through the terminal, "
            "so gates, security and baggage feel the strain before the airfield "
            "does."
        ),
    ),
    "departures_per_runway": MetricMeaning(
        label="Departures per runway",
        formula="Annual departures divided by the airport's runway count.",
        means=(
            "How hard each runway is worked. High values mean movements are "
            "concentrated on few runways - the classic airfield throughput "
            "constraint."
        ),
    ),
    "operations_per_runway": MetricMeaning(
        label="Operations per runway",
        formula=(
            "Departures plus arrivals, divided by the number of runways at "
            "least 5,000 ft long."
        ),
        means=(
            "Airfield loading counted properly: arrivals use the same concrete "
            "departures do, and a short general-aviation strip cannot take a "
            "scheduled jet."
        ),
    ),
    "airfield_saturation": MetricMeaning(
        label="Airfield saturation",
        formula=(
            "Operations per runway against an assumed planning ceiling of "
            "240,000 operations per runway per year, capped at 1."
        ),
        means=(
            "How close the airfield runs to its assumed practical capacity. A "
            "value near 1.0 means the runways are at or beyond what they are "
            "assumed to sustain. This is capacity utilization averaged over a "
            "year, not measured congestion."
        ),
    ),
    "enplanement_volume": MetricMeaning(
        label="Enplanement volume",
        formula="Total annual boarding passengers.",
        means=(
            "Raw passenger size. Not a constraint on its own, but it scales how "
            "much any given bottleneck costs, and it is what FAA hub tiers are "
            "derived from."
        ),
    ),
    "freight_share": MetricMeaning(
        label="Freight share",
        formula=(
            "Freight pounds divided by freight pounds plus passengers times "
            "200 lb, the assumed weight of a passenger and their bags."
        ),
        means=(
            "How cargo-oriented the airport is once passengers and freight are "
            "put on one scale. High values point to warehousing, ramp and "
            "logistics investment rather than terminal work."
        ),
    ),
    "runway_pressure": MetricMeaning(
        label="Runway pressure",
        formula=(
            "Departures per runway against an assumed planning ceiling of "
            "120,000 departures per runway per year, capped at 1."
        ),
        means=(
            "Departures per runway expressed against an assumed practical "
            "capacity. The ceiling is a planning heuristic, not a measured "
            "capacity."
        ),
    ),
    "mail_share": MetricMeaning(
        label="Mail share",
        formula=(
            "Mail pounds divided by mail plus freight pounds, left blank below "
            "100,000 lb of combined cargo."
        ),
        means=(
            "How much of the airport's cargo is postal rather than general "
            "freight. High values are communities where air mail is the supply "
            "line, such as the Alaska bypass network."
        ),
    ),
    "load_factor": MetricMeaning(
        label="Load factor",
        formula=(
            "Passengers divided by seats across every segment flown from the "
            "airport."
        ),
        means=(
            "How full aircraft leave. High values mean little slack left to "
            "absorb growth, so demand has to be met with more or larger flights "
            "rather than fuller ones."
        ),
        needs_segment=True,
    ),
    "long_haul_share": MetricMeaning(
        label="Long-haul share",
        formula=(
            "Share of departures on segments of 2,500 statute miles or more, "
            "weighted by departures performed."
        ),
        means=(
            "How much of the flying is long-distance. High values imply "
            "widebody gates, longer turns and heavier fuel and ground-handling "
            "demands."
        ),
        needs_segment=True,
    ),
    "international_share": MetricMeaning(
        label="International share",
        formula=(
            "Share of departures to non-US destinations, weighted by departures "
            "performed."
        ),
        means=(
            "How much of the traffic crosses a border. High values drive customs "
            "and border halls, international arrivals and sterile-corridor "
            "capacity."
        ),
        needs_segment=True,
    ),
    "schedule_shortfall": MetricMeaning(
        label="Schedule shortfall",
        formula=(
            "One minus the completion rate, over segments that actually had "
            "scheduled service."
        ),
        means=(
            "The share of scheduled departures that did not fly - the closest "
            "public proxy for demand the airport could not serve. High values "
            "suggest constraint or reliability problems rather than raw size."
        ),
        needs_segment=True,
    ),
}


def metric_catalog() -> dict:
    """Every weightable metric, described, for the dashboard to render.

    Ordered by METRICS so the profile editor's sliders keep the order the
    scoring module lists them in. `redundant_pairs` rides along because the
    editor warns on them and would otherwise need its own copy.
    """
    return {
        "metrics": [
            {"metric": metric, **asdict(GLOSSARY[metric])}
            for metric in METRICS
            if metric in GLOSSARY
        ],
        "redundant_pairs": [list(pair) for pair in REDUNDANT_METRIC_PAIRS],
    }


def glossary_for(weights: dict[str, float]) -> list[dict]:
    """The weighted metrics, described, heaviest first.

    Ordered rather than keyed so the reading order is decided here: a profile is
    understood fastest through the metric carrying most of it.
    """
    weighted = sorted(
        ((m, w) for m, w in weights.items() if w > 0 and m in GLOSSARY),
        key=lambda item: -item[1],
    )
    return [
        {"metric": metric, "weight": weight, **asdict(GLOSSARY[metric])}
        for metric, weight in weighted
    ]
