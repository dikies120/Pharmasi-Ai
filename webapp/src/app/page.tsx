import { redirect } from "next/navigation";
import { routes } from "@/lib/constants/routes";

export default async function Home() {
  // Redirect ke auth page
  // TODO: Implement proper session check via backend API
  redirect(routes.auth);
}