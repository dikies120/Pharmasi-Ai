import sys
import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from back.app.config import settings
from back.app.dependencies import set_server_script_path, get_mcp_client, close_mcp_client
from back.app.api.api_v1.router_api import router as api_v1_router
from back.app.middleware.cors import setup_cors
from back.app.middleware.logging import LoggingMiddleware
from back.app.middleware.error_handler import (
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


import pymongo
from back.core.settings import settings as core_settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    try:
        masked_url = core_settings.MONGO_URL
        if "@" in masked_url:
            parts = masked_url.split("@")
            masked_url = "mongodb://***:***@" + parts[1]
        logger.info(f" [DEBUG] Memeriksa koneksi MongoDB...")
        logger.info(f" [DEBUG] Host: {masked_url} | Database: {core_settings.MONGO_DB}")
        
        client = pymongo.MongoClient(core_settings.MONGO_URL, serverSelectionTimeoutMS=3000)
        client.admin.command('ping')
        logger.info(" [DEBUG] MongoDB berhasil terkoneksi dengan sukses!")
    except Exception as e:
        logger.error(f" [DEBUG] Koneksi MongoDB GAGAL saat startup: {e}")

    server_script = Path(__file__).resolve().parents[1] / "pharma_mcp" / "server.py"
    set_server_script_path(str(server_script))
    logger.info(f"MCP Server script: {server_script}")
    
    try:
        mcp_client = await get_mcp_client()
        logger.info(" MCP Client connected successfully")
        
        tools = await mcp_client.list_tools()
        logger.info(f" Available MCP Tools: {', '.join(tools)}")
    except Exception as e:
        logger.error(f" Failed to initialize MCP Client: {e}")
        raise
    
    yield
    
    logger.info("Shutting down...")
    await close_mcp_client()
    logger.info("Goodbye!")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Pharmasi AI Backend API - Business Logic & AI/LLM Integration",
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    
    setup_cors(app)
    
    app.add_middleware(LoggingMiddleware)
    
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    app.include_router(api_v1_router)
    
    @app.get("/")
    async def root():
        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "openapi": "/openapi.json",
            "status": "running"
        }
    
    return app


app = create_app()