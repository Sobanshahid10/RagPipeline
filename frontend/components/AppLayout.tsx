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
          gap: "16px",
          backgroundColor: "var(--bg)",
          color: "var(--accent-light)",
        }}
      >
        <Loader2 size={36} style={{ animation: "spin 1s linear infinite" }} />
        <span style={{ fontSize: "14px", color: "var(--text-secondary)" }}>
          Loading workspace...
        </span>
      </div>
    );
  }

  if (isAuthPage || !token) {
    return <main style={{ width: "100%", minHeight: "100vh" }}>{children}</main>;
  }

  return (
    <div style={{ display: "flex", width: "100vw", height: "100vh", overflow: "hidden" }}>
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
