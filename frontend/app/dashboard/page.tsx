"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/context/AuthContext";
import {
  Activity,
  Zap,
  Database,
  Clock,
  TrendingUp,
  ThumbsUp,
  ThumbsDown,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertCircle,
  BarChart3,
  MessageSquare,
  Cpu,
  Server,
  ExternalLink,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Types ──────────────────────────────────────────────────────────────────

interface AdminStats {
  total_queries_24h: number;
  avg_ttft_ms: number;
  p50_ttft_ms: number;
  p95_ttft_ms: number;
  p99_ttft_ms: number;
  cache_hit_rate: number;
  total_tokens_today: number;
  thumbs_up_rate: number;
  route_breakdown: {
    MULTI_HOP_GRAPH: number;
    FACTUAL_VECTOR: number;
    ANALYTICAL_SQL: number;
    GREETING_DIRECT: number;
  };
}

interface RecentQuery {
  id: string;
  raw_query: string;
  route_used: string;
  ttft_ms: number | null;
  total_latency_ms: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  user_feedback: number;
  created_at: string | null;
}

interface ServiceHealth {
  status: string;
  error?: string;
  active_workers?: number;
}

interface SystemHealth {
  overall: string;
  services: {
    postgres: ServiceHealth;
    redis: ServiceHealth;
    celery: ServiceHealth;
  };
}

// ── Small utility components ───────────────────────────────────────────────

const HealthBadge: React.FC<{ status: string; label: string; icon: React.ReactNode }> = ({
  status,
  label,
  icon,
}) => {
  const healthy = status === "healthy" || status === "no_workers";
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "10px",
        padding: "14px 18px",
        borderRadius: "10px",
        background: healthy ? "rgba(16,185,129,0.08)" : "rgba(239,68,68,0.08)",
        border: `1px solid ${healthy ? "rgba(16,185,129,0.25)" : "rgba(239,68,68,0.25)"}`,
        flex: "1 1 140px",
        minWidth: "140px",
      }}
    >
      <div style={{ color: healthy ? "#10B981" : "#EF4444" }}>{icon}</div>
      <div>
        <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text)" }}>{label}</div>
        <div
          style={{
            fontSize: "11px",
            color: healthy ? "#34D399" : "#F87171",
            fontWeight: 500,
            marginTop: "2px",
            textTransform: "capitalize",
          }}
        >
          {status}
        </div>
      </div>
      {healthy ? (
        <CheckCircle2 size={16} color="#10B981" style={{ marginLeft: "auto" }} />
      ) : (
        <XCircle size={16} color="#EF4444" style={{ marginLeft: "auto" }} />
      )}
    </div>
  );
};

const StatCard: React.FC<{
  title: string;
  value: string | number;
  sub?: string;
  icon: React.ReactNode;
  accent?: string;
  glow?: string;
}> = ({ title, value, sub, icon, accent = "#6366F1", glow = "rgba(99,102,241,0.15)" }) => (
  <div
    className="card"
    style={{
      padding: "22px 24px",
      display: "flex",
      flexDirection: "column",
      gap: "12px",
      flex: "1 1 180px",
      minWidth: "180px",
      position: "relative",
      overflow: "hidden",
    }}
  >
    <div
      style={{
        position: "absolute",
        top: "-20px",
        right: "-20px",
        width: "80px",
        height: "80px",
        borderRadius: "50%",
        background: glow,
        filter: "blur(20px)",
        pointerEvents: "none",
      }}
    />
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <span style={{ fontSize: "12px", color: "var(--muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
        {title}
      </span>
      <div
        style={{
          width: "34px",
          height: "34px",
          borderRadius: "8px",
          background: `${accent}22`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: accent,
        }}
      >
        {icon}
      </div>
    </div>
    <div>
      <div style={{ fontSize: "28px", fontWeight: 700, color: "#fff", fontFamily: "'Outfit', sans-serif", lineHeight: 1 }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: "12px", color: "var(--muted)", marginTop: "6px" }}>{sub}</div>
      )}
    </div>
  </div>
);

// Inline bar chart (no external lib)
const LatencyBar: React.FC<{ label: string; value: number; max: number; color: string }> = ({
  label,
  value,
  max,
  color,
}) => {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px" }}>
        <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>{label}</span>
        <span style={{ color: "#fff", fontWeight: 600 }}>{value.toLocaleString()} ms</span>
      </div>
      <div style={{ height: "6px", borderRadius: "4px", background: "rgba(255,255,255,0.06)", overflow: "hidden" }}>
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            borderRadius: "4px",
            background: color,
            transition: "width 0.6s cubic-bezier(0.4, 0, 0.2, 1)",
          }}
        />
      </div>
    </div>
  );
};

const routeColors: Record<string, string> = {
  FACTUAL_VECTOR: "#6366F1",
  MULTI_HOP_GRAPH: "#A78BFA",
  ANALYTICAL_SQL: "#F59E0B",
  GREETING_DIRECT: "#10B981",
  CACHE: "#34D399",
  cache: "#34D399",
};

const routeLabel: Record<string, string> = {
  FACTUAL_VECTOR: "Vector",
  MULTI_HOP_GRAPH: "GraphRAG",
  ANALYTICAL_SQL: "SQL",
  GREETING_DIRECT: "Direct",
  CACHE: "Cache",
  cache: "Cache",
};

// ── Main Page ──────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { token } = useAuth();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [recentQueries, setRecentQueries] = useState<RecentQuery[]>([]);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchAll = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [statsRes, queriesRes, healthRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/admin/stats`, { headers }),
        fetch(`${API_BASE}/api/v1/admin/recent_queries?limit=10`, { headers }),
        fetch(`${API_BASE}/api/v1/admin/health`),
      ]);
      if (statsRes.ok) setStats(await statsRes.json());
      if (queriesRes.ok) setRecentQueries(await queriesRes.json());
      if (healthRes.ok) setHealth(await healthRes.json());
      setLastRefresh(new Date());
    } catch (e) {
      console.error("Failed to fetch dashboard data:", e);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchAll();
    const id = setInterval(fetchAll, 30_000); // Poll every 30 s
    return () => clearInterval(id);
  }, [fetchAll]);

  const maxLatency = stats ? Math.max(stats.p50_ttft_ms, stats.p95_ttft_ms, stats.p99_ttft_ms, 1) : 1;
  const totalRouteQueries = stats
    ? Object.values(stats.route_breakdown).reduce((a, b) => a + b, 0)
    : 0;

  return (
    <div style={{ padding: "32px 36px", maxWidth: "1280px", margin: "0 auto" }}>
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "32px" }}>
        <div>
          <h1
            className="brand-font"
            style={{ fontSize: "26px", fontWeight: 700, letterSpacing: "-0.02em", marginBottom: "4px" }}
          >
            Admin Dashboard
          </h1>
          <p style={{ fontSize: "13px", color: "var(--muted)" }}>
            Live metrics · auto-refresh every 30 s · last updated{" "}
            {lastRefresh.toLocaleTimeString()}
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <a
            href="http://localhost:16686"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "8px 14px",
              borderRadius: "8px",
              background: "rgba(99,102,241,0.12)",
              border: "1px solid rgba(99,102,241,0.3)",
              color: "var(--accent-light)",
              fontSize: "13px",
              fontWeight: 500,
              textDecoration: "none",
              transition: "all 0.2s ease",
            }}
          >
            <Activity size={14} />
            Jaeger Traces
            <ExternalLink size={12} />
          </a>
          <button
            onClick={fetchAll}
            className="btn btn-secondary"
            style={{ gap: "6px", padding: "8px 14px", fontSize: "13px" }}
            disabled={loading}
          >
            <RefreshCw size={14} style={{ animation: loading ? "spin 1s linear infinite" : "none" }} />
            Refresh
          </button>
        </div>
      </div>

      {/* ── System Health ────────────────────────────────────────────────── */}
      <section style={{ marginBottom: "28px" }}>
        <div style={{ fontSize: "11px", color: "var(--muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "12px" }}>
          System Health
        </div>
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          <HealthBadge
            label="PostgreSQL"
            status={health?.services.postgres.status ?? "checking…"}
            icon={<Database size={18} />}
          />
          <HealthBadge
            label="Redis"
            status={health?.services.redis.status ?? "checking…"}
            icon={<Server size={18} />}
          />
          <HealthBadge
            label="Celery"
            status={health?.services.celery.status ?? "checking…"}
            icon={<Cpu size={18} />}
          />
          <HealthBadge
            label="Jaeger"
            status="healthy"
            icon={<Activity size={18} />}
          />
        </div>
      </section>

      {/* ── KPI Cards ────────────────────────────────────────────────────── */}
      <section style={{ marginBottom: "28px" }}>
        <div style={{ fontSize: "11px", color: "var(--muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "12px" }}>
          Last 24 Hours
        </div>
        <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
          <StatCard
            title="Total Queries"
            value={stats?.total_queries_24h.toLocaleString() ?? "—"}
            sub="queries in the last 24 h"
            icon={<MessageSquare size={16} />}
            accent="#6366F1"
            glow="rgba(99,102,241,0.15)"
          />
          <StatCard
            title="Avg TTFT"
            value={stats ? `${stats.avg_ttft_ms} ms` : "—"}
            sub="time-to-first-token"
            icon={<Clock size={16} />}
            accent="#A78BFA"
            glow="rgba(167,139,250,0.15)"
          />
          <StatCard
            title="Cache Hit Rate"
            value={stats ? `${(stats.cache_hit_rate * 100).toFixed(1)}%` : "—"}
            sub="semantic cache effectiveness"
            icon={<Zap size={16} />}
            accent="#10B981"
            glow="rgba(16,185,129,0.15)"
          />
          <StatCard
            title="Tokens Today"
            value={stats ? (stats.total_tokens_today >= 1000 ? `${(stats.total_tokens_today / 1000).toFixed(1)}k` : stats.total_tokens_today) : "—"}
            sub="prompt + completion tokens"
            icon={<TrendingUp size={16} />}
            accent="#F59E0B"
            glow="rgba(245,158,11,0.15)"
          />
          <StatCard
            title="Satisfaction"
            value={stats ? `${(stats.thumbs_up_rate * 100).toFixed(0)}%` : "—"}
            sub="thumbs-up rate"
            icon={<ThumbsUp size={16} />}
            accent="#34D399"
            glow="rgba(52,211,153,0.15)"
          />
        </div>
      </section>

      {/* ── Charts Row ───────────────────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "28px" }}>
        {/* Latency Distribution */}
        <div className="card" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "20px" }}>
            <BarChart3 size={16} color="var(--accent)" />
            <span style={{ fontSize: "14px", fontWeight: 600, color: "#fff" }}>Latency Percentiles (TTFT)</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <LatencyBar
              label="p50 (median)"
              value={stats?.p50_ttft_ms ?? 0}
              max={maxLatency}
              color="#6366F1"
            />
            <LatencyBar
              label="p95"
              value={stats?.p95_ttft_ms ?? 0}
              max={maxLatency}
              color="#A78BFA"
            />
            <LatencyBar
              label="p99"
              value={stats?.p99_ttft_ms ?? 0}
              max={maxLatency}
              color="#EF4444"
            />
          </div>
          <div
            style={{
              marginTop: "20px",
              padding: "10px 14px",
              borderRadius: "8px",
              background: stats && stats.p95_ttft_ms < 500 ? "rgba(16,185,129,0.08)" : "rgba(239,68,68,0.08)",
              border: stats && stats.p95_ttft_ms < 500 ? "1px solid rgba(16,185,129,0.2)" : "1px solid rgba(239,68,68,0.2)",
              fontSize: "12px",
              color: stats && stats.p95_ttft_ms < 500 ? "#34D399" : "#F87171",
              fontWeight: 500,
            }}
          >
            {stats && stats.p95_ttft_ms < 500
              ? "✓ p95 TTFT within 500 ms budget"
              : "⚠ p95 TTFT exceeds 500 ms budget"}
          </div>
        </div>

        {/* Route Distribution */}
        <div className="card" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "20px" }}>
            <Activity size={16} color="var(--accent)" />
            <span style={{ fontSize: "14px", fontWeight: 600, color: "#fff" }}>Route Distribution</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            {stats
              ? Object.entries(stats.route_breakdown).map(([route, count]) => {
                  const pct = totalRouteQueries > 0 ? (count / totalRouteQueries) * 100 : 0;
                  const color = routeColors[route] ?? "#6B6B80";
                  return (
                    <div key={route} style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: color }} />
                          <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>
                            {routeLabel[route] ?? route}
                          </span>
                        </div>
                        <span style={{ color: "#fff", fontWeight: 600 }}>
                          {count} <span style={{ color: "var(--muted)", fontWeight: 400 }}>({pct.toFixed(0)}%)</span>
                        </span>
                      </div>
                      <div style={{ height: "5px", borderRadius: "4px", background: "rgba(255,255,255,0.06)", overflow: "hidden" }}>
                        <div
                          style={{
                            width: `${pct}%`,
                            height: "100%",
                            borderRadius: "4px",
                            background: color,
                            transition: "width 0.6s cubic-bezier(0.4, 0, 0.2, 1)",
                          }}
                        />
                      </div>
                    </div>
                  );
                })
              : (
                <div style={{ color: "var(--muted)", fontSize: "13px" }}>Loading…</div>
              )}
          </div>
        </div>
      </div>

      {/* ── Recent Queries ─────────────────────────────────────────────── */}
      <section>
        <div
          style={{
            fontSize: "11px",
            color: "var(--muted)",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: "12px",
          }}
        >
          Recent Queries
        </div>
        <div className="card" style={{ overflow: "hidden" }}>
          {recentQueries.length === 0 ? (
            <div
              style={{
                padding: "40px",
                textAlign: "center",
                color: "var(--muted)",
                fontSize: "14px",
              }}
            >
              {loading ? "Loading recent queries…" : "No queries yet"}
            </div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr
                  style={{
                    borderBottom: "1px solid var(--border)",
                    background: "rgba(255,255,255,0.02)",
                  }}
                >
                  {["Query", "Route", "TTFT", "Tokens", "Feedback", "Time"].map((h) => (
                    <th
                      key={h}
                      style={{
                        padding: "11px 16px",
                        textAlign: "left",
                        fontSize: "11px",
                        fontWeight: 600,
                        color: "var(--muted)",
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recentQueries.map((q, i) => (
                  <tr
                    key={q.id}
                    style={{
                      borderBottom: i < recentQueries.length - 1 ? "1px solid var(--border)" : "none",
                      transition: "background 0.15s ease",
                    }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.background = "rgba(255,255,255,0.02)")
                    }
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  >
                    {/* Query text */}
                    <td
                      style={{
                        padding: "12px 16px",
                        fontSize: "13px",
                        color: "var(--text)",
                        maxWidth: "320px",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {q.raw_query}
                    </td>

                    {/* Route badge */}
                    <td style={{ padding: "12px 16px", whiteSpace: "nowrap" }}>
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          padding: "3px 8px",
                          borderRadius: "6px",
                          fontSize: "11px",
                          fontWeight: 600,
                          background: `${routeColors[q.route_used] ?? "#6B6B80"}22`,
                          color: routeColors[q.route_used] ?? "#9494A8",
                          border: `1px solid ${routeColors[q.route_used] ?? "#6B6B80"}44`,
                        }}
                      >
                        {routeLabel[q.route_used] ?? q.route_used}
                      </span>
                    </td>

                    {/* TTFT */}
                    <td
                      style={{
                        padding: "12px 16px",
                        fontSize: "13px",
                        color: "var(--text-secondary)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {q.ttft_ms != null ? `${q.ttft_ms} ms` : "—"}
                    </td>

                    {/* Tokens */}
                    <td
                      style={{
                        padding: "12px 16px",
                        fontSize: "13px",
                        color: "var(--text-secondary)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {q.prompt_tokens != null && q.completion_tokens != null
                        ? `${(q.prompt_tokens + q.completion_tokens).toLocaleString()}`
                        : "—"}
                    </td>

                    {/* Feedback */}
                    <td style={{ padding: "12px 16px" }}>
                      {q.user_feedback === 1 ? (
                        <ThumbsUp size={15} color="#10B981" />
                      ) : q.user_feedback === -1 ? (
                        <ThumbsDown size={15} color="#EF4444" />
                      ) : (
                        <span style={{ fontSize: "13px", color: "var(--muted)" }}>—</span>
                      )}
                    </td>

                    {/* Time */}
                    <td
                      style={{
                        padding: "12px 16px",
                        fontSize: "12px",
                        color: "var(--muted)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {q.created_at
                        ? new Date(q.created_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {/* Spinner keyframe */}
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
