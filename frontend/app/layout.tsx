import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { ToastProvider } from "@/context/ToastContext";
import { AppLayout } from "@/components/AppLayout";

export const metadata: Metadata = {
  title: "Nexus RAG — Production Multitenant Agentic RAG Platform",
  description: "Enterprise RAG with Streaming Chat, Layout-Aware PDF Highlighting & Verifiable Bounding-Box Grounding",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>
        <AuthProvider>
          <ToastProvider>
            <AppLayout>{children}</AppLayout>
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
