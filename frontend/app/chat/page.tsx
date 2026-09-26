"use client";

import React, { useState, useRef, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { 
  streamQuery, 
  CitationBlock, 
  QueryMetadata, 
  getDocumentFileUrl,
  uploadDocument
} from "@/lib/api";
import { ChatMessage } from "@/components/ChatMessage";
import { PDFViewer } from "@/components/PDFViewer";
import { 
  Send, 
  Sparkles, 
  FileText, 
  X, 
  Maximize2, 
  Minimize2, 
  Trash2, 
  Bot, 
  AlertCircle, 
  Download, 
  Zap, 
  Layers, 
  Database, 
  Search, 
  Plus,
  Paperclip,
  Sliders,
  Cpu,
  History,
  ChevronDown
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface MessageState {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: CitationBlock[];
  metadata?: QueryMetadata;
}

interface ChatSession {
  id: string;
  title: string;
  messages: MessageState[];
  updatedAt: number;
}

export default function ChatPage() {
  const { token, user } = useAuth();
  const { showToast } = useToast();

  // Multi-session State
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string>("default-session");
  const [showHistoryDrawer, setShowHistoryDrawer] = useState(false);

  // Active Chat State
  const [messages, setMessages] = useState<MessageState[]>([]);
  const [inputQuery, setInputQuery] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingPhase, setStreamingPhase] = useState<string>("Analyzing Query & Intent...");
  const [activeCitations, setActiveCitations] = useState<CitationBlock[]>([]);
  const [selectedCitation, setSelectedCitation] = useState<CitationBlock | null>(null);

  // Inference Controls
  const [activeModel, setActiveModel] = useState<string>("gpt-oss-120b");
  const [retrievalMode, setRetrievalMode] = useState<string>("tri-hybrid");
  const [showControlsPopover, setShowControlsPopover] = useState(false);

  // PDF Viewer Side Panel State
  const [pdfDocId, setPdfDocId] = useState<string | null>(null);
  const [pdfFilename, setPdfFilename] = useState<string>("document.pdf");
  const [isPdfExpanded, setIsPdfExpanded] = useState(false);
  const [showPdfPanel, setShowPdfPanel] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Restore sessions from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem("rag_chat_sessions");
      if (stored) {
        const parsed: ChatSession[] = JSON.parse(stored);
        if (parsed.length > 0) {
          setSessions(parsed);
          setCurrentSessionId(parsed[0].id);
          setMessages(parsed[0].messages || []);
          return;
        }
      }
    } catch (e) {
      console.warn("Could not parse saved chat sessions:", e);
    }

    // Default initial session
    const initialSession: ChatSession = {
      id: `session-${Date.now()}`,
      title: "New Investigation",
      messages: [],
      updatedAt: Date.now(),
    };
    setSessions([initialSession]);
    setCurrentSessionId(initialSession.id);
  }, []);

  // Save current messages to active session in localStorage
  useEffect(() => {
    if (!currentSessionId || sessions.length === 0) return;

    setSessions((prev) => {
      const updated = prev.map((s) => {
        if (s.id === currentSessionId) {
          const firstUserMsg = messages.find((m) => m.role === "user");
          const title = firstUserMsg
            ? firstUserMsg.content.length > 32
              ? `${firstUserMsg.content.slice(0, 30)}...`
              : firstUserMsg.content
            : s.title;

          return { ...s, messages, title, updatedAt: Date.now() };
        }
        return s;
      });

      try {
        localStorage.setItem("rag_chat_sessions", JSON.stringify(updated));
      } catch (e) {
        console.warn("Storage save error:", e);
      }
      return updated;
    });
  }, [messages, currentSessionId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  // Adjust textarea height dynamically
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [inputQuery]);

  const handleCitationClick = (citation: CitationBlock) => {
    setSelectedCitation(citation);
    if (citation.document_id) {
      setPdfDocId(citation.document_id);
    }
    if (citation.source_filename) {
      setPdfFilename(citation.source_filename);
    }
    setShowPdfPanel(true);
    showToast("info", `Inspecting Page ${citation.page_number}`, citation.source_filename || "Document source");
  };

  const handleCreateNewSession = () => {
    const newSession: ChatSession = {
      id: `session-${Date.now()}`,
      title: "New Investigation",
      messages: [],
      updatedAt: Date.now(),
    };
    setSessions((prev) => [newSession, ...prev]);
    setCurrentSessionId(newSession.id);
    setMessages([]);
    setActiveCitations([]);
    setSelectedCitation(null);
    setShowPdfPanel(false);
    showToast("info", "New Conversation Started");
  };

  const handleSwitchSession = (session: ChatSession) => {
    setCurrentSessionId(session.id);
    setMessages(session.messages || []);
    setActiveCitations([]);
    setSelectedCitation(null);
    setShowPdfPanel(false);
    setShowHistoryDrawer(false);
  };

  const handleDeleteSession = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const filtered = sessions.filter((s) => s.id !== sessionId);
    setSessions(filtered);
    try {
      localStorage.setItem("rag_chat_sessions", JSON.stringify(filtered));
    } catch (e) {}

    if (currentSessionId === sessionId) {
      if (filtered.length > 0) {
        handleSwitchSession(filtered[0]);
      } else {
        handleCreateNewSession();
      }
    }
    showToast("info", "Session deleted");
  };

  const handleFileUpload = async (file: File) => {
    if (!token) return;
    try {
      showToast("info", "Uploading document...", file.name);
      await uploadDocument(file, token, user?.tenant_id);
      showToast("success", "Document ingested", `"${file.name}" has been queued for layout parsing.`);
    } catch (err: any) {
      showToast("error", "Upload failed", err.message || "Failed to upload document.");
    }
  };

  const handleSend = async (e?: React.FormEvent, customPrompt?: string) => {
    if (e) e.preventDefault();
    const queryText = (customPrompt || inputQuery).trim();
    if (!queryText || isStreaming || !token) return;

    setError(null);
    setInputQuery("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";

    const userMsgId = `user-${Date.now()}`;
    const assistantMsgId = `assistant-${Date.now()}`;

    const userMessage: MessageState = {
      id: userMsgId,
      role: "user",
      content: queryText,
      citations: [],
    };

    const assistantPlaceholder: MessageState = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      citations: [],
    };

    setMessages((prev) => [...prev, userMessage, assistantPlaceholder]);
    setIsStreaming(true);
    setStreamingPhase("Routing intent & semantic cache lookup...");

    let accumulatedContent = "";
    const currentCitations: CitationBlock[] = [];

    try {
      for await (const event of streamQuery(queryText, token)) {
        if (event.type === "token") {
          accumulatedContent += event.content;
          setStreamingPhase("Synthesizing grounded response...");
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId
                ? { ...msg, content: accumulatedContent }
                : msg
            )
          );
        } else if (event.type === "citation") {
          currentCitations.push(event.citation);
          setActiveCitations((prev) => [...prev, event.citation]);
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId
                ? { ...msg, citations: [...currentCitations] }
                : msg
            )
          );

          if (currentCitations.length === 1 && event.citation.document_id) {
            setPdfDocId(event.citation.document_id);
            setPdfFilename(event.citation.source_filename || "document.pdf");
            setSelectedCitation(event.citation);
            setShowPdfPanel(true);
          }
        } else if (event.type === "done") {
          const finalAnswer = event.answer || accumulatedContent;
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId
                ? {
                    ...msg,
                    content: finalAnswer,
                    citations: currentCitations,
                    metadata: event.metadata,
                  }
                : msg
            )
          );
          setIsStreaming(false);
        } else if (event.type === "error") {
          setError(event.message);
          showToast("error", "Query execution failed", event.message);
          setIsStreaming(false);
        }
      }
    } catch (err: any) {
      console.error("Stream query error:", err);
      setError(err.message || "Failed to stream query response.");
      showToast("error", "Backend connection error", err.message || "Failed to stream answer.");
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId && !msg.content
            ? {
                ...msg,
                content:
                  "⚠️ An error occurred while retrieving or generating an answer. Please verify backend connectivity.",
              }
            : msg
        )
      );
    } finally {
      setIsStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearChat = () => {
    setMessages([]);
    setActiveCitations([]);
    setSelectedCitation(null);
    setShowPdfPanel(false);
    showToast("info", "Conversation cleared");
  };

  const exportChat = () => {
    if (messages.length === 0) return;
    const markdownContent = messages
      .map((m) => `### ${m.role === "user" ? "User" : "Nexus Assistant"}\n\n${m.content}\n\n`)
      .join("---\n\n");
    const blob = new Blob([markdownContent], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `nexus-chat-${new Date().toISOString().slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
    showToast("success", "Conversation exported", "Markdown file downloaded.");
  };

  const promptSuggestions = [
    {
      category: "Executive Summary",
      icon: Sparkles,
      color: "var(--accent-light)",
      title: "Synthesize Key Highlights",
      query: "Provide an executive summary of the uploaded document with key takeaways and findings.",
    },
    {
      category: "Architecture & Layout",
      icon: Layers,
      color: "var(--cyan-light)",
      title: "Architecture & Pipeline Flow",
      query: "Explain the system architecture, ingestion pipeline, and chunking strategy used here.",
    },
    {
      category: "Quantitative Data",
      icon: Database,
      color: "var(--emerald-light)",
      title: "Financial & Numeric Breakdown",
      query: "Extract all specific metrics, performance numbers, and financial tables with page references.",
    },
    {
      category: "Compliance & Risk",
      icon: Search,
      color: "#F59E0B",
      title: "Security & Isolation Policies",
      query: "What security measures, tenant isolation mechanisms, or compliance constraints are specified?",
    },
  ];

  return (
    <div
      style={{
        display: "flex",
        height: "100%",
        width: "100%",
        backgroundColor: "var(--bg)",
        overflow: "hidden",
      }}
    >
      {/* ── Left Chat Workspace ──────────────────────────────────── */}
      <div
        style={{
          flex: showPdfPanel && !isPdfExpanded ? "1 1 54%" : "1 1 100%",
          display: showPdfPanel && isPdfExpanded ? "none" : "flex",
          flexDirection: "column",
          height: "100%",
          minWidth: "380px",
          borderRight: showPdfPanel ? "1px solid var(--border)" : "none",
          transition: "flex 0.28s cubic-bezier(0.16, 1, 0.3, 1)",
        }}
      >
        {/* Top Header Bar */}
        <div
          style={{
            padding: "12px 24px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            backgroundColor: "rgba(16, 18, 29, 0.85)",
            backdropFilter: "blur(14px)",
            zIndex: 10,
            gap: "12px",
            flexWrap: "wrap",
          }}
        >
          {/* Left Session Info & History Toggle */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <button
              onClick={() => setShowHistoryDrawer(!showHistoryDrawer)}
              className="btn btn-secondary"
              style={{ padding: "6px 10px", fontSize: "12px", gap: "6px" }}
              title="Toggle Conversation History"
            >
              <History size={14} />
              <span>History ({sessions.length})</span>
            </button>

            <button
              onClick={handleCreateNewSession}
              className="btn btn-primary"
              style={{ padding: "6px 12px", fontSize: "12px" }}
              title="Start a new chat conversation"
            >
              <Plus size={14} />
              <span>New Chat</span>
            </button>
          </div>

          {/* Model & Strategy Controls Pills */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "5px 10px",
                borderRadius: "8px",
                backgroundColor: "rgba(255, 255, 255, 0.04)",
                border: "1px solid var(--border)",
                fontSize: "12px",
                color: "var(--text)",
              }}
            >
              <Cpu size={13} color="var(--accent-light)" />
              <select
                value={activeModel}
                onChange={(e) => setActiveModel(e.target.value)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#FFFFFF",
                  fontSize: "12px",
                  fontWeight: 600,
                  outline: "none",
                  cursor: "pointer",
                }}
              >
                <option value="gpt-oss-120b" style={{ background: "#10121D" }}>Groq GPT-OSS 120B</option>
                <option value="gemini-2.0-flash" style={{ background: "#10121D" }}>Gemini 2.0 Flash</option>
              </select>
            </div>

            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "5px 10px",
                borderRadius: "8px",
                backgroundColor: "rgba(255, 255, 255, 0.04)",
                border: "1px solid var(--border)",
                fontSize: "12px",
                color: "var(--text)",
              }}
            >
              <Zap size={13} color="var(--cyan-light)" />
              <select
                value={retrievalMode}
                onChange={(e) => setRetrievalMode(e.target.value)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#FFFFFF",
                  fontSize: "12px",
                  fontWeight: 600,
                  outline: "none",
                  cursor: "pointer",
                }}
              >
                <option value="tri-hybrid" style={{ background: "#10121D" }}>Tri-Hybrid Fusion</option>
                <option value="vector-only" style={{ background: "#10121D" }}>Dense Vector HNSW</option>
                <option value="bm25-only" style={{ background: "#10121D" }}>BM25 Lexical</option>
                <option value="graph-only" style={{ background: "#10121D" }}>GraphRAG Recursive</option>
              </select>
            </div>

            {messages.length > 0 && (
              <>
                <button
                  onClick={exportChat}
                  className="btn btn-ghost"
                  style={{ padding: "6px 8px", fontSize: "12px" }}
                  title="Export conversation as Markdown"
                >
                  <Download size={14} />
                </button>

                <button
                  onClick={clearChat}
                  className="btn btn-ghost"
                  style={{ padding: "6px 8px", fontSize: "12px", color: "var(--rose-light)" }}
                  title="Clear conversation"
                >
                  <Trash2 size={14} />
                </button>
              </>
            )}

            {pdfDocId && !showPdfPanel && (
              <button
                onClick={() => setShowPdfPanel(true)}
                className="btn btn-secondary"
                style={{ padding: "6px 12px", fontSize: "12px" }}
              >
                <FileText size={13} />
                <span>Source Inspector</span>
              </button>
            )}
          </div>
        </div>

        {/* Conversation History Drawer */}
        <AnimatePresence>
          {showHistoryDrawer && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              style={{
                backgroundColor: "rgba(11, 13, 20, 0.95)",
                borderBottom: "1px solid var(--border)",
                padding: "16px 24px",
                display: "flex",
                flexDirection: "column",
                gap: "10px",
                overflow: "hidden",
                zIndex: 9,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
                  Saved Conversations
                </span>
                <button
                  onClick={() => setShowHistoryDrawer(false)}
                  className="btn btn-ghost"
                  style={{ padding: "2px 6px", fontSize: "11px" }}
                >
                  Close
                </button>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
                  gap: "8px",
                  maxHeight: "180px",
                  overflowY: "auto",
                }}
              >
                {sessions.map((sess) => {
                  const isCurrent = sess.id === currentSessionId;
                  return (
                    <div
                      key={sess.id}
                      onClick={() => handleSwitchSession(sess)}
                      style={{
                        padding: "10px 12px",
                        borderRadius: "8px",
                        backgroundColor: isCurrent ? "rgba(99, 102, 241, 0.18)" : "rgba(255, 255, 255, 0.03)",
                        border: isCurrent ? "1px solid var(--accent-light)" : "1px solid var(--border)",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: "8px",
                        transition: "all 0.15s ease",
                      }}
                    >
                      <span
                        style={{
                          fontSize: "13px",
                          fontWeight: isCurrent ? 700 : 500,
                          color: isCurrent ? "#FFFFFF" : "var(--text)",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {sess.title || "Untitled Conversation"}
                      </span>

                      {sessions.length > 1 && (
                        <button
                          onClick={(e) => handleDeleteSession(sess.id, e)}
                          title="Delete session"
                          style={{
                            background: "transparent",
                            border: "none",
                            color: "var(--text-muted)",
                            cursor: "pointer",
                            padding: "2px",
                          }}
                        >
                          <Trash2 size={12} />
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error Alert */}
        {error && (
          <div
            style={{
              margin: "12px 24px 0",
              padding: "10px 14px",
              backgroundColor: "rgba(244, 63, 94, 0.12)",
              border: "1px solid rgba(244, 63, 94, 0.35)",
              borderRadius: "8px",
              color: "#FB7185",
              fontSize: "13px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* Message Stream Scroll View */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "24px 28px",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {messages.length === 0 ? (
            <div
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                maxWidth: "700px",
                margin: "0 auto",
                textAlign: "center",
                padding: "20px 0",
              }}
            >
              {/* Glowing Center Logo */}
              <div
                style={{
                  width: "68px",
                  height: "68px",
                  borderRadius: "20px",
                  background: "rgba(99, 102, 241, 0.14)",
                  border: "1px solid rgba(99, 102, 241, 0.35)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "20px",
                  boxShadow: "0 0 32px var(--accent-glow)",
                }}
              >
                <Sparkles size={32} color="var(--accent-light)" />
              </div>

              <h2
                className="brand-font"
                style={{ fontSize: "26px", fontWeight: 800, marginBottom: "8px", color: "#FFFFFF" }}
              >
                What would you like to explore today?
              </h2>
              <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: "32px", maxWidth: "540px" }}>
                Ask questions across your multi-tenant document repository. Every answer is grounded with verifiable 
                page layout bounding boxes and transparent reasoning.
              </p>

              {/* Categorized Prompt Suggestions */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "12px",
                  width: "100%",
                }}
              >
                {promptSuggestions.map((item, i) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={i}
                      onClick={() => handleSend(undefined, item.query)}
                      className="card card-interactive"
                      style={{
                        padding: "16px",
                        textAlign: "left",
                        display: "flex",
                        flexDirection: "column",
                        gap: "6px",
                        background: "rgba(16, 18, 29, 0.6)",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <Icon size={16} color={item.color} />
                        <span style={{ fontSize: "11px", fontWeight: 700, color: item.color, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                          {item.category}
                        </span>
                      </div>
                      <div style={{ fontSize: "13.5px", fontWeight: 700, color: "#FFFFFF" }}>
                        {item.title}
                      </div>
                      <div style={{ fontSize: "12px", color: "var(--text-muted)", lineHeight: 1.4 }}>
                        {item.query}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, index) => (
                <ChatMessage
                  key={msg.id || index}
                  role={msg.role}
                  content={msg.content}
                  citations={msg.citations}
                  isStreaming={isStreaming && index === messages.length - 1 && msg.role === "assistant"}
                  metadata={msg.metadata}
                  onCitationClick={handleCitationClick}
                  activeCitation={selectedCitation}
                />
              ))}

              {/* Live Streaming Stage Pill */}
              {isStreaming && (
                <div
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "8px",
                    padding: "6px 14px",
                    backgroundColor: "rgba(99, 102, 241, 0.12)",
                    border: "1px solid rgba(99, 102, 241, 0.3)",
                    borderRadius: "20px",
                    fontSize: "12px",
                    color: "var(--accent-light)",
                    fontWeight: 600,
                    margin: "0 0 16px 52px",
                    width: "fit-content",
                  }}
                >
                  <Zap size={14} style={{ animation: "pulse 1.2s infinite" }} />
                  <span>{streamingPhase}</span>
                </div>
              )}

              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* ── Input Bar ──────────────────────────────────────────── */}
        <div
          style={{
            padding: "16px 24px 20px",
            borderTop: "1px solid var(--border)",
            backgroundColor: "rgba(16, 18, 29, 0.85)",
            backdropFilter: "blur(14px)",
          }}
        >
          <form
            onSubmit={handleSend}
            style={{
              display: "flex",
              alignItems: "flex-end",
              gap: "10px",
              backgroundColor: "rgba(11, 13, 20, 0.95)",
              border: "1px solid var(--border)",
              borderRadius: "14px",
              padding: "8px 12px",
              boxShadow: "0 4px 24px rgba(0, 0, 0, 0.45)",
            }}
          >
            {/* Attachment Button */}
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: "none" }}
              accept=".pdf,.docx,.txt"
              onChange={(e) => {
                if (e.target.files && e.target.files.length > 0) {
                  handleFileUpload(e.target.files[0]);
                }
              }}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="btn btn-ghost"
              style={{ padding: "8px", borderRadius: "8px", color: "var(--text-muted)" }}
              title="Attach and ingest document"
            >
              <Paperclip size={18} />
            </button>

            <textarea
              ref={textareaRef}
              rows={1}
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about your documents (Press Enter to send, Shift+Enter for new line)..."
              disabled={isStreaming}
              style={{
                flex: 1,
                background: "transparent",
                border: "none",
                color: "#FFFFFF",
                fontSize: "14px",
                outline: "none",
                resize: "none",
                padding: "8px 4px",
                fontFamily: "inherit",
                lineHeight: "1.45",
                maxHeight: "140px",
              }}
            />

            <button
              type="submit"
              disabled={!inputQuery.trim() || isStreaming}
              className="btn btn-primary"
              style={{
                padding: "10px 16px",
                borderRadius: "10px",
                flexShrink: 0,
              }}
            >
              <Send size={15} />
              <span>Ask</span>
            </button>
          </form>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontSize: "11px",
              color: "var(--text-muted)",
              marginTop: "8px",
              padding: "0 6px",
            }}
          >
            <span>Hybrid Retrieval: pgvector HNSW + BM25 + Recursive Graph CTE</span>
            <span>Cryptographic RLS Isolation</span>
          </div>
        </div>
      </div>

      {/* ── Right PDF Viewer Inspector Panel ─────────────────────── */}
      {showPdfPanel && pdfDocId && (
        <div
          style={{
            flex: isPdfExpanded ? "1 1 100%" : "1 1 46%",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            backgroundColor: "#0B0D14",
            position: "relative",
            transition: "flex 0.28s cubic-bezier(0.16, 1, 0.3, 1)",
          }}
        >
          {/* Panel Header */}
          <div
            style={{
              padding: "10px 16px",
              borderBottom: "1px solid var(--border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              backgroundColor: "var(--surface)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <FileText size={16} color="var(--accent-light)" />
              <span style={{ fontSize: "13px", fontWeight: 700, color: "#FFFFFF" }}>
                Verifiable Source Inspector
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <button
                onClick={() => setIsPdfExpanded(!isPdfExpanded)}
                className="btn btn-ghost"
                style={{ padding: "6px 8px", height: "28px" }}
                title={isPdfExpanded ? "Split Screen View" : "Expand to Fullscreen"}
              >
                {isPdfExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
              </button>
              <button
                onClick={() => setShowPdfPanel(false)}
                className="btn btn-ghost"
                style={{ padding: "6px 8px", height: "28px" }}
                title="Close Inspector"
              >
                <X size={15} />
              </button>
            </div>
          </div>

          {/* PDF Viewer Canvas */}
          <div style={{ flex: 1, height: "calc(100% - 49px)" }}>
            <PDFViewer
              fileUrl={getDocumentFileUrl(pdfDocId)}
              filename={pdfFilename}
              initialPage={selectedCitation?.page_number || 1}
              highlights={activeCitations.filter((c) => c.document_id === pdfDocId)}
              activeCitation={selectedCitation}
            />
          </div>
        </div>
      )}
    </div>
  );
}
