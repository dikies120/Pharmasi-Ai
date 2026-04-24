import logging
import re
import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer, CrossEncoder
from back.core.settings import settings


logger = logging.getLogger(__name__)


class RAGPipeline:

    def __init__(
        self,
        db_connection,
        embedding_model_name: str = settings.EMBEDDING_MODEL,
        reranker_model_name: str = settings.RERANK_MODEL,
    ):

        self.conn = db_connection

        self.embedding_model = SentenceTransformer(embedding_model_name)

        self.reranker = CrossEncoder(reranker_model_name)

        self.vector_available = self._check_vector_availability()

    def _check_vector_availability(self) -> bool:
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vector');")
                row = cur.fetchone()
            return bool(row and row[0])
        except Exception as exc:
            logger.warning("Unable to verify pgvector availability: %s", exc)
            try:
                self.conn.rollback()
            except Exception:
                pass
            return False

    def _retrieve_text_fallback(self, query: str, top_k: int) -> List[str]:
        tokens = [t for t in re.findall(r"[A-Za-z0-9]+", query.lower()) if len(t) > 2][:5]

        try:
            with self.conn.cursor() as cur:
                if tokens:
                    clauses = " OR ".join(["LOWER(content) LIKE %s"] * len(tokens))
                    sql = f"""
                        SELECT content
                        FROM documents
                        WHERE {clauses}
                        LIMIT %s;
                    """
                    params = [f"%{token}%" for token in tokens] + [top_k]
                else:
                    sql = """
                        SELECT content
                        FROM documents
                        LIMIT %s;
                    """
                    params = [top_k]

                cur.execute(sql, params)
                rows = cur.fetchall()

            return [row[0] for row in rows]
        except Exception as exc:
            logger.error("RAG text fallback failed: %s", exc, exc_info=True)
            try:
                self.conn.rollback()
            except Exception:
                pass
            return []

    def embed_query(self, query: str) -> np.ndarray:

        return self.embedding_model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

    def retrieve(self, query: str, top_k: int = 10) -> List[str]:

        query_vector = self.embed_query(query)

        if not self.vector_available:
            return self._retrieve_text_fallback(query, top_k)

        sql = """
            SELECT content,
                   embedding <=> %s::vector AS distance
            FROM documents
            ORDER BY distance
            LIMIT %s;
        """

        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, (query_vector.tolist(), top_k))
                results = cur.fetchall()
        except Exception as exc:
            logger.warning("Vector retrieval failed, switching to text fallback: %s", exc)
            self.vector_available = False
            try:
                self.conn.rollback()
            except Exception:
                pass
            return self._retrieve_text_fallback(query, top_k)

        documents = [row[0] for row in results]

        return documents

    def rerank(self, query: str, documents: List[str], top_k: int = 3):

        if not documents:
            return []

        pairs = [(query, doc) for doc in documents]

        scores = self.reranker.predict(pairs)

        ranked = sorted(
            zip(documents, scores),
            key=lambda x: x[1],
            reverse=True
        )

        return [doc for doc, _ in ranked[:top_k]]

    def run(self, query: str, retrieve_k: int = 10, rerank_k: int = 3):

        retrieved_docs = self.retrieve(query, retrieve_k)

        reranked_docs = self.rerank(query, retrieved_docs, rerank_k)

        return reranked_docs