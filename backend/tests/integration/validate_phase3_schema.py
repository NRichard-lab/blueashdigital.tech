from __future__ import annotations

import argparse
import json
import os
from collections.abc import Iterable

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Inspector, make_url

from app.core.config import settings


REVISION_0005 = "20260825_0005"
REVISION_0006 = "20260827_0006"
RADAR_APPLICATION_ID = "6f742cd7-5090-4cb2-8c35-8d9644e9ab5e"
OLD_LAUNCH_URL = "https://blueashdigital.tech/OpportunityRadar"
RADAR_LAUNCH_URL = "https://radar.blueashdigital.tech/"
RADAR_HEALTH_URL = "https://radar.blueashdigital.tech/api/health"


def _require_disposable_database() -> None:
    if os.environ.get("PHASE3_ALLOW_DISPOSABLE_DATABASE") != "1":
        raise SystemExit("Refusing to inspect a database without PHASE3_ALLOW_DISPOSABLE_DATABASE=1.")
    url = make_url(settings.database_url)
    if url.get_backend_name() != "postgresql":
        raise SystemExit("Phase 3 migration validation requires disposable PostgreSQL.")
    if url.database != "portal_phase3" or url.host not in {"portal-postgres", "127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Refusing to inspect a database that is not the isolated portal_phase3 instance.")


def _column_names(inspector: Inspector, table_name: str) -> set[str]:
    return {str(column["name"]) for column in inspector.get_columns(table_name)}


def _assert_contains(actual: Iterable[str], expected: Iterable[str], label: str) -> None:
    missing = sorted(set(expected) - set(actual))
    if missing:
        raise AssertionError(f"{label} is missing: {', '.join(missing)}")


def _assert_unique(inspector: Inspector, table_name: str, column_name: str) -> None:
    constraints = inspector.get_unique_constraints(table_name)
    if not any(item.get("column_names") == [column_name] for item in constraints):
        raise AssertionError(f"{table_name}.{column_name} must have a unique constraint")


def _assert_foreign_keys(inspector: Inspector, table_name: str) -> None:
    expected = {
        ("user_id", "users", "id"),
        ("parent_session_id", "sessions", "id"),
        ("application_id", "applications", "id"),
    }
    actual: set[tuple[str, str, str]] = set()
    for foreign_key in inspector.get_foreign_keys(table_name):
        constrained = foreign_key.get("constrained_columns") or []
        referred = foreign_key.get("referred_columns") or []
        if len(constrained) == 1 and len(referred) == 1:
            actual.add((str(constrained[0]), str(foreign_key.get("referred_table")), str(referred[0])))
        if (foreign_key.get("options") or {}).get("ondelete") != "CASCADE":
            raise AssertionError(f"{table_name} foreign keys must cascade on delete")
    _assert_contains(actual, expected, f"{table_name} foreign keys")


def _assert_registry(connection, *, expected_revision: str) -> None:
    row = connection.execute(
        text(
            """
            SELECT id::text AS id, slug, launch_url, health_check_url,
                   internal_service_url, status::text AS status
            FROM applications
            WHERE id = CAST(:application_id AS uuid) AND slug = 'opportunity-radar'
            """
        ),
        {"application_id": RADAR_APPLICATION_ID},
    ).mappings().one()
    if row["status"] != "UNKNOWN" or row["internal_service_url"] is not None:
        raise AssertionError("Opportunity Radar registry status/internal URL is not migration-safe")
    if expected_revision == REVISION_0006:
        if row["launch_url"] != RADAR_LAUNCH_URL or row["health_check_url"] != RADAR_HEALTH_URL:
            raise AssertionError("0006 did not install the exact future Radar registry URLs")
    elif row["launch_url"] != OLD_LAUNCH_URL or row["health_check_url"] is not None:
        raise AssertionError("downgrade to 0005 did not restore the prior Radar registry values")


def validate(expected_revision: str) -> dict[str, object]:
    _require_disposable_database()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        with engine.connect() as connection:
            actual_revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            if actual_revision != expected_revision:
                raise AssertionError(f"expected Alembic {expected_revision}, found {actual_revision}")
            _assert_registry(connection, expected_revision=expected_revision)

        auth_tables = {"application_authorization_codes", "application_sessions"}
        if expected_revision == REVISION_0005:
            if tables & auth_tables:
                raise AssertionError("0005 must not retain the new application-auth tables")
            if "mfa_satisfied_at" in _column_names(inspector, "sessions"):
                raise AssertionError("0005 must not retain sessions.mfa_satisfied_at")
            if "return_to" in _column_names(inspector, "pre_auth_sessions"):
                raise AssertionError("0005 must not retain pre_auth_sessions.return_to")
            return {"status": "ok", "revision": actual_revision, "applicationAuthTables": "absent"}

        _assert_contains(tables, auth_tables, "0006 tables")
        _assert_contains(_column_names(inspector, "sessions"), {"mfa_satisfied_at"}, "sessions columns")
        _assert_contains(_column_names(inspector, "pre_auth_sessions"), {"return_to"}, "pre_auth_sessions columns")
        _assert_contains(
            _column_names(inspector, "application_authorization_codes"),
            {
                "id", "code_hash", "user_id", "parent_session_id", "application_id",
                "callback_uri", "pkce_challenge", "return_path", "created_at", "expires_at",
                "consumed_at", "revoked_at",
            },
            "authorization-code columns",
        )
        _assert_contains(
            _column_names(inspector, "application_sessions"),
            {
                "id", "token_hash", "user_id", "parent_session_id", "application_id",
                "created_at", "last_seen_at", "idle_expires_at", "absolute_expires_at",
                "revoked_at", "revocation_reason",
            },
            "application-session columns",
        )
        _assert_unique(inspector, "application_authorization_codes", "code_hash")
        _assert_unique(inspector, "application_sessions", "token_hash")
        _assert_foreign_keys(inspector, "application_authorization_codes")
        _assert_foreign_keys(inspector, "application_sessions")
        _assert_contains(
            {str(item["name"]) for item in inspector.get_check_constraints("application_authorization_codes")},
            {"ck_application_authorization_codes_expiry"},
            "authorization-code checks",
        )
        _assert_contains(
            {str(item["name"]) for item in inspector.get_check_constraints("application_sessions")},
            {"ck_application_sessions_idle_expiry", "ck_application_sessions_absolute_expiry"},
            "application-session checks",
        )
        _assert_contains(
            {str(index["name"]) for index in inspector.get_indexes("application_authorization_codes")},
            {
                "ix_application_authorization_codes_expires_at",
                "ix_application_authorization_codes_parent_session_id",
                "ix_application_authorization_codes_user_application",
            },
            "authorization-code indexes",
        )
        _assert_contains(
            {str(index["name"]) for index in inspector.get_indexes("application_sessions")},
            {
                "ix_application_sessions_idle_expires_at",
                "ix_application_sessions_absolute_expires_at",
                "ix_application_sessions_parent_session_id",
                "ix_application_sessions_user_application",
            },
            "application-session indexes",
        )
        return {"status": "ok", "revision": actual_revision, "applicationAuthTables": "validated"}
    finally:
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the isolated Phase 3 Portal schema.")
    parser.add_argument("revision", choices=["0005", "0006", REVISION_0005, REVISION_0006])
    args = parser.parse_args()
    expected = REVISION_0005 if args.revision in {"0005", REVISION_0005} else REVISION_0006
    print(json.dumps(validate(expected), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
