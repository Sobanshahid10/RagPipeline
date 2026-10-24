import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { ToastProvider } from "@/context/ToastContext";
import { AppLayout } from "@/components/AppLayout";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://rag-pipeline.internal";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "RAG Pipeline — Personal RAG Project",
    template: "%s | Nexus RAG",
  },
  description:
    "A personal project exploring document chat, public-book search, and retrieval-augmented generation with FastAPI, Next.js, and PostgreSQL.",
  keywords: [
    "RAG",
    "Retrieval-Augmented Generation",
    "PostgreSQL",
    "pgvector",
    "GraphRAG",
    "Agentic RAG",
    "Document Citations",
  ],
  authors: [{ name: "Muhammad Soban" }],
  openGraph: {
    title: "RAG Pipeline — Personal RAG Project",
    description:
      "Explore document chat and a public knowledge book in a personal RAG learning project.",
    url: siteUrl,
    siteName: "Nexus RAG Platform",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "RAG Pipeline — Personal RAG Project",
    description:
      "A personal RAG project with document search, source passages, and a public knowledge book.",
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
    "A personal project exploring hybrid retrieval, document chat, and source citations.",
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
