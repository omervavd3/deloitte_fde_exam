import pandas as pd
import pytest

from app.scoring.glossary import GLOSSARY, glossary_for, metric_catalog
from app.scoring.profiles import (
    DEFAULT_PROFILES,
    METRICS,
    REDUNDANT_METRIC_PAIRS,
)
from app.scoring.score import score_airports


def test_default_profiles_sum_to_one():
    for name, spec in DEFAULT_PROFILES.items():
        assert abs(sum(spec["weights"].values()) - 1.0) < 1e-6, name


def test_default_profiles_use_known_metrics():
    for name, spec in DEFAULT_PROFILES.items():
        assert set(spec["weights"]) <= set(METRICS), name


def test_no_profile_weights_both_halves_of_a_redundant_pair():
    """Percentile-identical metrics add up instead of blending, so a profile
    weighting both reads as two signals and behaves as one."""
    for name, spec in DEFAULT_PROFILES.items():
        weighted = {m for m, w in spec["weights"].items() if w > 0}
        for a, b in REDUNDANT_METRIC_PAIRS:
            assert not {a, b} <= weighted, f"{name} weights both {a} and {b}"


def test_redundant_pairs_name_real_metrics():
    for pair in REDUNDANT_METRIC_PAIRS:
        assert set(pair) <= set(METRICS), pair


def test_percentile_identical_metrics_are_interchangeable(sample_metrics):
    split = score_airports(
        sample_metrics, {"departures_per_runway": 0.3, "runway_pressure": 0.3}
    )
    merged = score_airports(sample_metrics, {"departures_per_runway": 0.6})
    assert split.ranked["score"].equals(merged.ranked["score"])


def test_every_profile_has_a_description_for_the_llm():
    for name, spec in DEFAULT_PROFILES.items():
        assert spec["label"], name
        assert len(spec["description"]) > 40, name


def test_every_scored_metric_can_be_explained():
    """A metric a profile may weight is a metric narrate will have to name, so
    adding one to METRICS without a description has to fail here."""
    assert set(GLOSSARY) == set(METRICS)
    for metric, meaning in GLOSSARY.items():
        assert meaning.label, metric
        assert meaning.formula.endswith("."), metric
        assert len(meaning.means) > 40, metric


def test_glossary_describes_the_weighted_metrics_heaviest_first():
    described = glossary_for(DEFAULT_PROFILES["terminal_expansion"]["weights"])

    assert [d["metric"] for d in described] == [
        "pax_per_departure",
        "enplanement_volume",
        "load_factor",
    ]
    assert [d["weight"] for d in described] == sorted(
        (d["weight"] for d in described), reverse=True
    )
    assert all(d["label"] and d["formula"] and d["means"] for d in described)


def test_glossary_leaves_out_metrics_the_profile_does_not_weight():
    """Describing an unweighted metric would imply the ranking used it."""
    described = glossary_for({"freight_share": 1.0, "load_factor": 0.0})
    assert [d["metric"] for d in described] == ["freight_share"]


def test_catalog_serves_every_metric_in_the_order_profiles_list_them():
    """The dashboard renders straight from this, so it has to be complete and
    ordered here rather than sorted again at the other end."""
    catalog = metric_catalog()

    assert [m["metric"] for m in catalog["metrics"]] == METRICS
    assert catalog["redundant_pairs"] == [list(p) for p in REDUNDANT_METRIC_PAIRS]
    for described in catalog["metrics"]:
        assert described.keys() == {
            "metric", "label", "formula", "means", "needs_segment"
        }


def test_catalog_flags_the_metrics_that_need_the_optional_extract():
    """Without the T-100 Segment file these are NaN everywhere, and the
    dashboard has to say so before someone builds a profile on them."""
    flagged = {m["metric"] for m in metric_catalog()["metrics"] if m["needs_segment"]}

    assert flagged == {
        "load_factor",
        "long_haul_share",
        "international_share",
        "schedule_shortfall",
    }


def test_scores_are_reproducible(sample_metrics):
    weights = DEFAULT_PROFILES["terminal_expansion"]["weights"]
    a = score_airports(sample_metrics, weights)
    b = score_airports(sample_metrics, weights)
    assert a.ranked["score"].equals(b.ranked["score"])


def test_breakdown_sums_to_score(sample_metrics):
    weights = DEFAULT_PROFILES["general_modernization"]["weights"]
    result = score_airports(sample_metrics, weights)
    for iata, components in result.breakdown.items():
        assert sum(components.values()) == pytest.approx(
            result.ranked.loc[iata, "score"], abs=0.05
        )


def test_scores_stay_within_zero_to_one_hundred(sample_metrics):
    result = score_airports(sample_metrics, DEFAULT_PROFILES["runway_capacity"]["weights"])
    assert result.ranked["score"].between(0, 100).all()


def test_missing_metric_renormalizes_instead_of_dropping(sample_metrics):
    thin = sample_metrics.copy()
    thin.loc["SNA", "operations_per_runway"] = pd.NA
    result = score_airports(thin, DEFAULT_PROFILES["general_modernization"]["weights"])

    assert "SNA" in result.ranked.index
    assert result.ranked.loc["SNA", "score"] <= 100
    assert any("SNA" in w for w in result.warnings)
    assert "operations_per_runway" not in result.breakdown["SNA"]


def test_subset_filters_after_scoring(sample_metrics):
    weights = DEFAULT_PROFILES["terminal_expansion"]["weights"]
    full = score_airports(sample_metrics, weights)
    subset = score_airports(sample_metrics, weights, subset=["BOS", "SNA"])

    assert list(subset.ranked.index) == ["BOS", "SNA"] or list(
        subset.ranked.index
    ) == ["SNA", "BOS"]
    # Filtering changes rank position, never the score itself.
    for iata in subset.ranked.index:
        assert subset.ranked.loc[iata, "score"] == pytest.approx(
            full.ranked.loc[iata, "score"]
        )


def test_ranks_are_dense_and_ordered(sample_metrics):
    result = score_airports(sample_metrics, DEFAULT_PROFILES["cargo_facility"]["weights"])
    assert list(result.ranked["rank"]) == list(range(1, len(result.ranked) + 1))
    assert result.ranked["score"].is_monotonic_decreasing


def test_rejects_weights_with_no_usable_metric(sample_metrics):
    with pytest.raises(ValueError):
        score_airports(sample_metrics, {"nonexistent_metric": 1.0})


def test_large_hub_outranks_small_on_volume_weighted_profile(sample_metrics):
    result = score_airports(
        sample_metrics, DEFAULT_PROFILES["terminal_expansion"]["weights"]
    )
    order = list(result.ranked.index)
    assert order.index("LAX") < order.index("SNA")


def test_peer_group_is_opt_in(sample_metrics):
    """Grouping by tier is available but must not be the default."""
    global_ranked = score_airports(
        sample_metrics, DEFAULT_PROFILES["terminal_expansion"]["weights"]
    )
    tiered = score_airports(
        sample_metrics,
        DEFAULT_PROFILES["terminal_expansion"]["weights"],
        peer_group_col="hub_tier",
    )
    assert not global_ranked.ranked["score"].equals(tiered.ranked["score"])
