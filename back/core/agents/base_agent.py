import json
import logging
import re
from typing import Dict, Any, List, Optional

from back.core.llm import get_llm
from back.core.config.agent_config import VALID_OPERATORS, OPERATOR_MAP
from back.core.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)
llm = get_llm()

class BaseAgent:
    def __init__(self) -> None:
        pass

    @staticmethod
    def _active_model_name() -> str:
        return getattr(llm, "model", None) or getattr(llm, "configured_model", "unknown")

    @staticmethod
    def _build_memory_context_text(memory_context: Optional[Dict[str, Any]]) -> str:
        if not memory_context:
            return "(kosong)"

        preferred_keys = [
            "last_patient_id",
            "last_patient_name",
            "last_medicine",
            "last_tool",
            "last_question",
        ]

        lines: List[str] = []
        for key in preferred_keys:
            value = memory_context.get(key)
            if value is None or str(value).strip() == "":
                continue
            lines.append(f"{key}: {value}")

        if not lines:
            for key, value in memory_context.items():
                if value is None:
                    continue
                lines.append(f"{key}: {value}")

        return "\n".join(lines) if lines else "(kosong)"

    @staticmethod
    def _apply_cached_arguments(
        tool: str,
        arguments: Dict[str, Any],
        memory_context: Optional[Dict[str, Any]],
        question: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            arguments = {}

        if not memory_context:
            return arguments

        updated = dict(arguments)
        cache_patient_id = memory_context.get("last_patient_id") or memory_context.get("last_patient_name")
        cache_medicine = memory_context.get("last_medicine")
        has_context_reference = BaseAgent._has_context_reference(question or "")

        if tool in {"get_patient_data", "check_medicine_safety"} and not updated.get("patient_id") and cache_patient_id:
            updated["patient_id"] = cache_patient_id
            logger.info(f"[CACHE ARG] Injected patient_id from Redis context: {cache_patient_id}")

        if tool == "check_medicine_safety" and not updated.get("medicine") and cache_medicine and has_context_reference:
            updated["medicine"] = cache_medicine
            logger.info(f"[CACHE ARG] Injected medicine from Redis context: {cache_medicine}")

        medicine_tools = {"search_obat_by_stock", "search_obat_by_harga", "search_obat_by_kadaluarsa"}
        if tool in medicine_tools and not updated.get("nama_obat") and cache_medicine and has_context_reference:
            updated["nama_obat"] = cache_medicine
            logger.info(f"[CACHE ARG] Injected nama_obat from Redis context: {cache_medicine}")

        return updated

    @staticmethod
    def _extract_context_updates(
        tool: Optional[str],
        arguments: Dict[str, Any],
        parsed_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not tool:
            return {}

        updates: Dict[str, Any] = {"last_tool": tool}

        if tool == "get_patient_data":
            patient_id = parsed_result.get("mrn") or arguments.get("patient_id")
            patient_name = parsed_result.get("nama")
            if patient_id:
                updates["last_patient_id"] = str(patient_id)
            if patient_name:
                updates["last_patient_name"] = str(patient_name)

        if tool == "check_medicine_safety":
            patient_id = parsed_result.get("patient_mrn") or parsed_result.get("mrn") or arguments.get("patient_id")
            patient_name = parsed_result.get("patient_name") or parsed_result.get("nama")
            medicine = parsed_result.get("medicine") or arguments.get("medicine")

            if patient_id:
                updates["last_patient_id"] = str(patient_id)
            if patient_name:
                updates["last_patient_name"] = str(patient_name)
            if medicine:
                updates["last_medicine"] = str(medicine)

        medicine_tools = {"search_obat_by_stock", "search_obat_by_harga", "search_obat_by_kadaluarsa"}
        if tool in medicine_tools:
            medicine = arguments.get("nama_obat") or parsed_result.get("resolved_name")
            if medicine:
                updates["last_medicine"] = str(medicine)

        return updates

    @staticmethod
    def _build_history_text(history: List[Dict[str, str]]) -> str:
        if not history:
            return ""

        text = []
        for msg in history:
            role = msg.get("role", "").strip().lower()
            content = msg.get("content", "").strip()
            
            if not content:
                continue
                
            if role == "user":
                text.append(f"User: {content}")
            elif role == "assistant":
                text.append(f"Assistant: {content}")
            else:
                text.append(f"{role}: {content}")

        return "\n".join(text) if text else ""

    @staticmethod
    def _contains_any(text: str, keywords: List[str]) -> bool:
        lowered = str(text or "").lower()
        return any(keyword in lowered for keyword in keywords)

    @staticmethod
    def _has_context_reference(question: str) -> bool:
        q = f" {str(question or '').lower().strip()} "
        reference_phrases = [
            " obatnya ", " obat itu ", " yang tadi ", " yang sebelumnya ", " tersebut ", " pasiennya ", " pasien itu ",
            " stoknya ", " harganya ", " kadaluarsanya ", " itu tadi ", " dia ", " beliau "
        ]
        return any(phrase in q for phrase in reference_phrases)

    @staticmethod
    def validate_operator(operator: str) -> str:
        if operator in VALID_OPERATORS:
            return operator
        operator_lower = str(operator).lower().strip()
        for invalid_text, valid_symbol in OPERATOR_MAP.items():
            if invalid_text in operator_lower:
                return valid_symbol
        return "<"

    def _answer_general_with_llm(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        history_text = self._build_history_text(conversation_history or []) or "(kosong)"
        prompt = (
            "Anda adalah Asisten Farmasi AI yang sangat berpengetahuan. Anda bertugas memberikan informasi edukasi obat-obatan dan kesehatan secara langsung menggunakan pengetahuan bawaan Anda.\n"
            "PENTING:\n"
            "- BERIKAN JAWABAN YANG JELAS, LENGKAP, DAN RAMAH.\n"
            "- JANGAN PERNAH menolak menjawab dengan alasan Anda hanya AI atau tidak memiliki akses data. Anda SUDAH memiliki pengetahuan yang cukup untuk menjawab pertanyaan edukasi ini.\n"
            "- Jika ditanya tentang keamanan untuk ibu hamil/menyusui, fungsi, indikasi, atau efek samping, jawablah berdasarkan panduan medis umum yang Anda ketahui.\n\n"
            f"RIWAYAT:\n{history_text}\n\n"
            f"PERTANYAAN: {question}\n\n"
            "JAWABAN:"
        )

        try:
            answer = llm.generate(prompt, options={"temperature": 0.0, "num_predict": 300}).strip()
            if answer:
                return answer
        except Exception as e:
            logger.warning(f"[DIRECT LLM] Failed: {e}")

        return "Maaf, saya belum bisa memproses pertanyaan saat ini. Silakan coba lagi atau hubungi apoteker."

    @staticmethod
    def _parse_tool_payload(tool_result: Any) -> Dict[str, Any]:
        if not tool_result:
            return {}
        if isinstance(tool_result, dict):
            return tool_result
        if isinstance(tool_result, list) and tool_result:
            return tool_result[0] if isinstance(tool_result[0], dict) else {"data": tool_result}
        
        try:
            if hasattr(tool_result, "content"):
                content = tool_result.content
                if isinstance(content, list) and content:
                    text_value = getattr(content[0], "text", "")
                    if isinstance(text_value, str) and text_value.strip():
                        raw_text = text_value.strip()
                        if raw_text.startswith("{") or raw_text.startswith("["):
                            parsed = json.loads(raw_text)
                            return parsed if isinstance(parsed, dict) else {"data": parsed}
                        return {"context": raw_text}

            if hasattr(tool_result, "model_dump"):
                dumped = tool_result.model_dump()
                if isinstance(dumped, dict):
                    return dumped

        except Exception as e:
            logger.warning(f"Failed to parse tool payload: {e}")

        return {}

    async def _call_tool_json(
        self,
        mcp_client: Any,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raw = await mcp_client.call_tool(tool_name, arguments or {})
        return self._parse_tool_payload(raw)

    def _extract_context_from_result(self, tool_result: Any) -> str:
        parsed = self._parse_tool_payload(tool_result)
        if not parsed:
            return ""
        
        if "data" in parsed:
            data = parsed["data"]
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                if len(data[0]) >= 4:
                    nama = data[0][0]
                    stok = data[0][1]
                    exp = data[0][3]
                    return f"Obat {nama}: stok {stok}, exp {exp}"
        return str(parsed)[:1000]

    def _extract_answer_from_rag_result(self, tool_result: Any) -> str:
        if not tool_result:
            return ""
        parsed = self._parse_tool_payload(tool_result)
        return parsed.get("answer", "") or parsed.get("context", "") or str(parsed)[:500]
