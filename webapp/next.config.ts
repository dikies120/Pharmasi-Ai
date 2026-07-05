import type { NextConfig } from "next";

function getHostnameFromUrl(value: string | undefined): string | null {
  if (!value) return null;
  try { return new URL(value).hostname; } catch { return null; }
}

const allowedDevOriginsFromEnv = (process.env.NEXT_ALLOWED_DEV_ORIGINS ?? "")
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

const appUrlHost = getHostnameFromUrl(process.env.NEXT_PUBLIC_APP_URL);
const apiUrlHost = getHostnameFromUrl(process.env.NEXT_PUBLIC_API_BASE_URL);

// Semua IP/Domain yang diizinkan untuk mengakses Web (termasuk HMR)
const allowedDevOrigins = Array.from(
  new Set(
    [
      "localhost",
      "127.0.0.1",
      "10.9.23.126",
      appUrlHost,
      apiUrlHost,
      ...allowedDevOriginsFromEnv,
    ].filter((origin): origin is string => Boolean(origin)),
  ),
);

const nextConfig: NextConfig = {
  reactStrictMode: false,
  poweredByHeader: false,
  compress: true,
  typedRoutes: true, // Sesuai warning Next.js 16
  allowedDevOrigins, // Di root level untuk mencegah blokir HMR
  compiler: {
    removeConsole:
      process.env.NODE_ENV === "production" ? { exclude: ["error"] } : false,
  },
};

export default nextConfig;
