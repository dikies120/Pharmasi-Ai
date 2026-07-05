import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from back.core.llm import get_llm
from back.core.agents.base_agent import BaseAgent
from back.core.prompts import VALIDATION_PROMPT, DISPENSING_PROMPT, DISPENSING_RETRY_PROMPT

logger = logging.getLogger(__name__)
llm = get_llm()

class DispensingAgent(BaseAgent):
    async def run_dispensing_preview(
        self,
        mcp_client: Any,
        prescription_id: str,
        include_llm_reasoning: bool = True,
    ) -> Dict[str, Any]:
        import asyncio as _asyncio

        # PARALLEL: get_dispensing_preview + validate_prescription sekaligus
        preview_task = self._call_tool_json(
            mcp_client, "get_dispensing_preview", {"prescription_id": prescription_id}
        )
        validation_task = self._call_tool_json(
            mcp_client, "validate_prescription", {"prescription_id": str(prescription_id)}
        )
        preview, validation = await _asyncio.gather(preview_task, validation_task, return_exceptions=True)

        if isinstance(preview, Exception) or not preview:
            return {"status": "error", "message": "Gagal mengambil data dispensing."}
        if isinstance(preview, dict) and preview.get("status") == "error":
            return preview
        if isinstance(validation, Exception):
            validation = {}

        validation_message = validation.get("context") or validation.get("message") or "Validasi resep berhasil."

        # Ambil data pasien — prioritaskan dari _patient_data yang sudah ada di preview
        patient_snapshot = {}
        inline_patient = preview.get("_patient_data")
        if isinstance(inline_patient, dict) and inline_patient.get("mrn"):
            patient_snapshot = {
                "usia_tahun": inline_patient.get("usia_tahun"),
                "alergi": inline_patient.get("alergi"),
                "bpjs_status": inline_patient.get("bpjs_status"),
                "faskes_level": inline_patient.get("faskes_level"),
                "diagnosis": inline_patient.get("diagnosis"),
                "diagnosis_notes": inline_patient.get("diagnosis_notes"),
            }
        else:
            # Fallback: lookup via MCP menggunakan MRN
            patient_mrn = preview.get("patient_mrn") or preview.get("mrn") or ""
            if patient_mrn:
                try:
                    patient_data = await self._call_tool_json(
                        mcp_client, "get_patient_data", {"patient_id": patient_mrn},
                    )
                    if patient_data and patient_data.get("status") != "error":
                        patient_snapshot = {
                            "usia_tahun": patient_data.get("usia_tahun"),
                            "alergi": patient_data.get("alergi"),
                            "bpjs_status": patient_data.get("bpjs_status"),
                            "faskes_level": patient_data.get("faskes_level"),
                            "diagnosis": patient_data.get("active_diagnosis", [None])[0] if isinstance(patient_data.get("active_diagnosis"), list) else patient_data.get("diagnosis"),
                        }
                except Exception as e:
                    logger.warning(f"[DISPENSING] Gagal ambil data pasien: {e}")
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

                prompt = DISPENSING_PROMPT.format(reasoning_payload=json.dumps(reasoning_payload, ensure_ascii=False))

                retry_prompt = DISPENSING_RETRY_PROMPT.format(reasoning_payload=json.dumps(reasoning_payload, ensure_ascii=False))

                llm_raw = ""
                for attempt in range(2):
                    attempt_prompt = prompt if attempt == 0 else retry_prompt
                    attempt_num_predict = 1000 if attempt == 0 else 1600
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
            "patient_snapshot": patient_snapshot,
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
