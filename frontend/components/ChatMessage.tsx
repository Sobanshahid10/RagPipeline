"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { CitationBlock, QueryMetadata, submitFeedback } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import { RAGPipelineInspector } from "@/components/RAGPipelineInspector";
import { 
  User, 
  Bot, 
  FileText, 
  Copy, 
  Check, 
  Clock, 
  Cpu, 
  Sparkles,
  ChevronRight,
  ThumbsUp,
  ThumbsDown,
  Layers,
  Zap
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

const routePillStyles: Record<string, { label: string; bg: string; color: string; border: string }> = {
  FACTUAL_VECTOR: { label: "Vector Search", bg: "rgba(99, 102, 241, 0.15)", color: "#A5B4FC", border: "rgba(99, 102, 241, 0.35)" },
  MULTI_HOP_GRAPH: { label: "GraphRAG Traversal", bg: "rgba(168, 85, 247, 0.15)", color: "#D8B4FE", border: "rgba(168, 85, 247, 0.35)" },
  ANALYTICAL_SQL: { label: "Analytical SQL", bg: "rgba(245, 158, 11, 0.15)", color: "#FCD34D", border: "rgba(245, 158, 11, 0.35)" },
  GREETING_DIRECT: { label: "Direct LLM", bg: "rgba(16, 185, 129, 0.15)", color: "#6EE7B7", border: "rgba(16, 185, 129, 0.35)" },
  CACHE: { label: "Semantic Cache", bg: "rgba(6, 182, 212, 0.15)", color: "#67E8F9", border: "rgba(6, 182, 212, 0.35)" },
};

export const ChatMessage: React.FC<ChatMessageProps> = ({
  role,
  content,
  citations = [],
  isStreaming = false,
  metadata,
  onCitationClick,
  activeCitation,
}) => {
  const { token, user } = useAuth();
  const { showToast } = useToast();
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<number | null>(null);
  const isUser = role === "user";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      showToast("success", "Copied to clipboard", "Response text copied successfully.");
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error("Clipboard copy failed:", e);
    }
  };

  const handleFeedback = async (score: 1 | -1) => {
    if (!token || !metadata?.interaction_id) {
      setFeedback(score);
      showToast("info", "Feedback recorded", score === 1 ? "Marked as helpful" : "Marked as unhelpful");
      return;
    }

    try {
      setFeedback(score);
      await submitFeedback(metadata.interaction_id, score, token);
      showToast("success", "Feedback saved", score === 1 ? "Thank you for the positive feedback!" : "Feedback noted for model improvements.");
    } catch (err) {
      console.warn("Feedback recording error:", err);
      showToast("info", "Feedback noted locally");
    }
  };

  // Strip raw citation tags [SOURCE:...:1] before markdown rendering
  const displayContent = content.replace(/\[SOURCE:[^:\]\s]+:\d+\]/g, "").trimEnd();

  const routeInfo = metadata?.route_used
    ? routePillStyles[metadata.route_used] || {
        label: metadata.route_used,
        bg: "rgba(99, 102, 241, 0.15)",
        color: "#A5B4FC",
        border: "rgba(99, 102, 241, 0.3)",
      }
    : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: "easeOut" }}
      style={{
        display: "flex",
        flexDirection: isUser ? "row-reverse" : "row",
        alignItems: "flex-start",
        gap: "14px",
        marginBottom: "26px",
        width: "100%",
      }}
    >
      {/* Role Avatar */}
      <div
        style={{
          width: "38px",
          height: "38px",
          borderRadius: "11px",
          backgroundColor: isUser ? "rgba(255, 255, 255, 0.08)" : "var(--accent)",
          background: isUser
            ? "linear-gradient(135deg, rgba(255,255,255,0.12), rgba(255,255,255,0.04))"
            : "var(--accent-gradient)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
          border: isUser
            ? "1px solid rgba(255, 255, 255, 0.12)"
            : "1px solid rgba(255, 255, 255, 0.25)",
          boxShadow: isUser ? "none" : "0 0 18px var(--accent-glow)",
        }}
      >
        {isUser ? (
          <User size={18} color="#E4E4F0" />
        ) : (
          <Bot size={20} color="#FFFFFF" />
        )}
      </div>

      {/* Message Bubble Container */}
      <div
        style={{
          maxWidth: isUser ? "78%" : "88%",
          display: "flex",
          flexDirection: "column",
          alignItems: isUser ? "flex-end" : "flex-start",
        }}
      >
        {/* Header (Author, Route Badge & Meta) */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            marginBottom: "6px",
            fontSize: "12px",
            color: "var(--text-muted)",
          }}
        >
          <span
            style={{
              fontWeight: 600,
              color: isUser ? "var(--text)" : "var(--accent-light)",
              fontFamily: "'Outfit', sans-serif",
            }}
          >
            {isUser ? (user?.email ? user.email.split("@")[0] : "You") : "Nexus Assistant"}
          </span>

          {routeInfo && (
            <span
              style={{
                fontSize: "10.5px",
                fontWeight: 600,
                padding: "2px 8px",
                borderRadius: "5px",
                backgroundColor: routeInfo.bg,
                color: routeInfo.color,
                border: `1px solid ${routeInfo.border}`,
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              <Zap size={10} />
              {routeInfo.label}
            </span>
          )}
        </div>

        {/* Message Content Box */}
        <div
          style={{
            padding: "18px 22px",
            backgroundColor: isUser ? "rgba(99, 102, 241, 0.14)" : "rgba(18, 20, 31, 0.8)",
            backdropFilter: "blur(12px)",
            border: isUser
              ? "1px solid rgba(99, 102, 241, 0.35)"
              : "1px solid var(--border)",
            borderRadius: isUser ? "18px 4px 18px 18px" : "4px 18px 18px 18px",
            boxShadow: isUser ? "0 4px 16px rgba(99, 102, 241, 0.08)" : "var(--shadow-sm)",
            color: "var(--text)",
            position: "relative",
            width: "100%",
          }}
        >
          {isUser ? (
            <div style={{ fontSize: "14px", lineHeight: 1.6, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
              {content}
            </div>
          ) : (
            <div>
              <MarkdownRenderer content={displayContent} />
              {isStreaming && <span className="streaming-cursor" />}
            </div>
          )}

          {/* RAG Reasoning & Retrieval Pipeline Flow */}
          {!isUser && !isStreaming && metadata && (
            <RAGPipelineInspector metadata={metadata} />
          )}

          {/* Assistant Action Bar (Copy, Metrics & Feedback) */}
          {!isUser && !isStreaming && content && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginTop: "16px",
                paddingTop: "10px",
                borderTop: "1px solid rgba(255, 255, 255, 0.06)",
                fontSize: "11.5px",
                color: "var(--text-muted)",
                flexWrap: "wrap",
                gap: "8px",
              }}
            >
              {/* Left Performance Telemetry */}
              <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
                {metadata?.ttft_ms !== undefined && (
                  <span style={{ display: "flex", alignItems: "center", gap: "4px", color: "var(--emerald-light)" }}>
                    <Clock size={12} />
                    TTFT: {metadata.ttft_ms}ms
                  </span>
                )}
                {metadata?.total_latency_ms !== undefined && (
                  <span style={{ color: "var(--text-secondary)" }}>
                    Latency: {metadata.total_latency_ms}ms
                  </span>
                )}
                {metadata?.completion_tokens !== undefined && (
                  <span style={{ display: "flex", alignItems: "center", gap: "4px", color: "var(--accent-light)" }}>
                    <Cpu size={12} />
                    {metadata.completion_tokens} tokens
                  </span>
                )}
              </div>

              {/* Right Action Buttons */}
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                {/* Feedback Buttons */}
                <div style={{ display: "flex", alignItems: "center", gap: "4px", marginRight: "4px" }}>
                  <button
                    onClick={() => handleFeedback(1)}
                    title="Helpful response"
                    style={{
                      background: feedback === 1 ? "rgba(16, 185, 129, 0.2)" : "transparent",
                      border: feedback === 1 ? "1px solid rgba(16, 185, 129, 0.4)" : "1px solid transparent",
                      borderRadius: "6px",
                      color: feedback === 1 ? "#10B981" : "var(--text-muted)",
                      cursor: "pointer",
                      padding: "4px 6px",
                      display: "flex",
                      alignItems: "center",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <ThumbsUp size={13} />
                  </button>
                  <button
                    onClick={() => handleFeedback(-1)}
                    title="Not helpful"
                    style={{
                      background: feedback === -1 ? "rgba(244, 63, 94, 0.2)" : "transparent",
                      border: feedback === -1 ? "1px solid rgba(244, 63, 94, 0.4)" : "1px solid transparent",
                      borderRadius: "6px",
                      color: feedback === -1 ? "#F43F5E" : "var(--text-muted)",
                      cursor: "pointer",
                      padding: "4px 6px",
                      display: "flex",
                      alignItems: "center",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <ThumbsDown size={13} />
                  </button>
                </div>

                {/* Copy Button */}
                <button
                  onClick={handleCopy}
                  style={{
                    background: "rgba(255, 255, 255, 0.04)",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                    borderRadius: "6px",
                    color: copied ? "var(--emerald-light)" : "var(--text-secondary)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "5px",
                    fontSize: "11px",
                    padding: "4px 8px",
                    transition: "all 0.15s ease",
                  }}
                >
                  {copied ? <Check size={12} color="#10B981" /> : <Copy size={12} />}
                  <span>{copied ? "Copied" : "Copy"}</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Live Verifiable Citations */}
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
                color: "var(--text-muted)",
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                gap: "5px",
                textTransform: "uppercase",
                letterSpacing: "0.04em",
              }}
            >
              <FileText size={12} color="var(--accent-light)" />
              Verifiable Sources:
            </span>

            {citations.map((citation, idx) => {
              const filename = citation.source_filename || "document.pdf";
              const cleanName = filename.length > 24 ? `${filename.slice(0, 21)}...` : filename;
              const isSelected =
                activeCitation?.chunk_id === citation.chunk_id ||
                (activeCitation?.document_id === citation.document_id &&
                  activeCitation?.page_number === citation.page_number);

              return (
                <button
                  key={`${citation.chunk_id}-${citation.page_number}-${idx}`}
                  onClick={() => onCitationClick?.(citation)}
                  className={`citation-chip ${isSelected ? "active" : ""}`}
                  title={citation.excerpt || `${filename} (Page ${citation.page_number}) - Click to inspect in PDF`}
                >
                  <span>{`${cleanName} : p.${citation.page_number}`}</span>
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
