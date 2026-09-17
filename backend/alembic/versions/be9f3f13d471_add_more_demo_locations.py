"""add more demo locations

Revision ID: be9f3f13d471
Revises: 07d1150f9de9
Create Date: 2026-09-15 00:41:03.031729

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be9f3f13d471'
down_revision: Union[str, Sequence[str], None] = '07d1150f9de9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NEW_LOCATIONS = [
    ("Apartament Rynek", "Rynek 5, Wrocław", 51.1079, 17.0385),
    ("Rezydencja Długi Targ", "ul. Długi Targ 10, Gdańsk", 54.3520, 18.6466),
    ("Loft Stary Rynek", "Stary Rynek 8, Poznań", 52.4064, 16.9252),
    ("Górska Chata", "ul. Krupówki 22, Zakopane", 49.2992, 19.9496),
    ("Apartament nad Morzem", "ul. Monte Cassino 12, Sopot", 54.4418, 18.5601),
    ("Domek w Górach", "Wisła, Beskidy", 49.6423, 18.8514),
    ("Kamienica Staromiejska", "Rynek Staromiejski 3, Toruń", 53.0138, 18.5981),
]


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    # Dopisz nowe lokalizacje demo tylko tym użytkownikom, którzy mieli już
    # wygenerowane dane demo (czyli mają choć jedną lokalizację).
    user_ids = [row[0] for row in conn.execute(sa.text("SELECT DISTINCT user_id FROM locations"))]

    for user_id in user_ids:
        for name, address, lat, lng in NEW_LOCATIONS:
            conn.execute(
                sa.text(
                    "INSERT INTO locations (user_id, name, address, latitude, longitude) "
                    "VALUES (:user_id, :name, :address, :lat, :lng)"
                ),
                {"user_id": user_id, "name": name, "address": address, "lat": lat, "lng": lng},
            )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    names = [name for name, _, _, _ in NEW_LOCATIONS]
    conn.execute(
        sa.text("DELETE FROM locations WHERE name IN :names").bindparams(
            sa.bindparam("names", expanding=True)
        ),
        {"names": names},
    )
