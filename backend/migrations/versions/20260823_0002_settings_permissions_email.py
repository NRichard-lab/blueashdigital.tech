"""settings permissions and email configuration

Revision ID: 20260823_0002
Revises: 20260823_0001
Create Date: 2026-08-23
"""

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260823_0002"
down_revision = "20260823_0001"
branch_labels = None
depends_on = None


PERMISSIONS = (
    ("dashboard.view", "View Dashboard", "Dashboard"),
    ("applications.view", "View Applications", "Applications"),
    ("applications.launch", "Launch Applications", "Applications"),
    ("profile.manage", "Manage Own Profile", "Profile"),
    ("users.view", "View Users", "Users"),
    ("users.create", "Add Users", "Users"),
    ("users.edit", "Edit Users", "Users"),
    ("users.delete", "Delete Users", "Users"),
    ("applications_admin.view", "View Application Administration", "Applications"),
    ("applications_admin.create", "Add Applications", "Applications"),
    ("applications_admin.edit", "Edit Applications", "Applications"),
    ("applications_admin.delete", "Delete Applications", "Applications"),
    ("audit.view", "View Audit Log", "Audit"),
    ("settings.view", "View Settings", "Settings"),
    ("settings.edit", "Modify Settings", "Settings"),
    ("roles.view", "View Roles", "Settings"),
    ("roles.edit", "Manage Roles", "Settings"),
    ("email_settings.view", "View Email Settings", "Email"),
    ("email_settings.edit", "Manage Email Settings", "Email"),
    ("email_settings.test", "Send Test Email", "Email"),
)

ADMIN_ROLE_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
USER_ROLE_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")


def upgrade() -> None:
    postgresql.ENUM("gmail", name="email_provider_enum").create(op.get_bind(), checkfirst=True)
    postgresql.ENUM("NOT_CONFIGURED", "CONFIGURED", "VERIFIED", "ERROR", name="email_status_enum").create(op.get_bind(), checkfirst=True)

    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("key", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_roles_key", "roles", ["key"])

    op.create_table(
        "permissions",
        sa.Column("key", sa.String(120), primary_key=True),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("group", sa.String(80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Uuid(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_key", sa.String(120), sa.ForeignKey("permissions.key", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("role_id", "permission_key", name="uq_role_permissions_role_permission"),
    )

    op.create_table(
        "email_settings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("provider", postgresql.ENUM("gmail", name="email_provider_enum", create_type=False), nullable=False, server_default="gmail"),
        sa.Column("email_address", sa.String(320)),
        sa.Column("encrypted_app_password", sa.Text()),
        sa.Column("from_name", sa.String(160)),
        sa.Column("reply_to", sa.String(320)),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", postgresql.ENUM("NOT_CONFIGURED", "CONFIGURED", "VERIFIED", "ERROR", name="email_status_enum", create_type=False), nullable=False, server_default="NOT_CONFIGURED"),
        sa.Column("last_test_at", sa.DateTime(timezone=True)),
        sa.Column("last_test_result", sa.String(40)),
        sa.Column("last_error", sa.String(240)),
        sa.Column("updated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "email_mfa_challenges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_hash", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ip_address", sa.String(64)),
    )
    op.create_index("ix_email_mfa_challenges_user_id", "email_mfa_challenges", ["user_id"])

    roles_table = sa.table(
        "roles",
        sa.column("id", sa.Uuid()),
        sa.column("key", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("system", sa.Boolean()),
    )
    permissions_table = sa.table(
        "permissions",
        sa.column("key", sa.String()),
        sa.column("label", sa.String()),
        sa.column("group", sa.String()),
        sa.column("description", sa.Text()),
    )
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_key", sa.String()),
    )

    op.bulk_insert(
        roles_table,
        [
            {"id": ADMIN_ROLE_ID, "key": "ADMINISTRATOR", "name": "Admin", "description": "Full portal administration access.", "system": True},
            {"id": USER_ROLE_ID, "key": "USER", "name": "User", "description": "Standard portal user with assigned application access.", "system": True},
        ],
    )
    op.bulk_insert(permissions_table, [{"key": key, "label": label, "group": group, "description": ""} for key, label, group in PERMISSIONS])
    op.bulk_insert(role_permissions_table, [{"role_id": ADMIN_ROLE_ID, "permission_key": key} for key, _, _ in PERMISSIONS])
    op.bulk_insert(
        role_permissions_table,
        [
            {"role_id": USER_ROLE_ID, "permission_key": "dashboard.view"},
            {"role_id": USER_ROLE_ID, "permission_key": "applications.view"},
            {"role_id": USER_ROLE_ID, "permission_key": "applications.launch"},
            {"role_id": USER_ROLE_ID, "permission_key": "profile.manage"},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_email_mfa_challenges_user_id", table_name="email_mfa_challenges")
    op.drop_table("email_mfa_challenges")
    op.drop_table("email_settings")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_index("ix_roles_key", table_name="roles")
    op.drop_table("roles")
    sa.Enum(name="email_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="email_provider_enum").drop(op.get_bind(), checkfirst=True)
