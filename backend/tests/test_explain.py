"""The transparency layer: statements a reader needs in order not to misread a
ranking, none of which are safe to leave to the narrating model."""

import pandas as pd
import pytest

from app.agent.trace import reasoning_steps
from app.scoring.explain import NEAR_TIE_POINTS, method_notes
from app.scoring.profiles import DEFAULT_PROFILES
from app.scoring.score import score_airports

TERMINAL = DEFAULT_PROFILES["terminal_expansion"]["weights"]
MODERNIZATION = DEFAULT_PROFILES["general_modernization"]["weights"]


def _rendered(result) -> list[dict]:
    """The rows as the score node builds them for the UI."""
    return [
        {"iata": iata, "score": round(float(row["score"]), 1), "rank": int(row["rank"])}
        for iata, row in result.ranked.iterrows()
    ]


def _topics(notes) -> set[str]:
    return {n.topic for n in notes}


def test_universe_is_the_frame_before_the_subset(sample_metrics):
    """Reporting the subset size instead would describe a national standing as
    a rank within a filtered list."""
    result = score_airports(sample_metrics, TERMINAL, subset=["BOS"])
    assert result.universe_size == len(sample_metrics)
    assert len(result.ranked) == 1


def test_normalization_note_states_the_national_basis(sample_metrics):
    result = score_airports(sample_metrics, TERMINAL, subset=["BOS", "SNA"])
    note = next(n for n in method_notes(result, TERMINAL, _rendered(result))
                if n.topic == "Normalization")

    assert str(len(sample_metrics)) in note.detail
    assert "nationwide" in note.detail
    assert "not a position within this list" in note.detail


def test_near_tied_scores_are_reported_as_one_band(sample_metrics):
    tied = sample_metrics.copy()
    tied.loc["BOS"] = tied.loc["LAX"]

    result = score_airports(tied, TERMINAL)
    rendered = _rendered(result)
    assert rendered[0]["score"] - rendered[1]["score"] <= NEAR_TIE_POINTS

    note = next(n for n in method_notes(result, TERMINAL, rendered) if n.topic == "Ties")
    assert "LAX" in note.detail and "BOS" in note.detail
    assert "one band" in note.detail


def test_no_tie_note_when_the_field_is_well_separated(sample_metrics):
    result = score_airports(sample_metrics, TERMINAL)
    assert "Ties" not in _topics(method_notes(result, TERMINAL, _rendered(result)))


def test_thin_row_warning_names_the_gap_and_the_reweighting(sample_metrics):
    """The warning has to say which metric went missing and what the weights
    became, not just that coverage was incomplete."""
    thin = sample_metrics.copy()
    thin.loc["SNA", "operations_per_runway"] = pd.NA

    result = score_airports(thin, MODERNIZATION)
    warning = next(w for w in result.warnings if w.startswith("SNA:"))

    assert "operations_per_runway" in warning
    assert "25%->" in warning  # the missing weight, redistributed
    assert result.missing["SNA"] == ["operations_per_runway"]


def test_effective_weights_are_renormalized_only_where_data_is_missing(sample_metrics):
    thin = sample_metrics.copy()
    thin.loc["SNA", "operations_per_runway"] = pd.NA
    result = score_airports(thin, MODERNIZATION)

    assert result.effective_weights["LAX"] == pytest.approx(
        {m: w for m, w in MODERNIZATION.items() if w > 0}, abs=1e-4
    )
    sna = result.effective_weights["SNA"]
    assert "operations_per_runway" not in sna
    assert sum(sna.values()) == pytest.approx(1.0, abs=1e-4)


def test_coverage_note_flags_rows_that_are_not_comparable(sample_metrics):
    thin = sample_metrics.copy()
    thin.loc["SNA", "operations_per_runway"] = pd.NA
    result = score_airports(thin, MODERNIZATION)

    note = next(n for n in method_notes(result, MODERNIZATION, _rendered(result))
                if n.topic == "Coverage")
    assert "SNA" in note.detail
    assert "not strictly comparable" in note.detail


def test_no_coverage_note_when_every_shown_row_is_complete(sample_metrics):
    result = score_airports(sample_metrics, MODERNIZATION)
    assert "Coverage" not in _topics(method_notes(result, MODERNIZATION, _rendered(result)))


def test_installed_capacity_caveat_is_always_present(sample_metrics):
    for weights in DEFAULT_PROFILES.values():
        result = score_airports(sample_metrics, weights["weights"])
        notes = method_notes(result, weights["weights"], _rendered(result))
        assert any("installed capacity" in n.detail for n in notes)


def test_peak_hour_caveat_only_where_an_airfield_metric_is_weighted(sample_metrics):
    result = score_airports(sample_metrics, MODERNIZATION)
    with_airfield = method_notes(result, MODERNIZATION, _rendered(result))
    assert any("peak-hour" in n.detail for n in with_airfield)

    result = score_airports(sample_metrics, TERMINAL)
    without = method_notes(result, TERMINAL, _rendered(result))
    assert not any("peak-hour" in n.detail for n in without)


def test_no_notes_without_a_ranking_to_explain(sample_metrics):
    result = score_airports(sample_metrics, TERMINAL)
    assert method_notes(result, TERMINAL, []) == []


def test_reasoning_trace_carries_the_profile_rationale():
    steps = reasoning_steps(
        {
            "intent": "rank",
            "region": "New England",
            "profile_name": "terminal_expansion",
            "profile_rationale": "the question asks about gate and concourse capacity",
            "airports": ["BOS", "BDL", "PWM"],
            "scores": [{"iata": "BOS"}, {"iata": "BDL"}, {"iata": "PWM"}],
            "weights": TERMINAL,
        }
    )
    by_step = {s["step"]: s["detail"] for s in steps}

    assert "New England" in by_step["Read the question as"]
    assert "gate and concourse capacity" in by_step["Scored under the profile"]
    assert "3 airports matched" in by_step["Set the scope to"]
    assert "pax_per_departure 40%" in by_step["Weighted the metrics"]


def test_reasoning_trace_says_the_unshown_airports_were_still_scored():
    """"top 10 of 54" must not read as "44 were left out of the comparison"."""
    steps = reasoning_steps(
        {
            "intent": "rank",
            "region": "New England",
            "airports": [f"A{i}" for i in range(54)],
            "scores": [{"iata": f"A{i}"} for i in range(10)],
        }
    )
    scope = next(s["detail"] for s in steps if s["step"] == "Set the scope to")
    assert "54 airports matched" in scope and "top 10" in scope
    assert "not excluded" in scope


def test_reasoning_trace_marks_live_conditions_as_advisory():
    steps = reasoning_steps(
        {"intent": "rank", "live_conditions": [{"iata": "BOS"}], "weights": TERMINAL}
    )
    live = next(s["detail"] for s in steps if s["step"].startswith("Checked live"))
    assert "never enter the score" in live


def test_reasoning_trace_omits_steps_that_did_not_happen():
    steps = reasoning_steps({"intent": "chitchat"})
    assert [s["step"] for s in steps] == ["Read the question as"]
