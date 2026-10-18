import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { ToastProvider } from "@/context/ToastContext";
import { AppLayout } from "@/components/AppLayout";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://rag-pipeline.internal";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Nexus RAG — Production Multitenant Agentic RAG Platform",
    template: "%s | Nexus RAG",
  },
  description:
    "Enterprise Multitenant RAG Platform featuring PostgreSQL pgvector, GraphRAG recursive traversal, SSE streaming chat, and layout-aware bounding-box grounding.",
  keywords: [
    "RAG",
    "Retrieval-Augmented Generation",
    "PostgreSQL",
    "pgvector",
    "GraphRAG",
    "Agentic RAG",
    "Document Citations",
  ],
  authors: [{ name: "Nexus Engineering Team" }],
  openGraph: {
    title: "Nexus RAG — Production Multitenant Agentic RAG Platform",
    description:
      "Enterprise Multitenant RAG with layout-aware document citations, GraphRAG reasoning, and verifiable evidence grounding.",
    url: siteUrl,
    siteName: "Nexus RAG Platform",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Nexus RAG — Production Multitenant Agentic RAG Platform",
    description:
      "Production Agentic RAG with PostgreSQL pgvector, GraphRAG traversal, and layout-aware PDF bounding-box inspection.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "Nexus RAG Platform",
  "applicationCategory": "BusinessApplication",
  "operatingSystem": "Web",
  "description":
    "Enterprise Multitenant Agentic RAG Platform with hybrid vector retrieval, GraphRAG traversal, and verifiable citation grounding.",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "USD",
  },
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
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body>
        <a href="#main-content" className="skip-link">
          Skip to main content
        </a>
        <AuthProvider>
          <ToastProvider>
            <AppLayout>{children}</AppLayout>
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
