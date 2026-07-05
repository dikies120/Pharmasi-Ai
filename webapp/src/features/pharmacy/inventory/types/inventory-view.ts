// Type definitions for inventory view
export type InventoryStatus = "Kritis" | "Hampir Habis" | "Hampir Expired" | "Aman";

export interface InventoryItem {
  id: string;
  name: string;
  stock: number;
  location: string;
  batch: string;
  expiry: string;
  status: InventoryStatus;
}

export interface InventorySummary {
  totalItems: number;
  criticalItems: number;
  lowItems: number;
  expiringSoonItems: number;
}

export interface InventoryViewModel {
  source: "backend" | "fallback";
  fetchedAt: string;
  items: InventoryItem[];
  summary: InventorySummary;
  notes: string[];
}

export interface PharmacyInventoryPageProps {
  inventory: InventoryViewModel;
  isAddModalOpen: boolean;
  setIsAddModalOpen: (val: boolean) => void;
  onAddStock: (data: any) => Promise<void>;
  isSubmitting: boolean;
  medicineList: any[]; // untuk dropdown/autocomplete
  successMessage?: string | null;
  errorMessage?: string | null;
  // Edit & Delete Props
  isEditModalOpen?: boolean;
  setIsEditModalOpen?: (val: boolean) => void;
  selectedBatch?: InventoryItem | null;
  setSelectedBatch?: (batch: InventoryItem | null) => void;
  onUpdateStock?: (id: string, data: any) => Promise<void>;
  onDeleteStock?: (id: string) => Promise<void>;
}

export interface InventoryStatusStyle {
  text: string;
  bg: string;
  border: string;
  dot: string;
}

export interface InventorySummaryConfig {
  key: "totalItems" | "criticalItems" | "lowItems" | "expiringSoonItems";
  label: string;
  color: string;
  bg: string;
  border: string;
}