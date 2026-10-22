import React from "react";
import Link from "next/link";
import { ArrowLeft, MessageSquare, BookOpen, FileText } from "lucide-react";

export const metadata = {
  title: "404: Page Not Found — Nexus RAG",
  description: "The requested route does not exist on the Nexus RAG Platform.",
};

export default function NotFound() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "32px 24px",
        backgroundColor: "var(--bg)",
        color: "var(--text)",
        textAlign: "center",
      }}
    >
      <div
        style={{
          maxWidth: "520px",
          backgroundColor: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          padding: "40px 32px",
          boxShadow: "var(--shadow-lg)",
        }}
      >
        <span
          style={{
            display: "inline-block",
            fontSize: "12px",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: "var(--text-muted)",
            backgroundColor: "var(--surface-raised)",
            border: "1px solid var(--border)",
            padding: "4px 10px",
            borderRadius: "4px",
            marginBottom: "16px",
          }}
        >
          Error 404
        </span>

        <h1
          className="brand-font"
          style={{
            fontSize: "28px",
            fontWeight: 800,
            color: "#FFFFFF",
            marginBottom: "12px",
            letterSpacing: "-0.02em",
          }}
        >
          Page Not Found
        </h1>

        <p
          style={{
            fontSize: "14.5px",
            color: "var(--text-secondary)",
            lineHeight: 1.6,
            marginBottom: "28px",
          }}
        >
          The page or document route you requested could not be located in this workspace. You can return to the active chat console or explore the public book index.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <Link
            href="/chat"
            className="btn btn-primary"
            style={{ width: "100%", padding: "11px 16px", textDecoration: "none" }}
          >
            <MessageSquare size={16} />
            <span>Return to Streaming Chat</span>
          </Link>

          <Link
            href="/public-book"
            className="btn btn-secondary"
            style={{ width: "100%", padding: "11px 16px", textDecoration: "none" }}
          >
            <BookOpen size={16} />
            <span>Explore Public Knowledge Book</span>
          </Link>
        </div>
      </div>
    </main>
  );
}
