"""Named regions to ISO region codes, matching OurAirports `iso_region`."""

REGIONS: dict[str, list[str]] = {
    "new england": ["US-ME", "US-NH", "US-VT", "US-MA", "US-RI", "US-CT"],
    "west coast": ["US-CA", "US-OR", "US-WA"],
    "southwest": ["US-AZ", "US-NM", "US-NV", "US-TX"],
    "midwest": ["US-IL", "US-IN", "US-IA", "US-KS", "US-MI", "US-MN",
                "US-MO", "US-NE", "US-ND", "US-OH", "US-SD", "US-WI"],
    "pacific northwest": ["US-WA", "US-OR", "US-ID"],
    "southeast": ["US-FL", "US-GA", "US-SC", "US-NC", "US-AL", "US-MS",
                  "US-TN", "US-KY"],
    "alaska": ["US-AK"],
}


def resolve_region(text: str) -> list[str] | None:
    """ISO region codes for a named region, or None if unrecognized."""
    return REGIONS.get(text.strip().lower())
