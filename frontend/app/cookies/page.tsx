import type { Metadata } from "next";
import Link from "next/link";
import { Footer } from "@/components/Footer";

export const metadata: Metadata = {
  title: "Cookie & Local Storage Policy — Nexus RAG Platform",
  description: "Learn about the storage technologies used by Nexus RAG. We do not use third-party tracking or advertising cookies.",
};

export default function CookiesPage() {
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
          <h1 className="legal-title">Cookie & Local Storage Policy</h1>
          <div className="legal-meta">
            <span>Effective Date: October 4, 2026</span>
            <span>&bull;</span>
            <span>Version: 1.0 (Production Verified)</span>
          </div>
        </header>

        <div className="legal-badge-notice">
          <strong>Key Summary:</strong> Nexus RAG does not use advertising cookies, marketing pixels (such as Meta Pixel or Google Tag Manager), heatmaps, or third-party behavioral tracking scripts. We utilize only essential browser LocalStorage strictly necessary to authenticate your session and preserve your chosen settings.
        </div>

        <section className="legal-section">
          <h2>1. What Are Cookies and Local Storage?</h2>
          <p>
            Cookies and browser LocalStorage are standard web technologies that store small pieces of information on your device when you browse a web application. LocalStorage persists data securely within your browser domain until explicitly cleared or updated by the application.
          </p>
        </section>

        <section className="legal-section">
          <h2>2. Exactly What We Store and Why</h2>
          <p>The following items are stored locally in your browser to enable platform functionality:</p>
          <div style={{ overflowX: "auto", marginBottom: "18px" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px", border: "1px solid var(--border)" }}>
              <thead>
                <tr style={{ backgroundColor: "rgba(255, 255, 255, 0.04)", borderBottom: "1px solid var(--border)", textAlign: "left" }}>
                  <th style={{ padding: "10px 14px", color: "var(--text)" }}>Key / Identifier</th>
                  <th style={{ padding: "10px 14px", color: "var(--text)" }}>Type</th>
                  <th style={{ padding: "10px 14px", color: "var(--text)" }}>Purpose</th>
                  <th style={{ padding: "10px 14px", color: "var(--text)" }}>Category</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <td style={{ padding: "10px 14px", fontFamily: "JetBrains Mono, monospace" }}>rag_token (session storage)</td>
                  <td style={{ padding: "10px 14px", color: "var(--text-secondary)" }}>LocalStorage</td>
                  <td style={{ padding: "10px 14px", color: "var(--text-secondary)" }}>Holds the signed JSON Web Token (JWT) required to authorize API calls to the backend.</td>
                  <td style={{ padding: "10px 14px", color: "var(--emerald-light)", fontWeight: 600 }}>Strictly Necessary</td>
                </tr>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <td style={{ padding: "10px 14px", fontFamily: "JetBrains Mono, monospace" }}>rag_settings</td>
                  <td style={{ padding: "10px 14px", color: "var(--text-secondary)" }}>LocalStorage</td>
                  <td style={{ padding: "10px 14px", color: "var(--text-secondary)" }}>Remembers your selected inference model (e.g., Gemini 3.8 Flash, Groq) and pipeline parameters.</td>
                  <td style={{ padding: "10px 14px", color: "var(--accent-light)", fontWeight: 600 }}>Functional Preference</td>
                </tr>
                <tr>
                  <td style={{ padding: "10px 14px", fontFamily: "JetBrains Mono, monospace" }}>rag_chat_sessions:&lt;workspace&gt;:&lt;account&gt;</td>
                  <td style={{ padding: "10px 14px", color: "var(--text-secondary)" }}>LocalStorage</td>
                  <td style={{ padding: "10px 14px", color: "var(--text-secondary)" }}>Caches recent chat exchanges client-side so conversations re-render instantly without waiting for network re-fetch.</td>
                  <td style={{ padding: "10px 14px", color: "var(--accent-light)", fontWeight: 600 }}>Functional / Performance</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section className="legal-section">
          <h2>3. Third-Party Tracking Technologies</h2>
          <p>
            Nexus RAG deliberately avoids all third-party tracking services:
          </p>
          <ul>
            <li>No Google Analytics or Tag Manager scripts are loaded.</li>
            <li>No advertising or retargeting pixels are embedded.</li>
            <li>No third-party session recording or keystroke logging services are active.</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>4. Managing and Clearing Storage</h2>
          <p>
            You can clear your local storage at any time by signing out of the application (via the &ldquo;Sign Out&rdquo; button in the sidebar) or by using your browser&apos;s privacy settings:
          </p>
          <ul>
            <li>In Chrome/Edge: Settings &rarr; Privacy and security &rarr; Clear browsing data &rarr; Cookies and site data.</li>
            <li>In Firefox: Settings &rarr; Privacy &amp; Security &rarr; Cookies and Site Data &rarr; Clear Data.</li>
            <li>In Safari: Preferences &rarr; Privacy &rarr; Manage Website Data.</li>
          </ul>
          <p>
            Please note that clearing LocalStorage will sign you out and reset your selected inference model to default.
          </p>
        </section>
      </div>
      <Footer />
    </div>
  );
}
