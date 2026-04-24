from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import logging

from back.pharma_mcp.client import MCPClient
from back.app.request_audit import persist_api_io
from back.app.dependencies import get_mcp_client, get_agent
from back.database.redis import get_cache, set_cache

router = APIRouter(prefix="/validasi-obat", tags=["validasi-obat"])
logger = logging.getLogger(__name__)
VALIDASI_CACHE_TTL_SECONDS = 86400  # 24 jam
VALIDASI_CACHE_VERSION = "v173"


class ValidasiRequest(BaseModel):
    patient_id: str


def _build_validasi_cache_key(patient_id: str) -> str:
    normalized = (patient_id or "").strip().lower()
    return f"validasi_result:{VALIDASI_CACHE_VERSION}:{normalized}"


@router.post("/")
async def validate_obat(req: ValidasiRequest, mcp_client: MCPClient = Depends(get_mcp_client)):
    """FastAPI bridge: validasi resep didelegasikan penuh ke AI Agent."""
    try:
        cache_key = _build_validasi_cache_key(req.patient_id)
        cached_result = get_cache(cache_key)
        if isinstance(cached_result, dict):
            cached_result["cache"] = {
                "hit": True,
                "ttl_seconds": VALIDASI_CACHE_TTL_SECONDS,
            }
            flow_trace = cached_result.get("flow_trace") if isinstance(cached_result.get("flow_trace"), dict) else {}
            flow_trace["step_2_fastapi_gateway"] = {
                "status": "done",
                "detail": "Request diproses oleh FastAPI gateway (cache hit)",
            }
            flow_trace["step_6_response_to_ui"] = {
                "status": "done",
                "detail": "Response dikirim ke UI dari cache",
            }
            cached_result["flow_trace"] = flow_trace
            persist_api_io(
                endpoint="/api/v1/validasi-obat/",
                method="POST",
                request_data=req,
                response_data=cached_result,
                status="success",
                user_id=req.patient_id,
            )
            return cached_result

        agent = get_agent()
        result = await agent.run_validasi_obat(
            mcp_client,
            req.patient_id,
        )
        if isinstance(result, dict):
            result["cache"] = {
                "hit": False,
                "ttl_seconds": VALIDASI_CACHE_TTL_SECONDS,
            }
            flow_trace = result.get("flow_trace") if isinstance(result.get("flow_trace"), dict) else {}
            flow_trace["step_2_fastapi_gateway"] = {
                "status": "done",
                "detail": "Request diproses oleh FastAPI gateway",
            }
            flow_trace["step_6_response_to_ui"] = {
                "status": "done",
                "detail": "Response inferensi baru dikirim ke UI",
            }
            result["flow_trace"] = flow_trace

        if isinstance(result, dict) and result.get("status") == "success":
            set_cache(cache_key, result, VALIDASI_CACHE_TTL_SECONDS)

        persist_api_io(
            endpoint="/api/v1/validasi-obat/",
            method="POST",
            request_data=req,
            response_data=result,
            status=result.get("status", "success"),
            user_id=req.patient_id,
        )
        return result
    except Exception as e:
        persist_api_io(
            endpoint="/api/v1/validasi-obat/",
            method="POST",
            request_data=req,
            response_data={"detail": str(e)},
            status="error",
            user_id=req.patient_id,
        )
        logger.error(f"Error in validasi obat orchestration: {e}")
        raise HTTPException(status_code=500, detail=str(e))
