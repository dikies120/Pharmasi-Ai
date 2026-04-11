import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer, CrossEncoder
from back.core.settings import settings


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

    def embed_query(self, query: str) -> np.ndarray:

        return self.embedding_model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

    def retrieve(self, query: str, top_k: int = 10) -> List[str]:

        query_vector = self.embed_query(query)

        sql = """
            SELECT content,
                   embedding <=> %s::vector AS distance
            FROM documents
            ORDER BY distance
            LIMIT %s;
        """

        with self.conn.cursor() as cur:

            cur.execute(sql, (query_vector.tolist(), top_k))

            results = cur.fetchall()

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