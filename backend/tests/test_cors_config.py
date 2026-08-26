import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.core.config import Settings


def test_explicit_production_cors_origins_are_parsed() -> None:
    config = Settings(
        _env_file=None,
        frontend_origin="https://blueashdigital.tech",
        cors_origins="https://blueashdigital.tech, https://www.blueashdigital.tech/",
    )

    assert config.allowed_cors_origins == [
        "https://blueashdigital.tech",
        "https://www.blueashdigital.tech",
    ]


def test_cors_origins_fall_back_to_frontend_origin() -> None:
    config = Settings(
        _env_file=None,
        frontend_origin="http://localhost:5173/",
        cors_origins=None,
    )

    assert config.allowed_cors_origins == ["http://localhost:5173"]


@pytest.mark.parametrize(
    "origin",
    [
        "https://blueashdigital.tech",
        "https://www.blueashdigital.tech",
    ],
)
def test_production_origins_pass_credentialed_cors_preflight(origin: str) -> None:
    config = Settings(
        _env_file=None,
        frontend_origin="https://blueashdigital.tech",
        cors_origins="https://blueashdigital.tech,https://www.blueashdigital.tech",
    )
    test_app = FastAPI()
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    response = TestClient(test_app).options(
        "/api/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"
