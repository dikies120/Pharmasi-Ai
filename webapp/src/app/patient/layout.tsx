import type { ReactNode } from "react";
import { PatientLayoutRoute } from "@/features/patient/layout/patient-layout-route";

interface PatientLayoutProps {
  children: ReactNode;
}

export default function PatientLayout({ children }: PatientLayoutProps) {
  return <PatientLayoutRoute>{children}</PatientLayoutRoute>;
}
