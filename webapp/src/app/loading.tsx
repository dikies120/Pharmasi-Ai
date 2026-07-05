export default function Loading() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 items-center px-6 py-16 md:px-10">
      <div className="w-full rounded-2xl border border-surface-border bg-surface p-6 shadow-sm">
        <div className="h-5 w-40 animate-pulse rounded bg-slate-200" />
        <div className="mt-4 h-4 w-full animate-pulse rounded bg-slate-200" />
        <div className="mt-3 h-4 w-5/6 animate-pulse rounded bg-slate-200" />
      </div>
    </main>
  );
}
