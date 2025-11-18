"""Migrate Entry to Media model for multiple files

Revision ID: 40e8643a08f8
Revises: 
Create Date: 2025-11-18 07:30:12.467249

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40e8643a08f8'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema and migrate data."""
    
    # 1. Create the new 'media' table
    op.create_table('media',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entry_id', sa.Integer(), nullable=False),
        sa.Column('media_path', sa.String(length=200), nullable=False),
        sa.Column('is_video', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['entry_id'], ['entry.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Get the connection object to execute raw SQL queries
    bind = op.get_bind()
    connection = bind.connect()

    # 2. CUSTOM DATA MIGRATION: Read old paths and insert into the new table
    print("Migrating existing image_path data to new media table...")
    
    # Define the structure of the target table for the insertion
    media_table = sa.Table('media', sa.MetaData(),
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('entry_id', sa.Integer, sa.ForeignKey('entry.id')),
        sa.Column('media_path', sa.String(200)),
        sa.Column('is_video', sa.Boolean)
    )

    # Fetch data from the old 'entry' table
    old_data = connection.execute(sa.text("SELECT id, image_path FROM entry WHERE image_path IS NOT NULL")).fetchall()
    
    # Prepare data for bulk insert
    insert_data = []
    for r in old_data:
        entry_id, image_path = r[0], r[1]
        is_video = False
        if image_path:
            # Check if path ends with a video extension to set is_video flag
            if image_path.lower().endswith(('.mp4', '.mov', '.webm')):
                is_video = True
        
        insert_data.append({
            'entry_id': entry_id, 
            'media_path': image_path, 
            'is_video': is_video
        })

    if insert_data:
        op.bulk_insert(media_table, insert_data)
        print(f"Successfully migrated {len(insert_data)} records.")
    else:
        print("No old image_path records found to migrate.")


    # 3. Drop the old 'image_path' column (using batch mode for SQLite)
    with op.batch_alter_table('entry', schema=None) as batch_op:
        batch_op.drop_column('image_path')


def downgrade() -> None:
    """Downgrade schema."""
    # This is an irreversible data loss operation in the downgrade path
    with op.batch_alter_table('entry', schema=None) as batch_op:
        # Re-add the column, but it will be null for new entries
        batch_op.add_column(sa.Column('image_path', sa.VARCHAR(length=200), nullable=True))
        
    # Drop the new table
    op.drop_table('media')
