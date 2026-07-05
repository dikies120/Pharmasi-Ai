import { env } from "@/lib/env";

// Backend API base URL
const BACKEND_URL = env.backendUrl;

export const routes = {
  // Frontend routes
  home: "/",
  auth: "/auth",
  // Admin routes
  admin: "/admin",
  adminLogin: "/admin/login",
  // Pharmacist routes
  pharmacy: "/pharmacy",
  pharmacyInventory: "/pharmacy/inventory",
  pharmacyValidation: "/pharmacy/validasi-obat",
  pharmacyDispensing: "/pharmacy/dispensing",
  pharmacyChat: "/pharmacy/chat",
  // Patient routes
  patient: "/patient",
  patientChat: "/patient/chat",
  patientReminder: "/patient/reminder",
  
  // Backend API routes (direct to backend)
  api: {
    auth: {
      register: `${BACKEND_URL}/api/v1/auth/register`,
      login: `${BACKEND_URL}/api/v1/auth/login`,
      changePassword: `${BACKEND_URL}/api/v1/auth/change-password`,
      logout: `${BACKEND_URL}/api/v1/auth/logout`,
    },
    admin: {
      users: `${BACKEND_URL}/api/v1/admin/users`,
      createPharmacist: `${BACKEND_URL}/api/v1/admin/users/pharmacist`,
      deleteUser: (id: string) => `${BACKEND_URL}/api/v1/admin/users/${id}`,
      updateRole: (id: string) => `${BACKEND_URL}/api/v1/admin/users/${id}/role`,
      llmStatus: `${BACKEND_URL}/api/v1/admin/llm/status`,
      dashboardStats: `${BACKEND_URL}/api/v1/admin/dashboard-stats`,
    },
    pharmacy: {
      chat: `${BACKEND_URL}/api/v1/chat/pharmacy/ask`,
      validation: `${BACKEND_URL}/api/v1/validasi-obat/`,
      queueValidation: `${BACKEND_URL}/api/v1/pharmacy/queue/validation`,
      dispensing: `${BACKEND_URL}/api/v1/dispensing/`,
      dispensingComplete: `${BACKEND_URL}/api/v1/dispensing/complete`,
      dashboard: `${BACKEND_URL}/api/v1/graph/dashboard`,
      inventory: `${BACKEND_URL}/api/v1/monitoring-stok/realtime`,
      medicines: `${BACKEND_URL}/api/v1/graph/medicines`,
    },
    patient: {
      chat: `${BACKEND_URL}/api/v1/chat/patient/ask`,
      reminder: `${BACKEND_URL}/api/v1/reminder/`,
    },
    health: `${BACKEND_URL}/api/v1/health`,
  },
} as const;
