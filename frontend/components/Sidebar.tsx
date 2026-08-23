"use client";

import React from "react";
import Link from "next/navigation";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { 
  MessageSquare, 
  FileText, 
  Layers, 
  LogOut, 
  Sparkles, 
  Database,
  ExternalLink
} from "lucide-react";

export const Sidebar: React.FC = () => {
  const pathname = usePathname();
  const { user, logoutUser } = useAuth();

  const navItems = [
    {
      name: "Streaming Chat",
      href: "/chat",
      icon: MessageSquare,
    },
    {
      name: "Document Library",
      href: "/documents",
      icon: FileText,
    },
  ];

  return (
    <aside
      style={{
        width: "var(--sidebar-width)",
        minWidth: "var(--sidebar-width)",
        height: "100vh",
        backgroundColor: "var(--surface)",
        borderRight: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: "24px 16px",
        position: "sticky",
        top: 0,
        zIndex: 40,
      }}
    >
      {/* Brand Header */}
      <div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            padding: "8px 12px",
            marginBottom: "32px",
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
              boxShadow: "0 0 16px var(--accent-glow)",
            }}
          >
            <Sparkles size={20} color="#FFFFFF" />
          </div>
          <div>
            <h1
              className="brand-font"
              style={{
                fontSize: "18px",
                fontWeight: 700,
                letterSpacing: "-0.02em",
                lineHeight: 1.2,
              }}
            >
              Nexus RAG
            </h1>
            <span
              style={{
                fontSize: "11px",
                color: "var(--accent-light)",
                fontWeight: 500,
                letterSpacing: "0.05em",
                textTransform: "uppercase",
              }}
            >
              Agentic Pipeline
            </span>
          </div>
        </div>

        {/* Navigation Section */}
        <nav style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <div
            style={{
              fontSize: "11px",
              color: "var(--muted)",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              padding: "4px 12px 8px",
            }}
          >
            Workspace
          </div>

          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
            return (
              <a
                key={item.href}
                href={item.href}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  padding: "10px 14px",
                  borderRadius: "8px",
                  fontSize: "14px",
                  fontWeight: isActive ? 600 : 500,
                  color: isActive ? "#FFFFFF" : "var(--text-secondary)",
                  backgroundColor: isActive ? "rgba(99, 102, 241, 0.15)" : "transparent",
                  border: isActive
                    ? "1px solid rgba(99, 102, 241, 0.35)"
                    : "1px solid transparent",
                  transition: "all 0.15s ease",
                  cursor: "pointer",
                }}
              >
                <Icon
                  size={18}
                  color={isActive ? "var(--accent-light)" : "var(--muted)"}
                />
                <span>{item.name}</span>
              </a>
            );
          })}

          <div
            style={{
              fontSize: "11px",
              color: "var(--muted)",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              padding: "16px 12px 8px",
            }}
          >
            Platform
          </div>

          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "10px 14px",
              borderRadius: "8px",
              fontSize: "14px",
              fontWeight: 500,
              color: "var(--text-secondary)",
              transition: "all 0.15s ease",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <Layers size={18} color="var(--muted)" />
              <span>FastAPI Docs</span>
            </div>
            <ExternalLink size={14} color="var(--muted)" />
          </a>
        </nav>
      </div>

      {/* User Footer Profile & Logout */}
      <div
        style={{
          borderTop: "1px solid var(--border)",
          paddingTop: "16px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
      >
        {user && (
          <div
            style={{
              padding: "10px 12px",
              backgroundColor: "rgba(255, 255, 255, 0.02)",
              borderRadius: "8px",
              border: "1px solid var(--border)",
            }}
          >
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
                gap: "6px",
                marginTop: "4px",
              }}
            >
              <Database size={12} color="var(--accent-light)" />
              <span
                style={{
                  fontSize: "11px",
                  color: "var(--accent-light)",
                  fontWeight: 500,
                }}
              >
                {user.tenant?.name || "Enterprise"}
              </span>
            </div>
          </div>
        )}

        <button
          onClick={logoutUser}
          className="btn btn-ghost"
          style={{
            width: "100%",
            justifyContent: "flex-start",
            padding: "8px 12px",
            color: "#EF4444",
            fontSize: "13px",
          }}
        >
          <LogOut size={16} color="#EF4444" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
};
