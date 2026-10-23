"use client";

import React, { useState, useEffect, useRef } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { useAuth } from "@/context/AuthContext";
import { CitationBlock, BoundingBox } from "@/lib/api";
import { 
  ChevronLeft, 
  ChevronRight, 
  ZoomIn, 
  ZoomOut, 
  Maximize2, 
  Loader2, 
  AlertCircle,
  FileText,
  Bookmark,
  Download,
  Layers,
  ExternalLink
} from "lucide-react";

// Configure PDF.js worker
if (typeof window !== "undefined") {
  pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();
}

export interface PDFViewerProps {
  fileUrl: string;
  filename?: string;
  initialPage?: number;
  highlights?: CitationBlock[];
  activeCitation?: CitationBlock | null;
  onPageChange?: (pageNumber: number) => void;
}

export const PDFViewer: React.FC<PDFViewerProps> = ({
  fileUrl,
  filename = "Document.pdf",
  initialPage = 1,
  highlights = [],
  activeCitation,
  onPageChange,
}) => {
  const { token } = useAuth();
  const [resolvedFileUrl, setResolvedFileUrl] = useState<string | null>(null);
  useEffect(() => {
    setResolvedFileUrl(null);
    if (!token) return;
    const controller = new AbortController();
    let objectUrl: string | null = null;
    setIsLoading(true); setError(null);
    fetch(fileUrl, {headers:{Authorization:`Bearer ${token}`}, signal:controller.signal})
      .then(response => { if (!response.ok) throw new Error("Document download unavailable"); return response.blob(); })
      .then(blob => { if (controller.signal.aborted) return; objectUrl = URL.createObjectURL(blob); setResolvedFileUrl(objectUrl); setIsLoading(false); if (!filename.toLowerCase().endsWith(".pdf")) setError("Preview is available for PDFs. Download this original document to view it."); })
      .catch(err => { if (!controller.signal.aborted) {setError(err.message); setIsLoading(false);} });
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [fileUrl, token, filename]);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState<number>(initialPage);
  const [scale, setScale] = useState<number>(1.0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [jumpPageInput, setJumpPageInput] = useState<string>(String(initialPage));
  const containerRef = useRef<HTMLDivElement>(null);

  // Sync with prop changes
  useEffect(() => {
    if (initialPage && initialPage >= 1) {
      setPageNumber(initialPage);
      setJumpPageInput(String(initialPage));
    }
  }, [initialPage]);

  // When active citation updates, jump to its page
  useEffect(() => {
    if (activeCitation?.page_number) {
      setPageNumber(activeCitation.page_number);
      setJumpPageInput(String(activeCitation.page_number));
    }
  }, [activeCitation]);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setIsLoading(false);
    setError(null);
  };

  const onDocumentLoadError = (err: Error) => {
    console.warn("PDF Load Notice:", err.message);
    setError("PDF preview renderer encountered a loading issue. You can inspect chunk coordinates below or download the file directly.");
    setIsLoading(false);
  };

  const changePage = (offset: number) => {
    setPageNumber((prev) => {
      const target = prev + offset;
      const clamped = Math.min(Math.max(1, target), numPages || 1);
      onPageChange?.(clamped);
      setJumpPageInput(String(clamped));
      return clamped;
    });
  };

  const handleJumpPage = (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = parseInt(jumpPageInput, 10);
    if (!isNaN(parsed) && parsed >= 1 && parsed <= (numPages || 999)) {
      setPageNumber(parsed);
      onPageChange?.(parsed);
    } else {
      setJumpPageInput(String(pageNumber));
    }
  };

  const zoomIn = () => setScale((prev) => Math.min(prev + 0.15, 2.2));
  const zoomOut = () => setScale((prev) => Math.max(prev - 0.15, 0.65));
  const resetZoom = () => setScale(1.0);

  // Filter citations matching current page
  const pageHighlights = highlights.filter(
    (h) => Number(h.page_number) === Number(pageNumber)
  );

  // Extract normalized 0-100% coordinates for bounding boxes
  const getNormalizedCoords = (bbox?: BoundingBox) => {
    if (!bbox || Object.keys(bbox).length === 0) return null;
    let ymin = bbox.ymin ?? bbox.y ?? 0;
    let xmin = bbox.xmin ?? bbox.x ?? 0;
    let ymax = bbox.ymax ?? (bbox.y !== undefined && bbox.height !== undefined ? bbox.y + bbox.height : 1);
    let xmax = bbox.xmax ?? (bbox.x !== undefined && bbox.width !== undefined ? bbox.x + bbox.width : 1);

    if (ymin > 1.0) ymin = ymin / 1000.0;
    if (xmin > 1.0) xmin = xmin / 1000.0;
    if (ymax > 1.0) ymax = ymax / 1000.0;
    if (xmax > 1.0) xmax = xmax / 1000.0;

    const top = `${ymin * 100}%`;
    const left = `${xmin * 100}%`;
    const width = `${Math.max((xmax - xmin) * 100, 4)}%`;
    const height = `${Math.max((ymax - ymin) * 100, 3)}%`;

    return { top, left, width, height };
  };

  return (
    <div
      ref={containerRef}
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        width: "100%",
        backgroundColor: "#0B0D14",
        borderRadius: "6px",
        overflow: "hidden",
        border: "1px solid var(--border)",
        position: "relative",
      }}
    >
      {/* ── Top Header & Navigation Toolbar ────────────────────── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 16px",
          backgroundColor: "var(--surface)",
          borderBottom: "1px solid var(--border)",
          zIndex: 20,
          gap: "10px",
          flexWrap: "wrap",
        }}
      >
        {/* Document Filename */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px", minWidth: 0, maxWidth: "38%" }}>
          <FileText size={16} color="var(--accent-light)" style={{ flexShrink: 0 }} />
          <span
            style={{
              fontSize: "13px",
              fontWeight: 600,
              color: "#FFFFFF",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {filename}
          </span>
        </div>

        {/* Page Nav & Jump Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <button
            onClick={() => changePage(-1)}
            disabled={pageNumber <= 1}
            className="btn btn-secondary"
            style={{ padding: "6px 8px", height: "30px" }}
            title="Previous Page"
          >
            <ChevronLeft size={16} />
          </button>

          <form onSubmit={handleJumpPage} style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <input
              type="text"
              value={jumpPageInput}
              onChange={(e) => setJumpPageInput(e.target.value)}
              onBlur={handleJumpPage}
              style={{
                width: "36px",
                height: "30px",
                textAlign: "center",
                background: "rgba(255, 255, 255, 0.05)",
                border: "1px solid var(--border)",
                borderRadius: "6px",
                color: "#FFFFFF",
                fontSize: "12.5px",
                fontWeight: 600,
                outline: "none",
              }}
            />
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              / {numPages || "--"}
            </span>
          </form>

          <button
            onClick={() => changePage(1)}
            disabled={!numPages || pageNumber >= numPages}
            className="btn btn-secondary"
            style={{ padding: "6px 8px", height: "30px" }}
            title="Next Page"
          >
            <ChevronRight size={16} />
          </button>
        </div>

        {/* Zoom & Download Tools */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <button
            onClick={zoomOut}
            className="btn btn-secondary"
            style={{ padding: "6px 8px", height: "30px" }}
            title="Zoom Out"
          >
            <ZoomOut size={14} />
          </button>
          <span style={{ fontSize: "12px", color: "var(--text-muted)", width: "38px", textAlign: "center", fontWeight: 600 }}>
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={zoomIn}
            className="btn btn-secondary"
            style={{ padding: "6px 8px", height: "30px" }}
            title="Zoom In"
          >
            <ZoomIn size={14} />
          </button>
          <button
            onClick={resetZoom}
            className="btn btn-ghost"
            style={{ padding: "6px 8px", height: "30px" }}
            title="Reset Zoom"
          >
            <Maximize2 size={13} />
          </button>

          <a
            href={resolvedFileUrl || undefined}
            target="_blank"
            rel="noopener noreferrer"
            download={filename}
            className="btn btn-secondary"
            style={{ padding: "6px 10px", height: "30px", fontSize: "12px", textDecoration: "none" }}
            title="Download Original PDF"
          >
            <Download size={13} />
          </a>
        </div>
      </div>

      {/* ── Active Citation Notification Bar ───────────────────── */}
      {pageHighlights.length > 0 && (
        <div
          style={{
            backgroundColor: "var(--surface-raised)",
            borderBottom: "1px solid var(--border)",
            padding: "8px 16px",
            fontSize: "12px",
            color: "var(--foreground)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Bookmark size={14} style={{ color: "var(--text-muted)" }} />
            <span style={{ fontWeight: 600 }}>
              {pageHighlights.length} verifiable citation {pageHighlights.length > 1 ? "overlays" : "overlay"} on page {pageNumber}
            </span>
          </div>

          {activeCitation?.excerpt && (
            <span
              style={{
                fontSize: "11px",
                color: "var(--text-secondary)",
                maxWidth: "320px",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                fontStyle: "italic",
              }}
            >
              &ldquo;{activeCitation.excerpt}&rdquo;
            </span>
          )}
        </div>
      )}

      {/* ── Main Canvas Viewport ────────────────────────────────── */}
      <div
        style={{
          flex: 1,
          overflow: "auto",
          display: "flex",
          justifyContent: "center",
          alignItems: "flex-start",
          padding: "24px",
          position: "relative",
        }}
      >
        {isLoading && !error && (
          <div
            style={{
              position: "absolute",
              top: "40%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "12px",
              color: "var(--accent-light)",
            }}
          >
            <Loader2 size={32} style={{ animation: "spin 1s linear infinite" }} />
            <span style={{ fontSize: "13.5px", color: "var(--text-secondary)" }}>
              Rendering layout-aware PDF...
            </span>
          </div>
        )}

        {/* Fallback View if PDF is unreachable or worker has issues */}
        {error ? (
          <div
            style={{
              width: "100%",
              maxWidth: "580px",
              margin: "24px auto",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            <div
              className="card"
              style={{
                padding: "24px",
                backgroundColor: "rgba(18, 20, 31, 0.8)",
                border: "1px solid var(--border)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
                <Layers size={20} color="var(--accent-light)" />
                <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF" }}>
                  Layout & Citation Inspector
                </h3>
              </div>
              <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "16px", lineHeight: 1.5 }}>
                {error}
              </p>

              <div style={{ display: "flex", gap: "10px" }}>
                <a
                  href={resolvedFileUrl || undefined}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-primary"
                  style={{ fontSize: "12.5px", padding: "8px 14px", textDecoration: "none" }}
                >
                  <Download size={14} />
                  <span>Download / Open PDF</span>
                </a>
              </div>
            </div>

            {/* List of cited excerpts & bounding boxes */}
            {highlights.length > 0 && (
              <div
                className="card"
                style={{
                  padding: "20px",
                  backgroundColor: "rgba(18, 20, 31, 0.6)",
                }}
              >
                <h4 style={{ fontSize: "13px", fontWeight: 700, color: "var(--accent-light)", marginBottom: "12px" }}>
                  Active Citation Chunks ({highlights.length})
                </h4>
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {highlights.map((h, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "10px 14px",
                        borderRadius: "8px",
                        backgroundColor: "rgba(255, 255, 255, 0.03)",
                        border: "1px solid rgba(255, 255, 255, 0.06)",
                        fontSize: "12.5px",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                        <span style={{ fontWeight: 600, color: "#FFFFFF" }}>Page {h.page_number}</span>
                        <span style={{ color: "var(--text-muted)", fontSize: "11px" }}>Chunk ID: {h.chunk_id.slice(0, 8)}...</span>
                      </div>
                      {h.excerpt && (
                        <p style={{ color: "var(--text-secondary)", fontStyle: "italic", lineHeight: 1.4 }}>
                          &ldquo;{h.excerpt}&rdquo;
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <Document
            file={resolvedFileUrl}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading=""
            className="pdf-document"
          >
            <div
              style={{
                position: "relative",
                boxShadow: "0 12px 40px rgba(0, 0, 0, 0.6)",
                borderRadius: "6px",
                overflow: "hidden",
                border: "1px solid rgba(255, 255, 255, 0.1)",
              }}
            >
              <Page
                pageNumber={pageNumber}
                scale={scale}
                renderAnnotationLayer={false}
                renderTextLayer={false}
              />

              {/* Bounding Box Highlights Overlay Layer */}
              {pageHighlights.map((hl, i) => {
                const coords = getNormalizedCoords(hl.bounding_box);
                if (!coords) return null;
                const isActive = activeCitation?.chunk_id === hl.chunk_id;

                return (
                  <div
                    key={`hl-${hl.chunk_id || i}`}
                    className="pdf-highlight"
                    style={{
                      top: coords.top,
                      left: coords.left,
                      width: coords.width,
                      height: coords.height,
                      backgroundColor: isActive ? "rgba(245, 158, 11, 0.25)" : "rgba(245, 158, 11, 0.15)",
                      border: isActive ? "2px solid #F59E0B" : "1.5px solid rgba(245, 158, 11, 0.6)",
                      borderRadius: "2px",
                      boxShadow: "none",
                    }}
                    title={hl.excerpt || `Cited chunk on page ${hl.page_number}`}
                  />
                );
              })}
            </div>
          </Document>
        )}
      </div>
    </div>
  );
};
