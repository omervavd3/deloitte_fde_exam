from app.agent.deps import Deps
from app.agent.state import AgentState
from app.scoring.score import score_airports

MAX_RESULTS = 10


async def score(deps: Deps, state: AgentState) -> dict:
    """Deterministic: normalize, weight, rank. Pure call into app.scoring."""
    metrics = deps.provider.get_metrics()
    subset = state.get("airports") or None

    result = score_airports(metrics, state["weights"], subset=subset)
    top = result.ranked.head(MAX_RESULTS)

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
        "warnings": state.get("warnings", [])
        + [w for w in result.warnings if w.split(":")[0] in top.index],
        "focus": list(top.index),
    }
