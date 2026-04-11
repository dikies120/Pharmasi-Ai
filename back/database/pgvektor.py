from psycopg2 import connect
from back.core.settings import settings

def get_pgvector_connection():
    return connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD
    )

def get_cursor():
    conn = get_pgvector_connection()
    cur = conn.cursor()
    return conn, cur

# if __name__ == "__main__":
#     try:
#         conn = get_pgvector_connection()
#         print("PostgreSQL connected successfully")

#         conn.close()
#     except Exception as e:
#         print("PostgreSQL connection failed")
#         print("Reason:", e)

# pgvektor = get_pgvector_connection