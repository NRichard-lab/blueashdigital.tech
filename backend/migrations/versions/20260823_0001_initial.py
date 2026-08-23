"""initial schema

Revision ID: 20260823_0001
Revises:
Create Date: 2026-08-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260823_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    role_enum = postgresql.ENUM("ADMINISTRATOR", "USER", name="role_enum", create_type=False)
    app_type_enum = postgresql.ENUM("INTERNAL_WEB", "INTERNAL_SERVICE", "EXTERNAL_URL", "API_APP", name="app_type_enum", create_type=False)
    app_status_enum = postgresql.ENUM("ONLINE", "OFFLINE", "UNKNOWN", "MAINTENANCE", name="app_status_enum", create_type=False)
    mfa_type_enum = postgresql.ENUM("TOTP", "EMAIL", "SMS", name="mfa_type_enum", create_type=False)

    postgresql.ENUM("ADMINISTRATOR", "USER", name="role_enum").create(op.get_bind(), checkfirst=True)
    postgresql.ENUM("INTERNAL_WEB", "INTERNAL_SERVICE", "EXTERNAL_URL", "API_APP", name="app_type_enum").create(op.get_bind(), checkfirst=True)
    postgresql.ENUM("ONLINE", "OFFLINE", "UNKNOWN", "MAINTENANCE", name="app_status_enum").create(op.get_bind(), checkfirst=True)
    postgresql.ENUM("TOTP", "EMAIL", "SMS", name="mfa_type_enum").create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("role", role_enum, nullable=False, server_default="USER"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("force_password_change", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("mfa_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "applications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("icon", sa.String(64), nullable=False, server_default="APP"),
        sa.Column("category", sa.String(80), nullable=False, server_default="Utilities"),
        sa.Column("application_type", app_type_enum, nullable=False),
        sa.Column("launch_url", sa.String(2048), nullable=False),
        sa.Column("internal_service_url", sa.String(2048)),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("administrator_only", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("health_check_url", sa.String(2048)),
        sa.Column("status", app_status_enum, nullable=False, server_default="UNKNOWN"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "user_applications",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("application_id", sa.Uuid(), sa.ForeignKey("applications.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "mfa_methods",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("method_type", mfa_type_enum, nullable=False),
        sa.Column("secret_encrypted", sa.String(2048)),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("target_type", sa.String(80)),
        sa.Column("target_id", sa.String(120)),
        sa.Column("result", sa.String(40), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_applications_category", "applications", ["category"])
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_sessions_expires_at", table_name="sessions")
    op.drop_index("ix_applications_category", table_name="applications")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("password_reset_tokens")
    op.drop_table("mfa_methods")
    op.drop_table("sessions")
    op.drop_table("user_applications")
    op.drop_table("applications")
    op.drop_table("users")
    sa.Enum(name="mfa_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="app_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="app_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="role_enum").drop(op.get_bind(), checkfirst=True)
