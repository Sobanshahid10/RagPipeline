"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { CitationBlock, QueryMetadata } from "@/lib/api";
import { 
  User, 
  Bot, 
  FileText, 
  Copy, 
  Check, 
  Clock, 
  Cpu, 
  Sparkles,
  ChevronRight
} from "lucide-react";

export interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  citations?: CitationBlock[];
  isStreaming?: boolean;
  metadata?: QueryMetadata;
  onCitationClick?: (citation: CitationBlock) => void;
  activeCitation?: CitationBlock | null;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  role,
  content,
  citations = [],
  isStreaming = false,
  metadata,
  onCitationClick,
  activeCitation,
}) => {
  const [copied, setCopied] = useState(false);
  const isUser = role === "user";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error("Clipboard copy failed:", e);
    }
  };

  // Clean citation tags from user-facing text if raw tags like [SOURCE:...:1] are present
  const displayContent = content.replace(/\[SOURCE:[^:\]\s]+:\d+\]/g, "").trimEnd();

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      style={{
        display: "flex",
        flexDirection: isUser ? "row-reverse" : "row",
        alignItems: "flex-start",
        gap: "14px",
        marginBottom: "24px",
        width: "100%",
      }}
    >
      {/* Role Avatar */}
      <div
        style={{
          width: "36px",
          height: "36px",
          borderRadius: "10px",
          backgroundColor: isUser ? "#2A2A3C" : "var(--accent)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
          border: isUser
            ? "1px solid rgba(255, 255, 255, 0.1)"
            : "1px solid rgba(167, 139, 250, 0.5)",
          boxShadow: isUser ? "none" : "0 0 14px var(--accent-glow)",
        }}
      >
        {isUser ? (
          <User size={18} color="#E4E4F0" />
        ) : (
          <Bot size={18} color="#FFFFFF" />
        )}
      </div>

      {/* Message Bubble Container */}
      <div
        style={{
          maxWidth: isUser ? "75%" : "82%",
          display: "flex",
          flexDirection: "column",
          alignItems: isUser ? "flex-end" : "flex-start",
        }}
      >
        {/* Header (Author & Meta) */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            marginBottom: "6px",
            fontSize: "12px",
            color: "var(--muted)",
          }}
        >
          <span style={{ fontWeight: 600, color: isUser ? "var(--text)" : "var(--accent-light)" }}>
            {isUser ? "You" : "Assistant"}
          </span>
          {metadata?.route_used && (
            <span
              style={{
                fontSize: "10px",
                padding: "1px 6px",
                borderRadius: "4px",
                backgroundColor: "rgba(99, 102, 241, 0.15)",
                color: "var(--accent-light)",
                border: "1px solid rgba(99, 102, 241, 0.3)",
              }}
            >
              {metadata.route_used}
            </span>
          )}
        </div>

        {/* Content Box */}
        <div
          className="card"
          style={{
            padding: "16px 20px",
            backgroundColor: isUser ? "rgba(99, 102, 241, 0.12)" : "var(--surface)",
            border: isUser
              ? "1px solid rgba(99, 102, 241, 0.3)"
              : "1px solid var(--border)",
            borderRadius: isUser ? "16px 4px 16px 16px" : "4px 16px 16px 16px",
            color: "var(--text)",
            lineHeight: 1.6,
            fontSize: "14px",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            position: "relative",
          }}
        >
          {displayContent}

          {/* Streaming Cursor */}
          {isStreaming && <span className="streaming-cursor" />}

          {/* Assistant Action Bar (Copy & Metadata) */}
          {!isUser && !isStreaming && content && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginTop: "12px",
                paddingTop: "8px",
                borderTop: "1px solid rgba(255, 255, 255, 0.05)",
                fontSize: "11px",
                color: "var(--muted)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                {metadata?.ttft_ms !== undefined && (
                  <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                    <Clock size={12} />
                    TTFT: {metadata.ttft_ms}ms
                  </span>
                )}
                {metadata?.total_latency_ms !== undefined && (
                  <span>Latency: {metadata.total_latency_ms}ms</span>
                )}
                {metadata?.completion_tokens !== undefined && (
                  <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                    <Cpu size={12} />
                    {metadata.completion_tokens} tokens
                  </span>
                )}
              </div>

              <button
                onClick={handleCopy}
                style={{
                  background: "transparent",
                  border: "none",
                  color: copied ? "var(--success)" : "var(--muted)",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                  fontSize: "11px",
                }}
              >
                {copied ? <Check size={12} /> : <Copy size={12} />}
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
          )}
        </div>

        {/* Live Citation Chips */}
        {citations && citations.length > 0 && (
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: "8px",
              marginTop: "10px",
            }}
          >
            <span
              style={{
                fontSize: "11px",
                color: "var(--muted)",
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              <FileText size={12} color="var(--accent-light)" />
              Sources:
            </span>

            {citations.map((citation, idx) => {
              const filename = citation.source_filename || "document.pdf";
              const cleanName = filename.length > 22 ? `${filename.slice(0, 19)}...` : filename;
              const isSelected =
                activeCitation?.chunk_id === citation.chunk_id ||
                (activeCitation?.document_id === citation.document_id &&
                  activeCitation?.page_number === citation.page_number);

              return (
                <button
                  key={`${citation.chunk_id}-${citation.page_number}-${idx}`}
                  onClick={() => onCitationClick?.(citation)}
                  className={`citation-chip ${isSelected ? "active" : ""}`}
                  title={citation.excerpt || `${filename} (Page ${citation.page_number})`}
                >
                  <span>{`${cleanName}:${citation.page_number}`}</span>
                  <ChevronRight size={12} />
                </button>
              );
            })}
          </div>
        )}
      </div>
    </motion.div>
  );
};
