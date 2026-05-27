/**
 * /admin/upload — Protected product upload page.
 * Middleware guarantees only authenticated admins reach this page.
 */

import type { Metadata } from "next";
import { AdminUploadShell } from "@/components/admin/AdminUploadShell";

export const metadata: Metadata = {
  title: "Add Product | BeHAZEL'd Admin",
  robots: "noindex, nofollow",  // never index admin pages
};

export default function AdminUploadPage() {
  return <AdminUploadShell />;
}
