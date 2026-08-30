import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import EnergyBeam from "@/components/EnergyBeam";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Bitcoin Analysis Dashboard",
  description: "Bitcoin price analysis with PostgreSQL data updated daily. Hosted on Railway.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        <EnergyBeam />
        <div className="relative z-10">
          {children}
        </div>
      </body>
    </html>
  );
}
