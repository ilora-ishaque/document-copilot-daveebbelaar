from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    database_url: str

    openai_api_key: str
    openai_embedding_model: str
    openai_embedding_dimensions: int

    allowed_origins: str

    @field_validator("database_url")
    @classmethod
    def _use_psycopg3(cls, value: str) -> str:
        # This project depends on psycopg[binary] (psycopg3), not psycopg2, which
        # SQLAlchemy defaults to for a plain "postgresql://" / "postgres://" scheme.
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        return value

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
