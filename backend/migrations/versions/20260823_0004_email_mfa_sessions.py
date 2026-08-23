"""email mfa and secure sessions

Revision ID: 20260823_0004
Revises: 20260823_0003
Create Date: 2026-08-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260823_0004"
down_revision = "20260823_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "authentication_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idle_timeout_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("absolute_timeout_minutes", sa.Integer(), nullable=False, server_default="480"),
        sa.Column("mfa_code_expiration_minutes", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("mfa_max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("mfa_resend_delay_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        INSERT INTO authentication_settings (
            id, idle_timeout_minutes, absolute_timeout_minutes,
            mfa_code_expiration_minutes, mfa_max_attempts, mfa_resend_delay_seconds
        )
        VALUES ('00000000-0000-4000-8000-000000000004', 30, 480, 10, 5, 60)
        """
    )

    op.create_table(
        "pre_auth_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_pre_auth_sessions_expires_at"), "pre_auth_sessions", ["expires_at"], unique=False)
    op.create_index(op.f("ix_pre_auth_sessions_user_id"), "pre_auth_sessions", ["user_id"], unique=False)

    op.add_column("sessions", sa.Column("last_activity_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.add_column("sessions", sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE sessions SET absolute_expires_at = expires_at WHERE absolute_expires_at IS NULL")
    op.alter_column("sessions", "absolute_expires_at", nullable=False)
    op.create_index(op.f("ix_sessions_absolute_expires_at"), "sessions", ["absolute_expires_at"], unique=False)

    op.add_column("email_mfa_challenges", sa.Column("pre_auth_session_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("email_mfa_challenges", sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_email_mfa_challenges_pre_auth_session_id",
        "email_mfa_challenges",
        "pre_auth_sessions",
        ["pre_auth_session_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_email_mfa_challenges_pre_auth_session_id"), "email_mfa_challenges", ["pre_auth_session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_email_mfa_challenges_pre_auth_session_id"), table_name="email_mfa_challenges")
    op.drop_constraint("fk_email_mfa_challenges_pre_auth_session_id", "email_mfa_challenges", type_="foreignkey")
    op.drop_column("email_mfa_challenges", "invalidated_at")
    op.drop_column("email_mfa_challenges", "pre_auth_session_id")
    op.drop_index(op.f("ix_sessions_absolute_expires_at"), table_name="sessions")
    op.drop_column("sessions", "absolute_expires_at")
    op.drop_column("sessions", "last_activity_at")
    op.drop_index(op.f("ix_pre_auth_sessions_user_id"), table_name="pre_auth_sessions")
    op.drop_index(op.f("ix_pre_auth_sessions_expires_at"), table_name="pre_auth_sessions")
    op.drop_table("pre_auth_sessions")
    op.drop_table("authentication_settings")
