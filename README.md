# Train.me

Backend: FastAPI + SQLAlchemy + Alembic (SQLite).
Frontend: Svelte 5 + Vite. Strona pobiera tekst powitania z API i wyświetla go, zachowując styl (kolory, font Inter, logo) ze strony referencyjnej.

## Backend

Zarządzanie paczkami przez [uv](https://docs.astral.sh/uv/).

```
cd backend
uv sync                       # instaluje zależności do .venv
uv run alembic upgrade head   # tworzy app.db i tabelę greetings
uv run uvicorn app.main:app --reload --port 8000
```

Dodawanie nowej paczki: `uv add <nazwa>`.

### Autentykacja

Sesyjna, oparta o ciasteczko `httpOnly` + tabelę `sessions` w bazie (nie JWT) - dzięki temu sesję da się natychmiast unieważnić (np. wylogowanie, blokada konta) samym usunięciem wiersza. W bazie trzymany jest tylko SHA-256 skrótu tokena, nie sam token.

- `POST /api/auth/register` - `{email, password}`
- `POST /api/auth/login` - `{email, password}`, ustawia ciasteczko `session_id`
- `POST /api/auth/logout` - kasuje sesję w bazie i ciasteczko
- `GET /api/auth/me` - dane zalogowanego użytkownika (401 jeśli brak/wygasła sesja)

Sesja ma sliding expiration (domyślnie 7 dni, `SESSION_TTL_MINUTES`) - każde użycie ją przedłuża.

Konfiguracja produkcyjna: skopiuj `backend/.env.example` do `backend/.env` i ustaw `ENVIRONMENT=production`, `FRONTEND_ORIGIN` na realny origin frontendu oraz uruchom całość po HTTPS (`SESSION_COOKIE_SECURE=true` wymaga HTTPS, inaczej przeglądarka odrzuci ciasteczko). Domyślnie w `ENVIRONMENT=development` ciasteczko jest bez flagi `Secure`, żeby działało po zwykłym HTTP lokalnie.

## Frontend

```
cd frontend
npm install
npm run dev
```

Frontend działa na http://localhost:5173 i proxuje żądania `/api/*` do backendu na porcie 8000.
