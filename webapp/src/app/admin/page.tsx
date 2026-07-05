import { AdminLayoutRoute } from "@/features/admin/layout/admin-layout-route";
import { AdminDashboardRoute } from "@/features/admin/dashboard/admin-dashboard-route";

export default function AdminPage() {
  return (
    <AdminLayoutRoute>
      <AdminDashboardRoute />
    </AdminLayoutRoute>
  );
}
