"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, CheckCircle, Loader2, User, Pill, ClipboardList, BookOpen, ShieldAlert, Activity, Package } from "lucide-react";
import { routes } from "@/lib/constants/routes";
import { getAuthHeader } from "@/lib/api/client";
import { cn } from "@/lib/utils/cn";

type JsonObject = Record<string, unknown>;
type View = "form" | "loading" | "result";

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

function LoadingScreen({ prescriptionId }: { prescriptionId: string }) {
  const steps = [
    { label: "Mengambil data resep & pasien", icon: <Package className="h-4 w-4" /> },
    { label: "Menyiapkan clinical reasoning AI", icon: <Activity className="h-4 w-4" /> },
    { label: "Membuat checklist serah obat", icon: <ClipboardList className="h-4 w-4" /> },
  ];
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center">
      <div className="w-full max-w-sm mx-auto flex flex-col items-center gap-8">
        {/* Spinner */}
        <div className="relative flex items-center justify-center">
          <div className="h-24 w-24 rounded-full border-4 border-emerald-100" />
          <div className="absolute inset-0 animate-spin rounded-full border-4 border-transparent border-t-emerald-500" />
          <div className="absolute inset-0 animate-spin rounded-full border-4 border-transparent border-r-emerald-300" style={{ animationDuration: "1.5s" }} />
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50">
              <Package className="h-6 w-6 text-emerald-600" />
            </div>
          </div>
        </div>

        {/* Title */}
        <div className="text-center space-y-1">
          <h3 className="text-2xl font-black text-slate-900">Memproses Dispensing</h3>
          <p className="text-sm text-slate-500">
            ID Resep: <span className="font-bold text-emerald-600">#{prescriptionId}</span>
          </p>
        </div>

        {/* Steps */}
        <div className="w-full space-y-2.5">
          {steps.map((step, i) => (
            <div key={i} className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3.5 shadow-sm">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-emerald-500">
                <Loader2 className="h-4 w-4 animate-spin" style={{ animationDelay: `${i * 250}ms` }} />
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

function ResultView({ preview, onBack, onComplete, isCompleting, completion }: {
  preview: JsonObject; onBack: () => void; onComplete: () => void; isCompleting: boolean; completion: JsonObject | null;
}) {
  const medicinesDetail = useMemo(() => toArray(preview.medicines_detail).filter(isObject), [preview]);

  // Ambil reasoning — bisa dari root dispensing_reasoning atau dari medgemma_output di dalamnya
  const reasoning = useMemo(() => {
    const dr = preview.dispensing_reasoning;
    if (!isObject(dr)) return null;
    const root = dr as JsonObject;
    const hasCara = Array.isArray(root.cara_penyiapan) && (root.cara_penyiapan as unknown[]).length > 0;
    if (hasCara) return root;
    const mo = root.medgemma_output;
    if (isObject(mo)) return mo as JsonObject;
    return root;
  }, [preview]);

  const checklistItems = useMemo(() => {
    const fromReasoning = toTextList(reasoning?.checklist_serah_obat);
    if (fromReasoning.length > 0) return fromReasoning;
    return toTextList(preview.pemberian_obat_checklist);
  }, [preview, reasoning]);

  const patientName = pickText(preview, ["patient_name"], "-");
  const prescriptionId = pickText(preview, ["prescription_id"], "-");
  const workflowStatus = pickText(preview, ["workflow_status"], "-");
  const validationMessage = pickText(preview, ["validation_message"], "-");
  const needsMixing = preview.need_mixing === true || readText(preview.need_mixing) === "true" ? "Perlu" : "Tidak Perlu";

  const snapshot = isObject(preview.patient_snapshot) ? preview.patient_snapshot as JsonObject : null;
  const usia = snapshot?.usia_tahun ? `${snapshot.usia_tahun} Tahun` : "-";
  const alergi = pickText(snapshot, ["alergi"], "Tidak Ada");
  const diagnosis = pickText(snapshot, ["diagnosis"], "-");
  const bpjs = pickText(snapshot, ["bpjs_status"], "-");
  const bpjsActive = bpjs.toLowerCase() === "aktif";

  const caraPenyiapan = toTextList(reasoning?.cara_penyiapan).slice(0, 3);
  const edukasiPenggunaan = toTextList(reasoning?.edukasi_penggunaan).slice(0, 3);
  const peringatan = toTextList(reasoning?.peringatan).slice(0, 3);
  const monitoringLanjutan = toTextList(reasoning?.monitoring_lanjutan).slice(0, 3);
  const ringkasan = pickText(reasoning, ["ringkasan"], "");

  const [checked, setChecked] = useState<Record<number, boolean>>({});
  const checkedCount = Object.values(checked).filter(Boolean).length;
  const allChecked = checklistItems.length > 0 && checkedCount === checklistItems.length;
  const progress = checklistItems.length > 0 ? Math.round((checkedCount / checklistItems.length) * 100) : 0;

  const firstMed = medicinesDetail[0];
  const medName = firstMed ? pickText(firstMed, ["nama_obat", "obat", "name"], "-") : "-";
  const medAturan = firstMed ? pickText(firstMed, ["aturan_minum", "signa"], "-") : "-";
  const medStok = firstMed ? pickText(firstMed, ["sediaan", "stok", "stok_tersedia"], "Tersedia") : "-";

  return (
    <div className="space-y-4">
      <button onClick={onBack} className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-800 transition-colors">
        <ArrowLeft className="h-4 w-4" /> Dispensing Resep Lain
      </button>

      {/* Header Card */}
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        <div className="flex flex-wrap items-center gap-4 px-6 py-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-emerald-100">
            <User className="h-5 w-5 text-emerald-600" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-bold text-slate-900">{patientName}</h2>
            <p className="text-sm text-slate-500">ID Resep: #{prescriptionId} · {bpjsActive ? "Pasien BPJS" : "Pasien Umum"}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-right">
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">Validasi</p>
              <p className="text-sm font-semibold text-slate-700 max-w-[200px] truncate">{validationMessage}</p>
            </div>
            <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-bold",
              workflowStatus.toLowerCase().includes("ready") || workflowStatus.toLowerCase().includes("siap")
                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                : "bg-amber-50 text-amber-700 border-amber-200"
            )}>
              <span className="h-2 w-2 rounded-full bg-current" />
              {workflowStatus}
            </span>
          </div>
        </div>
      </div>

      {/* Main 3-column layout — full height */}
      <div className="grid gap-4 lg:grid-cols-[280px_1fr_280px] min-h-[calc(100vh-280px)]">

        {/* Kiri: Detail Obat + Info Pasien */}
        <div className="space-y-4 flex flex-col">
          <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
            <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
              <Pill className="h-4 w-4 text-emerald-500" />
              <p className="text-sm font-bold text-slate-700">Detail Obat</p>
            </div>
            <div className="p-4">
              <p className="text-lg font-black text-emerald-700">{medName}</p>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <div className="rounded-xl bg-slate-50 border border-slate-100 px-3 py-2">
                  <p className="text-xs text-slate-400 font-medium">Aturan</p>
                  <p className="text-sm font-bold text-slate-800 mt-0.5">{medAturan}</p>
                </div>
                <div className="rounded-xl bg-slate-50 border border-slate-100 px-3 py-2">
                  <p className="text-xs text-slate-400 font-medium">Stok</p>
                  <p className="text-sm font-bold text-emerald-700 mt-0.5">{medStok}</p>
                </div>
              </div>
              {medicinesDetail.length > 1 && (
                <div className="mt-3 space-y-2">
                  {medicinesDetail.slice(1).map((item, i) => (
                    <div key={i} className="rounded-xl bg-slate-50 border border-slate-100 px-3 py-2">
                      <p className="text-sm font-semibold text-slate-800">{pickText(item, ["nama_obat", "obat", "name"], "-")}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{pickText(item, ["aturan_minum", "signa"], "-")}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
            {/* Info pasien */}
            <div className="border-t border-slate-100 px-4 py-3 space-y-2">
              {[
                { label: "Diagnosis", value: diagnosis },
                { label: "Racikan", value: needsMixing },
                { label: "Alergi", value: alergi, red: alergi !== "Tidak Ada" && alergi !== "-" },
              ].map((row) => (
                <div key={row.label} className="flex items-center justify-between text-sm">
                  <span className="text-slate-500">{row.label}</span>
                  <span className={cn("font-semibold", row.red ? "text-red-600" : "text-slate-800")}>{row.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Catatan apoteker */}
          {ringkasan && (
            <div className="rounded-2xl bg-emerald-700 p-4 text-white">
              <p className="text-xs font-semibold uppercase tracking-widest opacity-70 mb-2">Catatan Apoteker:</p>
              <p className="text-sm font-medium leading-relaxed italic">"{ringkasan.slice(0, 120)}{ringkasan.length > 120 ? "..." : ""}"</p>
            </div>
          )}
        </div>

        {/* Tengah: 4 Reasoning Cards 2x2 — stretch full */}
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-3 flex-1">
            {[
              { title: "Langkah Penyiapan", items: caraPenyiapan, icon: <Package className="h-3.5 w-3.5 text-white" />, bg: "bg-blue-50", border: "border-blue-200", titleCls: "text-blue-700", textCls: "text-blue-800", iconBg: "bg-blue-500" },
              { title: "Edukasi Penggunaan", items: edukasiPenggunaan, icon: <BookOpen className="h-3.5 w-3.5 text-white" />, bg: "bg-emerald-50", border: "border-emerald-200", titleCls: "text-emerald-700", textCls: "text-emerald-800", iconBg: "bg-emerald-500" },
              { title: "Peringatan & Kontraindikasi", items: peringatan, icon: <ShieldAlert className="h-3.5 w-3.5 text-white" />, bg: "bg-red-50", border: "border-red-200", titleCls: "text-red-700", textCls: "text-red-800", iconBg: "bg-red-500" },
              { title: "Monitoring Lanjutan", items: monitoringLanjutan, icon: <Activity className="h-3.5 w-3.5 text-white" />, bg: "bg-amber-50", border: "border-amber-200", titleCls: "text-amber-700", textCls: "text-amber-800", iconBg: "bg-amber-500" },
            ].map((card) => (
              <div key={card.title} className={cn("rounded-2xl border p-5 flex flex-col", card.bg, card.border)}>
                <div className="flex items-center gap-2 mb-3">
                  <div className={cn("flex h-6 w-6 shrink-0 items-center justify-center rounded-full", card.iconBg)}>{card.icon}</div>
                  <p className={cn("text-xs font-bold uppercase tracking-widest", card.titleCls)}>{card.title}</p>
                </div>
                {card.items.length > 0 ? (
                  <ul className="space-y-2 flex-1">
                    {card.items.map((item, i) => (
                      <li key={i} className={cn("flex items-start gap-2 text-sm leading-relaxed", card.textCls)}>
                        <span className={cn("mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full", card.iconBg)} />
                        {item}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-400">Belum ada data.</p>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Kanan: Checklist — stretch full */}
        <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden flex flex-col h-full">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <div className="flex items-center gap-2">
              <ClipboardList className="h-4 w-4 text-slate-500" />
              <p className="text-sm font-bold text-slate-700">Checklist Serah</p>
            </div>
            <span className={cn("rounded-full px-2 py-0.5 text-xs font-bold",
              allChecked ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600"
            )}>{checkedCount}/{checklistItems.length}</span>
          </div>
          {/* Progress bar */}
          <div className="h-1 bg-slate-100">
            <div className="h-1 bg-emerald-500 transition-all duration-500" style={{ width: `${progress}%` }} />
          </div>
          <div className="flex-1 divide-y divide-slate-100 overflow-y-auto">
            {checklistItems.map((item, i) => (
              <label key={i} className="flex cursor-pointer items-start gap-3 px-4 py-3 hover:bg-slate-50 transition-colors">
                <div className={cn("mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 transition-all",
                  checked[i] ? "bg-emerald-500 border-emerald-500" : "border-slate-300 bg-white"
                )}>
                  {checked[i] && <CheckCircle className="h-3.5 w-3.5 text-white" />}
                </div>
                <input type="checkbox" checked={!!checked[i]} onChange={() => setChecked((prev) => ({ ...prev, [i]: !prev[i] }))} className="sr-only" />
                <span className={cn("text-sm leading-relaxed", checked[i] ? "text-slate-400 line-through" : "text-slate-700")}>{item}</span>
              </label>
            ))}
          </div>
          <div className="border-t border-slate-100 p-4">
            <button onClick={onComplete} disabled={isCompleting || !allChecked}
              className={cn("w-full rounded-xl px-4 py-3 text-sm font-bold transition-all flex items-center justify-center gap-2",
                allChecked && !isCompleting
                  ? "bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm"
                  : isCompleting
                  ? "bg-emerald-100 text-emerald-700 cursor-wait"
                  : "bg-slate-100 text-slate-400 cursor-not-allowed"
              )}>
              {isCompleting ? <><Loader2 className="h-4 w-4 animate-spin" /> Menyelesaikan...</> : <>Selesaikan Dispensing →</>}
            </button>
            {!allChecked && <p className="mt-1.5 text-center text-xs text-slate-400">Selesaikan semua checklist untuk mengaktifkan tombol</p>}
            {completion && (
              <div className="mt-2 flex items-center justify-center gap-2 text-sm font-semibold text-emerald-700">
                <CheckCircle className="h-4 w-4" />
                {pickText(completion, ["message", "detail"], "Dispensing selesai.")}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function DispensingPanel() {
  const searchParams = useSearchParams();
  const queryPrescriptionId = searchParams.get("prescriptionId") ?? "";
  const [prescriptionId, setPrescriptionId] = useState(queryPrescriptionId);
  const [view, setView] = useState<View>("form");
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<JsonObject | null>(null);
  const [isCompleting, setIsCompleting] = useState(false);
  const [completion, setCompletion] = useState<JsonObject | null>(null);

  useEffect(() => {
    if (queryPrescriptionId && !prescriptionId) setPrescriptionId(queryPrescriptionId);
  }, [queryPrescriptionId, prescriptionId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const pid = prescriptionId.trim();
    if (!pid) { setError("ID resep wajib diisi."); return; }
    setView("loading"); setError(null); setPreview(null); setCompletion(null);
    try {
      const res = await fetch(routes.api.pharmacy.dispensing, {
        method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify({ prescription_id: pid, include_llm_reasoning: true }),
      });
      const body = (await res.json().catch(() => null)) as unknown;
      if (!res.ok) throw new Error(isObject(body) ? pickText(body, ["detail", "error", "message"], "") || "Gagal memuat preview." : "Gagal memuat preview.");
      if (!isObject(body)) throw new Error("Respons tidak valid.");
      setPreview(body); setView("result");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Terjadi kesalahan."); setView("form");
    }
  }

  async function handleComplete() {
    if (!preview) return;
    const pid = pickText(preview, ["prescription_id"], prescriptionId);
    if (!pid || pid === "-") { setError("ID resep tidak tersedia."); return; }
    setIsCompleting(true);
    try {
      const res = await fetch(routes.api.pharmacy.dispensingComplete, {
        method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify({ prescription_id: pid }),
      });
      const body = (await res.json().catch(() => null)) as unknown;
      if (!res.ok) throw new Error(isObject(body) ? pickText(body, ["detail", "error", "message"], "") || "Gagal menyelesaikan." : "Gagal menyelesaikan.");
      if (!isObject(body)) throw new Error("Respons tidak valid.");
      setCompletion(body);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Terjadi kesalahan.");
    } finally {
      setIsCompleting(false);
    }
  }

  return (
    <div className="space-y-5">
      {view === "form" && (
        <>
          <section className="pharmacy-hero pharmacy-hero--dispensing">
            <p className="text-sm font-bold uppercase tracking-widest text-emerald-600">Dispensing</p>
            <h1 className="mt-2 text-2xl font-black tracking-tight text-slate-900">Proses Dispensing Obat</h1>
            <p className="mt-2 max-w-xl text-base text-slate-600">Masukkan ID resep untuk menyiapkan dispensing, edukasi pasien, dan checklist serah obat.</p>
          </section>
          <section className="pharmacy-panel p-6">
            <h2 className="text-base font-bold text-slate-900">Masukkan ID Resep</h2>
            <p className="mt-1 text-base text-slate-500">AI akan memproses dispensing dengan clinical reasoning.</p>
            <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3 sm:flex-row">
              <input type="text" value={prescriptionId} onChange={(e) => setPrescriptionId(e.target.value)} placeholder="Contoh: 2" className="pharmacy-input flex-1 text-base" />
              <button type="submit" className="pharmacy-button-primary pharmacy-button-primary--emerald shrink-0 px-7 py-3 text-base">Ambil Preview</button>
            </form>
            {error && <div className="pharmacy-alert pharmacy-alert--error mt-3 text-base">{error}</div>}
          </section>
        </>
      )}
      {view === "loading" && <LoadingScreen prescriptionId={prescriptionId} />}
      {view === "result" && preview && (
        <ResultView preview={preview} onBack={() => { setView("form"); setPreview(null); setCompletion(null); }} onComplete={handleComplete} isCompleting={isCompleting} completion={completion} />
      )}
    </div>
  );
}
