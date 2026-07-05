"use client";

import type { PharmacyDashboardPageProps } from "@/features/pharmacy/dashboard/types/dashboard-view";
import Link from "next/link";
import { routes } from "@/lib/constants/routes";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";

const numFmt = new Intl.NumberFormat("id-ID");
const dateFmt = new Intl.DateTimeFormat("id-ID", { dateStyle: "medium", timeStyle: "short" });

const COLORS = {
  kritis: "#ef4444",
  hampir: "#f59e0b",
  aman: "#10b981",
  banyak: "#6366f1",
  expired: "#f97316",
};

function pickColor(label: string): string {
  const l = label.toLowerCase();
  if (l.includes("kritis")) return COLORS.kritis;
  if (l.includes("hampir habis") || l.includes("50-200")) return COLORS.hampir;
  if (l.includes("banyak") || l.includes(">200")) return COLORS.banyak;
  if (l.includes("segera") || l.includes("expired")) return COLORS.expired;
  return COLORS.aman;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 shadow-lg text-sm">
      <p className="font-semibold text-slate-800">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }} className="font-bold">
          {numFmt.format(p.value)} unit
        </p>
      ))}
    </div>
  );
};

function AnalyticsCard({
  type,
  items,
  loading,
}: {
  type: "deskriptif" | "prediktif" | "preskriptif";
  items: string[];
  loading: boolean;
}) {
  const config = {
    deskriptif: { border: "border-t-blue-500", dot: "bg-blue-500", badge: "bg-blue-50 text-blue-700", label: "Deskriptif", sub: "Kondisi saat ini" },
    prediktif: { border: "border-t-violet-500", dot: "bg-violet-500", badge: "bg-violet-50 text-violet-700", label: "Prediktif", sub: "Proyeksi 30 hari" },
    preskriptif: { border: "border-t-emerald-500", dot: "bg-emerald-500", badge: "bg-emerald-50 text-emerald-700", label: "Preskriptif", sub: "Aksi prioritas" },
  }[type];

  return (
    <article className={`rounded-2xl border-t-4 border border-slate-200 bg-white p-5 shadow-sm ${config.border}`}>
      <div className="flex items-center justify-between mb-4">
        <span className={`rounded-full px-3 py-1 text-xs font-bold ${config.badge}`}>{config.label}</span>
        <span className="text-xs text-slate-400">{config.sub}</span>
      </div>
      {loading ? (
        <div className="space-y-3">
          {[80, 100, 70].map((w, i) => (
            <div key={i} className="flex items-start gap-2.5">
              <div className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-slate-200 animate-pulse" />
              <div className="h-4 animate-pulse rounded bg-slate-100" style={{ width: `${w}%` }} />
            </div>
          ))}
        </div>
      ) : items.length === 0 ? (
        <p className="text-sm text-slate-400">Belum ada data analitik.</p>
      ) : (
        <ul className="space-y-3">
          {items.slice(0, 3).map((item, i) => {
            const parts = item.split(/(\([^)]+\))/g);
            return (
              <li key={i} className="flex items-start gap-2.5">
                <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${config.dot}`} />
                <span className="text-[15px] leading-snug text-slate-700">
                  {parts.map((part, j) =>
                    part.startsWith("(") && part.endsWith(")") ? (
                      <span key={j} className="font-bold text-slate-900">{part}</span>
                    ) : <span key={j}>{part}</span>
                  )}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </article>
  );
}

export function PharmacyDashboardPage({ dashboard, userName, analytics, analyticsLoading }: PharmacyDashboardPageProps) {
  const stockData = dashboard.stockDistribution.map((d) => ({
    name: d.label.replace(/\s*\(.*\)/, ""),
    value: d.value,
    fill: pickColor(d.label),
  }));

  const expiryData = dashboard.expiryDistribution.map((d) => ({
    name: d.label.length > 20 ? d.label.slice(0, 18) + "…" : d.label,
    value: d.value,
    fill: pickColor(d.label),
  }));

  const topMedData = dashboard.topMedicines.slice(0, 8).map((m) => ({
    name: m.name.split(" ").slice(0, 2).join(" "),
    stok: m.stock,
    fill: m.stock < 20 ? COLORS.kritis : m.stock < 50 ? COLORS.hampir : COLORS.banyak,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-slate-400">Pharma Analitik</p>
          <h1 className="mt-1 text-2xl font-black tracking-tight text-slate-900">
            Selamat datang, {userName || "Tim Farmasi"}
          </h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Diperbarui {dateFmt.format(new Date(dashboard.fetchedAt))}
          </p>
        </div>
        {dashboard.source === "fallback" && (
          <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">
            Backend belum merespons — data fallback
          </span>
        )}
      </div>

      {/* KPI Cards */}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Total Jenis Obat", value: numFmt.format(dashboard.totalMedicines), sub: "Jenis obat terdaftar", color: "border-t-blue-500", num: "text-blue-600" },
          { label: "Stok Kritis", value: numFmt.format(dashboard.criticalStock), sub: "Perlu segera restock", color: "border-t-red-500", num: "text-red-600" },
          { label: "Hampir Kadaluarsa", value: numFmt.format(dashboard.expiringSoon), sub: "Dalam 30 hari ke depan", color: "border-t-amber-500", num: "text-amber-600" },
          { label: "Konsultasi AI", value: numFmt.format(dashboard.totalChats), sub: "Total sesi chat AI", color: "border-t-violet-500", num: "text-violet-600" },
        ].map((c) => (
          <article key={c.label} className={`rounded-2xl border-t-4 border border-slate-200 bg-white p-5 shadow-sm ${c.color}`}>
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">{c.label}</p>
            <p className={`mt-3 text-4xl font-black tracking-tight ${c.num}`}>{c.value}</p>
            <p className="mt-1 text-xs text-slate-400">{c.sub}</p>
          </article>
        ))}
      </section>

      {/* AI Analytics */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900">Analitik AI Farmasi</h2>
            <p className="text-xs text-slate-500">Insight real-time dari AI berdasarkan data inventory</p>
          </div>
          {analyticsLoading && (
            <span className="flex items-center gap-2 text-xs text-slate-400">
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-slate-200 border-t-violet-500" />
              AI menganalisis...
            </span>
          )}
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          <AnalyticsCard type="deskriptif" items={analytics?.deskriptif?.temuan ?? []} loading={analyticsLoading ?? false} />
          <AnalyticsCard type="prediktif" items={analytics?.prediktif?.proyeksi ?? []} loading={analyticsLoading ?? false} />
          <AnalyticsCard type="preskriptif" items={analytics?.preskriptif?.aksi ?? []} loading={analyticsLoading ?? false} />
        </div>
      </section>

      {/* Charts */}
      <section className="grid gap-4 lg:grid-cols-2">
        {/* Bar Chart Distribusi Stok */}
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-base font-bold text-slate-900">Distribusi Stok</h3>
          <p className="text-xs text-slate-500 mt-0.5">Jumlah jenis obat per kategori</p>
          <div className="mt-4 h-52">
            {stockData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stockData} barSize={40}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                    {stockData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="flex h-full items-center justify-center text-sm text-slate-400">Belum ada data.</p>}
          </div>
        </article>

        {/* Pie Chart Kadaluarsa */}
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-base font-bold text-slate-900">Status Kadaluarsa</h3>
          <p className="text-xs text-slate-500 mt-0.5">Distribusi batch berdasarkan expiry</p>
          <div className="mt-4 h-52">
            {expiryData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={expiryData} cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={3} dataKey="value">
                    {expiryData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                  </Pie>
                  <Tooltip formatter={(v: any) => [`${v} batch`, ""]} />
                  <Legend iconType="circle" iconSize={8} formatter={(v) => <span className="text-xs text-slate-600">{v}</span>} />
                </PieChart>
              </ResponsiveContainer>
            ) : <p className="flex h-full items-center justify-center text-sm text-slate-400">Belum ada data.</p>}
          </div>
        </article>
      </section>

      {/* Top Obat Bar Chart */}
      {topMedData.length > 0 && (
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">Stok Obat Teratas</h3>
              <p className="text-xs text-slate-500 mt-0.5">8 obat dengan stok tertinggi</p>
            </div>
            <div className="flex items-center gap-4 text-xs text-slate-500">
              {[{ color: COLORS.kritis, label: "Kritis" }, { color: COLORS.hampir, label: "Hampir Habis" }, { color: COLORS.banyak, label: "Aman" }].map((l) => (
                <span key={l.label} className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full" style={{ background: l.color }} />
                  {l.label}
                </span>
              ))}
              <Link href={routes.pharmacyInventory as any} className="font-semibold text-blue-600 hover:underline ml-2">
                Lihat semua →
              </Link>
            </div>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topMedData} barSize={32}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="stok" radius={[6, 6, 0, 0]}>
                  {topMedData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>
      )}
    </div>
  );
}
