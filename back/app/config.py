
from back.core.settings import settings as core_settings


class FastAPIConfig:
    app_name: str = "Pharma MCP API"
    app_version: str = "1.0.0"
    debug: bool = False
    api_v1_str: str = "/api/v1"
    mcp_server_enabled: bool = True
    cors_origins: list = ["http://localhost:8501", "http://localhost:3000", "*"]


class Settings:
    def __init__(self):
        self.POSTGRES_HOST = core_settings.POSTGRES_HOST
        self.POSTGRES_PORT = core_settings.POSTGRES_PORT
        self.POSTGRES_DB = core_settings.POSTGRES_DB
        self.POSTGRES_USER = core_settings.POSTGRES_USER
        self.POSTGRES_PASSWORD = core_settings.POSTGRES_PASSWORD
        
        self.REDIS_HOST = core_settings.REDIS_HOST
        self.REDIS_PORT = core_settings.REDIS_PORT
        self.REDIS_PASSWORD = core_settings.REDIS_PASSWORD
        
        self.MONGO_URL = core_settings.MONGO_URL
        self.MONGO_DB = core_settings.MONGO_DB
        
        self.OLLAMA_HOST = core_settings.OLLAMA_HOST
        self.OLLAMA_MODEL = core_settings.OLLAMA_MODEL
        
        self.EMBEDDING_MODEL = core_settings.EMBEDDING_MODEL
        self.RERANK_MODEL = core_settings.RERANK_MODEL
        self.EMBEDDING_DEVICE = core_settings.EMBEDDING_DEVICE
        
        self.app_name = FastAPIConfig.app_name
        self.app_version = FastAPIConfig.app_version
        self.debug = FastAPIConfig.debug
        self.api_v1_str = FastAPIConfig.api_v1_str
        self.mcp_server_enabled = FastAPIConfig.mcp_server_enabled
        self.cors_origins = FastAPIConfig.cors_origins


settings = Settings()
__all__ = ["settings", "core_settings"]
