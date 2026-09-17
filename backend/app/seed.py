from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assistants import _ensure_demo_data
from app.models import User
from app.security import hash_password

DEMO_EMAIL = "demo@trainme.pl"
DEMO_PASSWORD = "demo1234"


def seed_demo_data(db: Session) -> None:
    # Konto demo dostaje ten sam bogaty zestaw danych, co każdy nowy użytkownik
    # przy pierwszym wejściu do aplikacji (patrz _ensure_demo_data w assistants.py).
    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if not user:
        user = User(
            email=DEMO_EMAIL,
            full_name="Konto demo",
            hashed_password=hash_password(DEMO_PASSWORD),
        )
        db.add(user)
        db.flush()

    _ensure_demo_data(db, user)
