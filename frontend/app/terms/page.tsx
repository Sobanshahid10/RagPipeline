import type { Metadata } from "next";
import Link from "next/link";
import { Footer } from "@/components/Footer";

export const metadata: Metadata = {
  title: "Terms & Conditions — Nexus RAG Platform",
  description: "Terms and conditions governing the use of the Nexus RAG Platform, multi-tenant workspace, and document ingestion services.",
};

export default function TermsPage() {
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
          <h1 className="legal-title">Terms & Conditions</h1>
          <div className="legal-meta">
            <span>Effective Date: October 4, 2026</span>
            <span>&bull;</span>
            <span>Version: 1.0 (Production Verified)</span>
          </div>
        </header>

        <section className="legal-section">
          <h2>1. Agreement to Terms</h2>
          <p>
            By accessing or using the Nexus RAG Platform (&ldquo;Service&rdquo;), you agree to be bound by these Terms and Conditions. If you are entering into these terms on behalf of a company, organization, or other legal entity, you represent that you have the authority to bind such entity.
          </p>
        </section>

        <section className="legal-section">
          <h2>2. Description of the Service</h2>
          <p>
            Nexus RAG provides an agentic retrieval-augmented generation platform allowing organizations to upload documents (PDF, DOCX, TXT), generate vector embeddings and entity triples, and perform semantic queries with streaming text responses and layout-aware bounding box citations.
          </p>
        </section>

        <section className="legal-section">
          <h2>3. Account Registration & Tenant Security</h2>
          <p>
            To use the Service, you must register a tenant organization and administrative user account. You are responsible for:
          </p>
          <ul>
            <li>Maintaining the confidentiality of your login credentials and JWT access tokens.</li>
            <li>All activities and data processing executed under your tenant workspace.</li>
            <li>Promptly notifying administrators of any unauthorized use or security incident.</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>4. User Content & Intellectual Property</h2>
          <ul>
            <li>
              <strong>Your Content:</strong> You retain all ownership, intellectual property rights, and responsibility for the documents, data, and queries you upload to the platform. We claim no ownership over your proprietary documentation.
            </li>
            <li>
              <strong>Platform License:</strong> The software, architecture, user interface, and proprietary ingestion pipelines are protected by applicable intellectual property laws.
            </li>
            <li>
              <strong>Public Knowledge Book:</strong> The public knowledge book artifacts made available within the demonstration environment are provided solely for evaluation and educational purposes.
            </li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>5. Acceptable Use Policy</h2>
          <p>You agree not to use the Service to:</p>
          <ul>
            <li>Upload documents containing malware, viruses, or destructive code.</li>
            <li>Attempt SQL injection, vector index poisoning, or bypass of PostgreSQL Row-Level Security isolation.</li>
            <li>Submit queries designed to cause intentional hallucination, exfiltration of other tenant data, or Denial of Service (DoS).</li>
            <li>Violate applicable export controls or privacy regulations.</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>6. Disclaimer of Warranties & Limitation of Liability</h2>
          <p>
            The Service and generated AI outputs are provided &ldquo;as is&rdquo; and &ldquo;as available&rdquo;. While Nexus RAG incorporates layout-aware bounding box grounding and citation validation to reduce hallucinations, generative AI responses should be verified against source documentation for critical decision-making.
          </p>
          <p>
            To the maximum extent permitted by applicable law, Nexus RAG and its operators shall not be liable for any indirect, incidental, special, consequential, or punitive damages arising out of your use of or inability to use the Service.
          </p>
        </section>

        <section className="legal-section">
          <h2>7. Governing Law & Dispute Resolution</h2>
          <div style={{ padding: "14px", backgroundColor: "rgba(255,255,255,0.03)", borderRadius: "8px", border: "1px solid var(--border)" }}>
            <p style={{ margin: 0, fontSize: "14px" }}>
              <strong>Jurisdiction:</strong> [TODO: Site Owner — Specify the governing state/country law and agreed dispute forum (e.g., courts of competent jurisdiction or binding arbitration) prior to commercial distribution].
            </p>
          </div>
        </section>
      </div>
      <Footer />
    </div>
  );
}
