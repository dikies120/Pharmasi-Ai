import type {
  InventoryStatus,
  InventoryStatusStyle,
  InventorySummaryConfig,
} from "@/features/pharmacy/inventory/types/inventory-view";

export const INVENTORY_STATUS_STYLE: Record<InventoryStatus, InventoryStatusStyle> = {
  Kritis: {
    text: "#f87171",
    bg: "rgba(239,68,68,0.08)",
    border: "rgba(239,68,68,0.2)",
    dot: "#ef4444",
  },
  "Hampir Habis": {
    text: "#fbbf24",
    bg: "rgba(251,191,36,0.08)",
    border: "rgba(251,191,36,0.2)",
    dot: "#f59e0b",
  },
  "Hampir Expired": {
    text: "#fb923c",
    bg: "rgba(251,146,60,0.08)",
    border: "rgba(251,146,60,0.2)",
    dot: "#f97316",
  },
  Aman: {
    text: "#34d399",
    bg: "rgba(16,185,129,0.08)",
    border: "rgba(16,185,129,0.2)",
    dot: "#10b981",
  },
};

export const INVENTORY_SUMMARY_CONFIG: InventorySummaryConfig[] = [
  {
    key: "totalItems",
    label: "Total Item",
    color: "#38bdf8",
    bg: "rgba(14,165,233,0.06)",
    border: "rgba(14,165,233,0.14)",
  },
  {
    key: "criticalItems",
    label: "Status Kritis",
    color: "#f87171",
    bg: "rgba(239,68,68,0.06)",
    border: "rgba(239,68,68,0.14)",
  },
  {
    key: "lowItems",
    label: "Hampir Habis",
    color: "#fbbf24",
    bg: "rgba(251,191,36,0.06)",
    border: "rgba(251,191,36,0.14)",
  },
  {
    key: "expiringSoonItems",
    label: "Hampir Expired",
    color: "#fb923c",
    bg: "rgba(251,146,60,0.06)",
    border: "rgba(251,146,60,0.14)",
  },
];

export const INVENTORY_TABLE_HEADERS = [
  "Nama Obat",
  "Stok",
  "Lokasi",
  "Batch",
  "Kadaluarsa",
  "Status",
] as const;