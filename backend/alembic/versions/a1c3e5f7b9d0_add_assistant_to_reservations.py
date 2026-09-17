"""add assistant to reservations

Revision ID: a1c3e5f7b9d0
Revises: 441603aac0ed
Create Date: 2026-09-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c3e5f7b9d0'
down_revision: Union[str, Sequence[str], None] = '441603aac0ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("reservations") as batch_op:
        batch_op.add_column(sa.Column("assistant_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_reservations_assistant_id_assistants",
            "assistants",
            ["assistant_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("reservations") as batch_op:
        batch_op.drop_constraint("fk_reservations_assistant_id_assistants", type_="foreignkey")
        batch_op.drop_column("assistant_id")
