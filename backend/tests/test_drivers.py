"""Score attribution: the figures that let narrate say why, not just what.

Each assertion here exists because the model is forbidden to compute, so
anything it cannot read off the payload it cannot say at all.
"""

import pandas as pd
import pytest

from app.scoring.drivers import (
    DECIDING_POINTS,
    MAX_ATTRIBUTED_ROWS,
    WEAK_PERCENTILE_BELOW,
    score_drivers,
)
from app.scoring.explain import NEAR_TIE_POINTS
from app.scoring.profiles import DEFAULT_PROFILES
from app.scoring.score import score_airports

MODERNIZATION = DEFAULT_PROFILES["general_modernization"]["weights"]
TERMINAL = DEFAULT_PROFILES["terminal_expansion"]["weights"]


def _rendered(result, weights) -> list[dict]:
    """The rows as the score node builds them for the UI."""
    return [
        {
            "iata": iata,
            "score": round(float(row["score"]), 1),
            "rank": int(row["rank"]),
            "metrics": {
                m: (None if row[m] != row[m] else round(float(row[m]), 4))
                for m in weights
                if m in row.index
            },
        }
        for iata, row in result.ranked.iterrows()
    ]


def _drivers(metrics, weights):
    result = score_airports(metrics, weights)
    return {d.iata: d for d in score_drivers(result, _rendered(result, weights))}


def test_percentiles_survive_scoring(sample_metrics):
    """Points are percentile times weight, so the standing has to be carried
    out separately or it cannot be recovered without dividing."""
    result = score_airports(sample_metrics, MODERNIZATION)

    assert set(result.percentiles) == set(result.ranked.index)
    for standings in result.percentiles.values():
        assert all(0 <= p <= 100 for p in standings.values())


def test_component_points_reconcile_with_the_score(sample_metrics):
    for driver in _drivers(sample_metrics, MODERNIZATION).values():
        assert sum(c.points for c in driver.components) == pytest.approx(
            driver.score, abs=0.05
        )


def test_each_component_carries_its_standing_and_its_raw_value(sample_metrics):
    """A percentile without the figure behind it is not an explanation."""
    lax = _drivers(sample_metrics, MODERNIZATION)["LAX"]
    pax = next(c for c in lax.components if c.metric == "pax_per_departure")

    assert pax.value == pytest.approx(127.5)
    assert pax.percentile == 100.0
    assert pax.weight == pytest.approx(MODERNIZATION["pax_per_departure"])
    assert pax.points == pytest.approx(pax.percentile * pax.weight, abs=0.05)


def test_every_component_carries_the_ceiling_its_points_are_read_against(
    sample_metrics,
):
    """"37.8 points" has no scale a reader can judge; "37.8 of a possible 40"
    does, and narrate may not multiply the weight out to get there."""
    for driver in _drivers(sample_metrics, MODERNIZATION).values():
        for component in driver.components:
            assert component.max_points == pytest.approx(component.weight * 100, abs=0.05)
            assert component.points <= component.max_points + 0.05


def test_components_are_ordered_by_what_built_the_score(sample_metrics):
    for driver in _drivers(sample_metrics, MODERNIZATION).values():
        points = [c.points for c in driver.components]
        assert points == sorted(points, reverse=True)
        assert driver.carried_by == driver.components[0].metric


def test_a_weak_weighted_metric_is_named(sample_metrics):
    """A score built on two strong metrics and one poor one reads differently
    from an evenly strong one, and only this field separates them."""
    sna = _drivers(sample_metrics, MODERNIZATION)["SNA"]
    weakest = min(sna.components, key=lambda c: c.percentile)

    assert weakest.percentile < WEAK_PERCENTILE_BELOW
    assert sna.held_back_by == weakest.metric


def test_no_weak_metric_named_when_the_airport_is_strong_throughout(sample_metrics):
    lax = _drivers(sample_metrics, MODERNIZATION)["LAX"]
    assert min(c.percentile for c in lax.components) >= WEAK_PERCENTILE_BELOW
    assert lax.held_back_by is None


def test_separation_names_the_metrics_that_decided_it(sample_metrics):
    result = score_airports(sample_metrics, MODERNIZATION)
    scores = _rendered(result, MODERNIZATION)
    drivers = score_drivers(result, scores)

    leader, runner_up = drivers[0], drivers[1]
    assert leader.ahead_of.iata == runner_up.iata
    assert leader.ahead_of.gap == pytest.approx(leader.score - runner_up.score, abs=0.05)
    assert leader.ahead_of.differs_by
    assert all(
        abs(d["points_ahead"]) >= DECIDING_POINTS for d in leader.ahead_of.differs_by
    )


def test_separation_keeps_the_sign_so_a_reversal_is_visible(sample_metrics):
    """BOS outranks SNA while SNA works its runways much harder. Stated
    unsigned, that reads as BOS being ahead on everything."""
    result = score_airports(sample_metrics, MODERNIZATION)
    scores = _rendered(result, MODERNIZATION)
    by_iata = {d.iata: d for d in score_drivers(result, scores)}

    bos = by_iata["BOS"]
    assert bos.ahead_of.iata == "SNA"
    operations = next(
        d for d in bos.ahead_of.differs_by if d["metric"] == "operations_per_runway"
    )
    assert operations["points_ahead"] < 0


def test_the_last_row_is_separated_from_nothing(sample_metrics):
    result = score_airports(sample_metrics, MODERNIZATION)
    drivers = score_drivers(result, _rendered(result, MODERNIZATION))
    assert drivers[-1].ahead_of is None
    assert drivers[-1].level_with is None


def test_a_gap_inside_the_tie_band_is_not_offered_as_an_ordering(sample_metrics):
    """The payload must not hand narrate an "ahead_of" for a pair the Ties note
    calls unresolvable - prose alone did not stop it being narrated as one."""
    tied = sample_metrics.copy()
    tied.loc["BOS"] = tied.loc["LAX"]

    result = score_airports(tied, TERMINAL)
    scores = _rendered(result, TERMINAL)
    leader = score_drivers(result, scores)[0]

    assert leader.ahead_of is None
    assert leader.level_with is not None
    assert leader.level_with.gap < NEAR_TIE_POINTS


def test_a_resolvable_gap_is_still_offered_as_an_ordering(sample_metrics):
    """The guard must not swallow separations the method can genuinely resolve."""
    leader = score_drivers(
        score_airports(sample_metrics, MODERNIZATION),
        _rendered(score_airports(sample_metrics, MODERNIZATION), MODERNIZATION),
    )[0]

    assert leader.ahead_of is not None
    assert leader.level_with is None
    assert leader.ahead_of.gap >= NEAR_TIE_POINTS


def test_the_two_separation_fields_are_mutually_exclusive(sample_metrics):
    for weights in (MODERNIZATION, TERMINAL):
        result = score_airports(sample_metrics, weights)
        for driver in score_drivers(result, _rendered(result, weights)):
            assert not (driver.ahead_of and driver.level_with)


def test_a_thin_row_is_attributed_on_the_metrics_it_actually_had(sample_metrics):
    """The renormalized blend, not the profile's nominal one."""
    thin = sample_metrics.copy()
    thin.loc["SNA", "operations_per_runway"] = pd.NA

    sna = _drivers(thin, MODERNIZATION)["SNA"]
    metrics = {c.metric for c in sna.components}

    assert "operations_per_runway" not in metrics
    assert sum(c.weight for c in sna.components) == pytest.approx(1.0, abs=1e-3)
    assert sum(c.points for c in sna.components) == pytest.approx(sna.score, abs=0.05)


def test_nothing_to_attribute_without_a_ranking(sample_metrics):
    result = score_airports(sample_metrics, TERMINAL)
    assert score_drivers(result, []) == []


def test_attribution_stops_at_the_cap(sample_metrics):
    """A ranking can run to every airport in a state; the payload must not."""
    result = score_airports(sample_metrics, MODERNIZATION)
    rendered = _rendered(result, MODERNIZATION)
    many = [
        {**rendered[i % len(rendered)], "iata": f"A{i}", "rank": i + 1}
        for i in range(MAX_ATTRIBUTED_ROWS + 5)
    ]

    drivers = score_drivers(result, many)
    assert len(drivers) == MAX_ATTRIBUTED_ROWS


def test_the_last_attributed_row_is_separated_from_a_real_neighbour(sample_metrics):
    """The cut is in the attribution, not in the ranking, so the final row is
    still compared against the airport that actually follows it."""
    result = score_airports(sample_metrics, MODERNIZATION)
    rendered = _rendered(result, MODERNIZATION)
    many = [
        {**rendered[i % len(rendered)], "iata": f"A{i}", "rank": i + 1}
        for i in range(MAX_ATTRIBUTED_ROWS + 5)
    ]

    last = score_drivers(result, many)[-1]
    assert last.ahead_of is not None
    assert last.ahead_of.iata == f"A{MAX_ATTRIBUTED_ROWS}"
