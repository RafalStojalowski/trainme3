from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="")

    environment: str = "development"

    frontend_origin: str = "http://localhost:5173"

    session_cookie_name: str = "session_id"
    session_ttl_minutes: int = 60 * 24 * 7  # 7 dni, odświeżane przy każdym użyciu
    session_cookie_secure: bool | None = None
    session_cookie_samesite: str = "lax"
    session_cookie_domain: str | None = None

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"

    @model_validator(mode="after")
    def _normalize(self) -> "Settings":
        if self.session_cookie_secure is None:
            # Lokalnie serwer działa po HTTP, więc ciasteczko "Secure" nigdy by nie dotarło.
            self.session_cookie_secure = not self.is_development
        if not self.session_cookie_domain:
            self.session_cookie_domain = None
        return self


settings = Settings()
