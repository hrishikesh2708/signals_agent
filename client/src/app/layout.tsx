import type { Metadata } from "next";

import { AuthProvider } from "@/contexts/auth-context";

import "./globals.css";

export const metadata: Metadata = {
  title: "Signals",
  description: "Signals mapping agent dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
