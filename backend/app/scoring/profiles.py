"""Default weight profiles.

These are seeds. Profiles are stored in Postgres and editable from the
frontend dashboard; these values are inserted on first startup only.

Each profile encodes an investment thesis. Weights must sum to 1.0.
"""

METRICS = [
    "pax_per_departure",
    "departures_per_runway",
    "enplanement_volume",
    "freight_share",
    "runway_pressure",
]

DEFAULT_PROFILES: dict[str, dict[str, float]] = {
    "terminal_expansion": {
        "pax_per_departure": 0.30,
        "enplanement_volume": 0.30,
        "departures_per_runway": 0.20,
        "runway_pressure": 0.15,
        "freight_share": 0.05,
    },
    "runway_capacity": {
        "departures_per_runway": 0.40,
        "runway_pressure": 0.30,
        "enplanement_volume": 0.15,
        "pax_per_departure": 0.10,
        "freight_share": 0.05,
    },
    "cargo_facility": {
        "freight_share": 0.45,
        "departures_per_runway": 0.20,
        "runway_pressure": 0.20,
        "enplanement_volume": 0.15,
        "pax_per_departure": 0.00,
    },
    "general_modernization": {
        "enplanement_volume": 0.25,
        "pax_per_departure": 0.20,
        "departures_per_runway": 0.20,
        "runway_pressure": 0.20,
        "freight_share": 0.15,
    },
}

FALLBACK_PROFILE = "general_modernization"
