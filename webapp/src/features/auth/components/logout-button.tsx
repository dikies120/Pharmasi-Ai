"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { routes } from "@/lib/constants/routes";

export function LogoutButton() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);

  async function onLogout() {
    if (isLoading) {
      return;
    }

    setIsLoading(true);

    try {
      await fetch(routes.api.auth.logout, {
        method: "POST",
        credentials: "include",
      });
    } finally {
      setIsLoading(false);
      // Hapus data user dari sessionStorage
      sessionStorage.removeItem("pharmacy_user");
      window.location.assign(routes.auth);
    }
  }

  return (
    <button
      type="button"
      onClick={onLogout}
      disabled={isLoading}
      className="inline-flex w-full items-center justify-center rounded-xl border border-slate-600 bg-slate-700/80 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-600 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {isLoading ? "Keluar..." : "Logout"}
    </button>
  );
}
