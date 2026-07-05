from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import logging
from back.pharma_mcp.client import MCPClient
from back.app.request_audit import persist_api_io
from back.app.dependencies import get_mcp_client

from back.app.middleware.auth import require_pharmacist_or_admin

router = APIRouter(
    prefix="/informasi-obat",
    tags=["informasi-obat"],
    dependencies=[Depends(require_pharmacist_or_admin)]
)
logger = logging.getLogger(__name__)

class InfoRequesst(BaseModel):
    query: str

@router.post("/")
async def get_informasi(req: InfoRequesst, mcp_client: MCPClient = Depends(get_mcp_client)):
    
    try:
        result = await mcp_client.call_tool("ask_question", {"question": req.query})

        response_payload = {
            "status": "success",
            "query": req.query,
            "answer": result
        }
        persist_api_io(
            endpoint="/api/v1/informasi-obat/",
            method="POST",
            request_data=req,
            response_data=response_payload,
            status="success",
        )
        return response_payload
    except Exception as e:
        persist_api_io(
            endpoint="/api/v1/informasi-obat/",
            method="POST",
            request_data=req,
            response_data={"detail": str(e)},
            status="error",
        )
        raise HTTPException(status_code=500, detail=str(e))
