import uuid
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from app.api.applications import launch_application, list_applications
from app.models.application import Application, ApplicationStatus, ApplicationType
from app.models.user import Role


def opportunity_radar() -> Application:
    return Application(
        id=uuid.UUID("6f742cd7-5090-4cb2-8c35-8d9644e9ab5e"),
        name="Opportunity Radar",
        slug="opportunity-radar",
        description="Job discovery, tracking, resume matching, and application management.",
        icon="RADAR",
        category="Career Tools",
        application_type=ApplicationType.INTERNAL_WEB,
        launch_url="https://blueashdigital.tech/OpportunityRadar",
        enabled=True,
        administrator_only=False,
        display_order=20,
        status=ApplicationStatus.UNKNOWN,
    )


def test_assigned_user_receives_opportunity_radar_from_existing_apps_query() -> None:
    user = Mock(id=uuid.uuid4(), role=Role.USER)
    db = Mock()
    db.scalars.return_value.all.return_value = [opportunity_radar()]

    result = list_applications(user=user, db=db)

    assert [item.slug for item in result] == ["opportunity-radar"]
    statement = db.scalars.call_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "JOIN user_applications" in sql
    assert str(user.id) in sql


def test_unassigned_user_does_not_receive_opportunity_radar() -> None:
    user = Mock(id=uuid.uuid4(), role=Role.USER)
    db = Mock()
    db.scalars.return_value.all.return_value = []

    assert list_applications(user=user, db=db) == []


def test_administrator_query_keeps_existing_all_enabled_apps_behavior() -> None:
    user = Mock(id=uuid.uuid4(), role=Role.ADMINISTRATOR)
    db = Mock()
    db.scalars.return_value.all.return_value = [opportunity_radar()]

    result = list_applications(user=user, db=db)

    assert result[0].launch_url == "https://blueashdigital.tech/OpportunityRadar"
    statement = db.scalars.call_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "JOIN user_applications" not in sql


def test_unassigned_user_cannot_launch_opportunity_radar() -> None:
    user = Mock(id=uuid.uuid4(), role=Role.USER)
    db = Mock()
    db.scalar.return_value = None

    with pytest.raises(HTTPException) as caught:
        launch_application(opportunity_radar().id, user=user, db=db)

    assert caught.value.status_code == 403


def test_assigned_user_can_launch_canonical_opportunity_radar_url() -> None:
    user = Mock(id=uuid.uuid4(), role=Role.USER)
    db = Mock()
    db.scalar.return_value = opportunity_radar()

    assert launch_application(opportunity_radar().id, user=user, db=db) == {
        "launch_url": "https://blueashdigital.tech/OpportunityRadar"
    }
