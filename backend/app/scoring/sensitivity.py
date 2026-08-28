"""Weight sensitivity check.

Answers whether a ranking is driven by the data or by the chosen weights.
"""

import pandas as pd


def top_n_stability(
    metrics: pd.DataFrame,
    weights: dict[str, float],
    n: int = 5,
    jitter: float = 0.2,
    trials: int = 100,
) -> dict[str, float]:
    """Share of perturbed runs in which each airport stays in the top n."""
    raise NotImplementedError
