"""Default weight profiles.

These are seeds. Profiles live in Postgres and are editable from the frontend
dashboard; these values are inserted on first startup only.

Each profile encodes an investment thesis. Weights must sum to 1.0.

`description` is written for the LLM: it is injected into the intent prompt as
the selection criteria for that profile. Editing a description in the dashboard
changes how the agent chooses, with no code change.
"""

METRICS = [
    "pax_per_departure",
    "departures_per_runway",
    "enplanement_volume",
    "freight_share",
    "runway_pressure",
]

DEFAULT_PROFILES: dict[str, dict] = {
    "terminal_expansion": {
        "label": "Terminal Expansion",
        "description": (
            "Passenger terminal, gate, concourse or check-in capacity. Choose when "
            "the question is about moving more passengers through the building "
            "rather than more aircraft through the airfield."
        ),
        "weights": {
            "pax_per_departure": 0.30,
            "enplanement_volume": 0.30,
            "departures_per_runway": 0.20,
            "runway_pressure": 0.15,
            "freight_share": 0.05,
        },
    },
    "runway_capacity": {
        "label": "Runway Capacity",
        "description": (
            "Airfield capacity, congestion, delays, taxi times or aircraft movement "
            "throughput. Choose for questions about congestion, or about how many "
            "flights an airport can physically handle."
        ),
        "weights": {
            "departures_per_runway": 0.40,
            "runway_pressure": 0.30,
            "enplanement_volume": 0.15,
            "pax_per_departure": 0.10,
            "freight_share": 0.05,
        },
    },
    "cargo_facility": {
        "label": "Cargo Facility",
        "description": (
            "Freight and cargo handling infrastructure. Choose when the question "
            "concerns cargo, freight, air mail or logistics hubs rather than "
            "passenger traffic."
        ),
        "weights": {
            "freight_share": 0.45,
            "departures_per_runway": 0.20,
            "runway_pressure": 0.20,
            "enplanement_volume": 0.15,
            "pax_per_departure": 0.00,
        },
    },
    "general_modernization": {
        "label": "General Modernization",
        "description": (
            "Balanced view across passenger volume, throughput and airfield "
            "pressure. Choose when no more specific investment thesis fits the "
            "question."
        ),
        "weights": {
            "enplanement_volume": 0.25,
            "pax_per_departure": 0.20,
            "departures_per_runway": 0.20,
            "runway_pressure": 0.20,
            "freight_share": 0.15,
        },
    },
}

FALLBACK_PROFILE = "general_modernization"
