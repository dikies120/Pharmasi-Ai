/**
 * API Client - Direct connection to backend
 * No proxy, langsung ke backend API
 */

import { env } from "@/lib/env";

export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  detail?: string;
  status_code?: number;
}

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, message: string, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail || message;
  }
}

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const adminStr = localStorage.getItem("admin_user");
    if (adminStr) {
      const parsed = JSON.parse(adminStr);
      if (parsed.access_token) return parsed.access_token;
    }
    const pharmacyStr = sessionStorage.getItem("pharmacy_user");
    if (pharmacyStr) {
      const parsed = JSON.parse(pharmacyStr);
      if (parsed.access_token) return parsed.access_token;
    }
  } catch (e) {
    // skip
  }
  return null;
}

export function getAuthHeader(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Make API request to backend
 */
async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${env.backendUrl}${endpoint}`;
  const token = getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };

  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new ApiError(
        response.status,
        data.error || data.detail || "Request failed",
        data.detail
      );
    }

    return data as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    // Network error or other issues
    throw new ApiError(502, "Failed to connect to backend", String(error));
  }
}

/**
 * API Client methods
 */
export const apiClient = {
  // Auth endpoints
  auth: {
    register: (data: { name: string; email: string; password: string }) =>
      apiRequest("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    login: (data: { email: string; password: string }) =>
      apiRequest("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    changePassword: (data: { email: string; new_password: string }) =>
      apiRequest("/api/v1/auth/change-password", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  // Pharmacy endpoints (direct DB, no MCP)
  pharmacy: {
    getDashboard: () => apiRequest("/api/v1/pharmacy/dashboard"),
    getInventory: () => apiRequest("/api/v1/pharmacy/inventory/realtime"),
    getMedicines: () => apiRequest("/api/v1/pharmacy/medicines"),
    addInventoryBatch: (data: { nama_obat: string; batch_no: string; expiry_date: string; stock_qty: number; unit?: string }) =>
      apiRequest("/api/v1/pharmacy/inventory/batches", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    updateInventoryBatch: (id: string, data: { batch_no: string; expiry_date: string; stock_qty: number; unit?: string }) =>
      apiRequest(`/api/v1/pharmacy/inventory/batches/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    deleteInventoryBatch: (id: string) =>
      apiRequest(`/api/v1/pharmacy/inventory/batches/${id}`, {
        method: "DELETE",
      }),
  },

  // Chat endpoints
  chat: {
    askPharmacy: (data: { question: string; user_id?: string }) =>
      apiRequest("/api/v1/chat/pharmacy/ask", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    askPatient: (data: { question: string; user_id?: string; patient_context?: any }) =>
      apiRequest("/api/v1/chat/patient/ask", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  // Dispensing endpoints
  dispensing: {
    process: (data: { prescription_id: string; include_llm_reasoning?: boolean }) =>
      apiRequest("/api/v1/dispensing/", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    complete: (data: any) =>
      apiRequest("/api/v1/dispensing/complete", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  // Validation endpoints
  validation: {
    validate: (data: any) =>
      apiRequest("/api/v1/validasi-obat/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  // Monitoring endpoints
  monitoring: {
    getRealtimeStock: () => apiRequest("/api/v1/monitoring-stok/realtime"),
  },

  // Graph endpoints
  graph: {
    getDashboard: () => apiRequest("/api/v1/graph/dashboard"),
    getMedicines: () => apiRequest("/api/v1/graph/medicines"),
  },

  // Analytics endpoints
  analytics: {
    getInsights: () => apiRequest("/api/v1/analytics/insights"),
  },

// Health check
  health: () => apiRequest("/api/v1/health"),
};

export function handleUnauthorized() {
  if (typeof window !== "undefined") {
    const isAdmin = window.location.pathname.startsWith('/admin');
    localStorage.removeItem("admin_user");
    sessionStorage.removeItem("pharmacy_user");
    window.location.href = isAdmin ? "/admin/login" : "/auth";
  }
}

// Global fetch interceptor for catching 401 Unauthorized errors everywhere
if (typeof window !== "undefined") {
  const originalFetch = window.fetch;
  window.fetch = async function (...args) {
    const response = await originalFetch.apply(this, args);
    if (response.status === 401) {
      const currentUrl = window.location.href;
      // Jangan redirect jika kita memang sedang berada di halaman auth/login
      if (!currentUrl.includes('/auth') && !currentUrl.includes('/login')) {
        console.warn("401 Unauthorized detected globally, redirecting to login...");
        handleUnauthorized();
      }
    }
    return response;
  };
}

export default apiClient;
