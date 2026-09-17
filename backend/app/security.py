import hashlib
import secrets

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def generate_session_token() -> str:
    # Losowy token wysyłany w ciasteczku - kryptograficznie bezpieczny, nie do odgadnięcia.
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    # To, co trafia do bazy - nieodwracalny skrót tokena z ciasteczka.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
