"""Intent classification eval set.

Small held-out set mapping questions to the profile they should select.
Mirrors the LangSmith dataset.
"""

import pytest

CASES = [
    ("Which airports in New England are strong candidates for terminal expansion?",
     "rank", "terminal_expansion"),
    ("Compare LA and Santa Ana airport congestion levels.",
     "compare", "runway_capacity"),
    ("What is the percentage of long haul flights out of Anchorage airport?",
     "metric", "general_modernization"),
    ("What is the unmet flight demand in SFO airport and why?",
     "explain", "runway_capacity"),
    ("How much would a new terminal at BOS cost to build?",
     "out_of_scope", "general_modernization"),
    ("Which cargo hubs need facility upgrades?",
     "rank", "cargo_facility"),
]


@pytest.mark.skip(reason="parse_intent not implemented")
@pytest.mark.parametrize("question,intent,profile", CASES)
def test_intent_classification(question, intent, profile):
    ...
