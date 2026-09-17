from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import Assistant, ClientUsage, Location, Reservation, Room, User
from app.schemas import (
    AssistantOut,
    AssistantUpdate,
    LocationCreate,
    LocationDetailOut,
    LocationOut,
    ReservationDetailOut,
    ReservationOut,
    RoomCreate,
    RoomOut,
    UsageOut,
)

router = APIRouter(prefix="/api", tags=["assistants"])

ROOM_TEMPLATE = [
    ("Pokój Standard", 2, 250.0, "Wi-Fi, TV, prywatna łazienka"),
    ("Pokój Comfort", 2, 320.0, "Wi-Fi, TV, klimatyzacja, minibar"),
    ("Apartament Rodzinny", 4, 480.0, "Wi-Fi, TV, aneks kuchenny, pralka"),
    ("Studio", 1, 190.0, "Wi-Fi, TV, aneks kuchenny"),
]

GUEST_NAMES = [
    "Marta Kowalska", "Piotr Zieliński", "Anna Nowak", "Tomasz Wiśniewski",
    "Katarzyna Lewandowska", "Michał Wójcik", "Agnieszka Kamińska", "Paweł Dąbrowski",
    "Magdalena Zając", "Krzysztof Szymański",
]

# (check_in_offset, check_out_offset) w dniach względem dzisiejszej daty - zróżnicowane,
# żeby na liście rezerwacji było widać zarówno zakończone, trwające, jak i nadchodzące pobyty.
RESERVATION_OFFSET_POOL = [
    (-18, -14),
    (-6, -3),
    (-1, 2),
    (4, 7),
    (12, 16),
    (25, 30),
]


def _ensure_demo_data(db: DbSession, user: User) -> None:
    if db.scalar(select(ClientUsage).where(ClientUsage.user_id == user.id)):
        return

    apartament = Location(
        user_id=user.id,
        name="Apartament Stare Miasto",
        address="ul. Floriańska 15, Kraków",
        description="Klimatyczny apartament w sercu krakowskiego Starego Miasta, blisko Rynku Głównego.",
        latitude=50.0614,
        longitude=19.9372,
    )
    dom = Location(
        user_id=user.id,
        name="Dom nad Jeziorem",
        address="Giżycko, Mazury",
        description="Przestronny dom z prywatnym pomostem, idealny na wypoczynek nad wodą.",
        latitude=54.0288,
        longitude=21.7666,
    )
    loft = Location(
        user_id=user.id,
        name="Loft Praga",
        address="ul. Ząbkowska 20, Warszawa",
        description="Industrialny loft na warszawskiej Pradze, w pobliżu klimatycznych knajpek i galerii.",
        latitude=52.2515,
        longitude=21.0364,
    )
    extra_locations = [
        Location(user_id=user.id, name=name, address=address, description=f"{name} - komfortowy obiekt na wynajem w atrakcyjnej lokalizacji.", latitude=lat, longitude=lng)
        for name, address, lat, lng in [
            ("Apartament Rynek", "Rynek 5, Wrocław", 51.1079, 17.0385),
            ("Rezydencja Długi Targ", "ul. Długi Targ 10, Gdańsk", 54.3520, 18.6466),
            ("Loft Stary Rynek", "Stary Rynek 8, Poznań", 52.4064, 16.9252),
            ("Górska Chata", "ul. Krupówki 22, Zakopane", 49.2992, 19.9496),
            ("Apartament nad Morzem", "ul. Monte Cassino 12, Sopot", 54.4418, 18.5601),
            ("Domek w Górach", "Wisła, Beskidy", 49.6423, 18.8514),
            ("Kamienica Staromiejska", "Rynek Staromiejski 3, Toruń", 53.0138, 18.5981),
        ]
    ]
    all_locations = [apartament, dom, loft, *extra_locations]
    db.add_all(all_locations)
    db.flush()

    ania = Assistant(
        user_id=user.id,
        name="Ania",
        status="active",
        voice="Kobiecy, ciepły ton",
        traits="Uprzejma i szybka w odpowiedziach, unika narzucania dodatkowych usług. "
        "Priorytetowo obsługuje gości mówiących po angielsku.",
        max_concurrent_calls=3,
        minutes_used=312,
        locations=[apartament, dom],
    )
    bartek = Assistant(
        user_id=user.id,
        name="Bartek",
        status="active",
        voice="Męski, rzeczowy",
        traits="Precyzyjny, podaje twarde fakty o cenach i dostępności bez owijania w bawełnę. "
        "Nie negocjuje cen — kieruje takie pytania do właściciela.",
        max_concurrent_calls=2,
        minutes_used=198,
        locations=[loft],
    )
    kasia = Assistant(
        user_id=user.id,
        name="Kasia",
        status="offline",
        voice="Kobiecy, spokojny",
        traits="Specjalizuje się w długoterminowych rezerwacjach grupowych. "
        "Wyłączona do czasu zakończenia aktualizacji cennika grupowego.",
        max_concurrent_calls=2,
        minutes_used=145,
        locations=[dom],
    )
    marek = Assistant(
        user_id=user.id,
        name="Marek",
        status="in_call",
        voice="Męski, energiczny",
        traits="Aktywnie dopytuje o preferencje gościa przed sfinalizowaniem rezerwacji. "
        "Testowany pod kątem obsługi rezerwacji last-minute.",
        max_concurrent_calls=1,
        minutes_used=87,
        locations=[apartament],
    )
    db.add_all([ania, bartek, kasia, marek])
    db.flush()

    # Demo rezerwacje pokazują różne warianty obsługi: przez jednego z asystentów
    # albo bez żadnego asystenta (rezerwacja ręczna) - cyklicznie, żeby strona
    # rezerwacji miała sporo zróżnicowanych danych do przeglądania i filtrowania.
    assistant_cycle = [ania.id, bartek.id, kasia.id, marek.id, None]

    today = date.today()
    reservation_index = 0
    for location in all_locations:
        rooms = [
            Room(location_id=location.id, name=name, capacity=capacity, price_per_night=price, amenities=amenities)
            for name, capacity, price, amenities in ROOM_TEMPLATE
        ]
        db.add_all(rooms)
        db.flush()

        for room in rooms[:2]:
            check_in_offset, check_out_offset = RESERVATION_OFFSET_POOL[reservation_index % len(RESERVATION_OFFSET_POOL)]
            db.add(
                Reservation(
                    room_id=room.id,
                    guest_name=GUEST_NAMES[reservation_index % len(GUEST_NAMES)],
                    check_in=today + timedelta(days=check_in_offset),
                    check_out=today + timedelta(days=check_out_offset),
                    assistant_id=assistant_cycle[reservation_index % len(assistant_cycle)],
                )
            )
            reservation_index += 1

    db.add(ClientUsage(user_id=user.id, minutes_used=742, minutes_included=1500))
    db.commit()


def _get_owned_location(db: DbSession, user: User, location_id: int) -> Location:
    location = db.scalar(
        select(Location).where(Location.id == location_id, Location.user_id == user.id)
    )
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    return location


def _get_owned_room(db: DbSession, user: User, room_id: int) -> Room:
    room = db.scalar(
        select(Room).join(Location, Room.location_id == Location.id).where(
            Room.id == room_id, Location.user_id == user.id
        )
    )
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return room


def _get_owned_assistant(db: DbSession, user: User, assistant_id: int) -> Assistant:
    assistant = db.scalar(
        select(Assistant)
        .where(Assistant.id == assistant_id, Assistant.user_id == user.id)
        .options(selectinload(Assistant.locations))
    )
    if not assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assistant not found")
    return assistant


@router.get("/assistants", response_model=list[AssistantOut])
def list_assistants(current_user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    _ensure_demo_data(db, current_user)

    assistants = db.scalars(
        select(Assistant)
        .where(Assistant.user_id == current_user.id)
        .options(selectinload(Assistant.locations))
        .order_by(Assistant.id)
    ).all()
    return assistants


@router.patch("/assistants/{assistant_id}", response_model=AssistantOut)
def update_assistant(
    assistant_id: int,
    payload: AssistantUpdate,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    assistant = _get_owned_assistant(db, current_user, assistant_id)

    data = payload.model_dump(exclude_unset=True, exclude={"location_ids"})
    for field, value in data.items():
        setattr(assistant, field, value)

    if payload.location_ids is not None:
        locations = db.scalars(
            select(Location).where(
                Location.id.in_(payload.location_ids),
                Location.user_id == current_user.id,
            )
        ).all()
        found_ids = {location.id for location in locations}
        missing = set(payload.location_ids) - found_ids
        if missing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
        assistant.locations = list(locations)

    db.commit()
    db.refresh(assistant)
    return assistant


@router.get("/locations", response_model=list[LocationOut])
def list_locations(current_user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    _ensure_demo_data(db, current_user)

    return db.scalars(
        select(Location).where(Location.user_id == current_user.id).order_by(Location.id)
    ).all()


@router.post("/locations", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
def create_location(
    payload: LocationCreate,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    location = Location(
        user_id=current_user.id,
        name=payload.name,
        address=payload.address,
        description=payload.description,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


def _build_rooms_out(location: Location) -> list[RoomOut]:
    today = date.today()
    rooms_out = []
    for room in location.rooms:
        current = next(
            (r for r in room.reservations if r.check_in <= today <= r.check_out),
            None,
        )
        rooms_out.append(
            RoomOut(
                id=room.id,
                name=room.name,
                capacity=room.capacity,
                price_per_night=room.price_per_night,
                amenities=room.amenities,
                current_reservation=ReservationOut.model_validate(current) if current else None,
            )
        )
    return rooms_out


def _get_location_with_rooms(db: DbSession, user: User, location_id: int) -> Location:
    location = db.scalar(
        select(Location)
        .where(Location.id == location_id, Location.user_id == user.id)
        .options(selectinload(Location.rooms).selectinload(Room.reservations))
    )
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    return location


@router.get("/locations/{location_id}", response_model=LocationDetailOut)
def get_location_detail(
    location_id: int,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    _ensure_demo_data(db, current_user)

    location = _get_location_with_rooms(db, current_user, location_id)

    return LocationDetailOut(
        id=location.id,
        name=location.name,
        address=location.address,
        description=location.description,
        latitude=location.latitude,
        longitude=location.longitude,
        rooms=_build_rooms_out(location),
    )


@router.put("/locations/{location_id}", response_model=LocationDetailOut)
def update_location(
    location_id: int,
    payload: LocationCreate,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    location = _get_location_with_rooms(db, current_user, location_id)

    location.name = payload.name
    location.address = payload.address
    location.description = payload.description
    location.latitude = payload.latitude
    location.longitude = payload.longitude
    db.commit()
    db.refresh(location)

    return LocationDetailOut(
        id=location.id,
        name=location.name,
        address=location.address,
        description=location.description,
        latitude=location.latitude,
        longitude=location.longitude,
        rooms=_build_rooms_out(location),
    )


@router.post("/locations/{location_id}/rooms", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
def create_room(
    location_id: int,
    payload: RoomCreate,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    location = _get_owned_location(db, current_user, location_id)

    room = Room(
        location_id=location.id,
        name=payload.name,
        capacity=payload.capacity,
        price_per_night=payload.price_per_night,
        amenities=payload.amenities,
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    return RoomOut(
        id=room.id,
        name=room.name,
        capacity=room.capacity,
        price_per_night=room.price_per_night,
        amenities=room.amenities,
        current_reservation=None,
    )


@router.put("/rooms/{room_id}", response_model=RoomOut)
def update_room(
    room_id: int,
    payload: RoomCreate,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    room = _get_owned_room(db, current_user, room_id)
    room.name = payload.name
    room.capacity = payload.capacity
    room.price_per_night = payload.price_per_night
    room.amenities = payload.amenities
    db.commit()
    db.refresh(room)

    today = date.today()
    current = next(
        (r for r in room.reservations if r.check_in <= today <= r.check_out),
        None,
    )

    return RoomOut(
        id=room.id,
        name=room.name,
        capacity=room.capacity,
        price_per_night=room.price_per_night,
        amenities=room.amenities,
        current_reservation=ReservationOut.model_validate(current) if current else None,
    )


@router.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    room = _get_owned_room(db, current_user, room_id)
    db.delete(room)
    db.commit()


@router.get("/reservations", response_model=list[ReservationDetailOut])
def list_reservations(current_user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    _ensure_demo_data(db, current_user)

    rows = db.execute(
        select(Reservation, Room.name, Room.location_id, Location.name, Assistant.name)
        .join(Room, Reservation.room_id == Room.id)
        .join(Location, Room.location_id == Location.id)
        .outerjoin(Assistant, Reservation.assistant_id == Assistant.id)
        .where(Location.user_id == current_user.id)
        .order_by(Reservation.check_in)
    ).all()

    return [
        ReservationDetailOut(
            id=reservation.id,
            guest_name=reservation.guest_name,
            check_in=reservation.check_in,
            check_out=reservation.check_out,
            room_id=reservation.room_id,
            room_name=room_name,
            location_id=location_id,
            location_name=location_name,
            assistant_id=reservation.assistant_id,
            assistant_name=assistant_name,
        )
        for reservation, room_name, location_id, location_name, assistant_name in rows
    ]


@router.get("/usage/me", response_model=UsageOut)
def get_usage(current_user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    _ensure_demo_data(db, current_user)

    usage = db.scalar(select(ClientUsage).where(ClientUsage.user_id == current_user.id))
    return usage
