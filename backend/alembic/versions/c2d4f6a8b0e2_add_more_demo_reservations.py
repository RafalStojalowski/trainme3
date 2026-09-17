"""add more demo reservations

Revision ID: c2d4f6a8b0e2
Revises: a1c3e5f7b9d0
Create Date: 2026-09-17 13:30:00.000000

"""
import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2d4f6a8b0e2'
down_revision: Union[str, Sequence[str], None] = 'a1c3e5f7b9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


GUEST_NAMES = [
    "Marta Kowalska", "Piotr Zieliński", "Anna Nowak", "Tomasz Wiśniewski",
    "Katarzyna Lewandowska", "Michał Wójcik", "Agnieszka Kamińska", "Paweł Dąbrowski",
    "Magdalena Zając", "Krzysztof Szymański",
]

RESERVATION_OFFSET_POOL = [
    (-18, -14),
    (-6, -3),
    (-1, 2),
    (4, 7),
    (12, 16),
    (25, 30),
]


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    today = datetime.date.today()

    # Dopisz dodatkowe rezerwacje demo tylko użytkownikom, którzy mają już
    # wygenerowane dane demo (lokalizacje) - żeby strona rezerwacji miała
    # wystarczająco dużo zróżnicowanych danych do przeglądania i filtrowania.
    user_ids = [row[0] for row in conn.execute(sa.text("SELECT DISTINCT user_id FROM locations"))]

    for user_id in user_ids:
        assistant_ids = [
            row[0]
            for row in conn.execute(
                sa.text("SELECT id FROM assistants WHERE user_id=:user_id ORDER BY id"),
                {"user_id": user_id},
            )
        ]
        assistant_cycle = assistant_ids + [None]

        location_ids = [
            row[0]
            for row in conn.execute(
                sa.text("SELECT id FROM locations WHERE user_id=:user_id ORDER BY id"),
                {"user_id": user_id},
            )
        ]

        reservation_index = 0
        for location_id in location_ids:
            room_ids = [
                row[0]
                for row in conn.execute(
                    sa.text("SELECT id FROM rooms WHERE location_id=:location_id ORDER BY id LIMIT 2"),
                    {"location_id": location_id},
                )
            ]
            for room_id in room_ids:
                check_in_offset, check_out_offset = RESERVATION_OFFSET_POOL[
                    reservation_index % len(RESERVATION_OFFSET_POOL)
                ]
                conn.execute(
                    sa.text(
                        "INSERT INTO reservations (room_id, guest_name, check_in, check_out, assistant_id) "
                        "VALUES (:room_id, :guest_name, :check_in, :check_out, :assistant_id)"
                    ),
                    {
                        "room_id": room_id,
                        "guest_name": GUEST_NAMES[reservation_index % len(GUEST_NAMES)],
                        "check_in": (today + datetime.timedelta(days=check_in_offset)).isoformat(),
                        "check_out": (today + datetime.timedelta(days=check_out_offset)).isoformat(),
                        "assistant_id": assistant_cycle[reservation_index % len(assistant_cycle)],
                    },
                )
                reservation_index += 1


def downgrade() -> None:
    """Downgrade schema."""
    # Rezerwacje dopisane tu na stałe mieszają się z wcześniejszymi danymi demo
    # i z rezerwacjami tworzonymi ręcznie po tej migracji - nie da się ich
    # jednoznacznie odróżnić, więc downgrade nie usuwa danych.
    pass
