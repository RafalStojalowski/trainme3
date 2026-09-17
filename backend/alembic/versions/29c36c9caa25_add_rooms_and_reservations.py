"""add rooms and reservations

Revision ID: 29c36c9caa25
Revises: be9f3f13d471
Create Date: 2026-09-15 01:10:00.000000

"""
import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29c36c9caa25'
down_revision: Union[str, Sequence[str], None] = 'be9f3f13d471'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ROOM_TEMPLATE = [
    ("Pokój Standard", 2, 250.0),
    ("Pokój Comfort", 2, 320.0),
    ("Apartament Rodzinny", 4, 480.0),
    ("Studio", 1, 190.0),
]

GUEST_NAMES = ["Marta Kowalska", "Piotr Zieliński", "Anna Nowak", "Tomasz Wiśniewski"]

KNOWN_DESCRIPTIONS = {
    "Apartament Stare Miasto": "Klimatyczny apartament w sercu krakowskiego Starego Miasta, blisko Rynku Głównego.",
    "Dom nad Jeziorem": "Przestronny dom z prywatnym pomostem, idealny na wypoczynek nad wodą.",
    "Loft Praga": "Industrialny loft na warszawskiej Pradze, w pobliżu klimatycznych knajpek i galerii.",
}


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("locations") as batch_op:
        batch_op.add_column(sa.Column("description", sa.String(length=500), server_default="", nullable=False))

    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("price_per_night", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_table(
        "reservations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("guest_name", sa.String(length=255), nullable=False),
        sa.Column("check_in", sa.Date(), nullable=False),
        sa.Column("check_out", sa.Date(), nullable=False),
    )

    # Dopisz pokoje (i dla części budynków aktualną rezerwację) do lokalizacji,
    # które istniały przed tą migracją - żeby strona szczegółów budynku miała realne dane.
    conn = op.get_bind()
    today = datetime.date.today()

    location_rows = conn.execute(sa.text("SELECT id, name FROM locations ORDER BY user_id, id")).fetchall()

    reservation_counter = 0
    for location_id, location_name in location_rows:
        description = KNOWN_DESCRIPTIONS.get(
            location_name, f"{location_name} - komfortowy obiekt na wynajem w atrakcyjnej lokalizacji."
        )
        conn.execute(
            sa.text("UPDATE locations SET description=:description WHERE id=:id"),
            {"description": description, "id": location_id},
        )

        room_ids = []
        for name, capacity, price in ROOM_TEMPLATE:
            result = conn.execute(
                sa.text(
                    "INSERT INTO rooms (location_id, name, capacity, price_per_night) "
                    "VALUES (:location_id, :name, :capacity, :price)"
                ),
                {"location_id": location_id, "name": name, "capacity": capacity, "price": price},
            )
            room_ids.append(result.lastrowid)

        if reservation_counter < 4:
            check_in = today - datetime.timedelta(days=1)
            check_out = today + datetime.timedelta(days=2)
            conn.execute(
                sa.text(
                    "INSERT INTO reservations (room_id, guest_name, check_in, check_out) "
                    "VALUES (:room_id, :guest_name, :check_in, :check_out)"
                ),
                {
                    "room_id": room_ids[0],
                    "guest_name": GUEST_NAMES[reservation_counter % len(GUEST_NAMES)],
                    "check_in": check_in.isoformat(),
                    "check_out": check_out.isoformat(),
                },
            )
            reservation_counter += 1


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("reservations")
    op.drop_table("rooms")
    with op.batch_alter_table("locations") as batch_op:
        batch_op.drop_column("description")
