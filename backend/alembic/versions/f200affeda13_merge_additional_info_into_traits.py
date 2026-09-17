"""merge additional_info into traits

Revision ID: f200affeda13
Revises: 4b115e573fc0
Create Date: 2026-09-15 00:11:38.561880

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f200affeda13'
down_revision: Union[str, Sequence[str], None] = '4b115e573fc0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, traits, additional_info FROM assistants")).fetchall()
    for row in rows:
        additional_info = (row.additional_info or "").strip()
        if additional_info:
            merged = f"{row.traits} {additional_info}".strip()
            conn.execute(
                sa.text("UPDATE assistants SET traits = :traits WHERE id = :id"),
                {"traits": merged, "id": row.id},
            )

    with op.batch_alter_table("assistants") as batch_op:
        batch_op.alter_column("traits", type_=sa.String(length=2000))
        batch_op.drop_column("additional_info")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("assistants") as batch_op:
        batch_op.add_column(
            sa.Column("additional_info", sa.String(length=1000), server_default="", nullable=False)
        )
        batch_op.alter_column("traits", type_=sa.String(length=1000))
