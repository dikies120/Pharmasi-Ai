export interface HomeSection {
  title: string;
  description: string;
  path: string;
}

export const homeSections: HomeSection[] = [
  {
    title: "Routing Layer",
    description:
      "Route files and page boundaries stay in src/app following App Router conventions.",
    path: "src/app",
  },
  {
    title: "Feature Layer",
    description:
      "Business modules are grouped by domain in src/features for team-scale collaboration.",
    path: "src/features",
  },
  {
    title: "Shared Layer",
    description:
      "Reusable UI, hooks, and utilities live in src/components, src/hooks, and src/lib.",
    path: "src/components | src/hooks | src/lib",
  },
  {
    title: "Server Layer",
    description:
      "Server-side services and actions are isolated under src/server for clear boundaries.",
    path: "src/server",
  },
  {
    title: "Testing Layer",
    description:
      "Unit, integration, and e2e test suites are organized in src/tests.",
    path: "src/tests",
  },
];
