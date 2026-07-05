import type { Route } from "next";

import { routes } from "@/lib/constants/routes";
import type {
  PharmacyNavItem,
  PharmacyQuickLink,
  // PharmacySupportItem,
} from "@/features/pharmacy/layout/types/navigation";

export const PHARMACY_NAV_ITEMS: PharmacyNavItem[] = [
  {
    title: "Dashboard",
    description: "Ringkasan operasional apotek",
    href: routes.pharmacy as Route,
  },
  {
    title: "Inventory",
    description: "Monitoring stok real-time",
    href: routes.pharmacyInventory as Route,
  },
  {
    title: "Validasi Obat",
    description: "Safety check resep pasien",
    href: routes.pharmacyValidation as Route,
  },
  {
    title: "Dispensing",
    description: "Finalisasi serah obat",
    href: routes.pharmacyDispensing as Route,
  },
  {
    title: "Chat Assistant",
    description: "Tanya AI seputar farmasi",
    href: routes.pharmacyChat as Route,
  },
];

// export const PHARMACY_SUPPORT_ITEMS: PharmacySupportItem[] = [
//   { label: "Calendar" },
//   { label: "User Profile" },
//   { label: "Forms" },
//   { label: "Tables" },
// ];

export const PHARMACY_QUICK_LINKS: PharmacyQuickLink[] = [
  {
    label: "Dashboard",
    href: routes.pharmacy as Route,
    highlighted: true,
  },
  {
    label: "Inventory",
    href: routes.pharmacyInventory as Route,
  },
  {
    label: "Validasi",
    href: routes.pharmacyValidation as Route,
  },
  {
    label: "Dispensing",
    href: routes.pharmacyDispensing as Route,
  },
  {
    label: "Chat",
    href: routes.pharmacyChat as Route,
  },
];