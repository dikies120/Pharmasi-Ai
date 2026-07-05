"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";
import { Card } from "@/components/ui/card";
import {
  AuthApiError,
  changePassword,
  loginUser,
  registerUser,
} from "@/features/auth/lib/auth-api";
import { routes } from "@/lib/constants/routes";

type AuthMode = "login" | "register";

type AuthFormState = {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
  nik: string;
};

type ChangePasswordFormState = {
  email: string;
  newPassword: string;
  confirmNewPassword: string;
};

const initialFormState: AuthFormState = {
  name: "",
  email: "",
  password: "",
  confirmPassword: "",
  nik: "",
};

const initialChangePasswordFormState: ChangePasswordFormState = {
  email: "",
  newPassword: "",
  confirmNewPassword: "",
};

const modeLabel: Record<AuthMode, string> = {
  login: "Login",
  register: "Daftar",
};

export function PharmacyAuthCard() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const modeParam = searchParams.get("mode");

  const [mode, setMode] = useState<AuthMode>(
    modeParam === "register" ? "register" : "login",
  );
  const [form, setForm] = useState<AuthFormState>(initialFormState);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmNewPassword, setShowConfirmNewPassword] = useState(false);
  const [changePasswordForm, setChangePasswordForm] = useState<ChangePasswordFormState>(
    initialChangePasswordFormState,
  );

  useEffect(() => {
    const resolvedMode = modeParam === "register" ? "register" : "login";
    setMode(resolvedMode);
    setError(null);
    setErrorStatus(null);
    setShowChangePassword(false);
    setChangePasswordForm(initialChangePasswordFormState);
    if (resolvedMode === "register") {
      setSuccess(null);
    }
  }, [modeParam]);

  const heading = useMemo(
    () => (mode === "login" ? "Masuk ke Akun Anda" : "Buat Akun Pasien"),
    [mode],
  );

  function updateField(field: keyof AuthFormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateChangePasswordField(field: keyof ChangePasswordFormState, value: string) {
    setChangePasswordForm((current) => ({ ...current, [field]: value }));
  }

  function openChangePasswordForm() {
    setShowChangePassword(true);
    setError(null);
    setErrorStatus(null);
    setSuccess(null);
    setChangePasswordForm({
      email: form.email.trim().toLowerCase(),
      newPassword: "",
      confirmNewPassword: "",
    });
  }

  function closeChangePasswordForm() {
    setShowChangePassword(false);
    setChangePasswordForm(initialChangePasswordFormState);
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (isSubmitting) return;

    setError(null);
    setErrorStatus(null);
    setSuccess(null);
    setShowChangePassword(false);

    const name = form.name.trim();
    const email = form.email.trim().toLowerCase();

    if (mode === "register" && form.password !== form.confirmPassword) {
      setError("Konfirmasi password tidak sama.");
      return;
    }

    setIsSubmitting(true);

    try {
      if (mode === "login") {
        const result = await loginUser({ email, password: form.password });

        if (result.user) {
          // Simpan user info + access_token di sessionStorage (per-tab, tidak berbagi antar tab)
          sessionStorage.setItem(
            "pharmacy_user",
            JSON.stringify({
              ...result.user,
              access_token: result.access_token,
            }),
          );
        }

        setForm((c) => ({ ...c, password: "", confirmPassword: "" }));

        // Redirect berdasarkan role
        const role = result.user?.role;
        if (role === "admin") {
          window.location.assign(routes.admin);
        } else if (role === "pharmacist") {
          window.location.assign(routes.pharmacy);
        } else {
          // patient ke halaman pasien
          window.location.assign(routes.patient);
        }
        return;
      } else {
        // Register selalu sebagai pasien — apoteker dibuat oleh admin
        const result = await registerUser({ name, email, password: form.password, nik: form.nik });
        setSuccess(`${result.message} Silakan login untuk melanjutkan.`);
        setForm((c) => ({ ...c, name: "", password: "", confirmPassword: "", nik: "" }));
        router.replace(routes.auth);
      }
    } catch (requestError) {
      let message = "Terjadi kesalahan saat autentikasi.";
      if (requestError instanceof AuthApiError) {
        setErrorStatus(requestError.status);
        message = requestError.message;
      } else if (requestError instanceof Error) {
        message = requestError.message;
      }
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleChangePasswordSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (isSubmitting) return;

    const email = changePasswordForm.email.trim().toLowerCase();

    if (changePasswordForm.newPassword !== changePasswordForm.confirmNewPassword) {
      setError("Konfirmasi password baru tidak sama.");
      setErrorStatus(400);
      return;
    }

    setError(null);
    setErrorStatus(null);
    setSuccess(null);
    setIsSubmitting(true);

    try {
      const result = await changePassword({
        email,
        new_password: changePasswordForm.newPassword,
      });
      setSuccess(result.message);
      setForm((c) => ({ ...c, email, password: "", confirmPassword: "" }));
      closeChangePasswordForm();
    } catch (requestError) {
      let message = "Terjadi kesalahan saat mengganti password.";
      if (requestError instanceof AuthApiError) {
        setErrorStatus(requestError.status);
        message = requestError.message;
      } else if (requestError instanceof Error) {
        message = requestError.message;
      }
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  const inputCls =
    "mt-2 w-full rounded-xl border border-teal-100 bg-white px-4 py-3 text-sm outline-none ring-teal-200 transition focus:border-teal-400 focus:ring-4";

  return (
    <Card className="relative w-full overflow-hidden border-teal-200/70 bg-white/90 p-0 shadow-xl backdrop-blur-sm">
      <div className="pointer-events-none absolute -right-20 -top-20 h-56 w-56 rounded-full bg-teal-200/60 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-24 -left-20 h-64 w-64 rounded-full bg-emerald-200/50 blur-3xl" />

      <div className="relative p-8 md:p-10">
        {/* Tab Login / Daftar */}
        <div className="mb-8 flex flex-col gap-5">
          <div className="inline-flex w-fit rounded-full border border-teal-100 bg-teal-50 p-1">
            {(Object.keys(modeLabel) as AuthMode[]).map((item) => {
              const active = item === mode;
              const href =
                item === "register"
                  ? { pathname: routes.auth, query: { mode: "register" } }
                  : routes.auth;
              return (
                <Link
                  key={item}
                  href={href as any}
                  className={[
                    "rounded-full px-4 py-2 text-center text-sm font-semibold transition",
                    active ? "bg-teal-700 text-white" : "text-teal-700 hover:bg-teal-100",
                  ].join(" ")}
                >
                  {modeLabel[item]}
                </Link>
              );
            })}
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">
              PharmaCare
            </p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900 md:text-3xl">
              {heading}
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              {mode === "login"
                ? "Masuk untuk mengakses layanan farmasi Anda."
                : "Daftarkan diri sebagai pasien untuk mulai menggunakan layanan."}
            </p>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === "register" && (
            <>
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Nomor Induk Kependudukan (NIK)</span>
                <input
                  type="text"
                  required
                  maxLength={16}
                  value={form.nik}
                  onChange={(e) => {
                    const val = e.target.value.replace(/\D/g, '').slice(0, 16);
                    updateField("nik", val);
                  }}
                  className={inputCls}
                  placeholder="16 Digit NIK Anda"
                />
              </label>

              <label className="block">
                <span className="text-sm font-medium text-slate-700">Nama Lengkap</span>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => updateField("name", e.target.value)}
                  className={inputCls}
                  placeholder="Contoh: Budi Santoso"
                />
              </label>
            </>
          )}

          <label className="block">
            <span className="text-sm font-medium text-slate-700">Email</span>
            <input
              type="email"
              required
              autoComplete="email"
              value={form.email}
              onChange={(e) => updateField("email", e.target.value)}
              className={inputCls}
              placeholder="email@contoh.com"
            />
          </label>

          <div className="block">
            <span className="text-sm font-medium text-slate-700">Password</span>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                required
                minLength={8}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                value={form.password}
                onChange={(e) => updateField("password", e.target.value)}
                className={`${inputCls} pr-10`}
                placeholder="Minimal 8 karakter"
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

          {mode === "register" && (
            <div className="block">
              <span className="text-sm font-medium text-slate-700">Konfirmasi Password</span>
              <div className="relative">
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  required
                  minLength={8}
                  autoComplete="new-password"
                  value={form.confirmPassword}
                  onChange={(e) => updateField("confirmPassword", e.target.value)}
                  className={`${inputCls} pr-10`}
                  placeholder="Ulangi password"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 mt-[3px]"
                >
                  {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <p>{error}</p>
              {mode === "login" && errorStatus === 401 && (
                <button
                  type="button"
                  onClick={openChangePasswordForm}
                  className="mt-3 inline-flex rounded-lg border border-red-300 bg-white px-3 py-1.5 text-xs font-semibold text-red-700 transition hover:bg-red-100"
                >
                  Ganti password
                </button>
              )}
              {mode === "login" && errorStatus === 404 && (
                <Link
                  href={{ pathname: routes.auth, query: { mode: "register" } } as any}
                  className="mt-3 inline-flex rounded-lg border border-red-300 bg-white px-3 py-1.5 text-xs font-semibold text-red-700 transition hover:bg-red-100"
                >
                  Daftar sekarang
                </Link>
              )}
            </div>
          )}

          {success && (
            <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              {success}
            </p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-2 inline-flex w-full items-center justify-center rounded-xl bg-teal-700 px-4 py-3 text-sm font-semibold text-white transition hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Memproses..." : mode === "login" ? "Masuk" : "Daftar Sekarang"}
          </button>
        </form>

        {/* Ganti Password */}
        {showChangePassword && mode === "login" && (
          <section className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-4">
            <p className="text-sm font-semibold text-amber-900">Ganti password</p>
            <p className="mt-1 text-xs text-amber-800">
              Masukkan email terdaftar dan password baru, lalu login kembali.
            </p>
            <form onSubmit={handleChangePasswordSubmit} className="mt-4 space-y-3">
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Email</span>
                <input
                  type="email"
                  required
                  autoComplete="email"
                  value={changePasswordForm.email}
                  onChange={(e) => updateChangePasswordField("email", e.target.value)}
                  className={inputCls}
                  placeholder="email@contoh.com"
                />
              </label>
              <div className="block">
                <span className="text-sm font-medium text-slate-700">Password Baru</span>
                <div className="relative">
                  <input
                    type={showNewPassword ? "text" : "password"}
                    required
                    minLength={8}
                    autoComplete="new-password"
                    value={changePasswordForm.newPassword}
                    onChange={(e) => updateChangePasswordField("newPassword", e.target.value)}
                    className={`${inputCls} pr-10`}
                    placeholder="Minimal 8 karakter"
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 mt-[3px]"
                  >
                    {showNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>
              <div className="block">
                <span className="text-sm font-medium text-slate-700">Konfirmasi Password Baru</span>
                <div className="relative">
                  <input
                    type={showConfirmNewPassword ? "text" : "password"}
                    required
                    minLength={8}
                    autoComplete="new-password"
                    value={changePasswordForm.confirmNewPassword}
                    onChange={(e) => updateChangePasswordField("confirmNewPassword", e.target.value)}
                    className={`${inputCls} pr-10`}
                    placeholder="Ulangi password baru"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmNewPassword(!showConfirmNewPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 mt-[3px]"
                  >
                    {showConfirmNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>
              <div className="flex flex-wrap gap-2 pt-1">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="inline-flex items-center justify-center rounded-xl bg-amber-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-amber-700 disabled:opacity-60"
                >
                  {isSubmitting ? "Memproses..." : "Simpan Password Baru"}
                </button>
                <button
                  type="button"
                  onClick={closeChangePasswordForm}
                  disabled={isSubmitting}
                  className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:opacity-60"
                >
                  Batal
                </button>
              </div>
            </form>
          </section>
        )}
      </div>
    </Card>
  );
}
