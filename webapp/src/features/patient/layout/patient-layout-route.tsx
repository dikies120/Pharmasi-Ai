"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { routes } from "@/lib/constants/routes";

interface PatientLayoutRouteProps {
  children: ReactNode;
}

const NAV_ITEMS = [
  {
    href: routes.patientChat,
    title: "Info Obat",
    description: "Tanya AI seputar obat",
    icon: (active: boolean) => (
      <svg fill="none" viewBox="0 0 20 20" stroke={active ? "#0d9488" : "#64748b"} strokeWidth={1.8} className="h-[17px] w-[17px]">
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 5.5h12A1.5 1.5 0 0117.5 7v6A1.5 1.5 0 0116 14.5H8l-4 3v-3H4A1.5 1.5 0 012.5 13V7A1.5 1.5 0 014 5.5z" />
      </svg>
    ),
  },
  {
    href: routes.patientReminder,
    title: "Reminder Obat",
    description: "Atur jadwal minum obat",
    icon: (active: boolean) => (
      <svg fill="none" viewBox="0 0 20 20" stroke={active ? "#0d9488" : "#64748b"} strokeWidth={1.8} className="h-[17px] w-[17px]">
        <circle cx="10" cy="10" r="7.5" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M10 6v4l2.5 2.5" />
      </svg>
    ),
  },
];

const dayFormatter = new Intl.DateTimeFormat("id-ID", {
  weekday: "short",
  day: "2-digit",
  month: "short",
  year: "numeric",
});

export function PatientLayoutRoute({ children }: PatientLayoutRouteProps) {
  const [user, setUser] = useState({ name: "", email: "" });
  const [ready, setReady] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [hasSimrs, setHasSimrs] = useState(true);
  const drawerRef = useRef<HTMLDivElement>(null);
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => { setDrawerOpen(false); }, [pathname]);

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
      const stored = sessionStorage.getItem("pharmacy_user");
      if (!stored) {
        router.replace(routes.auth as Parameters<typeof router.replace>[0]);
        return;
      }
      const parsed = JSON.parse(stored);
      const role = parsed.role as string | undefined | null;

      // Hanya patient boleh masuk halaman ini
      if (role === "pharmacist") {
        router.replace(routes.pharmacy as Parameters<typeof router.replace>[0]);
        return;
      }
      if (role === "admin") {
        router.replace(routes.admin as Parameters<typeof router.replace>[0]);
        return;
      }
      if (role !== "patient") {
        // Role tidak dikenal atau kosong → ke auth
        router.replace(routes.auth as Parameters<typeof router.replace>[0]);
        return;
      }
      // "patient" → boleh masuk
      setUser({ name: parsed.name || "", email: parsed.email || "" });
      
      if (parsed.nik) {
        fetch(`${routes.api.health.replace('/health', '')}/simrs/${parsed.nik}`)
          .then(res => {
            if (!res.ok) setHasSimrs(false);
          })
          .catch(() => setHasSimrs(false));
      } else {
        setHasSimrs(false);
      }
      
      setReady(true);
    } catch {
      router.replace(routes.auth as Parameters<typeof router.replace>[0]);
    }
  }, [router]);

  function handleLogout() {
    sessionStorage.removeItem("pharmacy_user");
    // Hapus semua history chat pasien agar pasien berikutnya mulai dari awal
    const keysToRemove: string[] = [];
    for (let i = 0; i < sessionStorage.length; i++) {
      const key = sessionStorage.key(i);
      if (key && key.startsWith("patient_chat_")) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach((k) => sessionStorage.removeItem(k));
    window.location.assign(routes.auth);
  }

  const userLabel = user.name || "Pasien";
  const userEmail = user.email || "-";
  const userInitial = userLabel.slice(0, 1).toUpperCase();
  const todayLabel = dayFormatter.format(new Date());

  const SidebarContent = () => (
    <>
      {/* Logo — selaras dengan apoteker */}
      <div className="px-6 pb-5 pt-6">
        <Link href={routes.patientChat} className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-teal-600 to-emerald-500 text-sm font-black text-white">
            Rx
          </div>
          <div>
            <p className="text-xl font-extrabold tracking-tight text-slate-900">PharmaCare</p>
            <p className="text-xs text-slate-500">Portal Pasien</p>
          </div>
        </Link>
      </div>

      {/* Nav */}
      <div className="flex-1 overflow-y-auto px-4 pb-6">
        <p className="px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">Menu</p>
        <nav className="mt-3 space-y-1.5">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            const isReminder = item.href === routes.patientReminder;
            const locked = isReminder && !hasSimrs;

            if (locked) {
              return (
                <div
                  key={item.href}
                  title="Fitur terkunci karena tidak ada riwayat medis SIM RS"
                  className="group flex cursor-not-allowed items-center gap-3 rounded-xl border border-transparent px-3 py-2.5 opacity-50 transition-all duration-150"
                >
                  <span className="shrink-0">{item.icon(false)}</span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-slate-500">
                      {item.title}
                    </p>
                    <p className="mt-0.5 truncate text-[11px] text-slate-400">
                      Terkunci (Butuh Rekam Medis)
                    </p>
                  </div>
                  <svg fill="currentColor" viewBox="0 0 20 20" className="h-3.5 w-3.5 text-slate-400">
                    <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" />
                  </svg>
                </div>
              );
            }

            return (
              <Link
                key={item.href}
                href={item.href}
                className="group flex items-center gap-3 rounded-xl border px-3 py-2.5 transition-all duration-150"
                style={
                  active
                    ? { borderColor: "#99f6e4", background: "#f0fdfa" }
                    : { borderColor: "transparent", background: "transparent" }
                }
              >
                <span className="shrink-0">{item.icon(active)}</span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold" style={{ color: active ? "#0f766e" : "#334155" }}>
                    {item.title}
                  </p>
                  <p className="mt-0.5 truncate text-[11px]" style={{ color: active ? "#14b8a6" : "#64748b" }}>
                    {item.description}
                  </p>
                </div>
                {active && <span className="h-1.5 w-1.5 rounded-full bg-teal-500" />}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* User card + Logout */}
      <div className="border-t border-slate-200 px-4 py-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-600 text-sm font-bold text-white">
              {userInitial}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-slate-900">{userLabel}</p>
              <p className="truncate text-xs text-slate-500">{userEmail}</p>
            </div>
          </div>
          <div className="mt-3">
            <button
              onClick={handleLogout}
              className="inline-flex w-full items-center justify-center rounded-xl border border-slate-600 bg-slate-700/80 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-600"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </>
  );

  // Jangan render konten sampai auth check selesai — cegah flash sebelum redirect
  if (!ready) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-teal-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <main className="h-screen overflow-hidden bg-[#f3f6fb] text-slate-900">
      <div className="flex h-full">

        {/* Desktop Sidebar */}
        <aside className="hidden h-full w-[278px] shrink-0 flex-col border-r border-slate-200 bg-[#f8fafc] lg:flex">
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
          <header className="shrink-0 border-b border-slate-200 bg-white/90 backdrop-blur-lg">
            <div className="flex items-center gap-3 px-4 py-3 lg:px-7">

              {/* Hamburger — mobile only */}
              <button
                type="button"
                onClick={() => setDrawerOpen(true)}
                className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-slate-200 bg-white text-slate-600 transition-colors hover:bg-slate-50 lg:hidden"
                aria-label="Open menu"
              >
                <svg fill="none" viewBox="0 0 20 20" stroke="currentColor" strokeWidth={1.8} className="h-5 w-5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 5h14M3 10h14M3 15h14" />
                </svg>
              </button>

              <div className="flex-1" />

              {/* Date badge */}
              <div className="hidden md:flex items-center gap-2 rounded-xl border border-teal-100 bg-teal-50 px-3 py-1.5 shrink-0">
                <div className="h-2 w-2 rounded-full bg-teal-500" />
                <p className="text-xs font-bold text-teal-700 whitespace-nowrap">{todayLabel}</p>
              </div>

              {/* User pill */}
              <div className="flex shrink-0 items-center gap-2 rounded-full border border-slate-200 bg-white px-2 py-1.5">
                <div className="grid h-7 w-7 place-items-center rounded-full bg-teal-600 text-xs font-bold text-white">
                  {userInitial}
                </div>
                <div className="hidden sm:block">
                  <p className="max-w-[120px] truncate text-sm font-semibold text-slate-900">{userLabel}</p>
                  <p className="max-w-[120px] truncate text-[11px] text-slate-500">{userEmail}</p>
                </div>
              </div>
            </div>
          </header>

          {/* Content */}
          <section className="flex-1 overflow-y-auto px-4 py-5 lg:px-7 lg:py-6">
            {children}
          </section>
        </div>
      </div>
    </main>
  );
}
