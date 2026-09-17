"""add amenities to rooms

Revision ID: 441603aac0ed
Revises: 29c36c9caa25
Create Date: 2026-09-15 01:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '441603aac0ed'
down_revision: Union[str, Sequence[str], None] = '29c36c9caa25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


KNOWN_AMENITIES = {
    "Pokój Standard": "Wi-Fi, TV, prywatna łazienka",
    "Pokój Comfort": "Wi-Fi, TV, klimatyzacja, minibar",
    "Apartament Rodzinny": "Wi-Fi, TV, aneks kuchenny, pralka",
    "Studio": "Wi-Fi, TV, aneks kuchenny",
}


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("rooms") as batch_op:
        batch_op.add_column(sa.Column("amenities", sa.String(length=500), server_default="", nullable=False))

    conn = op.get_bind()
    for name, amenities in KNOWN_AMENITIES.items():
        conn.execute(
            sa.text("UPDATE rooms SET amenities=:amenities WHERE name=:name"),
            {"amenities": amenities, "name": name},
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("rooms") as batch_op:
        batch_op.drop_column("amenities")
