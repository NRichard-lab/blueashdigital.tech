import pytest

from app.core.redirects import normalize_radar_return_path, normalize_return_to


RADAR_ORIGIN = "https://radar.blueashdigital.tech"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("/", f"{RADAR_ORIGIN}/"),
        ("/jobs", f"{RADAR_ORIGIN}/jobs"),
        ("/jobs?view=active", f"{RADAR_ORIGIN}/jobs?view=active"),
        (f"{RADAR_ORIGIN}/jobs", f"{RADAR_ORIGIN}/jobs"),
    ],
)
def test_accepts_exact_radar_ui_destinations(value: str, expected: str) -> None:
    assert normalize_return_to(value, radar_origin=RADAR_ORIGIN) == expected


@pytest.mark.parametrize(
    "value",
    [
        "http://radar.blueashdigital.tech/",
        "https://evil.example.com/",
        "https://radar.blueashdigital.tech.evil.example.com/",
        "https://user@radar.blueashdigital.tech/",
        "//radar.blueashdigital.tech/",
        "javascript:alert(1)",
        "/api",
        "/api/auth/start",
        "/x/../api/auth/start",
        "/./jobs",
        "/%2e%2e/api",
        "/%252e%252e/api",
        "/jobs%2f%2fexample.com",
        "/jobs\\@evil.example.com",
        "/jobs\nLocation:https://evil.example.com",
        "/jobs\x7f",
        "https://[::1",
        "https://radar.blueashdigital.tech]:443/",
    ],
)
def test_rejects_external_api_malformed_or_ambiguous_destinations(value: str) -> None:
    assert normalize_return_to(value, radar_origin=RADAR_ORIGIN) is None


@pytest.mark.parametrize("value", ["/", "/jobs", "/jobs?tab=active"])
def test_accepts_safe_local_radar_return_paths(value: str) -> None:
    assert normalize_radar_return_path(value) == value


def test_invalid_return_to_is_total() -> None:
    assert normalize_return_to("not a url", radar_origin=RADAR_ORIGIN) is None
    assert normalize_return_to(None, radar_origin=RADAR_ORIGIN) is None
