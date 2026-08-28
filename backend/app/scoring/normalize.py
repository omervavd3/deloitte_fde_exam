"""Percentile rank within peer group.

Percentile rank rather than z-score: a handful of very large hubs would
otherwise dominate the distribution and flatten differences elsewhere.
"""

import pandas as pd


def percentile_within_group(
    df: pd.DataFrame, metric: str, group_col: str
) -> pd.Series:
    """0-100 rank of `metric` within each `group_col`. NaN stays NaN."""
    return (
        df.groupby(group_col, observed=True)[metric]
        .rank(pct=True, na_option="keep")
        .mul(100)
    )


def coverage(df: pd.DataFrame, metrics: list[str]) -> pd.Series:
    """Fraction of scored metrics present per row, for flagging thin data."""
    available = [m for m in metrics if m in df.columns]
    if not available:
        return pd.Series(0.0, index=df.index)
    return df[available].notna().sum(axis=1) / len(available)
