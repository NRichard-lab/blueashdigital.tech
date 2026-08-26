"""register Opportunity Radar

Revision ID: 20260825_0005
Revises: 20260823_0004
Create Date: 2026-08-25
"""

import uuid

from alembic import op


revision = "20260825_0005"
down_revision = "20260823_0004"
branch_labels = None
depends_on = None

APPLICATION_ID = uuid.UUID("6f742cd7-5090-4cb2-8c35-8d9644e9ab5e")


def upgrade() -> None:
    op.execute(
        f"""
        INSERT INTO applications (
            id, name, slug, description, icon, category, application_type,
            launch_url, enabled, administrator_only, display_order, status
        ) VALUES (
            '{APPLICATION_ID}',
            'Opportunity Radar',
            'opportunity-radar',
            'Job discovery, tracking, resume matching, and application management.',
            'RADAR',
            'Career Tools',
            'INTERNAL_WEB',
            'https://blueashdigital.tech/OpportunityRadar',
            TRUE,
            FALSE,
            20,
            'UNKNOWN'
        )
        ON CONFLICT (slug) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            icon = EXCLUDED.icon,
            category = EXCLUDED.category,
            application_type = EXCLUDED.application_type,
            launch_url = EXCLUDED.launch_url,
            enabled = EXCLUDED.enabled,
            administrator_only = EXCLUDED.administrator_only,
            display_order = EXCLUDED.display_order,
            updated_at = now()
        """
    )


def downgrade() -> None:
    op.execute(f"DELETE FROM applications WHERE id = '{APPLICATION_ID}' AND slug = 'opportunity-radar'")
