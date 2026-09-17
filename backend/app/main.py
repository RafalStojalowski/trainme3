from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assistants import router as assistants_router
from app.auth import router as auth_router
from app.config import settings
from app.database import get_db
from app.models import Greeting
from app.schemas import GreetingOut

app = FastAPI(title="Train.me API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,  # wymagane, by przeglądarka wysyłała ciasteczko sesji do innego originu (Vite dev server)
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(assistants_router)


@app.get("/api/greeting", response_model=GreetingOut)
def get_greeting(db: Session = Depends(get_db)):
    greeting = db.scalar(select(Greeting).limit(1))
    return greeting
