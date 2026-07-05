from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# settings.py ada di back/core/settings.py
# parent   = back/core
# parent.parent = back/   <-- ini yang kita mau, karena .env ada di back/.env
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str

    MONGO_URL: str
    MONGO_DB: str

    OLLAMA_HOST: str
    OLLAMA_MODEL: str

    EMBEDDING_MODEL: str
    RERANK_MODEL: str
    EMBEDDING_DEVICE: str

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
