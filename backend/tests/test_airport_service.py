import pytest

from app.services.region_service import resolve_region


def test_new_england_resolves_to_six_states():
    assert len(resolve_region("New England")) == 6


def test_unknown_region_returns_none():
    assert resolve_region("Middle Earth") is None


@pytest.mark.skip(reason="resolve not implemented")
def test_la_is_ambiguous():
    ...
