from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    env: str = "dev"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # DB / Redis
    database_url: str = "sqlite+aiosqlite:///./app.db"
    redis_url: str = "redis://localhost:6379/0"  # not used by tests yet

    # JWT
    jwt_secret: str = "change-me"
    jwt_alg: str = "HS256"
    jwt_expire_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

settings = Settings()
