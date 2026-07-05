"use client";

import { useEffect, useState } from "react";
import { PharmacyDashboardPage } from "@/features/pharmacy/dashboard/components/dashboard-page";
import { apiClient } from "@/lib/api";
import type { DashboardViewModel } from "@/features/pharmacy/dashboard/types/dashboard-view";
const FALLBACK: DashboardViewModel = {
  source: "fallback",
  fetchedAt: new Date().toISOString(),
  totalMedicines: 0,
  criticalStock: 0,
  expiringSoon: 0,
  totalChats: 0,
  stockDistribution: [],
  expiryDistribution: [],
  topMedicines: [],
  notes: [],
};

function mapBackendToDashboard(raw: any): DashboardViewModel {
  const medicines = raw?.medicines ?? {};
  const chatTrends = raw?.chat_trends ?? {};
  const stockDist = medicines?.stock_distribution ?? {};
  const expiryDist = medicines?.expiry_distribution ?? {};
  const medicineList = medicines?.medicines ?? [];

  return {
    source: "backend",
    fetchedAt: raw?.timestamp ?? new Date().toISOString(),
    totalMedicines: medicines?.total_medicines ?? 0,
    criticalStock: stockDist["Kritis (<50)"] ?? 0,
    expiringSoon: expiryDist["Segera Kadaluarsa (< 30 hari)"] ?? 0,
    totalChats: chatTrends?.total_chats ?? 0,
    stockDistribution: Object.entries(stockDist).map(([label, value]) => ({ label, value: Number(value) })),
    expiryDistribution: Object.entries(expiryDist).map(([label, value]) => ({ label, value: Number(value) })),
    topMedicines: medicineList.slice(0, 8).map((m: any) => ({
      name: m.nama_obat ?? "-",
      stock: m.stok ?? 0,
      expiry: m.tanggal_kadaluarsa ?? "-",
    })),
    notes: [],
  };
}

export function PharmacyDashboardRoute() {
  const [dashboard, setDashboard] = useState<DashboardViewModel>(FALLBACK);
  const [analytics, setAnalytics] = useState<any | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchDashboard = () => {
      apiClient.pharmacy.getDashboard()
        .then((data) => setDashboard(mapBackendToDashboard(data)))
        .catch(() => setDashboard(FALLBACK))
        .finally(() => setIsLoading(false));
    };

    fetchDashboard();
    const interval = setInterval(fetchDashboard, 30000); // 30 detik polling

    // Generate analytics via AI (hanya di awal)
    setAnalyticsLoading(true);
    apiClient.analytics.getInsights()
      .then((data: any) => {
        const result = data?.analytics ?? null;
        setAnalytics(result);
      })
      .catch(() => setAnalytics(null))
      .finally(() => setAnalyticsLoading(false));
  }, []);

  if (isLoading) {
    return <div className="p-6 text-slate-500">Memuat dashboard...</div>;
  }

  return (
    <PharmacyDashboardPage
      dashboard={dashboard}
      analytics={analytics}
      analyticsLoading={analyticsLoading}
      userName="Tim Farmasi"
      sessionEmail={null}
    />
  );
}
