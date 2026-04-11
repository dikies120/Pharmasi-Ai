from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import logging

from back.pharma_mcp.client import MCPClient
from back.app.request_audit import persist_api_io
from back.app.dependencies import get_mcp_client, get_agent

router = APIRouter(prefix="/dispensing", tags=["dispensing"])
logger = logging.getLogger(__name__)


class DispensingRequest(BaseModel):
    prescription_id: str


@router.post("/")
async def process_dispensing(req: DispensingRequest, mcp_client: MCPClient = Depends(get_mcp_client)):
    """FastAPI bridge: preview dispensing diproses oleh AI Agent."""
    try:
        agent = get_agent()
        result = await agent.run_dispensing_preview(mcp_client, req.prescription_id)
        persist_api_io(
            endpoint="/api/v1/dispensing/",
            method="POST",
            request_data=req,
            response_data=result,
            status=result.get("status", "success"),
            user_id=req.prescription_id,
        )
        return result
    except Exception as e:
        persist_api_io(
            endpoint="/api/v1/dispensing/",
            method="POST",
            request_data=req,
            response_data={"detail": str(e)},
            status="error",
            user_id=req.prescription_id,
        )
        logger.error(f"Error in dispensing preview orchestration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete")
async def complete_dispensing(req: DispensingRequest, mcp_client: MCPClient = Depends(get_mcp_client)):
    """FastAPI bridge: penyelesaian dispensing (update stok) via AI Agent -> MCP."""
    try:
        agent = get_agent()
        result = await agent.run_dispensing_complete(mcp_client, req.prescription_id)
        persist_api_io(
            endpoint="/api/v1/dispensing/complete",
            method="POST",
            request_data=req,
            response_data=result,
            status=result.get("status", "success"),
            user_id=req.prescription_id,
        )
        return result
    except Exception as e:
        persist_api_io(
            endpoint="/api/v1/dispensing/complete",
            method="POST",
            request_data=req,
            response_data={"detail": str(e)},
            status="error",
            user_id=req.prescription_id,
        )
        logger.error(f"Error completing dispensing via agent orchestration: {e}")
        raise HTTPException(status_code=500, detail=str(e))
