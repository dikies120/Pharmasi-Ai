"use client";

import { useMemo, useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  CheckCircle, AlertTriangle, Shield, Activity, Pill, FileText, ArrowLeft, Loader2, Search, ChevronRight, Clock, Link as LinkIcon, User
} from "lucide-react";
import { routes } from "@/lib/constants/routes";
import { getAuthHeader } from "@/lib/api/client";
import { cn } from "@/lib/utils/cn";

type JsonObject = Record<string, unknown>;
type View = "form" | "preview" | "loading" | "result";

function isObject(v: unknown): v is JsonObject { return typeof v === "object" && v !== null && !Array.isArray(v); }
function toArray(v: unknown): unknown[] { return Array.isArray(v) ? v : []; }
function readText(v: unknown, fb = "-"): string {
  if (typeof v === "string") return v.trim() || fb;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return fb;
}
function pickText(r: JsonObject | null, keys: string[], fb = "-"): string {
  if (!r) return fb;
  for (const k of keys) { if (k in r) { const val = readText(r[k], ""); if (val) return val; } }
  return fb;
}
function toTextList(v: unknown): string[] {
  if (Array.isArray(v)) return v.map((i) => readText(i, "")).filter(Boolean);
  if (typeof v === "string") return v.split("\n").map((i) => i.trim()).filter(Boolean);
  return [];
}

function parseRawResponse(raw: unknown): JsonObject | null {
  if (!raw || typeof raw !== "string") return null;
  try {
    const candidates: JsonObject[] = [];
    let i = 0;
    while (i < raw.length) {
      const start = raw.indexOf("{", i);
      if (start < 0) break;
      let depth = 0;
      let end = -1;
      for (let j = start; j < raw.length; j++) {
        if (raw[j] === "{") depth++;
        else if (raw[j] === "}") {
          depth--;
          if (depth === 0) { end = j; break; }
        }
      }
      if (end < 0) break;
      try {
        const p = JSON.parse(raw.slice(start, end + 1));
        if (isObject(p)) candidates.push(p);
      } catch {}
      i = end + 1;
    }

    if (candidates.length === 0) return null;

    // Pilih kandidat yang paling lengkap (punya hasil_per_obat dengan cek_klinik)
    const withHasil = candidates.filter((c) => {
      const h = c.hasil_per_obat;
      if (!Array.isArray(h) || h.length === 0) return false;
      // Pastikan ada cek_klinik dengan 4 keys
      const first = h[0];
      return isObject(first) && isObject((first as JsonObject).cek_klinik);
    });
    if (withHasil.length > 0) {
      // Ambil yang punya cek_klinik paling lengkap
      return withHasil.reduce((best, c) => {
        const bestKeys = Object.keys((best.hasil_per_obat as any[])?.[0]?.cek_klinik ?? {}).length;
        const cKeys = Object.keys((c.hasil_per_obat as any[])?.[0]?.cek_klinik ?? {}).length;
        return cKeys > bestKeys ? c : best;
      });
    }

    // Fallback: kandidat dengan hasil_per_obat
    const withVerdict = candidates.find((c) => c.hasil_per_obat || c.verdict || c.ringkasan_klinis);
    if (withVerdict) return withVerdict;

    // Last resort: merge semua
    return candidates.reduce((acc, c) => ({ ...acc, ...c }), {} as JsonObject);
  } catch {}
  return null;
}

//  Risk Badge 
function RiskBadge({ level }: { level: string }) {
  const l = (level || "LOW").toUpperCase();
  const cls = l === "HIGH" ? "bg-red-100 text-red-700 border-red-300"
    : l === "MEDIUM" ? "bg-amber-100 text-amber-700 border-amber-300"
    : "bg-emerald-100 text-emerald-700 border-emerald-300";
  return <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-semibold", cls)}>Risiko: {l}</span>;
}

//  Status Badge 
function StatusBadge({ label }: { label: string }) {
  const l = (label || "").toLowerCase();
  // Klasifikasi status berdasarkan output LLM
  const isDanger = l.includes("bahaya") || l.includes("tidak aman") || l.includes("tidak sesuai");
  const isWarning = l.includes("waspada") || l.includes("perlu review") || l.includes("review");
  const isSafe = l.includes("aman") || l.includes("sesuai") || l.includes("normal") || l.includes("ok");
  // Prioritas: danger > warning > safe > fallback warning
  const level = isDanger ? "danger" : isWarning ? "warning" : isSafe ? "safe" : "warning";
  const config = {
    danger: { cls: "bg-red-100 text-red-700 border-red-300", Icon: AlertTriangle },
    warning: { cls: "bg-amber-100 text-amber-700 border-amber-300", Icon: Clock },
    safe: { cls: "bg-emerald-100 text-emerald-700 border-emerald-300", Icon: CheckCircle },
  };
  const { cls, Icon } = config[level];
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-semibold", cls)}>
      <Icon className="h-3.5 w-3.5" />
      {label}
    </span>
  );
}

//  Loading 
function LoadingScreen({ patientId }: { patientId: string }) {
  const steps = [
    { label: "Mengambil data pasien & riwayat medis" },
    { label: "Memeriksa stok dan ketersediaan obat" },
    { label: "Analisis klinis AI (dosis, interaksi, alergi)" },
  ];
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center">
      <div className="w-full max-w-sm mx-auto flex flex-col items-center gap-8">
        {/* Spinner */}
        <div className="relative flex items-center justify-center">
          <div className="h-24 w-24 rounded-full border-4 border-violet-100" />
          <div className="absolute inset-0 animate-spin rounded-full border-4 border-transparent border-t-violet-500" />
          <div className="absolute inset-0 animate-spin rounded-full border-4 border-transparent border-r-violet-300" style={{ animationDuration: "1.5s" }} />
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-violet-50">
              <Shield className="h-6 w-6 text-violet-600" />
            </div>
          </div>
        </div>

        {/* Title */}
        <div className="text-center space-y-1">
          <h3 className="text-2xl font-black text-slate-900">Memvalidasi Resep</h3>
          <p className="text-sm text-slate-500">
            MRN: <span className="font-bold text-violet-600">{patientId}</span>
          </p>
        </div>

        {/* Steps */}
        <div className="w-full space-y-2.5">
          {steps.map((step, i) => (
            <div key={i} className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3.5 shadow-sm">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-violet-50">
                <Loader2 className="h-4 w-4 animate-spin text-violet-500" style={{ animationDelay: `${i * 250}ms` }} />
              </div>
              <span className="text-sm font-medium text-slate-700">{step.label}</span>
            </div>
          ))}
        </div>

        {/* Note */}
        <p className="text-xs text-slate-400 text-center">AI sedang menganalisis data klinis, harap tunggu...</p>
      </div>
    </div>
  );
}

//  Result 
function ResultView({ result, onBack }: { result: JsonObject; onBack: () => void }) {
  const medgemma = useMemo(() => {
    if (!result) return null;
    // Prioritas 1: medgemma_output yang sudah di-parse oleh backend
    const mo = result.medgemma_output;
    if (isObject(mo) && (mo.hasil_per_obat || mo.verdict || mo.ringkasan_klinis || mo.analysis)) return mo;
    // Prioritas 2: parse dari raw response
    const parsed = parseRawResponse(result.medgemma_raw_response);
    if (parsed && (parsed.hasil_per_obat || parsed.verdict || parsed.ringkasan_klinis)) return parsed;
    // Fallback: pakai medgemma_output apapun isinya
    if (isObject(mo) && Object.keys(mo).length > 0) return mo;
    return null;
  }, [result]);

  const hasilPerObat = useMemo(() => toArray(medgemma?.hasil_per_obat).filter(isObject), [medgemma]);
  const prescriptionContext = useMemo(() => toArray(result.prescription_context).filter(isObject), [result]);

  const patientName = pickText(result, ["patient_name"], "-");
  const patientMrn = pickText(result, ["patient_mrn"], "-");
  const diagnosis = pickText(result, ["diagnosis"], "-");
  const snapshot = isObject(result.patient_snapshot) ? result.patient_snapshot as JsonObject : null;
  const alergi = pickText(snapshot, ["alergi"], "-");
  const usia = snapshot?.usia_tahun ? `${snapshot.usia_tahun} Tahun` : "-";
  const bpjs = pickText(snapshot, ["bpjs_status"], "-");
  const faskes = pickText(snapshot, ["faskes_level"], "-");
  const riskLevel = pickText(medgemma, ["risk_level"], "LOW");
  const verdict = pickText(medgemma, ["verdict"], "-");
  const ringkasan = pickText(medgemma, ["ringkasan_klinis", "analysis", "ringkasan", "recommendation"], "");
  const nextStep = pickText(medgemma, ["next_step"], "-");
  const alasanUtama = toArray(medgemma?.alasan_utama).map((a) => readText(a, "")).filter(Boolean);
  const kesimpulan = isObject(medgemma?.kesimpulan)
    ? pickText(medgemma.kesimpulan as JsonObject, ["saran", "text"], "")
    : readText(medgemma?.kesimpulan, "");
  const activePrescriptionId = readText(result.active_prescription_id, "");

  // Bisa lanjut dispensing hanya jika: ada prescription ID dan next_step = DISPENSING
  const canDispense = Boolean(activePrescriptionId) && nextStep === "DISPENSING";
  const dispensingHref = canDispense ? `${routes.pharmacyDispensing}?prescriptionId=${encodeURIComponent(activePrescriptionId)}` : "";
  const bpjsActive = bpjs.toLowerCase() === "aktif";

  const cekLabels: Record<string, string> = {
    validasi_dosis: "Validasi Dosis",
    screening_interaksi_obat: "Skrining Interaksi",
    cek_kontraindikasi: "Kontraindikasi",
    cek_alergi: "Cek Alergi",
  };

  return (
    <div className="space-y-5">
      <button onClick={onBack} className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-800 transition-colors">
        <ArrowLeft className="h-4 w-4" /> Validasi Pasien Lain
      </button>

      {/*  Patient Card  */}
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        {/* Top row */}
        <div className="flex flex-wrap items-center gap-4 px-6 py-5 border-b border-slate-100">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-violet-100">
            <User className="h-6 w-6 text-violet-600" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-xl font-bold text-slate-900">{patientName}</h2>
            <p className="text-sm text-slate-500">No. Rekam Medis: {patientMrn}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <RiskBadge level={riskLevel} />
            <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-semibold",
              bpjsActive ? "bg-blue-100 text-blue-700 border-blue-300" : "bg-slate-100 text-slate-600 border-slate-200"
            )}>
              BPJS: {bpjs}
            </span>
          </div>
        </div>
        {/* Info row */}
        <div className="grid grid-cols-3 divide-x divide-slate-100 bg-slate-50/50">
          <div className="px-6 py-4">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-1">Usia</p>
            <p className="text-base font-semibold text-slate-800">{usia}</p>
          </div>
          <div className="px-6 py-4">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-1">Alergi</p>
            <p className={cn("text-base font-semibold", alergi !== "-" ? "text-red-600" : "text-slate-800")}>{alergi}</p>
          </div>
          <div className="px-6 py-4">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-1">Diagnosis Utama</p>
            <p className="text-base font-semibold text-slate-800">{diagnosis}</p>
          </div>
        </div>
      </div>

      {/*  Main Grid  */}
      <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
        {/* Left */}
        <div className="space-y-5">
          {/* Ringkasan AI */}
          {ringkasan && (
            <div className="rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50 to-orange-50 p-5">
              <div className="flex items-center gap-2 mb-3">
                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-amber-400">
                  <Activity className="h-4 w-4 text-white" />
                </div>
                <p className="text-sm font-bold uppercase tracking-widest text-amber-800">Ringkasan Analisis AI</p>
              </div>
              <p className="text-base text-amber-900 leading-relaxed">{ringkasan}</p>
            </div>
          )}

          {/* Tabel Stok */}
          {prescriptionContext.length > 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
              <div className="flex items-center gap-2 border-b border-slate-100 px-5 py-4">
                <Pill className="h-4 w-4 text-slate-500" />
                <p className="text-sm font-bold uppercase tracking-widest text-slate-600">Ketersediaan Obat</p>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50">
                      {["Nama Obat", "Qty", "Stok", "Aturan Minum", "Status"].map((h) => (
                        <th key={h} className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-widest text-slate-500">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {prescriptionContext.map((item, i) => {
                      const cukup = readText(item.stok_ada, "-") === "IYA";
                      return (
                        <tr key={i} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                          <td className="px-5 py-3.5 text-base font-semibold text-slate-800">{readText(item.obat, "-")}</td>
                          <td className="px-5 py-3.5 text-base text-slate-700">{readText(item.resep_qty, "-")}</td>
                          <td className="px-5 py-3.5 text-base font-mono font-bold text-slate-700">{readText(item.stok_tersedia, "-")}</td>
                          <td className="px-5 py-3.5 text-base text-slate-600">{readText(item.aturan_minum, "-")}</td>
                          <td className="px-5 py-3.5">
                            <span className={cn("inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-sm font-semibold",
                              cukup ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-red-50 text-red-700 border-red-200"
                            )}>
                              {cukup ? <CheckCircle className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3" />}
                              {cukup ? "CUKUP" : "KURANG"}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Hasil Per Obat */}
          {hasilPerObat.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-slate-500" />
                <p className="text-sm font-bold uppercase tracking-widest text-slate-600">Hasil Validasi Per Obat</p>
              </div>
              {hasilPerObat.map((item, index) => {
                const namaObat = pickText(item, ["obat", "nama_obat", "name"], `Obat ${index + 1}`);
                const rawStatus = pickText(item, ["status"], "-");
                const alasanList = toTextList(item.alasan);
                const alasan = alasanList.join("; ");
                const status = rawStatus;
                const rekomendasiList = toTextList(item.rekomendasi);
                const rekomendasi = rekomendasiList.join("; ") || readText(item.rekomendasi, "");
                const cekKlinik = isObject(item.cek_klinik) ? item.cek_klinik as JsonObject : null;

                const defaultKeys = ["validasi_dosis", "screening_interaksi_obat", "cek_kontraindikasi", "cek_alergi"];
                const allEntries = defaultKeys.map((k) => {
                  const val = cekKlinik?.[k] ?? null;
                  return [k, val] as [string, unknown];
                });

                return (
                  <div key={index} className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
                    {/* Header obat */}
                    <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 border-b border-slate-100 bg-slate-50/50">
                      <h5 className="text-base font-bold text-slate-900">{namaObat}</h5>
                      <StatusBadge label={status} />
                    </div>

                    {/* Alasan + Rekomendasi */}
                    <div className="grid sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-slate-100 border-b border-slate-100">
                      {alasan && (
                        <div className="p-5">
                          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-2">Alasan Analisis</p>
                          <p className="text-base text-slate-700 leading-relaxed">{alasan}</p>
                        </div>
                      )}
                      {rekomendasi && (
                        <div className="p-5">
                          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-2">Rekomendasi</p>
                          <p className="text-base text-slate-700 leading-relaxed">{rekomendasi}</p>
                        </div>
                      )}
                    </div>

                    {/* 4 Cek Klinik  2x2 grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-4">
                      {allEntries.map(([key, val]) => {
                        const cd = isObject(val) ? val as JsonObject : null;
                        const rawS = cd ? pickText(cd, ["status"], "-") : readText(val, "-");
                        const note = cd ? pickText(cd, ["catatan", "note"], "") : "";
                        const cs = rawS === "-" ? "-" : rawS;
                        const label = cekLabels[key] || key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
                        return (
                          <div key={key} className="border-r border-t border-slate-100 p-4 last:border-r-0">
                            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-2">{label}</p>
                            <StatusBadge label={cs} />
                            {note && <p className="mt-2 text-sm text-slate-600 leading-relaxed">{note}</p>}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Sidebar */}
        <div className="space-y-4">
          {/* Status Card */}
          {(() => {
            const vl = verdict.toLowerCase();
            const isAman = vl.includes("aman") && !vl.includes("tidak");
            const isWaspada = vl.includes("waspada");
            const isBahaya = vl.includes("bahaya") || vl.includes("tidak aman");
            const cardGradient = isBahaya ? "bg-gradient-to-br from-red-600 to-rose-700"
              : isWaspada ? "bg-gradient-to-br from-amber-500 to-orange-600"
              : canDispense || isAman ? "bg-gradient-to-br from-emerald-600 to-teal-700"
              : "bg-gradient-to-br from-slate-600 to-slate-700";
            const cardTitle = isBahaya ? "Obat Berbahaya!"
              : isWaspada ? "Perlu Perhatian Khusus"
              : canDispense ? "Siap untuk Dispensing"
              : "Menunggu Review";
            const cardDesc = isBahaya ? "Ada risiko serius. Konsultasikan dengan dokter sebelum memberikan obat."
              : isWaspada ? "Obat dapat digunakan dengan pengawasan. Periksa catatan klinis."
              : canDispense ? "Validasi selesai. Lanjutkan ke proses penyiapan obat."
              : "Tinjau hasil validasi dan konsultasikan dengan dokter.";
            return (
              <div className={cn("rounded-2xl p-5 text-white", cardGradient)}>
                <p className="text-xs font-semibold uppercase tracking-widest opacity-70 mb-2">Status Alur Kerja</p>
                <h3 className="text-2xl font-black leading-tight mb-2">{cardTitle}</h3>
                <p className="text-sm opacity-80 leading-relaxed mb-4">{cardDesc}</p>
                <div className="rounded-xl bg-white/20 px-4 py-2 mb-4">
                  <p className="text-xs opacity-70 uppercase tracking-widest">Verdict AI</p>
                  <p className="text-lg font-bold">{verdict !== "-" ? verdict : (canDispense ? "AMAN" : "PERLU REVIEW FARMASIS")}</p>
                </div>
                {canDispense && (
                  <Link href={dispensingHref as never}
                    className="flex items-center justify-center gap-2 rounded-xl border-2 border-white/80 bg-white/10 px-4 py-3 text-base font-bold text-white hover:bg-white hover:text-indigo-700 active:bg-white active:text-indigo-700 focus-visible:bg-white focus-visible:text-indigo-700 transition-all">
                    Lanjut ke Dispensing <ChevronRight className="h-4 w-4" />
                  </Link>
                )}
              </div>
            );
          })()}

          {/* Temuan Keamanan */}
          {(() => {
            const isRisky = (item: JsonObject) => {
              const rawS = pickText(item, ["status"], "-").toLowerCase();
              return rawS.includes("bahaya") || rawS.includes("tidak aman") || rawS.includes("waspada") || rawS.includes("perlu review");
            };
            const riskyItems = hasilPerObat.filter(isRisky);
            return (
              <div className="rounded-2xl border border-red-200 bg-red-50 p-5">
                <div className="flex items-center gap-2 mb-3">
                  <AlertTriangle className="h-4 w-4 text-red-600" />
                  <p className="text-sm font-bold uppercase tracking-widest text-red-700">Temuan Keamanan</p>
                </div>
                {riskyItems.length === 0 ? (
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-emerald-600" />
                    <p className="text-base text-emerald-700 font-medium">Tidak ada temuan kritis</p>
                  </div>
                ) : (
                  riskyItems.map((item, i) => {
                    const namaObat = pickText(item, ["obat", "nama_obat", "name"], `Obat ${i + 1}`);
                    const rawS = pickText(item, ["status"], "-");
                    const alasanList = toTextList(item.alasan);
                    const alasan = alasanList.join("; ");
                    return (
                      <div key={i} className="rounded-xl border border-red-200 bg-white p-3 mb-2">
                        <p className="text-base font-semibold text-red-900">{namaObat}</p>
                        {alasan && <p className="mt-1 text-sm text-red-700 leading-relaxed">{alasan.slice(0, 120)}{alasan.length > 120 ? "..." : ""}</p>}
                        <div className="mt-2"><StatusBadge label={rawS} /></div>
                      </div>
                    );
                  })
                )}
              </div>
            );
          })()}

          {/* BPJS Info */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">Info Jaminan</p>
            <div className="space-y-2">
              <div className="flex justify-between text-base">
                <span className="text-slate-500">Status BPJS</span>
                <span className={cn("font-semibold", bpjsActive ? "text-emerald-600" : "text-slate-700")}>{bpjs}</span>
              </div>
              <div className="flex justify-between text-base">
                <span className="text-slate-500">Faskes Level</span>
                <span className="font-semibold text-slate-700">Level {faskes}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* DSS Disclaimer */}
      <div className="rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4 flex items-start gap-3">
        <AlertTriangle className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
        <p className="text-sm text-slate-500 leading-relaxed">
          <span className="font-semibold text-slate-600">Catatan DSS (Decision Support System): </span>
          Hasil validasi ini merupakan rekomendasi berbasis AI sebagai alat bantu pengambilan keputusan klinis.
          Keputusan akhir tetap berada pada apoteker dan tenaga medis yang berwenang.
          Selalu verifikasi dengan dokter penanggung jawab sebelum dispensing.
        </p>
      </div>
    </div>
  );
}

//  Main 
export function ValidasiObatPanel() {
  const [queue, setQueue] = useState<any[]>([]);
  const [loadingQueue, setLoadingQueue] = useState(true);
  const [activeQueueItem, setActiveQueueItem] = useState<any>(null);
  const [view, setView] = useState<View>("form");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<JsonObject | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const filteredQueue = useMemo(() => {
    const list = queue.filter((i) => i.status !== "DISPENSING");
    if (!searchQuery) return list;
    const q = searchQuery.toLowerCase();
    return list.filter(
      (i) => i.name.toLowerCase().includes(q) || i.id.toLowerCase().includes(q)
    );
  }, [queue, searchQuery]);

  useEffect(() => {
    async function fetchQueue() {
      try {
        setLoadingQueue(true);
        const res = await fetch(routes.api.pharmacy.queueValidation, {
          headers: getAuthHeader()
        });
        if (res.ok) {
          const data = await res.json();
          if (data && data.queue) {
            setQueue(data.queue);
          }
        }
      } catch (err) {
        console.error("Failed to fetch queue", err);
      } finally {
        setLoadingQueue(false);
      }
    }
    fetchQueue();
  }, []);

  function selectQueueItem(item: any) {
    if (item.status === 'DISPENSING') return;
    setActiveQueueItem(item);
    setView("preview");
    setError(null);
    setResult(null);
  }

  async function handleStartValidation() {
    if (!activeQueueItem) return;
    setView("loading"); setError(null); setResult(null);
    try {
      const fetchId = activeQueueItem.id;
      const res = await fetch(routes.api.pharmacy.validation, {
        method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify({ patient_id: fetchId }),
      });
      const body = (await res.json().catch(() => null)) as unknown;
      if (!res.ok) throw new Error(isObject(body) ? pickText(body, ["detail", "error", "message"], "") || "Gagal memproses validasi." : "Gagal memproses validasi.");
      if (!isObject(body)) throw new Error("Respons tidak valid.");
      setResult(body); setView("result");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Terjadi kesalahan."); setView("preview");
    }
  }

  return (
    <div className={cn("overflow-hidden", (view === "form" || view === "preview") ? "grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-6 h-[calc(100vh-140px)]" : "space-y-5")}>
      {(view === "form" || view === "preview") && (
        <>
          {/* KIRI: Daftar Antrean (Bisa di scroll) */}
          <div className="flex flex-col border-r border-slate-200 pr-6 h-full min-h-0">
            <div className="shrink-0 mb-5">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search or type command..."
                  className="w-full pl-9 pr-12 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-medium text-slate-400 bg-white border border-slate-200 px-1.5 py-0.5 rounded">Ctrl K</span>
              </div>
            </div>

            <div className="flex items-center gap-3 mb-4 shrink-0">
              <h3 className="font-bold text-slate-800 text-base">Antrean Validasi</h3>
              <span className="bg-amber-100 text-amber-700 text-xs px-2 py-0.5 rounded-full font-bold">{filteredQueue.length}</span>
            </div>

            {/* Scrollable list area */}
            <div className="flex-1 overflow-y-auto pb-6 pr-2 -mr-2 space-y-3 custom-scrollbar">
              {loadingQueue ? (
                <div className="text-center py-8 text-slate-500 text-sm">Memuat antrean...</div>
              ) : filteredQueue.length === 0 ? (
                <div className="text-center py-8 text-slate-500 text-sm">Tidak ada antrean validasi.</div>
              ) : filteredQueue.map((item) => {
                const isActive = activeQueueItem?.id === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => selectQueueItem(item)}
                    className={cn(
                      "w-full text-left p-4 rounded-xl border transition-all shadow-sm group relative overflow-hidden",
                      isActive
                        ? "border-blue-500 bg-blue-50/30 ring-1 ring-blue-500"
                        : "border-slate-200 bg-white hover:border-slate-300 hover:shadow-md"
                    )}
                  >
                    {isActive && <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-500" />}
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-semibold text-blue-600 text-xs">{item.id}</span>
                      <span className={cn("text-[10px] font-bold px-2 py-0.5 rounded-sm uppercase tracking-wider", item.status === 'VALIDASI' ? 'bg-amber-100 text-amber-700' : item.status === 'REVISI' ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700')}>{item.status}</span>
                    </div>
                    <div className="text-sm font-semibold text-slate-800 mb-3">
                      {item.name} <span className="font-normal text-slate-500">({item.age})</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-[11px] px-2.5 py-1 bg-slate-100 text-slate-500 rounded-md border border-slate-200 flex items-center gap-1.5">
                        <Activity className="h-3 w-3" /> {item.poli}
                      </span>
                      <ChevronRight className={cn("h-4 w-4", isActive ? "text-blue-500" : "text-slate-300 group-hover:text-slate-400")} />
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* KANAN: Detail Pasien */}
          <div className="h-full pr-2 flex flex-col min-h-0 overflow-y-auto custom-scrollbar">
            {!activeQueueItem && (
              <div className="flex flex-1 items-center justify-center text-slate-400 flex-col gap-4">
                <Shield className="h-16 w-16 opacity-20" />
                <p className="text-lg font-medium">Pilih antrean di sebelah kiri untuk memulai validasi.</p>
              </div>
            )}
            
            {view === "preview" && activeQueueItem && (
              <div className="space-y-6">
                {/* Box 1: Info Pasien */}
                <div className="rounded-2xl border border-slate-200 bg-white shadow-sm p-8">
                  <div className="flex items-start gap-4 mb-8">
                    <div className="h-14 w-14 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-xl shrink-0">
                      {activeQueueItem.name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <h2 className="font-bold text-slate-900 text-2xl mb-1">{activeQueueItem.name}</h2>
                      <p className="text-base text-slate-500 mb-2">({activeQueueItem.diagnosis})</p>
                      <div className="flex items-center gap-2 text-sm text-slate-500">
                        <span className="bg-slate-100 px-2 py-0.5 rounded text-xs font-semibold">{activeQueueItem.id}</span>
                        <span>•</span>
                        <span>{activeQueueItem.age}</span>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-x-8 gap-y-6">
                    <div>
                      <div className="flex items-center gap-2 text-slate-400 mb-1.5">
                        <Activity className="h-4 w-4" />
                        <p className="text-[11px] font-semibold uppercase tracking-widest">Poliklinik</p>
                      </div>
                      <p className="font-semibold text-slate-900 text-base">{activeQueueItem.poli}</p>
                    </div>
                    <div>
                      <div className="flex items-center gap-2 text-slate-400 mb-1.5">
                        <Clock className="h-4 w-4" />
                        <p className="text-[11px] font-semibold uppercase tracking-widest">Tanggal Lahir</p>
                      </div>
                      <p className="font-semibold text-slate-900 text-base">{activeQueueItem.dateOfBirth}</p>
                    </div>
                    <div>
                      <div className="flex items-center gap-2 text-slate-400 mb-1.5">
                        <AlertTriangle className="h-4 w-4" />
                        <p className="text-[11px] font-semibold uppercase tracking-widest text-red-500">Alergi Obat</p>
                      </div>
                      {activeQueueItem.allergies === "Tidak ada alergi yang diketahui" || activeQueueItem.allergies === "-" ? (
                        <div className="bg-red-50/50 border border-red-100 text-red-600 px-4 py-3 rounded-xl text-sm font-medium">
                          {activeQueueItem.allergies}
                        </div>
                      ) : (
                        <p className="font-bold text-red-600 text-base">{activeQueueItem.allergies}</p>
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-2 text-slate-400 mb-1.5">
                        <Activity className="h-4 w-4" />
                        <p className="text-[11px] font-semibold uppercase tracking-widest">Diagnosis</p>
                      </div>
                      <p className="font-semibold text-slate-900 text-base">{activeQueueItem.diagnosis}</p>
                    </div>
                  </div>
                </div>

                {/* Box 2: Daftar Obat */}
                <div className="rounded-2xl border border-slate-200 bg-white shadow-sm p-8">
                  <div className="flex items-center gap-2 mb-6">
                    <LinkIcon className="h-5 w-5 text-emerald-600" />
                    <h3 className="font-bold text-slate-900 text-lg">Daftar Obat Resep</h3>
                  </div>

                  <ul className="space-y-3">
                    {activeQueueItem.medicines?.map((m: string, i: number) => {
                      let title = m;
                      let dosis = "1 x 1 sesudah makan"; 
                      
                      return (
                        <li key={i} className="flex items-start gap-3 p-4 rounded-xl bg-slate-50 border border-slate-100">
                          <div className="h-2 w-2 rounded-full bg-emerald-500 flex-shrink-0 mt-2" />
                          <div>
                            <p className="text-base font-semibold text-slate-800 mb-1">{title}</p>
                            <div className="flex items-center gap-2">
                              <span className="text-[10px] bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded font-medium">Dosis</span>
                              <span className="text-sm text-slate-500">{dosis}</span>
                            </div>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </div>

                {/* Action Buttons */}
                <div className="flex justify-end gap-3 pt-2">
                  <button onClick={() => { setActiveQueueItem(null); setView("form"); }} className="px-6 py-2.5 rounded-xl font-semibold text-slate-600 hover:bg-slate-100 transition-colors bg-white border border-slate-200 shadow-sm">
                    Batal
                  </button>
                  <button onClick={handleStartValidation} className="px-8 py-2.5 rounded-xl font-bold bg-[#0d9468] hover:bg-[#0a7a55] text-white shadow-md transition-all flex items-center gap-2">
                    <Shield className="h-5 w-5" /> Mulai Validasi AI Sekarang
                  </button>
                </div>
              </div>
            )}
            
            {(view === "form" || view === "preview") && error && (
              <div className="p-6 bg-red-50 text-red-700 rounded-xl border border-red-200 mt-4">
                {error}
              </div>
            )}
          </div>
        </>
      )}

      {view === "loading" && activeQueueItem && (
        <div className="w-full">
          <LoadingScreen patientId={activeQueueItem.id} />
        </div>
      )}
      {view === "result" && result && (
        <div className="w-full">
          <ResultView result={result} onBack={() => { setActiveQueueItem(null); setView("form"); setResult(null); }} />
        </div>
      )}
    </div>
  );
}
