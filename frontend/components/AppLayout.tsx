"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";
import { useAuth } from "@/context/AuthContext";
import { Loader2 } from "lucide-react";

export const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const pathname = usePathname();
  const { isLoading, token } = useAuth();
  const isAuthPage = pathname?.startsWith("/login");

  if (isLoading) {
    return (
      <div
        style={{
          width: "100vw",
          height: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "18px",
          backgroundColor: "var(--bg)",
          color: "var(--accent-light)",
          position: "relative",
          zIndex: 10,
        }}
      >
        <div
          style={{
            width: "44px",
            height: "44px",
            borderRadius: "8px",
            background: "#1E2025",
            border: "1px solid rgba(255, 255, 255, 0.12)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Loader2 size={20} color="#FFFFFF" style={{ animation: "spin 1s linear infinite" }} />
        </div>
        <span style={{ fontSize: "13px", color: "var(--text-muted)", fontWeight: 500 }}>
          Loading workspace...
        </span>
      </div>
    );
  }

  if (isAuthPage || !token) {
    return <main id="main-content" style={{ width: "100%", minHeight: "100vh", position: "relative", zIndex: 1 }}>{children}</main>;
  }

  return (
    <div style={{ display: "flex", width: "100vw", height: "100vh", overflow: "hidden", position: "relative", zIndex: 1 }}>
      <Sidebar />
      <main
        id="main-content"
        style={{
          flex: 1,
          height: "100vh",
          overflowY: "auto",
          backgroundColor: "var(--bg)",
          position: "relative",
        }}
      >
        {children}
      </main>
    </div>
  );
};
