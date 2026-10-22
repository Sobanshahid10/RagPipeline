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
            <span>Effective Date: October 4, 2026</span>
            <span>&bull;</span>
            <span>Version: 1.0 (Production Verified)</span>
          </div>
        </header>

        <section className="legal-section">
          <h2>1. Current Platform Tier Status</h2>
          <p>
            Nexus RAG is currently deployed as an evaluation and demonstration enterprise environment. Self-serve credit-card processing is not currently active on this instance.
          </p>
        </section>

        <section className="legal-section">
          <h2>2. Enterprise Commercial Subscriptions (Site Owner Specification Required)</h2>
          <div style={{ padding: "18px", backgroundColor: "rgba(255,255,255,0.03)", borderRadius: "10px", border: "1px dashed var(--border)", marginBottom: "20px" }}>
            <p style={{ color: "var(--accent-light)", fontWeight: 600, fontSize: "14px", marginBottom: "8px" }}>
              [TODO: Site Owner — Specify Commercial Refund Terms Upon Commercial Launch]
            </p>
            <p style={{ fontSize: "13.5px", color: "var(--text-secondary)", margin: 0 }}>
              Prior to activating paid Stripe/payment gateways for multi-tenant SaaS subscriptions or token usage billing, the platform owner must define:
            </p>
            <ul style={{ marginTop: "10px", marginBottom: 0, fontSize: "13px", color: "var(--text-muted)" }}>
              <li>Subscription cancellation timelines (e.g., immediate vs. end-of-billing-cycle).</li>
              <li>Prorated refund policies for enterprise SLA downtime or processing disruptions.</li>
              <li>Token consumption dispute resolution procedures.</li>
              <li>Billing support contact channel.</li>
            </ul>
          </div>
        </section>

        <section className="legal-section">
          <h2>3. Service Disruptions and Inquiries</h2>
          <p>
            If you experience service unavailability, ingest pipeline failures, or billing discrepancies under an active enterprise contract, please submit an issue through your designated technical support contact or platform administrator.
          </p>
        </section>
      </div>
      <Footer />
    </div>
  );
}
