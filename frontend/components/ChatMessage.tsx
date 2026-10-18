"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { CitationBlock, QueryMetadata } from "@/lib/api";
import { useToast } from "@/context/ToastContext";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import { FileText, Copy, Check, Sparkles } from "lucide-react";

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
  onCitationClick,
  activeCitation,
}) => {
  const { showToast } = useToast();
  const [copied, setCopied] = useState(false);
  const isUser = role === "user";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      showToast("success", "Copied to clipboard", "Response copied successfully.");
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error("Clipboard copy failed:", e);
    }
  };

  // Strip raw citation tags [SOURCE:...:1] before markdown rendering
  const displayContent = content.replace(/\[SOURCE:[^:\]\s]+:\d+\]/g, "").trimEnd();

  // Modern LLM User Message (Clean, comfortable bubble aligned to right)
  if (isUser) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.16, ease: "easeOut" }}
        style={{
          display: "flex",
          justifyContent: "flex-end",
          width: "100%",
          marginBottom: "20px",
        }}
      >
        <div
          style={{
            maxWidth: "78%",
            backgroundColor: "rgba(255, 255, 255, 0.08)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderRadius: "18px 18px 4px 18px",
            padding: "12px 18px",
            fontSize: "14.5px",
            lineHeight: 1.55,
            color: "#FFFFFF",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {content}
        </div>
      </motion.div>
    );
  }

  // Modern LLM Assistant Message (Open, natural typography without boxy cards)
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: "14px",
        width: "100%",
        marginBottom: "28px",
      }}
    >
      {/* Subtle Assistant Indicator */}
      <div
        style={{
          width: "28px",
          height: "28px",
          borderRadius: "50%",
          backgroundColor: "rgba(255, 255, 255, 0.06)",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
          marginTop: "3px",
        }}
      >
        <Sparkles size={13} color="#FFFFFF" />
      </div>

      {/* Main Content Area */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Rendered Text */}
        <div
          style={{
            fontSize: "14.5px",
            lineHeight: 1.7,
            color: "var(--foreground)",
          }}
        >
          <MarkdownRenderer content={displayContent} />
          {isStreaming && <span className="streaming-cursor" />}
        </div>

        {/* Citations as Clean, Modern Source Pills */}
        {citations && citations.length > 0 && (
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: "6px",
              marginTop: "14px",
            }}
          >
            {citations.map((citation, idx) => {
              const filename = citation.source_filename || "document.pdf";
              const cleanName = filename.length > 26 ? `${filename.slice(0, 23)}...` : filename;
              const isSelected =
                activeCitation?.chunk_id === citation.chunk_id ||
                (activeCitation?.document_id === citation.document_id &&
                  activeCitation?.page_number === citation.page_number);

              return (
                <button
                  key={`${citation.chunk_id}-${citation.page_number}-${idx}`}
                  onClick={() => onCitationClick?.(citation)}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "5px",
                    padding: "3px 10px",
                    borderRadius: "14px",
                    fontSize: "11.5px",
                    backgroundColor: isSelected ? "rgba(255, 255, 255, 0.12)" : "rgba(255, 255, 255, 0.04)",
                    border: isSelected ? "1px solid rgba(255, 255, 255, 0.28)" : "1px solid var(--border)",
                    color: isSelected ? "#FFFFFF" : "var(--text-secondary)",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.08)";
                    e.currentTarget.style.color = "#FFFFFF";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = isSelected ? "rgba(255, 255, 255, 0.12)" : "rgba(255, 255, 255, 0.04)";
                    e.currentTarget.style.color = isSelected ? "#FFFFFF" : "var(--text-secondary)";
                  }}
                  title={
                    citation.excerpt ||
                    `${filename}${citation.page_number ? ` (Page ${citation.page_number})` : ""} - Click to inspect source`
                  }
                >
                  <FileText size={11} style={{ color: "var(--accent-light)" }} />
                  <span style={{ fontWeight: 500 }}>{cleanName}</span>
                  {citation.page_number && (
                    <span style={{ opacity: 0.6 }}>· p. {citation.page_number}</span>
                  )}
                </button>
              );
            })}
          </div>
        )}

        {/* Minimal Actions: Sleek Copy Button */}
        {!isStreaming && content && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              marginTop: "12px",
            }}
          >
            <button
              onClick={handleCopy}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
                padding: "4px 8px",
                borderRadius: "6px",
                background: "transparent",
                border: "none",
                color: copied ? "var(--emerald-light)" : "var(--text-muted)",
                cursor: "pointer",
                fontSize: "12px",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => {
                if (!copied) e.currentTarget.style.color = "#FFFFFF";
              }}
              onMouseLeave={(e) => {
                if (!copied) e.currentTarget.style.color = "var(--text-muted)";
              }}
              title="Copy response to clipboard"
              aria-label="Copy response to clipboard"
            >
              {copied ? <Check size={13} color="#10B981" /> : <Copy size={13} />}
              <span>{copied ? "Copied" : "Copy"}</span>
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
};
