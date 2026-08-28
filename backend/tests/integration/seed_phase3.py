from __future__ import annotations

import json
import os
import uuid

from sqlalchemy import delete, select
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.application import Application, ApplicationStatus, UserApplication
from app.models.user import Role, User


RADAR_APPLICATION_ID = uuid.UUID("6f742cd7-5090-4cb2-8c35-8d9644e9ab5e")
TRUSTED_ADMIN_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
ASSIGNED_USER_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
UNASSIGNED_USER_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")
DISABLED_USER_ID = uuid.UUID("44444444-4444-4444-8444-444444444444")


def _require_disposable_database() -> str:
    if os.environ.get("PHASE3_ALLOW_DISPOSABLE_DATABASE") != "1":
        raise SystemExit("Refusing to seed without PHASE3_ALLOW_DISPOSABLE_DATABASE=1.")
    url = make_url(settings.database_url)
    if url.database != "portal_phase3" or url.host != "portal-postgres":
        raise SystemExit("Refusing to seed anything except the isolated portal_phase3 service.")
    password = os.environ.get("PHASE3_SYNTHETIC_PASSWORD", "")
    if len(password) < 16 or not password.startswith("phase3-"):
        raise SystemExit("PHASE3_SYNTHETIC_PASSWORD must be an explicit synthetic Phase 3 value.")
    expected_admin = os.environ.get("APP_TRUSTED_ADMIN_USER_ID", str(TRUSTED_ADMIN_ID))
    if expected_admin.casefold() != str(TRUSTED_ADMIN_ID):
        raise SystemExit("The integration trusted-administrator UUID does not match the fixture.")
    return password


def _upsert_user(db, *, user_id: uuid.UUID, username: str, email: str, display_name: str,
                 role: Role, enabled: bool, mfa_required: bool, password_hash: str) -> User:
    conflicting = db.scalar(
        select(User).where((User.username == username) | (User.email == email)).where(User.id != user_id)
    )
    if conflicting:
        raise RuntimeError(f"Synthetic identity conflicts with existing user {conflicting.id}")
    user = db.get(User, user_id)
    if user is None:
        user = User(id=user_id, username=username, email=email, display_name=display_name,
                    password_hash=password_hash, role=role, enabled=enabled)
        db.add(user)
    user.username = username
    user.email = email
    user.display_name = display_name
    user.password_hash = password_hash
    user.role = role
    user.enabled = enabled
    user.force_password_change = False
    user.mfa_required = mfa_required
    return user


def seed() -> dict[str, object]:
    password = _require_disposable_database()
    password_hash = hash_password(password)
    users = (
        (TRUSTED_ADMIN_ID, "phase3-admin", "phase3-admin@example.com", "Phase 3 Trusted Admin", Role.ADMINISTRATOR, True, True),
        (ASSIGNED_USER_ID, "phase3-assigned", "phase3-assigned@example.com", "Phase 3 Assigned User", Role.USER, True, False),
        (UNASSIGNED_USER_ID, "phase3-unassigned", "phase3-unassigned@example.com", "Phase 3 Unassigned User", Role.USER, True, False),
        (DISABLED_USER_ID, "phase3-disabled", "phase3-disabled@example.com", "Phase 3 Disabled User", Role.USER, False, False),
    )
    with SessionLocal() as db:
        application = db.get(Application, RADAR_APPLICATION_ID)
        if application is None or application.slug != "opportunity-radar":
            raise RuntimeError("Migration 0006 must register Opportunity Radar before seeding")
        application.enabled = True
        application.administrator_only = False
        application.status = ApplicationStatus.UNKNOWN
        for values in users:
            _upsert_user(
                db,
                user_id=values[0], username=values[1], email=values[2], display_name=values[3],
                role=values[4], enabled=values[5], mfa_required=values[6], password_hash=password_hash,
            )
        fixture_ids = [item[0] for item in users]
        db.flush()
        db.execute(delete(UserApplication).where(UserApplication.user_id.in_(fixture_ids)))
        for user_id in (TRUSTED_ADMIN_ID, ASSIGNED_USER_ID, DISABLED_USER_ID):
            db.add(UserApplication(user_id=user_id, application_id=RADAR_APPLICATION_ID))
        db.commit()
    return {
        "status": "seeded",
        "synthetic": True,
        "trustedAdminId": str(TRUSTED_ADMIN_ID),
        "assignedUserId": str(ASSIGNED_USER_ID),
        "unassignedUserId": str(UNASSIGNED_USER_ID),
        "disabledUserId": str(DISABLED_USER_ID),
    }


if __name__ == "__main__":
    print(json.dumps(seed(), sort_keys=True))
