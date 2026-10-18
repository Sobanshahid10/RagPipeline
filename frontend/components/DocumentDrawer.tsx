"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { DocumentItem, getDocumentFileUrl } from "@/lib/api";
import { useToast } from "@/context/ToastContext";
import {
  X,
  FileText,
  MessageSquare,
  Eye,
  Download,
  Layers,
  Database,
  Check,
  Copy,
  Clock,
  GitCommit,
  CheckCircle2,
  Share2
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface DocumentDrawerProps {
  document: DocumentItem | null;
  onClose: () => void;
}

export const DocumentDrawer: React.FC<DocumentDrawerProps> = ({ document, onClose }) => {
  const router = useRouter();
  const { showToast } = useToast();
  const [activeTab, setActiveTab] = useState<"overview" | "chunks" | "graph">("overview");
  const [copied, setCopied] = useState(false);

  if (!document) return null;

  const handleCopyId = async () => {
    try {
      await navigator.clipboard.writeText(document.document_id);
      setCopied(true);
      showToast("info", "Document UUID copied", document.document_id);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error(e);
    }
  };

  // Mock sample extracted entity triples for the knowledge graph tab based on doc
  const sampleTriples = [
    { subject: document.filename.replace(/\.[^/.]+$/, ""), predicate: "INGESTED_BY", object: "VisionLayoutEngine" },
    { subject: document.filename.replace(/\.[^/.]+$/, ""), predicate: "CHUNKS_COUNT", object: `${document.chunk_count} Chunks` },
    { subject: "LayoutExtractor", predicate: "DETECTED_BOUNDING_BOXES", object: `${document.total_pages} Pages` },
    { subject: "TenantPartition", predicate: "ENFORCES_RLS_ISOLATION", object: "PostgreSQL 16" },
  ];

  return (
    <AnimatePresence>
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0, 0, 0, 0.7)",
          backdropFilter: "blur(10px)",
          zIndex: 9999,
          display: "flex",
          justifyContent: "flex-end",
        }}
        onClick={onClose}
      >
        <motion.div
          initial={{ x: "100%" }}
          animate={{ x: 0 }}
          exit={{ x: "100%" }}
          transition={{ duration: 0.28, ease: "easeOut" }}
          style={{
            width: "100%",
            maxWidth: "540px",
            height: "100vh",
            backgroundColor: "rgba(16, 18, 29, 0.98)",
            borderLeft: "1px solid var(--border)",
            boxShadow: "-16px 0 48px rgba(0, 0, 0, 0.75)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div
            style={{
              padding: "20px 24px",
              borderBottom: "1px solid var(--border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              backgroundColor: "rgba(255, 255, 255, 0.02)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px", minWidth: 0 }}>
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "6px",
                  backgroundColor: "var(--surface-raised)",
                  border: "1px solid var(--border)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <FileText size={18} color="var(--text-secondary)" />
              </div>
              <div style={{ minWidth: 0 }}>
                <h3
                  style={{
                    fontSize: "15px",
                    fontWeight: 600,
                    color: "var(--foreground)",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {document.filename}
                </h3>
                <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  {document.file_type.toUpperCase()} • {document.total_pages} pages
                </span>
              </div>
            </div>

            <button onClick={onClose} className="btn btn-ghost" style={{ padding: "6px" }}>
              <X size={18} />
            </button>
          </div>

          {/* Tab Navigation */}
          <div
            style={{
              display: "flex",
              borderBottom: "1px solid var(--border)",
              padding: "0 20px",
              backgroundColor: "transparent",
            }}
          >
            {[
              { id: "overview", label: "Metadata & Info" },
              { id: "chunks", label: `Chunks (${document.chunk_count})` },
              { id: "graph", label: "Knowledge Graph" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                style={{
                  padding: "12px 16px",
                  background: "transparent",
                  border: "none",
                  borderBottom: activeTab === tab.id ? "2px solid var(--foreground)" : "2px solid transparent",
                  color: activeTab === tab.id ? "var(--foreground)" : "var(--text-muted)",
                  fontSize: "13px",
                  fontWeight: activeTab === tab.id ? 600 : 500,
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Drawer Body Scroll */}
          <div style={{ flex: 1, overflowY: "auto", padding: "24px" }}>
            {activeTab === "overview" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                {/* UUID Card */}
                <div
                  style={{
                    padding: "14px 16px",
                    borderRadius: "10px",
                    backgroundColor: "rgba(255, 255, 255, 0.03)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", marginBottom: "6px" }}>
                    Document UUID
                  </div>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <code style={{ fontSize: "13px", color: "var(--foreground)" }}>{document.document_id}</code>
                    <button
                      onClick={handleCopyId}
                      className="btn btn-ghost"
                      style={{ padding: "4px 8px", fontSize: "11px" }}
                    >
                      {copied ? <Check size={12} color="#10B981" /> : <Copy size={12} />}
                      <span>{copied ? "Copied" : "Copy"}</span>
                    </button>
                  </div>
                </div>

                {/* Key Metrics */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div style={{ padding: "14px", borderRadius: "6px", backgroundColor: "var(--surface-raised)", border: "1px solid var(--border)" }}>
                    <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Total Pages</span>
                    <div style={{ fontSize: "20px", fontWeight: 700, color: "var(--foreground)", marginTop: "4px" }}>{document.total_pages}</div>
                  </div>
                  <div style={{ padding: "14px", borderRadius: "6px", backgroundColor: "var(--surface-raised)", border: "1px solid var(--border)" }}>
                    <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Indexed Chunks</span>
                    <div style={{ fontSize: "20px", fontWeight: 700, color: "var(--foreground)", marginTop: "4px" }}>{document.chunk_count}</div>
                  </div>
                </div>

                {/* Ingestion Pipeline Badges */}
                <div style={{ padding: "14px", borderRadius: "6px", backgroundColor: "rgba(16, 185, 129, 0.05)", border: "1px solid rgba(16, 185, 129, 0.2)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#34D399", fontWeight: 600, fontSize: "13px", marginBottom: "4px" }}>
                    <CheckCircle2 size={15} />
                    <span>Vision Layout Indexing Complete</span>
                  </div>
                  <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                    Tables, paragraphs, and multi-column bounding boxes extracted and stored in pgvector HNSW index.
                  </span>
                </div>
              </div>
            )}

            {activeTab === "chunks" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {Array.from({ length: Math.min(document.chunk_count || 3, 6) }).map((_, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: "14px",
                      borderRadius: "6px",
                      backgroundColor: "var(--surface-raised)",
                      border: "1px solid var(--border)",
                      fontSize: "12.5px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                      <span style={{ fontWeight: 600, color: "var(--foreground)" }}>Chunk #{idx + 1}</span>
                      <span className="badge">Page {Math.floor(idx / 2) + 1}</span>
                    </div>
                    <p style={{ color: "var(--text-secondary)", lineHeight: 1.45, fontStyle: "italic" }}>
                      &ldquo;Document section covering key operational specifications, architectural layout details, and compliance requirements...&rdquo;
                    </p>
                    <div style={{ display: "flex", gap: "12px", fontSize: "11px", color: "var(--text-muted)", marginTop: "8px" }}>
                      <span>Dim: 1536</span>
                      <span>•</span>
                      <span>BBox: [ymin, xmin, ymax, xmax]</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {activeTab === "graph" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  Recursive Common Table Expression (CTE) Entity Graph Triples:
                </span>
                {sampleTriples.map((triple, i) => (
                  <div
                    key={i}
                    style={{
                      padding: "12px 14px",
                      borderRadius: "6px",
                      backgroundColor: "var(--surface-raised)",
                      border: "1px solid var(--border)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "10px",
                      fontSize: "12px",
                    }}
                  >
                    <span style={{ fontWeight: 600, color: "var(--foreground)" }}>{triple.subject}</span>
                    <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase" }}>{triple.predicate}</span>
                    <span style={{ fontWeight: 600, color: "var(--text-secondary)" }}>{triple.object}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Action Footer */}
          <div
            style={{
              padding: "16px 24px",
              borderTop: "1px solid var(--border)",
              backgroundColor: "rgba(11, 13, 20, 0.8)",
              display: "flex",
              alignItems: "center",
              gap: "10px",
            }}
          >
            <button
              onClick={() => {
                onClose();
                router.push(`/documents/${document.document_id}`);
              }}
              className="btn btn-secondary"
              style={{ flex: 1 }}
            >
              <Eye size={15} />
              <span>Inspect PDF</span>
            </button>

            <button
              onClick={() => {
                onClose();
                router.push("/chat");
              }}
              className="btn btn-primary"
              style={{ flex: 1 }}
            >
              <MessageSquare size={15} />
              <span>Ask in Chat</span>
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
