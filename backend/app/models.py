import datetime

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Greeting(Base):
    __tablename__ = "greetings"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(String(255), nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    assistants: Mapped[list["Assistant"]] = relationship(cascade="all, delete-orphan")
    locations: Mapped[list["Location"]] = relationship(cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    # SHA-256 skrótu tokena z ciasteczka - surowy token nigdy nie trafia do bazy,
    # więc wyciek bazy nie pozwala od razu przejąć aktywnych sesji.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped["User"] = relationship(back_populates="sessions")


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")
    description: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")
    # domyślnie środek Warszawy - realne współrzędne nadpisywane przy seedowaniu/edycji
    latitude: Mapped[float] = mapped_column(Float, nullable=False, server_default="52.2297")
    longitude: Mapped[float] = mapped_column(Float, nullable=False, server_default="21.0122")

    rooms: Mapped[list["Room"]] = relationship(cascade="all, delete-orphan")


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="2")
    price_per_night: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    amenities: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")

    reservations: Mapped[list["Reservation"]] = relationship(cascade="all, delete-orphan")


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    guest_name: Mapped[str] = mapped_column(String(255), nullable=False)
    check_in: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    check_out: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    # NULL = rezerwacja wprowadzona ręcznie, bez udziału wirtualnego asystenta.
    assistant_id: Mapped[int | None] = mapped_column(
        ForeignKey("assistants.id", ondelete="SET NULL"), nullable=True
    )


assistant_locations = Table(
    "assistant_locations",
    Base.metadata,
    Column("assistant_id", ForeignKey("assistants.id", ondelete="CASCADE"), primary_key=True),
    Column("location_id", ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True),
)


class Assistant(Base):
    __tablename__ = "assistants"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # "active" | "offline" | "in_call" - "in_call" jest tylko obserwowanym stanem, przełącznik ustawia active/offline
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    voice: Mapped[str] = mapped_column(String(255), nullable=False)
    traits: Mapped[str] = mapped_column(String(2000), nullable=False)
    max_concurrent_calls: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    minutes_used: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    locations: Mapped[list["Location"]] = relationship(secondary=assistant_locations)


class ClientUsage(Base):
    __tablename__ = "client_usage"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    minutes_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minutes_included: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
