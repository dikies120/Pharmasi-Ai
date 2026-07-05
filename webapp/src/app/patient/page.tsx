import { redirect } from "next/navigation";
import { routes } from "@/lib/constants/routes";

export default function PatientPage() {
  // @ts-ignore
  redirect(routes.patientChat);
}
