"""Deterministic scoring. No LLM, no I/O, no network.

Every user-visible number originates here.
"""

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ScoreResult:
    ranked: pd.DataFrame
    breakdown: dict[str, dict[str, float]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def score_airports(
    metrics: pd.DataFrame,
    weights: dict[str, float],
    peer_group_col: str = "hub_tier",
) -> ScoreResult:
    """Normalize within peer group, apply weights, rank.

    Returns per-component point contributions so the ranking is explainable.
    """
    raise NotImplementedError
