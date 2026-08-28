import pytest

from app.scoring.profiles import DEFAULT_PROFILES, METRICS


def test_default_profiles_sum_to_one():
    for name, weights in DEFAULT_PROFILES.items():
        assert abs(sum(weights.values()) - 1.0) < 1e-6, name


def test_default_profiles_use_known_metrics():
    for name, weights in DEFAULT_PROFILES.items():
        assert set(weights) <= set(METRICS), name


@pytest.mark.skip(reason="score_airports not implemented")
def test_scores_are_reproducible(sample_metrics):
    ...


@pytest.mark.skip(reason="score_airports not implemented")
def test_breakdown_sums_to_score(sample_metrics):
    ...
