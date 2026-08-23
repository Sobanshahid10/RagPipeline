"use client";

import React, { useState, useRef, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { 
  streamQuery, 
  CitationBlock, 
  QueryMetadata, 
  getDocumentFileUrl 
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
  HelpCircle
} from "lucide-react";

interface MessageState {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: CitationBlock[];
  metadata?: QueryMetadata;
}

export default function ChatPage() {
  const { token, user } = useAuth();
  const [messages, setMessages] = useState<MessageState[]>([]);
  const [inputQuery, setInputQuery] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeCitations, setActiveCitations] = useState<CitationBlock[]>([]);
  const [selectedCitation, setSelectedCitation] = useState<CitationBlock | null>(null);
  const [pdfDocId, setPdfDocId] = useState<string | null>(null);
  const [pdfFilename, setPdfFilename] = useState<string>("document.pdf");
  const [isPdfExpanded, setIsPdfExpanded] = useState(false);
  const [showPdfPanel, setShowPdfPanel] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  const handleCitationClick = (citation: CitationBlock) => {
    setSelectedCitation(citation);
    if (citation.document_id) {
      setPdfDocId(citation.document_id);
    }
    if (citation.source_filename) {
      setPdfFilename(citation.source_filename);
    }
    setShowPdfPanel(true);
  };

  const handleSend = async (e?: React.FormEvent, customPrompt?: string) => {
    if (e) e.preventDefault();
    const queryText = (customPrompt || inputQuery).trim();
    if (!queryText || isStreaming || !token) return;

    setError(null);
    setInputQuery("");

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

    let accumulatedContent = "";
    const currentCitations: CitationBlock[] = [];

    try {
      for await (const event of streamQuery(queryText, token)) {
        if (event.type === "token") {
          accumulatedContent += event.content;
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

          // Auto-open PDF viewer on the first cited document
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
          setIsStreaming(false);
        }
      }
    } catch (err: any) {
      console.error("Stream query error:", err);
      setError(err.message || "Failed to stream query response.");
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId && !msg.content
            ? {
                ...msg,
                content:
                  "⚠️ An error occurred while retrieving or generating an answer. Please check backend connectivity.",
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
  };

  const promptSuggestions = [
    "What are the main key takeaways in the uploaded document?",
    "Find specific financial figures and cite exact pages.",
    "Summarize the architecture and layout pipeline.",
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
      {/* Left Chat Area */}
      <div
        style={{
          flex: showPdfPanel && !isPdfExpanded ? "1 1 50%" : "1 1 100%",
          display: showPdfPanel && isPdfExpanded ? "none" : "flex",
          flexDirection: "column",
          height: "100%",
          minWidth: "360px",
          borderRight: showPdfPanel ? "1px solid var(--border)" : "none",
          transition: "flex 0.3s ease",
        }}
      >
        {/* Top Header */}
        <div
          style={{
            padding: "16px 24px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            backgroundColor: "rgba(19, 19, 26, 0.6)",
            backdropFilter: "blur(8px)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "8px",
                background: "var(--accent-gradient)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Bot size={18} color="#FFFFFF" />
            </div>
            <div>
              <h2 style={{ fontSize: "16px", fontWeight: 600 }}>RAG Assistant</h2>
              <span style={{ fontSize: "12px", color: "var(--muted)" }}>
                Layout-aware grounded answers with verifiable bounding box citations
              </span>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            {messages.length > 0 && (
              <button
                onClick={clearChat}
                className="btn btn-ghost"
                style={{ padding: "6px 10px", fontSize: "12px" }}
                title="Clear conversation"
              >
                <Trash2 size={14} />
                <span>Clear</span>
              </button>
            )}
          </div>
        </div>

        {/* Error Notification */}
        {error && (
          <div
            style={{
              margin: "12px 24px 0",
              padding: "10px 14px",
              backgroundColor: "rgba(239, 68, 68, 0.12)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              borderRadius: "8px",
              color: "#F87171",
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

        {/* Message Stream Scroll Area */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "24px",
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
                maxWidth: "600px",
                margin: "0 auto",
                textAlign: "center",
              }}
            >
              <div
                style={{
                  width: "60px",
                  height: "60px",
                  borderRadius: "16px",
                  background: "rgba(99, 102, 241, 0.12)",
                  border: "1px solid rgba(99, 102, 241, 0.3)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "20px",
                  boxShadow: "0 0 24px var(--accent-glow)",
                }}
              >
                <Sparkles size={28} color="var(--accent-light)" />
              </div>

              <h2
                className="brand-font"
                style={{ fontSize: "22px", fontWeight: 700, marginBottom: "8px" }}
              >
                Ask anything about your documents
              </h2>
              <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: "28px" }}>
                Answers are streamed live with interactive citation chips linking directly to bounding boxes in the original PDF.
              </p>

              {/* Suggestions */}
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", width: "100%" }}>
                {promptSuggestions.map((prompt, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(undefined, prompt)}
                    className="card card-interactive"
                    style={{
                      padding: "12px 16px",
                      textAlign: "left",
                      fontSize: "13px",
                      color: "var(--text)",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                    }}
                  >
                    <HelpCircle size={15} color="var(--accent-light)" />
                    <span>{prompt}</span>
                  </button>
                ))}
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
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input Bar */}
        <div
          style={{
            padding: "16px 24px",
            borderTop: "1px solid var(--border)",
            backgroundColor: "rgba(19, 19, 26, 0.75)",
            backdropFilter: "blur(8px)",
          }}
        >
          <form
            onSubmit={handleSend}
            style={{
              display: "flex",
              alignItems: "flex-end",
              gap: "12px",
              backgroundColor: "rgba(10, 10, 15, 0.9)",
              border: "1px solid var(--border)",
              borderRadius: "12px",
              padding: "8px 12px",
              boxShadow: "0 4px 20px rgba(0, 0, 0, 0.3)",
            }}
          >
            <textarea
              ref={textareaRef}
              rows={1}
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your indexed documents (Press Enter to submit)..."
              disabled={isStreaming}
              style={{
                flex: 1,
                background: "transparent",
                border: "none",
                color: "var(--text)",
                fontSize: "14px",
                outline: "none",
                resize: "none",
                padding: "8px 4px",
                fontFamily: "inherit",
                lineHeight: "1.4",
                maxHeight: "120px",
              }}
            />

            <button
              type="submit"
              disabled={!inputQuery.trim() || isStreaming}
              className="btn btn-primary"
              style={{
                padding: "10px 14px",
                borderRadius: "8px",
                flexShrink: 0,
              }}
            >
              <Send size={16} />
              <span>Ask</span>
            </button>
          </form>
          <div
            style={{
              fontSize: "11px",
              color: "var(--muted)",
              marginTop: "8px",
              textAlign: "center",
            }}
          >
            Powered by Multi-Tenant Agentic Vector + BM25 + GraphRAG Fusion
          </div>
        </div>
      </div>

      {/* Right PDF Viewer Side Panel */}
      {showPdfPanel && pdfDocId && (
        <div
          style={{
            flex: isPdfExpanded ? "1 1 100%" : "1 1 50%",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            backgroundColor: "#0A0A0F",
            position: "relative",
            transition: "flex 0.3s ease",
          }}
        >
          {/* Panel Header Controls */}
          <div
            style={{
              padding: "8px 16px",
              borderBottom: "1px solid var(--border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              backgroundColor: "var(--surface)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <FileText size={16} color="var(--accent-light)" />
              <span style={{ fontSize: "13px", fontWeight: 600, color: "#FFFFFF" }}>
                Source Inspector
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <button
                onClick={() => setIsPdfExpanded(!isPdfExpanded)}
                className="btn btn-ghost"
                style={{ padding: "6px 8px", height: "28px" }}
                title={isPdfExpanded ? "Split View" : "Expand to Fullscreen"}
              >
                {isPdfExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
              </button>
              <button
                onClick={() => setShowPdfPanel(false)}
                className="btn btn-ghost"
                style={{ padding: "6px 8px", height: "28px" }}
                title="Close PDF Inspector"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* PDF Viewer */}
          <div style={{ flex: 1, height: "calc(100% - 45px)" }}>
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
