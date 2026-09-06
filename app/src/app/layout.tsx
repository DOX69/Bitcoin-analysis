import type { Metadata } from "next";
import { Inter, Geist } from "next/font/google";
import "./globals.css";
import { TooltipProvider } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Bitcoin Analysis Dashboard",
  description: "Explore Bitcoin price history, compare periods and currencies, and put market trends in context.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning className={cn("font-sans", geist.variable)}>
      <body className={`${inter.variable} font-sans antialiased`}>
        <div className="relative z-10">
          <TooltipProvider>{children}</TooltipProvider>
        </div>
      </body>
    </html>
  );
}
