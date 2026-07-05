import type { ReactNode } from "react";
import { PharmacyLayoutRoute } from "@/features/pharmacy/layout/pharmacy-layout-route";

interface PharmacyLayoutProps {
  children: ReactNode;
}
export default function PharmacyLayout({ children }: PharmacyLayoutProps) {
  return (
    <PharmacyLayoutRoute>{children}</PharmacyLayoutRoute>
  );
}
