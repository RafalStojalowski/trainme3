import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Assistant, ClientUsage, Location, Reservation, Room, User
from app.security import hash_password

DEMO_EMAIL = "demo@trainme.pl"
DEMO_PASSWORD = "demo1234"


def seed_demo_data(db: Session) -> None:
    # Idempotentne - jeśli konto demo już istnieje (np. dane przetrwały restart), nic nie rób.
    if db.scalar(select(User).where(User.email == DEMO_EMAIL)):
        return

    user = User(
        email=DEMO_EMAIL,
        full_name="Konto demo",
        hashed_password=hash_password(DEMO_PASSWORD),
    )
    db.add(user)
    db.flush()

    db.add(ClientUsage(user_id=user.id, minutes_used=42, minutes_included=500))

    warszawa = Location(
        user_id=user.id,
        name="Apartamenty Centrum",
        address="ul. Marszałkowska 10, Warszawa",
        description="Nowoczesne apartamenty w sercu miasta.",
        latitude=52.2297,
        longitude=21.0122,
    )
    krakow = Location(
        user_id=user.id,
        name="Dom Gościnny Kazimierz",
        address="ul. Józefa 5, Kraków",
        description="Klimatyczny dom gościnny na Kazimierzu.",
        latitude=50.0483,
        longitude=19.9440,
    )
    db.add_all([warszawa, krakow])
    db.flush()

    room1 = Room(
        location_id=warszawa.id,
        name="Pokój 101",
        capacity=2,
        price_per_night=250,
        amenities="Wi-Fi, klimatyzacja, parking",
    )
    room2 = Room(
        location_id=warszawa.id,
        name="Pokój 102",
        capacity=4,
        price_per_night=380,
        amenities="Wi-Fi, balkon, kuchnia",
    )
    room3 = Room(
        location_id=krakow.id,
        name="Pokój Kazimierz A",
        capacity=2,
        price_per_night=220,
        amenities="Wi-Fi, śniadanie",
    )
    db.add_all([room1, room2, room3])
    db.flush()

    assistant = Assistant(
        user_id=user.id,
        name="Asystentka Ania",
        status="active",
        voice="Kobiecy, ciepły",
        traits="Uprzejma, cierpliwa, mówi po polsku i angielsku",
        max_concurrent_calls=3,
        minutes_used=42,
    )
    assistant.locations = [warszawa, krakow]
    db.add(assistant)
    db.flush()

    today = datetime.date.today()
    db.add_all(
        [
            Reservation(
                room_id=room1.id,
                guest_name="Jan Kowalski",
                check_in=today,
                check_out=today + datetime.timedelta(days=3),
                assistant_id=assistant.id,
            ),
            Reservation(
                room_id=room2.id,
                guest_name="Anna Nowak",
                check_in=today + datetime.timedelta(days=5),
                check_out=today + datetime.timedelta(days=7),
            ),
            Reservation(
                room_id=room3.id,
                guest_name="Piotr Wiśniewski",
                check_in=today - datetime.timedelta(days=2),
                check_out=today + datetime.timedelta(days=1),
                assistant_id=assistant.id,
            ),
        ]
    )

    db.commit()
