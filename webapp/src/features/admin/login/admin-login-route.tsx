"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";
import { routes } from "@/lib/constants/routes";

export function AdminLoginRoute() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Jika sudah login sebagai admin, langsung ke dashboard
  useEffect(() => {
    try {
      const stored = localStorage.getItem("admin_user");
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed.role === "admin" && parsed.access_token) {
          router.replace(routes.admin as Parameters<typeof router.replace>[0]);
        }
      }
    } catch {}
  }, [router]);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (isSubmitting) return;

    setError(null);
    setIsSubmitting(true);

    try {
      const res = await fetch(routes.api.auth.login, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
      });

      const body = await res.json().catch(() => null) as Record<string, unknown> | null;

      if (!res.ok) {
        const msg = typeof body?.detail === "string" ? body.detail : "Login gagal.";
        throw new Error(msg);
      }

      const user = body?.user as Record<string, unknown> | undefined;
      const role = user?.role as string | undefined;

      if (role !== "admin") {
        throw new Error("Akun ini bukan admin. Gunakan halaman login yang sesuai.");
      }

      // Simpan ke key terpisah khusus admin
      localStorage.setItem(
        "admin_user",
        JSON.stringify({
          id: user?.id,
          name: user?.name,
          email: user?.email,
          role: "admin",
          access_token: body?.access_token,
        }),
      );

      window.location.assign(routes.admin);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Terjadi kesalahan.");
    } finally {
      setIsSubmitting(false);
    }
  }

  const inputCls =
    "mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-violet-400 focus:ring-2 focus:ring-violet-100";

  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 via-violet-950 to-slate-900 p-4">
      {/* Background glow */}
      <div className="pointer-events-none absolute left-1/4 top-1/4 h-96 w-96 rounded-full bg-violet-600/20 blur-3xl" />
      <div className="pointer-events-none absolute bottom-1/4 right-1/4 h-96 w-96 rounded-full bg-indigo-600/20 blur-3xl" />

      <div className="relative w-full max-w-sm">
        {/* Card */}
        <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/95 shadow-2xl backdrop-blur-sm">
          {/* Top accent */}
          <div className="h-1 w-full bg-gradient-to-r from-violet-500 via-purple-500 to-indigo-500" />

          <div className="p-8">
            {/* Logo */}
            <div className="mb-8 flex flex-col items-center gap-3">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-600 text-xl font-black text-white shadow-lg">
                A
              </div>
              <div className="text-center">
                <h1 className="text-xl font-bold text-slate-900">Admin Panel</h1>
                <p className="mt-0.5 text-xs text-slate-500">PharmaCare System · Akses Terbatas</p>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Email Admin</span>
                <input
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={inputCls}
                  placeholder="email"
                />
              </label>

              <div className="block">
                <span className="text-sm font-medium text-slate-700">Password</span>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className={`${inputCls} pr-10`}
                    placeholder="password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 mt-[3px]"
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              {error && (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={isSubmitting}
                className="mt-2 w-full rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 py-3 text-sm font-semibold text-white shadow-md transition hover:from-violet-700 hover:to-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSubmitting ? "Memverifikasi..." : "Masuk sebagai Admin"}
              </button>
            </form>

            <p className="mt-6 text-center text-xs text-slate-400">
              Halaman ini hanya untuk administrator sistem.
            </p>
          </div>
        </div>

        <p className="mt-4 text-center text-xs text-white/40">
          PharmaCare © {new Date().getFullYear()}
        </p>
      </div>
    </main>
  );
}
