from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
import logging
from back.pharma_mcp.client import MCPClient
from back.app.request_audit import persist_api_io
from back.app.dependencies import get_mcp_client

router = APIRouter(prefix="/reminder", tags=["reminder"])
logger = logging.getLogger(__name__)

class ReminderRequest(BaseModel):
    patient_id: str
    medicine: str
    schedule: List[str]

@router.post("/")
async def set_reminder(req: ReminderRequest, mcp_client: MCPClient = Depends(get_mcp_client)):
    """Set pengingat obat melalui tool mcp."""
    try:
        result = await mcp_client.call_tool(
            "create_reminder", 
            {"patient_id": req.patient_id, "medicine": req.medicine, "schedule": req.schedule}
        )
        response_payload = {
            "status": "success",
            "data": result
        }
        persist_api_io(
            endpoint="/api/v1/reminder/",
            method="POST",
            request_data=req,
            response_data=response_payload,
            status="success",
            user_id=req.patient_id,
        )
        return response_payload
    except Exception as e:
        persist_api_io(
            endpoint="/api/v1/reminder/",
            method="POST",
            request_data=req,
            response_data={"detail": str(e)},
            status="error",
            user_id=req.patient_id,
        )
        raise HTTPException(status_code=500, detail=str(e))
