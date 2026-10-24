import type { Metadata } from "next";
import Link from "next/link";
import { Footer } from "@/components/Footer";

export const metadata: Metadata = {
  title: "Refund Policy — Nexus RAG Platform",
  description: "Billing and refund policy details for the Nexus RAG Platform.",
};

export default function RefundPage() {
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <div className="legal-container">
        <header className="legal-header">
          <Link
            href="/chat"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              fontSize: "13px",
              color: "var(--accent-light)",
              marginBottom: "16px",
            }}
          >
            &larr; Return to Application
          </Link>
          <h1 className="legal-title">Refund & Billing Policy</h1>
          <div className="legal-meta">
            <span>Effective Date: October 24, 2026</span>
            <span>&bull;</span>
            <span>Version: 1.1</span>
          </div>
        </header>

        <section className="legal-section">
          <h2>1. Personal Project</h2>
          <p>
            RAG Pipeline is a personal learning project. It does not offer paid subscriptions or collect payments, so there are no project subscription charges to refund.
          </p>
        </section>

        <section className="legal-section">
          <h2>2. Model Provider Costs</h2>
          <p>
            Running the project with your own API keys may incur charges from your model provider. Those charges are handled by that provider under its own billing terms.
          </p>
        </section>

        <section className="legal-section">
          <h2>3. Project Questions</h2>
          <p>
            For bugs or setup questions, visit the <a href="https://github.com/Sobanshahid10/RagPipeline" target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent-light)", textDecoration: "underline" }}>GitHub repository</a>. Please keep API keys and private documents out of public issues.
          </p>
        </section>
      </div>
      <Footer />
    </div>
  );
}
