import sys
import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from back.app.config import settings
from back.app.dependencies import set_server_script_path, get_mcp_client, close_mcp_client
from back.app.api.api_v1.router_api import router as api_v1_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
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
        description="API bridge antara Frontend dan MCP Server",
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router)
    
    @app.get("/")
    async def root():
        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "openapi": "/openapi.json",
        }
    
    return app


app = create_app()