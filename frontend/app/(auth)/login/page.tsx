"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { login, register } from "@/lib/api";
import { 
  Sparkles, 
  ArrowRight, 
  Lock, 
  Mail, 
  Building, 
  AlertCircle, 
  Loader2, 
  ShieldCheck, 
  Zap, 
  Database, 
  Cpu, 
  Eye, 
  EyeOff,
  CheckCircle2
} from "lucide-react";
import { motion } from "framer-motion";

export default function LoginPage() {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenantName, setTenantName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { loginUser } = useAuth();
  const { showToast } = useToast();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (isRegister) {
        if (!tenantName.trim()) {
          throw new Error("Please enter your organization or tenant name.");
        }
        await register(email, password, tenantName);
        showToast("success", "Tenant created", "Organization registered successfully. Logging in...");
        const tokenRes = await login(email, password);
        await loginUser(tokenRes.access_token);
      } else {
        const tokenRes = await login(email, password);
        await loginUser(tokenRes.access_token);
        showToast("success", "Welcome back", "Authentication verified.");
      }
      router.push("/chat");
    } catch (err: any) {
      // If logging in fails with user not found, give friendly tip
      if (!isRegister && (err.message?.includes("Invalid") || err.message?.includes("credentials") || err.message?.includes("401"))) {
        setError("Invalid credentials. If this is your first time, switch to 'Register Tenant' to create your organization.");
      } else {
        setError(err.message || "An unexpected error occurred. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickDemoFill = () => {
    setEmail("admin@acme.corp");
    setPassword("SecurePassword2026!");
    setTenantName("Acme Corporation");
    showToast("info", "Demo credentials filled", "Ready to sign in or register.");
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "var(--bg)",
        padding: "32px 24px",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Background Ambient Glows */}
      <div
        style={{
          position: "absolute",
          top: "15%",
          left: "20%",
          width: "550px",
          height: "550px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(99, 102, 241, 0.12) 0%, rgba(8, 9, 14, 0) 70%)",
          filter: "blur(80px)",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: "10%",
          right: "20%",
          width: "500px",
          height: "500px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(139, 92, 246, 0.1) 0%, rgba(8, 9, 14, 0) 70%)",
          filter: "blur(80px)",
          pointerEvents: "none",
        }}
      />

      {/* Main Dual-Card Container */}
      <div
        style={{
          width: "100%",
          maxWidth: "1020px",
          display: "grid",
          gridTemplateColumns: "1.1fr 1fr",
          gap: "32px",
          alignItems: "center",
          position: "relative",
          zIndex: 10,
        }}
      >
        {/* Left Presentation & Architecture Showcase */}
        <motion.div
          initial={{ opacity: 0, x: -24 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
          style={{
            padding: "20px 24px",
            display: "flex",
            flexDirection: "column",
            gap: "24px",
          }}
        >
          {/* Brand Heading */}
          <div>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "6px 14px",
                borderRadius: "20px",
                backgroundColor: "rgba(99, 102, 241, 0.12)",
                border: "1px solid rgba(99, 102, 241, 0.3)",
                color: "var(--accent-light)",
                fontSize: "12px",
                fontWeight: 600,
                letterSpacing: "0.04em",
                marginBottom: "16px",
              }}
            >
              <Sparkles size={14} />
              <span>Next-Gen Enterprise RAG Platform</span>
            </div>

            <h1
              className="brand-font"
              style={{
                fontSize: "36px",
                fontWeight: 800,
                letterSpacing: "-0.03em",
                lineHeight: 1.15,
                marginBottom: "14px",
              }}
            >
              Layout-Aware Intelligence with Verifiable Citations
            </h1>

            <p style={{ fontSize: "15px", color: "var(--text-secondary)", lineHeight: 1.6 }}>
              Production multi-tenant RAG combining PostgreSQL pgvector, recursive CTE GraphRAG, 
              and sub-second SSE streaming with real-time bounding box inspection.
            </p>
          </div>

          {/* Core Architecture Feature Badges */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div
              className="card"
              style={{
                padding: "16px",
                backgroundColor: "rgba(18, 20, 31, 0.5)",
                display: "flex",
                flexDirection: "column",
                gap: "6px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--accent-light)" }}>
                <ShieldCheck size={18} />
                <span style={{ fontSize: "13px", fontWeight: 700, color: "#FFFFFF" }}>Strict RLS Isolation</span>
              </div>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Cryptographic JWT tenant RLS enforced at PostgreSQL session level.
              </span>
            </div>

            <div
              className="card"
              style={{
                padding: "16px",
                backgroundColor: "rgba(18, 20, 31, 0.5)",
                display: "flex",
                flexDirection: "column",
                gap: "6px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--cyan-light)" }}>
                <Database size={18} />
                <span style={{ fontSize: "13px", fontWeight: 700, color: "#FFFFFF" }}>Tri-Hybrid Fusion</span>
              </div>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                HNSW cosine similarity + BM25 tsvector + GraphRAG CTE traversal.
              </span>
            </div>

            <div
              className="card"
              style={{
                padding: "16px",
                backgroundColor: "rgba(18, 20, 31, 0.5)",
                display: "flex",
                flexDirection: "column",
                gap: "6px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--emerald-light)" }}>
                <Zap size={18} />
                <span style={{ fontSize: "13px", fontWeight: 700, color: "#FFFFFF" }}>Sub-second TTFT</span>
              </div>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Parallel retrieval with Redis semantic cache (&lt;15ms hits).
              </span>
            </div>

            <div
              className="card"
              style={{
                padding: "16px",
                backgroundColor: "rgba(18, 20, 31, 0.5)",
                display: "flex",
                flexDirection: "column",
                gap: "6px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#F59E0B" }}>
                <Cpu size={18} />
                <span style={{ fontSize: "13px", fontWeight: 700, color: "#FFFFFF" }}>Vision Grounding</span>
              </div>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Direct jump-to-page citation highlighting in original PDF view.
              </span>
            </div>
          </div>
        </motion.div>

        {/* Right Form Glass Card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 16 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="glass-panel"
          style={{
            padding: "36px 32px",
            borderRadius: "18px",
            boxShadow: "0 24px 60px -12px rgba(0, 0, 0, 0.75), 0 0 24px -2px var(--accent-glow)",
          }}
        >
          {/* Header */}
          <div style={{ marginBottom: "26px" }}>
            <h2
              className="brand-font"
              style={{ fontSize: "22px", fontWeight: 700, letterSpacing: "-0.02em", marginBottom: "6px" }}
            >
              {isRegister ? "Register Organization" : "Sign In to Workspace"}
            </h2>
            <p style={{ fontSize: "13.5px", color: "var(--text-secondary)" }}>
              {isRegister
                ? "Create a dedicated multitenant partition in seconds"
                : "Enter your tenant credentials to continue"}
            </p>
          </div>

          {/* Tab Switcher */}
          <div
            style={{
              display: "flex",
              backgroundColor: "rgba(255, 255, 255, 0.04)",
              padding: "4px",
              borderRadius: "10px",
              marginBottom: "22px",
              border: "1px solid var(--border)",
            }}
          >
            <button
              type="button"
              onClick={() => {
                setIsRegister(false);
                setError(null);
              }}
              style={{
                flex: 1,
                padding: "8px 12px",
                borderRadius: "7px",
                border: "none",
                backgroundColor: !isRegister ? "var(--surface-hover)" : "transparent",
                color: !isRegister ? "#FFFFFF" : "var(--text-muted)",
                fontWeight: !isRegister ? 600 : 500,
                fontSize: "13px",
                cursor: "pointer",
                transition: "all 0.18s ease",
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setIsRegister(true);
                setError(null);
              }}
              style={{
                flex: 1,
                padding: "8px 12px",
                borderRadius: "7px",
                border: "none",
                backgroundColor: isRegister ? "var(--surface-hover)" : "transparent",
                color: isRegister ? "#FFFFFF" : "var(--text-muted)",
                fontWeight: isRegister ? 600 : 500,
                fontSize: "13px",
                cursor: "pointer",
                transition: "all 0.18s ease",
              }}
            >
              Register Tenant
            </button>
          </div>

          {/* Error Alert */}
          {error && (
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "10px",
                padding: "12px 14px",
                marginBottom: "20px",
                backgroundColor: "rgba(244, 63, 94, 0.12)",
                border: "1px solid rgba(244, 63, 94, 0.35)",
                borderRadius: "9px",
                color: "#FB7185",
                fontSize: "13px",
                lineHeight: 1.45,
              }}
            >
              <AlertCircle size={17} style={{ flexShrink: 0, marginTop: "2px" }} />
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {isRegister && (
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "11.5px",
                    fontWeight: 600,
                    color: "var(--text-secondary)",
                    marginBottom: "6px",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                  }}
                >
                  Tenant / Organization Name
                </label>
                <div style={{ position: "relative" }}>
                  <Building
                    size={17}
                    color="var(--text-muted)"
                    style={{ position: "absolute", left: "14px", top: "14px" }}
                  />
                  <input
                    type="text"
                    required
                    placeholder="Acme Corporation"
                    value={tenantName}
                    onChange={(e) => setTenantName(e.target.value)}
                    className="input-field"
                    style={{ paddingLeft: "42px" }}
                  />
                </div>
              </div>
            )}

            <div>
              <label
                style={{
                  display: "block",
                  fontSize: "11.5px",
                  fontWeight: 600,
                  color: "var(--text-secondary)",
                  marginBottom: "6px",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Work Email Address
              </label>
              <div style={{ position: "relative" }}>
                <Mail
                  size={17}
                  color="var(--text-muted)"
                  style={{ position: "absolute", left: "14px", top: "14px" }}
                />
                <input
                  type="email"
                  required
                  placeholder="admin@acme.corp"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-field"
                  style={{ paddingLeft: "42px" }}
                />
              </div>
            </div>

            <div>
              <label
                style={{
                  display: "block",
                  fontSize: "11.5px",
                  fontWeight: 600,
                  color: "var(--text-secondary)",
                  marginBottom: "6px",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Password
              </label>
              <div style={{ position: "relative" }}>
                <Lock
                  size={17}
                  color="var(--text-muted)"
                  style={{ position: "absolute", left: "14px", top: "14px" }}
                />
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field"
                  style={{ paddingLeft: "42px", paddingRight: "42px" }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: "absolute",
                    right: "14px",
                    top: "14px",
                    background: "transparent",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                  }}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="btn btn-primary"
              style={{
                width: "100%",
                padding: "13px",
                marginTop: "6px",
                fontSize: "14.5px",
              }}
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={18} style={{ animation: "spin 1s linear infinite" }} />
                  <span>{isRegister ? "Provisioning Tenant..." : "Signing In..."}</span>
                </>
              ) : (
                <>
                  <span>{isRegister ? "Create Organization" : "Sign In to Console"}</span>
                  <ArrowRight size={17} />
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Credentials Assistant */}
          <div
            style={{
              marginTop: "20px",
              padding: "12px",
              backgroundColor: "rgba(255, 255, 255, 0.025)",
              border: "1px dashed var(--border)",
              borderRadius: "10px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "10px",
            }}
          >
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              <span>Need test credentials?</span>
            </div>
            <button
              type="button"
              onClick={handleQuickDemoFill}
              className="btn btn-secondary"
              style={{
                padding: "5px 10px",
                fontSize: "11.5px",
                borderRadius: "6px",
              }}
            >
              <Sparkles size={12} color="var(--accent-light)" />
              <span>Fill Demo Admin</span>
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
