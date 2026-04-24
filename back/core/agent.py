import json
import logging
import re
import uuid
from typing import Dict, Any, List, Optional

from back.core.llm import get_llm
from back.core.config.agent_config import VALID_OPERATORS, OPERATOR_MAP
from back.core.prompts import SYSTEM_PROMPT, FINAL_ANSWER_PROMPT

logger = logging.getLogger(__name__)
llm = get_llm()


class Agent:
    def __init__(self) -> None:
        logger.debug("Initializing Pharma Agent")

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
        has_context_reference = Agent._has_context_reference(question or "")

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
            " obatnya ",
            " obat itu ",
            " yang tadi ",
            " yang sebelumnya ",
            " tersebut ",
            " pasiennya ",
            " pasien itu ",
            " stoknya ",
            " harganya ",
            " kadaluarsanya ",
            " itu tadi ",
            " dia ",
            " beliau ",
        ]
        return any(phrase in q for phrase in reference_phrases)

    @classmethod
    def _is_db_intent_question(cls, question: str) -> bool:
        q = str(question or "").strip().lower()
        if not q:
            return False

        patient_markers = [
            "pasien",
            "mrn",
            "rekam medis",
            "diagnosa",
            "diagnosis",
            "bpjs",
            "faskes",
            "resep",
            "kartu",
        ]
        inventory_markers = [
            "stok",
            "persediaan",
            "harga",
            "kadaluarsa",
            "expired",
            "batch",
            "inventory",
            "transaksi",
            "pendapatan",
            "terlaris",
            "laporan",
            "dashboard",
            "grafik",
            "chart",
        ]
        safety_markers = ["aman", "bahaya", "alergi", "interaksi", "kontraindikasi"]
        action_markers = ["cek", "cari", "tampilkan", "lihat", "berapa", "list", "daftar", "ambil", "show"]
        definitional_markers = [
            "apa itu",
            "apa arti",
            "jelaskan",
            "pengertian",
            "maksud",
            "definisi",
            "bedanya",
            "bedakan",
            "kenapa",
            "mengapa",
        ]
        explicit_db_markers = ["database", " di db", "di sistem", "data internal", "di gudang", "di apotek"]

        has_patient = cls._contains_any(q, patient_markers) or bool(re.search(r"\bmr[-_\s]?\d+\b", q))
        has_inventory = cls._contains_any(q, inventory_markers)
        has_safety = cls._contains_any(q, safety_markers)
        has_analytics = cls._contains_any(q, ["analytics", "analitik", "ringkasan inventory", "ringkasan stok"])
        has_action = cls._contains_any(q, action_markers)
        has_definition_tone = cls._contains_any(q, definitional_markers)
        asks_internal_data = cls._contains_any(q, explicit_db_markers)

        if has_analytics or asks_internal_data or has_patient:
            return True

        if has_inventory:
            if has_definition_tone and not has_action:
                return False
            return True

        if has_safety and has_patient:
            return True

        return False

    def _answer_general_with_llm(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        history_text = self._build_history_text(conversation_history or []) or "(kosong)"
        prompt = (
            "Anda adalah asisten farmasi AI untuk edukasi umum.\n"
            "Jawab berdasarkan pengetahuan medis umum, jelas, ringkas, dan aman.\n"
            "Jika user tidak meminta data internal, jangan menyebut data database pasien/stok/harga internal.\n\n"
            f"KONTEKS RIWAYAT:\n{history_text}\n\n"
            f"PERTANYAAN USER:\n{question}\n\n"
            "JAWABAN:"
        )

        try:
            answer = llm.generate(prompt).strip()
            if answer:
                return answer
        except Exception as e:
            logger.warning(f"[DIRECT LLM] Prompted response failed: {e}")

        try:
            fallback = llm.generate(question).strip()
            if fallback:
                return fallback
        except Exception as e:
            logger.warning(f"[DIRECT LLM] Fallback response failed: {e}")

        return "Maaf, saya belum bisa memproses pertanyaan saat ini."


    @staticmethod
    def validate_operator(operator: str) -> str:
        if operator in VALID_OPERATORS:
            logger.debug(f"Operator '{operator}' is valid")
            return operator

        operator_lower = str(operator).lower().strip()
        logger.debug(f"Normalizing operator: {operator_lower}")

        for invalid_text, valid_symbol in OPERATOR_MAP.items():
            if invalid_text in operator_lower:
                logger.debug(f"Mapped '{operator_lower}' to '{valid_symbol}'")
                return valid_symbol

        logger.warning(f"Unknown operator '{operator}', defaulting to '<'")
        return "<"

    def decide(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        memory_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        logger.info(f"Deciding tool for question: {question[:100]}...")

        history_text = self._build_history_text(conversation_history or []) or "(kosong)"
        memory_context_text = self._build_memory_context_text(memory_context)

        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"KONTEKS PERCAKAPAN TERAKHIR:\n{history_text}\n\n"
            f"KONTEKS CACHE REDIS:\n{memory_context_text}\n\n"
            "ATURAN KONTEKS LANJUTAN:\n"
            "- Jika user memakai rujukan seperti 'pasien itu', 'dia', atau tidak menyebut ulang patient_id, gunakan KONTEKS CACHE REDIS jika relevan.\n"
            "- Jika tool membutuhkan patient_id atau medicine dan user tidak menyebut ulang, boleh isi dari KONTEKS CACHE REDIS.\n\n"
            f"PERTANYAAN USER:\n{question}\n\n"
            "JAWAB DENGAN JSON HANYA, JANGAN ADA TEKS LAIN:"
        )

        try:
            response = llm.generate(prompt).strip()
            logger.debug(f"LLM Response: {response[:200]}")

            response = response.replace("```json", "").replace("```", "").strip()

            if not response:
                logger.warning("Empty LLM response, routing to ask_question as fallback")
                return {"tool": "ask_question", "arguments": {"question": question}}

            data = json.loads(response)
            tool = data.get("tool")
            arguments = data.get("arguments", {})

            if not tool:
                logger.warning("Invalid JSON structure, routing to ask_question as fallback")
                return {"tool": "ask_question", "arguments": {"question": question}}

            if arguments is None:
                arguments = {}

            if "operator" in arguments:
                arguments["operator"] = self.validate_operator(arguments["operator"])

            logger.info(f"Decided tool: {tool}")
            return {"tool": tool, "arguments": arguments}

        except json.JSONDecodeError as e:
            logger.warning(f"LLM JSON parse failed: {e}, routing to ask_question as fallback")
            return {"tool": "ask_question", "arguments": {"question": question}}
        except Exception as e:
            logger.error(f"Error in decide(): {e}", exc_info=True)
            return {"tool": "ask_question", "arguments": {"question": question}}


    def final_answer(
        self,
        question: str,
        tool_result: Any,
        tool_name: str = None,
        conversation_history: List[Dict[str, str]] | None = None,
        custom_prompt: str = None
    ) -> str:
        """Generate final answer based on question and tool result
        
        Args:
            question: User's original question
            tool_result: Result from the MCP tool
            tool_name: Name of the tool that was called (optional)
            conversation_history: Conversation history for context (optional)
            custom_prompt: Optional custom prompt to override the default FINAL_ANSWER_PROMPT
            
        Returns:
            Natural language answer
        """
        logger.info(f"Generating final answer for question: {question[:100]}... (tool: {tool_name})")

        # For all tools, use adaptive final_answer_prompt with extracted context.
        parsed_payload = self._parse_tool_payload(tool_result)
        context = ""
        if isinstance(parsed_payload, dict):
            context = str(parsed_payload.get("context") or parsed_payload.get("answer") or "").strip()

        if not context:
            context = self._extract_context_from_result(tool_result)

        logger.info(f"[EXTRACT] context extracted: '{context[:80] if context else 'EMPTY'}'")

        question_lower = str(question or "").lower()
        force_raw_keywords = (
            "raw",
            "mentah",
            "apa adanya",
            "verbatim",
            "jangan diringkas",
            "copy",
        )
        force_raw = any(keyword in question_lower for keyword in force_raw_keywords)
        if force_raw and context and context.strip():
            logger.info(f"[DIRECT] User requested raw response (tool={tool_name})")
            return context

        if not context or context.strip() == "":
            context = "Data tidak ditemukan di database."
            logger.debug("No data found, using default message")

        history_text = self._build_history_text(conversation_history or [])
        
        if custom_prompt:
            prompt = custom_prompt.format(
                history_text=history_text,
                context=context,
                question=question
            )
        else:
            prompt = FINAL_ANSWER_PROMPT.format(
                history_text=history_text,
                context=context,
                question=question
            )
        
        logger.info(f"[LLM] Calling LLM with prompt (first 300 chars):\n{prompt[:300]}")

        try:
            answer = llm.generate(prompt).strip()
            logger.info(f"[LLM] Answer generated: '{answer[:100]}'")
            return answer
        except Exception as e:
            logger.error(f"Error generating final answer: {e}", exc_info=True)
            fallback_answer = self._extract_answer_from_rag_result(tool_result)
            if fallback_answer:
                return fallback_answer
            return f"Maaf, terjadi kesalahan saat memproses jawaban: {str(e)}"

    @staticmethod
    def _parse_tool_payload(tool_result: Any) -> Dict[str, Any]:
        """Parse generic MCP tool result into plain dict payload."""
        try:
            if isinstance(tool_result, dict):
                if "content" in tool_result and isinstance(tool_result["content"], list) and tool_result["content"]:
                    raw_text = tool_result["content"][0].get("text", "")
                    if isinstance(raw_text, str) and raw_text.strip():
                        if raw_text.strip().startswith("{") or raw_text.strip().startswith("["):
                            parsed = json.loads(raw_text)
                            return parsed if isinstance(parsed, dict) else {"data": parsed}
                        return {"context": raw_text.strip()}
                return tool_result

            if isinstance(tool_result, str):
                raw_text = tool_result.strip()
                if not raw_text:
                    return {}
                if raw_text.startswith("{") or raw_text.startswith("["):
                    parsed = json.loads(raw_text)
                    return parsed if isinstance(parsed, dict) else {"data": parsed}
                return {"context": raw_text}

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

    async def run_monitoring_realtime(
        self,
        mcp_client: Any,
        nama_obat: Optional[str] = None,
        lokasi: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        result = await self._call_tool_json(
            mcp_client,
            "get_realtime_stock",
            {"nama_obat": nama_obat, "lokasi": lokasi, "status": status},
        )
        if result:
            return result
        return {"status": "success", "data": []}

    async def run_chat_turn(
        self,
        mcp_client: Any,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        memory_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Single chat turn orchestration: decide -> tool call -> final answer."""
        model_name = self._active_model_name()

        # Pertanyaan edukasi umum dijawab langsung oleh LLM agar tidak memicu query DB internal.
        if not self._is_db_intent_question(question):
            direct_answer = self._answer_general_with_llm(question, conversation_history=conversation_history)
            return {
                "answer": direct_answer,
                "tool_used": None,
                "status": "success",
                "model_name": model_name,
                "context_updates": {
                    "last_tool": "direct_llm",
                },
            }

        decision = self.decide(
            question,
            conversation_history=conversation_history,
            memory_context=memory_context,
        )

        if "answer" in decision:
            return {
                "answer": decision["answer"],
                "tool_used": None,
                "status": "success",
                "model_name": model_name,
            }

        tool = decision.get("tool")
        arguments = decision.get("arguments", {}) or {}
        arguments = self._apply_cached_arguments(tool, arguments, memory_context, question=question)

        if not tool:
            return {
                "answer": "Tidak dapat menentukan tool yang sesuai untuk pertanyaan ini",
                "tool_used": None,
                "status": "error",
                "model_name": model_name,
            }

        try:
            available_tools = await mcp_client.list_tools()
            if tool not in available_tools:
                return {
                    "answer": f"Tool '{tool}' tidak tersedia. Available: {available_tools}",
                    "tool_used": tool,
                    "status": "error",
                    "model_name": model_name,
                }
        except Exception as e:
            return {
                "answer": f"Gagal check available tools: {str(e)}",
                "tool_used": tool,
                "status": "error",
                "model_name": model_name,
            }

        try:
            result = await mcp_client.call_tool(tool, arguments)
        except Exception as e:
            return {
                "answer": f"Error calling tool: {str(e)}",
                "tool_used": tool,
                "status": "error",
                "model_name": model_name,
            }

        try:
            answer = self.final_answer(
                question,
                result,
                tool_name=tool,
                conversation_history=conversation_history,
            )
        except Exception:
            parsed = self._parse_tool_payload(result)
            answer = parsed.get("answer") or parsed.get("context") or "Maaf, terjadi kesalahan memproses jawaban."

        parsed_result = self._parse_tool_payload(result)
        context_updates = self._extract_context_updates(tool, arguments, parsed_result)

        return {
            "answer": answer,
            "tool_used": tool,
            "status": "success",
            "model_name": model_name,
            "context_updates": context_updates,
        }

    async def run_monitoring_analytics(self, mcp_client: Any) -> Dict[str, Any]:
        result = await self._call_tool_json(mcp_client, "get_inventory_analytics", {})
        if not result:
            result = {"status": "success", "data": {}}

        inventory_data = result.get("data", {}) if isinstance(result, dict) else {}

        stok_data = inventory_data.get("stok", {})
        transaksi_data = inventory_data.get("transaksi", {})
        top_selling = inventory_data.get("penjualan", {}).get("top_selling", [])

        stok_tertinggi = stok_data.get("tertinggi") or {}
        stok_terendah = stok_data.get("terendah") or {}
        hampir_habis = stok_data.get("hampir_habis", [])

        top_lines = []
        for idx, item in enumerate(top_selling[:5], start=1):
            top_lines.append(f"{idx}. {item.get('nama', '-')} = {item.get('total_terjual', 0)}")
        top_block = "\n".join(top_lines) if top_lines else "-"

        ai_insight = (
            f"stok tertinggi obat = {stok_tertinggi.get('nama', '-')} ({stok_tertinggi.get('stok', 0)})\n"
            f"stok terendah obat = {stok_terendah.get('nama', '-')} ({stok_terendah.get('stok', 0)})\n"
            f"total jenis obat = {stok_data.get('total_jenis_obat', 0)}\n"
            f"jumlah obat stok kritis (<50) = {len(hampir_habis)}\n"
            f"pendapatan bulan ini = Rp {float(transaksi_data.get('pendapatan_bulan_ini', 0)):,.0f}\n"
            f"transaksi bulan ini = {int(transaksi_data.get('transaksi_bulan_ini', 0))}\n"
            f"total transaksi = {int(transaksi_data.get('jumlah', 0))}\n"
            f"total pendapatan = Rp {float(transaksi_data.get('revenue', 0)):,.0f}\n"
            f"top obat terjual =\n{top_block}"
        )

        result["ai_insight"] = ai_insight
        return result

    async def run_validasi_obat(
        self,
        mcp_client: Any,
        patient_id: str,
    ) -> Dict[str, Any]:
        logger.info(f"[Agent] Starting validation workflow for patient: {patient_id}")

        patient_data = await self._call_tool_json(
            mcp_client,
            "get_patient_data",
            {"patient_id": patient_id},
        )
        if patient_data.get("error"):
            return {"status": "error", "message": patient_data.get("error")}

        if str(patient_data.get("status", "")).lower() == "error":
            return {"status": "error", "message": patient_data.get("error", "Data pasien tidak ditemukan")}

        diagnosis_raw = patient_data.get("active_diagnosis", [])
        if isinstance(diagnosis_raw, list) and diagnosis_raw:
            diagnosis_code = str(diagnosis_raw[0] or "").strip()
        elif isinstance(diagnosis_raw, str):
            diagnosis_code = diagnosis_raw.strip()
        else:
            diagnosis_code = ""

        diagnosis_notes_raw = patient_data.get("diagnosis_notes", [])
        if isinstance(diagnosis_notes_raw, list):
            diagnosis_notes = [str(x).strip() for x in diagnosis_notes_raw if str(x).strip()]
        elif isinstance(diagnosis_notes_raw, str) and diagnosis_notes_raw.strip():
            diagnosis_notes = [diagnosis_notes_raw.strip()]
        else:
            diagnosis_notes = []

        prescriptions = patient_data.get("active_prescriptions", [])
        if not prescriptions:
            return {
                "status": "error",
                "message": "Tidak ada resep aktif untuk pasien ini, validasi obat tidak dapat dijalankan.",
            }

        bpjs_status = patient_data.get("bpjs_status", "UMUM")
        faskes_level = patient_data.get("faskes_level", 1)

        icd_data: Dict[str, Any] = {}
        if diagnosis_code:
            icd_data = await self._call_tool_json(
                mcp_client,
                "get_icd11_data",
                {"kode_diagnosa": diagnosis_code},
            )

        icd_name = str(icd_data.get("nama") or icd_data.get("name") or "").strip()
        if icd_name and icd_name.lower() not in {"diagnosis umum", "unspecified", "diagnosis unspecified"}:
            diag_name = icd_name
        elif diagnosis_notes:
            diag_name = diagnosis_notes[0]
        elif diagnosis_code:
            diag_name = f"Kode {diagnosis_code}"
        else:
            diag_name = "Diagnosis belum tercatat"

        if diagnosis_code and diagnosis_code.upper() not in diag_name.upper():
            diag_name = f"{diag_name} [{diagnosis_code}]"

        obat_list: List[str] = []
        enriched_prescriptions: List[Dict[str, Any]] = []
        prescription_lookup: Dict[str, Dict[str, Any]] = {}

        for p in prescriptions:
            drug_name = p.get("drug", "Unknown")
            qty = p.get("qty", 0) or 0
            aturan_minum = p.get("aturan_minum", "Sesuai petunjuk dokter")
            obat_list.append(drug_name)

            fornas_data = await self._call_tool_json(
                mcp_client,
                "get_fornas_data",
                {"drug_name": drug_name},
            )
            stock_data = await self._call_tool_json(
                mcp_client,
                "get_drug_stock",
                {"drug_name": drug_name},
            )

            fornas_summary = "Data Fornas tidak tersedia"
            if isinstance(fornas_data, dict):
                if fornas_data.get("pesan"):
                    fornas_summary = str(fornas_data.get("pesan"))
                elif any(k in fornas_data for k in ("fpktp", "fpktl")):
                    fornas_summary = (
                        f"Fornas fpktp={fornas_data.get('fpktp', '-')}, "
                        f"fpktl={fornas_data.get('fpktl', '-')}"
                    )

            enriched_item = {
                "obat": drug_name,
                "resep_qty": qty,
                "aturan_minum": aturan_minum,
                "stok_data": stock_data,
                "fornas_data": fornas_data,
                "fornas_summary": fornas_summary,
            }
            enriched_prescriptions.append(enriched_item)
            prescription_lookup[str(drug_name).strip().lower()] = enriched_item

        patient_payload = {
            "nama": patient_data.get("nama", patient_id),
            "mrn": patient_data.get("mrn", patient_id),
            "tanggal_lahir": patient_data.get("tanggal_lahir"),
            "usia_tahun": patient_data.get("usia_tahun"),
            "jenis_kelamin": patient_data.get("jenis_kelamin"),
            "alergi": patient_data.get("alergi"),
            "bpjs_status": bpjs_status,
            "faskes_level": faskes_level,
            "diagnosis_code": diagnosis_code,
            "diagnosis_name": diag_name,
            "diagnosis_notes": diagnosis_notes,
        }

        llm_payload = {
            "target_engine": "MedGemma",
            "workflow": "VALIDASI_FARMASI_KLINIK",
            "mandatory_checks": [
                "validasi_dosis",
                "screening_interaksi_obat",
                "cek_kontraindikasi",
                "cek_alergi",
            ],
            "patient": patient_payload,
            "prescriptions": enriched_prescriptions,
        }

        prompt = (
            "Anda adalah MedGemma yang bertindak sebagai apoteker klinis AI.\n"
            "Lakukan validasi farmasi klinik untuk setiap obat resep pasien.\n"
            "WAJIB melakukan 4 pemeriksaan berikut per item obat:\n"
            "A. Validasi Dosis\n"
            "B. Screening Interaksi Obat\n"
            "C. Cek Kontraindikasi\n"
            "D. Cek Alergi\n"
            "Gunakan data pasien sebagai sumber fakta utama. Jangan mengarang data pasien di luar input.\n"
            "Buat output klinis yang informatif, spesifik, dan actionable seperti konseling apoteker klinis.\n"
            "Untuk tiap pemeriksaan, isi catatan dengan alasan klinis, dampak pada pasien, dan langkah tindak lanjut.\n"
            "Catatan boleh 1-3 kalimat per pemeriksaan agar tetap jelas namun tidak terlalu singkat.\n"
            "Output HARUS JSON valid tanpa markdown.\n\n"
            "DATA KLINIS (JSON):\n"
            f"{json.dumps(llm_payload, ensure_ascii=False, indent=2)}\n\n"
            "Skema output JSON wajib:\n"
            "{\n"
            "  \"verdict\": \"AMAN|PERLU REVIEW FARMASIS/DOKTER\",\n"
            "  \"risk_level\": \"LOW|MEDIUM|HIGH\",\n"
            "  \"analysis\": \"...\",\n"
            "  \"recommendation\": \"...\",\n"
            "  \"confidence\": 0.0,\n"
            "  \"next_step\": \"DISPENSING|STOP\",\n"
            "  \"validasi\": {\n"
            "    \"administrasi\": true,\n"
            "    \"inventory\": true\n"
            "  },\n"
            "  \"ringkasan_klinis\": \"...\",\n"
            "  \"alasan_utama\": [\"...\"],\n"
            "  \"hasil_per_obat\": [\n"
            "    {\n"
            "      \"obat\": \"Ibuprofen 400 mg 3x sehari\",\n"
            "      \"status\": \"SESUAI|TIDAK AMAN\",\n"
            "      \"alasan\": [\"...\"],\n"
            "      \"rekomendasi\": \"...\",\n"
            "      \"cek_klinik\": {\n"
            "        \"validasi_dosis\": {\"status\": \"AMAN|PERLU REVIEW|TIDAK AMAN\", \"catatan\": \"...\"},\n"
            "        \"screening_interaksi_obat\": {\"status\": \"AMAN|PERLU REVIEW|TIDAK AMAN\", \"catatan\": \"...\"},\n"
            "        \"cek_kontraindikasi\": {\"status\": \"AMAN|PERLU REVIEW|TIDAK AMAN\", \"catatan\": \"...\"},\n"
            "        \"cek_alergi\": {\"status\": \"AMAN|PERLU REVIEW|TIDAK AMAN\", \"catatan\": \"...\"}\n"
            "      },\n"
            "      \"output_ringkas\": {\"dosis\": \"AMAN|PERLU REVIEW|TIDAK AMAN\", \"catatan\": \"...\"}\n"
            "    }\n"
            "  ],\n"
            "  \"kesimpulan\": {\n"
            "    \"jumlah_masalah\": 0,\n"
            "    \"saran\": \"...\"\n"
            "  }\n"
            "}"
        )

        def _extract_first_json_object(text: str) -> Optional[Dict[str, Any]]:
            if not text:
                return None

            expected_keys = {
                "verdict",
                "risk_level",
                "next_step",
                "validasi",
                "obat_checks",
                "hasil_per_obat",
                "kesimpulan",
            }
            fallback_candidate: Optional[Dict[str, Any]] = None
            candidate_starts = [idx for idx, ch in enumerate(text) if ch == "{"]
            for start in candidate_starts:
                depth = 0
                for idx in range(start, len(text)):
                    ch = text[idx]
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            snippet = text[start : idx + 1]
                            try:
                                parsed = json.loads(snippet)
                                if isinstance(parsed, dict):
                                    if expected_keys.intersection(set(parsed.keys())):
                                        return parsed
                                    if fallback_candidate is None:
                                        fallback_candidate = parsed
                            except Exception:
                                break
            return fallback_candidate

        model_name = self._active_model_name()
        llm_raw = ""
        llm_result: Optional[Dict[str, Any]] = None
        llm_parse_error: Optional[Exception] = None
        expected_obat_names = [str(x).strip() for x in obat_list if str(x).strip()]
        expected_obat_names_lower = [x.lower() for x in expected_obat_names]

        def _extract_covered_obat(
            raw_text: str,
            parsed_result: Optional[Dict[str, Any]],
        ) -> set[str]:
            covered: set[str] = set()

            if isinstance(parsed_result, dict):
                hasil_per_obat = parsed_result.get("hasil_per_obat")
                if isinstance(hasil_per_obat, list):
                    for item in hasil_per_obat:
                        if not isinstance(item, dict):
                            continue
                        obat_name = str(item.get("obat") or item.get("nama_obat") or "").strip().lower()
                        if not obat_name:
                            continue
                        for expected in expected_obat_names_lower:
                            if expected and (expected in obat_name or obat_name in expected):
                                covered.add(expected)

            text_lower = str(raw_text or "").lower()
            for expected in expected_obat_names_lower:
                if expected and expected in text_lower:
                    covered.add(expected)

            return covered

        expected_obat_text = "\n".join(f"- {name}" for name in expected_obat_names)
        coverage_guard_prompt = (
            "PENTING: WAJIB validasi SEMUA obat resep berikut.\n"
            f"{expected_obat_text}\n"
            f"Jumlah obat wajib tervalidasi: {len(expected_obat_names)}.\n"
            "Jangan berhenti di satu obat saja."
        )

        base_prompt = f"{prompt}\n\n{coverage_guard_prompt}"
        covered_obat_lower: set[str] = set()

        for attempt in range(3):
            attempt_prompt = base_prompt
            if attempt > 0:
                attempt_prompt = (
                    "Output sebelumnya belum mencakup semua obat. Ulangi dan lengkapi SEMUA obat.\n"
                    f"Tercakup saat ini: {len(covered_obat_lower)}/{len(expected_obat_names)} obat.\n"
                    f"{coverage_guard_prompt}\n\n"
                    "DATA KLINIS (JSON):\n"
                    f"{json.dumps(llm_payload, ensure_ascii=False, indent=2)}"
                )

            try:
                llm_raw = llm.generate(
                    attempt_prompt,
                    options={"temperature": 0.0, "num_predict": 3200},
                    response_format="json",
                ).strip()
                llm_clean = llm_raw.replace("```json", "").replace("```", "").strip()
                try:
                    parsed_result = json.loads(llm_clean)
                except Exception:
                    parsed_result = _extract_first_json_object(llm_clean)

                llm_result = parsed_result if isinstance(parsed_result, dict) else None
                covered_obat_lower = _extract_covered_obat(llm_raw, llm_result)

                if len(covered_obat_lower) >= len(expected_obat_names_lower):
                    llm_parse_error = None if isinstance(llm_result, dict) else ValueError(
                        "LLM output is not a JSON object"
                    )
                    break

                llm_parse_error = ValueError(
                    f"Output belum mencakup semua obat ({len(covered_obat_lower)}/{len(expected_obat_names_lower)})"
                )
            except Exception as e:
                llm_parse_error = e
                llm_raw = ""

        missing_obat = [
            expected_obat_names[idx]
            for idx, expected in enumerate(expected_obat_names_lower)
            if expected not in covered_obat_lower
        ]

        if missing_obat:
            return {
                "status": "error",
                "message": "Output MedGemma belum memvalidasi semua obat resep.",
                "expected_obat_count": len(expected_obat_names),
                "validated_obat_count": len(covered_obat_lower),
                "missing_obat": missing_obat,
                "medgemma_raw_response": llm_raw,
            }

        if llm_parse_error is not None:
            logger.warning(f"[VALIDASI LLM] Output tidak ter-parse JSON, dikirim raw: {llm_parse_error}")

        # Direct mode: output dikembalikan apa adanya dari MedGemma tanpa normalisasi/fallback.
        required_checks = {
            "validasi_dosis": ["validasi_dosis"],
            "screening_interaksi_obat": ["screening_interaksi_obat"],
            "cek_kontraindikasi": ["cek_kontraindikasi"],
            "cek_alergi": ["cek_alergi"],
        }
        repair_pass_used = False

        if isinstance(llm_result, dict):
            medgemma_output: Dict[str, Any] = llm_result
        else:
            medgemma_output = {"raw_text": llm_raw}

        prescription_context: List[Dict[str, Any]] = []
        for item in enriched_prescriptions:
            if not isinstance(item, dict):
                continue

            stok_data = item.get("stok_data") if isinstance(item.get("stok_data"), dict) else {}
            resep_qty = item.get("resep_qty")
            stok_tersedia = stok_data.get("stok")
            stok_ada = None
            try:
                if stok_tersedia is not None and resep_qty is not None:
                    stok_ada = "IYA" if float(stok_tersedia) >= float(resep_qty) else "TIDAK"
            except Exception:
                stok_ada = None

            prescription_context.append(
                {
                    "obat": item.get("obat"),
                    "resep_qty": resep_qty,
                    "stok_tersedia": stok_tersedia,
                    "stok_ada": stok_ada,
                    "stok_data": stok_data,
                    "aturan_minum": item.get("aturan_minum"),
                    "fornas_summary": item.get("fornas_summary"),
                }
            )

        medgemma_items_count = len(covered_obat_lower)
        expected_obat_count = len(expected_obat_names)

        medgemma_routed = "medgemma" in str(model_name).lower()
        flow_trace = {
            "step_1_ui_input": {
                "status": "done",
                "detail": f"Validasi pasien {patient_payload['mrn']}",
            },
            "step_2_fastapi_gateway": {
                "status": "done",
                "detail": "Request diterima endpoint validasi",
            },
            "step_3_agent_understanding": {
                "status": "done",
                "detail": f"Entity pasien={patient_payload['mrn']}, jumlah_obat={len(obat_list)}",
            },
            "step_4_mcp_tools_execution": {
                "status": "done",
                "detail": "Data pasien, resep, stok, fornas, dan ICD diambil dari DB tools",
            },
            "step_5_agent_reasoning": {
                "status": "done",
                "detail": (
                    f"Output validasi klinis berasal langsung dari MedGemma model={model_name} "
                    f"untuk {medgemma_items_count}/{expected_obat_count} item obat (raw passthrough)."
                ),
            },
            "step_6_response_to_ui": {
                "status": "done",
                "detail": "Hasil MedGemma siap ditampilkan di UI",
            },
        }

        return {
            "status": "success",
            "patient_name": patient_data.get("nama", patient_id),
            "patient_mrn": patient_data.get("mrn", patient_id),
            "active_prescription_id": patient_data.get("active_prescription_id"),
            "active_prescription_date": patient_data.get("active_prescription_date"),
            "patient_snapshot": {
                "jenis_kelamin": patient_payload.get("jenis_kelamin"),
                "usia_tahun": patient_payload.get("usia_tahun"),
                "tanggal_lahir": patient_payload.get("tanggal_lahir"),
                "alergi": patient_payload.get("alergi"),
                "bpjs_status": bpjs_status,
                "faskes_level": faskes_level,
                "diagnosis": diag_name,
                "diagnosis_code": diagnosis_code,
            },
            "diagnosis": diag_name,
            "clinical_engine": {
                "target": "MedGemma",
                "provider": "Ollama",
                "model": model_name,
                "routed_to_medgemma": medgemma_routed,
                "mandatory_checks": list(required_checks.keys()),
                "repair_pass_used": repair_pass_used,
                "raw_passthrough": True,
                "json_parse_ok": isinstance(llm_result, dict),
                "expected_obat_count": expected_obat_count,
                "validated_obat_count": medgemma_items_count,
            },
            "medgemma_output": medgemma_output,
            "medgemma_raw_response": llm_raw,
            "prescription_context": prescription_context,
            "flow_trace": flow_trace,
            "architecture_flow": "UI -> FastAPI (Bridge) -> AI Agent -> MCP Tools -> MedGemma (Ollama) -> UI",
        }

        def _to_bool(value: Any, default: bool = False) -> bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return value != 0
            if isinstance(value, str):
                normalized = value.strip().lower()
                if normalized in {"true", "ya", "yes", "iya", "1", "valid", "aman"}:
                    return True
                if normalized in {"false", "tidak", "no", "0", "invalid", "bahaya"}:
                    return False
            return default

        def _normalize_check_status(status: Any) -> str:
            normalized = str(status or "").strip().upper()
            if normalized in {"AMAN", "SESUAI", "OK", "SAFE", "NORMAL", "LOW"}:
                return "AMAN"
            if normalized in {"TIDAK AMAN", "TIDAK SESUAI", "BAHAYA", "HIGH"}:
                return "TIDAK AMAN"
            if normalized in {"PERLU REVIEW", "WARNING", "WASPADA", "REVIEW", "MEDIUM"}:
                return "PERLU REVIEW"
            return "PERLU REVIEW"

        def _normalize_item_status(status: Any, cek_klinik: Dict[str, Dict[str, str]]) -> str:
            normalized = str(status or "").strip().upper()
            if normalized in {"SESUAI", "AMAN", "SAFE", "OK"}:
                return "SESUAI"
            if normalized in {"TIDAK AMAN", "TIDAK SESUAI", "WARNING", "PERLU REVIEW", "BAHAYA"}:
                return "TIDAK AMAN"
            has_risk = any(v.get("status") in {"TIDAK AMAN", "PERLU REVIEW"} for v in cek_klinik.values())
            return "TIDAK AMAN" if has_risk else "SESUAI"

        def _short_note(text: Any, max_words: int = 18) -> str:
            cleaned = str(text or "").replace("\n", " ").strip()
            if not cleaned:
                return ""

            first_sentence = cleaned.split(".")[0].strip()
            source = first_sentence or cleaned
            words = source.split()
            if len(words) <= max_words:
                return source
            return " ".join(words[:max_words]).strip() + "..."

        def _find_fallback_obat(obat_name: str) -> Dict[str, Any]:
            normalized = str(obat_name or "").strip().lower()
            if not normalized:
                return {}
            if normalized in prescription_lookup:
                return prescription_lookup[normalized]
            for key, value in prescription_lookup.items():
                if key in normalized or normalized in key:
                    return value
            return {}

        def _extract_check(raw_checks: Dict[str, Any], aliases: List[str], fallback_note: str = "") -> Dict[str, str]:
            for alias in aliases:
                value = raw_checks.get(alias)
                if isinstance(value, dict):
                    status = _normalize_check_status(value.get("status"))
                    note = str(value.get("catatan") or value.get("detail") or value.get("reason") or "").strip()
                    return {"status": status, "catatan": note or fallback_note}
                if isinstance(value, str):
                    return {
                        "status": _normalize_check_status(value),
                        "catatan": fallback_note,
                    }
            return {"status": "PERLU REVIEW", "catatan": fallback_note}

        obat_checks: List[Dict[str, Any]] = []
        clinical_items: List[Dict[str, Any]] = []
        processed_obat_names = set()

        hasil_per_obat = llm_result.get("hasil_per_obat")
        if isinstance(hasil_per_obat, list):
            for item in hasil_per_obat:
                if not isinstance(item, dict):
                    continue

                obat_name = str(item.get("obat") or item.get("nama_obat") or "").strip()
                fallback = _find_fallback_obat(obat_name)
                if not fallback:
                    continue

                canonical_obat = str(fallback.get("obat") or obat_name or "").strip()
                if not canonical_obat:
                    continue

                canonical_key = canonical_obat.lower()
                if canonical_key in processed_obat_names:
                    continue
                processed_obat_names.add(canonical_key)

                stok_data = fallback.get("stok_data", {}) if isinstance(fallback, dict) else {}
                stok_tersedia = stok_data.get("stok", 0)
                resep_qty = item.get("resep_qty", fallback.get("resep_qty", 0))
                aturan_minum = str(
                    item.get("aturan_minum")
                    or fallback.get("aturan_minum")
                    or "Sesuai petunjuk dokter"
                )
                status_bpjs_fornas = str(
                    item.get("status_bpjs_fornas")
                    or fallback.get("fornas_summary")
                    or "Data Fornas tidak tersedia"
                )

                raw_checks = item.get("cek_klinik") if isinstance(item.get("cek_klinik"), dict) else {}
                cek_klinik = {
                    "validasi_dosis": _extract_check(
                        raw_checks,
                        ["validasi_dosis", "dosis", "dose_validation"],
                        fallback_note="Perlu verifikasi dosis terhadap profil pasien.",
                    ),
                    "screening_interaksi_obat": _extract_check(
                        raw_checks,
                        ["screening_interaksi_obat", "interaksi_obat", "drug_interaction"],
                        fallback_note="Perlu evaluasi potensi interaksi dengan terapi aktif.",
                    ),
                    "cek_kontraindikasi": _extract_check(
                        raw_checks,
                        ["cek_kontraindikasi", "kontraindikasi", "contraindication"],
                        fallback_note="Perlu evaluasi kontraindikasi terhadap kondisi pasien.",
                    ),
                    "cek_alergi": _extract_check(
                        raw_checks,
                        ["cek_alergi", "alergi", "allergy"],
                        fallback_note="Perlu verifikasi alergi obat pasien.",
                    ),
                }

                status_item = _normalize_item_status(item.get("status"), cek_klinik)
                alasan = item.get("alasan") if isinstance(item.get("alasan"), list) else []
                alasan = [str(x).strip() for x in alasan if str(x).strip()]
                if not alasan:
                    for section in cek_klinik.values():
                        if section.get("status") == "TIDAK AMAN" and section.get("catatan"):
                            alasan.append(section.get("catatan", ""))

                rekomendasi_item = str(item.get("rekomendasi") or "").strip()
                if not rekomendasi_item:
                    rekomendasi_item = (
                        "Pertimbangkan alternatif lebih aman atau lakukan konfirmasi dosis ke dokter."
                        if status_item == "TIDAK AMAN"
                        else "Terapi sesuai, lanjutkan monitoring klinis rutin."
                    )

                try:
                    stok_ada = "IYA" if float(stok_tersedia or 0) >= float(resep_qty or 0) else "TIDAK"
                except Exception:
                    stok_ada = "TIDAK"

                clinical_item = {
                    "obat": canonical_obat,
                    "status": status_item,
                    "alasan": alasan,
                    "rekomendasi": rekomendasi_item,
                    "cek_klinik": cek_klinik,
                }
                clinical_items.append(clinical_item)

                obat_checks.append(
                    {
                        "obat": clinical_item["obat"],
                        "resep_qty": resep_qty,
                        "stok_tersedia": stok_tersedia,
                        "stok_ada": stok_ada,
                        "status_bpjs_fornas": status_bpjs_fornas,
                        "aturan_minum": aturan_minum,
                        "catatan_klinis": " ; ".join(alasan) if alasan else "Tidak ada catatan klinis tambahan.",
                    }
                )

        if not clinical_items:
            obat_checks_from_llm = llm_result.get("obat_checks")
            if isinstance(obat_checks_from_llm, list):
                for item in obat_checks_from_llm:
                    if not isinstance(item, dict):
                        continue

                    obat_name = str(item.get("obat", "")).strip()
                    fallback = _find_fallback_obat(obat_name)
                    if not fallback:
                        continue

                    canonical_obat = str(fallback.get("obat") or obat_name or "").strip()
                    if not canonical_obat:
                        continue

                    canonical_key = canonical_obat.lower()
                    if canonical_key in processed_obat_names:
                        continue
                    processed_obat_names.add(canonical_key)

                    stok_data = fallback.get("stok_data", {}) if isinstance(fallback, dict) else {}
                    stok_tersedia = item.get("stok_tersedia", stok_data.get("stok", 0))
                    resep_qty = item.get("resep_qty", fallback.get("resep_qty", 0))
                    aturan_minum = item.get("aturan_minum", fallback.get("aturan_minum", "Sesuai petunjuk dokter"))
                    status_bpjs_fornas = item.get("status_bpjs_fornas", fallback.get("fornas_summary", "Data Fornas tidak tersedia"))
                    stok_ada = str(item.get("stok_ada", "")).strip().upper()
                    if stok_ada not in {"IYA", "TIDAK"}:
                        try:
                            stok_ada = "IYA" if float(stok_tersedia or 0) >= float(resep_qty or 0) else "TIDAK"
                        except Exception:
                            stok_ada = "TIDAK"

                    catatan_klinis = str(item.get("catatan_klinis", "")).strip()
                    status_item = "TIDAK AMAN"
                    clinical_items.append(
                        {
                            "obat": canonical_obat,
                            "status": status_item,
                            "alasan": [catatan_klinis] if catatan_klinis else [],
                            "rekomendasi": "Gunakan review klinis manual untuk keputusan akhir.",
                            "cek_klinik": {
                                "validasi_dosis": {"status": "PERLU REVIEW", "catatan": "Tidak tersedia dari output model."},
                                "screening_interaksi_obat": {"status": "PERLU REVIEW", "catatan": "Tidak tersedia dari output model."},
                                "cek_kontraindikasi": {"status": "PERLU REVIEW", "catatan": "Tidak tersedia dari output model."},
                                "cek_alergi": {"status": "PERLU REVIEW", "catatan": "Tidak tersedia dari output model."},
                            },
                        }
                    )

                    obat_checks.append(
                        {
                            "obat": canonical_obat,
                            "resep_qty": resep_qty,
                            "stok_tersedia": stok_tersedia,
                            "stok_ada": stok_ada,
                            "status_bpjs_fornas": status_bpjs_fornas,
                            "aturan_minum": aturan_minum,
                            "catatan_klinis": catatan_klinis or "LLM tidak mengembalikan detail klinis terstruktur.",
                        }
                    )

        if not clinical_items:
            for item in enriched_prescriptions:
                stok_data = item.get("stok_data", {}) if isinstance(item, dict) else {}
                stok_tersedia = stok_data.get("stok", 0)
                resep_qty = item.get("resep_qty", 0)
                try:
                    stok_ok = float(stok_tersedia or 0) >= float(resep_qty or 0)
                except Exception:
                    stok_ok = False

                clinical_items.append(
                    {
                        "obat": item.get("obat", "Unknown"),
                        "status": "TIDAK AMAN",
                        "alasan": ["Model tidak mengembalikan detail evaluasi per obat."],
                        "rekomendasi": "Lakukan review manual oleh dokter/farmasis sebelum terapi dilanjutkan.",
                        "cek_klinik": {
                            "validasi_dosis": {"status": "PERLU REVIEW", "catatan": "Tidak tersedia dari output model."},
                            "screening_interaksi_obat": {"status": "PERLU REVIEW", "catatan": "Tidak tersedia dari output model."},
                            "cek_kontraindikasi": {"status": "PERLU REVIEW", "catatan": "Tidak tersedia dari output model."},
                            "cek_alergi": {"status": "PERLU REVIEW", "catatan": "Tidak tersedia dari output model."},
                        },
                    }
                )

                obat_checks.append(
                    {
                        "obat": item.get("obat", "Unknown"),
                        "resep_qty": resep_qty,
                        "stok_tersedia": stok_tersedia,
                        "stok_ada": "IYA" if stok_ok else "TIDAK",
                        "status_bpjs_fornas": item.get("fornas_summary", "Data Fornas tidak tersedia"),
                        "aturan_minum": item.get("aturan_minum", "Sesuai petunjuk dokter"),
                        "catatan_klinis": "LLM tidak mengembalikan detail item obat. Gunakan review klinis manual.",
                    }
                )

        existing_obat_keys = {
            str(item.get("obat", "")).strip().lower()
            for item in clinical_items
            if str(item.get("obat", "")).strip()
        }
        for item in enriched_prescriptions:
            db_obat_name = str(item.get("obat", "")).strip()
            if not db_obat_name:
                continue

            db_obat_key = db_obat_name.lower()
            if db_obat_key in existing_obat_keys:
                continue

            stok_data = item.get("stok_data", {}) if isinstance(item, dict) else {}
            stok_tersedia = stok_data.get("stok", 0)
            resep_qty = item.get("resep_qty", 0)
            try:
                stok_ok = float(stok_tersedia or 0) >= float(resep_qty or 0)
            except Exception:
                stok_ok = False

            clinical_items.append(
                {
                    "obat": db_obat_name,
                    "status": "TIDAK AMAN",
                    "alasan": ["Model tidak memberikan evaluasi untuk item resep ini."],
                    "rekomendasi": "Lakukan review manual oleh dokter/farmasis sebelum terapi dilanjutkan.",
                    "cek_klinik": {
                        "validasi_dosis": {"status": "PERLU REVIEW", "catatan": "Tidak tersedia dari output model."},
                        "screening_interaksi_obat": {"status": "PERLU REVIEW", "catatan": "Tidak tersedia dari output model."},
                        "cek_kontraindikasi": {"status": "PERLU REVIEW", "catatan": "Tidak tersedia dari output model."},
                        "cek_alergi": {"status": "PERLU REVIEW", "catatan": "Tidak tersedia dari output model."},
                    },
                }
            )

            obat_checks.append(
                {
                    "obat": db_obat_name,
                    "resep_qty": resep_qty,
                    "stok_tersedia": stok_tersedia,
                    "stok_ada": "IYA" if stok_ok else "TIDAK",
                    "status_bpjs_fornas": item.get("fornas_summary", "Data Fornas tidak tersedia"),
                    "aturan_minum": item.get("aturan_minum", "Sesuai petunjuk dokter"),
                    "catatan_klinis": "LLM tidak mengembalikan evaluasi untuk item resep ini.",
                }
            )

        validasi_ringkas_per_obat: List[Dict[str, str]] = []
        for item in clinical_items:
            if not isinstance(item, dict):
                continue

            obat_name = str(item.get("obat") or "-").strip() or "-"
            cek_klinik = item.get("cek_klinik", {}) if isinstance(item.get("cek_klinik"), dict) else {}
            dosis_data = cek_klinik.get("validasi_dosis") if isinstance(cek_klinik.get("validasi_dosis"), dict) else {}

            output_ringkas = item.get("output_ringkas") if isinstance(item.get("output_ringkas"), dict) else {}
            dosis_status = _normalize_check_status(output_ringkas.get("dosis") or dosis_data.get("status"))

            catatan_candidates = [
                output_ringkas.get("catatan"),
                dosis_data.get("catatan"),
                (item.get("alasan") or [""])[0] if isinstance(item.get("alasan"), list) and item.get("alasan") else "",
                item.get("rekomendasi"),
            ]
            catatan_singkat = ""
            for candidate in catatan_candidates:
                catatan_singkat = _short_note(candidate)
                if catatan_singkat:
                    break

            if not catatan_singkat:
                if dosis_status == "AMAN":
                    catatan_singkat = "Dosis sesuai profil pasien berdasarkan evaluasi MedGemma."
                elif dosis_status == "TIDAK AMAN":
                    catatan_singkat = "Dosis berisiko, perlu penyesuaian dan review farmasis/dokter."
                else:
                    catatan_singkat = "Perlu verifikasi tambahan untuk memastikan dosis aman."

            item["output_ringkas"] = {
                "dosis": dosis_status,
                "catatan": catatan_singkat,
            }
            validasi_ringkas_per_obat.append(
                {
                    "obat": obat_name,
                    "dosis": dosis_status,
                    "catatan": catatan_singkat,
                }
            )

        clinical_issues_count = sum(1 for item in clinical_items if item.get("status") == "TIDAK AMAN")

        validasi_result = llm_result.get("validasi") if isinstance(llm_result.get("validasi"), dict) else {}
        default_inventory_ok = all(str(item.get("stok_ada", "")).upper() == "IYA" for item in obat_checks) if obat_checks else False
        validasi_inventory = _to_bool(validasi_result.get("inventory"), default=default_inventory_ok)
        validasi_administrasi = _to_bool(validasi_result.get("administrasi"), default=True)

        verdict = str(llm_result.get("verdict", "")).strip().upper()
        if verdict not in {"AMAN", "PERLU REVIEW FARMASIS/DOKTER"}:
            verdict = "PERLU REVIEW FARMASIS/DOKTER" if clinical_issues_count > 0 else "AMAN"

        next_step = str(llm_result.get("next_step", "")).strip().upper()
        if next_step not in {"DISPENSING", "STOP"}:
            if verdict == "PERLU REVIEW FARMASIS/DOKTER" or not validasi_inventory:
                next_step = "STOP"
            else:
                next_step = "DISPENSING"

        risk_level = str(llm_result.get("risk_level", "")).strip().upper()
        if risk_level not in {"LOW", "MEDIUM", "HIGH"}:
            if verdict == "PERLU REVIEW FARMASIS/DOKTER":
                risk_level = "HIGH"
            elif not validasi_inventory or not validasi_administrasi:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

        kesimpulan_data = llm_result.get("kesimpulan") if isinstance(llm_result.get("kesimpulan"), dict) else {}
        jumlah_masalah_raw = kesimpulan_data.get("jumlah_masalah")
        try:
            jumlah_masalah = int(jumlah_masalah_raw)
        except Exception:
            jumlah_masalah = clinical_issues_count

        saran_kesimpulan = str(kesimpulan_data.get("saran") or "").strip()
        if not saran_kesimpulan:
            saran_kesimpulan = (
                "Disarankan revisi resep dokter."
                if jumlah_masalah > 0
                else "Terapi dapat dilanjutkan dengan monitoring klinis rutin."
            )

        alasan_utama = llm_result.get("alasan_utama") if isinstance(llm_result.get("alasan_utama"), list) else []
        alasan_utama = [str(x).strip() for x in alasan_utama if str(x).strip()]
        if not alasan_utama:
            for item in clinical_items:
                if item.get("status") == "TIDAK AMAN":
                    alasan_utama.extend(item.get("alasan", []))
            if not alasan_utama:
                alasan_utama = ["Tidak ada alasan utama tambahan dari model."]

        ringkasan_klinis = str(llm_result.get("ringkasan_klinis", "")).strip()
        if not ringkasan_klinis:
            ringkasan_klinis = (
                f"Terdapat {jumlah_masalah} masalah terapi obat."
                if jumlah_masalah > 0
                else "Tidak ditemukan masalah terapi obat bermakna."
            )

        analysis = str(llm_result.get("analysis", "")).strip() or ringkasan_klinis
        recommendation = str(llm_result.get("recommendation", "")).strip() or saran_kesimpulan

        confidence_raw = llm_result.get("confidence")
        try:
            confidence = float(confidence_raw)
        except Exception:
            confidence = 0.85 if risk_level == "LOW" else 0.8 if risk_level == "MEDIUM" else 0.75
        confidence = max(0.0, min(1.0, confidence))

        patient_demo_parts: List[str] = []
        if patient_payload.get("jenis_kelamin"):
            patient_demo_parts.append(str(patient_payload.get("jenis_kelamin")))
        if patient_payload.get("usia_tahun") is not None:
            patient_demo_parts.append(f"{patient_payload.get('usia_tahun')} tahun")
        patient_demo_text = ", ".join(patient_demo_parts) if patient_demo_parts else "-"

        stock_lookup: Dict[str, Dict[str, Any]] = {}
        for stock_item in obat_checks:
            stock_name = str(stock_item.get("obat", "")).strip().lower()
            if stock_name:
                stock_lookup[stock_name] = stock_item

        def _find_stock_item(obat_name: str) -> Dict[str, Any]:
            normalized = str(obat_name or "").strip().lower()
            if not normalized:
                return {}
            if normalized in stock_lookup:
                return stock_lookup[normalized]
            for key, value in stock_lookup.items():
                if key in normalized or normalized in key:
                    return value
            return {}

        report_lines: List[str] = [
            "VALIDASI FARMASI KLINIK (RINGKAS)",
            f"Nama: {patient_payload['nama']}",
            f"No: {patient_payload['mrn']}",
            f"Profil: {patient_demo_text}",
            f"Diagnosa: {diag_name}",
            "",
        ]

        for idx, item in enumerate(clinical_items, start=1):
            status_item = str(item.get("status", "TIDAK AMAN")).upper()
            status_label = "AMAN" if status_item == "SESUAI" else "TIDAK AMAN"
            cek_klinik = item.get("cek_klinik", {}) if isinstance(item.get("cek_klinik"), dict) else {}
            stock_item = _find_stock_item(str(item.get("obat", "")))

            stock_ada_raw = str(stock_item.get("stok_ada", "-")).strip().upper()
            if stock_ada_raw == "IYA":
                stock_label = "ADA"
            elif stock_ada_raw == "TIDAK":
                stock_label = "TIDAK ADA"
            else:
                stock_label = "-"

            stock_qty = stock_item.get("stok_tersedia", "-")
            resep_qty = stock_item.get("resep_qty", "-")

            def _line_check(label: str, key: str) -> str:
                check_data = cek_klinik.get(key) if isinstance(cek_klinik.get(key), dict) else {}
                check_status = str(check_data.get("status", "PERLU REVIEW"))
                check_note = str(check_data.get("catatan", "")).strip() or "-"
                return f"- {label}: {check_status} ({check_note})"

            report_lines.append(
                f"{idx}. {item.get('obat', '-')} = {status_label} | "
                f"Stok: {stock_label} (stok {stock_qty}, resep {resep_qty})"
            )
            report_lines.append(_line_check("Validasi Dosis", "validasi_dosis"))
            report_lines.append(_line_check("Screening Interaksi Obat", "screening_interaksi_obat"))
            report_lines.append(_line_check("Cek Kontraindikasi", "cek_kontraindikasi"))
            report_lines.append(_line_check("Cek Alergi", "cek_alergi"))
            report_lines.append("")

        report_lines.append(f"Masalah terapi obat: {jumlah_masalah}")
        report_lines.append(f"Saran: {saran_kesimpulan}")
        clinical_validation_report = "\n".join(report_lines).strip()

        alasan_text = "\n".join([f"- {x}" for x in alasan_utama])
        ai_response = (
            f"Engine: MedGemma ({model_name})\n"
            f"Risk Level: {risk_level}\n"
            f"Verdict: {verdict}\n"
            f"Confidence: {confidence:.2f}\n"
            f"Rekomendasi Alur: {next_step}\n\n"
            f"Analisis:\n{analysis}\n\n"
            f"Rekomendasi:\n{recommendation}\n\n"
            f"Alasan Utama:\n{alasan_text}\n\n"
            f"{clinical_validation_report}"
        )

        medgemma_routed = "medgemma" in str(model_name).lower()
        flow_trace = {
            "step_1_ui_input": {
                "status": "done",
                "detail": f"Validasi pasien {patient_payload['mrn']}",
            },
            "step_2_fastapi_gateway": {
                "status": "done",
                "detail": "Request diterima endpoint validasi",
            },
            "step_3_agent_understanding": {
                "status": "done",
                "detail": f"Entity pasien={patient_payload['mrn']}, jumlah_obat={len(obat_list)}",
            },
            "step_4_mcp_tools_execution": {
                "status": "done",
                "detail": "Data pasien, resep, stok, fornas, dan ICD diambil dari DB tools",
            },
            "step_5_agent_reasoning": {
                "status": "done",
                "detail": (
                    f"Data dikirim ke MedGemma model={model_name}, "
                    f"4 cek klinis dieksekusi untuk {len(clinical_items)} obat, "
                    f"risk_level={risk_level}, verdict={verdict}, confidence={confidence:.2f}"
                ),
            },
            "step_6_response_to_ui": {
                "status": "done",
                "detail": "Hasil siap ditampilkan di UI",
            },
        }

        return {
            "status": "success",
            "patient_name": patient_data.get("nama", patient_id),
            "patient_mrn": patient_data.get("mrn", patient_id),
            "patient_snapshot": {
                "jenis_kelamin": patient_payload.get("jenis_kelamin"),
                "usia_tahun": patient_payload.get("usia_tahun"),
                "tanggal_lahir": patient_payload.get("tanggal_lahir"),
                "alergi": patient_payload.get("alergi"),
                "bpjs_status": bpjs_status,
                "faskes_level": faskes_level,
                "diagnosis": diag_name,
                "diagnosis_code": diagnosis_code,
            },
            "diagnosis": diag_name,
            "obat_list": obat_list,
            "clinical_engine": {
                "target": "MedGemma",
                "provider": "Ollama",
                "model": model_name,
                "routed_to_medgemma": medgemma_routed,
                "mandatory_checks": [
                    "validasi_dosis",
                    "screening_interaksi_obat",
                    "cek_kontraindikasi",
                    "cek_alergi",
                ],
            },
            "clinical_items": clinical_items,
            "validasi_ringkas_per_obat": validasi_ringkas_per_obat,
            "clinical_summary": {
                "jumlah_masalah_terapi_obat": jumlah_masalah,
                "saran": saran_kesimpulan,
            },
            "clinical_validation_report": clinical_validation_report,
            "ai_analysis": ai_response,
            "risk_level": risk_level,
            "analysis": analysis,
            "recommendation": recommendation,
            "confidence": confidence,
            "validation_summary": {
                "diagnosis": diag_name,
                "diagnosis_code": diagnosis_code,
                "stok_obat_ada": "IYA" if validasi_inventory else "TIDAK",
                "administrasi_valid": "IYA" if validasi_administrasi else "TIDAK",
                "bpjs_status": bpjs_status,
                "faskes_level": faskes_level,
                "rekomendasi_alur": next_step,
                "masalah_terapi_obat": jumlah_masalah,
                "obat_checks": obat_checks,
            },
            "validasi": {
                "administrasi": validasi_administrasi,
                "inventory": validasi_inventory,
                "bpjs_status": bpjs_status,
                "faskes_level": faskes_level,
            },
            "verdict": verdict,
            "llm_reasoning": {
                "ringkasan_klinis": ringkasan_klinis,
                "alasan_utama": alasan_utama,
            },
            "next_step": next_step,
            "flow_trace": flow_trace,
            "architecture_flow": "UI -> FastAPI (Bridge) -> AI Agent -> MCP Tools -> MedGemma (Ollama) -> UI",
        }

    async def run_dispensing_preview(
        self,
        mcp_client: Any,
        prescription_id: str,
        include_llm_reasoning: bool = True,
    ) -> Dict[str, Any]:
        preview = await self._call_tool_json(
            mcp_client,
            "get_dispensing_preview",
            {"prescription_id": prescription_id},
        )
        if not preview:
            return {"status": "error", "message": "Gagal mengambil data dispensing."}
        if preview.get("status") == "error":
            return preview

        validation = await self._call_tool_json(
            mcp_client,
            "validate_prescription",
            {"prescription_id": str(prescription_id)},
        )

        validation_message = validation.get("context") or validation.get("message") or "Validasi resep berhasil."
        stages = preview.get("dispensing_stages") or {
            "penyiapan_obat": "SIAP DIPROSES",
            "peracikan": "DIPERLUKAN" if preview.get("need_mixing") else "TIDAK DIPERLUKAN",
            "pemberian_obat": "MENUNGGU FINALISASI DISPENSING",
        }

        model_name = self._active_model_name()
        medgemma_routed = include_llm_reasoning and ("medgemma" in str(model_name).lower())

        def _extract_first_json_object(text: str) -> Optional[Dict[str, Any]]:
            if not text:
                return None

            expected_keys = {
                "ringkasan",
                "cara_penyiapan",
                "edukasi_penggunaan",
                "peringatan",
                "monitoring_lanjutan",
                "kapan_harus_hubungi_faskes",
            }
            fallback_candidate: Optional[Dict[str, Any]] = None
            candidate_starts = [idx for idx, ch in enumerate(text) if ch == "{"]
            for start in candidate_starts:
                depth = 0
                for idx in range(start, len(text)):
                    ch = text[idx]
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            snippet = text[start : idx + 1]
                            try:
                                parsed = json.loads(snippet)
                                if isinstance(parsed, dict):
                                    if expected_keys.intersection(set(parsed.keys())):
                                        return parsed
                                    if fallback_candidate is None:
                                        fallback_candidate = parsed
                            except Exception:
                                break
            return fallback_candidate

        def _as_text_list(value: Any) -> List[str]:
            def _clean_item(raw: Any) -> str:
                text = str(raw or "").strip()
                if not text:
                    return ""

                # Drop common markdown artifacts without changing semantic content.
                text = text.replace("**", "").strip()
                text = text.lstrip("-*0123456789. )\t").strip()
                if not text or len(text) < 3:
                    return ""
                return text

            if isinstance(value, list):
                cleaned_items = []
                for item in value:
                    cleaned = _clean_item(item)
                    if cleaned:
                        cleaned_items.append(cleaned)
                return cleaned_items
            if isinstance(value, str):
                text = value.strip()
                if not text:
                    return []
                split_by = "\n" if "\n" in text else ";"
                parts = [_clean_item(part) for part in text.split(split_by)]
                parts = [part for part in parts if part]
                if parts:
                    return parts
                cleaned_text = _clean_item(text)
                return [cleaned_text] if cleaned_text else []
            return []

        def _normalized_key(value: Any) -> str:
            text = str(value or "").strip().lower()
            if not text:
                return ""
            normalized = []
            for ch in text:
                if ch.isalnum():
                    normalized.append(ch)
            return "".join(normalized)

        def _pick_value_casefold(data: Dict[str, Any], key_aliases: List[str]) -> Any:
            if not isinstance(data, dict):
                return None
            alias_set = {_normalized_key(alias) for alias in key_aliases if _normalized_key(alias)}
            if not alias_set:
                return None
            for key, value in data.items():
                if _normalized_key(key) in alias_set:
                    return value
            return None

        def _extract_from_plain_text(raw_text: str) -> Dict[str, Any]:
            sections: Dict[str, List[str]] = {
                "ringkasan": [],
                "cara_penyiapan": [],
                "edukasi_penggunaan": [],
                "peringatan": [],
                "monitoring_lanjutan": [],
                "kapan_harus_hubungi_faskes": [],
            }
            if not raw_text:
                return sections

            header_aliases = {
                "ringkasan": {
                    "ringkasan",
                    "summary",
                },
                "cara_penyiapan": {
                    "carapenyiapan",
                    "penyiapan",
                    "langkahpenyiapan",
                    "prepare",
                },
                "edukasi_penggunaan": {
                    "edukasipenggunaan",
                    "edukasipasien",
                    "edukasi",
                    "konseling",
                },
                "peringatan": {
                    "peringatan",
                    "warning",
                    "warningpoints",
                    "catatanpenting",
                },
                "monitoring_lanjutan": {
                    "monitoringlanjutan",
                    "monitoring",
                    "pemantauan",
                    "tindaklanjut",
                },
                "kapan_harus_hubungi_faskes": {
                    "kapanharushubungifaskes",
                    "kapanharuskerumahsakit",
                    "redflags",
                    "warninglanjutan",
                },
            }

            active_section: Optional[str] = None
            for raw_line in str(raw_text).splitlines():
                line = str(raw_line or "").strip()
                if not line:
                    continue

                line_no_bullet = line.lstrip("-*0123456789. )\t").strip()
                key_candidate = _normalized_key(line_no_bullet.split(":", 1)[0])

                matched_section: Optional[str] = None
                for section_name, aliases in header_aliases.items():
                    if key_candidate in aliases:
                        matched_section = section_name
                        break

                if matched_section:
                    active_section = matched_section
                    if ":" in line_no_bullet:
                        tail = line_no_bullet.split(":", 1)[1].strip(" -\t")
                        if tail:
                            sections[active_section].append(tail)
                    continue

                if active_section:
                    sections[active_section].append(line_no_bullet)

            return {
                "ringkasan": " ".join(sections["ringkasan"]).strip(),
                "cara_penyiapan": sections["cara_penyiapan"],
                "edukasi_penggunaan": sections["edukasi_penggunaan"],
                "peringatan": sections["peringatan"],
                "monitoring_lanjutan": sections["monitoring_lanjutan"],
                "kapan_harus_hubungi_faskes": sections["kapan_harus_hubungi_faskes"],
            }

        preview_checklist = preview.get("pemberian_obat_checklist", [])
        if not isinstance(preview_checklist, list):
            preview_checklist = []

        dispensing_reasoning: Dict[str, Any] = {
            "ringkasan": "",
            "cara_penyiapan": [],
            "edukasi_penggunaan": [],
            "peringatan": [],
            "monitoring_lanjutan": [],
            "kapan_harus_hubungi_faskes": [],
            "checklist_serah_obat": [str(x).strip() for x in preview_checklist if str(x).strip()],
        }
        used_medgemma_reasoning = False

        if include_llm_reasoning:
            try:
                reasoning_payload = {
                    "target_engine": "MedGemma",
                    "workflow": "DISPENSING_CLINICAL_REASONING",
                    "prescription_id": str(preview.get("prescription_id", prescription_id)),
                    "patient_name": preview.get("patient_name", "-"),
                    "need_mixing": bool(preview.get("need_mixing", False)),
                    "medicines_detail": (preview.get("medicines_detail", []) if isinstance(preview.get("medicines_detail"), list) else [])[:6],
                }

                prompt = (
                    "Anda adalah MedGemma yang bertindak sebagai apoteker klinis pada tahap dispensing obat.\n"
                    "Buat screening dispensing yang sangat informatif, praktis, aman, dan mudah dipahami pasien.\n"
                    "Gunakan data input sebagai sumber utama; jangan mengarang item obat baru.\n"
                    "Sertakan langkah operasional dan edukasi pasien yang jelas.\n"
                    "Untuk setiap list, isi 4-6 poin; tiap poin 1-2 kalimat pendek yang actionable.\n"
                    "Output HARUS JSON valid tanpa markdown.\n\n"
                    "DATA DISPENSING (JSON):\n"
                    f"{json.dumps(reasoning_payload, ensure_ascii=False)}\n\n"
                    "Skema output JSON wajib:\n"
                    "{\n"
                    "  \"ringkasan\": \"...\",\n"
                    "  \"cara_penyiapan\": [\"...\"],\n"
                    "  \"edukasi_penggunaan\": [\"...\"],\n"
                    "  \"peringatan\": [\"...\"],\n"
                    "  \"monitoring_lanjutan\": [\"...\"],\n"
                    "  \"kapan_harus_hubungi_faskes\": [\"...\"]\n"
                    "}"
                )

                retry_prompt = (
                    "Anda adalah MedGemma, apoteker klinis.\n"
                    "Jawab informatif berdasarkan data dispensing berikut.\n"
                    "Jika JSON gagal, jawab format teks dengan 6 bagian ini:\n"
                    "Ringkasan:\nCara Penyiapan:\nEdukasi Penggunaan:\nPeringatan:\nMonitoring Lanjutan:\nKapan Harus Hubungi Faskes:\n"
                    "Masing-masing 4-6 poin, jangan menambah obat baru.\n"
                    "DATA DISPENSING (JSON):\n"
                    f"{json.dumps(reasoning_payload, ensure_ascii=False)}"
                )

                llm_raw = ""
                for attempt in range(2):
                    attempt_prompt = prompt if attempt == 0 else retry_prompt
                    attempt_num_predict = 1400 if attempt == 0 else 2200
                    llm_raw = llm.generate(
                        attempt_prompt,
                        options={"temperature": 0.0, "num_predict": attempt_num_predict},
                        response_format="json" if attempt == 0 else None,
                    ).strip()

                    llm_clean = llm_raw.replace("```json", "").replace("```", "").strip()
                    try:
                        llm_result = json.loads(llm_clean)
                    except Exception:
                        llm_result = _extract_first_json_object(llm_clean)

                    ringkasan = ""
                    cara_penyiapan: List[str] = []
                    edukasi_penggunaan: List[str] = []
                    peringatan: List[str] = []
                    monitoring_lanjutan: List[str] = []
                    kapan_harus_hubungi_faskes: List[str] = []

                    if isinstance(llm_result, dict):
                        ringkasan_value = _pick_value_casefold(
                            llm_result,
                            ["ringkasan", "summary", "ringkasan_klinis"],
                        )
                        cara_value = _pick_value_casefold(
                            llm_result,
                            ["cara_penyiapan", "penyiapan", "langkah_penyiapan"],
                        )
                        edukasi_value = _pick_value_casefold(
                            llm_result,
                            ["edukasi_penggunaan", "edukasi", "konseling"],
                        )
                        peringatan_value = _pick_value_casefold(
                            llm_result,
                            ["peringatan", "warning", "catatan_penting"],
                        )
                        monitoring_value = _pick_value_casefold(
                            llm_result,
                            ["monitoring_lanjutan", "monitoring", "pemantauan"],
                        )
                        hubungi_faskes_value = _pick_value_casefold(
                            llm_result,
                            [
                                "kapan_harus_hubungi_faskes",
                                "kapan_harus_ke_faskes",
                                "kapan_harus_ke_rumah_sakit",
                                "red_flags",
                            ],
                        )

                        ringkasan = str(ringkasan_value or "").strip()
                        cara_penyiapan = _as_text_list(cara_value)
                        edukasi_penggunaan = _as_text_list(edukasi_value)
                        peringatan = _as_text_list(peringatan_value)
                        monitoring_lanjutan = _as_text_list(monitoring_value)
                        kapan_harus_hubungi_faskes = _as_text_list(hubungi_faskes_value)

                    if not (
                        ringkasan
                        or cara_penyiapan
                        or edukasi_penggunaan
                        or peringatan
                        or monitoring_lanjutan
                        or kapan_harus_hubungi_faskes
                    ):
                        parsed_text_sections = _extract_from_plain_text(llm_clean)
                        if isinstance(parsed_text_sections, dict):
                            ringkasan = str(parsed_text_sections.get("ringkasan") or "").strip()
                            cara_penyiapan = _as_text_list(parsed_text_sections.get("cara_penyiapan"))
                            edukasi_penggunaan = _as_text_list(parsed_text_sections.get("edukasi_penggunaan"))
                            peringatan = _as_text_list(parsed_text_sections.get("peringatan"))
                            monitoring_lanjutan = _as_text_list(parsed_text_sections.get("monitoring_lanjutan"))
                            kapan_harus_hubungi_faskes = _as_text_list(
                                parsed_text_sections.get("kapan_harus_hubungi_faskes")
                            )

                    if (
                        ringkasan
                        or cara_penyiapan
                        or edukasi_penggunaan
                        or peringatan
                        or monitoring_lanjutan
                        or kapan_harus_hubungi_faskes
                    ):
                        detail_quality_ok = (
                            len(cara_penyiapan) >= 3
                            and len(edukasi_penggunaan) >= 3
                            and len(peringatan) >= 3
                        )

                        if attempt == 0 and not detail_quality_ok:
                            logger.info(
                                "[DISPENSING LLM] Output awal terlalu ringkas, meminta elaborasi ulang. "
                                f"cara={len(cara_penyiapan)}, edukasi={len(edukasi_penggunaan)}, peringatan={len(peringatan)}"
                            )
                            continue

                        used_medgemma_reasoning = True
                        dispensing_reasoning["raw_response"] = llm_raw
                        if isinstance(llm_result, dict):
                            dispensing_reasoning["medgemma_output"] = llm_result
                        if ringkasan:
                            dispensing_reasoning["ringkasan"] = ringkasan
                        if cara_penyiapan:
                            dispensing_reasoning["cara_penyiapan"] = cara_penyiapan
                        if edukasi_penggunaan:
                            dispensing_reasoning["edukasi_penggunaan"] = edukasi_penggunaan
                        if peringatan:
                            dispensing_reasoning["peringatan"] = peringatan
                        if monitoring_lanjutan:
                            dispensing_reasoning["monitoring_lanjutan"] = monitoring_lanjutan
                        if kapan_harus_hubungi_faskes:
                            dispensing_reasoning["kapan_harus_hubungi_faskes"] = kapan_harus_hubungi_faskes
                        break

                if not used_medgemma_reasoning and llm_raw:
                    dispensing_reasoning["raw_response"] = llm_raw
                    logger.warning(
                        "[DISPENSING LLM] Output MedGemma tidak dapat dipetakan ke schema dispensing. "
                        f"Potongan output: {llm_raw[:240]}"
                    )
            except Exception as e:
                logger.warning(f"[DISPENSING LLM] Gagal memproses output model: {e}")

        checklist_final = dispensing_reasoning.get("checklist_serah_obat", [])
        if not isinstance(checklist_final, list) or not checklist_final:
            checklist_final = preview.get("pemberian_obat_checklist", [])

        reasoning_source = "medgemma" if used_medgemma_reasoning else ("medgemma-empty" if include_llm_reasoning else "disabled")

        return {
            "status": "success",
            "prescription_id": preview.get("prescription_id", prescription_id),
            "patient_name": preview.get("patient_name", "-"),
            "medicines": preview.get("medicines", []),
            "medicines_detail": preview.get("medicines_detail", []),
            "need_mixing": preview.get("need_mixing", False),
            "dispensing_stages": stages,
            "pemberian_obat_checklist": checklist_final,
            "validation": validation,
            "validation_message": validation_message,
            "dispensing_reasoning": {
                "engine": {
                    "target": "MedGemma",
                    "provider": "Ollama",
                    "model": model_name,
                    "routed_to_medgemma": medgemma_routed,
                    "mode": "llm" if include_llm_reasoning else "fast",
                    "reasoning_source": reasoning_source,
                },
                "ringkasan": dispensing_reasoning.get("ringkasan", ""),
                "cara_penyiapan": dispensing_reasoning.get("cara_penyiapan", []),
                "edukasi_penggunaan": dispensing_reasoning.get("edukasi_penggunaan", []),
                "peringatan": dispensing_reasoning.get("peringatan", []),
                "monitoring_lanjutan": dispensing_reasoning.get("monitoring_lanjutan", []),
                "kapan_harus_hubungi_faskes": dispensing_reasoning.get("kapan_harus_hubungi_faskes", []),
                "checklist_serah_obat": checklist_final,
                "medgemma_output": dispensing_reasoning.get("medgemma_output"),
                "raw_response": dispensing_reasoning.get("raw_response", ""),
            },
            "workflow_status": "Ready for dispensing",
        }

    async def run_dispensing_complete(self, mcp_client: Any, prescription_id: str) -> Dict[str, Any]:
        result = await self._call_tool_json(
            mcp_client,
            "complete_dispensing",
            {"prescription_id": prescription_id},
        )
        if isinstance(result, dict) and result.get("status") == "success":
            result.setdefault(
                "dispensing_stages",
                {
                    "penyiapan_obat": "SELESAI",
                    "peracikan": "SELESAI / TIDAK DIPERLUKAN",
                    "pemberian_obat": "SIAP DIBERIKAN KE PASIEN",
                },
            )
            result.setdefault(
                "pemberian_obat_checklist",
                [
                    "Serahkan obat sesuai etiket dan nama pasien",
                    "Edukasi aturan minum diulang saat serah obat",
                    "Konfirmasi pasien menerima seluruh item obat",
                ],
            )
        if result:
            return result
        return {"status": "error", "message": "Gagal menyelesaikan dispensing."}

    async def run_insurance_verification(
        self,
        mcp_client: Any,
        kartu_id: str,
        jenis: str,
    ) -> Dict[str, Any]:
        billing = await self._call_tool_json(
            mcp_client,
            "get_patient_billing",
            {"kartu_id": kartu_id},
        )

        if billing.get("status") == "error":
            return {
                "status": "error",
                "verification": billing.get("verification", "Data pasien tidak ditemukan."),
            }

        patient_name = billing.get("patient_name", kartu_id)
        total_tagihan = float(billing.get("total_tagihan", 0) or 0)
        trans_no = f"TRX-{uuid.uuid4().hex[:6].upper()}"

        if jenis == "BPJS Kesehatan":
            await self._call_tool_json(mcp_client, "validate_bpjs", {"kartu_id": kartu_id})
            return {
                "status": "success",
                "kartu_id": kartu_id,
                "jenis": jenis,
                "patient_name": patient_name,
                "total_tagihan": 0,
                "verification": "Tagihan Rp 0. Dijamin sepenuhnya oleh BPJS Kesehatan (Sesuai restriksi Fornas).",
                "plafon": "Unlimited (Sesuai Diagnosa INA-CBG)",
                "trans_no": trans_no,
            }

        if jenis == "Asuransi Swasta":
            verdict = await self._call_tool_json(
                mcp_client,
                "validate_private_insurance",
                {"kartu_id": kartu_id},
            )
            verification_msg = verdict.get("context", "Asuransi Swasta terverifikasi.")
        else:
            verification_msg = "Pasien Umum (Bayar Penuh)"

        return {
            "status": "success",
            "kartu_id": kartu_id,
            "jenis": jenis,
            "patient_name": patient_name,
            "total_tagihan": total_tagihan,
            "verification": verification_msg,
            "plafon": "Bayar Sendiri / Sesuai Limit Asuransi",
            "trans_no": trans_no,
        }

    async def run_payment_process(
        self,
        mcp_client: Any,
        kartu_id: str,
        jenis: str,
        total_tagihan: float = 0,
    ) -> Dict[str, Any]:
        result = await self._call_tool_json(
            mcp_client,
            "process_payment",
            {
                "kartu_id": kartu_id,
                "jenis": jenis,
                "total_tagihan": float(total_tagihan or 0),
            },
        )
        if result:
            return result
        return {"status": "error", "message": "Gagal mencatat pembayaran."}


    @staticmethod
    def _extract_answer_from_rag_result(tool_result: Any) -> str:
        """Extract answer field from RAG/ask_question tool result"""
        try:
            # Handle MCP TextContent format
            if hasattr(tool_result, "content"):
                content = tool_result.content
                if isinstance(content, list) and len(content) > 0:
                    content = content[0]
                if hasattr(content, "text"):
                    # Parse JSON from text
                    import json
                    try:
                        data = json.loads(content.text)
                        return data.get("answer", "")
                    except:
                        return content.text if hasattr(content, "text") else str(content)
                if isinstance(content, dict):
                    return content.get("answer", "")
                return str(content) if content else ""
            
            # Handle dict format
            elif isinstance(tool_result, dict):
                return tool_result.get("answer", "")
            
            return ""
        except Exception as e:
            logger.warning(f"Error extracting RAG answer: {str(e)}")
            return ""

    @staticmethod
    def _extract_context_from_result(tool_result: Any) -> str:
        """Extract context field from MCP CallToolResult"""
        try:
            # Debug log the actual result
            logger.info(f"_extract_context type={type(tool_result).__name__}, hasattr content={hasattr(tool_result, 'content')}")
            
            # MCP returns CallToolResult with content list of TextContent objects
            if hasattr(tool_result, "content"):
                content = tool_result.content
                # Extract first TextContent from list
                if isinstance(content, list) and len(content) > 0:
                    content = content[0]
                
                # Parse JSON from TextContent.text
                if hasattr(content, "text"):
                    text_content = content.text
                    logger.info(f"_extract text length={len(text_content)}, starts with={text_content[:100]}")
                    data = json.loads(text_content)
                    ctx = data.get("context", "") or data.get("answer", "")
                    if ctx:
                        logger.info(f"✓ Got context: {ctx[:60]}...")
                        return ctx
                    logger.warning("No context field in JSON")
            
            # Fallback: try as dict
            elif isinstance(tool_result, dict):
                ctx = tool_result.get("context", "") or tool_result.get("answer", "")
                if ctx:
                    return ctx
            
            logger.warning(f"Could not extract context from {type(tool_result).__name__}")
            return ""
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {str(e)}")
            return ""
        except Exception as e:
            logger.error(f"Error extracting context: {str(e)}", exc_info=True)
            return ""
