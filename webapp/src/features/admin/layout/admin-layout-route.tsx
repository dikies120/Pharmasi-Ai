"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useEffect, useRef, useState, createContext, useContext } from "react";
import { usePathname, useRouter } from "next/navigation";
import { routes } from "@/lib/constants/routes";
import { Shield, Activity, Users, UserCog, LogOut, Database } from "lucide-react";

interface AdminLayoutRouteProps {
  children: ReactNode;
}

export const AdminTabContext = createContext<{
  activeTab: string;
  setActiveTab: (tab: string) => void;
}>({ activeTab: "overview", setActiveTab: () => {} });

export function AdminLayoutRoute({ children }: AdminLayoutRouteProps) {
  const [user, setUser] = useState({ name: "", email: "" });
  const [ready, setReady] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);
  const pathname = usePathname();
  const router = useRouter();

  // Instant local tab state
  const [activeTab, setActiveTab] = useState("overview");

  // Sync tab from URL on initial load only
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const tab = params.get('tab');
    if (tab) setActiveTab(tab);
  }, []);

  // Sync URL when tab changes silently
  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set('tab', activeTab);
    window.history.replaceState(null, '', url.toString());
  }, [activeTab]);

  useEffect(() => { setDrawerOpen(false); }, [pathname, activeTab]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (drawerRef.current && !drawerRef.current.contains(e.target as Node)) {
        setDrawerOpen(false);
      }
    }
    if (drawerOpen) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [drawerOpen]);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") setDrawerOpen(false);
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, []);

  useEffect(() => {
    document.body.style.overflow = drawerOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [drawerOpen]);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("admin_user");
      if (!stored) {
        router.replace(routes.adminLogin as Parameters<typeof router.replace>[0]);
        return;
      }
      const parsed = JSON.parse(stored);
      if (parsed.role !== "admin" || !parsed.access_token) {
        localStorage.removeItem("admin_user");
        router.replace(routes.adminLogin as Parameters<typeof router.replace>[0]);
        return;
      }
      setUser({ name: parsed.name || "", email: parsed.email || "" });
      setReady(true);
    } catch {
      router.replace(routes.adminLogin as Parameters<typeof router.replace>[0]);
    }
  }, [router]);

  function handleLogout() {
    localStorage.removeItem("admin_user");
    window.location.assign(routes.adminLogin);
  }

  const userLabel = user.name || "Admin";
  const userEmail = user.email || "-";
  const userInitial = userLabel.slice(0, 1).toUpperCase();

  const NAV_ITEMS = [
    {
      id: "overview",
      label: "System Overview",
      icon: Activity,
    },
    { type: "divider", label: "USER MANAGEMENT" },
    {
      id: "patient",
      label: "Data Pasien",
      icon: Users,
    },
    {
      id: "pharmacist",
      label: "Akun Apoteker",
      icon: UserCog,
    },
  ];

  const SidebarContent = () => (
    <div className="flex h-full flex-col bg-[#0f172a] text-slate-300">
      {/* Logo */}
      <div className="px-6 pb-6 pt-8">
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => setActiveTab('overview')}>
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-lg shadow-indigo-500/20">
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <p className="text-lg font-black tracking-widest text-white"><span className="font-medium">PHARMACY</span>ADMIN</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <div className="flex-1 overflow-y-auto px-4 pb-6 mt-2">
        <nav className="space-y-1">
          {NAV_ITEMS.map((item, idx) => {
            if (item.type === "divider") {
              return (
                <div key={idx} className="px-3 pt-4 pb-2">
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
                    {item.label}
                  </p>
                </div>
              );
            }

            const active = activeTab === item.id;
            const Icon = item.icon!;

            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id!)}
                className={[
                  "w-full group flex items-center gap-3 rounded-xl px-3 py-2.5 transition-all duration-150 text-left",
                  active
                    ? "bg-indigo-600/10 text-indigo-400 font-semibold"
                    : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 font-medium"
                ].join(" ")}
              >
                <Icon className={`h-5 w-5 ${active ? "text-indigo-400" : "text-slate-500 group-hover:text-slate-400"}`} />
                {item.label}
                {active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-indigo-500" />}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom Profile */}
      <div className="border-t border-slate-800 px-4 py-6">
        <div className="flex items-center gap-3 mb-6 px-2">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-800 text-sm font-bold text-white border border-slate-700">
            SA
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-bold text-white">Super Admin</p>
            <p className="truncate text-xs text-slate-500">IT Department</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-800/50 px-4 py-2.5 text-sm font-semibold text-slate-300 transition hover:bg-slate-800 hover:text-white"
        >
          <LogOut className="h-4 w-4" />
          Sign Out
        </button>
      </div>
    </div>
  );

  if (!ready) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-violet-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <main className="h-screen overflow-hidden bg-[#f3f6fb] text-slate-900">
      <div className="flex h-full">

        {/* Desktop Sidebar */}
        <aside className="hidden h-full w-[280px] shrink-0 flex-col lg:flex shadow-2xl z-10">
          <SidebarContent />
        </aside>

        {/* Mobile Drawer Overlay */}
        {drawerOpen && (
          <div className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm lg:hidden" aria-hidden="true" />
        )}

        {/* Mobile Drawer Panel */}
        <div
          ref={drawerRef}
          className={[
            "fixed inset-y-0 left-0 z-50 flex w-[280px] flex-col border-r border-slate-200 bg-[#f8fafc] shadow-2xl transition-transform duration-300 ease-in-out lg:hidden",
            drawerOpen ? "translate-x-0" : "-translate-x-full",
          ].join(" ")}
        >
          <button
            type="button"
            onClick={() => setDrawerOpen(false)}
            className="absolute right-3 top-3 grid h-8 w-8 place-items-center rounded-lg border border-slate-200 bg-white text-slate-500 hover:bg-slate-50"
          >
            <svg fill="none" viewBox="0 0 20 20" stroke="currentColor" strokeWidth={1.8} className="h-4 w-4">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 5l10 10M15 5L5 15" />
            </svg>
          </button>
          <SidebarContent />
        </div>

        {/* Main Area */}
        <div className="flex h-full min-w-0 flex-1 flex-col">

          {/* Navbar */}
          <header className="shrink-0 border-b border-slate-200 bg-white shadow-sm z-0">
            <div className="flex items-center gap-4 px-6 py-4">
              <button
                type="button"
                onClick={() => setDrawerOpen(true)}
                className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 lg:hidden"
              >
                <svg fill="none" viewBox="0 0 20 20" stroke="currentColor" strokeWidth={1.8} className="h-5 w-5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 5h14M3 10h14M3 15h14" />
                </svg>
              </button>

              <div className="flex items-center gap-3">
                {activeTab === 'overview' ? (
                  <>
                    <Activity className="h-6 w-6 text-indigo-600" />
                    <h1 className="text-xl font-bold text-slate-800">System Overview</h1>
                  </>
                ) : activeTab === 'patient' ? (
                  <>
                    <Users className="h-6 w-6 text-indigo-600" />
                    <h1 className="text-xl font-bold text-slate-800">Data Pasien</h1>
                  </>
                ) : (
                  <>
                    <UserCog className="h-6 w-6 text-indigo-600" />
                    <h1 className="text-xl font-bold text-slate-800">Akun Apoteker</h1>
                  </>
                )}
              </div>

              <div className="flex-1" />

              <div className="hidden sm:flex items-center gap-3">
                {/* Date */}
                <div className="pl-4 border-l border-slate-200">
                  <p suppressHydrationWarning className="text-sm font-medium text-slate-500">
                    {new Intl.DateTimeFormat("id-ID", { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' }).format(new Date())}
                  </p>
                </div>
              </div>
            </div>
          </header>

          {/* Content */}
          <section className="flex-1 overflow-y-auto px-4 py-6 lg:px-8 lg:py-8">
            <AdminTabContext.Provider value={{ activeTab, setActiveTab }}>
              {children}
            </AdminTabContext.Provider>
          </section>
        </div>
      </div>
    </main>
  );
}
