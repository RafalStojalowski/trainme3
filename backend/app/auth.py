import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.config import settings
from app.database import get_db
from app.models import Session as SessionModel
from app.models import User
from app.schemas import UserCreate, UserLogin, UserOut
from app.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _session_expiry() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=settings.session_ttl_minutes
    )


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        domain=settings.session_cookie_domain,
        max_age=settings.session_ttl_minutes * 60,
        path="/",
    )


def _create_session(db: DbSession, user: User, request: Request) -> str:
    token = generate_session_token()
    db_session = SessionModel(
        token_hash=hash_session_token(token),
        user_id=user.id,
        expires_at=_session_expiry(),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    db.add(db_session)
    db.commit()
    return token


def get_current_user(
    request: Request,
    response: Response,
    db: DbSession = Depends(get_db),
) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token_hash = hash_session_token(token)
    db_session = db.scalar(select(SessionModel).where(SessionModel.token_hash == token_hash))

    now = datetime.datetime.now(datetime.timezone.utc)
    expires_at = db_session.expires_at.replace(tzinfo=datetime.timezone.utc) if db_session else None

    if not db_session or expires_at < now:
        if db_session:
            db.delete(db_session)
            db.commit()
        response.delete_cookie(settings.session_cookie_name, path="/")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    # Sliding expiration - każde użycie przedłuża sesję i odświeża ciasteczko.
    db_session.expires_at = _session_expiry()
    db.commit()
    _set_session_cookie(response, token)

    return db_session.user


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: DbSession = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=UserOut)
def login(payload: UserLogin, request: Request, response: Response, db: DbSession = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))

    # Ta sama wiadomość dla złego maila i złego hasła - nie zdradzamy, które pole było błędne.
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = _create_session(db, user, request)
    _set_session_cookie(response, token)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DbSession = Depends(get_db)):
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        token_hash = hash_session_token(token)
        db_session = db.scalar(select(SessionModel).where(SessionModel.token_hash == token_hash))
        if db_session:
            db.delete(db_session)
            db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
