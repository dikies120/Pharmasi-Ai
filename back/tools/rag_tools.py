import logging

logger = logging.getLogger(__name__)


def ask_question(rag_pipeline, question: str) -> dict:
    
    if not question or not str(question).strip():
        logger.warning("Empty question received")
        return {
            "tool": "ask_question",
            "status": "invalid",
            "answer": "Pertanyaan tidak boleh kosong"
        }

    if rag_pipeline is None:
        logger.error("RAG pipeline tidak tersedia")
        return {
            "tool": "ask_question",
            "status": "unavailable",
            "answer": "RAG pipeline tidak tersedia"
        }

    try:
        logger.debug(f"Processing question: {question}")
        result = rag_pipeline.run(question)
        
        if isinstance(result, str):
            logger.info("RAG returned string result")
            return {
                "tool": "ask_question",
                "status": "success",
                "answer": result
            }

        if isinstance(result, list):
            if not result:
                logger.info("RAG returned empty list")
                return {
                    "tool": "ask_question",
                    "status": "no_result",
                    "answer": "Data tidak ditemukan untuk pertanyaan Anda"
                }

            logger.debug(f"RAG returned {len(result)} documents")
            contexts = []
            for doc in result:
                if hasattr(doc, "page_content"):
                    contexts.append(doc.page_content)
                else:
                    contexts.append(str(doc))

            context = "\n".join(contexts[:3])
            logger.info(f"Extracted {len(contexts)} contexts")
            return {
                "tool": "ask_question",
                "status": "success",
                "answer": context,
                "context_count": len(contexts)
            }

        logger.debug(f"RAG returned unexpected type: {type(result)}")
        return {
            "tool": "ask_question",
            "status": "success",
            "answer": str(result)
        }

    except Exception as e:
        logger.error(f"Error in ask_question: {str(e)}", exc_info=True)
        return {
            "tool": "ask_question",
            "status": "error",
            "answer": f"Error: {str(e)}"
        }
