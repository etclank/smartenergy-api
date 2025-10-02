# app/config.py
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    env: str = Field(default="dev", validation_alias=AliasChoices("ENV"))
    api_host: str = Field(default="0.0.0.0", validation_alias=AliasChoices("API_HOST"))
    api_port: int = Field(default=8000, validation_alias=AliasChoices("API_PORT"))

    # DB / Redis
    # Defaults are empty so mypy is happy, but real values should come from env/.env
    database_url: str = Field(default="", validation_alias=AliasChoices("DATABASE_URL"))
    redis_url: str = Field(default="", validation_alias=AliasChoices("REDIS_URL"))

    # Cache
    cache_ttl_seconds: int = 60

    # JWT
    jwt_secret: str = Field(default="", validation_alias=AliasChoices("JWT_SECRET"))
    jwt_alg: str = Field(default="HS256", validation_alias=AliasChoices("JWT_ALG"))
    jwt_expire_minutes: int = Field(
        default=60, validation_alias=AliasChoices("JWT_EXPIRE_MINUTES")
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,  # don't override defaults with empty values
        extra="ignore",
    )


settings = Settings()
