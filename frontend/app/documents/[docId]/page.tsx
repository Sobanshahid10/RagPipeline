"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
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
  AlertCircle 
} from "lucide-react";

export default function DocumentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { token } = useAuth();
  const docId = params.docId as string;

  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  if (isLoading) {
    return (
      <div
        style={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "12px",
          color: "var(--accent-light)",
        }}
      >
        <Loader2 size={32} style={{ animation: "spin 1s linear infinite" }} />
        <span style={{ fontSize: "14px", color: "var(--text-secondary)" }}>
          Loading document reader...
        </span>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div
        style={{
          padding: "48px 24px",
          maxWidth: "500px",
          margin: "0 auto",
          textAlign: "center",
        }}
      >
        <AlertCircle size={40} color="#EF4444" style={{ margin: "0 auto 16px" }} />
        <h2 style={{ fontSize: "18px", fontWeight: 600, marginBottom: "8px" }}>
          Document Not Found
        </h2>
        <p style={{ fontSize: "14px", color: "var(--muted)", marginBottom: "24px" }}>
          {error || "The requested document could not be retrieved from the server."}
        </p>
        <button
          onClick={() => router.push("/documents")}
          className="btn btn-secondary"
        >
          <ArrowLeft size={16} />
          <span>Back to Documents</span>
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
      {/* Top Navigation Bar */}
      <div
        style={{
          padding: "12px 24px",
          backgroundColor: "var(--surface)",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          zIndex: 30,
        }}
      >
        {/* Left Action & Title */}
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <button
            onClick={() => router.push("/documents")}
            className="btn btn-ghost"
            style={{ padding: "6px 10px", fontSize: "13px" }}
          >
            <ArrowLeft size={16} />
            <span>Documents</span>
          </button>

          <div style={{ height: "18px", width: "1px", backgroundColor: "var(--border)" }} />

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <FileText size={18} color="var(--accent-light)" />
            <div>
              <h2 style={{ fontSize: "15px", fontWeight: 600, color: "#FFFFFF" }}>
                {document.filename}
              </h2>
              <span style={{ fontSize: "12px", color: "var(--muted)" }}>
                {document.total_pages} {document.total_pages === 1 ? "page" : "pages"} • {document.chunk_count} indexed chunks
              </span>
            </div>
          </div>
        </div>

        {/* Right Action */}
        <button
          onClick={() => router.push("/chat")}
          className="btn btn-primary"
          style={{ padding: "8px 16px", fontSize: "13px" }}
        >
          <MessageSquare size={16} />
          <span>Chat with Document</span>
        </button>
      </div>

      {/* Main Viewer Area */}
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
