"""010_endpoint_inventory_relationships

Revision ID: 010_endpoint_inventory_relationships
Revises: 009_discovery_jobs
Create Date: 2026-11-12 20:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from app.models.base import GUID

revision: str = '010_endpoint_inventory_relationships'
down_revision: Union[str, None] = '009_discovery_jobs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'endpoint_relationships',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('application_id', GUID(), nullable=False),
        sa.Column('source_endpoint_id', GUID(), nullable=False),
        sa.Column('target_endpoint_id', GUID(), nullable=False),
        sa.Column('relationship_type', sa.String(length=100), nullable=False),
        sa.Column('evidence_source', sa.String(length=100), nullable=False),
        sa.Column('confidence', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('explanation', sa.String(length=500), nullable=False),
        sa.Column('provenance', sa.String(length=50), server_default='inferred', nullable=False),
        sa.Column('raw_metadata', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_endpoint_id'], ['discovered_endpoints.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_endpoint_id'], ['discovered_endpoints.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('application_id', 'source_endpoint_id', 'target_endpoint_id', 'relationship_type', name='uq_endpoint_relationship')
    )
    op.create_index('ix_endpoint_relationships_application_id', 'endpoint_relationships', ['application_id'])
    op.create_index('ix_endpoint_relationships_source_endpoint_id', 'endpoint_relationships', ['source_endpoint_id'])
    op.create_index('ix_endpoint_relationships_target_endpoint_id', 'endpoint_relationships', ['target_endpoint_id'])
    op.create_index('ix_endpoint_relationships_relationship_type', 'endpoint_relationships', ['relationship_type'])


def downgrade() -> None:
    op.drop_index('ix_endpoint_relationships_relationship_type', table_name='endpoint_relationships')
    op.drop_index('ix_endpoint_relationships_target_endpoint_id', table_name='endpoint_relationships')
    op.drop_index('ix_endpoint_relationships_source_endpoint_id', table_name='endpoint_relationships')
    op.drop_index('ix_endpoint_relationships_application_id', table_name='endpoint_relationships')
    op.drop_table('endpoint_relationships')

