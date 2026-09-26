"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { 
  MessageSquare, 
  FileText, 
  Layers, 
  LogOut, 
  Sparkles, 
  Database, 
  ExternalLink, 
  BarChart3, 
  ChevronLeft, 
  ChevronRight, 
  Activity, 
  ShieldCheck, 
  Search,
  Settings,
  Plus
} from "lucide-react";
import { CommandPalette } from "@/components/CommandPalette";
import { SettingsModal } from "@/components/SettingsModal";

export const Sidebar: React.FC = () => {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logoutUser } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [isCommandOpen, setIsCommandOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

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

  const navItems = [
    {
      name: "Streaming Chat",
      href: "/chat",
      icon: MessageSquare,
      badge: "Live SSE",
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
      badge: "SLA",
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
                  width: "36px",
                  height: "36px",
                  borderRadius: "10px",
                  background: "var(--accent-gradient)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 0 18px var(--accent-glow)",
                  flexShrink: 0,
                }}
              >
                <Sparkles size={19} color="#FFFFFF" />
              </div>

              {!collapsed && (
                <div style={{ minWidth: 0 }}>
                  <h1
                    className="brand-font"
                    style={{
                      fontSize: "17px",
                      fontWeight: 800,
                      letterSpacing: "-0.02em",
                      lineHeight: 1.2,
                      color: "#FFFFFF",
                    }}
                  >
                    Nexus RAG
                  </h1>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "2px" }}>
                    <span className="status-dot-active" />
                    <span
                      style={{
                        fontSize: "10.5px",
                        color: "var(--accent-light)",
                        fontWeight: 600,
                        letterSpacing: "0.06em",
                        textTransform: "uppercase",
                      }}
                    >
                      Enterprise v1.0
                    </span>
                  </div>
                </div>
              )}
            </Link>

            {!collapsed && (
              <button
                onClick={() => setCollapsed(true)}
                title="Collapse sidebar"
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
                onClick={() => router.push("/chat")}
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
            <button
              onClick={() => setIsCommandOpen(true)}
              title="Search commands (⌘K)"
              className="btn btn-secondary"
              style={{
                width: "100%",
                padding: "10px 0",
                marginBottom: "16px",
                borderRadius: "9px",
              }}
            >
              <Search size={16} />
            </button>
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
                    borderRadius: "9px",
                    fontSize: "13.5px",
                    fontWeight: isActive ? 600 : 500,
                    color: isActive ? "#FFFFFF" : "var(--text-secondary)",
                    backgroundColor: isActive ? "rgba(99, 102, 241, 0.16)" : "transparent",
                    border: isActive
                      ? "1px solid rgba(99, 102, 241, 0.38)"
                      : "1px solid transparent",
                    boxShadow: isActive ? "0 0 14px -2px rgba(99, 102, 241, 0.25)" : "none",
                    transition: "all 0.18s ease",
                    textDecoration: "none",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <Icon
                      size={18}
                      color={isActive ? "var(--accent-light)" : "var(--text-muted)"}
                      style={{ flexShrink: 0 }}
                    />
                    {!collapsed && <span>{item.name}</span>}
                  </div>

                  {!collapsed && item.badge && (
                    <span
                      style={{
                        fontSize: "10px",
                        fontWeight: 700,
                        padding: "2px 6px",
                        borderRadius: "4px",
                        backgroundColor: isActive ? "rgba(99, 102, 241, 0.3)" : "rgba(255, 255, 255, 0.06)",
                        color: isActive ? "#FFFFFF" : "var(--text-muted)",
                      }}
                    >
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}

            {/* Platform & External Tools */}
            {!collapsed && (
              <div
                style={{
                  fontSize: "10px",
                  color: "var(--text-muted)",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  padding: "16px 8px 6px",
                }}
              >
                Developer
              </div>
            )}

            <button
              onClick={() => setIsSettingsOpen(true)}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: collapsed ? "center" : "flex-start",
                gap: "10px",
                padding: collapsed ? "11px 0" : "9px 12px",
                borderRadius: "9px",
                fontSize: "13px",
                fontWeight: 500,
                color: "var(--text-secondary)",
                background: "transparent",
                border: "none",
                cursor: "pointer",
                width: "100%",
                transition: "all 0.15s ease",
              }}
              title="Platform Settings (⌘,)"
            >
              <Settings size={17} color="var(--text-muted)" />
              {!collapsed && <span>Configuration</span>}
            </button>

            <a
              href="http://localhost:8001/docs"
              target="_blank"
              rel="noopener noreferrer"
              title="FastAPI Interactive Documentation"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: collapsed ? "center" : "space-between",
                padding: collapsed ? "11px 0" : "9px 12px",
                borderRadius: "9px",
                fontSize: "13px",
                fontWeight: 500,
                color: "var(--text-secondary)",
                transition: "all 0.15s ease",
                textDecoration: "none",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Layers size={17} color="var(--text-muted)" />
                {!collapsed && <span>FastAPI Swagger</span>}
              </div>
              {!collapsed && <ExternalLink size={13} color="var(--text-muted)" />}
            </a>

            <a
              href="http://localhost:16686"
              target="_blank"
              rel="noopener noreferrer"
              title="Jaeger Distributed Tracing"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: collapsed ? "center" : "space-between",
                padding: collapsed ? "11px 0" : "9px 12px",
                borderRadius: "9px",
                fontSize: "13px",
                fontWeight: 500,
                color: "var(--text-secondary)",
                transition: "all 0.15s ease",
                textDecoration: "none",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Activity size={17} color="var(--cyan-light)" />
                {!collapsed && <span>Jaeger Traces</span>}
              </div>
              {!collapsed && <ExternalLink size={13} color="var(--text-muted)" />}
            </a>
          </nav>
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
            <div
              title={`${user.email} (${tenantName})`}
              style={{
                padding: collapsed ? "6px" : "10px 12px",
                backgroundColor: "rgba(255, 255, 255, 0.025)",
                borderRadius: "10px",
                border: "1px solid var(--border)",
                display: "flex",
                alignItems: "center",
                gap: "10px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "8px",
                  background: "linear-gradient(135deg, #4F46E5 0%, #06B6D4 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "12px",
                  fontWeight: 700,
                  color: "#FFFFFF",
                  flexShrink: 0,
                }}
              >
                {userInitials}
              </div>

              {!collapsed && (
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div
                    style={{
                      fontSize: "13px",
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
                      marginTop: "2px",
                    }}
                  >
                    <ShieldCheck size={12} color="var(--emerald-light)" />
                    <span
                      style={{
                        fontSize: "11px",
                        color: "var(--accent-light)",
                        fontWeight: 600,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {tenantName}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          <button
            onClick={logoutUser}
            className="btn btn-ghost"
            title="Sign out of current workspace"
            style={{
              width: "100%",
              justifyContent: collapsed ? "center" : "flex-start",
              padding: "7px 10px",
              color: "var(--rose-light)",
              fontSize: "12.5px",
              borderRadius: "8px",
            }}
          >
            <LogOut size={15} color="var(--rose-light)" />
            {!collapsed && <span>Sign Out</span>}
          </button>
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
