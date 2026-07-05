
function getEnv(key: string, defaultValue: string): string {
  return process.env[key] || defaultValue;
}

function resolveBackendUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_API_BASE_URL;

  if (explicit) {
    if (
      typeof window !== "undefined" &&
      explicit.includes("localhost")
    ) {
      const { hostname, protocol } = window.location;
      if (hostname && hostname !== "localhost" && hostname !== "127.0.0.1") {
        return `${protocol}//${hostname}:8000`;
      }
    }

    return explicit;
  }

  const appUrl = process.env.NEXT_PUBLIC_APP_URL;
  if (appUrl) {
    try {
      const parsed = new URL(appUrl);
      return `${parsed.protocol}//${parsed.hostname}:8000`;
    } catch {
      // Ignore malformed app URL.
    }
  }

  if (typeof window !== "undefined") {
    const { hostname, protocol } = window.location;
    if (hostname) {
      return `${protocol}//${hostname}:8000`;
    }
  }

  return "http://localhost:8000";
}

export const env = {
  // Backend API URL - fallback to localhost:8000
  backendUrl: resolveBackendUrl(),
  
  // App URL
  appUrl: getEnv("NEXT_PUBLIC_APP_URL", "http://localhost:3000"),
  
  // Environment
  nodeEnv: getEnv("NODE_ENV", "development"),
  isDevelopment: process.env.NODE_ENV === "development",
  isProduction: process.env.NODE_ENV === "production",
} as const;

export default env;
