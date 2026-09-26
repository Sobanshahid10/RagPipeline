"use client";

import React, { useState } from "react";
import { QueryMetadata } from "@/lib/api";
import { 
  ChevronDown, 
  ChevronUp, 
  Zap, 
  Database, 
  Layers, 
  Cpu, 
  Clock, 
  CheckCircle2, 
  Sparkles,
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
          background: isOpen ? "rgba(99, 102, 241, 0.16)" : "rgba(255, 255, 255, 0.04)",
          border: isOpen ? "1px solid rgba(99, 102, 241, 0.4)" : "1px solid rgba(255, 255, 255, 0.08)",
          borderRadius: "8px",
          padding: "5px 12px",
          color: isOpen ? "#FFFFFF" : "var(--text-secondary)",
          fontSize: "11.5px",
          fontWeight: 600,
          cursor: "pointer",
          transition: "all 0.18s ease",
        }}
      >
        <Sparkles size={13} color="var(--accent-light)" />
        <span>RAG Pipeline Reasoning & Retrieval Telemetry</span>
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
                padding: "16px",
                borderRadius: "10px",
                backgroundColor: "rgba(11, 13, 20, 0.9)",
                border: "1px solid rgba(99, 102, 241, 0.25)",
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
                    borderRadius: "8px",
                    backgroundColor: "rgba(255, 255, 255, 0.03)",
                    border: "1px solid rgba(255, 255, 255, 0.06)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--cyan-light)", fontWeight: 700, marginBottom: "4px" }}>
                    <Zap size={13} />
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
                    borderRadius: "8px",
                    backgroundColor: "rgba(255, 255, 255, 0.03)",
                    border: "1px solid rgba(255, 255, 255, 0.06)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--accent-light)", fontWeight: 700, marginBottom: "4px" }}>
                    <GitBranch size={13} />
                    <span>2. Agent Route</span>
                  </div>
                  <div style={{ color: "var(--text-secondary)", fontSize: "11px" }}>
                    Dynamic Router
                  </div>
                  <div style={{ color: "#FFFFFF", fontWeight: 600, marginTop: "4px", fontSize: "11px" }}>
                    {route}
                  </div>
                </div>

                {/* 3. Tri-Hybrid Retrieval */}
                <div
                  style={{
                    padding: "10px",
                    borderRadius: "8px",
                    backgroundColor: "rgba(255, 255, 255, 0.03)",
                    border: "1px solid rgba(255, 255, 255, 0.06)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "#F59E0B", fontWeight: 700, marginBottom: "4px" }}>
                    <Database size={13} />
                    <span>3. Retrieval</span>
                  </div>
                  <div style={{ color: "var(--text-secondary)", fontSize: "11px" }}>
                    pgvector + BM25 + CTE
                  </div>
                  <div style={{ color: "var(--emerald-light)", fontWeight: 600, marginTop: "4px", fontSize: "11px" }}>
                    Parallel Gathered
                  </div>
                </div>

                {/* 4. RRF & Reranking */}
                <div
                  style={{
                    padding: "10px",
                    borderRadius: "8px",
                    backgroundColor: "rgba(255, 255, 255, 0.03)",
                    border: "1px solid rgba(255, 255, 255, 0.06)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--accent-lighter)", fontWeight: 700, marginBottom: "4px" }}>
                    <Layers size={13} />
                    <span>4. Fusion & Rank</span>
                  </div>
                  <div style={{ color: "var(--text-secondary)", fontSize: "11px" }}>
                    RRF k=60 + Cross-Encoder
                  </div>
                  <div style={{ color: "var(--emerald-light)", fontWeight: 600, marginTop: "4px", fontSize: "11px" }}>
                    ONNX Optimized
                  </div>
                </div>

                {/* 5. Generation */}
                <div
                  style={{
                    padding: "10px",
                    borderRadius: "8px",
                    backgroundColor: "rgba(255, 255, 255, 0.03)",
                    border: "1px solid rgba(255, 255, 255, 0.06)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "#10B981", fontWeight: 700, marginBottom: "4px" }}>
                    <Cpu size={13} />
                    <span>5. Synthesis</span>
                  </div>
                  <div style={{ color: "var(--text-secondary)", fontSize: "11px" }}>
                    Streaming SSE
                  </div>
                  <div style={{ color: "#FFFFFF", fontWeight: 600, marginTop: "4px", fontSize: "11px" }}>
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
                  borderTop: "1px solid rgba(255, 255, 255, 0.05)",
                  color: "var(--text-muted)",
                  fontSize: "11px",
                  flexWrap: "wrap",
                  gap: "10px",
                }}
              >
                <span>Total Latency: <strong style={{ color: "#FFFFFF" }}>{latency}ms</strong></span>
                <span>Prompt Tokens: <strong style={{ color: "#FFFFFF" }}>{promptTokens}</strong></span>
                <span>Completion Tokens: <strong style={{ color: "#FFFFFF" }}>{completionTokens}</strong></span>
                <span>Total Tokens: <strong style={{ color: "#FFFFFF" }}>{promptTokens + completionTokens}</strong></span>
                {metadata.interaction_id && (
                  <span>ID: <code style={{ color: "var(--accent-light)" }}>{metadata.interaction_id.slice(0, 8)}</code></span>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
