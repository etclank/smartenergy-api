# app/core/config.py
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Any, Optional


class Settings(BaseSettings):
    # App
    env: str = Field(default="dev", validation_alias=AliasChoices("ENV"))
    api_host: str = Field(default="0.0.0.0", validation_alias=AliasChoices("API_HOST"))
    api_port: int = Field(default=8000, validation_alias=AliasChoices("API_PORT"))

    # Database
    database_url: str = Field(default="", validation_alias=AliasChoices("DATABASE_URL"))

    # Redis / Cache
    redis_url: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("REDIS_URL"),
        description="External Redis URL (Upstash or local redis://). Leave empty to disable caching."
    )
    cache_ttl_seconds: int = Field(
        default=60, validation_alias=AliasChoices("CACHE_TTL_SECONDS"),
        description="Default cache lifetime (seconds)."
    )

    # JWT
    jwt_secret: str = Field(default="", validation_alias=AliasChoices("JWT_SECRET"))
    jwt_algorithm: str = Field(default="HS256", validation_alias=AliasChoices("JWT_ALG"))
    jwt_expire_minutes: int = Field(
        default=60, validation_alias=AliasChoices("JWT_EXPIRE_MINUTES")
    )

    # Frontend & Demo
    frontend_origins: List[str] = []
    seed_demo: str | int | bool = Field(default=1, validation_alias=AliasChoices("SEED_DEMO"))

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    # --- Helpers -------------------------------------------------------------
    def _parse_comma_list(self, v: str | list[str] | None) -> list[str]:
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return [s.strip() for s in v.split(",") if s.strip()]

    def __init__(self, **values: Any) -> None:
        super().__init__(**values)
        # Normalize frontend_origins
        if isinstance(self.frontend_origins, str):
            self.frontend_origins = self._parse_comma_list(self.frontend_origins)
        # Normalize empty redis_url to None
        if not self.redis_url:
            self.redis_url = None


settings = Settings()
