import json
import logging
from typing import Dict, Any, List, Optional
from back.core.llm import get_llm
from back.core.agents.base_agent import BaseAgent
from back.core.prompts import VALIDATION_PROMPT, DISPENSING_PROMPT, DISPENSING_RETRY_PROMPT

logger = logging.getLogger(__name__)
llm = get_llm()

class ValidationAgent(BaseAgent):
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

        prompt = VALIDATION_PROMPT.format(llm_payload=json.dumps(llm_payload, ensure_ascii=False, indent=2))

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

        if not isinstance(llm_result, dict):
            llm_result = {}

        medgemma_output: Dict[str, Any] = llm_result
        medgemma_raw_response = llm_raw

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
            if normalized in {"WASPADA", "WARNING", "CAUTION", "MEDIUM"}:
                return "WASPADA"
            if normalized in {"BAHAYA", "TIDAK AMAN", "TIDAK SESUAI", "DANGER", "HIGH"}:
                return "BAHAYA"
            if normalized in {"PERLU REVIEW", "REVIEW", "NEED REVIEW"}:
                return "PERLU REVIEW"
            return "PERLU REVIEW"

        def _normalize_item_status(status: Any, cek_klinik: Dict[str, Dict[str, str]]) -> str:
            normalized = str(status or "").strip().upper()
            if normalized in {"AMAN", "SESUAI", "SAFE", "OK"}:
                return "AMAN"
            if normalized in {"WASPADA", "WARNING", "CAUTION"}:
                return "WASPADA"
            if normalized in {"BAHAYA", "TIDAK AMAN", "TIDAK SESUAI", "DANGER"}:
                return "BAHAYA"
            if normalized in {"PERLU REVIEW FARMASIS", "PERLU REVIEW", "REVIEW"}:
                return "PERLU REVIEW FARMASIS"
            # Fallback: cek apakah ada risiko dari cek_klinik
            has_danger = any(v.get("status") in {"BAHAYA", "TIDAK AMAN"} for v in cek_klinik.values())
            has_warning = any(v.get("status") in {"WASPADA", "PERLU REVIEW"} for v in cek_klinik.values())
            if has_danger:
                return "BAHAYA"
            if has_warning:
                return "WASPADA"
            return "AMAN"

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

        def _extract_check(raw_checks: Dict[str, Any], aliases: List[str]) -> Dict[str, str]:
            for alias in aliases:
                value = raw_checks.get(alias)
                if isinstance(value, dict):
                    status = str(value.get("status") or "").strip()
                    note = str(value.get("catatan") or value.get("detail") or value.get("reason") or "").strip()
                    return {"status": status, "catatan": note}
                if isinstance(value, str):
                    return {
                        "status": value.strip(),
                        "catatan": "",
                    }
            return {"status": "", "catatan": ""}

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
                    ),
                    "screening_interaksi_obat": _extract_check(
                        raw_checks,
                        ["screening_interaksi_obat", "interaksi_obat", "drug_interaction"],
                    ),
                    "cek_kontraindikasi": _extract_check(
                        raw_checks,
                        ["cek_kontraindikasi", "kontraindikasi", "contraindication"],
                    ),
                    "cek_alergi": _extract_check(
                        raw_checks,
                        ["cek_alergi", "alergi", "allergy"],
                    ),
                }

                status_item = str(item.get("status") or "").strip()
                alasan_raw = item.get("alasan")
                if isinstance(alasan_raw, list):
                    alasan = [str(x).strip() for x in alasan_raw if str(x).strip()]
                elif isinstance(alasan_raw, str) and alasan_raw.strip():
                    alasan = [alasan_raw.strip()]
                else:
                    alasan = []

                rekomendasi_item = str(item.get("rekomendasi") or "").strip()

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
                        "catatan_klinis": " ; ".join(alasan) if alasan else "",
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
            dosis_status = str(output_ringkas.get("dosis") or dosis_data.get("status") or "").strip()
            catatan_singkat = str(output_ringkas.get("catatan") or dosis_data.get("catatan") or "").strip()

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
        validasi_inventory = validasi_result.get("inventory")
        validasi_administrasi = validasi_result.get("administrasi")

        verdict = str(llm_result.get("verdict", "")).strip()
        next_step = str(llm_result.get("next_step", "")).strip()
        risk_level = str(llm_result.get("risk_level", "")).strip()

        kesimpulan_data = llm_result.get("kesimpulan") if isinstance(llm_result.get("kesimpulan"), dict) else {}
        jumlah_masalah_raw = kesimpulan_data.get("jumlah_masalah")
        try:
            jumlah_masalah = int(jumlah_masalah_raw) if jumlah_masalah_raw is not None else None
        except Exception:
            jumlah_masalah = None

        saran_kesimpulan = str(kesimpulan_data.get("saran") or "").strip()
        alasan_utama = llm_result.get("alasan_utama") if isinstance(llm_result.get("alasan_utama"), list) else []
        alasan_utama = [str(x).strip() for x in alasan_utama if str(x).strip()]

        ringkasan_klinis = str(llm_result.get("ringkasan_klinis", "")).strip()

        analysis = str(llm_result.get("analysis", "")).strip()
        recommendation = str(llm_result.get("recommendation", "")).strip()

        confidence_raw = llm_result.get("confidence")
        try:
            confidence = float(confidence_raw)
        except Exception:
            confidence = None

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
            status_item = str(item.get("status") or "").strip()
            status_label = status_item or "-"
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
                check_status = str(check_data.get("status") or "").strip() or "-"
                check_note = str(check_data.get("catatan") or "").strip() or "-"
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
        confidence_text = f"{confidence:.2f}" if isinstance(confidence, float) else "-"
        ai_response = (
            f"Engine: MedGemma ({model_name})\n"
            f"Risk Level: {risk_level}\n"
            f"Verdict: {verdict}\n"
            f"Confidence: {confidence_text}\n"
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
                    f"risk_level={risk_level}, verdict={verdict}, confidence={confidence_text}"
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
            "obat_list": obat_list,
            "prescription_context": prescription_context,
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
            "medgemma_output": medgemma_output,
            "medgemma_raw_response": medgemma_raw_response,
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
                "stok_obat_ada": validasi_inventory,
                "administrasi_valid": validasi_administrasi,
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

