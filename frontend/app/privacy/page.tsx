import type { Metadata } from "next";
import Link from "next/link";
import { Footer } from "@/components/Footer";

export const metadata: Metadata = {
  title: "Privacy Policy — Nexus RAG Platform",
  description: "Learn how Nexus RAG collects, processes, and protects your tenant documents, queries, and credentials.",
};

export default function PrivacyPolicyPage() {
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
          <h1 className="legal-title">Privacy Policy</h1>
          <div className="legal-meta">
            <span>Effective Date: October 4, 2026</span>
            <span>&bull;</span>
            <span>Version: 1.0 (Production Verified)</span>
          </div>
        </header>

        <div className="legal-badge-notice">
          <strong>Transparency Notice:</strong> This privacy policy reflects the actual technical architecture of the Nexus RAG Platform. We do not sell personal data, do not run third-party advertising trackers, and enforce cryptographic tenant isolation at the database layer.
        </div>

        <section className="legal-section">
          <h2>1. Information We Collect</h2>
          <p>
            Nexus RAG is a multi-tenant enterprise Retrieval-Augmented Generation (RAG) platform. We collect only information strictly necessary to provide document indexing, hybrid search, and generative question answering:
          </p>
          <ul>
            <li>
              <strong>Account & Authentication Information:</strong> Work email address, organization/tenant name, and cryptographic password hashes (stored using bcrypt with unique salts). We never store plaintext passwords.
            </li>
            <li>
              <strong>Tenant Documents:</strong> Files you explicitly upload (PDF, DOCX, TXT). These documents are processed through our ingestion pipeline into layout-aware text chunks, contextual summaries, and vector embeddings.
            </li>
            <li>
              <strong>Interaction & Query Logs:</strong> Queries submitted in the chat interface, retrieved chunk identifiers, generated answers, token consumption counts, and latency metrics. These are saved to facilitate session history and RAG quality evaluation.
            </li>
            <li>
              <strong>Client-Side Preferences:</strong> Inference model selection and interface state, stored locally on your device via browser LocalStorage.
            </li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>2. How We Use Your Information</h2>
          <p>We process collected data exclusively for the following operational purposes:</p>
          <ul>
            <li>Authenticating tenant users and enforcing PostgreSQL Row-Level Security (RLS) to prevent cross-tenant data access.</li>
            <li>Chunking, embedding (via local or configured embedding models), and indexing your uploaded documents.</li>
            <li>Generating streaming responses and layout-aware bounding box citations when you ask questions.</li>
            <li>Diagnosing pipeline latency, tracking cache hit rates in Redis, and monitoring system availability.</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>3. Data Storage & Multi-Tenant Isolation</h2>
          <p>
            All document chunks, vector embeddings, and interaction logs are tagged with your unique <code>tenant_id</code>. PostgreSQL Row-Level Security policies ensure that queries executed on behalf of one tenant cannot read or modify data belonging to another tenant.
          </p>
          <p>
            Ephemeral caching of query embeddings and exact-match responses occurs in Redis and expires based on standard TTL policies.
          </p>
        </section>

        <section className="legal-section">
          <h2>4. Third-Party Model Providers</h2>
          <p>
            When you initiate a query, prompt text and retrieved document passages are transmitted to the LLM inference provider configured by the tenant or platform administrator (e.g., Google Gemini or Groq):
          </p>
          <ul>
            <li>Transmission occurs over encrypted HTTPS connections.</li>
            <li>Only retrieved context passages and the user prompt are sent; full document files are never transmitted to LLM providers.</li>
            <li>Refer to the respective provider privacy terms regarding data retention for API inference.</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>5. Cookies & Local Storage</h2>
          <p>
            We do not use advertising cookies, marketing pixels, or third-party behavioral trackers. Our application uses standard browser LocalStorage solely for essential functionality:
          </p>
          <ul>
            <li><code>rag_token</code>: Your JSON Web Token (JWT) used to authenticate API requests.</li>
            <li><code>rag_settings</code>: Your preferred model and retrieval parameters.</li>
            <li><code>rag_chat_sessions</code>: Local caching of chat conversation history for instant client rendering.</li>
          </ul>
          <p>
            For more details, please review our <Link href="/cookies" style={{ color: "var(--accent-light)", textDecoration: "underline" }}>Cookie & Local Storage Policy</Link>.
          </p>
        </section>

        <section className="legal-section">
          <h2>6. Data Retention & Deletion</h2>
          <p>
            Tenants retain full ownership of their data. When you delete a document from the Document Library, its associated text chunks, vector embeddings, and entity triples are deleted from the database via cascading deletion.
          </p>
        </section>

        <section className="legal-section">
          <h2>7. Contact & Site Administration</h2>
          <p>
            For privacy inquiries, data deletion requests, or technical audits, contact the platform administrator:
          </p>
          <div style={{ padding: "14px", backgroundColor: "rgba(255,255,255,0.03)", borderRadius: "8px", border: "1px solid var(--border)" }}>
            <p style={{ margin: 0, fontSize: "14px" }}>
              <strong>Platform Contact:</strong> Nexus RAG Administration<br />
              <strong>Email:</strong> privacy@nexus-rag.internal (or your organization administrator)<br />
              <strong>Entity:</strong> [TODO: Site Owner — Specify legal entity name and registered jurisdiction prior to commercial deployment]
            </p>
          </div>
        </section>
      </div>
      <Footer />
    </div>
  );
}
