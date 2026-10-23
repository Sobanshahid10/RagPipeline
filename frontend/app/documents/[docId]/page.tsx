"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { getDocumentStatus, getDocumentFileUrl, deleteDocument, DocumentItem } from "@/lib/api";
import dynamic from "next/dynamic";
const PDFViewer = dynamic(() => import("@/components/PDFViewer").then(module => module.PDFViewer), { ssr: false });
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
  Download,
  Trash2
} from "lucide-react";

export default function DocumentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { token } = useAuth();
  const { showToast } = useToast();
  const docId = params.docId as string;

  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDeleting, setIsDeleting] = useState(false);
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

  const handleDelete = async () => {
    if (!token || !docId || !document) return;
    if (!window.confirm(`Are you sure you want to delete "${document.filename}"? This will permanently delete the file, its vector embeddings, and indexed chunks.`)) {
      return;
    }
    try {
      setIsDeleting(true);
      await deleteDocument(docId, token);
      showToast("success", "Document deleted", `"${document.filename}" was permanently removed.`);
      router.push("/documents");
    } catch (err: any) {
      showToast("error", "Delete failed", err.message || "Could not delete document.");
      setIsDeleting(false);
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
        <h1 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "8px", color: "#FFFFFF" }}>
          Document Not Found
        </h1>
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
                width: "32px",
                height: "32px",
                borderRadius: "6px",
                backgroundColor: "var(--surface-raised)",
                border: "1px solid var(--border)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <FileText size={16} color="var(--text-secondary)" />
            </div>

            <div style={{ minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <h1
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
                </h1>
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
            onClick={handleDelete}
            disabled={isDeleting}
            className="btn btn-ghost"
            style={{
              padding: "8px 14px",
              fontSize: "13px",
              color: "var(--rose-light)",
              border: "1px solid var(--border)",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
            }}
            title={`Delete "${document.filename}"`}
          >
            {isDeleting ? (
              <Loader2 size={15} style={{ animation: "spin 1s linear infinite" }} />
            ) : (
              <Trash2 size={15} />
            )}
            <span>Delete PDF</span>
          </button>

          <button
            disabled={document.status !== "indexed"}
            onClick={() => router.push(`/chat?document=${docId}`)}
            className="btn btn-primary"
            style={{ padding: "8px 16px", fontSize: "13px" }}
          >
            <MessageSquare size={15} />
            <span>Chat with Document</span>
          </button>
        </div>
      </div>

      <p role="status" style={{padding:"10px 20px",fontSize:13}}>Status: {document.status}{document.stage ? ` · ${document.stage}` : ""}{document.error ? ` · ${document.error}` : ""}</p>

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
