from psycopg2 import connect, OperationalError
from back.core.settings import settings
import logging

logger = logging.getLogger(__name__)


def get_pgvector_connection():
    return connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD
    )


def get_db_connection():
    try:
        conn = get_pgvector_connection()
        # Reset any aborted transaction
        conn.rollback()
        return conn
    except OperationalError as e:
        logger.error(f"PostgreSQL connection failed: {e}")
        return None


def get_cursor():
    conn = get_pgvector_connection()
    cur = conn.cursor()
    return conn, cur
