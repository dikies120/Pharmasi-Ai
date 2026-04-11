"""Graph data endpoints"""
import logging
from fastapi import APIRouter, Depends, HTTPException

from back.app.dependencies import get_mcp_client, get_memory_manager_instance
from back.app.request_audit import persist_api_io
from back.services.graph_data import GraphDataService
from back.database.pgvektor import get_pgvector_connection

router = APIRouter(prefix="/graph", tags=["graph"])
logger = logging.getLogger(__name__)


@router.get("/medicines")
async def get_medicines_graph():
    """Get medicines overview data untuk graph visualization
    
    Returns:
    - total_medicines: Total jumlah obat
    - stock_distribution: Distribusi stok (low, medium, high)
    - price_distribution: Distribusi harga
    - expiry_distribution: Status kadaluarsa
    - medicines: List lengkap obat
    """
    try:
        pg_conn = get_pgvector_connection()
        data = GraphDataService.get_medicines_overview(pg_conn)
        logger.info("Medicines graph data retrieved")
        persist_api_io(
            endpoint="/api/v1/graph/medicines",
            method="GET",
            response_data=data,
            status="success",
        )
        return data
    except Exception as e:
        persist_api_io(
            endpoint="/api/v1/graph/medicines",
            method="GET",
            response_data={"detail": str(e)},
            status="error",
        )
        logger.error(f"Error retrieving medicines graph: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/chat-history")
async def get_chat_history_graph():
    """Get chat history trends untuk graph visualization
    
    Returns:
    - total_chats: Total chat dijalankan
    - most_asked_medicines: Top 5 obat paling ditanya
    - tool_usage: Usage count setiap tool
    """
    try:
        memory_manager = get_memory_manager_instance()
        data = GraphDataService.get_chat_history_trends(memory_manager)
        logger.info("Chat history graph data retrieved")
        persist_api_io(
            endpoint="/api/v1/graph/chat-history",
            method="GET",
            response_data=data,
            status="success",
        )
        return data
    except Exception as e:
        persist_api_io(
            endpoint="/api/v1/graph/chat-history",
            method="GET",
            response_data={"detail": str(e)},
            status="error",
        )
        logger.error(f"Error retrieving chat history graph: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/dashboard")
async def get_dashboard_data():
    """Get combined dashboard data (medicines + chat history)
    
    Returns:
    - medicines: Medicines overview
    - chat_trends: Chat history trends
    """
    try:
        pg_conn = get_pgvector_connection()
        memory_manager = get_memory_manager_instance()
        
        medicines_data = GraphDataService.get_medicines_overview(pg_conn)
        chat_trends = GraphDataService.get_chat_history_trends(memory_manager)
        
        logger.info("Dashboard data retrieved")
        
        response_payload = {
            "medicines": medicines_data,
            "chat_trends": chat_trends,
            "timestamp": str(__import__('datetime').datetime.now())
        }
        persist_api_io(
            endpoint="/api/v1/graph/dashboard",
            method="GET",
            response_data=response_payload,
            status="success",
        )
        return response_payload
    except Exception as e:
        persist_api_io(
            endpoint="/api/v1/graph/dashboard",
            method="GET",
            response_data={"detail": str(e)},
            status="error",
        )
        logger.error(f"Error retrieving dashboard data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
