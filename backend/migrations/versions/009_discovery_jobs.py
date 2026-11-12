"""009_discovery_jobs

Revision ID: 009_discovery_jobs
Revises: 008_remediation_recommendations
Create Date: 2026-11-12 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from app.models.base import GUID

revision: str = '009_discovery_jobs'
down_revision: Union[str, None] = '008_remediation_recommendations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'discovery_jobs',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('organization_id', GUID(), nullable=False),
        sa.Column('application_id', GUID(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='PENDING', nullable=False),
        sa.Column('endpoints_found', sa.Integer(), server_default='0', nullable=False),
        sa.Column('endpoints_in_scope', sa.Integer(), server_default='0', nullable=False),
        sa.Column('endpoints_out_of_scope', sa.Integer(), server_default='0', nullable=False),
        sa.Column('error_message', sa.String(length=1000), nullable=True),
        sa.Column('summary', sa.JSON(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_discovery_jobs_organization_id', 'discovery_jobs', ['organization_id'])
    op.create_index('ix_discovery_jobs_application_id', 'discovery_jobs', ['application_id'])
    op.create_index('ix_discovery_jobs_status', 'discovery_jobs', ['status'])


def downgrade() -> None:
    op.drop_index('ix_discovery_jobs_status', table_name='discovery_jobs')
    op.drop_index('ix_discovery_jobs_application_id', table_name='discovery_jobs')
    op.drop_index('ix_discovery_jobs_organization_id', table_name='discovery_jobs')
    op.drop_table('discovery_jobs')

