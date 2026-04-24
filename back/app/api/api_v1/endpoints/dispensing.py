from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import logging

from back.pharma_mcp.client import MCPClient
from back.app.request_audit import persist_api_io
from back.app.dependencies import get_mcp_client, get_agent
from back.database.redis import get_cache, set_cache, delete_cache

router = APIRouter(prefix="/dispensing", tags=["dispensing"])
logger = logging.getLogger(__name__)
DISPENSING_PREVIEW_CACHE_TTL_SECONDS = 3600  # 1 jam
DISPENSING_PREVIEW_CACHE_VERSION = "v8"


class DispensingRequest(BaseModel):
    prescription_id: str
    include_llm_reasoning: bool = True


def _build_dispensing_preview_cache_key(prescription_id: str, include_llm_reasoning: bool) -> str:
    normalized = str(prescription_id or "").strip().lower()
    mode = "llm" if include_llm_reasoning else "fast"
    return f"dispensing_preview:{DISPENSING_PREVIEW_CACHE_VERSION}:{mode}:{normalized}"


def _clear_dispensing_preview_cache(prescription_id: str) -> None:
    delete_cache(_build_dispensing_preview_cache_key(prescription_id, include_llm_reasoning=False))
    delete_cache(_build_dispensing_preview_cache_key(prescription_id, include_llm_reasoning=True))


@router.post("/")
async def process_dispensing(req: DispensingRequest, mcp_client: MCPClient = Depends(get_mcp_client)):
    """FastAPI bridge: preview dispensing diproses oleh AI Agent."""
    try:
        # Auto mode: dispensing screening selalu melalui LLM, tetap dipercepat dengan cache.
        include_llm_reasoning = True

        cache_key = _build_dispensing_preview_cache_key(req.prescription_id, include_llm_reasoning)
        cached_result = get_cache(cache_key)
        if isinstance(cached_result, dict):
            cached_result["cache"] = {
                "hit": True,
                "ttl_seconds": DISPENSING_PREVIEW_CACHE_TTL_SECONDS,
            }
            persist_api_io(
                endpoint="/api/v1/dispensing/",
                method="POST",
                request_data=req,
                response_data=cached_result,
                status="success",
                user_id=req.prescription_id,
            )
            return cached_result

        agent = get_agent()
        result = await agent.run_dispensing_preview(
            mcp_client,
            req.prescription_id,
            include_llm_reasoning=include_llm_reasoning,
        )
        if isinstance(result, dict):
            result["cache"] = {
                "hit": False,
                "ttl_seconds": DISPENSING_PREVIEW_CACHE_TTL_SECONDS,
            }

        if isinstance(result, dict) and result.get("status") == "success":
            set_cache(cache_key, result, DISPENSING_PREVIEW_CACHE_TTL_SECONDS)

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
        if isinstance(result, dict) and result.get("status") == "success":
            _clear_dispensing_preview_cache(req.prescription_id)
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
