"use client";

import React, { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { 
  X, 
  Settings, 
  Cpu, 
  Sliders, 
  ShieldCheck, 
  Database, 
  Key, 
  Save, 
  CheckCircle2,
  RefreshCw
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export const SettingsModal: React.FC<{ isOpen: boolean; onClose: () => void }> = ({
  isOpen,
  onClose,
}) => {
  const { user } = useAuth();
  const { showToast } = useToast();

  const [activeTab, setActiveTab] = useState<"models" | "retrieval" | "tenant">("models");
  const [llmProvider, setLlmProvider] = useState("groq");
  const [llmModel, setLlmModel] = useState("gpt-oss-120b");
  const [topK, setTopK] = useState(5);
  const [hnswEf, setHnswEf] = useState(100);
  const [enableReranker, setEnableReranker] = useState(true);
  const [enableCache, setEnableCache] = useState(true);
  const [groqKey, setGroqKey] = useState("••••••••••••••••••••••••");
  const [geminiKey, setGeminiKey] = useState("••••••••••••••••••••••••");

  const handleSave = () => {
    localStorage.setItem(
      "rag_settings",
      JSON.stringify({
        llmProvider,
        llmModel,
        topK,
        hnswEf,
        enableReranker,
        enableCache,
      })
    );
    showToast("success", "Settings Saved", "Runtime retrieval and generation parameters updated.");
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(12px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: "20px",
          }}
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            style={{
              width: "100%",
              maxWidth: "680px",
              backgroundColor: "rgba(16, 18, 29, 0.95)",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: "18px",
              boxShadow: "0 24px 64px rgba(0, 0, 0, 0.8), 0 0 32px var(--accent-glow)",
              overflow: "hidden",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "20px 24px",
                borderBottom: "1px solid var(--border)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "10px",
                    backgroundColor: "rgba(99, 102, 241, 0.14)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Settings size={18} color="var(--accent-light)" />
                </div>
                <div>
                  <h3 style={{ fontSize: "17px", fontWeight: 700, color: "#FFFFFF" }}>
                    Platform & Model Configuration
                  </h3>
                  <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                    Tune pipeline inference, vector indexing, and multi-tenant parameters
                  </span>
                </div>
              </div>

              <button onClick={onClose} className="btn btn-ghost" style={{ padding: "6px" }}>
                <X size={18} />
              </button>
            </div>

            {/* Tabs */}
            <div
              style={{
                display: "flex",
                borderBottom: "1px solid var(--border)",
                padding: "0 24px",
                backgroundColor: "rgba(255, 255, 255, 0.02)",
              }}
            >
              {[
                { id: "models", label: "LLM & Vision Models", icon: Cpu },
                { id: "retrieval", label: "Retrieval & Ranking", icon: Sliders },
                { id: "tenant", label: "Tenant & Security", icon: ShieldCheck },
              ].map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      padding: "14px 16px",
                      background: "transparent",
                      border: "none",
                      borderBottom: isActive ? "2px solid var(--accent-light)" : "2px solid transparent",
                      color: isActive ? "#FFFFFF" : "var(--text-muted)",
                      fontWeight: isActive ? 600 : 500,
                      fontSize: "13px",
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <Icon size={15} color={isActive ? "var(--accent-light)" : "var(--text-muted)"} />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Tab Contents */}
            <div style={{ padding: "24px", maxHeight: "420px", overflowY: "auto" }}>
              {activeTab === "models" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                  <div>
                    <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: "8px", textTransform: "uppercase" }}>
                      Primary Inference Provider
                    </label>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                      {[
                        { id: "groq", name: "Groq LPU (GPT-OSS 120B)", speed: "<300ms TTFT", desc: "Ultra-fast low-latency streaming" },
                        { id: "gemini", name: "Google Gemini 2.0 Flash", speed: "Native Multimodal", desc: "Large context window reasoning" },
                      ].map((prov) => (
                        <div
                          key={prov.id}
                          onClick={() => {
                            setLlmProvider(prov.id);
                            setLlmModel(prov.id === "groq" ? "gpt-oss-120b" : "gemini-2.0-flash");
                          }}
                          style={{
                            padding: "14px",
                            borderRadius: "10px",
                            backgroundColor: llmProvider === prov.id ? "rgba(99, 102, 241, 0.16)" : "rgba(255, 255, 255, 0.03)",
                            border: llmProvider === prov.id ? "1.5px solid var(--accent-light)" : "1px solid var(--border)",
                            cursor: "pointer",
                            transition: "all 0.15s ease",
                          }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                            <span style={{ fontWeight: 700, color: "#FFFFFF", fontSize: "13px" }}>{prov.name}</span>
                            <span className="badge badge-accent" style={{ fontSize: "10px" }}>{prov.speed}</span>
                          </div>
                          <span style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>{prov.desc}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: "8px", textTransform: "uppercase" }}>
                      Active Model Target
                    </label>
                    <select
                      value={llmModel}
                      onChange={(e) => setLlmModel(e.target.value)}
                      className="input-field"
                    >
                      <option value="gpt-oss-120b">gpt-oss-120b (Production 120B Agentic)</option>
                      <option value="gpt-oss-20b">gpt-oss-20b (Ultra-Fast 20B Lightweight)</option>
                      <option value="gemini-2.0-flash">gemini-2.0-flash (Google Multimodal Flash)</option>
                    </select>
                  </div>
                </div>
              )}

              {activeTab === "retrieval" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                      <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>
                        Top-K Context Chunks
                      </label>
                      <span style={{ fontWeight: 700, color: "var(--accent-light)", fontSize: "13px" }}>{topK} chunks</span>
                    </div>
                    <input
                      type="range"
                      min={3}
                      max={20}
                      value={topK}
                      onChange={(e) => setTopK(parseInt(e.target.value))}
                      style={{ width: "100%", accentColor: "var(--accent)" }}
                    />
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                      <span>3 (Precise)</span>
                      <span>10 (Balanced)</span>
                      <span>20 (Comprehensive)</span>
                    </div>
                  </div>

                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                      <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>
                        HNSW ef_search Parameter
                      </label>
                      <span style={{ fontWeight: 700, color: "var(--accent-light)", fontSize: "13px" }}>{hnswEf}</span>
                    </div>
                    <input
                      type="range"
                      min={40}
                      max={200}
                      step={20}
                      value={hnswEf}
                      onChange={(e) => setHnswEf(parseInt(e.target.value))}
                      style={{ width: "100%", accentColor: "var(--accent)" }}
                    />
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                      <span>40 (Speed)</span>
                      <span>100 (Default)</span>
                      <span>200 (Highest Recall)</span>
                    </div>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "12px", paddingTop: "8px", borderTop: "1px solid var(--border)" }}>
                    <label style={{ display: "flex", alignItems: "center", justifyContent: "space-between", cursor: "pointer" }}>
                      <div>
                        <div style={{ fontSize: "13.5px", fontWeight: 600, color: "#FFFFFF" }}>ONNX Cross-Encoder Reranker</div>
                        <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Reorders fused vector and BM25 results with deep cross-attention</div>
                      </div>
                      <input
                        type="checkbox"
                        checked={enableReranker}
                        onChange={(e) => setEnableReranker(e.target.checked)}
                        style={{ width: "18px", height: "18px", accentColor: "var(--accent)" }}
                      />
                    </label>

                    <label style={{ display: "flex", alignItems: "center", justifyContent: "space-between", cursor: "pointer" }}>
                      <div>
                        <div style={{ fontSize: "13.5px", fontWeight: 600, color: "#FFFFFF" }}>Redis Semantic Vector Cache</div>
                        <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Sub-15ms instant responses for semantically duplicate user questions</div>
                      </div>
                      <input
                        type="checkbox"
                        checked={enableCache}
                        onChange={(e) => setEnableCache(e.target.checked)}
                        style={{ width: "18px", height: "18px", accentColor: "var(--accent)" }}
                      />
                    </label>
                  </div>
                </div>
              )}

              {activeTab === "tenant" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div
                    style={{
                      padding: "16px",
                      borderRadius: "10px",
                      backgroundColor: "rgba(255, 255, 255, 0.03)",
                      border: "1px solid var(--border)",
                    }}
                  >
                    <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", marginBottom: "4px" }}>
                      Tenant Identifier
                    </div>
                    <code style={{ fontSize: "13px", color: "var(--accent-light)" }}>
                      {user?.tenant_id || "76d4016f-ca64-4898-8bcf-3a4a0da2d7ab"}
                    </code>
                  </div>

                  <div
                    style={{
                      padding: "16px",
                      borderRadius: "10px",
                      backgroundColor: "rgba(255, 255, 255, 0.03)",
                      border: "1px solid var(--border)",
                    }}
                  >
                    <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", marginBottom: "4px" }}>
                      Organization Name
                    </div>
                    <div style={{ fontSize: "14px", fontWeight: 600, color: "#FFFFFF" }}>
                      {user?.tenant?.name || "Acme Corporation"}
                    </div>
                  </div>

                  <div
                    style={{
                      padding: "16px",
                      borderRadius: "10px",
                      backgroundColor: "rgba(16, 185, 129, 0.08)",
                      border: "1px solid rgba(16, 185, 129, 0.25)",
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                    }}
                  >
                    <CheckCircle2 size={18} color="#10B981" />
                    <div>
                      <div style={{ fontSize: "13px", fontWeight: 700, color: "#34D399" }}>
                        PostgreSQL Row-Level Security Enforced
                      </div>
                      <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                        All chunks, vectors, and entity triples are isolated to your tenant UUID.
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "flex-end",
                gap: "10px",
                padding: "16px 24px",
                borderTop: "1px solid var(--border)",
                backgroundColor: "rgba(11, 13, 20, 0.6)",
              }}
            >
              <button onClick={onClose} className="btn btn-secondary">
                Cancel
              </button>
              <button onClick={handleSave} className="btn btn-primary">
                <Save size={15} />
                <span>Save Configuration</span>
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
