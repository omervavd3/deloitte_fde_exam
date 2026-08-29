"""Turns user text into airport codes.

Ambiguity is surfaced, never guessed: "LA" must not silently become LAX.
"""

import pandas as pd

from app.schemas.airport import AirportResolution

AMBIGUOUS_NAMES: dict[str, list[str]] = {
    "la": ["LAX", "BUR", "LGB", "ONT", "SNA"],
    "los angeles": ["LAX", "BUR", "LGB", "ONT"],
    "new york": ["JFK", "LGA", "EWR"],
    "nyc": ["JFK", "LGA", "EWR"],
    "washington": ["DCA", "IAD", "BWI"],
    "chicago": ["ORD", "MDW"],
    "bay area": ["SFO", "OAK", "SJC"],
    "dallas": ["DFW", "DAL"],
    "houston": ["IAH", "HOU"],
}


def resolve(entities: list[str], airports: pd.DataFrame) -> AirportResolution:
    resolved: list[str] = []
    ambiguous: dict[str, list[str]] = {}
    unresolved: list[str] = []

    municipality = airports["municipality"].fillna("").str.lower()
    name = airports["name"].fillna("").str.lower()

    for raw in entities:
        text = raw.strip()
        key = text.lower()

        if text.upper() in airports.index:
            resolved.append(text.upper())
            continue

        if key in AMBIGUOUS_NAMES:
            options = [c for c in AMBIGUOUS_NAMES[key] if c in airports.index]
            if len(options) == 1:
                resolved.append(options[0])
            elif options:
                ambiguous[text] = options
            else:
                unresolved.append(text)
            continue

        hits = airports.index[municipality == key].tolist()
        if not hits:
            # A partial name - "Santa" - matches both cities and airport titles,
            # and either can be the better candidate.
            partial = municipality.str.contains(key, regex=False) | name.str.contains(
                key, regex=False
            )
            hits = airports.index[partial].tolist()

        if len(hits) == 1:
            resolved.append(hits[0])
        elif len(hits) > 1:
            # Prefer the busiest; surface the rest only if they are comparable.
            ranked = airports.loc[hits].sort_values("enplanement_volume", ascending=False)
            ambiguous[text] = ranked.index[:5].tolist()
        else:
            unresolved.append(text)

    return AirportResolution(
        resolved=list(dict.fromkeys(resolved)),
        ambiguous=ambiguous,
        unresolved=unresolved,
    )
