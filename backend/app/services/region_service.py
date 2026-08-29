"""Named places to ISO region codes, matching OurAirports `iso_region`.

Covers both multi-state regions and individual states. A state name must
resolve here, or it falls through to airport-name matching and "Oregon" finds
the two airports with "Oregon" in their title instead of the state's 14.
"""

REGIONS: dict[str, list[str]] = {
    "new england": ["US-ME", "US-NH", "US-VT", "US-MA", "US-RI", "US-CT"],
    "west coast": ["US-CA", "US-OR", "US-WA"],
    "southwest": ["US-AZ", "US-NM", "US-NV", "US-TX"],
    "midwest": ["US-IL", "US-IN", "US-IA", "US-KS", "US-MI", "US-MN",
                "US-MO", "US-NE", "US-ND", "US-OH", "US-SD", "US-WI"],
    "pacific northwest": ["US-WA", "US-OR", "US-ID"],
    "southeast": ["US-FL", "US-GA", "US-SC", "US-NC", "US-AL", "US-MS",
                  "US-TN", "US-KY"],
    "northeast": ["US-ME", "US-NH", "US-VT", "US-MA", "US-RI", "US-CT",
                  "US-NY", "US-NJ", "US-PA"],
    "mid-atlantic": ["US-NY", "US-NJ", "US-PA", "US-DE", "US-MD", "US-VA",
                     "US-DC", "US-WV"],
    "mountain west": ["US-MT", "US-ID", "US-WY", "US-CO", "US-UT", "US-NV"],
    "gulf coast": ["US-TX", "US-LA", "US-MS", "US-AL", "US-FL"],
    "alaska": ["US-AK"],
}

STATES: dict[str, str] = {
    "alabama": "US-AL", "alaska": "US-AK", "arizona": "US-AZ",
    "arkansas": "US-AR", "california": "US-CA", "colorado": "US-CO",
    "connecticut": "US-CT", "delaware": "US-DE", "florida": "US-FL",
    "georgia": "US-GA", "hawaii": "US-HI", "idaho": "US-ID",
    "illinois": "US-IL", "indiana": "US-IN", "iowa": "US-IA",
    "kansas": "US-KS", "kentucky": "US-KY", "louisiana": "US-LA",
    "maine": "US-ME", "maryland": "US-MD", "massachusetts": "US-MA",
    "michigan": "US-MI", "minnesota": "US-MN", "mississippi": "US-MS",
    "missouri": "US-MO", "montana": "US-MT", "nebraska": "US-NE",
    "nevada": "US-NV", "new hampshire": "US-NH", "new jersey": "US-NJ",
    "new mexico": "US-NM", "new york": "US-NY", "north carolina": "US-NC",
    "north dakota": "US-ND", "ohio": "US-OH", "oklahoma": "US-OK",
    "oregon": "US-OR", "pennsylvania": "US-PA", "rhode island": "US-RI",
    "south carolina": "US-SC", "south dakota": "US-SD", "tennessee": "US-TN",
    "texas": "US-TX", "utah": "US-UT", "vermont": "US-VT",
    "virginia": "US-VA", "washington": "US-WA", "west virginia": "US-WV",
    "wisconsin": "US-WI", "wyoming": "US-WY",
    "district of columbia": "US-DC", "washington dc": "US-DC",
    "washington, d.c.": "US-DC", "puerto rico": "US-PR",
}

# "New York" and "Washington" are also metro areas with several airports each.
# Those readings are handled by AMBIGUOUS_NAMES in airport_service; a bare
# state name reaching here means the caller already decided it is a scope.
_PREFIXES = ("the ", "state of ", "us ", "u.s. ")


def _key(text: str) -> str:
    key = text.strip().lower().rstrip(".")
    for prefix in _PREFIXES:
        if key.startswith(prefix):
            key = key[len(prefix) :]
    return key.removesuffix(" state").removesuffix(" region").strip()


def resolve_region(text: str) -> list[str] | None:
    """ISO region codes for a state or named region, or None if unrecognized."""
    key = _key(text)
    if key in REGIONS:
        return REGIONS[key]
    if key in STATES:
        return [STATES[key]]
    return None


def is_place(text: str) -> bool:
    """True when this string names a scope rather than an airport."""
    return resolve_region(text) is not None
