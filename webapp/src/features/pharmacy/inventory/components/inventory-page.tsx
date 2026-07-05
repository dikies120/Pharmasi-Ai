import { useState, useEffect } from "react";
import {
  INVENTORY_STATUS_STYLE,
  INVENTORY_SUMMARY_CONFIG,
  INVENTORY_TABLE_HEADERS,
} from "@/features/pharmacy/inventory/constants/inventory-view";
import type { PharmacyInventoryPageProps } from "@/features/pharmacy/inventory/types/inventory-view";

const numberFormatter = new Intl.NumberFormat("id-ID");
const dateFormatter = new Intl.DateTimeFormat("id-ID", { dateStyle: "medium", timeStyle: "short" });

export function PharmacyInventoryPage({ 
  inventory,
  isAddModalOpen,
  setIsAddModalOpen,
  onAddStock,
  isSubmitting,
  medicineList,
  successMessage,
  errorMessage,
  isEditModalOpen,
  setIsEditModalOpen,
  selectedBatch,
  setSelectedBatch,
  onUpdateStock,
  onDeleteStock
}: PharmacyInventoryPageProps) {
  const [formData, setFormData] = useState({
    nama_obat: "",
    batch_no: "",
    expiry_date: "",
    stock_qty: 0,
    unit: "Box"
  });

  const [editFormData, setEditFormData] = useState({
    batch_no: "",
    expiry_date: "",
    stock_qty: 0,
    unit: "Box"
  });

  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("Semua Status");

  const filteredItems = inventory.items.filter((item) => {
    const matchesSearch = item.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          item.batch.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === "Semua Status" || item.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Sync edit form with selected batch
  useEffect(() => {
    if (selectedBatch && isEditModalOpen) {
      setEditFormData({
        batch_no: selectedBatch.batch,
        expiry_date: selectedBatch.expiry !== "-" ? selectedBatch.expiry : "",
        stock_qty: selectedBatch.stock,
        unit: "Box" // default fallback
      });
    }
  }, [selectedBatch, isEditModalOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onAddStock(formData);
    // Reset form after successful submit is handled in route or here
    setFormData({ nama_obat: "", batch_no: "", expiry_date: "", stock_qty: 0, unit: "Box" });
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (onUpdateStock && selectedBatch) {
      await onUpdateStock(selectedBatch.id, editFormData);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <section className="pharmacy-hero pharmacy-hero--inventory">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-600">Inventory</p>
        <h1 className="mt-2 text-2xl font-black tracking-tight text-slate-900 md:text-3xl">
          Monitoring Stok Real-time
        </h1>
        <p className="mt-2 max-w-xl text-sm text-slate-600">
          Prioritaskan refill item kritis dan antisipasi obat mendekati tanggal kadaluarsa.
        </p>
      </section>

      {/* Summary Cards */}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {INVENTORY_SUMMARY_CONFIG.map((item) => (
          <article key={item.label} className="pharmacy-panel p-5">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{item.label}</p>
            <p className="mt-2 text-3xl font-black" style={{ color: item.color }}>
              {numberFormatter.format(inventory.summary[item.key])}
            </p>
          </article>
        ))}
      </section>

      {/* Messages */}
      {successMessage && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 font-medium shadow-sm">
          ✓ {successMessage}
        </div>
      )}
      {errorMessage && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 font-medium shadow-sm">
          ⚠️ {errorMessage}
        </div>
      )}

      {/* Table */}
      <section className="pharmacy-panel overflow-hidden">
        <div className="flex flex-col gap-4 px-5 py-4 md:flex-row md:items-center md:justify-between pharmacy-panel-divider">
          <div>
            <h2 className="text-base font-bold text-slate-900">Daftar Inventory</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              Diperbarui {dateFormatter.format(new Date(inventory.fetchedAt))}
            </p>
          </div>
          <button
            type="button"
            className="pharmacy-button-primary pharmacy-button-primary--sky w-fit"
            onClick={() => setIsAddModalOpen(true)}
          >
            + Tambah Obat
          </button>
        </div>

        <div className="flex flex-col gap-3 px-5 py-3 pharmacy-panel-muted md:flex-row">
          <input
            type="text"
            placeholder="Cari obat atau batch..."
            className="pharmacy-input-sm flex-1"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <select 
            className="pharmacy-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option>Semua Status</option>
            <option>Kritis</option>
            <option>Hampir Habis</option>
            <option>Hampir Expired</option>
            <option>Aman</option>
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr>
                {INVENTORY_TABLE_HEADERS.map((h) => (
                  <th key={h} className="pharmacy-table-header">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={INVENTORY_TABLE_HEADERS.length} className="px-5 py-8 text-center text-slate-400">
                    Tidak ada data inventory yang sesuai.
                  </td>
                </tr>
              ) : (
                filteredItems.map((item, index) => {
                  const style = INVENTORY_STATUS_STYLE[item.status];
                  return (
                    <tr key={item.id} className="pharmacy-table-row hover:bg-slate-50 transition-colors">
                      <td className="px-5 py-3.5 font-semibold text-slate-800">{item.name}</td>
                      <td className="px-5 py-3.5 font-mono text-slate-700">{numberFormatter.format(item.stock)}</td>
                      <td className="px-5 py-3.5 text-slate-600">{item.location}</td>
                      <td className="px-5 py-3.5 text-slate-600">{item.batch}</td>
                      <td className="px-5 py-3.5 text-slate-600">{item.expiry}</td>
                      <td className="px-5 py-3.5">
                        <span
                          className="inline-flex items-center justify-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold border w-[120px]"
                          style={{ color: style.text, background: style.bg, borderColor: style.border }}
                        >
                          <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: style.dot }} />
                          <span className="truncate">{item.status}</span>
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => {
                              if (setSelectedBatch && setIsEditModalOpen) {
                                setSelectedBatch(item);
                                setIsEditModalOpen(true);
                              }
                            }}
                            className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-200"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => {
                              if (onDeleteStock && window.confirm(`Hapus batch ${item.batch} untuk obat ${item.name}?`)) {
                                onDeleteStock(item.id);
                              }
                            }}
                            className="rounded-lg bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-100"
                          >
                            Hapus
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Modal Tambah Stok */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-900">Tambah Obat / Stok</h3>
              <button 
                onClick={() => setIsAddModalOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-semibold text-slate-700">Nama Obat</label>
                <input
                  type="text"
                  required
                  placeholder="Ketik nama obat (baru / lama)..."
                  className="pharmacy-input w-full"
                  value={formData.nama_obat}
                  onChange={(e) => setFormData({...formData, nama_obat: e.target.value})}
                  list="medicine-list"
                />
                <datalist id="medicine-list">
                  {medicineList?.map(m => (
                    <option key={m.nama_obat} value={m.nama_obat} />
                  ))}
                </datalist>
                <p className="mt-1 text-xs text-slate-500">Jika nama belum ada, sistem akan mendaftarkannya sebagai Master Obat baru.</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-semibold text-slate-700">Nomor Batch</label>
                  <input
                    type="text"
                    required
                    className="pharmacy-input w-full"
                    value={formData.batch_no}
                    onChange={(e) => setFormData({...formData, batch_no: e.target.value})}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-semibold text-slate-700">Tanggal Kadaluarsa</label>
                  <input
                    type="date"
                    required
                    className="pharmacy-input w-full"
                    value={formData.expiry_date}
                    onChange={(e) => setFormData({...formData, expiry_date: e.target.value})}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-semibold text-slate-700">Jumlah Stok</label>
                  <input
                    type="number"
                    min="1"
                    required
                    className="pharmacy-input w-full"
                    value={formData.stock_qty || ""}
                    onChange={(e) => setFormData({...formData, stock_qty: parseInt(e.target.value) || 0})}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-semibold text-slate-700">Satuan (Unit)</label>
                  <select
                    className="pharmacy-select w-full"
                    value={formData.unit}
                    onChange={(e) => setFormData({...formData, unit: e.target.value})}
                  >
                    <option value="Box">Box</option>
                    <option value="Botol">Botol</option>
                    <option value="Strip">Strip</option>
                    <option value="Tablet">Tablet</option>
                    <option value="Kapsul">Kapsul</option>
                    <option value="Ampul">Ampul</option>
                  </select>
                </div>
              </div>

              <div className="mt-6 flex justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="rounded-xl px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100"
                  disabled={isSubmitting}
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-xl bg-sky-600 px-6 py-2 text-sm font-bold text-white shadow-sm hover:bg-sky-700 disabled:opacity-50"
                >
                  {isSubmitting ? "Menyimpan..." : "Simpan Stok"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Edit Stok */}
      {isEditModalOpen && selectedBatch && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-900">Edit Stok Obat</h3>
              <button 
                onClick={() => setIsEditModalOpen && setIsEditModalOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>
            
            <form onSubmit={handleEditSubmit} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-semibold text-slate-700">Nama Obat</label>
                <input
                  type="text"
                  disabled
                  value={selectedBatch.name}
                  className="pharmacy-input w-full bg-slate-100 text-slate-500 cursor-not-allowed"
                />
                <p className="mt-1 text-xs text-slate-500">Nama obat tidak bisa diubah. Jika salah input, hapus batch ini dan buat ulang.</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-semibold text-slate-700">Nomor Batch</label>
                  <input
                    type="text"
                    required
                    className="pharmacy-input w-full"
                    value={editFormData.batch_no}
                    onChange={(e) => setEditFormData({...editFormData, batch_no: e.target.value})}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-semibold text-slate-700">Tanggal Kadaluarsa</label>
                  <input
                    type="date"
                    required
                    className="pharmacy-input w-full"
                    value={editFormData.expiry_date}
                    onChange={(e) => setEditFormData({...editFormData, expiry_date: e.target.value})}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-semibold text-slate-700">Jumlah Stok</label>
                  <input
                    type="number"
                    min="1"
                    required
                    className="pharmacy-input w-full"
                    value={editFormData.stock_qty || ""}
                    onChange={(e) => setEditFormData({...editFormData, stock_qty: parseInt(e.target.value) || 0})}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-semibold text-slate-700">Satuan (Unit)</label>
                  <select
                    className="pharmacy-select w-full"
                    value={editFormData.unit}
                    onChange={(e) => setEditFormData({...editFormData, unit: e.target.value})}
                  >
                    <option value="Box">Box</option>
                    <option value="Botol">Botol</option>
                    <option value="Strip">Strip</option>
                    <option value="Tablet">Tablet</option>
                    <option value="Kapsul">Kapsul</option>
                    <option value="Ampul">Ampul</option>
                  </select>
                </div>
              </div>

              <div className="mt-6 flex justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsEditModalOpen && setIsEditModalOpen(false)}
                  className="rounded-xl px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100"
                  disabled={isSubmitting}
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-xl bg-violet-600 px-6 py-2 text-sm font-bold text-white shadow-sm hover:bg-violet-700 disabled:opacity-50"
                >
                  {isSubmitting ? "Menyimpan..." : "Simpan Perubahan"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
