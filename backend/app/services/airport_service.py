"""Turns user text into airport codes.

Ambiguity is surfaced, never guessed: "LA" must not silently become LAX.
"""

import pandas as pd

from app.schemas.airport import AirportResolution

AMBIGUOUS_NAMES: dict[str, list[str]] = {
    "la": ["LAX", "BUR", "LGB", "ONT", "SNA"],
    "los angeles": ["LAX", "BUR", "LGB", "ONT"],
    "new york": ["JFK", "LGA", "EWR"],
    "washington": ["DCA", "IAD", "BWI"],
    "chicago": ["ORD", "MDW"],
    "bay area": ["SFO", "OAK", "SJC"],
}


def resolve(entities: list[str], airports: pd.DataFrame) -> AirportResolution:
    raise NotImplementedError
