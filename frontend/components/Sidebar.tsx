"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { chatHistoryKey } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import {
  MessageSquare,
  FileText,
  Layers,
  LogOut,
  Database,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  Search,
  Settings,
  Plus,
  ChevronsUpDown,
  Command,
  Trash2
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { CommandPalette } from "@/components/CommandPalette";
import { SettingsModal } from "@/components/SettingsModal";

export const Sidebar: React.FC = () => {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logoutUser } = useAuth();
  const historyKey = chatHistoryKey(user);
  const [collapsed, setCollapsed] = useState(false);
  const [isCommandOpen, setIsCommandOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [recentSessions, setRecentSessions] = useState<Array<{ id: string; title: string; updatedAt: number }>>([]);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Load and subscribe to saved chat sessions for continuing conversations
  useEffect(() => {
    const loadSessions = () => {
      setRecentSessions([]);
      if (!historyKey) return;
      try {
        const stored = localStorage.getItem(historyKey);
        if (stored) {
          const parsed = JSON.parse(stored);
          if (Array.isArray(parsed)) {
            setRecentSessions(parsed);
          }
        }
      } catch (e) {}
    };

    loadSessions();
    window.addEventListener("rag-sessions-updated", loadSessions);
    window.addEventListener("storage", loadSessions);
    return () => {
      window.removeEventListener("rag-sessions-updated", loadSessions);
      window.removeEventListener("storage", loadSessions);
    };
  }, [historyKey]);

  const handleNewConversation = () => {
    window.dispatchEvent(new CustomEvent("rag-new-chat"));
    router.push("/chat");
  };

  const handleDeleteSessionFromSidebar = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!historyKey) return;
    try {
      const stored = localStorage.getItem(historyKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        const filtered = parsed.filter((s: any) => s.id !== sessionId);
        localStorage.setItem(historyKey, JSON.stringify(filtered));
        setRecentSessions(filtered);
        window.dispatchEvent(new CustomEvent("rag-delete-session", {detail:{id:sessionId}}));
        window.dispatchEvent(new CustomEvent("rag-sessions-updated"));
      }
    } catch (e) {}
  };

  // Keyboard shortcut listener for ⌘K and ⌘,
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsCommandOpen((prev) => !prev);
      } else if ((e.metaKey || e.ctrlKey) && e.key === ",") {
        e.preventDefault();
        setIsSettingsOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Close user dropdown menu when clicking outside or pressing Escape
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setIsUserMenuOpen(false);
      }
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isUserMenuOpen) {
        setIsUserMenuOpen(false);
      }
    };
    if (isUserMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleEscape);
      return () => {
        document.removeEventListener("mousedown", handleClickOutside);
        document.removeEventListener("keydown", handleEscape);
      };
    }
  }, [isUserMenuOpen]);

  const navItems = [
    {
      name: "Public Book",
      href: "/public-book",
      icon: Search,
      badge: null,
    },
    {
      name: "Streaming Chat",
      href: "/chat",
      icon: MessageSquare,
      badge: null,
    },
    {
      name: "Document Library",
      href: "/documents",
      icon: FileText,
      badge: null,
    },
    {
      name: "Admin Dashboard",
      href: "/dashboard",
      icon: BarChart3,
      badge: null,
    },
  ];

  const tenantName = user?.tenant?.name || "Production Enterprise";
  const userInitials = user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : "NX";

  return (
    <>
      <aside
        style={{
          width: collapsed ? "var(--sidebar-collapsed-width)" : "var(--sidebar-width)",
          minWidth: collapsed ? "var(--sidebar-collapsed-width)" : "var(--sidebar-width)",
          height: "100vh",
          backgroundColor: "var(--surface)",
          borderRight: "1px solid var(--border)",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: collapsed ? "18px 8px" : "18px 14px",
          position: "sticky",
          top: 0,
          zIndex: 40,
          transition: "all 0.22s cubic-bezier(0.16, 1, 0.3, 1)",
        }}
      >
        {/* ── Top Header & Navigation ────────────────────────────── */}
        <div>
          {/* Brand Logo */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: collapsed ? "center" : "space-between",
              padding: collapsed ? "4px 0" : "4px 6px",
              marginBottom: "18px",
            }}
          >
            <Link
              href="/chat"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                minWidth: 0,
                textDecoration: "none",
              }}
            >
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "6px",
                  background: "#1E2025",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <Layers size={17} color="#FFFFFF" />
              </div>

              {!collapsed && (
                <div style={{ minWidth: 0 }}>
                  <span
                    className="brand-font"
                    style={{
                      display: "block",
                      fontSize: "15px",
                      fontWeight: 600,
                      letterSpacing: "-0.015em",
                      lineHeight: 1.2,
                      color: "#FFFFFF",
                    }}
                  >
                    RAG Pipeline
                  </span>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "2px" }}>
                    <span className="status-dot-active" />
                    <span
                      style={{
                        fontSize: "11px",
                        color: "var(--text-muted)",
                        fontWeight: 500,
                      }}
                    >
                      Document workspace
                    </span>
                  </div>
                </div>
              )}
            </Link>

            {!collapsed && (
              <button
                onClick={() => setCollapsed(true)}
                title="Collapse sidebar"
                aria-label="Collapse sidebar"
                className="btn btn-ghost"
                style={{
                  padding: "6px",
                  borderRadius: "6px",
                  color: "var(--text-muted)",
                }}
              >
                <ChevronLeft size={16} />
              </button>
            )}
          </div>

          {collapsed && (
            <button
              onClick={() => setCollapsed(false)}
              title="Expand sidebar"
              aria-label="Expand sidebar"
              className="btn btn-ghost"
              style={{
                width: "100%",
                padding: "8px 0",
                marginBottom: "14px",
                color: "var(--text-muted)",
              }}
            >
              <ChevronRight size={16} />
            </button>
          )}

          {/* Quick Action: New Chat & Search */}
          {!collapsed ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "18px" }}>
              <button
                onClick={handleNewConversation}
                className="btn btn-primary"
                style={{
                  width: "100%",
                  padding: "9px 12px",
                  fontSize: "13px",
                  justifyContent: "flex-start",
                  borderRadius: "9px",
                }}
              >
                <Plus size={16} />
                <span>New Conversation</span>
              </button>

              <button
                onClick={() => setIsCommandOpen(true)}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "8px 12px",
                  borderRadius: "8px",
                  backgroundColor: "rgba(255, 255, 255, 0.04)",
                  border: "1px solid var(--border)",
                  color: "var(--text-muted)",
                  fontSize: "12.5px",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Search size={14} />
                  <span>Search commands...</span>
                </div>
                <kbd style={{ fontSize: "10px", padding: "1px 5px", background: "rgba(255,255,255,0.08)", borderRadius: "4px" }}>
                  ⌘K
                </kbd>
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "16px" }}>
              <button
                onClick={handleNewConversation}
                title="New Conversation"
                className="btn btn-primary"
                style={{
                  width: "100%",
                  padding: "10px 0",
                  borderRadius: "9px",
                  display: "flex",
                  justifyContent: "center",
                }}
              >
                <Plus size={16} />
              </button>
              <button
                onClick={() => setIsCommandOpen(true)}
                title="Search commands (⌘K)"
                className="btn btn-secondary"
                style={{
                  width: "100%",
                  padding: "10px 0",
                  borderRadius: "9px",
                  display: "flex",
                  justifyContent: "center",
                }}
              >
                <Search size={16} />
              </button>
            </div>
          )}

          {/* Workspace Nav Items */}
          <nav style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            {!collapsed && (
              <div
                style={{
                  fontSize: "10px",
                  color: "var(--text-muted)",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  padding: "4px 8px 6px",
                }}
              >
                Workspace
              </div>
            )}

            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  title={collapsed ? item.name : undefined}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: collapsed ? "center" : "space-between",
                    gap: "12px",
                    padding: collapsed ? "11px 0" : "10px 12px",
                    borderRadius: "6px",
                    fontSize: "13px",
                    fontWeight: isActive ? 600 : 500,
                    color: isActive ? "#FFFFFF" : "var(--text-secondary)",
                    backgroundColor: isActive ? "rgba(255, 255, 255, 0.08)" : "transparent",
                    border: isActive
                      ? "1px solid rgba(255, 255, 255, 0.12)"
                      : "1px solid transparent",
                    boxShadow: "none",
                    transition: "all 0.15s ease",
                    textDecoration: "none",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <Icon
                      size={16}
                      color={isActive ? "#FFFFFF" : "var(--text-muted)"}
                      style={{ flexShrink: 0 }}
                    />
                    {!collapsed && <span>{item.name}</span>}
                  </div>

                  {!collapsed && item.badge && (
                    <span
                      style={{
                        fontSize: "10px",
                        fontWeight: 600,
                        padding: "1px 6px",
                        borderRadius: "4px",
                        backgroundColor: isActive ? "rgba(255, 255, 255, 0.12)" : "rgba(255, 255, 255, 0.05)",
                        color: isActive ? "#FFFFFF" : "var(--text-muted)",
                      }}
                    >
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}

          </nav>

          {/* Recent Conversations (Continuing Old Chats) */}
          {!collapsed && (
            <div style={{ marginTop: "18px", display: "flex", flexDirection: "column", gap: "4px" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "4px 8px 6px",
                }}
              >
                <span
                  style={{
                    fontSize: "10px",
                    color: "var(--text-muted)",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                  }}
                >
                  Recent Chats
                </span>
                <button
                  onClick={handleNewConversation}
                  title="New conversation"
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    padding: "2px",
                    display: "flex",
                    alignItems: "center",
                  }}
                >
                  <Plus size={12} />
                </button>
              </div>

              {recentSessions.length === 0 ? (
                <div style={{ padding: "6px 8px", fontSize: "12px", color: "var(--text-muted)" }}>
                  No saved chats
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "2px", maxHeight: "170px", overflowY: "auto" }}>
                  {recentSessions.slice(0, 10).map((sess) => {
                    return (
                      <div
                        key={sess.id}
                        onClick={() => {
                          window.dispatchEvent(new CustomEvent("rag-switch-session", { detail: { id: sess.id } }));
                          router.push(`/chat?session=${sess.id}`);
                        }}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "6px 8px",
                          borderRadius: "6px",
                          fontSize: "12px",
                          color: "var(--text-secondary)",
                          cursor: "pointer",
                          backgroundColor: "transparent",
                          transition: "all 0.12s ease",
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = "var(--surface-hover)";
                          e.currentTarget.style.color = "#FFFFFF";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = "transparent";
                          e.currentTarget.style.color = "var(--text-secondary)";
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", minWidth: 0, flex: 1 }}>
                          <MessageSquare size={13} style={{ flexShrink: 0, color: "var(--text-muted)" }} />
                          <span
                            style={{
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {sess.title || "Untitled Chat"}
                          </span>
                        </div>

                        <button
                          onClick={(e) => handleDeleteSessionFromSidebar(sess.id, e)}
                          title="Delete conversation"
                          style={{
                            background: "transparent",
                            border: "none",
                            color: "var(--text-muted)",
                            cursor: "pointer",
                            padding: "2px 4px",
                            display: "flex",
                            alignItems: "center",
                            opacity: 0.6,
                            flexShrink: 0,
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.opacity = "1";
                            e.currentTarget.style.color = "var(--rose-light)";
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.opacity = "0.6";
                            e.currentTarget.style.color = "var(--text-muted)";
                          }}
                        >
                          <Trash2 size={11} />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── Footer Profile & Session ────────────────────────────── */}
        <div
          style={{
            borderTop: "1px solid var(--border)",
            paddingTop: "14px",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
          }}
        >
          {user && (
            <div ref={userMenuRef} style={{ position: "relative" }}>
              {/* Floating User Menu Popover */}
              <AnimatePresence>
                {isUserMenuOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: 6, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 6, scale: 0.98 }}
                    transition={{ duration: 0.12, ease: "easeOut" }}
                    style={{
                      position: "absolute",
                      bottom: "calc(100% + 8px)",
                      left: 0,
                      width: collapsed ? "220px" : "100%",
                      backgroundColor: "var(--surface-raised)",
                      border: "1px solid var(--border)",
                      borderRadius: "8px",
                      padding: "6px",
                      boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.4)",
                      zIndex: 60,
                      display: "flex",
                      flexDirection: "column",
                      gap: "2px",
                    }}
                  >
                    {/* User Metadata Header */}
                    <div style={{ padding: "8px 10px 6px", borderBottom: "1px solid var(--border-subtle)" }}>
                      <div
                        style={{
                          fontSize: "12px",
                          fontWeight: 600,
                          color: "#FFFFFF",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {user.email}
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "5px", marginTop: "3px" }}>
                        <ShieldCheck size={11} color="var(--emerald-light)" />
                        <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                          {tenantName}
                        </span>
                      </div>
                    </div>

                    {/* Configuration & Settings Action */}
                    <button
                      onClick={() => {
                        setIsSettingsOpen(true);
                        setIsUserMenuOpen(false);
                      }}
                      className="btn btn-ghost"
                      style={{
                        width: "100%",
                        justifyContent: "space-between",
                        padding: "7px 10px",
                        fontSize: "12px",
                        borderRadius: "6px",
                        color: "var(--text)",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <Settings size={14} color="var(--text-muted)" />
                        <span>Configuration & Settings</span>
                      </div>
                      <kbd
                        style={{
                          fontSize: "10px",
                          color: "var(--text-muted)",
                          background: "rgba(255, 255, 255, 0.06)",
                          padding: "1px 5px",
                          borderRadius: "3px",
                          fontFamily: "inherit",
                        }}
                      >
                        ⌘,
                      </kbd>
                    </button>

                    {/* Quick Command Palette Action */}
                    <button
                      onClick={() => {
                        setIsCommandOpen(true);
                        setIsUserMenuOpen(false);
                      }}
                      className="btn btn-ghost"
                      style={{
                        width: "100%",
                        justifyContent: "space-between",
                        padding: "7px 10px",
                        fontSize: "12px",
                        borderRadius: "6px",
                        color: "var(--text)",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <Command size={14} color="var(--text-muted)" />
                        <span>Command Palette</span>
                      </div>
                      <kbd
                        style={{
                          fontSize: "10px",
                          color: "var(--text-muted)",
                          background: "rgba(255, 255, 255, 0.06)",
                          padding: "1px 5px",
                          borderRadius: "3px",
                          fontFamily: "inherit",
                        }}
                      >
                        ⌘K
                      </kbd>
                    </button>

                    <div style={{ height: "1px", backgroundColor: "var(--border-subtle)", margin: "3px 0" }} />

                    {/* Sign Out Action */}
                    <button
                      onClick={() => {
                        setIsUserMenuOpen(false);
                        logoutUser();
                      }}
                      className="btn btn-ghost"
                      style={{
                        width: "100%",
                        justifyContent: "flex-start",
                        padding: "7px 10px",
                        fontSize: "12px",
                        borderRadius: "6px",
                        color: "var(--rose-light)",
                        gap: "8px",
                      }}
                    >
                      <LogOut size={14} color="var(--rose-light)" />
                      <span>Sign Out</span>
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Interactive Admin / User Card */}
              <div
                role="button"
                tabIndex={0}
                aria-haspopup="menu"
                aria-expanded={isUserMenuOpen}
                onClick={() => setIsUserMenuOpen((prev) => !prev)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setIsUserMenuOpen((prev) => !prev);
                  }
                }}
                title={`${user.email} (${tenantName}) - Click for menu`}
                style={{
                  padding: collapsed ? "6px" : "8px 10px",
                  backgroundColor: isUserMenuOpen ? "var(--surface-hover)" : "rgba(255, 255, 255, 0.025)",
                  borderRadius: "8px",
                  border: isUserMenuOpen ? "1px solid var(--border-hover)" : "1px solid var(--border)",
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                  userSelect: "none",
                }}
              >
                <div
                  style={{
                    width: "30px",
                    height: "30px",
                    borderRadius: "6px",
                    background: "var(--surface-raised)",
                    border: "1px solid var(--border)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "12px",
                    fontWeight: 600,
                    color: "var(--foreground)",
                    flexShrink: 0,
                  }}
                >
                  {userInitials}
                </div>

                {!collapsed && (
                  <>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div
                        style={{
                          fontSize: "12.5px",
                          fontWeight: 600,
                          color: "var(--text)",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {user.email}
                      </div>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "5px",
                          marginTop: "1px",
                        }}
                      >
                        <ShieldCheck size={11} color="var(--emerald-light)" />
                        <span
                          style={{
                            fontSize: "11px",
                            color: "var(--text-secondary)",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {tenantName}
                        </span>
                      </div>
                    </div>

                    <ChevronsUpDown size={14} color="var(--text-muted)" style={{ flexShrink: 0, opacity: 0.7 }} />
                  </>
                )}
              </div>
            </div>
          )}

          {!collapsed && (
            <div
              style={{
                marginTop: "12px",
                paddingTop: "10px",
                borderTop: "1px solid var(--border-subtle)",
                display: "flex",
                flexWrap: "wrap",
                gap: "8px",
                fontSize: "11px",
                color: "var(--text-muted)",
              }}
            >
              <Link href="/privacy" style={{ color: "var(--text-muted)" }}>Privacy</Link>
              <span>&bull;</span>
              <Link href="/terms" style={{ color: "var(--text-muted)" }}>Terms</Link>
              <span>&bull;</span>
              <Link href="/cookies" style={{ color: "var(--text-muted)" }}>Cookies</Link>
            </div>
          )}
        </div>
      </aside>

      {/* Global Modals */}
      <CommandPalette
        isOpen={isCommandOpen}
        onClose={() => setIsCommandOpen(false)}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </>
  );
};
