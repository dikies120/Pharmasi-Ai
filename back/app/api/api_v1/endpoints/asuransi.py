from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from back.pharma_mcp.client import MCPClient
from back.app.request_audit import persist_api_io
from back.app.dependencies import get_mcp_client, get_agent

from back.app.middleware.auth import require_pharmacist_or_admin

router = APIRouter(
    prefix="/asuransi",
    tags=["asuransi"],
    dependencies=[Depends(require_pharmacist_or_admin)]
)
logger = logging.getLogger(__name__)


class AsuransiRequest(BaseModel):
    kartu_id: str
    jenis: str


class ProsesBayarRequest(BaseModel):
    kartu_id: str
    jenis: str
    total_tagihan: Optional[float] = 0


@router.post("/")
async def verifikasi_asuransi(req: AsuransiRequest, mcp_client: MCPClient = Depends(get_mcp_client)):
    """FastAPI bridge: verifikasi asuransi diproses oleh AI Agent."""
    try:
        agent = get_agent()
        result = await agent.run_insurance_verification(mcp_client, req.kartu_id, req.jenis)
        persist_api_io(
            endpoint="/api/v1/asuransi/",
            method="POST",
            request_data=req,
            response_data=result,
            status=result.get("status", "success"),
            user_id=req.kartu_id,
        )
        return result
    except Exception as e:
        persist_api_io(
            endpoint="/api/v1/asuransi/",
            method="POST",
            request_data=req,
            response_data={"detail": str(e)},
            status="error",
            user_id=req.kartu_id,
        )
        logger.error(f"Error insurance verification orchestration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/proses-bayar")
async def proses_pembayaran(req: ProsesBayarRequest, mcp_client: MCPClient = Depends(get_mcp_client)):
    """FastAPI bridge: pencatatan pembayaran diproses oleh AI Agent."""
    try:
        agent = get_agent()
        result = await agent.run_payment_process(
            mcp_client,
            kartu_id=req.kartu_id,
            jenis=req.jenis,
            total_tagihan=req.total_tagihan or 0,
        )
        persist_api_io(
            endpoint="/api/v1/asuransi/proses-bayar",
            method="POST",
            request_data=req,
            response_data=result,
            status=result.get("status", "success"),
            user_id=req.kartu_id,
        )
        return result
    except Exception as e:
        persist_api_io(
            endpoint="/api/v1/asuransi/proses-bayar",
            method="POST",
            request_data=req,
            response_data={"detail": str(e)},
            status="error",
            user_id=req.kartu_id,
        )
        logger.error(f"Error processing payment orchestration: {e}")
        raise HTTPException(status_code=500, detail=str(e))
