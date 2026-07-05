import type { Route } from "next";

export interface PharmacyNavItem {
  title: string;
  description: string;
  href: Route;
}

export interface PharmacySupportItem {
  label: string;
}

export interface PharmacyQuickLink {
  label: string;
  href: Route;
  highlighted?: boolean;
}