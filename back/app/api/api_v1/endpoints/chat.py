from fastapi import APIRouter, Depends, HTTPException
import logging

from back.app.models import ChatRequest, ChatResponse
from back.app.request_audit import persist_api_io
from back.app.dependencies import (
    get_mcp_client,
    get_memory_manager_instance,
    get_agent,
)
from back.pharma_mcp.client import MCPClient

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/ask", response_model=ChatResponse)
async def ask_question(
    request: ChatRequest,
    mcp_client: MCPClient = Depends(get_mcp_client),
):
    """
    Unified chat endpoint - tanya apapun tentang obat
    
    Agent otomatis menentukan tool yang sesuai:
    - Pertanyaan tentang stok → search_obat_by_stock
    - Pertanyaan tentang harga → search_obat_by_harga
    - Pertanyaan tentang kadaluarsa → search_obat_by_kadaluarsa
    - Pertanyaan umum → ask_question (RAG)

    Request: 
    - **question**: Pertanyaan apapun (contoh: "Stok paracetamol berapa?", "Obat mana yang paling murah?")
    - **user_id**: User identifier (opsional)
    """
    try:
        user_id = request.user_id or "user_1"
        memory = get_memory_manager_instance().get_or_create_memory(user_id)
        
        logger.info(f"[USER {user_id}] Question: {request.question}")
        memory.add_message("user", request.question)
        
        # FastAPI bridge: seluruh orkestrasi ada di AI Agent
        agent = get_agent()
        conversation_history = memory.get_conversation_history(limit=5)
        orchestrated = await agent.run_chat_turn(
            mcp_client=mcp_client,
            question=request.question,
            conversation_history=conversation_history,
        )

        final = orchestrated.get("answer", "Maaf, terjadi kesalahan memproses jawaban.")
        tool = orchestrated.get("tool_used")

        memory.add_message("assistant", final)
        logger.info(f"[SUCCESS] Response saved to memory")

        response_payload = {
            "answer": final,
            "tool_used": tool,
            "user_id": user_id,
        }
        persist_api_io(
            endpoint="/api/v1/chat/ask",
            method="POST",
            request_data=request,
            response_data=response_payload,
            status="success",
            user_id=user_id,
        )
        
        return ChatResponse(
            answer=final,
            tool_used=tool,
            user_id=user_id
        )
        
    except Exception as e:
        persist_api_io(
            endpoint="/api/v1/chat/ask",
            method="POST",
            request_data=request,
            response_data={"detail": str(e)},
            status="error",
            user_id=request.user_id,
        )
        logger.error(f"[ERROR] Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
