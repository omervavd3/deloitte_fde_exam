"""Percentile rank within peer group.

Percentile rank rather than z-score: a handful of very large hubs would
otherwise dominate the distribution and flatten differences elsewhere.
"""

import pandas as pd


def percentile_within_group(
    df: pd.DataFrame, metric: str, group_col: str
) -> pd.Series:
    """0-100 rank of `metric` within each `group_col`. NaN stays NaN."""
    raise NotImplementedError


def coverage(df: pd.DataFrame, metrics: list[str]) -> pd.Series:
    """Fraction of scored metrics present per row, for flagging thin data."""
    raise NotImplementedError
