"use client";

import React from "react";
import Link from "next/link";
import { Layers, Shield, BookOpen, FileText, ExternalLink } from "lucide-react";

export const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer
      style={{
        borderTop: "1px solid var(--border)",
        backgroundColor: "var(--surface)",
        padding: "36px 24px 28px 24px",
        marginTop: "auto",
        width: "100%",
        position: "relative",
        zIndex: 10,
      }}
    >
      <div
        style={{
          maxWidth: "1140px",
          margin: "0 auto",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "32px",
          marginBottom: "28px",
        }}
      >
        {/* Brand & Purpose */}
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
            <div
              style={{
                width: "26px",
                height: "26px",
                borderRadius: "6px",
                background: "#1E2025",
                border: "1px solid rgba(255, 255, 255, 0.12)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Layers size={14} color="#FFFFFF" />
            </div>
            <span style={{ fontWeight: 600, fontSize: "15px", color: "#FFFFFF" }} className="brand-font">
              RAG Pipeline
            </span>
          </div>
          <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.6, maxWidth: "280px" }}>
            Multitenant Agentic RAG Platform combining PostgreSQL pgvector, GraphRAG CTE traversal, and layout-aware document citations.
          </p>
        </div>

        {/* Navigation Links */}
        <div>
          <h2 style={{ fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-muted)", marginBottom: "12px", fontWeight: 700 }}>
            Platform Navigation
          </h2>
          <nav aria-label="Footer platform navigation">
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "8px" }}>
              <li>
                <Link href="/chat" style={{ fontSize: "13.5px", color: "var(--text-secondary)", transition: "color 0.15s ease" }} className="hover:text-white">
                  Streaming Chat
                </Link>
              </li>
              <li>
                <Link href="/public-book" style={{ fontSize: "13.5px", color: "var(--text-secondary)", transition: "color 0.15s ease" }}>
                  Public Knowledge Book
                </Link>
              </li>
              <li>
                <Link href="/documents" style={{ fontSize: "13.5px", color: "var(--text-secondary)", transition: "color 0.15s ease" }}>
                  Document Library
                </Link>
              </li>
              <li>
                <Link href="/dashboard" style={{ fontSize: "13.5px", color: "var(--text-secondary)", transition: "color 0.15s ease" }}>
                  Admin Dashboard
                </Link>
              </li>
            </ul>
          </nav>
        </div>

        {/* Compliance & Legal */}
        <div>
          <h2 style={{ fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-muted)", marginBottom: "12px", fontWeight: 700 }}>
            Trust & Compliance
          </h2>
          <nav aria-label="Footer legal navigation">
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "8px" }}>
              <li>
                <Link href="/privacy" style={{ fontSize: "13.5px", color: "var(--text-secondary)", transition: "color 0.15s ease" }}>
                  Privacy Policy
                </Link>
              </li>
              <li>
                <Link href="/terms" style={{ fontSize: "13.5px", color: "var(--text-secondary)", transition: "color 0.15s ease" }}>
                  Terms & Conditions
                </Link>
              </li>
              <li>
                <Link href="/cookies" style={{ fontSize: "13.5px", color: "var(--text-secondary)", transition: "color 0.15s ease" }}>
                  Cookie Policy
                </Link>
              </li>
              <li>
                <Link href="/refund" style={{ fontSize: "13.5px", color: "var(--text-secondary)", transition: "color 0.15s ease" }}>
                  Refund Policy
                </Link>
              </li>
            </ul>
          </nav>
        </div>

        {/* Technical Architecture */}
        <div>
          <h2 style={{ fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-muted)", marginBottom: "12px", fontWeight: 700 }}>
            Security & Storage
          </h2>
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "8px", fontSize: "13px", color: "var(--text-muted)" }}>
            <li style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <Shield size={14} color="var(--emerald-light)" />
              <span>PostgreSQL RLS Tenant Isolation</span>
            </li>
            <li style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <BookOpen size={14} color="var(--accent-light)" />
              <span>Verifiable Passage Citations</span>
            </li>
            <li style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <FileText size={14} color="var(--cyan-light)" />
              <span>Local Storage: Functional Only</span>
            </li>
          </ul>
        </div>
      </div>

      {/* Bottom Row */}
      <div
        style={{
          maxWidth: "1140px",
          margin: "0 auto",
          paddingTop: "20px",
          borderTop: "1px solid var(--border-subtle)",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "12px",
          fontSize: "12.5px",
          color: "var(--text-muted)",
        }}
      >
        <div>
          &copy; {currentYear} Nexus RAG Platform. All rights reserved.
        </div>
        <div style={{ display: "flex", gap: "16px" }}>
          <span>Version 1.0.0</span>
          <span>&bull;</span>
          <Link href="/privacy" style={{ color: "var(--text-muted)", textDecoration: "underline" }}>
            Privacy
          </Link>
          <span>&bull;</span>
          <Link href="/terms" style={{ color: "var(--text-muted)", textDecoration: "underline" }}>
            Terms
          </Link>
        </div>
      </div>
    </footer>
  );
};
