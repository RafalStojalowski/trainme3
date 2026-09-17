"""add coordinates to locations

Revision ID: 07d1150f9de9
Revises: f200affeda13
Create Date: 2026-09-15 00:26:49.534181

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '07d1150f9de9'
down_revision: Union[str, Sequence[str], None] = 'f200affeda13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("locations") as batch_op:
        batch_op.add_column(sa.Column("address", sa.String(length=255), server_default="", nullable=False))
        batch_op.add_column(
            sa.Column("latitude", sa.Float(), server_default="52.2297", nullable=False)
        )
        batch_op.add_column(
            sa.Column("longitude", sa.Float(), server_default="21.0122", nullable=False)
        )

    # Nadpisz przybliżonymi, realnymi współrzędnymi istniejące lokalizacje z danych demo -
    # nowe konta i tak dostają te same wartości bezpośrednio z funkcji seedującej.
    conn = op.get_bind()
    known = {
        "Apartament Stare Miasto": (50.0614, 19.9372, "ul. Floriańska 15, Kraków"),
        "Dom nad Jeziorem": (54.0288, 21.7666, "Giżycko, Mazury"),
        "Loft Praga": (52.2515, 21.0364, "ul. Ząbkowska 20, Warszawa"),
    }
    for name, (lat, lng, address) in known.items():
        conn.execute(
            sa.text(
                "UPDATE locations SET latitude=:lat, longitude=:lng, address=:address WHERE name=:name"
            ),
            {"lat": lat, "lng": lng, "address": address, "name": name},
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("locations") as batch_op:
        batch_op.drop_column("longitude")
        batch_op.drop_column("latitude")
        batch_op.drop_column("address")
