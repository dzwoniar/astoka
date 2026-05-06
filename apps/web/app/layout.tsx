import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin", "latin-ext"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Astoka",
  description: "Self-hosted production tool for shorts (Akademia 100k)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pl" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased dark`}>{children}</body>
    </html>
  );
}
