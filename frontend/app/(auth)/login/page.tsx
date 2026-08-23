"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { login, register } from "@/lib/api";
import { Sparkles, ArrowRight, Lock, Mail, Building, AlertCircle, Loader2 } from "lucide-react";
import { motion } from "framer-motion";

export default function LoginPage() {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenantName, setTenantName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { loginUser } = useAuth();
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
        // Automatically login after successful registration
        const tokenRes = await login(email, password);
        await loginUser(tokenRes.access_token);
      } else {
        const tokenRes = await login(email, password);
        await loginUser(tokenRes.access_token);
      }
      router.push("/chat");
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "var(--bg)",
        padding: "24px",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Background Ambient Glows */}
      <div
        style={{
          position: "absolute",
          top: "20%",
          left: "30%",
          width: "450px",
          height: "450px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, rgba(10, 10, 15, 0) 70%)",
          filter: "blur(60px)",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: "15%",
          right: "25%",
          width: "400px",
          height: "400px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(167, 139, 250, 0.12) 0%, rgba(10, 10, 15, 0) 70%)",
          filter: "blur(60px)",
          pointerEvents: "none",
        }}
      />

      {/* Main Glass Card */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className="card"
        style={{
          width: "100%",
          maxWidth: "460px",
          padding: "40px 36px",
          backgroundColor: "rgba(19, 19, 26, 0.75)",
          boxShadow: "0 20px 40px -15px rgba(0, 0, 0, 0.7)",
          position: "relative",
          zIndex: 10,
        }}
      >
        {/* Brand Header */}
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              margin: "0 auto 16px",
              borderRadius: "14px",
              background: "var(--accent-gradient)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 24px var(--accent-glow)",
            }}
          >
            <Sparkles size={26} color="#FFFFFF" />
          </div>

          <h1
            className="brand-font"
            style={{ fontSize: "24px", fontWeight: 700, letterSpacing: "-0.02em", marginBottom: "8px" }}
          >
            {isRegister ? "Create Organization" : "Welcome Back"}
          </h1>
          <p style={{ fontSize: "14px", color: "var(--text-secondary)" }}>
            {isRegister
              ? "Set up your multitenant RAG instance in seconds"
              : "Sign in to access your documents and agentic chat"}
          </p>
        </div>

        {/* Tab Switcher */}
        <div
          style={{
            display: "flex",
            backgroundColor: "rgba(255, 255, 255, 0.04)",
            padding: "4px",
            borderRadius: "10px",
            marginBottom: "24px",
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
              color: !isRegister ? "#FFFFFF" : "var(--muted)",
              fontWeight: !isRegister ? 600 : 500,
              fontSize: "13px",
              cursor: "pointer",
              transition: "all 0.2s ease",
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
              color: isRegister ? "#FFFFFF" : "var(--muted)",
              fontWeight: isRegister ? 600 : 500,
              fontSize: "13px",
              cursor: "pointer",
              transition: "all 0.2s ease",
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
              alignItems: "center",
              gap: "10px",
              padding: "12px 14px",
              marginBottom: "20px",
              backgroundColor: "rgba(239, 68, 68, 0.12)",
              border: "1px solid rgba(239, 68, 68, 0.35)",
              borderRadius: "8px",
              color: "#F87171",
              fontSize: "13px",
            }}
          >
            <AlertCircle size={18} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        {/* Form Inputs */}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {isRegister && (
            <div>
              <label
                style={{
                  display: "block",
                  fontSize: "12px",
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
                  size={18}
                  color="var(--muted)"
                  style={{ position: "absolute", left: "14px", top: "14px" }}
                />
                <input
                  type="text"
                  required
                  placeholder="Acme Corp"
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
                fontSize: "12px",
                fontWeight: 600,
                color: "var(--text-secondary)",
                marginBottom: "6px",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              Email Address
            </label>
            <div style={{ position: "relative" }}>
              <Mail
                size={18}
                color="var(--muted)"
                style={{ position: "absolute", left: "14px", top: "14px" }}
              />
              <input
                type="email"
                required
                placeholder="admin@example.com"
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
                fontSize: "12px",
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
                size={18}
                color="var(--muted)"
                style={{ position: "absolute", left: "14px", top: "14px" }}
              />
              <input
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-field"
                style={{ paddingLeft: "42px" }}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="btn btn-primary"
            style={{
              width: "100%",
              padding: "13px",
              marginTop: "8px",
              fontSize: "15px",
            }}
          >
            {isSubmitting ? (
              <>
                <Loader2 size={18} style={{ animation: "spin 1s linear infinite" }} />
                <span>{isRegister ? "Creating Tenant..." : "Signing In..."}</span>
              </>
            ) : (
              <>
                <span>{isRegister ? "Get Started" : "Continue to Chat"}</span>
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        {/* Quick Demo Credentials Helper */}
        <div
          style={{
            marginTop: "24px",
            padding: "12px 14px",
            backgroundColor: "rgba(255, 255, 255, 0.02)",
            border: "1px dashed var(--border)",
            borderRadius: "8px",
            fontSize: "12px",
            color: "var(--muted)",
            textAlign: "center",
          }}
        >
          <span>💡 Need a new account? Switch to &ldquo;Register Tenant&rdquo; above.</span>
        </div>
      </motion.div>
    </div>
  );
}
