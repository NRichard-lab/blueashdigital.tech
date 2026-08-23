"""hostinger email provider

Revision ID: 20260823_0003
Revises: 20260823_0002
Create Date: 2026-08-23
"""

from alembic import op
import sqlalchemy as sa

revision = "20260823_0003"
down_revision = "20260823_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE email_provider_enum ADD VALUE IF NOT EXISTS 'hostinger'")
    op.add_column("email_settings", sa.Column("smtp_username", sa.String(320), nullable=True))
    op.add_column("email_settings", sa.Column("encrypted_smtp_password", sa.Text(), nullable=True))
    op.add_column("email_settings", sa.Column("from_email", sa.String(320), nullable=True))
    op.add_column("email_settings", sa.Column("smtp_port", sa.Integer(), nullable=False, server_default="465"))
    op.add_column("email_settings", sa.Column("smtp_security", sa.String(20), nullable=False, server_default="SSL_TLS"))


def downgrade() -> None:
    op.drop_column("email_settings", "smtp_security")
    op.drop_column("email_settings", "smtp_port")
    op.drop_column("email_settings", "from_email")
    op.drop_column("email_settings", "encrypted_smtp_password")
    op.drop_column("email_settings", "smtp_username")
