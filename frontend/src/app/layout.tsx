import type { Metadata } from "next";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import "./globals.css";

export const metadata: Metadata = {
  title: "Cortex",
  description: "Agent-ready company context from connected source truth.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={cn("font-sans antialiased")}>{children}</body>
    </html>
  );
}
