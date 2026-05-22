from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = ""
    jwt_secret: str = ""
    initial_admin_email: str = ""
    initial_admin_password: str = ""
    cors_origins: str = "http://localhost:5173,http://localhost:8000"
    upload_max_mb: int = 25
    storage_dir: str = "backend/storage"
    soundfont_base_url: str = "https://gleitz.github.io/midi-js-soundfonts/FluidR3_GM/"
    omr_audiveris_path: str = ""
    omr_homr_path: str = ""
    omr_oemer_path: str = ""
    openai_api_key: str = ""
    render_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            return self.database_url.replace("postgres://", "postgresql://", 1)
        data_dir = Path("backend/data")
        data_dir.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{data_dir / 'dev.db'}"

    @property
    def effective_jwt_secret(self) -> str:
        return self.jwt_secret or "local-development-only-secret-change-me"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
