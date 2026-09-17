# Train.me — wskazówki dla Claude Code

## Konwencje

- **Adresy URL / ścieżki routingu zawsze po angielsku, bez polskich znaków ani słów.** UI, treści i komunikaty w bazie mogą być po polsku, ale segmenty ścieżek (np. `/assistants`, nie `/asystenci`) muszą być angielskimi, ASCII-safe slugami.

## Struktura projektu

- `backend/` — FastAPI + SQLAlchemy + Alembic (SQLite), zależności przez `uv` (`uv sync`, `uv run ...`, `uv add <pakiet>`)
- `frontend/` — Svelte 5 + Vite, prosty router oparty o History API (`pathByView`/`viewByPath` w `App.svelte`) — bez zewnętrznej biblioteki routingu

## Uruchamianie

```
cd backend && uv run alembic upgrade head && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

Szczegóły w `README.md`.
