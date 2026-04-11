import sys
import os
import logging

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stderr)],
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)

from mcp.server.fastmcp import FastMCP
from back.database.pgvektor import get_pgvector_connection
from back.core.rag import RAGPipeline
from back.core.memory import get_memory_manager
from back.pharma_mcp.router import register_tools


def create_server():
    mcp = FastMCP("Pharma MCP Server")

    pg_conn = None
    try:
        pg_conn = get_pgvector_connection()
        logger.info("Database connected")
    except Exception as e:
        logger.error(f"DB error: {e}")

    rag_pipeline = None
    try:
        if pg_conn:
            rag_pipeline = RAGPipeline(db_connection=pg_conn)
            logger.info("RAG ready")
    except Exception as e:
        logger.error(f"RAG error: {e}")

    try:
        get_memory_manager()
        logger.info("Memory manager ready")
    except Exception as e:
        logger.error(f"Memory init error: {e}")

    register_tools(mcp, pg_conn=pg_conn, rag_pipeline=rag_pipeline)
    return mcp


mcp = create_server()

if __name__ == "__main__":
    logger.info("MCP Server Running...")
    mcp.run()