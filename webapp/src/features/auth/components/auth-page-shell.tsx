import { PharmacyAuthCard } from "@/features/auth/components/pharmacy-auth-card";


export function AuthPageShell() {
  return (
    <main className="relative isolate flex flex-1 overflow-hidden bg-slate-50">
      <div className="pointer-events-none absolute -left-24 top-8 h-72 w-72 rounded-full bg-emerald-200/70 blur-3xl" />
      <div className="pointer-events-none absolute right-[-80px] top-1/3 h-72 w-72 rounded-full bg-teal-200/70 blur-3xl" />

      <div className="mx-auto grid w-full max-w-7xl gap-10 px-6 py-14 md:grid-cols-[1.1fr_1fr] md:px-10 md:py-20">
        <section className="flex flex-col justify-center">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-teal-700">
            Sistem Cerdas PharmaCare
          </p>
          <h1 className="mt-4 text-4xl font-semibold leading-tight tracking-tight text-slate-900 md:text-5xl">
            Selamat Datang
            <br />
            di Portal Terpadu
          </h1>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-slate-600 md:text-lg">
            Silakan masuk atau daftar untuk mengakses seluruh layanan kesehatan, manajemen rekam medis, dan ekosistem farmasi cerdas Anda.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <span className="inline-flex items-center rounded-xl border border-teal-100 bg-teal-50 px-4 py-2 text-sm font-medium text-teal-700">
              Keamanan Data Terenkripsi
            </span>
          </div>
        </section>

        <section className="flex items-center">
          <PharmacyAuthCard />
        </section>
      </div>
    </main>
  );
}
