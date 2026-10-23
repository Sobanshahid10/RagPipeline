"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { login, register } from "@/lib/api";
import {
  ArrowRight,
  Lock,
  Mail,
  Building,
  AlertCircle,
  Loader2,
  ShieldCheck,
  Activity,
  Database,
  Cpu,
  Eye,
  EyeOff,
  CheckCircle2,
  Layers,
  KeyRound
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


  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "var(--bg)",
        padding: "32px 24px",
        position: "relative",
        overflow: "hidden",
      }}
    >
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
            <h1
              className="brand-font"
              style={{
                fontSize: "34px",
                fontWeight: 700,
                letterSpacing: "-0.03em",
                lineHeight: 1.2,
                marginBottom: "14px",
                color: "#FFFFFF",
              }}
            >
              Layout-Aware RAG with Verifiable Citations
            </h1>

            <p style={{ fontSize: "14.5px", color: "var(--text-secondary)", lineHeight: 1.65, maxWidth: "460px" }}>
              Multi-tenant retrieval platform combining PostgreSQL pgvector, recursive GraphRAG traversal, and source passage citations.
            </p>
          </div>

          {/* Technical Specifications */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "14px",
              paddingTop: "14px",
              borderTop: "1px solid var(--border)",
            }}
          >
            <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
              <span style={{ fontSize: "13px", fontWeight: 600, color: "#FFFFFF" }}>Row-Level Security (RLS) Isolation</span>
              <span style={{ fontSize: "12.5px", color: "var(--text-muted)", lineHeight: 1.5 }}>
                Verified accounts select the workspace context used for database access.
              </span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
              <span style={{ fontSize: "13px", fontWeight: 600, color: "#FFFFFF" }}>Tri-Hybrid Retrieval Engine</span>
              <span style={{ fontSize: "12.5px", color: "var(--text-muted)", lineHeight: 1.5 }}>
                HNSW cosine similarity, full-text tsvector search, and recursive knowledge graph traversal fused via rank fusion.
              </span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
              <span style={{ fontSize: "13px", fontWeight: 600, color: "#FFFFFF" }}>Vision Grounding &amp; Provenance</span>
              <span style={{ fontSize: "12.5px", color: "var(--text-muted)", lineHeight: 1.5 }}>
                Inspect source passages and original document pages. Region highlights appear only when reliable coordinates are available.
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
            borderRadius: "8px",
            boxShadow: "0 16px 40px rgba(0, 0, 0, 0.4)",
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
              role="alert"
              aria-live="polite"
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
                  htmlFor="tenant-name"
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
                    id="tenant-name"
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
                htmlFor="work-email"
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
                  id="work-email"
                  type="email"
                  required
                  autoComplete="email"
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
                htmlFor="login-password"
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
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  required
                  autoComplete={isRegister ? "new-password" : "current-password"}
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field"
                  style={{ paddingLeft: "42px", paddingRight: "42px" }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
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

          {/* Contextual Form Privacy & Legal Notice */}
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "14px", textAlign: "center", lineHeight: 1.5 }}>
            By continuing, you agree to our{" "}
            <a href="/terms" style={{ color: "var(--accent-light)", textDecoration: "underline" }}>
              Terms &amp; Conditions
            </a>{" "}
            and acknowledge our{" "}
            <a href="/privacy" style={{ color: "var(--accent-light)", textDecoration: "underline" }}>
              Privacy Policy
            </a>
            . Passwords are salted and hashed using bcrypt.
          </div>

        </motion.div>
      </div>

      {/* Login Screen Legal Footer */}
      <footer
        style={{
          position: "relative",
          zIndex: 10,
          marginTop: "40px",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "center",
          gap: "18px",
          fontSize: "12.5px",
          color: "var(--text-muted)",
        }}
      >
        <span>&copy; {new Date().getFullYear()} Nexus RAG Platform</span>
        <span>&bull;</span>
        <a href="/privacy" style={{ color: "var(--text-secondary)" }}>Privacy Policy</a>
        <span>&bull;</span>
        <a href="/terms" style={{ color: "var(--text-secondary)" }}>Terms &amp; Conditions</a>
        <span>&bull;</span>
        <a href="/cookies" style={{ color: "var(--text-secondary)" }}>Cookie Policy</a>
        <span>&bull;</span>
        <a href="/refund" style={{ color: "var(--text-secondary)" }}>Refund Policy</a>
      </footer>
    </div>
  );
}
