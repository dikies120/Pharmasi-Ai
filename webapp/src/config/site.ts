/**
 * Site Configuration
 */

export const siteConfig = {
  name: "Pharmasi AI",
  description: "Intelligent Pharmacy Management System with AI Assistant",
  url: process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
  locale: "id-ID",
} as const;

export default siteConfig;
