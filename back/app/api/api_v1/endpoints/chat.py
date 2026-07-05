from fastapi import APIRouter, Depends, HTTPException
import logging

from back.app.models import ChatRequest, ChatResponse
from back.app.request_audit import persist_api_io
from back.app.dependencies import (
    get_mcp_client,
    get_memory_manager_instance,
    get_agent,
)
from back.app.middleware.auth import get_current_user, require_pharmacist_or_admin
from back.pharma_mcp.client import MCPClient

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


async def _process_chat_request(
    request: ChatRequest,
    mcp_client: MCPClient,
    role: str,
    endpoint_path: str,
    user_name: str = ""
) -> ChatResponse:
    try:
        user_id = request.user_id or "user_1"
        memory = get_memory_manager_instance().get_or_create_memory(user_id)
        
        logger.info(f"[USER {user_id}][ROLE {role}] Question: {request.question}")
        memory.add_message("user", request.question, name=user_name)

        cached_context = memory.get_context() or {}
        if not isinstance(cached_context, dict):
            cached_context = {}
        
        agent = get_agent()
        conversation_history = memory.get_conversation_history(limit=5)
        orchestrated = await agent.run_chat_turn(
            mcp_client=mcp_client,
            question=request.question,
            conversation_history=conversation_history,
            memory_context=cached_context,
            role=role,
            patient_context=request.patient_context,
        )

        final = orchestrated.get("answer", "Maaf, terjadi kesalahan memproses jawaban.")
        tool = orchestrated.get("tool_used")
        model_name = orchestrated.get("model_name")
        context_updates = orchestrated.get("context_updates")

        if isinstance(context_updates, dict) and context_updates:
            merged_context = {**cached_context, **context_updates, "last_question": request.question}
            memory.set_context(merged_context)

        memory.add_message("assistant", final, name="Pharmasi AI")
        logger.info(f"[SUCCESS] Response saved to memory")

        response_payload = {
            "answer": final,
            "tool_used": tool,
            "user_id": user_id,
            "model_name": model_name,
        }
        persist_api_io(
            endpoint=endpoint_path,
            method="POST",
            request_data=request,
            response_data=response_payload,
            status="success",
            user_id=user_id,
        )
        
        return ChatResponse(
            answer=final,
            tool_used=tool,
            user_id=user_id,
            model_name=model_name,
        )
        
    except Exception as e:
        persist_api_io(
            endpoint=endpoint_path,
            method="POST",
            request_data=request,
            response_data={"detail": str(e)},
            status="error",
            user_id=request.user_id,
        )
        logger.error(f"[ERROR] Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/pharmacy/ask", response_model=ChatResponse)
async def ask_pharmacy(
    request: ChatRequest,
    mcp_client: MCPClient = Depends(get_mcp_client),
    current_user: dict = Depends(require_pharmacist_or_admin),
):
    user_name = current_user.get("name", "Apoteker")
    return await _process_chat_request(request, mcp_client, "pharmacist", "/api/v1/chat/pharmacy/ask", user_name)


@router.post("/patient/ask", response_model=ChatResponse)
async def ask_patient(
    request: ChatRequest,
    mcp_client: MCPClient = Depends(get_mcp_client),
    current_user: dict = Depends(get_current_user),
):
    user_name = current_user.get("name", "Pasien")
    return await _process_chat_request(request, mcp_client, "patient", "/api/v1/chat/patient/ask", user_name)
