import type { Metadata } from "next";
import { Navbar } from "@/components/navbar";
import { AuthProvider } from "@/components/providers/auth-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "TipForTea | Живая поддержка",
  description: "Платформа теплой коллективной поддержки для личных и общественных сборов.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body className="antialiased">
        <AuthProvider>
          <Navbar />
          <main className="mx-auto max-w-[1180px] px-4 py-7 md:px-8 md:py-12">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
