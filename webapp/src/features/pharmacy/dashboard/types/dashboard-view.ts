export interface DashboardDistributionItem {
  label: string;
  value: number;
}

export interface DashboardTopMedicine {
  name: string;
  stock: number;
  expiry: string;
}

export interface DashboardViewModel {
  source: "backend" | "fallback";
  fetchedAt: string;
  totalMedicines: number;
  criticalStock: number;
  expiringSoon: number;
  totalChats: number;
  stockDistribution: DashboardDistributionItem[];
  expiryDistribution: DashboardDistributionItem[];
  topMedicines: DashboardTopMedicine[];
  notes: string[];
}

export interface PharmacyDashboardPageProps {
  dashboard: DashboardViewModel;
  userName: string;
  sessionEmail?: string | null;
  analytics?: {
    deskriptif: { judul: string; ringkasan: string; temuan: string[] };
    prediktif: { judul: string; ringkasan: string; proyeksi: string[] };
    preskriptif: { judul: string; ringkasan: string; aksi: string[] };
  } | null;
  analyticsLoading?: boolean;
}
