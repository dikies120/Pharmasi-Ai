"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { LogoutButton } from "@/features/auth/components/logout-button";
import { PharmacyNavigation } from "@/features/pharmacy/layout/components/pharmacy-navigation";
import { routes } from "@/lib/constants/routes";

interface PharmacyLayoutRouteProps {
  children: ReactNode;
}

const dayFormatter = new Intl.DateTimeFormat("id-ID", {
  weekday: "short",
  day: "2-digit",
  month: "short",
  year: "numeric",
});

export function PharmacyLayoutRoute({ children }: PharmacyLayoutRouteProps) {
  const [user, setUser] = useState({ name: "", email: "" });
  const [drawerOpen, setDrawerOpen] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);
  const pathname = usePathname();
  const router = useRouter();

  // Tutup drawer saat route berubah
  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  // Tutup drawer saat klik di luar
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (drawerRef.current && !drawerRef.current.contains(e.target as Node)) {
        setDrawerOpen(false);
      }
    }
    if (drawerOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [drawerOpen]);

  // Tutup drawer saat Escape
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") setDrawerOpen(false);
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, []);

  // Cegah scroll body saat drawer terbuka
  useEffect(() => {
    document.body.style.overflow = drawerOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [drawerOpen]);

  useEffect(() => {
    try {
      const stored = sessionStorage.getItem("pharmacy_user");
      if (stored) {
        const parsed = JSON.parse(stored);
        const role = parsed.role as string | undefined | null;
        // Hanya pharmacist boleh masuk halaman ini
        if (role === "patient") {
          router.replace(routes.patient as Parameters<typeof router.replace>[0]);
          return;
        }
        if (role === "admin") {
          router.replace(routes.admin as Parameters<typeof router.replace>[0]);
          return;
        }
        if (role !== "pharmacist") {
          // Role tidak dikenal atau kosong → ke auth
          router.replace(routes.auth as Parameters<typeof router.replace>[0]);
          return;
        }
        setUser({ name: parsed.name || "", email: parsed.email || "" });
      } else {
        router.replace(routes.auth as Parameters<typeof router.replace>[0]);
      }
    } catch {}
  }, [router]);

  const todayLabel = dayFormatter.format(new Date());
  const userLabel = user.name || "Tim Farmasi";
  const userEmail = user.email || "-";
  const userInitial = userLabel.slice(0, 1).toUpperCase();

  const SidebarContent = () => (
    <>
      {/* Logo */}
      <div className="px-6 pb-5 pt-6">
        <Link href={routes.pharmacy} className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-500 text-sm font-black text-white">
            Rx
          </div>
          <div>
            <p className="text-xl font-extrabold tracking-tight text-slate-900">Pharmasi Admin</p>
            <p className="text-xs text-slate-500">Smart Pharmacy Dashboard</p>
          </div>
        </Link>
      </div>

      {/* Nav */}
      <div className="flex-1 overflow-y-auto px-4 pb-6">
        <PharmacyNavigation />
      </div>

      {/* User card */}
      <div className="border-t border-slate-200 px-4 py-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-900 text-sm font-bold text-white">
              {userInitial}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-slate-900">{userLabel}</p>
              <p className="truncate text-xs text-slate-500">{userEmail}</p>
            </div>
          </div>
          <div className="mt-3">
            <LogoutButton />
          </div>
        </div>
      </div>
    </>
  );

  return (
    <main className="h-screen overflow-hidden bg-[#f3f6fb] text-slate-900">
      <div className="flex h-full">

        {/* ── Desktop Sidebar ── */}
        <aside className="hidden h-full w-[278px] shrink-0 flex-col border-r border-slate-200 bg-[#f8fafc] lg:flex">
          <SidebarContent />
        </aside>

        {/* ── Mobile Drawer Overlay ── */}
        {drawerOpen && (
          <div
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm lg:hidden"
            aria-hidden="true"
          />
        )}

        {/* ── Mobile Drawer Panel ── */}
        <div
          ref={drawerRef}
          className={[
            "fixed inset-y-0 left-0 z-50 flex w-[280px] flex-col border-r border-slate-200 bg-[#f8fafc] shadow-2xl transition-transform duration-300 ease-in-out lg:hidden",
            drawerOpen ? "translate-x-0" : "-translate-x-full",
          ].join(" ")}
          aria-label="Mobile navigation"
        >
          {/* Close button */}
          <button
            type="button"
            onClick={() => setDrawerOpen(false)}
            className="absolute right-3 top-3 grid h-8 w-8 place-items-center rounded-lg border border-slate-200 bg-white text-slate-500 hover:bg-slate-50"
            aria-label="Close menu"
          >
            <svg fill="none" viewBox="0 0 20 20" stroke="currentColor" strokeWidth={1.8} className="h-4 w-4">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 5l10 10M15 5L5 15" />
            </svg>
          </button>
          <SidebarContent />
        </div>

        {/* ── Main Area ── */}
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
                aria-expanded={drawerOpen}
              >
                <svg fill="none" viewBox="0 0 20 20" stroke="currentColor" strokeWidth={1.8} className="h-5 w-5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 5h14M3 10h14M3 15h14" />
                </svg>
              </button>

              {/* Search */}
              <div className="relative min-w-0 flex-1 max-w-2xl">
                <svg className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.9}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
                </svg>
                <input
                  type="text"
                  placeholder="Search or type command..."
                  className="w-full rounded-xl border border-slate-200 bg-[#f8fafc] py-2 pl-10 pr-20 text-sm text-slate-700 outline-none transition focus:border-blue-300"
                />
                <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded-md border border-slate-200 bg-white px-2 py-0.5 text-[11px] text-slate-500 hidden sm:block">
                  Ctrl K
                </span>
              </div>

              {/* Spacer */}
              <div className="hidden sm:block flex-1" />

              {/* Date badge */}
              <div className="hidden md:flex items-center gap-2 rounded-xl border border-blue-100 bg-blue-50 px-3 py-1.5 shrink-0">
                <div className="h-2 w-2 rounded-full bg-blue-500" />
                <p suppressHydrationWarning className="text-xs font-bold text-blue-700 whitespace-nowrap">
                  <span className="text-blue-400 font-semibold">Test</span> · {todayLabel}
                </p>
              </div>

              {/* User */}
              <div className="flex shrink-0 items-center gap-2 rounded-full border border-slate-200 bg-white px-2 py-1.5">
                <div className="grid h-7 w-7 place-items-center rounded-full bg-blue-600 text-xs font-bold text-white">
                  {userInitial}
                </div>
                <div className="hidden sm:block">
                  <p className="text-sm font-semibold text-slate-900 max-w-[120px] truncate">{userLabel}</p>
                  <p className="text-[11px] text-slate-500 max-w-[120px] truncate">{userEmail}</p>
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
