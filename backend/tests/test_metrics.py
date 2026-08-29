"""Metric derivation. Hand-built frames only; never touches the network."""

import numpy as np
import pandas as pd
import pytest

from app.data import metrics


def _frames(runway_kwargs: dict | None = None, **t100_overrides):
    """One airport, KTST/TST, with easily checked numbers."""
    t100 = pd.DataFrame([{
        "iata": "TST", "year": 2024, "enplanements": 1_000_000,
        "passengers": 2_000_000, "departures": 20_000, "arrivals": 20_000,
        "freight": 1_000_000, "mail": 0,
        **t100_overrides,
    }])
    airports = pd.DataFrame([{
        "ident": "KTST", "iata": "TST", "type": "large_airport", "name": "Test",
        "municipality": "Test", "iso_region": "US-XX",
        "latitude_deg": 0.0, "longitude_deg": 0.0,
    }])
    runways = pd.DataFrame([{
        "ident": "KTST", "runway_count": 4, "air_carrier_runway_count": 2,
        "longest_runway_ft": 11_000, **(runway_kwargs or {}),
    }])
    return t100, airports, runways


def test_operations_count_both_directions():
    df = metrics.build(*_frames())
    # (20,000 departures + 20,000 arrivals) / 2 usable runways
    assert df.loc["TST", "operations_per_runway"] == pytest.approx(20_000)
    # ...against the one-directional metric, over all four runways.
    assert df.loc["TST", "departures_per_runway"] == pytest.approx(5_000)


def test_usable_runways_ignores_strips_too_short_for_jets():
    df = metrics.build(*_frames())
    assert df.loc["TST", "usable_runway_count"] == 2
    assert df.loc["TST", "runway_count"] == 4


def test_falls_back_to_every_runway_when_none_are_air_carrier():
    """A field with only short runways still flies the traffic T-100 reports."""
    df = metrics.build(*_frames({"air_carrier_runway_count": 0}))
    assert df.loc["TST", "usable_runway_count"] == 4
    assert df.loc["TST", "operations_per_runway"] == pytest.approx(10_000)


def test_falls_back_when_the_column_is_absent_entirely():
    t100, airports, runways = _frames()
    df = metrics.build(t100, airports, runways.drop(columns=["air_carrier_runway_count"]))
    assert df.loc["TST", "usable_runway_count"] == 4


def test_saturation_is_a_share_of_the_operations_ceiling():
    df = metrics.build(*_frames())
    expected = 20_000 / metrics.RUNWAY_OPERATIONS_CEILING
    assert df.loc["TST", "airfield_saturation"] == pytest.approx(expected)


def test_saturation_clips_at_one():
    df = metrics.build(*_frames(departures=500_000, arrivals=500_000))
    assert df.loc["TST", "airfield_saturation"] == 1.0


def test_missing_arrivals_leaves_the_metric_missing_not_halved():
    t100, airports, runways = _frames()
    df = metrics.build(t100.drop(columns=["arrivals"]), airports, runways)
    assert np.isnan(df.loc["TST", "operations_per_runway"])
    # The one-directional metric is unaffected, so the airport still scores.
    assert df.loc["TST", "departures_per_runway"] == pytest.approx(5_000)


def test_no_runway_data_leaves_airfield_metrics_missing():
    t100, airports, _ = _frames()
    runways = pd.DataFrame(columns=["ident", "runway_count",
                                    "air_carrier_runway_count", "longest_runway_ft"])
    df = metrics.build(t100, airports, runways)
    assert np.isnan(df.loc["TST", "operations_per_runway"])
    assert np.isnan(df.loc["TST", "departures_per_runway"])


def test_mail_share_is_mail_against_all_cargo():
    df = metrics.build(*_frames(mail=3_000_000, freight=1_000_000))
    assert df.loc["TST", "mail_share"] == pytest.approx(0.75)


def test_zero_mail_beside_real_freight_is_a_true_zero():
    """Not missing data: that airport genuinely handles no mail."""
    df = metrics.build(*_frames(mail=0, freight=1_000_000))
    assert df.loc["TST", "mail_share"] == 0.0


def test_mail_share_is_dropped_below_the_volume_floor():
    """A near-total mail ratio on a few thousand pounds is noise, not a hub."""
    df = metrics.build(*_frames(mail=10_408, freight=154))
    assert np.isnan(df.loc["TST", "mail_share"])


def test_mail_share_survives_at_the_volume_floor():
    df = metrics.build(*_frames(mail=metrics.MAIL_SHARE_MIN_LB, freight=0))
    assert df.loc["TST", "mail_share"] == pytest.approx(1.0)


def test_no_cargo_at_all_leaves_mail_share_missing():
    df = metrics.build(*_frames(mail=0, freight=0))
    assert np.isnan(df.loc["TST", "mail_share"])


def test_existing_metrics_are_unchanged_by_the_additions():
    """The new pair must not move a score any saved profile already produced."""
    df = metrics.build(*_frames())
    assert df.loc["TST", "pax_per_departure"] == pytest.approx(100.0)
    assert df.loc["TST", "runway_pressure"] == pytest.approx(
        5_000 / metrics.RUNWAY_DEPARTURE_CEILING
    )
    freight = 1_000_000
    assert df.loc["TST", "freight_share"] == pytest.approx(
        freight / (freight + 2_000_000 * metrics.PAX_WEIGHT_LB)
    )
