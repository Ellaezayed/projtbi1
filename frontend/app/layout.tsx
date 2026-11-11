import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sephora Business Insight",
  description: "Product and customer review analytics",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="en"><body className="bg-white text-charcoal">{children}</body></html>;
}
