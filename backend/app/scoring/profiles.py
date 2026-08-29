"""Default weight profiles.

These are seeds. Profiles live in Postgres and are editable from the frontend
dashboard; these values are inserted on first startup only.

Each profile encodes an investment thesis. Weights must sum to 1.0.

`description` is written for the LLM: it is injected into the intent prompt as
the selection criteria for that profile. Editing a description in the dashboard
changes how the agent chooses, with no code change.

Weights are tuned so that profiles return *different* airports, not just
different-sounding theses. Measured on the live frame as top-25 overlap between
every pair, the worst pair was 92% - terminal_expansion and runway_capacity, two
opposite theses returning nearly the same list. Two causes, both fixed here:
weighting a redundant metric pair (see REDUNDANT_METRIC_PAIRS) and loading
`enplanement_volume` in every profile, which correlates 0.89 with the airfield
metrics and 0.78 with pax_per_departure, so size drowned out the thesis. The
worst pair is now 72%.

That 72% is a floor imposed by the data, not slack left in the tuning. Almost
every metric here scales with airport size; the genuinely independent axes are
freight_share, mail_share, the two international shares, and schedule_shortfall.
A new profile that does not lean on one of those will return the big hubs again
whatever its weights say - verify a new thesis by its ranking, not its wording.
"""

# Every metric a profile may weight. Each must read "higher means more
# investment need", since scoring percentiles them and rewards the high end.
METRICS = [
    "pax_per_departure",
    "departures_per_runway",
    "enplanement_volume",
    "freight_share",
    "runway_pressure",
    # Airfield loading counted in both directions and divided by runways long
    # enough for scheduled jets. Strictly better than the two above, but kept
    # beside them rather than replacing them: swapping the denominator would
    # move every score a saved profile has already produced.
    "operations_per_runway",
    "airfield_saturation",
    "mail_share",
    # From the optional T-100 Segment extract. NaN where the extract does not
    # cover an airport; scoring renormalizes the remaining weights and flags
    # the row, so a profile using these still scores every airport.
    "load_factor",
    "long_haul_share",
    "international_share",
    "schedule_shortfall",
]

# Metrics that are monotone transforms of each other, so percentile-identical.
# `runway_pressure` is `departures_per_runway` over a fixed ceiling, clipped at
# 1 - but no US airport reaches the ceiling, so the clip never binds and the
# rank order is the same. Under percentile scoring w1*p + w2*p == (w1+w2)*p, so
# weighting both silently concentrates a profile on one signal instead of
# blending two: `runway_capacity` used to put 70% of its weight here while
# reading as 40/30. Both stay weightable - the clipped form is the readable one
# to display - but no default profile may weight both, and the dashboard warns.
REDUNDANT_METRIC_PAIRS = [
    ("departures_per_runway", "runway_pressure"),
    ("operations_per_runway", "airfield_saturation"),
]

DEFAULT_PROFILES: dict[str, dict] = {
    "terminal_expansion": {
        "label": "Terminal Expansion",
        "description": (
            "Passenger terminal, gate, concourse or check-in capacity. Choose when "
            "the question is about moving more passengers through the building "
            "rather than more aircraft through the airfield."
        ),
        # load_factor comes from the optional T-100 Segment extract. It carries
        # weight here because it is the only signal that separates a crowded
        # terminal from a merely large one; without the extract this falls back
        # to passenger size alone and converges on general_modernization.
        "weights": {
            "pax_per_departure": 0.40,
            "enplanement_volume": 0.30,
            "load_factor": 0.30,
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
            "operations_per_runway": 0.60,
            "pax_per_departure": 0.20,
            "enplanement_volume": 0.20,
        },
    },
    "cargo_facility": {
        "label": "Cargo Facility",
        "description": (
            "Freight and cargo handling infrastructure: warehousing, ramp and "
            "logistics hubs. Choose when the question concerns cargo or freight "
            "rather than passenger traffic. For postal and air-mail questions "
            "specifically, prefer air_mail_hub."
        ),
        "weights": {
            "freight_share": 0.50,
            "operations_per_runway": 0.25,
            "enplanement_volume": 0.25,
        },
    },
    "air_mail_hub": {
        "label": "Air Mail Hub",
        "description": (
            "Postal and air-mail infrastructure: mail docks, sorting facilities "
            "and the apron serving them. Choose when the question is about mail, "
            "postal service, or communities that depend on air delivery for "
            "goods. Distinct from cargo_facility, which is about general "
            "freight: this one surfaces the Alaska bypass-mail network, where "
            "mail rather than freight is the reason the airport exists."
        ),
        "weights": {
            "mail_share": 0.45,
            "freight_share": 0.20,
            "operations_per_runway": 0.20,
            "enplanement_volume": 0.15,
        },
    },
    "international_gateway": {
        "label": "International Gateway",
        "description": (
            "International or long-haul passenger facilities: customs and border "
            "halls, widebody gates, international arrivals. Choose when the question "
            "is about overseas or long-distance service rather than domestic traffic. "
            "Needs the T-100 Segment extract."
        ),
        "weights": {
            "international_share": 0.40,
            "long_haul_share": 0.30,
            "pax_per_departure": 0.15,
            "enplanement_volume": 0.15,
        },
    },
    "capacity_relief": {
        "label": "Capacity Relief",
        "description": (
            "Airports straining against the capacity they already have: aircraft "
            "flying full, scheduled service that does not operate, pressure on the "
            "airfield. Choose for questions about unmet demand, constraint or "
            "reliability rather than raw size. Needs the T-100 Segment extract."
        ),
        "weights": {
            "schedule_shortfall": 0.40,
            "load_factor": 0.35,
            "operations_per_runway": 0.25,
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
            "enplanement_volume": 0.30,
            "pax_per_departure": 0.25,
            "operations_per_runway": 0.25,
            "freight_share": 0.20,
        },
    },
}

FALLBACK_PROFILE = "general_modernization"
