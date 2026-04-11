from fastapi import APIRouter, Depends

from back.app.models import HealthResponse
from back.app.config import settings
from back.app.request_audit import persist_api_io
from back.app.dependencies import get_mcp_client
from back.pharma_mcp.client import MCPClient

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=HealthResponse)
async def health_check(
    mcp_client: MCPClient = Depends(get_mcp_client),
):
    """
    Check health dan status MCP connection
    """
    mcp_connected = mcp_client.session is not None
    
    response_payload = HealthResponse(
        status="ok" if mcp_connected else "degraded",
        mcp_connected=mcp_connected,
        version=settings.app_version
    )
    persist_api_io(
        endpoint="/api/v1/health/",
        method="GET",
        response_data=response_payload,
        status="success" if mcp_connected else "degraded",
    )
    return response_payload


@router.get("/status")
async def status():
    response_payload = {
        "status": "running",
        "app": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug,
    }
    persist_api_io(
        endpoint="/api/v1/health/status",
        method="GET",
        response_data=response_payload,
        status="success",
    )
    return response_payload
