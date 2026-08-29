from app.agent.deps import Deps
from app.agent.state import AgentState
from app.services.profile_service import resolve_weights


async def load_metrics(deps: Deps, state: AgentState) -> dict:
    """Deterministic: resolve the weight set for this turn."""
    name, weights, overridden = await resolve_weights(
        deps.pool, state.get("profile_name"), state.get("weight_overrides")
    )
    return {
        "profile_name": name,
        "weights": weights,
        "assumptions": state.get("assumptions", []) + [
            f"weight profile: {name}" + (" (overridden)" if overridden else ""),
            "weights: "
            + ", ".join(f"{k} {v:.2f}" for k, v in sorted(weights.items()) if v > 0),
        ],
    }
