"use client";

import { useEffect, useState, useCallback, Suspense, useContext } from "react";
import { AdminTabContext } from "@/features/admin/layout/admin-layout-route";
import { routes } from "@/lib/constants/routes";
import { Users, UserCog, Server, CheckCircle2, Activity } from "lucide-react";

type UserRole = "admin" | "pharmacist" | "patient";

interface UserEntry {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  created_at: string | null;
}

interface CreatePharmacistForm {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
}

const ROLE_LABEL: Record<UserRole, string> = {
  admin: "Admin",
  pharmacist: "Apoteker",
  patient: "Pasien",
};

const ROLE_STYLE: Record<UserRole, string> = {
  admin: "bg-violet-100 text-violet-700",
  pharmacist: "bg-blue-100 text-blue-700",
  patient: "bg-teal-100 text-teal-700",
};

function getAuthHeader(): Record<string, string> {
  try {
    // Admin token disimpan di key terpisah "admin_user"
    const stored = localStorage.getItem("admin_user");
    if (stored) {
      const parsed = JSON.parse(stored);
      if (parsed.access_token) {
        return { Authorization: `Bearer ${parsed.access_token}` };
      }
    }
  } catch { }
  return {};
}

export function AdminDashboardPage() {
  const [users, setUsers] = useState<UserEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // LLM Status
  const [llmStatus, setLlmStatus] = useState<{ status: "on" | "off", model: string | null } | null>(null);
  const [isLlmLoading, setIsLlmLoading] = useState(true);

  // Dashboard Stats
  const [dashboardStats, setDashboardStats] = useState<{
    total_patients: number;
    active_pharmacists: number;
    validated_prescriptions: number;
    pharmacist_activities: Array<{ name: string, initials: string, status: string, time: string }>;
  } | null>(null);

  // Create pharmacist form
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createForm, setCreateForm] = useState<CreatePharmacistForm>({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createSuccess, setCreateSuccess] = useState<string | null>(null);

  // Delete confirm
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);


  // Get tab from layout context
  const { activeTab } = useContext(AdminTabContext);
  const currentTab = activeTab || 'overview';

  const [search, setSearch] = useState("");

  const fetchUsers = useCallback(async (isManualRefresh = false) => {
    if (isManualRefresh) setIsRefreshing(true);
    else setIsLoading(true);
    setFetchError(null);
    try {
      const res = await fetch(routes.api.admin.users, {
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null) as Record<string, unknown> | null;
        throw new Error(typeof body?.detail === "string" ? body.detail : "Gagal memuat data user.");
      }
      const body = await res.json() as { users: UserEntry[] };
      setUsers(body.users ?? []);
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : "Terjadi kesalahan.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  const fetchLlmStatus = useCallback(async () => {
    setIsLlmLoading(true);
    try {
      const res = await fetch(routes.api.admin.llmStatus, {
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
      });
      if (res.ok) {
        const data = await res.json();
        setLlmStatus(data);
      }
    } catch (err) {
      console.error("Failed to fetch LLM status:", err);
    } finally {
      setIsLlmLoading(false);
    }
  }, []);

  const fetchDashboardStats = useCallback(async () => {
    try {
      const res = await fetch(routes.api.admin.dashboardStats, {
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
      });
      if (res.ok) {
        const data = await res.json();
        setDashboardStats(data);
      }
    } catch (err) {
      console.error("Failed to fetch dashboard stats:", err);
    }
  }, []);

  // Layout sudah pastikan user terautentikasi sebelum render ini
  useEffect(() => { 
    fetchUsers(false); 
    fetchLlmStatus();
    fetchDashboardStats();
    
    // Refresh stats periodically
    const interval = setInterval(fetchDashboardStats, 10000);
    return () => clearInterval(interval);
  }, [fetchUsers, fetchLlmStatus, fetchDashboardStats]);

  async function handleCreatePharmacist(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (createForm.password !== createForm.confirmPassword) {
      setCreateError("Konfirmasi password tidak sama.");
      return;
    }
    setCreateError(null);
    setCreateSuccess(null);
    setIsCreating(true);
    try {
      const res = await fetch(routes.api.admin.createPharmacist, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify({
          name: createForm.name.trim(),
          email: createForm.email.trim().toLowerCase(),
          password: createForm.password,
        }),
      });
      const body = await res.json().catch(() => null) as Record<string, unknown> | null;
      if (!res.ok) {
        throw new Error(typeof body?.detail === "string" ? body.detail : "Gagal membuat akun apoteker.");
      }
      setCreateSuccess(`Akun apoteker "${createForm.name}" berhasil dibuat.`);
      setCreateForm({ name: "", email: "", password: "", confirmPassword: "" });
      setShowCreateForm(false);
      fetchUsers(false);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Terjadi kesalahan.");
    } finally {
      setIsCreating(false);
    }
  }

  async function handleDeleteUser(userId: string) {
    setDeletingId(userId);
    setDeleteError(null);
    try {
      const res = await fetch(routes.api.admin.deleteUser(userId), {
        method: "DELETE",
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
      });
      const body = await res.json().catch(() => null) as Record<string, unknown> | null;
      if (!res.ok) {
        throw new Error(typeof body?.detail === "string" ? body.detail : "Gagal menghapus user.");
      }
      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Terjadi kesalahan.");
    } finally {
      setDeletingId(null);
    }
  }



  const filteredUsers = users.filter((u) => {
    if (u.role === "admin") return false; // Hide admin
    const targetRole = currentTab === 'patient' ? 'patient' : 'pharmacist';
    const matchRole = u.role === targetRole;
    const matchSearch =
      !search ||
      u.name.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase());
    return matchRole && matchSearch;
  });

  const inputCls =
    "w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm outline-none transition focus:border-violet-400 focus:ring-2 focus:ring-violet-100";

  if (currentTab === 'overview') {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
            <p className="text-slate-500 font-medium mb-1">Total Pasien Terdaftar</p>
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-3xl font-bold text-slate-800">
                  {dashboardStats ? dashboardStats.total_patients : "-"}
                </h3>
              </div>
              <div className="h-12 w-12 rounded-full bg-indigo-50 flex items-center justify-center">
                <Users className="h-6 w-6 text-indigo-600" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
            <p className="text-slate-500 font-medium mb-1">Apoteker Aktif</p>
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-3xl font-bold text-slate-800">
                  {dashboardStats ? dashboardStats.active_pharmacists : "-"}
                </h3>
              </div>
              <div className="h-12 w-12 rounded-full bg-violet-50 flex items-center justify-center">
                <UserCog className="h-6 w-6 text-violet-600" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
            <p className="text-slate-500 font-medium mb-1">Status AI Validator</p>
            <div className="flex items-center justify-between">
              <div>
                {isLlmLoading ? (
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent mt-1" />
                ) : (
                  <>
                    <h3 className={`text-2xl font-bold flex items-center gap-2 ${llmStatus?.status === 'on' ? 'text-emerald-600' : 'text-red-600'}`}>
                      <span className={`h-2.5 w-2.5 rounded-full ${llmStatus?.status === 'on' ? 'bg-emerald-500' : 'bg-red-500'}`}></span>
                      {llmStatus?.status === 'on' ? 'Online' : 'Offline'}
                    </h3>
                    <div className="inline-block px-2 py-1 bg-slate-100 rounded text-xs text-slate-500 font-medium mt-2">
                      {llmStatus?.model || "Unknown Model"}
                    </div>
                  </>
                )}
              </div>
              <div className="h-12 w-12 rounded-full bg-emerald-50 flex items-center justify-center">
                <Server className="h-6 w-6 text-emerald-600" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
            <p className="text-slate-500 font-medium mb-1">Resep Tervalidasi</p>
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-3xl font-bold text-slate-800">
                  {dashboardStats ? dashboardStats.validated_prescriptions : "-"}
                </h3>
              </div>
              <div className="h-12 w-12 rounded-full bg-indigo-50 flex items-center justify-center relative">
                <CheckCircle2 className="h-6 w-6 text-indigo-600" />
                <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-violet-400" />
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
              <Activity className="h-5 w-5 text-indigo-500" />
              Aktivitas Apoteker Terkini
            </h2>
            <button className="text-sm font-semibold text-indigo-600 hover:text-indigo-700">
              Lihat Semua
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/50">
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Apoteker</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Status</th>
                  <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">Terakhir Online</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {dashboardStats?.pharmacist_activities && dashboardStats.pharmacist_activities.length > 0 ? (
                  dashboardStats.pharmacist_activities.map((act, i) => (
                    <tr key={i} className="group transition hover:bg-slate-50">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                            act.status === 'Online' ? 'bg-violet-100 text-violet-700' :
                            'bg-slate-100 text-slate-700'
                          }`}>
                            {act.initials}
                          </div>
                          <span className="font-semibold text-slate-700">{act.name}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium border ${
                          act.status === 'Online' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                          'bg-slate-50 text-slate-700 border-slate-200'
                        }`}>
                          <span className={`h-1.5 w-1.5 rounded-full ${
                            act.status === 'Online' ? 'bg-emerald-500' :
                            'bg-slate-500'
                          }`}></span>
                          {act.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right text-slate-500">{act.time}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={3} className="px-6 py-8 text-center text-slate-500 text-sm">
                      Belum ada data aktivitas apoteker.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Title */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">
            {currentTab === "patient" ? "Data Pasien" : "Data Apoteker"}
          </h1>
          <p className="mt-0.5 text-sm text-slate-500">
            {currentTab === "patient" ? "Manajemen akun dan akses pasien." : "Manajemen akun apoteker."}
          </p>
        </div>
        {currentTab === "pharmacist" && (
          <button
            onClick={() => { setShowCreateForm(true); setCreateError(null); setCreateSuccess(null); }}
            className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-700"
          >
            <svg fill="none" viewBox="0 0 20 20" stroke="currentColor" strokeWidth={2} className="h-4 w-4">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 4v12M4 10h12" />
            </svg>
            Tambah Apoteker
          </button>
        )}
      </div>

      {/* Create Pharmacist Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-900">Buat Akun Apoteker</h2>
                <p className="mt-0.5 text-xs text-slate-500">Akun akan langsung aktif dengan role apoteker.</p>
              </div>
              <button
                onClick={() => setShowCreateForm(false)}
                className="grid h-8 w-8 place-items-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50"
              >
                <svg fill="none" viewBox="0 0 20 20" stroke="currentColor" strokeWidth={2} className="h-4 w-4">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 5l10 10M15 5L5 15" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleCreatePharmacist} className="space-y-3">
              <label className="block">
                <span className="text-xs font-medium text-slate-700">Nama Lengkap</span>
                <input
                  type="text"
                  required
                  value={createForm.name}
                  onChange={(e) => setCreateForm((f) => ({ ...f, name: e.target.value }))}
                  className={`mt-1 ${inputCls}`}
                  placeholder="Contoh: dr. Siti Rahayu"
                />
              </label>
              <label className="block">
                <span className="text-xs font-medium text-slate-700">Email</span>
                <input
                  type="email"
                  required
                  value={createForm.email}
                  onChange={(e) => setCreateForm((f) => ({ ...f, email: e.target.value }))}
                  className={`mt-1 ${inputCls}`}
                  placeholder="apoteker@pharmacy.id"
                />
              </label>
              <label className="block">
                <span className="text-xs font-medium text-slate-700">Password</span>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={createForm.password}
                  onChange={(e) => setCreateForm((f) => ({ ...f, password: e.target.value }))}
                  className={`mt-1 ${inputCls}`}
                  placeholder="Minimal 8 karakter"
                />
              </label>
              <label className="block">
                <span className="text-xs font-medium text-slate-700">Konfirmasi Password</span>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={createForm.confirmPassword}
                  onChange={(e) => setCreateForm((f) => ({ ...f, confirmPassword: e.target.value }))}
                  className={`mt-1 ${inputCls}`}
                  placeholder="Ulangi password"
                />
              </label>

              {createError && (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700">
                  {createError}
                </div>
              )}

              <div className="flex gap-2 pt-1">
                <button
                  type="submit"
                  disabled={isCreating}
                  className="flex-1 rounded-xl bg-violet-600 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-700 disabled:opacity-60"
                >
                  {isCreating ? "Membuat..." : "Buat Akun"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="flex-1 rounded-xl border border-slate-200 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                >
                  Batal
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Success toast */}
      {createSuccess && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          ✓ {createSuccess}
        </div>
      )}
      {deleteError && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {deleteError}
        </div>
      )}

      {/* Search & Filter */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <svg className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Cari nama atau email..."
            className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-10 pr-4 text-sm outline-none transition focus:border-violet-400 focus:ring-2 focus:ring-violet-100"
          />
        </div>

        <button
          onClick={() => fetchUsers(true)}
          disabled={isRefreshing}
          className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
          title="Refresh"
        >
          {isRefreshing ? (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-violet-600 border-t-transparent" />
          ) : (
            <svg fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-4 w-4">
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
            </svg>
          )}
        </button>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <div className="flex flex-col items-center gap-3">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-violet-600 border-t-transparent" />
              <p className="text-sm text-slate-500">Memuat data user...</p>
            </div>
          </div>
        ) : fetchError ? (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <p className="text-3xl">⚠️</p>
            <p className="text-sm font-medium text-slate-700">{fetchError}</p>
            <button
              onClick={() => fetchUsers(false)}
              className="rounded-xl bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700"
            >
              Coba Lagi
            </button>
          </div>
        ) : filteredUsers.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-16 text-center">
            <p className="text-3xl">👥</p>
            <p className="text-sm font-medium text-slate-600">Tidak ada user ditemukan.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50">
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Nama</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Email</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Role</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Dibuat</th>
                  <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredUsers.map((u) => (
                  <tr key={u.id} className="group transition hover:bg-slate-50">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2.5">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-200 text-xs font-bold text-slate-600">
                          {u.name.slice(0, 1).toUpperCase()}
                        </div>
                        <span className="font-medium text-slate-900">{u.name}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 text-slate-600">{u.email}</td>
                    <td className="px-5 py-3.5">
                      <span
                        className={[
                          "inline-block rounded-full px-2.5 py-1 text-xs font-semibold w-24 text-center",
                          ROLE_STYLE[u.role],
                        ].join(" ")}
                      >
                        {ROLE_LABEL[u.role]}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-slate-500">
                      {u.created_at
                        ? new Intl.DateTimeFormat("id-ID", {
                          day: "2-digit",
                          month: "short",
                          year: "numeric",
                        }).format(new Date(u.created_at))
                        : "-"}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      {u.role !== "admin" && (
                        <button
                          onClick={() => handleDeleteUser(u.id)}
                          disabled={deletingId === u.id}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-600 transition hover:bg-red-100 disabled:opacity-50"
                        >
                          {deletingId === u.id ? (
                            "Menghapus..."
                          ) : (
                            <>
                              <svg fill="none" viewBox="0 0 20 20" stroke="currentColor" strokeWidth={1.8} className="h-3.5 w-3.5">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M6 4h8M4 6h12l-1 10H5L4 6zM8 6V4h4v2" />
                              </svg>
                              Hapus
                            </>
                          )}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Footer info */}
      <p className="text-xs text-slate-400">
        Menampilkan {filteredUsers.length} akun.
      </p>
    </div>
  );
}

export default function AdminDashboardPageWrapper() {
  return (
    <Suspense fallback={<div className="p-8">Loading...</div>}>
      <AdminDashboardPage />
    </Suspense>
  );
}
