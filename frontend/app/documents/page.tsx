"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { 
  uploadDocument, 
  getDocuments, 
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
  Sparkles,
  Search,
  Filter,
  LayoutGrid,
  List,
  Copy,
  Check,
  HardDrive,
  Database
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { DocumentDrawer } from "@/components/DocumentDrawer";

export default function DocumentsPage() {
  const { token, user } = useAuth();
  const { showToast } = useToast();
  const router = useRouter();

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadFileName, setUploadFileName] = useState<string>("");
  const [isDragging, setIsDragging] = useState(false);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocs = useCallback(async () => {
    if (!token) return;
    try {
      const list = await getDocuments(token, user?.tenant_id);
      setDocuments(list);
    } catch (err: any) {
      console.error("Failed to fetch documents:", err);
      showToast("error", "Failed to load documents", err.message);
    } finally {
      setIsLoadingList(false);
    }
  }, [token, user, showToast]);

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
    setIsUploading(true);
    setUploadFileName(file.name);

    try {
      await uploadDocument(file, token, user?.tenant_id);
      showToast("success", "Document uploaded", `"${file.name}" queued for layout parsing.`);
      await fetchDocs();
    } catch (err: any) {
      showToast("error", "Upload failed", err.message || "Failed to upload document.");
    } finally {
      setIsUploading(false);
      setUploadFileName("");
    }
  };

  const handleCopyId = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(id);
      setCopiedId(id);
      showToast("info", "Document ID copied", id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error(err);
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

  // Filter & Search Documents
  const filteredDocs = documents.filter((doc) => {
    const matchesSearch = doc.filename.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === "all" || doc.status.toLowerCase() === statusFilter.toLowerCase();
    return matchesSearch && matchesStatus;
  });

  // Calculate Aggregates
  const totalPages = documents.reduce((sum, d) => sum + (d.total_pages || 0), 0);
  const totalChunks = documents.reduce((sum, d) => sum + (d.chunk_count || 0), 0);
  const readyDocs = documents.filter((d) => d.status === "indexed" || d.status === "ready").length;

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "indexed":
      case "ready":
        return (
          <span className="badge badge-indexed">
            <CheckCircle2 size={12} /> Ready
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
            <Clock size={12} /> In Queue
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
        padding: "36px 44px",
        maxWidth: "1320px",
        margin: "0 auto",
      }}
    >
      {/* ── Top Header ───────────────────────────────────────────── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "32px",
          flexWrap: "wrap",
          gap: "16px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
            <h1
              className="brand-font"
              style={{ fontSize: "28px", fontWeight: 800, letterSpacing: "-0.025em" }}
            >
              Document Library
            </h1>
            <span className="badge badge-accent">Enterprise Corpus</span>
          </div>
          <p style={{ fontSize: "14px", color: "var(--text-secondary)" }}>
            Multitenant document catalog with vision layout parsing, semantic chunking, and knowledge graph ingestion.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="btn btn-primary"
            style={{ fontSize: "13.5px", padding: "9px 18px" }}
          >
            <UploadCloud size={16} />
            <span>Upload Document</span>
          </button>

          <button
            onClick={fetchDocs}
            className="btn btn-secondary"
            style={{ fontSize: "13px", padding: "9px 14px" }}
            title="Refresh document status"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* ── Aggregate Stat Cards ─────────────────────────────────── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "16px",
          marginBottom: "28px",
        }}
      >
        <div className="card" style={{ padding: "20px 22px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
            <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Total Documents
            </span>
            <FileText size={18} color="var(--accent-light)" />
          </div>
          <div style={{ fontSize: "28px", fontWeight: 800, color: "#FFFFFF", fontFamily: "'Outfit', sans-serif" }}>
            {documents.length}
          </div>
          <div style={{ fontSize: "12px", color: "var(--emerald-light)", marginTop: "4px" }}>
            {readyDocs} ready for retrieval
          </div>
        </div>

        <div className="card" style={{ padding: "20px 22px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
            <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Total Pages
            </span>
            <Layers size={18} color="var(--cyan-light)" />
          </div>
          <div style={{ fontSize: "28px", fontWeight: 800, color: "#FFFFFF", fontFamily: "'Outfit', sans-serif" }}>
            {totalPages.toLocaleString()}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
            Visual layout & bounding-boxes
          </div>
        </div>

        <div className="card" style={{ padding: "20px 22px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
            <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Indexed Chunks
            </span>
            <Database size={18} color="#F59E0B" />
          </div>
          <div style={{ fontSize: "28px", fontWeight: 800, color: "#FFFFFF", fontFamily: "'Outfit', sans-serif" }}>
            {totalChunks.toLocaleString()}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
            Dense vectors & BM25 indices
          </div>
        </div>

        <div className="card" style={{ padding: "20px 22px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
            <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Ingestion Status
            </span>
            <Sparkles size={18} color="var(--emerald-light)" />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "4px" }}>
            <span className="status-dot-active" />
            <span style={{ fontSize: "18px", fontWeight: 700, color: "#FFFFFF" }}>
              Online
            </span>
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "8px" }}>
            Celery async workers listening
          </div>
        </div>
      </div>

      {/* ── Drag & Drop Upload Zone ──────────────────────────────── */}
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        className="card"
        style={{
          padding: "36px 28px",
          textAlign: "center",
          border: isDragging
            ? "2px dashed var(--accent-light)"
            : "2px dashed rgba(255, 255, 255, 0.12)",
          backgroundColor: isDragging
            ? "rgba(99, 102, 241, 0.12)"
            : "rgba(18, 20, 31, 0.4)",
          boxShadow: isDragging ? "0 0 28px var(--accent-glow)" : "none",
          borderRadius: "16px",
          cursor: "pointer",
          marginBottom: "32px",
          transition: "all 0.22s ease",
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
            width: "56px",
            height: "56px",
            borderRadius: "16px",
            background: "rgba(99, 102, 241, 0.14)",
            border: "1px solid rgba(99, 102, 241, 0.3)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 16px",
          }}
        >
          {isUploading ? (
            <Loader2 size={28} color="var(--accent-light)" style={{ animation: "spin 1s linear infinite" }} />
          ) : (
            <UploadCloud size={28} color="var(--accent-light)" />
          )}
        </div>

        <h3 style={{ fontSize: "17px", fontWeight: 700, marginBottom: "6px", color: "#FFFFFF" }}>
          {isUploading
            ? `Uploading "${uploadFileName}" & generating SHA-256 digest...`
            : "Drag & drop files to ingest, or click to browse"}
        </h3>
        <p style={{ fontSize: "13.5px", color: "var(--text-muted)", maxWidth: "480px", margin: "0 auto 16px" }}>
          Extracts tables, headers, and bounding boxes via layout vision model. Supports PDF, DOCX, and TXT (Max 50MB).
        </p>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
          <span className="badge badge-accent">PDF with Vision</span>
          <span className="badge badge-cyan">DOCX</span>
          <span className="badge">Plain TXT</span>
        </div>
      </div>

      {/* ── Search, Filters & View Toggle ────────────────────────── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "20px",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        {/* Search Input */}
        <div style={{ position: "relative", minWidth: "260px", flex: "1 1 300px" }}>
          <Search
            size={16}
            color="var(--text-muted)"
            style={{ position: "absolute", left: "12px", top: "12px" }}
          />
          <input
            type="text"
            placeholder="Search documents by filename..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input-field"
            style={{ paddingLeft: "38px", height: "40px" }}
          />
        </div>

        {/* Status Filter Tabs */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            background: "rgba(255, 255, 255, 0.03)",
            padding: "4px",
            borderRadius: "10px",
            border: "1px solid var(--border)",
          }}
        >
          {["all", "ready", "processing", "failed"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              style={{
                background: statusFilter === st ? "var(--surface-hover)" : "transparent",
                border: "none",
                borderRadius: "7px",
                padding: "6px 12px",
                color: statusFilter === st ? "#FFFFFF" : "var(--text-muted)",
                fontSize: "12.5px",
                fontWeight: statusFilter === st ? 600 : 500,
                cursor: "pointer",
                textTransform: "capitalize",
                transition: "all 0.15s ease",
              }}
            >
              {st}
            </button>
          ))}
        </div>

        {/* View Mode Switcher */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            background: "rgba(255, 255, 255, 0.03)",
            borderRadius: "8px",
            border: "1px solid var(--border)",
            padding: "2px",
          }}
        >
          <button
            onClick={() => setViewMode("list")}
            className="btn btn-ghost"
            style={{
              padding: "6px 10px",
              background: viewMode === "list" ? "rgba(255, 255, 255, 0.08)" : "transparent",
              color: viewMode === "list" ? "#FFFFFF" : "var(--text-muted)",
              borderRadius: "6px",
            }}
            title="List View"
          >
            <List size={16} />
          </button>
          <button
            onClick={() => setViewMode("grid")}
            className="btn btn-ghost"
            style={{
              padding: "6px 10px",
              background: viewMode === "grid" ? "rgba(255, 255, 255, 0.08)" : "transparent",
              color: viewMode === "grid" ? "#FFFFFF" : "var(--text-muted)",
              borderRadius: "6px",
            }}
            title="Grid View"
          >
            <LayoutGrid size={16} />
          </button>
        </div>
      </div>

      {/* ── Documents Content View ───────────────────────────────── */}
      {isLoadingList ? (
        <div style={{ textAlign: "center", padding: "60px 0", color: "var(--text-muted)" }}>
          <Loader2 size={32} style={{ animation: "spin 1s linear infinite", margin: "0 auto 14px" }} />
          <p style={{ fontSize: "14px" }}>Loading catalog...</p>
        </div>
      ) : filteredDocs.length === 0 ? (
        <div
          className="card"
          style={{
            padding: "56px 24px",
            textAlign: "center",
            backgroundColor: "rgba(18, 20, 31, 0.5)",
          }}
        >
          <FileText size={44} color="var(--text-muted)" style={{ margin: "0 auto 16px" }} />
          <h3 style={{ fontSize: "17px", fontWeight: 700, marginBottom: "6px", color: "#FFFFFF" }}>
            {searchQuery ? "No matching documents found" : "No documents uploaded yet"}
          </h3>
          <p style={{ fontSize: "13.5px", color: "var(--text-muted)", maxWidth: "420px", margin: "0 auto 20px" }}>
            {searchQuery
              ? "Try searching for another keyword or change your status filter."
              : "Upload your first PDF or DOCX file to enable semantic search and AI grounded answers."}
          </p>
        </div>
      ) : viewMode === "list" ? (
        /* Detailed List View */
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {filteredDocs.map((doc) => (
            <div
              key={doc.document_id}
              className="card card-interactive"
              onClick={() => router.push(`/documents/${doc.document_id}`)}
              style={{
                padding: "16px 20px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                backgroundColor: "var(--surface)",
                gap: "16px",
              }}
            >
              {/* File Info */}
              <div style={{ display: "flex", alignItems: "center", gap: "16px", minWidth: 0, flex: 1 }}>
                <div
                  style={{
                    width: "44px",
                    height: "44px",
                    borderRadius: "12px",
                    backgroundColor: "rgba(99, 102, 241, 0.12)",
                    border: "1px solid rgba(99, 102, 241, 0.28)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  <FileText size={22} color="var(--accent-light)" />
                </div>

                <div style={{ minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: "15px",
                      fontWeight: 700,
                      color: "#FFFFFF",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      marginBottom: "4px",
                    }}
                  >
                    {doc.filename}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "12px", fontSize: "12px", color: "var(--text-muted)" }}>
                    <span style={{ textTransform: "uppercase", fontWeight: 600 }}>{doc.file_type}</span>
                    <span>•</span>
                    <span>{doc.total_pages} {doc.total_pages === 1 ? "page" : "pages"}</span>
                    <span>•</span>
                    <span>{doc.chunk_count} chunks</span>
                    <span>•</span>
                    <button
                      onClick={(e) => handleCopyId(doc.document_id, e)}
                      title="Copy document UUID"
                      style={{
                        background: "transparent",
                        border: "none",
                        color: "var(--text-muted)",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                        fontSize: "11px",
                      }}
                    >
                      {copiedId === doc.document_id ? <Check size={11} color="#10B981" /> : <Copy size={11} />}
                      <span>{doc.document_id.slice(0, 8)}...</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Status & Actions */}
              <div style={{ display: "flex", alignItems: "center", gap: "14px", flexShrink: 0 }}>
                {getStatusBadge(doc.status)}

                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      router.push(`/documents/${doc.document_id}`);
                    }}
                    className="btn btn-secondary"
                    style={{ padding: "8px 12px", fontSize: "12.5px" }}
                  >
                    <Eye size={14} />
                    <span>View PDF</span>
                  </button>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      router.push(`/chat`);
                    }}
                    className="btn btn-primary"
                    style={{ padding: "8px 14px", fontSize: "12.5px" }}
                  >
                    <MessageSquare size={14} />
                    <span>Ask RAG</span>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Rich Grid View */
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
            gap: "16px",
          }}
        >
          {filteredDocs.map((doc) => (
            <div
              key={doc.document_id}
              className="card card-interactive"
              onClick={() => router.push(`/documents/${doc.document_id}`)}
              style={{
                padding: "20px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                backgroundColor: "var(--surface)",
                minHeight: "180px",
              }}
            >
              <div>
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "14px" }}>
                  <div
                    style={{
                      width: "42px",
                      height: "42px",
                      borderRadius: "10px",
                      backgroundColor: "rgba(99, 102, 241, 0.12)",
                      border: "1px solid rgba(99, 102, 241, 0.28)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <FileText size={20} color="var(--accent-light)" />
                  </div>
                  {getStatusBadge(doc.status)}
                </div>

                <h3
                  style={{
                    fontSize: "15px",
                    fontWeight: 700,
                    color: "#FFFFFF",
                    marginBottom: "6px",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                  title={doc.filename}
                >
                  {doc.filename}
                </h3>

                <p style={{ fontSize: "12.5px", color: "var(--text-muted)" }}>
                  {doc.total_pages} {doc.total_pages === 1 ? "page" : "pages"} • {doc.chunk_count} indexed chunks
                </p>
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginTop: "16px",
                  paddingTop: "12px",
                  borderTop: "1px solid rgba(255, 255, 255, 0.06)",
                }}
              >
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    router.push(`/documents/${doc.document_id}`);
                  }}
                  className="btn btn-ghost"
                  style={{ padding: "6px 8px", fontSize: "12px" }}
                >
                  <Eye size={13} />
                  <span>Inspect</span>
                </button>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    router.push(`/chat`);
                  }}
                  className="btn btn-primary"
                  style={{ padding: "6px 12px", fontSize: "12px" }}
                >
                  <MessageSquare size={13} />
                  <span>Chat</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Slide-over Document & Knowledge Graph Drawer */}
      <DocumentDrawer
        document={selectedDoc}
        onClose={() => setSelectedDoc(null)}
      />
    </div>
  );
}
