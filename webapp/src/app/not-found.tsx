import Link from "next/link";
import { routes } from "@/lib/constants/routes";

export default function NotFound() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 items-center px-6 py-16 md:px-10">
      <div className="w-full rounded-2xl border border-surface-border bg-surface p-6 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          404
        </p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">
          Halaman tidak ditemukan
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          URL yang kamu akses tidak tersedia di struktur routing aplikasi ini.
        </p>
        <Link
          href={routes.home}
          className="mt-5 inline-flex rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700"
        >
          Kembali ke Beranda
        </Link>
      </div>
    </main>
  );
}
