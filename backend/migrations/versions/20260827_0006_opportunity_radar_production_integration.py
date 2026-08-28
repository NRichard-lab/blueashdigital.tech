"""add Opportunity Radar application authentication handoff

Revision ID: 20260827_0006
Revises: 20260825_0005
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260827_0006"
down_revision = "20260825_0005"
branch_labels = None
depends_on = None

APPLICATION_ID = "6f742cd7-5090-4cb2-8c35-8d9644e9ab5e"
OLD_LAUNCH_URL = "https://blueashdigital.tech/OpportunityRadar"
RADAR_LAUNCH_URL = "https://radar.blueashdigital.tech/"
RADAR_HEALTH_URL = "https://radar.blueashdigital.tech/api/health"


def upgrade() -> None:
    op.add_column("sessions", sa.Column("mfa_satisfied_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("pre_auth_sessions", sa.Column("return_to", sa.String(length=2048), nullable=True))

    op.create_table(
        "application_authorization_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("callback_uri", sa.String(length=2048), nullable=False),
        sa.Column("pkce_challenge", sa.String(length=128), nullable=False),
        sa.Column("return_path", sa.String(length=2048), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("expires_at > created_at", name="ck_application_authorization_codes_expiry"),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_hash"),
    )
    op.create_index("ix_application_authorization_codes_expires_at", "application_authorization_codes", ["expires_at"])
    op.create_index("ix_application_authorization_codes_consumed_at", "application_authorization_codes", ["consumed_at"])
    op.create_index("ix_application_authorization_codes_revoked_at", "application_authorization_codes", ["revoked_at"])
    op.create_index("ix_application_authorization_codes_parent_session_id", "application_authorization_codes", ["parent_session_id"])
    op.create_index("ix_application_authorization_codes_user_application", "application_authorization_codes", ["user_id", "application_id"])

    op.create_table(
        "application_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocation_reason", sa.String(length=80), nullable=True),
        sa.CheckConstraint("idle_expires_at > created_at", name="ck_application_sessions_idle_expiry"),
        sa.CheckConstraint("absolute_expires_at > created_at", name="ck_application_sessions_absolute_expiry"),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_application_sessions_idle_expires_at", "application_sessions", ["idle_expires_at"])
    op.create_index("ix_application_sessions_absolute_expires_at", "application_sessions", ["absolute_expires_at"])
    op.create_index("ix_application_sessions_revoked_at", "application_sessions", ["revoked_at"])
    op.create_index("ix_application_sessions_parent_session_id", "application_sessions", ["parent_session_id"])
    op.create_index("ix_application_sessions_user_application", "application_sessions", ["user_id", "application_id"])

    op.execute(
        f"""
        UPDATE applications
        SET launch_url = '{RADAR_LAUNCH_URL}',
            health_check_url = '{RADAR_HEALTH_URL}',
            internal_service_url = NULL,
            status = 'UNKNOWN',
            updated_at = now()
        WHERE id = '{APPLICATION_ID}' AND slug = 'opportunity-radar'
        """
    )


def downgrade() -> None:
    op.execute(
        f"""
        UPDATE applications
        SET launch_url = '{OLD_LAUNCH_URL}',
            health_check_url = NULL,
            internal_service_url = NULL,
            status = 'UNKNOWN',
            updated_at = now()
        WHERE id = '{APPLICATION_ID}'
          AND slug = 'opportunity-radar'
          AND launch_url = '{RADAR_LAUNCH_URL}'
        """
    )
    op.drop_index("ix_application_sessions_user_application", table_name="application_sessions")
    op.drop_index("ix_application_sessions_parent_session_id", table_name="application_sessions")
    op.drop_index("ix_application_sessions_absolute_expires_at", table_name="application_sessions")
    op.drop_index("ix_application_sessions_revoked_at", table_name="application_sessions")
    op.drop_index("ix_application_sessions_idle_expires_at", table_name="application_sessions")
    op.drop_table("application_sessions")
    op.drop_index("ix_application_authorization_codes_user_application", table_name="application_authorization_codes")
    op.drop_index("ix_application_authorization_codes_parent_session_id", table_name="application_authorization_codes")
    op.drop_index("ix_application_authorization_codes_expires_at", table_name="application_authorization_codes")
    op.drop_index("ix_application_authorization_codes_revoked_at", table_name="application_authorization_codes")
    op.drop_index("ix_application_authorization_codes_consumed_at", table_name="application_authorization_codes")
    op.drop_table("application_authorization_codes")
    op.drop_column("pre_auth_sessions", "return_to")
    op.drop_column("sessions", "mfa_satisfied_at")
