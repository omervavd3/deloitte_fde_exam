from dataclasses import asdict

from app.agent.deps import Deps
from app.agent.state import DEFAULT_RESULT_LIMIT, AgentState
from app.scoring.explain import method_notes
from app.scoring.score import score_airports


async def score(deps: Deps, state: AgentState) -> dict:
    """Deterministic: normalize, weight, rank. Pure call into app.scoring."""
    metrics = deps.provider.get_metrics()
    subset = state.get("airports") or []

    # An empty subset means nothing matched, not "score everything". Treating
    # it as None would silently widen a failed regional filter to all airports.
    if not subset:
        return {
            "scores": [],
            "breakdown": {},
            "method_notes": [],
            "focus": [],
            "warnings": state.get("warnings", []) + ["no airports matched the query"],
        }

    result = score_airports(metrics, state["weights"], subset=subset)
    top = result.ranked.head(state.get("result_limit") or DEFAULT_RESULT_LIMIT)

    scores = [
        {
            "iata": iata,
            "name": row["name"],
            "score": round(float(row["score"]), 1),
            "rank": int(row["rank"]),
            "metrics": {
                m: (None if row[m] != row[m] else round(float(row[m]), 4))
                for m in state["weights"]
                if m in row.index
            },
        }
        for iata, row in top.iterrows()
    ]

    return {
        "scores": scores,
        "breakdown": {k: v for k, v in result.breakdown.items() if k in top.index},
        # Describes the rows that are shown, not the ones that were computed:
        # a tie or a coverage gap only matters where the reader can see it.
        "method_notes": [
            asdict(n) for n in method_notes(result, state["weights"], scores)
        ],
        "warnings": state.get("warnings", [])
        + [w for w in result.warnings if w.split(":")[0] in top.index],
        "focus": list(top.index),
    }
