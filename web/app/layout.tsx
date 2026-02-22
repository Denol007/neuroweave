import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { AuthProvider } from "@/lib/auth-context";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
const jetbrains = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "NeuroWeave — Technical Knowledge Base",
  description:
    "Structured technical knowledge extracted from Discord communities. Search solutions, code snippets, and debugging guides.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrains.variable}`}>
      <body className="min-h-screen bg-bg font-sans text-white antialiased">
        <AuthProvider>
          <Navbar />
          <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
          <Footer />
        </AuthProvider>
      </body>
    </html>
  );
}
