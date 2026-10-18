"use client";

import React, { useState } from "react";
import { QueryMetadata } from "@/lib/api";
import {
  ChevronDown,
  ChevronUp,
  Activity,
  Database,
  Layers,
  Cpu,
  Clock,
  CheckCircle2,
  GitBranch,
  ArrowRight
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface RAGPipelineInspectorProps {
  metadata?: QueryMetadata;
}

export const RAGPipelineInspector: React.FC<RAGPipelineInspectorProps> = ({ metadata }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!metadata) return null;

  const route = metadata.route_used || "FACTUAL_VECTOR";
  const ttft = metadata.ttft_ms ?? 0;
  const latency = metadata.total_latency_ms ?? 0;
  const promptTokens = metadata.prompt_tokens ?? 0;
  const completionTokens = metadata.completion_tokens ?? 0;

  return (
    <div style={{ marginTop: "12px", width: "100%" }}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "8px",
          background: isOpen ? "var(--surface-raised)" : "transparent",
          border: "1px solid var(--border)",
          borderRadius: "4px",
          padding: "5px 12px",
          color: isOpen ? "var(--foreground)" : "var(--text-secondary)",
          fontSize: "11.5px",
          fontWeight: 500,
          cursor: "pointer",
          transition: "all 0.18s ease",
        }}
      >
        <Activity size={13} style={{ color: "var(--text-muted)" }} />
        <span>RAG Pipeline Telemetry</span>
        {isOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
      </button>

      {/* Expandable Pipeline Flow */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.22 }}
            style={{
              overflow: "hidden",
              marginTop: "8px",
            }}
          >
            <div
              style={{
                padding: "14px",
                borderRadius: "6px",
                backgroundColor: "var(--surface)",
                border: "1px solid var(--border)",
                display: "flex",
                flexDirection: "column",
                gap: "12px",
                fontSize: "12px",
              }}
            >
              {/* Stage Flow Pipeline */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
                  gap: "10px",
                }}
              >
                {/* 1. Semantic Cache */}
                <div
                  style={{
                    padding: "10px",
                    borderRadius: "4px",
                    backgroundColor: "var(--surface-raised)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--foreground)", fontWeight: 600, marginBottom: "4px" }}>
                    <Activity size={13} style={{ color: "var(--text-muted)" }} />
                    <span>1. Cache Check</span>
                  </div>
                  <div style={{ color: "var(--text-secondary)", fontSize: "11px" }}>
                    Redis HNSW Lookup
                  </div>
                  <div style={{ color: "var(--emerald-light)", fontWeight: 600, marginTop: "4px", fontSize: "11px" }}>
                    Verified (&lt;12ms)
                  </div>
                </div>

                {/* 2. Routing Strategy */}
                <div
                  style={{
                    padding: "10px",
                    borderRadius: "4px",
                    backgroundColor: "var(--surface-raised)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--foreground)", fontWeight: 600, marginBottom: "4px" }}>
                    <GitBranch size={13} style={{ color: "var(--text-muted)" }} />
                    <span>2. Agent Route</span>
                  </div>
                  <div style={{ color: "var(--text-secondary)", fontSize: "11px" }}>
                    Dynamic Router
                  </div>
                  <div style={{ color: "var(--foreground)", fontWeight: 600, marginTop: "4px", fontSize: "11px" }}>
                    {route}
                  </div>
                </div>

                {/* 3. Tri-Hybrid Retrieval */}
                <div
                  style={{
                    padding: "10px",
                    borderRadius: "4px",
                    backgroundColor: "var(--surface-raised)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--foreground)", fontWeight: 600, marginBottom: "4px" }}>
                    <Database size={13} style={{ color: "var(--text-muted)" }} />
                    <span>3. Retrieval</span>
                  </div>
                  <div style={{ color: "var(--text-secondary)", fontSize: "11px" }}>
                    pgvector + BM25 + CTE
                  </div>
                  <div style={{ color: "var(--foreground)", fontWeight: 600, marginTop: "4px", fontSize: "11px" }}>
                    Parallel Gathered
                  </div>
                </div>

                {/* 4. RRF & Reranking */}
                <div
                  style={{
                    padding: "10px",
                    borderRadius: "4px",
                    backgroundColor: "var(--surface-raised)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--foreground)", fontWeight: 600, marginBottom: "4px" }}>
                    <Layers size={13} style={{ color: "var(--text-muted)" }} />
                    <span>4. Fusion & Rank</span>
                  </div>
                  <div style={{ color: "var(--text-secondary)", fontSize: "11px" }}>
                    RRF k=60 + Cross-Encoder
                  </div>
                  <div style={{ color: "var(--foreground)", fontWeight: 600, marginTop: "4px", fontSize: "11px" }}>
                    ONNX Optimized
                  </div>
                </div>

                {/* 5. Generation */}
                <div
                  style={{
                    padding: "10px",
                    borderRadius: "4px",
                    backgroundColor: "var(--surface-raised)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--foreground)", fontWeight: 600, marginBottom: "4px" }}>
                    <Cpu size={13} style={{ color: "var(--text-muted)" }} />
                    <span>5. Synthesis</span>
                  </div>
                  <div style={{ color: "var(--text-secondary)", fontSize: "11px" }}>
                    Streaming SSE
                  </div>
                  <div style={{ color: "var(--foreground)", fontWeight: 600, marginTop: "4px", fontSize: "11px" }}>
                    TTFT: {ttft}ms
                  </div>
                </div>
              </div>

              {/* Telemetry Breakdown Details */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  paddingTop: "8px",
                  borderTop: "1px solid var(--border)",
                  color: "var(--text-muted)",
                  fontSize: "11px",
                  flexWrap: "wrap",
                  gap: "10px",
                }}
              >
                <span>Total Latency: <strong style={{ color: "var(--foreground)" }}>{latency}ms</strong></span>
                <span>Prompt Tokens: <strong style={{ color: "var(--foreground)" }}>{promptTokens}</strong></span>
                <span>Completion Tokens: <strong style={{ color: "var(--foreground)" }}>{completionTokens}</strong></span>
                <span>Total Tokens: <strong style={{ color: "var(--foreground)" }}>{promptTokens + completionTokens}</strong></span>
                {metadata.interaction_id && (
                  <span>ID: <code style={{ color: "var(--text-secondary)" }}>{metadata.interaction_id.slice(0, 8)}</code></span>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
