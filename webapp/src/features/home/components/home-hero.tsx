import Link from "next/link";
import { Stack } from "@/components/shared/stack";
import { Card } from "@/components/ui/card";
import { siteConfig } from "@/config/site";
import { homeSections } from "@/features/home/lib/home-sections";
import { routes } from "@/lib/constants/routes";

export function HomeHero() {
  return (
    <Stack gap="lg" className="w-full">
      <Card className="border-accent/40 bg-white/85">
        <p className="mb-2 text-sm font-semibold uppercase tracking-wide text-accent">
          Production Blueprint
        </p>
        <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">
          {siteConfig.name}
        </h1>
        <p className="mt-3 max-w-3xl text-base text-slate-600 md:text-lg">
          Struktur ini dirancang untuk pengembangan jangka panjang: modular,
          terukur, dan jelas pemisahan concern antar layer.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            href={routes.auth}
            className="rounded-xl bg-accent px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
          >
            Login Pharmacy
          </Link>
          <Link
            href={{ pathname: routes.auth, query: { mode: "register" } }}
            className="rounded-xl border border-accent px-4 py-2 text-sm font-medium text-accent transition hover:bg-accent/10"
          >
            Register Pharmacy
          </Link>
          <a
            href={routes.api.health}
            className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
          >
            Check Health API
          </a>
          <Link
            href="https://nextjs.org/docs"
            target="_blank"
            rel="noreferrer"
            className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
          >
            Next.js Docs
          </Link>
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        {homeSections.map((section) => (
          <Card key={section.title}>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {section.path}
            </p>
            <h2 className="mt-2 text-xl font-semibold text-slate-900">
              {section.title}
            </h2>
            <p className="mt-2 text-sm text-slate-600">{section.description}</p>
          </Card>
        ))}
      </div>
    </Stack>
  );
}
