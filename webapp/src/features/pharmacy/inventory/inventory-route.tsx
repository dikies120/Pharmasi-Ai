"use client";

import { useEffect, useState } from "react";
import { PharmacyInventoryPage } from "@/features/pharmacy/inventory/components/inventory-page";
import type { InventoryViewModel, InventoryItem, InventoryStatus } from "@/features/pharmacy/inventory/types/inventory-view";
import { env } from "@/lib/env";
import { getAuthHeader } from "@/lib/api/client";
import { apiClient } from "@/lib/api";

const FALLBACK: InventoryViewModel = {
  source: "fallback",
  fetchedAt: new Date().toISOString(),
  items: [],
  summary: { totalItems: 0, criticalItems: 0, lowItems: 0, expiringSoonItems: 0 },
  notes: [],
};

function deriveStatus(stock: number, expiry: string): InventoryStatus {
  const daysLeft = expiry
    ? Math.floor((new Date(expiry).getTime() - Date.now()) / 86400000)
    : null;
  if (daysLeft !== null && daysLeft <= 30) return "Hampir Expired";
  if (stock < 20) return "Kritis";
  if (stock < 50) return "Hampir Habis";
  return "Aman";
}

function mapBackendToInventory(raw: any): InventoryViewModel {
  const items: InventoryItem[] = (raw?.data ?? []).map((item: any, i: number) => {
    const stock = item.stok ?? item.stock ?? item.stock_qty ?? 0;
    const expiry = item.tanggal_kadaluarsa ?? item.expiry_date ?? item.expiry ?? "-";
    return {
      id: item.id ?? `item-${i}`,
      name: item.nama_obat ?? item.name ?? "-",
      stock,
      location: item.lokasi ?? item.location ?? "Gudang Utama",
      batch: item.batch_no ?? item.batch ?? "-",
      expiry,
      status: deriveStatus(stock, expiry),
    };
  });

  const summary = {
    totalItems: items.length,
    criticalItems: items.filter((i) => i.status === "Kritis").length,
    lowItems: items.filter((i) => i.status === "Hampir Habis").length,
    expiringSoonItems: items.filter((i) => i.status === "Hampir Expired").length,
  };

  return {
    source: "backend",
    fetchedAt: new Date().toISOString(),
    items,
    summary,
    notes: ["Data dari backend monitoring stok."],
  };
}

export function PharmacyInventoryRoute() {
  const [inventory, setInventory] = useState<InventoryViewModel>(FALLBACK);
  const [isLoading, setIsLoading] = useState(true);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [medicineList, setMedicineList] = useState<any[]>([]);

  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [selectedBatch, setSelectedBatch] = useState<InventoryItem | null>(null);

  const fetchInventory = () => {
    fetch(`${env.backendUrl}/api/v1/pharmacy/inventory/realtime`, { headers: getAuthHeader() })
      .then((r) => r.json())
      .then((data) => setInventory(mapBackendToInventory(data)))
      .catch(() => setInventory(FALLBACK))
      .finally(() => setIsLoading(false));
  };

  const fetchMedicines = () => {
    apiClient.pharmacy.getMedicines()
      .then((data) => setMedicineList(data.medicines || []))
      .catch(() => {});
  };

  useEffect(() => {
    fetchInventory();
    fetchMedicines();
  }, []);

  const handleAddStock = async (formData: any) => {
    setIsSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await apiClient.pharmacy.addInventoryBatch(formData);
      setIsAddModalOpen(false);
      fetchInventory();
      fetchMedicines();
      setSuccessMessage(`Stok ${formData.nama_obat} berhasil ditambahkan!`);
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err: any) {
      setErrorMessage(`Gagal menambahkan stok: ${err.message || "Unknown error"}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdateStock = async (id: string, formData: any) => {
    setIsSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await apiClient.pharmacy.updateInventoryBatch(id, formData);
      setIsEditModalOpen(false);
      setSelectedBatch(null);
      fetchInventory();
      setSuccessMessage(`Batch ${formData.batch_no} berhasil diupdate!`);
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err: any) {
      setErrorMessage(`Gagal mengupdate stok: ${err.message || "Unknown error"}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteStock = async (id: string) => {
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await apiClient.pharmacy.deleteInventoryBatch(id);
      fetchInventory();
      setSuccessMessage(`Batch berhasil dihapus!`);
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err: any) {
      setErrorMessage(`Gagal menghapus stok: ${err.message || "Unknown error"}`);
    }
  };

  if (isLoading) {
    return <div className="p-6 text-slate-500">Memuat inventory...</div>;
  }

  return (
    <PharmacyInventoryPage 
      inventory={inventory} 
      isAddModalOpen={isAddModalOpen}
      setIsAddModalOpen={(val) => {
        setIsAddModalOpen(val);
        if (val) {
          setErrorMessage(null);
          setSuccessMessage(null);
        }
      }}
      onAddStock={handleAddStock}
      isSubmitting={isSubmitting}
      medicineList={medicineList}
      successMessage={successMessage}
      errorMessage={errorMessage}
      isEditModalOpen={isEditModalOpen}
      setIsEditModalOpen={setIsEditModalOpen}
      selectedBatch={selectedBatch}
      setSelectedBatch={setSelectedBatch}
      onUpdateStock={handleUpdateStock}
      onDeleteStock={handleDeleteStock}
    />
  );
}
