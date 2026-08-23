"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { 
  uploadDocument, 
  getDocuments, 
  getDocumentStatus, 
  DocumentItem 
} from "@/lib/api";
import { 
  UploadCloud, 
  FileText, 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  Layers, 
  File, 
  Eye, 
  MessageSquare, 
  RefreshCw, 
  Loader2,
  Sparkles
} from "lucide-react";

export default function DocumentsPage() {
  const { token, user } = useAuth();
  const router = useRouter();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocs = useCallback(async () => {
    if (!token) return;
    try {
      const list = await getDocuments(token, user?.tenant_id);
      setDocuments(list);
    } catch (err: any) {
      console.error("Failed to fetch documents:", err);
    } finally {
      setIsLoadingList(false);
    }
  }, [token, user]);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  // Polling for documents that are still in 'pending' or 'processing' status
  useEffect(() => {
    if (!token) return;
    const hasUnfinished = documents.some(
      (doc) => doc.status === "pending" || doc.status === "processing"
    );

    if (!hasUnfinished) return;

    const interval = setInterval(async () => {
      try {
        const updatedList = await getDocuments(token, user?.tenant_id);
        setDocuments(updatedList);
      } catch (e) {
        console.warn("Poll status failed:", e);
      }
    }, 4000);

    return () => clearInterval(interval);
  }, [documents, token, user]);

  const handleFileUpload = async (file: File) => {
    if (!token) return;
    setUploadError(null);
    setUploadSuccess(null);
    setIsUploading(true);

    try {
      const res = await uploadDocument(file, token, user?.tenant_id);
      setUploadSuccess(`"${file.name}" uploaded successfully and queued for parsing.`);
      await fetchDocs();
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload document.");
    } finally {
      setIsUploading(false);
    }
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = () => {
    setIsDragging(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const onFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "indexed":
      case "ready":
        return (
          <span className="badge badge-indexed">
            <CheckCircle2 size={12} /> Indexed
          </span>
        );
      case "processing":
        return (
          <span className="badge badge-processing">
            <Loader2 size={12} style={{ animation: "spin 1s linear infinite" }} /> Parsing Layout
          </span>
        );
      case "pending":
        return (
          <span className="badge badge-pending">
            <Clock size={12} /> Queued
          </span>
        );
      case "failed":
        return (
          <span className="badge badge-failed">
            <AlertCircle size={12} /> Failed
          </span>
        );
      default:
        return <span className="badge">{status}</span>;
    }
  };

  return (
    <div
      style={{
        padding: "36px 40px",
        maxWidth: "1200px",
        margin: "0 auto",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "28px",
        }}
      >
        <div>
          <h1
            className="brand-font"
            style={{ fontSize: "26px", fontWeight: 700, letterSpacing: "-0.02em", marginBottom: "6px" }}
          >
            Document Library
          </h1>
          <p style={{ fontSize: "14px", color: "var(--text-secondary)" }}>
            Upload PDFs, DOCX, or text files for layout-aware parsing, chunking, and knowledge graph indexing.
          </p>
        </div>

        <button
          onClick={fetchDocs}
          className="btn btn-secondary"
          style={{ fontSize: "13px", padding: "8px 14px" }}
        >
          <RefreshCw size={14} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Drag & Drop Upload Zone */}
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        className="card"
        style={{
          padding: "36px 24px",
          textAlign: "center",
          border: isDragging
            ? "2px dashed var(--accent-light)"
            : "2px dashed rgba(255, 255, 255, 0.15)",
          backgroundColor: isDragging
            ? "rgba(99, 102, 241, 0.08)"
            : "rgba(255, 255, 255, 0.02)",
          borderRadius: "14px",
          cursor: "pointer",
          marginBottom: "32px",
          transition: "all 0.2s ease",
        }}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={onFileInputChange}
          accept=".pdf,.docx,.txt"
          style={{ display: "none" }}
        />

        <div
          style={{
            width: "52px",
            height: "52px",
            borderRadius: "14px",
            background: "rgba(99, 102, 241, 0.15)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 16px",
          }}
        >
          {isUploading ? (
            <Loader2 size={26} color="var(--accent-light)" style={{ animation: "spin 1s linear infinite" }} />
          ) : (
            <UploadCloud size={26} color="var(--accent-light)" />
          )}
        </div>

        <h3 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "6px" }}>
          {isUploading ? "Uploading & Computing SHA-256 Digest..." : "Drag & drop your document here, or click to browse"}
        </h3>
        <p style={{ fontSize: "13px", color: "var(--muted)" }}>
          Supports PDF with vision layout extraction, DOCX, and TXT (Max 50MB)
        </p>
      </div>

      {/* Feedback Alerts */}
      {uploadError && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            padding: "12px 16px",
            marginBottom: "24px",
            backgroundColor: "rgba(239, 68, 68, 0.12)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: "8px",
            color: "#F87171",
            fontSize: "13px",
          }}
        >
          <AlertCircle size={18} />
          <span>{uploadError}</span>
        </div>
      )}

      {uploadSuccess && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            padding: "12px 16px",
            marginBottom: "24px",
            backgroundColor: "rgba(16, 185, 129, 0.12)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            borderRadius: "8px",
            color: "#34D399",
            fontSize: "13px",
          }}
        >
          <CheckCircle2 size={18} />
          <span>{uploadSuccess}</span>
        </div>
      )}

      {/* Documents Table / Grid */}
      <div style={{ marginTop: "12px" }}>
        <h2 style={{ fontSize: "18px", fontWeight: 600, marginBottom: "16px" }}>
          Uploaded Documents ({documents.length})
        </h2>

        {isLoadingList ? (
          <div style={{ textAlign: "center", padding: "48px 0", color: "var(--muted)" }}>
            <Loader2 size={32} style={{ animation: "spin 1s linear infinite", margin: "0 auto 12px" }} />
            <p>Loading documents...</p>
          </div>
        ) : documents.length === 0 ? (
          <div
            className="card"
            style={{
              padding: "48px 24px",
              textAlign: "center",
              backgroundColor: "rgba(255, 255, 255, 0.02)",
            }}
          >
            <FileText size={40} color="var(--muted)" style={{ margin: "0 auto 12px" }} />
            <h3 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "6px" }}>No documents yet</h3>
            <p style={{ fontSize: "13px", color: "var(--muted)", maxWidth: "400px", margin: "0 auto 20px" }}>
              Upload your first document above to enable layout parsing, semantic chunking, and AI grounded answers.
            </p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {documents.map((doc) => (
              <div
                key={doc.document_id}
                className="card card-interactive"
                style={{
                  padding: "16px 20px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  backgroundColor: "var(--surface)",
                }}
              >
                {/* Left File Info */}
                <div style={{ display: "flex", alignItems: "center", gap: "16px", minWidth: 0 }}>
                  <div
                    style={{
                      width: "42px",
                      height: "42px",
                      borderRadius: "10px",
                      backgroundColor: "rgba(99, 102, 241, 0.12)",
                      border: "1px solid rgba(99, 102, 241, 0.3)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    <FileText size={20} color="var(--accent-light)" />
                  </div>

                  <div style={{ minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: "15px",
                        fontWeight: 600,
                        color: "#FFFFFF",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        marginBottom: "4px",
                      }}
                    >
                      {doc.filename}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "12px", fontSize: "12px", color: "var(--muted)" }}>
                      <span>Type: {doc.file_type.toUpperCase()}</span>
                      <span>•</span>
                      <span>{doc.total_pages} {doc.total_pages === 1 ? "page" : "pages"}</span>
                      <span>•</span>
                      <span>{doc.chunk_count} chunks</span>
                    </div>
                  </div>
                </div>

                {/* Right Status & Actions */}
                <div style={{ display: "flex", alignItems: "center", gap: "16px", flexShrink: 0 }}>
                  {getStatusBadge(doc.status)}

                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <button
                      onClick={() => router.push(`/documents/${doc.document_id}`)}
                      className="btn btn-secondary"
                      style={{ padding: "8px 12px", fontSize: "13px" }}
                      title="View PDF with Layout Overlay"
                    >
                      <Eye size={15} />
                      <span>View PDF</span>
                    </button>

                    <button
                      onClick={() => router.push(`/chat`)}
                      className="btn btn-primary"
                      style={{ padding: "8px 14px", fontSize: "13px" }}
                      title="Chat with this document"
                    >
                      <MessageSquare size={15} />
                      <span>Chat</span>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
