import json
import logging
from typing import Dict, Any, List, Optional

from back.core.llm import get_llm
from back.core.agents.base_agent import BaseAgent
from back.core.prompts import PATIENT_CHATBOT_PROMPT, PHARMACIST_CHATBOT_PROMPT, FINAL_ANSWER_PROMPT, SYSTEM_PROMPT

logger = logging.getLogger(__name__)
llm = get_llm()

class ChatAgent(BaseAgent):
    def final_answer(
        self,
        question: str,
        tool_result: Any,
        tool_name: str = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        custom_prompt: str = None
    ) -> str:
        logger.info(f"Generating final answer for question: {question[:100]}... (tool: {tool_name})")

        parsed_payload = self._parse_tool_payload(tool_result)
        context = ""
        if isinstance(parsed_payload, dict):
            context = str(parsed_payload.get("context") or parsed_payload.get("answer") or "").strip()

        if not context:
            context = self._extract_context_from_result(tool_result)

        logger.info(f"[EXTRACT] context extracted: '{context[:80] if context else 'EMPTY'}'")

        question_lower = str(question or "").lower()
        force_raw_keywords = ("raw", "mentah", "apa adanya", "verbatim", "jangan diringkas", "copy")
        force_raw = any(keyword in question_lower for keyword in force_raw_keywords)
        if force_raw and context and context.strip():
            logger.info(f"[DIRECT] User requested raw response (tool={tool_name})")
            return context

        if not context or context.strip() == "":
            context = "Data tidak ditemukan di database."

        history_text = self._build_history_text(conversation_history or []) or "(kosong)"

        if custom_prompt:
            system_text = custom_prompt.format(context=context, history_text=history_text, question=question)
            user_text = f"Pertanyaan User: {question}\n\nJawaban Akhir:"
        else:
            system_text = FINAL_ANSWER_PROMPT
            user_text = (
                f"Riwayat Percakapan:\n{history_text}\n\n"
                f"Konteks Fakta / Hasil DB:\n{context}\n\n"
                f"Pertanyaan User: {question}\n\n"
                "Jawaban Akhir:"
            )

        try:
            answer = llm.generate(
                user_text, 
                system=system_text, 
                options={"temperature": 0.0, "num_predict": 500, "repeat_penalty": 1.2}
            ).strip()
            
            # Bersihkan JSON block secara menyeluruh dengan memotong string sebelum '{'
            if "{" in answer:
                answer = answer.split("{")[0].strip()
            
            return answer
        except Exception as e:
            logger.error(f"Error generating final answer: {e}")
            return "Maaf, terjadi kesalahan saat merangkum jawaban. Data mentah: " + context

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
            response = llm.generate(prompt, options={"temperature": 0.0, "num_predict": 120}).strip()
            response = response.replace("```json", "").replace("```", "").strip()

            if not response:
                return {"tool": "ask_question", "arguments": {"question": question}}

            data = json.loads(response)
            tool = data.get("tool")
            arguments = data.get("arguments", {})

            if not tool:
                return {"tool": "ask_question", "arguments": {"question": question}}

            if arguments is None:
                arguments = {}

            if "operator" in arguments:
                arguments["operator"] = self.validate_operator(arguments["operator"])

            return {"tool": tool, "arguments": arguments}

        except json.JSONDecodeError:
            return {"tool": "ask_question", "arguments": {"question": question}}
        except Exception:
            return {"tool": "ask_question", "arguments": {"question": question}}

    async def run_chat_turn(
        self,
        mcp_client: Any,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        memory_context: Optional[Dict[str, Any]] = None,
        role: str = "patient",
        patient_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        model_name = self._active_model_name()
        history_text = self._build_history_text(conversation_history or []) or "(kosong)"
        memory_context_text = self._build_memory_context_text(memory_context)

        if role == "patient":
            # --- GUARDRAIL PRE-FLIGHT UNTUK PASIEN ---
            ql = question.lower()
            if any(k in ql for k in ["stok", "harga", "sisa", "habis", "kritis", "laporan", "inventory"]):
                return {
                    "answer": "Maaf, sebagai asisten pasien, saya hanya bisa memberikan edukasi medis dan info resep Anda. Untuk mengecek ketersediaan stok atau harga, silakan tanyakan langsung ke apoteker di kasir.",
                    "tool_used": "BLOCKED_FOR_PATIENT",
                    "status": "success",
                    "model_name": model_name,
                }
            # -----------------------------------------
            patient_medical_block = ""
            if patient_context:
                nama = patient_context.get("nama", "-")
                diagnosa = patient_context.get("diagnosa", "-")
                tanggal = patient_context.get("tanggal_kunjungan", "-")
                obat_list = patient_context.get("obat", [])

                obat_lines = ""
                for o in obat_list:
                    nama_obat = o.get("nama", "?")
                    dosis = o.get("dosis", "?")
                    waktu = o.get("waktu", "?")
                    obat_lines += f"  - {nama_obat} ({dosis}): {waktu}\n"

                obat_text = obat_lines if obat_lines else "  (tidak ada resep aktif)\n"
                patient_medical_block = (
                    "=== DATA MEDIS PASIEN (FAKTA, JANGAN DIUBAH) ===\n"
                    f"Nama: {nama}\n"
                    f"Diagnosa: {diagnosa}\n"
                    f"Tanggal Kunjungan: {tanggal}\n"
                    f"Obat yang sedang dikonsumsi:\n{obat_text}"
                    "================================================\n"
                )

            system_text = PATIENT_CHATBOT_PROMPT.format(
                patient_medical_block=patient_medical_block,
                history_text="",
                question=""
            )
            user_text = f"Riwayat Percakapan:\n{history_text}\n\nPertanyaan Pasien: {question}\n\nJawaban:"
        else:
            system_text = PHARMACIST_CHATBOT_PROMPT.split("Riwayat Percakapan:")[0].format(tools_instruction="")
            user_text = f"Riwayat Percakapan:\n{history_text}\n\nPertanyaan: {question}\n\nJawaban:"

        try:
            logger.info(f"Generating chat with model {model_name}...")
            generate_kwargs = {
                "options": {"temperature": 0.0, "num_predict": 400, "repeat_penalty": 1.2},
                "system": system_text,
            }
            if role != "patient":
                generate_kwargs["response_format"] = "json"
                
            raw = llm.generate(user_text, **generate_kwargs)
        except Exception as e:
            logger.error(f"[CHAT] LLM Generation failed: {e}")
            return {
                "answer": "Maaf, sistem sedang sibuk atau mengalami gangguan. Silakan coba lagi.",
                "tool_used": None,
                "status": "error",
                "model_name": model_name,
            }

        clean = raw.replace("```json", "").replace("```", "").strip()
        tool_decision = None
        answer_text = None

        candidate_starts = [idx for idx, ch in enumerate(clean) if ch == "{"]
        for start in candidate_starts:
            depth = 0
            for idx in range(start, len(clean)):
                ch = clean[idx]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        snippet = clean[start : idx + 1]
                        try:
                            parsed = json.loads(snippet)
                            if isinstance(parsed, dict):
                                tool_name = parsed.get("tool")
                                if isinstance(tool_name, str) and tool_name.strip():
                                    tool_decision = parsed
                                else:
                                    answer_text = parsed.get("answer") or parsed.get("jawaban") or parsed.get("response") or parsed.get("respon") or parsed.get("message")
                                break
                        except json.JSONDecodeError:
                            pass
            if tool_decision or answer_text:
                break

        if tool_decision is None:
            final_answer = answer_text or clean
            if role == "patient" and not answer_text:
                # Fallback if patient model fails to follow JSON format
                pass
            return {
                "answer": final_answer,
                "tool_used": None,
                "status": "success",
                "model_name": model_name,
                "context_updates": {"last_tool": "direct_llm"},
            }

        tool = tool_decision.get("tool")
        arguments = tool_decision.get("arguments", {}) or {}

        # --- GUARDRAIL KOMPREHENSIF UNTUK MODEL 1B ---
        ql = question.lower()
        
        # 1. Jika murni pertanyaan medis umum (tanpa konteks data RS)
        general_keywords = ["dosis", "kegunaan", "manfaat", "perbedaan", "efek samping", "aturan pakai", "aman", "indikasi", "fungsi", "apa itu", "bagaimana cara"]
        needs_data = ["stok", "harga", "mrn", "laporan", "pasien", "sisa", "kritis", "habis", "resep"]
        if any(k in ql for k in general_keywords) and not any(k in ql for k in needs_data):
            tool = ""
            arguments = {}
            
        # 2. Jika tanya stok mau habis / kritis
        elif "habis" in ql or "kritis" in ql or "menipis" in ql:
            tool = "detect_low_stock"
            arguments = {}
            
        # 3. Jika tanya pasien tapi ga sebut MRN (mencegah get_patient_data palsu)
        elif tool == "get_patient_data" and "mrn" not in ql:
            tool = ""
            arguments = {}
            
        # 4. Jika tanya stok spesifik (mengoreksi get_inventory_analytics)
        elif "stok" in ql and "laporan" not in ql and "ringkasan" not in ql and tool != "detect_low_stock":
            tool = "search_obat_by_stock"
            words = ql.replace("?", "").split()
            if "obat" in words:
                idx = words.index("obat")
                if idx + 1 < len(words):
                    arguments = {"nama_obat": words[idx+1]}
                    
        # 5. Jika tanya harga
        elif "harga" in ql:
            tool = "search_obat_by_harga"
            words = ql.replace("?", "").split()
            if "harga" in words:
                idx = words.index("harga")
                if idx + 1 < len(words):
                    arguments = {"nama_obat": words[idx+1]}
        # ----------------------------------------------

        if role == "patient":
            fallback_msg = (
                "Maaf, sebagai asisten pasien, saya tidak memiliki akses ke sistem inventory atau rekam medis eksternal. "
                "Silakan tanyakan langsung ke apoteker di kasir untuk informasi stok, harga, atau data medis lengkap."
            )
            return {
                "answer": fallback_msg,
                "tool_used": "BLOCKED_FOR_PATIENT",
                "status": "success",
                "model_name": model_name,
                "context_updates": {"last_tool": "direct_llm"},
            }

        arguments = self._apply_cached_arguments(tool, arguments, memory_context, question=question)

        if "operator" in arguments:
            arguments["operator"] = self.validate_operator(arguments["operator"])

        try:
            if tool == "get_inventory_analytics":
                from back.core.agents.analytics_agent import AnalyticsAgent
                analytics_result = await AnalyticsAgent().run_monitoring_analytics(mcp_client)
                result = {"status": "success", "context": analytics_result.get("ai_insight", "Laporan tidak tersedia")}
            else:
                result = await mcp_client.call_tool(tool, arguments)
        except Exception as e:
            logger.warning(f"[CHAT] Tool '{tool}' failed: {e}")
            fallback = self._answer_general_with_llm(question, conversation_history=conversation_history)
            return {
                "answer": fallback,
                "tool_used": tool,
                "status": "success",
                "model_name": model_name,
                "context_updates": {"last_tool": "direct_llm"},
            }

        parsed_result = self._parse_tool_payload(result)
        
        if role == "patient" and parsed_result.get("status") == "error":
            answer = "Maaf, saya tidak dapat menemukan data medis Anda saat ini. Silakan hubungi apoteker di kasir."
        else:
            custom_prompt = None
            if role == "patient":
                if tool == "ask_question":
                    custom_prompt = (
                        "Anda adalah Asisten Farmasi AI yang bertugas mengedukasi PASIEN.\n\n"
                        "Informasi Medis Referensi (RAG):\n{context}\n\n"
                        "Riwayat Percakapan:\n{history_text}\n\n"
                        "Pertanyaan Pasien: {question}\n\n"
                        "TUGAS:\n"
                        "1. Jawab pertanyaan pasien dengan bahasa awam yang ramah dan mudah dimengerti (maksimal 4 kalimat).\n"
                        "2. JAWAB BERDASARKAN Informasi Medis Referensi di atas.\n"
                        "Jawaban Anda:"
                    )
                else:
                    custom_prompt = (
                        "Anda adalah Asisten Farmasi AI yang bertugas menjawab pertanyaan PASIEN.\n\n"
                        "Data Medis Pasien dari Sistem:\n{context}\n\n"
                        "Riwayat Percakapan:\n{history_text}\n\n"
                        "Pertanyaan Pasien: {question}\n\n"
                        "TUGAS:\n"
                        "1. Jawab pertanyaan pasien dengan bahasa awam yang ramah (maksimal 4 kalimat).\n"
                        "2. JAWAB HANYA BERDASARKAN DATA MEDIS DI ATAS. Jika pasien tanya 'obat saya apa', sebutkan obat di data.\n"
                        "Jawaban Anda:"
                    )

            try:
                answer = self.final_answer(
                    question,
                    result,
                    tool_name=tool,
                    conversation_history=conversation_history,
                    custom_prompt=custom_prompt
                )
            except Exception:
                answer = parsed_result.get("answer") or parsed_result.get("context") or "Maaf, terjadi kesalahan."

        context_updates = self._extract_context_updates(tool, arguments, parsed_result)

        return {
            "answer": answer,
            "tool_used": tool,
            "status": "success",
            "model_name": model_name,
            "context_updates": context_updates,
        }
