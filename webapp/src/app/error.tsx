"use client";

import { useEffect } from "react";

type AppErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function Error({ error, reset }: AppErrorProps) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 items-center px-6 py-16 md:px-10">
      <div className="w-full rounded-2xl border border-red-200 bg-red-50 p-6 text-red-900 shadow-sm">
        <h1 className="text-2xl font-semibold tracking-tight">Terjadi Error</h1>
        <p className="mt-2 text-sm text-red-700">
          Aplikasi mengalami kegagalan saat memproses halaman ini.
        </p>
        <button
          type="button"
          onClick={reset}
          className="mt-5 rounded-xl bg-red-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-800"
        >
          Coba Lagi
        </button>
      </div>
    </main>
  );
}
