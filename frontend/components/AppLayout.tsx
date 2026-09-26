"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";
import { useAuth } from "@/context/AuthContext";
import { Sparkles, Loader2 } from "lucide-react";

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
            width: "56px",
            height: "56px",
            borderRadius: "16px",
            background: "var(--accent-gradient)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 0 32px var(--accent-glow)",
          }}
        >
          <Sparkles size={28} color="#FFFFFF" />
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Loader2 size={18} style={{ animation: "spin 1s linear infinite" }} />
          <span style={{ fontSize: "14px", color: "var(--text-secondary)", fontWeight: 500 }}>
            Initializing secure workspace...
          </span>
        </div>
      </div>
    );
  }

  if (isAuthPage || !token) {
    return <main style={{ width: "100%", minHeight: "100vh", position: "relative", zIndex: 1 }}>{children}</main>;
  }

  return (
    <div style={{ display: "flex", width: "100vw", height: "100vh", overflow: "hidden", position: "relative", zIndex: 1 }}>
      <Sidebar />
      <main
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
