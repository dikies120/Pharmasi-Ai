import type { ClinicalCheckConfig } from "@/features/pharmacy/validation/types/validation-view";

export const CLINICAL_CHECKS: ClinicalCheckConfig[] = [
  { key: "validasi_dosis", label: "Dosis" },
  { key: "screening_interaksi_obat", label: "Interaksi" },
  { key: "cek_kontraindikasi", label: "Kontraindikasi" },
  { key: "cek_alergi", label: "Alergi" },
];