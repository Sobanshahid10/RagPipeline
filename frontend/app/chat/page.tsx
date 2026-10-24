"use client";

import React, { useState, useRef, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { 
  streamQuery,
  chatHistoryKey,
  getDocuments,
  configuredModels,
  DocumentItem,
  askPublicBook,
  CitationBlock, 
  QueryMetadata, 
  getDocumentFileUrl,
  uploadDocument
} from "@/lib/api";
import { ChatMessage } from "@/components/ChatMessage";
import { DEFAULT_MODEL, isAvailableModel, MODEL_OPTIONS } from "@/lib/models";
import dynamic from "next/dynamic";
const PDFViewer = dynamic(() => import("@/components/PDFViewer").then(module => module.PDFViewer), { ssr: false });
import {
  Send,
  MessageSquare,
  FileText,
  BookOpen,
  X,
  Maximize2,
  Minimize2,
  Trash2,
  AlertCircle,
  Download,
  Activity,
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
  source?: "documents" | "public_book";
}

interface ChatSession {
  id: string;
  title: string;
  messages: MessageState[];
  updatedAt: number;
  source?: "documents" | "public_book";
  documentIds?: string[];
}

export default function ChatPage() {
  const { token, user } = useAuth();
  const { showToast } = useToast();
  const historyKey = chatHistoryKey(user);
  const [historyOwner, setHistoryOwner] = useState<string | null>(null);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [indexedDocs, setIndexedDocs] = useState<DocumentItem[]>([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const requestController = useRef<AbortController | null>(null);
  useEffect(() => {
    setAvailableModels([]);
    setIndexedDocs([]);
    if (!token) return;
    let active = true;
    configuredModels(token)
      .then(models => { if (active) setAvailableModels(models); })
      .catch(() => { if (active) setAvailableModels([]); });
    let refreshing = false;
    const refreshDocuments = async () => {
      if (refreshing || document.hidden) return;
      refreshing = true;
      try {
        const docs = await getDocuments(token);
        if (active) setIndexedDocs(docs.filter(d => d.status === "indexed"));
      } catch { /* Keep the last successful list during a transient outage. */ }
      finally { refreshing = false; }
    };
    void refreshDocuments();
    const interval = window.setInterval(refreshDocuments, 15000);
    window.addEventListener("focus", refreshDocuments);
    return () => {
      active = false;
      window.clearInterval(interval);
      window.removeEventListener("focus", refreshDocuments);
      requestController.current?.abort();
    };
  }, [token]);

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
  const [activeModel, setActiveModel] = useState<string>(DEFAULT_MODEL);

  useEffect(() => {
    const applySavedModel = () => {
      try {
        const saved = JSON.parse(localStorage.getItem("rag_settings") || "{}");
        if (typeof saved.llmModel === "string" && isAvailableModel(saved.llmModel)) {
          setActiveModel(saved.llmModel);
        }
      } catch {
        // Ignore invalid settings saved by an older frontend version.
      }
    };
    applySavedModel();
    window.addEventListener("rag-model-change", applySavedModel);
    return () => window.removeEventListener("rag-model-change", applySavedModel);
  }, []);

  const chooseAnswerModel = (modelId: string) => {
    setActiveModel(modelId);
    try {
      const saved = JSON.parse(localStorage.getItem("rag_settings") || "{}");
      localStorage.setItem("rag_settings", JSON.stringify({
        ...saved,
        llmModel: modelId,
        llmProvider: MODEL_OPTIONS.find((model) => model.id === modelId)?.provider,
      }));
    } catch {
      // The current request still uses the selected model if local storage is unavailable.
    }
  };

  useEffect(() => { if (availableModels.length && !availableModels.includes(activeModel)) setActiveModel(availableModels[0]); }, [availableModels, activeModel]);

  const [knowledgeSource, setKnowledgeSource] = useState<"documents" | "public_book">("documents");

  // PDF Viewer Side Panel State
  const [pdfDocId, setPdfDocId] = useState<string | null>(null);
  const [pdfFilename, setPdfFilename] = useState<string>("document.pdf");
  const [isPdfExpanded, setIsPdfExpanded] = useState(false);
  const [showPdfPanel, setShowPdfPanel] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Restore only after verified identity is known; never copy another account's state.
  useEffect(() => {
    requestController.current?.abort();
    setMessages([]); setSessions([]); setActiveCitations([]); setShowPdfPanel(false);
    setIsStreaming(false); setSelectedDocumentIds([]);
    setHistoryOwner(historyKey);
    if (!historyKey) return;
    try {
      const stored = localStorage.getItem(historyKey);
      if (stored) {
        const parsed: ChatSession[] = JSON.parse(stored);
        if (parsed.length > 0) {
          setSessions(parsed);
          setCurrentSessionId(parsed[0].id);
          setMessages(parsed[0].messages || []);
          setKnowledgeSource(parsed[0].source || "documents");
          setSelectedDocumentIds(parsed[0].documentIds || []);
          return;
        }
      }
    } catch (e) {
      console.warn("Could not parse saved chat sessions:", e);
    }

    // Default initial session
    const initialSession: ChatSession = {
      id: crypto.randomUUID(),
      title: "New Investigation",
      messages: [],
      updatedAt: Date.now(),
    };
    setSessions([initialSession]);
    setCurrentSessionId(initialSession.id);
  }, [historyKey]);

  // Save current messages to active session in localStorage
  useEffect(() => {
    if (!historyKey || historyOwner !== historyKey || !currentSessionId || sessions.length === 0) return;

    setSessions((prev) => {
      const updated = prev.map((s) => {
        if (s.id === currentSessionId) {
          const firstUserMsg = messages.find((m) => m.role === "user");
          const title = firstUserMsg
            ? firstUserMsg.content.length > 32
              ? `${firstUserMsg.content.slice(0, 30)}...`
              : firstUserMsg.content
            : s.title;

          return { ...s, messages, title, source: knowledgeSource, documentIds: selectedDocumentIds, updatedAt: Date.now() };
        }
        return s;
      });

      return updated;
    });
  }, [messages, currentSessionId, historyKey, historyOwner, knowledgeSource, selectedDocumentIds]);

  // Persist after React commits state; never notify other components from a state updater.
  useEffect(() => {
    if (!historyKey || historyOwner !== historyKey) return;
    try {
      localStorage.setItem(historyKey, JSON.stringify(sessions));
      window.dispatchEvent(new CustomEvent("rag-sessions-updated"));
    } catch { /* Browser storage can be disabled. */ }
  }, [sessions, historyKey, historyOwner]);

  // Global listeners for starting a new chat or continuing a past session (from Sidebar or navigation)
  useEffect(() => {
    const handleNew = () => handleCreateNewSession();
    const handleClearHistory = () => { requestController.current?.abort(); const empty: ChatSession = {id:crypto.randomUUID(),title:"New conversation",messages:[],updatedAt:Date.now()}; setSessions([empty]); setMessages([]); setCurrentSessionId(empty.id); };
    const handleSwitch = (e: any) => {
      const targetId = e.detail?.id;
      if (targetId) {
        const found = sessions.find((s) => s.id === targetId);
        if (found) {
          handleSwitchSession(found);
        }
      }
    };

    const handleDelete = (event: any) => { if (event.detail?.id) handleDeleteSession(event.detail.id); };
    window.addEventListener("rag-delete-session", handleDelete);
    window.addEventListener("rag-history-cleared", handleClearHistory);
    window.addEventListener("rag-new-chat", handleNew);
    window.addEventListener("rag-switch-session", handleSwitch);
    return () => {
      window.removeEventListener("rag-delete-session", handleDelete);
      window.removeEventListener("rag-history-cleared", handleClearHistory);
      window.removeEventListener("rag-new-chat", handleNew);
      window.removeEventListener("rag-switch-session", handleSwitch);
    };
  }, [sessions, currentSessionId]);

  // Check URL query parameters for session restoration or new chat trigger
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const sessionParam = params.get("session");
      const documentParam = params.get("document");
      if (documentParam) setSelectedDocumentIds([documentParam]);
      const newParam = params.get("new");
      if (newParam) {
        handleCreateNewSession();
      } else if (sessionParam && sessions.length > 0) {
        const found = sessions.find((s) => s.id === sessionParam);
        if (found && found.id !== currentSessionId) {
          handleSwitchSession(found);
        }
      }
    }
  }, [sessions.length]);

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
    if (citation.source_type === "public_book") setPdfDocId(null);
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
    requestController.current?.abort();
    setIsStreaming(false);
    const newSession: ChatSession = {
      id: crypto.randomUUID(),
      title: "New Investigation",
      messages: [],
      updatedAt: Date.now(),
    };
    setSessions((prev) => {
      const updated = [newSession, ...prev];
      return updated;
    });
    setCurrentSessionId(newSession.id);
    setMessages([]);
    setActiveCitations([]);
    setSelectedCitation(null);
    setShowPdfPanel(false);
    showToast("info", "New Conversation Started");
  };

  const handleSwitchSession = (session: ChatSession) => {
    setCurrentSessionId(session.id);
    requestController.current?.abort();
    setIsStreaming(false);
    setKnowledgeSource(session.source || "documents");
    setSelectedDocumentIds(session.documentIds || []);
    setMessages(session.messages || []);
    setActiveCitations([]);
    setSelectedCitation(null);
    setShowPdfPanel(false);
    setShowHistoryDrawer(false);
    showToast("info", "Continuing Conversation", session.title || "Untitled Chat");
  };

  const handleDeleteSession = (sessionId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    const filtered = sessions.filter((s) => s.id !== sessionId);
    setSessions(filtered);
    try {
      localStorage.setItem(historyKey!, JSON.stringify(filtered));
      window.dispatchEvent(new CustomEvent("rag-sessions-updated"));
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
      const result = await uploadDocument(file, token, user?.tenant_id);
      showToast(result.status === "failed" ? "error" : "info", result.status === "failed" ? "Retry required in Documents" : "Document status", result.message);
    } catch (err: any) {
      showToast("error", "Upload failed", err.message || "Failed to upload document.");
    }
  };

  const handleSend = async (e?: React.FormEvent, customPrompt?: string) => {
    if (e) e.preventDefault();
    const queryText = (customPrompt || inputQuery).trim();
    if (!queryText || isStreaming || !token) return;
    if (!availableModels.includes(activeModel)) { showToast("error", "Select a configured answer model"); return; }

    setError(null);
    setInputQuery("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";

    const userMsgId = `user-${Date.now()}`;
    const assistantMsgId = `assistant-${Date.now()}`;

    const userMessage: MessageState = {
      id: userMsgId,
      source: knowledgeSource,
      role: "user",
      content: queryText,
      citations: [],
    };

    const assistantPlaceholder: MessageState = {
      id: assistantMsgId,
      source: knowledgeSource,
      role: "assistant",
      content: "",
      citations: [],
    };

    setMessages((prev) => [...prev, userMessage, assistantPlaceholder]);
    setIsStreaming(true);

    const controller = new AbortController();
    requestController.current = controller;

    const queryPublicBook = async () => {
      setStreamingPhase("Searching Public Knowledge Book index...");
      try {
        const res = await askPublicBook(token, queryText, activeModel, controller.signal);
        if (controller.signal.aborted || requestController.current !== controller) return;
        const publicCitations: CitationBlock[] = res.sources.filter(s => res.citations.includes(s.source_id)).map((s, idx) => ({
          chunk_id: s.chunk_id || `public-source-${idx + 1}`,
          source_type: "public_book",
          source_filename: s.section ? `${s.section} [${s.source_id}]` : "PUBLIC_KNOWLEDGE_BOOK.md",
          page_number: 1,
          excerpt: s.text,
        }));
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? {
                  ...msg,
                  content: res.answer,
                  citations: publicCitations,
                }
              : msg
          )
        );
        setActiveCitations(publicCitations);
      } catch (err: any) {
        if (controller.signal.aborted) return;
        const errMsg = err.message || "Failed to query public knowledge book.";
        setError(errMsg);
        showToast("error", "Public Book Query Error", errMsg);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? {
                  ...msg,
                  content: `⚠️ Failed to query public knowledge book: ${errMsg}`,
                }
              : msg
          )
        );
      } finally {
        if (requestController.current === controller) setIsStreaming(false);
      }
    };

    if (knowledgeSource === "public_book") {
      await queryPublicBook();
      return;
    }

    setStreamingPhase("Routing intent & semantic cache lookup...");

    let accumulatedContent = "";
    const currentCitations: CitationBlock[] = [];

    try {
      for await (const event of streamQuery(queryText, token, activeModel, currentSessionId, selectedDocumentIds.length ? selectedDocumentIds : undefined, controller.signal)) {
        if (controller.signal.aborted || requestController.current !== controller) return;
        if (event.type === "token") {
          accumulatedContent += event.content;
          setStreamingPhase("Receiving answer...");
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
      if (controller.signal.aborted) return;
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
      if (requestController.current === controller) setIsStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearChat = () => {
    requestController.current?.abort();
    setIsStreaming(false);
    // A cleared conversation must not reuse its previous server-side turns.
    const nextSessionId = crypto.randomUUID();
    setSessions(prev => prev.map(session => session.id === currentSessionId
      ? { ...session, id: nextSessionId, messages: [], title: "New conversation", updatedAt: Date.now() }
      : session));
    setCurrentSessionId(nextSessionId);
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

  const documentSuggestions = [
    {
      category: "Summary",
      icon: FileText,
      color: "var(--text-secondary)",
      title: "Synthesize Key Highlights",
      query: "Provide an executive summary of the uploaded document with key takeaways and findings.",
    },
    {
      category: "Architecture",
      icon: Layers,
      color: "var(--text-secondary)",
      title: "Architecture & Pipeline Flow",
      query: "Explain the system architecture, ingestion pipeline, and chunking strategy used here.",
    },
    {
      category: "Metrics",
      icon: Database,
      color: "var(--text-secondary)",
      title: "Financial & Numeric Breakdown",
      query: "Extract all specific metrics, performance numbers, and financial tables with page references.",
    },
    {
      category: "Compliance",
      icon: Search,
      color: "var(--text-secondary)",
      title: "Security & Isolation Policies",
      query: "What security measures, tenant isolation mechanisms, or compliance constraints are specified?",
    },
  ];

  const publicBookSuggestions = [
    {
      category: "Timeline",
      icon: BookOpen,
      color: "var(--text-secondary)",
      title: "Project Origins & Timelines",
      query: "When did Umar start doing projects? What can the dates actually prove?",
    },
    {
      category: "Portfolio",
      icon: Layers,
      color: "var(--text-secondary)",
      title: "Strongest Engineering Evidence",
      query: "What is the best part of Omer's portfolio, based on the evidence?",
    },
    {
      category: "Boundaries",
      icon: Database,
      color: "var(--text-secondary)",
      title: "Verification Limits & Boundaries",
      query: "What is the worst part of Omer's portfolio, based on the evidence?",
    },
    {
      category: "Architecture",
      icon: Search,
      color: "var(--text-secondary)",
      title: "Pipeline Architecture & Steps",
      query: "What are the core technical achievements and architecture of this RAG pipeline?",
    },
  ];

  const promptSuggestions = knowledgeSource === "public_book" ? publicBookSuggestions : documentSuggestions;

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
        {/* ── Sleek, Streamlined Header Rail ── */}
        <div
          style={{
            minHeight: "52px",
            height: "auto",
            flexWrap: "wrap",
            padding: "10px 20px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            backgroundColor: "rgba(16, 18, 22, 0.95)",
            backdropFilter: "blur(14px)",
            zIndex: 10,
            gap: "16px",
          }}
        >
          {/* Left: Chat Title & Scope Toggle */}
          <div style={{ display: "flex", alignItems: "center", gap: "12px", flexShrink: 0 }}>
            <h1 style={{ fontSize: "14px", fontWeight: 600, color: "#FFFFFF", margin: 0, whiteSpace: "nowrap", letterSpacing: "-0.01em" }}>
              Chat
            </h1>

            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                backgroundColor: "rgba(255, 255, 255, 0.03)",
                border: "1px solid var(--border)",
                borderRadius: "6px",
                padding: "2px",
                gap: "2px",
              }}
            >
              <button
                type="button"
                onClick={() => {
                  setKnowledgeSource("documents");
                  showToast("info", "Tenant Documents Active");
                }}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "5px",
                  padding: "3px 9px",
                  borderRadius: "4px",
                  fontSize: "12px",
                  fontWeight: knowledgeSource === "documents" ? 600 : 400,
                  backgroundColor: knowledgeSource === "documents" ? "var(--surface-raised)" : "transparent",
                  color: knowledgeSource === "documents" ? "#FFFFFF" : "var(--text-muted)",
                  border: knowledgeSource === "documents" ? "1px solid var(--border-subtle)" : "1px solid transparent",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                <FileText size={12} />
                <span>Documents</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setKnowledgeSource("public_book");
                  showToast("info", "Public Book Active");
                }}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "5px",
                  padding: "3px 9px",
                  borderRadius: "4px",
                  fontSize: "12px",
                  fontWeight: knowledgeSource === "public_book" ? 600 : 400,
                  backgroundColor: knowledgeSource === "public_book" ? "var(--surface-raised)" : "transparent",
                  color: knowledgeSource === "public_book" ? "#FFFFFF" : "var(--text-muted)",
                  border: knowledgeSource === "public_book" ? "1px solid var(--border-subtle)" : "1px solid transparent",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                <BookOpen size={12} />
                <span>Public Book</span>
              </button>
            </div>
          </div>

          {/* Right: Model Selector, Inspector, History & Actions */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 1, flexWrap:"wrap", minWidth:0 }}>
            {/* Answer Model */}
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "3px 8px",
                borderRadius: "6px",
                backgroundColor: "var(--surface-raised)",
                border: "1px solid var(--border)",
                fontSize: "12px",
                color: "var(--text)",
              }}
            >
              <Cpu size={13} color="var(--text-muted)" />
              <select
                disabled={isStreaming || availableModels.length === 0}
                aria-label="Inference model"
                value={activeModel}
                onChange={(e) => chooseAnswerModel(e.target.value)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#FFFFFF",
                  fontSize: "12px",
                  fontWeight: 500,
                  outline: "none",
                  cursor: "pointer",
                }}
              >
                {availableModels.length === 0 && <option value="">No configured models</option>}
                {MODEL_OPTIONS.filter(m => availableModels.includes(m.id)).map((model) => (
                  <option key={model.id} value={model.id} style={{ background: "#16181C" }}>
                    {model.label}
                  </option>
                ))}
              </select>
            </div>

            {(pdfDocId || selectedCitation) && !showPdfPanel && (
              <button
                onClick={() => setShowPdfPanel(true)}
                className="btn btn-secondary"
                style={{ padding: "4px 10px", fontSize: "12px", gap: "5px" }}
              >
                <FileText size={13} />
                <span>Source Inspector</span>
              </button>
            )}

            <button
              onClick={() => setShowHistoryDrawer(!showHistoryDrawer)}
              className={`btn ${showHistoryDrawer ? "btn-secondary" : "btn-ghost"}`}
              style={{ padding: "4px 8px", fontSize: "12px", gap: "5px" }}
              title="Toggle Conversation History"
              aria-label={`Toggle conversation history (${sessions.length} saved)`}
            >
              <History size={13} />
              <span>History ({sessions.length})</span>
            </button>

            <button
              onClick={handleCreateNewSession}
              className="btn btn-secondary"
              style={{ padding: "4px 10px", fontSize: "12px", gap: "5px" }}
              title="Start a new chat conversation"
              aria-label="Start a new chat conversation"
            >
              <Plus size={13} />
              <span>New Chat</span>
            </button>

            {messages.length > 0 && (
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "2px",
                  borderLeft: "1px solid var(--border)",
                  paddingLeft: "6px",
                  marginLeft: "2px",
                }}
              >
                <button
                  onClick={exportChat}
                  className="btn btn-ghost"
                  style={{ padding: "5px 7px" }}
                  title="Export conversation as Markdown"
                >
                  <Download size={13} />
                </button>

                <button
                  onClick={clearChat}
                  className="btn btn-ghost"
                  style={{ padding: "5px 7px", color: "var(--rose-light)" }}
                  title="Clear conversation"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            )}
          </div>
        </div>

        {knowledgeSource === "documents" && (
          <div
            style={{
              fontSize: "12px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "12px",
              padding: "7px 20px",
              borderBottom: "1px solid var(--border)",
              backgroundColor: "rgba(16, 18, 22, 0.5)",
              overflow: "hidden",
            }}
          >
            <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", minWidth: 0, flexShrink: 1 }}>
              <span style={{ color: "var(--text-muted)", fontWeight: 500, whiteSpace: "nowrap", flexShrink: 0 }}>
                Evidence scope:
              </span>
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "3px 8px",
                  borderRadius: "6px",
                  backgroundColor: "var(--surface-raised)",
                  border: "1px solid var(--border)",
                  fontSize: "12px",
                  maxWidth: "320px",
                  minWidth: 0,
                }}
              >
                <FileText size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                <select
                  aria-label="Document evidence scope"
                  value={selectedDocumentIds[0] || ""}
                  onChange={(e) => setSelectedDocumentIds(e.target.value ? [e.target.value] : [])}
                  disabled={isStreaming}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "#FFFFFF",
                    fontSize: "12px",
                    fontWeight: 500,
                    outline: "none",
                    cursor: "pointer",
                    maxWidth: "280px",
                    textOverflow: "ellipsis",
                  }}
                >
                  <option value="" style={{ background: "#16181C" }}>All indexed documents</option>
                  {selectedDocumentIds[0] && !indexedDocs.some((doc) => doc.document_id === selectedDocumentIds[0]) && (
                    <option value={selectedDocumentIds[0]} disabled style={{ background: "#16181C" }}>
                      Selected document is unavailable
                    </option>
                  )}
                  {indexedDocs.map((doc) => (
                    <option key={doc.document_id} value={doc.document_id} style={{ background: "#16181C" }}>
                      {doc.filename}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <span style={{ fontSize: "11px", color: "var(--text-muted)", whiteSpace: "nowrap", flexShrink: 0 }}>
              {indexedDocs.length} {indexedDocs.length === 1 ? "document" : "documents"} available
            </span>
          </div>
        )}

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
                        padding: "10px 14px",
                        borderRadius: "8px",
                        backgroundColor: isCurrent ? "var(--surface-raised)" : "rgba(255, 255, 255, 0.02)",
                        border: isCurrent ? "1px solid var(--accent-light)" : "1px solid var(--border)",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: "10px",
                        transition: "all 0.15s ease",
                      }}
                    >
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          <MessageSquare size={13} style={{ flexShrink: 0, color: isCurrent ? "var(--accent-light)" : "var(--text-muted)" }} />
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
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "4px", fontSize: "11px", color: "var(--text-muted)" }}>
                          <span>{sess.messages?.length || 0} messages</span>
                          <span>•</span>
                          <span>{new Date(sess.updatedAt || Date.now()).toLocaleDateString([], { month: "short", day: "numeric" })}</span>
                        </div>
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: "6px", flexShrink: 0 }}>
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: 600,
                            padding: "3px 8px",
                            borderRadius: "4px",
                            backgroundColor: isCurrent ? "rgba(255, 255, 255, 0.12)" : "rgba(255, 255, 255, 0.04)",
                            color: isCurrent ? "#FFFFFF" : "var(--text-secondary)",
                          }}
                        >
                          {isCurrent ? "Active" : "Continue"}
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
                              padding: "4px",
                              borderRadius: "4px",
                              display: "flex",
                              alignItems: "center",
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.color = "var(--rose-light)";
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.color = "var(--text-muted)";
                            }}
                          >
                            <Trash2 size={13} />
                          </button>
                        )}
                      </div>
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
                alignItems: "flex-start",
                justifyContent: "center",
                maxWidth: "720px",
                margin: "0 auto",
                textAlign: "left",
                padding: "20px 0",
                width: "100%",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                  GET STARTED
                </span>
                <span style={{ color: "var(--border)" }}>&bull;</span>
                <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--emerald-light)" }}>
                  DOCUMENT QUESTIONS
                </span>
              </div>
              <h2
                className="brand-font"
                style={{ fontSize: "22px", fontWeight: 700, marginBottom: "8px", color: "#FFFFFF", letterSpacing: "-0.02em" }}
              >
                {knowledgeSource === "public_book"
                  ? "Public Knowledge Book Explorer"
                  : "Analytical Document Workbench"}
              </h2>
              <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: "24px", maxWidth: "620px", lineHeight: 1.6 }}>
                {knowledgeSource === "public_book"
                  ? "Query the public knowledge book and inspect the supporting passages."
                  : "Ask about your indexed documents and inspect the cited passages. Choose a file above to narrow the evidence scope."}
              </p>

              {/* Structured Analytical Inquiry Manifest (Non-card layout) */}
              {availableModels.length === 0 && <p role="status">No configured answer models are available. Check provider configuration.</p>}
              <div style={{ display: "flex", flexDirection: "column", width: "100%", gap: "8px" }}>
                <div style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-muted)", marginBottom: "4px" }}>
                  Suggested questions
                </div>
                {promptSuggestions.map((item, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(undefined, item.query)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "12px 16px",
                      textAlign: "left",
                      background: "var(--surface)",
                      border: "1px solid var(--border)",
                      borderRadius: "6px",
                      color: "var(--text)",
                      cursor: "pointer",
                      transition: "all 0.12s ease",
                      gap: "14px",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.28)";
                      e.currentTarget.style.backgroundColor = "var(--surface-hover)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = "var(--border)";
                      e.currentTarget.style.backgroundColor = "var(--surface)";
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "14px", minWidth: 0 }}>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--text-muted)", fontWeight: 600, flexShrink: 0 }}>
                        0{i + 1}
                      </span>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: "13px", fontWeight: 600, color: "#FFFFFF", marginBottom: "2px" }}>
                          {item.title}
                        </div>
                        <div style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {item.query}
                        </div>
                      </div>
                    </div>
                    <ChevronDown size={14} color="var(--text-muted)" style={{ transform: "rotate(-90deg)", flexShrink: 0 }} />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div
              style={{
                maxWidth: "768px",
                width: "100%",
                margin: "0 auto",
                display: "flex",
                flexDirection: "column",
              }}
            >
              {messages.map((msg, index) => (
                <ChatMessage
                  key={msg.id || index}
                  source={msg.source}
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
                    padding: "4px 10px",
                    backgroundColor: "rgba(255, 255, 255, 0.05)",
                    border: "1px solid var(--border)",
                    borderRadius: "14px",
                    fontSize: "12px",
                    color: "var(--foreground)",
                    fontWeight: 500,
                    margin: "0 0 16px 42px",
                    width: "fit-content",
                  }}
                >
                  <Activity size={13} style={{ color: "var(--text-muted)" }} />
                  <span>{streamingPhase}</span>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* ── Modern Centered Input Bar ──────────────────────────── */}
        <div
          style={{
            padding: "12px 20px 18px",
            borderTop: "1px solid var(--border)",
            backgroundColor: "rgba(16, 18, 22, 0.9)",
            backdropFilter: "blur(14px)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <div style={{ maxWidth: "768px", width: "100%" }}>
            <form
              onSubmit={handleSend}
              style={{
                display: "flex",
                alignItems: "flex-end",
                gap: "8px",
                backgroundColor: "rgba(255, 255, 255, 0.04)",
                border: "1px solid var(--border)",
                borderRadius: "16px",
                padding: "8px 12px",
                boxShadow: "0 4px 20px rgba(0, 0, 0, 0.3)",
                transition: "border-color 0.15s ease",
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
                style={{ padding: "8px", borderRadius: "10px", color: "var(--text-muted)" }}
                title="Attach and ingest document"
                aria-label="Attach and ingest document"
              >
                <Paperclip size={18} />
              </button>

              <textarea
                id="chat-query-input"
                aria-label={knowledgeSource === "public_book" ? "Ask a question about the public knowledge book" : "Ask a question about your documents"}
                ref={textareaRef}
                rows={1}
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  knowledgeSource === "public_book"
                    ? "Ask anything about the public knowledge book..."
                    : "Ask anything about your documents..."
                }
                disabled={isStreaming}
                style={{
                  flex: 1,
                  background: "transparent",
                  border: "none",
                  color: "#FFFFFF",
                  fontSize: "14.5px",
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
                disabled={!inputQuery.trim() || isStreaming || !availableModels.includes(activeModel)}
                className="btn btn-primary"
                aria-label="Submit query"
                style={{
                  padding: "8px 14px",
                  borderRadius: "10px",
                  flexShrink: 0,
                  fontSize: "13px",
                  gap: "6px",
                }}
              >
                <Send size={14} />
                <span>Ask</span>
              </button>
            </form>

            <div
              style={{
                textAlign: "center",
                fontSize: "11px",
                color: "var(--text-muted)",
                marginTop: "8px",
              }}
            >
              Answers use the selected source. Check the cited passages for important decisions.
            </div>
          </div>
        </div>
      </div>

      {/* ── Right PDF / Markdown Verifiable Source Inspector Panel ─────────────────────── */}
      {showPdfPanel && (pdfDocId || selectedCitation) && (
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
              {selectedCitation?.source_type === "public_book" ? (
                <BookOpen size={15} color="var(--accent-light)" />
              ) : (
                <FileText size={15} color="var(--accent-light)" />
              )}
              <span style={{ fontSize: "12.5px", fontWeight: 700, color: "#FFFFFF" }}>
                Source & Margin Inspector
              </span>
              {selectedCitation && (
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "11px",
                    color: "var(--text-secondary)",
                    backgroundColor: "rgba(255, 255, 255, 0.04)",
                    padding: "2px 6px",
                    borderRadius: "3px",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  {selectedCitation.page_number ? `PAGE // 0${selectedCitation.page_number}` : "SOURCE REF"}
                </span>
              )}
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

          {/* Inspector Content */}
          <div style={{ flex: 1, height: "calc(100% - 49px)", overflow: "auto" }}>
            {selectedCitation?.source_type === "public_book" ? (
              <div style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "16px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "8px" }}>
                  <span className="badge">
                    Public Knowledge Book Evidence
                  </span>
                  <span style={{ fontSize: "12px", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                    {selectedCitation.source_filename}
                  </span>
                </div>

                <div
                  style={{
                    backgroundColor: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                    padding: "16px",
                  }}
                >
                  <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "10px" }}>
                    Source passage
                  </div>
                  <p style={{ fontSize: "13.5px", lineHeight: "1.7", color: "var(--text)", margin: 0, whiteSpace: "pre-wrap" }}>
                    {selectedCitation.excerpt || "No excerpt text available for this citation."}
                  </p>
                </div>

                <div style={{ display: "flex", gap: "10px", marginTop: "4px" }}>
                  <a
                    href="/public-book"
                    className="btn btn-secondary"
                    style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "12px", padding: "6px 12px" }}
                  >
                    <BookOpen size={13} />
                    <span>Open in Public Book Explorer</span>
                  </a>
                </div>
              </div>
            ) : pdfDocId ? (
              <PDFViewer
                fileUrl={getDocumentFileUrl(pdfDocId)}
                filename={pdfFilename}
                initialPage={selectedCitation?.page_number || 1}
                highlights={activeCitations.filter((c) => c.document_id === pdfDocId)}
                activeCitation={selectedCitation}
              />
            ) : (
              <div style={{ padding: "24px", color: "var(--text-muted)", textAlign: "center" }}>
                Select a citation from the message to inspect its source document.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
