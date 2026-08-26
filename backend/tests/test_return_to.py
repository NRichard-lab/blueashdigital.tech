import pytest

from app.core.redirects import normalize_return_to


ORIGIN = "https://blueashdigital.tech"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("/OpportunityRadar", "/OpportunityRadar"),
        ("/OpportunityRadar/jobs", "/OpportunityRadar/jobs"),
        ("/OpportunityRadar/utilities?tab=email", "/OpportunityRadar/utilities?tab=email"),
        ("https://blueashdigital.tech/OpportunityRadar/jobs", "/OpportunityRadar/jobs"),
    ],
)
def test_accepts_canonical_opportunity_radar_destinations(value: str, expected: str) -> None:
    assert normalize_return_to(value, site_origin=ORIGIN) == expected


@pytest.mark.parametrize(
    "value",
    [
        "https://evil.example.com",
        "//evil.example.com/OpportunityRadar",
        "javascript:alert(1)",
        "/opportunityradar",
        "/OpportunityRadar%2f%2fevil.example.com",
        "/OpportunityRadar\\@evil.example.com",
        "https%3A%2F%2Fevil.example.com",
        "/OpportunityRadar\nLocation:https://evil.example.com",
    ],
)
def test_rejects_external_malformed_or_noncanonical_destinations(value: str) -> None:
    assert normalize_return_to(value, site_origin=ORIGIN) is None


def test_invalid_return_to_does_not_raise() -> None:
    assert normalize_return_to("not a url", site_origin=ORIGIN) is None
    assert normalize_return_to(None, site_origin=ORIGIN) is None
