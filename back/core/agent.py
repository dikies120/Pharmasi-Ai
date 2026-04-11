import json
import logging
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

    def decide(self, question: str) -> Dict[str, Any]:
        logger.info(f"Deciding tool for question: {question[:100]}...")
        
        prompt = f"{SYSTEM_PROMPT}\n\nPERTANYAAN USER:\n{question}\n\nJAWAB DENGAN JSON HANYA, JANGAN ADA TEKS LAIN:"

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
        
        # ⭐ SPECIAL HANDLING: ask_question returns final answer directly
        if tool_name == "ask_question":
            answer = self._extract_answer_from_rag_result(tool_result)
            if answer:
                logger.info("Using RAG answer directly (no final_answer_prompt)")
                return answer
        
        # For database tools, use final_answer_prompt to format
        context = self._extract_context_from_result(tool_result)
        logger.info(f"[EXTRACT] context extracted: '{context[:80] if context else 'EMPTY'}'")
        
        # ⭐ JIKA ADA DATA OBAT, LANGSUNG RETURN TANPA PERLU LLM (kecuali ada custom prompt)
        if not custom_prompt and context and context.strip() and "Stok:" in context:
            logger.info(f"[DIRECT] Data obat ditemukan, return langsung: {context[:60]}")
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
    ) -> Dict[str, Any]:
        """Single chat turn orchestration: decide -> tool call -> final answer."""
        decision = self.decide(question)

        if "answer" in decision:
            return {
                "answer": decision["answer"],
                "tool_used": None,
                "status": "success",
            }

        tool = decision.get("tool")
        arguments = decision.get("arguments", {}) or {}

        if not tool:
            return {
                "answer": "Tidak dapat menentukan tool yang sesuai untuk pertanyaan ini",
                "tool_used": None,
                "status": "error",
            }

        try:
            available_tools = await mcp_client.list_tools()
            if tool not in available_tools:
                return {
                    "answer": f"Tool '{tool}' tidak tersedia. Available: {available_tools}",
                    "tool_used": tool,
                    "status": "error",
                }
        except Exception as e:
            return {
                "answer": f"Gagal check available tools: {str(e)}",
                "tool_used": tool,
                "status": "error",
            }

        try:
            result = await mcp_client.call_tool(tool, arguments)
        except Exception as e:
            return {
                "answer": f"Error calling tool: {str(e)}",
                "tool_used": tool,
                "status": "error",
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

        return {
            "answer": answer,
            "tool_used": tool,
            "status": "success",
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

    async def run_validasi_obat(self, mcp_client: Any, patient_id: str) -> Dict[str, Any]:
        logger.info(f"[Agent] Starting validation workflow for patient: {patient_id}")

        patient_data = await self._call_tool_json(
            mcp_client,
            "get_patient_data",
            {"patient_id": patient_id},
        )
        if patient_data.get("error"):
            return {"status": "error", "message": patient_data.get("error")}

        diagnosis_code = (
            patient_data.get("active_diagnosis", ["J06.9"])[0]
            if patient_data.get("active_diagnosis")
            else "J06.9"
        )
        prescriptions = patient_data.get("active_prescriptions", [])
        bpjs_status = patient_data.get("bpjs_status", "UMUM")
        faskes_level = patient_data.get("faskes_level", 1)

        icd_data = await self._call_tool_json(
            mcp_client,
            "get_icd11_data",
            {"kode_diagnosa": diagnosis_code},
        )
        diag_name = icd_data.get("nama", "Diagnosis Umum (ISPA)")

        obat_details: List[str] = []
        obat_list: List[str] = []
        obat_checks: List[Dict[str, Any]] = []
        validasi_administrasi = True
        validasi_inventory = True

        for p in prescriptions:
            drug_name = p.get("drug", "Unknown")
            qty = p.get("qty", 0)
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

            try:
                stok_tersedia = float(stock_data.get("stok", 0) or 0)
            except Exception:
                stok_tersedia = 0

            if stok_tersedia < float(qty or 0):
                validasi_inventory = False

            if bpjs_status == "BPJS":
                is_covered = True
                if faskes_level == 1 and not fornas_data.get("fpktp", True):
                    is_covered = False
                elif faskes_level in [2, 3] and not fornas_data.get("fpktl", True):
                    is_covered = False

                if not is_covered:
                    validasi_administrasi = False
                    pesan_adm = "TIDAK DITANGGUNG BPJS DI FASKES INI"
                else:
                    pesan_adm = "DITANGGUNG BPJS"
            else:
                is_covered = True
                pesan_adm = "PASIEN UMUM (Bebas Restriksi Faskes)"

            obat_details.append(
                "\n".join(
                    [
                        f"- obat = {drug_name}",
                        f"  resep qty = {qty}",
                        f"  stok tersedia = {stock_data.get('stok', 0)}",
                        f"  apakah stok obat ada? = {'IYA' if stok_tersedia >= float(qty or 0) else 'TIDAK'}",
                        f"  status bpjs/fornas = {pesan_adm}",
                        f"  aturan minum = {aturan_minum}",
                    ]
                )
            )
            obat_checks.append(
                {
                    "obat": drug_name,
                    "resep_qty": qty,
                    "stok_tersedia": stock_data.get("stok", 0),
                    "stok_ada": "IYA" if stok_tersedia >= float(qty or 0) else "TIDAK",
                    "status_bpjs_fornas": pesan_adm,
                    "aturan_minum": aturan_minum,
                }
            )

        context_string = "\n".join(obat_details)

        if validasi_inventory and validasi_administrasi:
            next_step = "DISPENSING" if bpjs_status == "BPJS" else "PEMBAYARAN"
        else:
            next_step = "STOP"

        ai_response = (
            f"diagnosis = {diag_name} ({diagnosis_code})\n"
            f"apakah stok obat ada? = {'IYA' if validasi_inventory else 'TIDAK'}\n"
            f"apakah administrasi valid? = {'IYA' if validasi_administrasi else 'TIDAK'}\n"
            f"status bpjs pasien = {bpjs_status}\n"
            f"faskes level = {faskes_level}\n"
            f"rekomendasi alur = {next_step}\n"
            f"detail obat:\n{context_string}"
        )

        return {
            "status": "success",
            "patient_name": patient_data.get("nama", patient_id),
            "patient_mrn": patient_data.get("mrn", patient_id),
            "diagnosis": diag_name,
            "obat_list": obat_list,
            "ai_analysis": ai_response,
            "validation_summary": {
                "diagnosis": diag_name,
                "diagnosis_code": diagnosis_code,
                "stok_obat_ada": "IYA" if validasi_inventory else "TIDAK",
                "administrasi_valid": "IYA" if validasi_administrasi else "TIDAK",
                "bpjs_status": bpjs_status,
                "faskes_level": faskes_level,
                "rekomendasi_alur": next_step,
                "obat_checks": obat_checks,
            },
            "validasi": {
                "administrasi": validasi_administrasi,
                "inventory": validasi_inventory,
                "bpjs_status": bpjs_status,
                "faskes_level": faskes_level,
            },
            "next_step": next_step,
            "architecture_flow": "UI -> FastAPI (Bridge) -> AI Agent (Brain) -> MCP Client -> MCP Server",
        }

    async def run_dispensing_preview(self, mcp_client: Any, prescription_id: str) -> Dict[str, Any]:
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

        return {
            "status": "success",
            "prescription_id": preview.get("prescription_id", prescription_id),
            "patient_name": preview.get("patient_name", "-"),
            "medicines": preview.get("medicines", []),
            "medicines_detail": preview.get("medicines_detail", []),
            "need_mixing": preview.get("need_mixing", False),
            "dispensing_stages": stages,
            "pemberian_obat_checklist": preview.get("pemberian_obat_checklist", []),
            "validation": validation,
            "validation_message": validation_message,
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
                    ctx = data.get("context", "")
                    if ctx:
                        logger.info(f"✓ Got context: {ctx[:60]}...")
                        return ctx
                    logger.warning("No context field in JSON")
            
            # Fallback: try as dict
            elif isinstance(tool_result, dict):
                ctx = tool_result.get("context", "")
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
