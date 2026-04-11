from fastapi import APIRouter, Depends, HTTPException, Query
import logging
from back.pharma_mcp.client import MCPClient
from back.app.request_audit import persist_api_io
from back.app.dependencies import get_mcp_client, get_agent
from typing import Optional

router = APIRouter(prefix="/monitoring-stok", tags=["monitoring-stok"])
logger = logging.getLogger(__name__)

@router.get("/")
async def get_stok(mcp_client: MCPClient = Depends(get_mcp_client)):
    """FastAPI bridge: delegasikan pengambilan stok ke AI Agent."""
    try:
        agent = get_agent()
        result = await agent.run_monitoring_realtime(mcp_client)
        if result.get("status") == "error":
            persist_api_io(
                endpoint="/api/v1/monitoring-stok/",
                method="GET",
                response_data=result,
                status="error",
            )
            return result
        response_payload = {
            "status": "success",
            "message": "Data stok berhasil diambil via AI Agent.",
            "data": result.get("data", []),
            "actions": ["calculate_stock_status", "detect_low_stock"]
        }
        persist_api_io(
            endpoint="/api/v1/monitoring-stok/",
            method="GET",
            response_data=response_payload,
            status="success",
        )
        return response_payload
    except Exception as e:
        persist_api_io(
            endpoint="/api/v1/monitoring-stok/",
            method="GET",
            response_data={"detail": str(e)},
            status="error",
        )
        logger.error(f"Error in monitoring stok: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/realtime")
async def get_stok_realtime(
    nama_obat: Optional[str] = Query(None, description="Filter by patient name"),
    lokasi: Optional[str] = Query(None, description="Filter by location"),
    status: Optional[str] = Query(None, description="Filter by stock status"),
    mcp_client: MCPClient = Depends(get_mcp_client)
):
    try:
        agent = get_agent()
        request_data = {
            "nama_obat": nama_obat,
            "lokasi": lokasi,
            "status": status,
        }
        result = await agent.run_monitoring_realtime(
            mcp_client,
            nama_obat=nama_obat,
            lokasi=lokasi,
            status=status,
        )
        persist_api_io(
            endpoint="/api/v1/monitoring-stok/realtime",
            method="GET",
            request_data=request_data,
            response_data=result,
            status=result.get("status", "success"),
        )
        return result
    except Exception as e:
        persist_api_io(
            endpoint="/api/v1/monitoring-stok/realtime",
            method="GET",
            request_data={"nama_obat": nama_obat, "lokasi": lokasi, "status": status},
            response_data={"detail": str(e)},
            status="error",
        )
        logger.error(f"Error fetching realtime stock via MCP: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics")
async def get_stok_analytics(mcp_client: MCPClient = Depends(get_mcp_client)):
    try:
        agent = get_agent()
        result = await agent.run_monitoring_analytics(mcp_client)
        persist_api_io(
            endpoint="/api/v1/monitoring-stok/analytics",
            method="GET",
            response_data=result,
            status=result.get("status", "success"),
        )
        return result
    except Exception as e:
        persist_api_io(
            endpoint="/api/v1/monitoring-stok/analytics",
            method="GET",
            response_data={"detail": str(e)},
            status="error",
        )
        logger.error(f"Error fetching analytics data via MCP: {e}")
        raise HTTPException(status_code=500, detail=str(e))
