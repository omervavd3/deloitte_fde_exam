import pandas as pd

from app.agent.deps import Deps
from app.agent.state import AgentState

# A direct question is about a handful of named airports. More than this and it
# is not a lookup, so no per-airport facts are attached and narrate answers
# from what the system covers rather than from rows.
MAX_FACT_AIRPORTS = 5

FACT_COLUMNS = [
    "name",
    "municipality",
    "iso_region",
    "hub_tier",
    "enplanement_volume",
    "passengers",
    "departures",
    "freight",
    "runway_count",
    "pax_per_departure",
    "departures_per_runway",
    "freight_share",
    "runway_pressure",
    # From the optional T-100 Segment extract. Absent until the file is added,
    # and _clean drops missing values so the answer path stays honest.
    "seats",
    "load_factor",
    "avg_stage_length_sm",
    "long_haul_share",
    "international_share",
    "destinations_served",
    "completion_rate",
    "schedule_shortfall",
]


def _clean(value):
    """A JSON-safe Python scalar.

    numpy int64 is not a Python int, so an unconverted value serialises as a
    quoted string and the model reads a count as text.
    """
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    if hasattr(value, "item"):  # numpy scalar -> python scalar
        value = value.item()
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        # Counts arrive as floats from the merge; "3.0 runways" reads wrong.
        return int(value) if value.is_integer() else round(value, 4)
    return str(value)


async def load_facts(deps: Deps, state: AgentState) -> dict:
    """Deterministic: the raw metric row for each named airport.

    The lookup path's answer to load_metrics + score. It ranks nothing and
    computes nothing - narrate gets the stored values and may only restate
    them, which is what keeps a one-line question from returning a ranking.
    """
    metrics = deps.provider.get_metrics()
    airports = state.get("airports") or []

    if not airports or len(airports) > MAX_FACT_AIRPORTS:
        return {"facts": {}}

    columns = [c for c in FACT_COLUMNS if c in metrics.columns]
    facts = {
        code: {c: _clean(metrics.loc[code, c]) for c in columns}
        for code in airports
        if code in metrics.index
    }
    return {"facts": facts, "focus": list(facts)}
