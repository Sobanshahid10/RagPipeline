import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { AppLayout } from "@/components/AppLayout";

export const metadata: Metadata = {
  title: "Nexus RAG — Multitenant Agentic RAG Platform",
  description: "Streaming Chat UI, Layout-Aware PDF Viewer & Real-Time Live Citation Highlighting",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <AppLayout>{children}</AppLayout>
        </AuthProvider>
      </body>
    </html>
  );
}
