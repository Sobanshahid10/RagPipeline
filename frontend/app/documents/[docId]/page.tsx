"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { getDocumentStatus, getDocumentFileUrl, DocumentItem } from "@/lib/api";
import { PDFViewer } from "@/components/PDFViewer";
import { 
  ArrowLeft, 
  MessageSquare, 
  Layers, 
  FileText, 
  Clock, 
  CheckCircle2, 
  Loader2, 
  AlertCircle,
  Copy,
  Check,
  Download
} from "lucide-react";

export default function DocumentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { token } = useAuth();
  const { showToast } = useToast();
  const docId = params.docId as string;

  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const fetchDetail = async () => {
      if (!token || !docId) return;
      try {
        const doc = await getDocumentStatus(docId, token);
        setDocument(doc);
      } catch (err: any) {
        setError(err.message || "Failed to load document details.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchDetail();
  }, [docId, token]);

  const handleCopyId = async () => {
    if (!docId) return;
    try {
      await navigator.clipboard.writeText(docId);
      setCopied(true);
      showToast("info", "Document ID copied", docId);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error(e);
    }
  };

  if (isLoading) {
    return (
      <div
        style={{
          height: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "14px",
          color: "var(--accent-light)",
        }}
      >
        <Loader2 size={36} style={{ animation: "spin 1s linear infinite" }} />
        <span style={{ fontSize: "14px", color: "var(--text-secondary)", fontWeight: 500 }}>
          Initializing layout reader...
        </span>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div
        style={{
          padding: "60px 24px",
          maxWidth: "520px",
          margin: "0 auto",
          textAlign: "center",
        }}
      >
        <AlertCircle size={44} color="#F43F5E" style={{ margin: "0 auto 16px" }} />
        <h2 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "8px", color: "#FFFFFF" }}>
          Document Not Found
        </h2>
        <p style={{ fontSize: "14px", color: "var(--text-muted)", marginBottom: "28px", lineHeight: 1.5 }}>
          {error || "The requested document could not be retrieved from the server."}
        </p>
        <button
          onClick={() => router.push("/documents")}
          className="btn btn-secondary"
        >
          <ArrowLeft size={16} />
          <span>Return to Documents</span>
        </button>
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        width: "100%",
        backgroundColor: "var(--bg)",
        overflow: "hidden",
      }}
    >
      {/* ── Top Navigation Bar ───────────────────────────────────── */}
      <div
        style={{
          padding: "12px 24px",
          backgroundColor: "var(--surface)",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          zIndex: 30,
          gap: "16px",
          flexWrap: "wrap",
        }}
      >
        {/* Left Action & Title */}
        <div style={{ display: "flex", alignItems: "center", gap: "16px", minWidth: 0 }}>
          <button
            onClick={() => router.push("/documents")}
            className="btn btn-ghost"
            style={{ padding: "6px 10px", fontSize: "13px" }}
          >
            <ArrowLeft size={16} />
            <span>Documents</span>
          </button>

          <div style={{ height: "18px", width: "1px", backgroundColor: "var(--border)" }} />

          <div style={{ display: "flex", alignItems: "center", gap: "10px", minWidth: 0 }}>
            <div
              style={{
                width: "34px",
                height: "34px",
                borderRadius: "8px",
                backgroundColor: "rgba(99, 102, 241, 0.14)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <FileText size={18} color="var(--accent-light)" />
            </div>

            <div style={{ minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <h2
                  style={{
                    fontSize: "15px",
                    fontWeight: 700,
                    color: "#FFFFFF",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {document.filename}
                </h2>
                <button
                  onClick={handleCopyId}
                  title="Copy Document ID"
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                  }}
                >
                  {copied ? <Check size={12} color="#10B981" /> : <Copy size={12} />}
                </button>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "12px", color: "var(--text-muted)" }}>
                <span>{document.total_pages} {document.total_pages === 1 ? "page" : "pages"}</span>
                <span>•</span>
                <span>{document.chunk_count} indexed chunks</span>
                <span>•</span>
                <span style={{ textTransform: "uppercase" }}>{document.file_type}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Actions */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            onClick={() => router.push("/chat")}
            className="btn btn-primary"
            style={{ padding: "8px 16px", fontSize: "13px" }}
          >
            <MessageSquare size={15} />
            <span>Chat with Document</span>
          </button>
        </div>
      </div>

      {/* ── Main Viewer Area ─────────────────────────────────────── */}
      <div style={{ flex: 1, height: "calc(100vh - 65px)", padding: "16px" }}>
        <PDFViewer
          fileUrl={getDocumentFileUrl(docId)}
          filename={document.filename}
          initialPage={1}
          highlights={[]}
        />
      </div>
    </div>
  );
}
