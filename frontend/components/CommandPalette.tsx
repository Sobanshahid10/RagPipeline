"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { 
  Search, 
  MessageSquare, 
  FileText, 
  BarChart3, 
  UploadCloud, 
  Settings, 
  ExternalLink, 
  Sparkles, 
  Zap,
  Layers,
  ArrowRight
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface CommandItem {
  id: string;
  title: string;
  category: "Navigation" | "Actions" | "Developer";
  icon: any;
  action: () => void;
  shortcut?: string;
}

export const CommandPalette: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onOpenSettings?: () => void;
  onNewChat?: () => void;
}> = ({ isOpen, onClose, onOpenSettings, onNewChat }) => {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const commands: CommandItem[] = [
    {
      id: "chat",
      title: "Open Streaming Chat",
      category: "Navigation",
      icon: MessageSquare,
      action: () => {
        router.push("/chat");
        onClose();
      },
      shortcut: "G C",
    },
    {
      id: "documents",
      title: "Browse Document Library",
      category: "Navigation",
      icon: FileText,
      action: () => {
        router.push("/documents");
        onClose();
      },
      shortcut: "G D",
    },
    {
      id: "dashboard",
      title: "View Admin & Telemetry Dashboard",
      category: "Navigation",
      icon: BarChart3,
      action: () => {
        router.push("/dashboard");
        onClose();
      },
      shortcut: "G A",
    },
    {
      id: "new-chat",
      title: "Start New Chat Conversation",
      category: "Actions",
      icon: Sparkles,
      action: () => {
        onNewChat?.();
        router.push("/chat");
        onClose();
      },
      shortcut: "⌘ N",
    },
    {
      id: "upload",
      title: "Upload & Ingest Document",
      category: "Actions",
      icon: UploadCloud,
      action: () => {
        router.push("/documents");
        onClose();
      },
      shortcut: "⌘ U",
    },
    {
      id: "settings",
      title: "Platform & Model Settings",
      category: "Actions",
      icon: Settings,
      action: () => {
        onClose();
        onOpenSettings?.();
      },
      shortcut: "⌘ ,",
    },
    {
      id: "fastapi",
      title: "FastAPI Swagger Documentation",
      category: "Developer",
      icon: Layers,
      action: () => {
        window.open("http://localhost:8001/docs", "_blank");
        onClose();
      },
    },
    {
      id: "jaeger",
      title: "Jaeger Distributed Traces",
      category: "Developer",
      icon: Zap,
      action: () => {
        window.open("http://localhost:16686", "_blank");
        onClose();
      },
    },
  ];

  const filteredCommands = commands.filter((c) =>
    c.title.toLowerCase().includes(query.toLowerCase()) ||
    c.category.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQuery("");
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Keyboard navigation inside palette
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % (filteredCommands.length || 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filteredCommands.length) % (filteredCommands.length || 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filteredCommands[selectedIndex]) {
        filteredCommands[selectedIndex].action();
      }
    } else if (e.key === "Escape") {
      onClose();
    }
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
            alignItems: "flex-start",
            justifyContent: "center",
            paddingTop: "14vh",
            zIndex: 9999,
          }}
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -10 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            style={{
              width: "100%",
              maxWidth: "580px",
              backgroundColor: "rgba(16, 18, 29, 0.95)",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: "16px",
              boxShadow: "0 24px 64px rgba(0, 0, 0, 0.8), 0 0 32px var(--accent-glow)",
              overflow: "hidden",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Input Bar */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                padding: "16px 20px",
                borderBottom: "1px solid var(--border)",
              }}
            >
              <Search size={18} color="var(--accent-light)" />
              <input
                ref={inputRef}
                type="text"
                placeholder="Type a command or search workspace..."
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setSelectedIndex(0);
                }}
                onKeyDown={handleKeyDown}
                style={{
                  flex: 1,
                  background: "transparent",
                  border: "none",
                  color: "#FFFFFF",
                  fontSize: "15px",
                  outline: "none",
                  fontFamily: "inherit",
                }}
              />
              <span
                style={{
                  fontSize: "11px",
                  color: "var(--text-muted)",
                  padding: "3px 6px",
                  borderRadius: "5px",
                  backgroundColor: "rgba(255, 255, 255, 0.06)",
                  border: "1px solid var(--border)",
                }}
              >
                ESC
              </span>
            </div>

            {/* Command List */}
            <div
              style={{
                maxHeight: "360px",
                overflowY: "auto",
                padding: "8px",
              }}
            >
              {filteredCommands.length === 0 ? (
                <div style={{ padding: "32px 16px", textAlign: "center", color: "var(--text-muted)", fontSize: "13.5px" }}>
                  No matching commands found.
                </div>
              ) : (
                filteredCommands.map((item, idx) => {
                  const Icon = item.icon;
                  const isSelected = idx === selectedIndex;
                  return (
                    <div
                      key={item.id}
                      onClick={() => item.action()}
                      onMouseEnter={() => setSelectedIndex(idx)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "10px 14px",
                        borderRadius: "10px",
                        backgroundColor: isSelected ? "rgba(99, 102, 241, 0.16)" : "transparent",
                        border: isSelected ? "1px solid rgba(99, 102, 241, 0.35)" : "1px solid transparent",
                        cursor: "pointer",
                        transition: "all 0.12s ease",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <Icon size={17} color={isSelected ? "var(--accent-light)" : "var(--text-muted)"} />
                        <span style={{ fontSize: "13.5px", fontWeight: isSelected ? 600 : 500, color: isSelected ? "#FFFFFF" : "var(--text)" }}>
                          {item.title}
                        </span>
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span
                          style={{
                            fontSize: "10.5px",
                            color: "var(--text-muted)",
                            textTransform: "uppercase",
                            letterSpacing: "0.04em",
                          }}
                        >
                          {item.category}
                        </span>
                        {item.shortcut && (
                          <span
                            style={{
                              fontSize: "11px",
                              color: isSelected ? "var(--accent-lighter)" : "var(--text-muted)",
                              fontFamily: "'JetBrains Mono', monospace",
                              backgroundColor: "rgba(255, 255, 255, 0.05)",
                              padding: "2px 6px",
                              borderRadius: "4px",
                            }}
                          >
                            {item.shortcut}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Footer */}
            <div
              style={{
                padding: "10px 20px",
                borderTop: "1px solid var(--border)",
                backgroundColor: "rgba(11, 13, 20, 0.6)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                fontSize: "11.5px",
                color: "var(--text-muted)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <span>Use <kbd style={{ padding: "1px 5px", background: "rgba(255,255,255,0.08)", borderRadius: "3px" }}>↑</kbd> <kbd style={{ padding: "1px 5px", background: "rgba(255,255,255,0.08)", borderRadius: "3px" }}>↓</kbd> to navigate</span>
                <span><kbd style={{ padding: "1px 5px", background: "rgba(255,255,255,0.08)", borderRadius: "3px" }}>↵</kbd> to select</span>
              </div>
              <span>Nexus RAG Spotlight</span>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
