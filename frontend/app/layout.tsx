import type { Metadata } from "next";
import type { ReactNode } from "react";
import { DashboardShell } from "./dashboard-shell";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sephora Business Insight",
  description: "Product and customer review analytics",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body><DashboardShell>{children}</DashboardShell></body>
    </html>
  );
}
