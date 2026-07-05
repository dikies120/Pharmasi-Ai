"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  PHARMACY_NAV_ITEMS,
  // PHARMACY_SUPPORT_ITEMS,
} from "@/features/pharmacy/layout/constants/navigation";
import { routes } from "@/lib/constants/routes";

function isActivePath(pathname: string, href: string): boolean {
  if (href === routes.pharmacy) {
    return pathname === href;
  }

  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavGlyph({ index, active }: { index: number; active: boolean }) {
  const className = "h-[17px] w-[17px]";
  const color = active ? "#2563eb" : "#64748b";

  if (index === 1) {
    return (
      <svg fill="none" viewBox="0 0 20 20" stroke={color} strokeWidth={1.8} className={className}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 5h12M4 10h12M4 15h8" />
        <rect x="2.5" y="2.5" width="15" height="15" rx="2" />
      </svg>
    );
  }

  if (index === 2) {
    return (
      <svg fill="none" viewBox="0 0 20 20" stroke={color} strokeWidth={1.8} className={className}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M10 2l7 3v5c0 4.2-2.6 6.9-7 8-4.4-1.1-7-3.8-7-8V5l7-3z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 10.5l1.8 1.8 3.2-3.2" />
      </svg>
    );
  }

  if (index === 3) {
    return (
      <svg fill="none" viewBox="0 0 20 20" stroke={color} strokeWidth={1.8} className={className}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 5.5h12A1.5 1.5 0 0117.5 7v6A1.5 1.5 0 0116 14.5H8l-4 3v-3H4A1.5 1.5 0 012.5 13V7A1.5 1.5 0 014 5.5z" />
      </svg>
    );
  }

  return (
    <svg fill="none" viewBox="0 0 20 20" stroke={color} strokeWidth={1.8} className={className}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 10.5L10 4l7 6.5V16a1 1 0 01-1 1H4a1 1 0 01-1-1v-5.5z" />
    </svg>
  );
}

export function PharmacyNavigation() {
  const pathname = usePathname();

  return (
    <div className="space-y-6">
      <div>
        <p className="px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">Menu</p>
        <nav className="mt-3 space-y-1.5">
          {PHARMACY_NAV_ITEMS.map((item, index) => {
            const active = isActivePath(pathname, item.href as string);

            return (
              <Link
                key={item.href}
                href={item.href}
                className="group flex items-center gap-3 rounded-xl border px-3 py-2.5 transition-all duration-150"
                style={
                  active
                    ? {
                        borderColor: "#dbe8ff",
                        background: "#eaf1ff",
                      }
                    : {
                        borderColor: "transparent",
                        background: "transparent",
                      }
                }
              >
                <span className="shrink-0">
                  <NavGlyph index={index} active={active} />
                </span>

                <div className="min-w-0 flex-1">
                  <p
                    className="truncate text-sm font-semibold"
                    style={{ color: active ? "#1e3a8a" : "#334155" }}
                  >
                    {item.title}
                  </p>
                  <p
                    className="mt-0.5 truncate text-[11px]"
                    style={{ color: active ? "#3b82f6" : "#64748b" }}
                  >
                    {item.description}
                  </p>
                </div>

                {active && <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* <div>
        <p className="px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">Support</p>
        <div className="mt-3 space-y-1.5">
          {PHARMACY_SUPPORT_ITEMS.map((item) => (
            <div
              key={item.label}
              className="flex items-center rounded-xl border border-transparent px-3 py-2 text-sm text-slate-500 transition-colors duration-150 hover:bg-slate-100"
            >
              {item.label}
            </div>
          ))}
        </div>
      </div> */}
    </div>
  );
}