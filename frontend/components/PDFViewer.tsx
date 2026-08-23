"use client";

import React, { useState, useEffect, useRef } from "react";
import { Document, Page, pdfjs } from "react-pdf";
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
  Bookmark
} from "lucide-react";

// Configure PDFjs worker for client-side execution in Next.js
if (typeof window !== "undefined") {
  pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
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
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState<number>(initialPage);
  const [scale, setScale] = useState<number>(1.0);
  const [pageWidth, setPageWidth] = useState<number>(600);
  const [pageHeight, setPageHeight] = useState<number>(800);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Sync with prop changes
  useEffect(() => {
    if (initialPage && initialPage >= 1) {
      setPageNumber(initialPage);
    }
  }, [initialPage]);

  // When an active citation is selected, jump to its page
  useEffect(() => {
    if (activeCitation?.page_number) {
      setPageNumber(activeCitation.page_number);
    }
  }, [activeCitation]);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setIsLoading(false);
    setError(null);
  };

  const onDocumentLoadError = (err: Error) => {
    console.error("PDF Load Error:", err);
    setError("Failed to load PDF file. Ensure the backend is reachable.");
    setIsLoading(false);
  };

  const onPageLoadSuccess = (page: any) => {
    if (page?.width && page?.height) {
      setPageWidth(page.width);
      setPageHeight(page.height);
    }
  };

  const changePage = (offset: number) => {
    setPageNumber((prev) => {
      const target = prev + offset;
      const clamped = Math.min(Math.max(1, target), numPages || 1);
      onPageChange?.(clamped);
      return clamped;
    });
  };

  const zoomIn = () => setScale((prev) => Math.min(prev + 0.15, 2.2));
  const zoomOut = () => setScale((prev) => Math.max(prev - 0.15, 0.6));
  const resetZoom = () => setScale(1.0);

  // Filter citations matching the current page
  const pageHighlights = highlights.filter(
    (h) => Number(h.page_number) === Number(pageNumber)
  );

  // Helper to extract normalized coordinates (0.0 - 1.0)
  const getNormalizedCoords = (bbox?: BoundingBox) => {
    if (!bbox) return null;
    let ymin = bbox.ymin ?? bbox.y ?? 0;
    let xmin = bbox.xmin ?? bbox.x ?? 0;
    let ymax = bbox.ymax ?? (bbox.y !== undefined && bbox.height !== undefined ? bbox.y + bbox.height : 1);
    let xmax = bbox.xmax ?? (bbox.x !== undefined && bbox.width !== undefined ? bbox.x + bbox.width : 1);

    // Normalize if scale is 1000-based
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
        backgroundColor: "#0F0F16",
        borderRadius: "12px",
        overflow: "hidden",
        border: "1px solid var(--border)",
      }}
    >
      {/* Top Header & Navigation Bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 16px",
          backgroundColor: "var(--surface)",
          borderBottom: "1px solid var(--border)",
          zIndex: 20,
        }}
      >
        {/* Document Title */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px", maxWidth: "40%" }}>
          <FileText size={16} color="var(--accent-light)" />
          <span
            style={{
              fontSize: "13px",
              fontWeight: 600,
              color: "var(--text)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {filename}
          </span>
        </div>

        {/* Page Nav Controls */}
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

          <span style={{ fontSize: "13px", color: "var(--text-secondary)", minWidth: "70px", textAlign: "center" }}>
            {numPages ? `${pageNumber} / ${numPages}` : "-- / --"}
          </span>

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

        {/* Zoom & Fit Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <button
            onClick={zoomOut}
            className="btn btn-secondary"
            style={{ padding: "6px 8px", height: "30px" }}
            title="Zoom Out"
          >
            <ZoomOut size={15} />
          </button>
          <span style={{ fontSize: "12px", color: "var(--muted)", width: "40px", textAlign: "center" }}>
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={zoomIn}
            className="btn btn-secondary"
            style={{ padding: "6px 8px", height: "30px" }}
            title="Zoom In"
          >
            <ZoomIn size={15} />
          </button>
          <button
            onClick={resetZoom}
            className="btn btn-ghost"
            style={{ padding: "6px 8px", height: "30px" }}
            title="Reset Zoom"
          >
            <Maximize2 size={14} />
          </button>
        </div>
      </div>

      {/* Highlights Notification Pill */}
      {pageHighlights.length > 0 && (
        <div
          style={{
            backgroundColor: "rgba(99, 102, 241, 0.12)",
            borderBottom: "1px solid rgba(99, 102, 241, 0.25)",
            padding: "6px 16px",
            fontSize: "12px",
            color: "var(--accent-light)",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <Bookmark size={14} />
          <span>
            {pageHighlights.length} citation {pageHighlights.length > 1 ? "highlights" : "highlight"} on page {pageNumber}
          </span>
        </div>
      )}

      {/* Main Canvas Scroll View */}
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
        {isLoading && (
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
            <Loader2 size={32} className="animate-spin" style={{ animation: "spin 1s linear infinite" }} />
            <span style={{ fontSize: "14px", color: "var(--text-secondary)" }}>Rendering PDF...</span>
          </div>
        )}

        {error && (
          <div
            style={{
              position: "absolute",
              top: "35%",
              maxWidth: "400px",
              textAlign: "center",
              padding: "24px",
              backgroundColor: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              borderRadius: "12px",
              color: "#F87171",
            }}
          >
            <AlertCircle size={32} style={{ margin: "0 auto 12px" }} />
            <div style={{ fontWeight: 600, marginBottom: "6px" }}>Unable to load document</div>
            <p style={{ fontSize: "13px", opacity: 0.9 }}>{error}</p>
          </div>
        )}

        <Document
          file={fileUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          onLoadError={onDocumentLoadError}
          loading=""
          className="pdf-document"
        >
          <div style={{ position: "relative", boxShadow: "0 8px 32px rgba(0, 0, 0, 0.5)", borderRadius: "4px" }}>
            <Page
              pageNumber={pageNumber}
              scale={scale}
              onLoadSuccess={onPageLoadSuccess}
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
                    boxShadow: isActive
                      ? "0 0 16px 4px rgba(99, 102, 241, 0.9)"
                      : "0 0 8px rgba(99, 102, 241, 0.5)",
                    borderColor: isActive ? "#FFFFFF" : "rgba(99, 102, 241, 0.8)",
                  }}
                  title={hl.excerpt || `Cited on page ${hl.page_number}`}
                />
              );
            })}
          </div>
        </Document>
      </div>
    </div>
  );
};
