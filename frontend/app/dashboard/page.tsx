"use client";

import React, { useState, useEffect, useCallback } from "react";
import { API_BASE } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
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
  ShieldCheck,
  Search,
  X
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

// API origin is shared with authenticated document and chat requests.
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
    CACHE?: number;
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

const routeColors: Record<string, string> = {
  FACTUAL_VECTOR: "var(--foreground)",
  MULTI_HOP_GRAPH: "var(--text-secondary)",
  ANALYTICAL_SQL: "#F59E0B",
  GREETING_DIRECT: "#10B981",
  CACHE: "#06B6D4",
  cache: "#06B6D4",
};

const routeLabel: Record<string, string> = {
  HYBRID: "Hybrid retrieval",
  FACTUAL_VECTOR: "Legacy vector route",
  MULTI_HOP_GRAPH: "GraphRAG Traversal",
  ANALYTICAL_SQL: "Analytical SQL",
  GREETING_DIRECT: "Greeting",
  CACHE: "Semantic Cache",
  cache: "Semantic Cache",
};

// ── Component ──────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { token } = useAuth();
  const { showToast } = useToast();

  const [stats, setStats] = useState<AdminStats | null>(null);
  const [recentQueries, setRecentQueries] = useState<RecentQuery[]>([]);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [refreshInterval, setRefreshInterval] = useState<number>(30); // in seconds, 0 = paused
  const [querySearch, setQuerySearch] = useState("");
  const [inspectQuery, setInspectQuery] = useState<RecentQuery | null>(null);

  const fetchAll = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [statsRes, queriesRes, healthRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/admin/stats`, { headers }),
        fetch(`${API_BASE}/api/v1/admin/recent_queries?limit=25`, { headers }),
        fetch(`${API_BASE}/api/v1/admin/health`, { headers }),
      ]);
      if (!statsRes.ok || !queriesRes.ok || !healthRes.ok) throw new Error("Dashboard unavailable or administrator access required");
      if (statsRes.ok) setStats(await statsRes.json());
      if (queriesRes.ok) setRecentQueries(await queriesRes.json());
      if (healthRes.ok) setHealth(await healthRes.json());
      setLastRefresh(new Date());
    } catch (e) {
      showToast("error", "Dashboard unavailable", e instanceof Error ? e.message : "Please retry");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // Polling interval
  useEffect(() => {
    if (refreshInterval <= 0) return;
    const id = setInterval(fetchAll, refreshInterval * 1000);
    return () => clearInterval(id);
  }, [fetchAll, refreshInterval]);

  const maxLatency = stats ? Math.max(stats.p50_ttft_ms, stats.p95_ttft_ms, stats.p99_ttft_ms, 1) : 1;
  const totalRouteQueries = stats
    ? Object.values(stats.route_breakdown).reduce((a, b) => a + b, 0)
    : 0;

  const filteredQueries = recentQueries.filter((q) =>
    q.raw_query.toLowerCase().includes(querySearch.toLowerCase())
  );

  return (
    <div style={{ padding: "36px 44px", maxWidth: "1340px", margin: "0 auto" }}>
      {/* ── Top Header ───────────────────────────────────────────── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "32px",
          flexWrap: "wrap",
          gap: "16px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
            <h1
              className="brand-font"
              style={{ fontSize: "28px", fontWeight: 800, letterSpacing: "-0.025em" }}
            >
              System & Telemetry Dashboard
            </h1>
            <span className="badge badge-accent">Live Observability</span>
          </div>
          <p style={{ fontSize: "14px", color: "var(--text-secondary)" }}>
            Real-time latency SLA monitoring, service availability and query analytics.
          </p>
        </div>

        {/* Action Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          {/* Refresh Interval Selector */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              background: "rgba(255, 255, 255, 0.04)",
              padding: "4px 8px",
              borderRadius: "8px",
              border: "1px solid var(--border)",
              fontSize: "12px",
            }}
          >
            <Clock size={13} color="var(--text-muted)" />
            <span style={{ color: "var(--text-muted)" }}>Poll:</span>
            {[10, 30, 0].map((sec) => (
              <button
                key={sec}
                onClick={() => setRefreshInterval(sec)}
                style={{
                  background: refreshInterval === sec ? "var(--surface-hover)" : "transparent",
                  border: "none",
                  borderRadius: "5px",
                  padding: "3px 7px",
                  color: refreshInterval === sec ? "#FFFFFF" : "var(--text-muted)",
                  fontSize: "11.5px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {sec === 0 ? "Pause" : `${sec}s`}
              </button>
            ))}
          </div>

          <a
            href="http://localhost:16686"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary"
            style={{ padding: "8px 14px", fontSize: "13px", textDecoration: "none" }}
          >
            <Activity size={14} color="var(--cyan-light)" />
            <span>Jaeger UI</span>
            <ExternalLink size={12} color="var(--text-muted)" />
          </a>

          <button
            onClick={() => {
              fetchAll();
              showToast("info", "Refreshed metrics");
            }}
            className="btn btn-secondary"
            style={{ padding: "8px 14px", fontSize: "13px" }}
            disabled={loading}
          >
            <RefreshCw size={14} style={{ animation: loading ? "spin 1s linear infinite" : "none" }} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* ── System Health Grid ───────────────────────────────────── */}
      <section style={{ marginBottom: "28px" }}>
        <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "12px" }}>
          Infrastructure Services
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px" }}>
          {/* Postgres */}
          <div
            className="card"
            style={{
              padding: "16px 18px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              border: `1px solid ${health?.services.postgres.status === "healthy" ? "rgba(16, 185, 129, 0.3)" : "rgba(244, 63, 94, 0.3)"}`,
              backgroundColor: health?.services.postgres.status === "healthy" ? "rgba(16, 185, 129, 0.05)" : "rgba(244, 63, 94, 0.05)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <div style={{ color: "#10B981" }}><Database size={20} /></div>
              <div>
                <div style={{ fontSize: "13.5px", fontWeight: 700, color: "#FFFFFF" }}>PostgreSQL 16</div>
                <div style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>pgvector + Recursive CTEs</div>
              </div>
            </div>
            <span className="badge badge-success">Healthy</span>
          </div>

          {/* Redis */}
          <div
            className="card"
            style={{
              padding: "16px 18px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              border: `1px solid ${health?.services.redis.status === "healthy" ? "rgba(16, 185, 129, 0.3)" : "rgba(244, 63, 94, 0.3)"}`,
              backgroundColor: health?.services.redis.status === "healthy" ? "rgba(16, 185, 129, 0.05)" : "rgba(244, 63, 94, 0.05)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <div style={{ color: "var(--cyan-light)" }}><Server size={20} /></div>
              <div>
                <div style={{ fontSize: "13.5px", fontWeight: 700, color: "#FFFFFF" }}>Redis 7</div>
                <div style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>Semantic Cache & Queue</div>
              </div>
            </div>
            <span className="badge badge-success">Healthy</span>
          </div>

          {/* Celery */}
          <div
            className="card"
            style={{
              padding: "16px 18px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              border: "1px solid rgba(16, 185, 129, 0.3)",
              backgroundColor: "rgba(16, 185, 129, 0.05)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <div style={{ color: "var(--accent-light)" }}><Cpu size={20} /></div>
              <div>
                <div style={{ fontSize: "13.5px", fontWeight: 700, color: "#FFFFFF" }}>Celery Worker</div>
                <div style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>Background Layout Parser</div>
              </div>
            </div>
            <span className="badge badge-success">Active</span>
          </div>

          {/* Jaeger */}
          <div
            className="card"
            style={{
              padding: "16px 18px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              border: "1px solid rgba(16, 185, 129, 0.3)",
              backgroundColor: "rgba(16, 185, 129, 0.05)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <div style={{ color: "var(--accent-light)" }}><Activity size={20} /></div>
              <div>
                <div style={{ fontSize: "13.5px", fontWeight: 700, color: "#FFFFFF" }}>Jaeger Tracing</div>
                <div style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>OTel Distributed Telemetry</div>
              </div>
            </div>
            <span className="badge badge-success">Connected</span>
          </div>
        </div>
      </section>

      {/* ── KPI Metrics Cards ─────────────────────────────────────── */}
      <section style={{ marginBottom: "28px" }}>
        <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "12px" }}>
          Production Performance Metrics (24 Hours)
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: "16px" }}>
          {/* Total Queries */}
          <div className="card" style={{ padding: "22px 24px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Queries Processed
              </span>
              <MessageSquare size={18} color="var(--accent-light)" />
            </div>
            <div style={{ fontSize: "30px", fontWeight: 800, color: "#FFFFFF", fontFamily: "'Outfit', sans-serif" }}>
              {stats?.total_queries_24h.toLocaleString() ?? "—"}
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
              last 24 hours traffic
            </div>
          </div>

          {/* Avg TTFT */}
          <div className="card" style={{ padding: "22px 24px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Avg TTFT
              </span>
              <Clock size={18} color="var(--cyan-light)" />
            </div>
            <div style={{ fontSize: "30px", fontWeight: 800, color: "#FFFFFF", fontFamily: "'Outfit', sans-serif" }}>
              {stats ? `${stats.avg_ttft_ms} ms` : "—"}
            </div>
            <div style={{ fontSize: "12px", color: "var(--emerald-light)", marginTop: "4px" }}>
              time-to-first-token stream
            </div>
          </div>

          {/* Cache Hit Rate */}
          <div className="card" style={{ padding: "22px 24px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Semantic Cache Rate
              </span>
              <Zap size={18} color="#10B981" />
            </div>
            <div style={{ fontSize: "30px", fontWeight: 800, color: "#FFFFFF", fontFamily: "'Outfit', sans-serif" }}>
              {stats ? `${(stats.cache_hit_rate * 100).toFixed(1)}%` : "—"}
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
              &lt;15ms sub-second cache hits
            </div>
          </div>

          {/* Tokens Today */}
          <div className="card" style={{ padding: "22px 24px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Tokens Consumed
              </span>
              <TrendingUp size={18} color="#F59E0B" />
            </div>
            <div style={{ fontSize: "30px", fontWeight: 800, color: "#FFFFFF", fontFamily: "'Outfit', sans-serif" }}>
              {stats
                ? stats.total_tokens_today >= 1000
                  ? `${(stats.total_tokens_today / 1000).toFixed(1)}k`
                  : stats.total_tokens_today
                : "—"}
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
              prompt + completion
            </div>
          </div>

          {/* Satisfaction */}
          <div className="card" style={{ padding: "22px 24px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                User Satisfaction
              </span>
              <ThumbsUp size={18} color="var(--emerald-light)" />
            </div>
            <div style={{ fontSize: "30px", fontWeight: 800, color: "#FFFFFF", fontFamily: "'Outfit', sans-serif" }}>
              {stats ? `${(stats.thumbs_up_rate * 100).toFixed(0)}%` : "—"}
            </div>
            <div style={{ fontSize: "12px", color: "var(--emerald-light)", marginTop: "4px" }}>
              positive feedback ratio
            </div>
          </div>
        </div>
      </section>

      {/* ── Charts Row (Latency Percentiles & Route Breakdown) ──────── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "28px" }}>
        {/* Latency Distribution */}
        <div className="card" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <BarChart3 size={17} color="var(--accent-light)" />
              <span style={{ fontSize: "15px", fontWeight: 700, color: "#FFFFFF" }}>
                Latency Percentiles (TTFT)
              </span>
            </div>
            <span className="badge badge-accent">SLA Target &lt;500ms</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
            {/* p50 */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", marginBottom: "6px" }}>
                <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>p50 (Median)</span>
                <span style={{ color: "#FFFFFF", fontWeight: 700 }}>{stats?.p50_ttft_ms ?? 0} ms</span>
              </div>
              <div style={{ height: "7px", borderRadius: "5px", background: "rgba(255, 255, 255, 0.06)", overflow: "hidden" }}>
                <div
                  style={{
                    width: `${Math.min(((stats?.p50_ttft_ms ?? 0) / maxLatency) * 100, 100)}%`,
                    height: "100%",
                    borderRadius: "5px",
                    background: "var(--accent)",
                    transition: "width 0.6s ease",
                  }}
                />
              </div>
            </div>

            {/* p95 */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", marginBottom: "6px" }}>
                <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>p95 Percentile</span>
                <span style={{ color: "#FFFFFF", fontWeight: 700 }}>{stats?.p95_ttft_ms ?? 0} ms</span>
              </div>
              <div style={{ height: "7px", borderRadius: "5px", background: "rgba(255, 255, 255, 0.06)", overflow: "hidden" }}>
                <div
                  style={{
                    width: `${Math.min(((stats?.p95_ttft_ms ?? 0) / maxLatency) * 100, 100)}%`,
                    height: "100%",
                    borderRadius: "5px",
                    background: "var(--text-secondary)",
                    transition: "width 0.6s ease",
                  }}
                />
              </div>
            </div>

            {/* p99 */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", marginBottom: "6px" }}>
                <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>p99 Percentile</span>
                <span style={{ color: "#FFFFFF", fontWeight: 700 }}>{stats?.p99_ttft_ms ?? 0} ms</span>
              </div>
              <div style={{ height: "7px", borderRadius: "5px", background: "rgba(255, 255, 255, 0.06)", overflow: "hidden" }}>
                <div
                  style={{
                    width: `${Math.min(((stats?.p99_ttft_ms ?? 0) / maxLatency) * 100, 100)}%`,
                    height: "100%",
                    borderRadius: "5px",
                    background: "#F43F5E",
                    transition: "width 0.6s ease",
                  }}
                />
              </div>
            </div>
          </div>

          <div
            style={{
              marginTop: "22px",
              padding: "10px 14px",
              borderRadius: "8px",
              background: stats && stats.p95_ttft_ms < 500 ? "rgba(16, 185, 129, 0.08)" : "rgba(244, 63, 94, 0.08)",
              border: stats && stats.p95_ttft_ms < 500 ? "1px solid rgba(16, 185, 129, 0.25)" : "1px solid rgba(244, 63, 94, 0.25)",
              fontSize: "12px",
              color: stats && stats.p95_ttft_ms < 500 ? "#34D399" : "#FB7185",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              fontWeight: 600,
            }}
          >
            {stats && stats.p95_ttft_ms < 500 ? (
              <>
                <CheckCircle2 size={15} />
                <span>p95 TTFT complies with strict sub-500ms SLA</span>
              </>
            ) : (
              <>
                <AlertCircle size={15} />
                <span>p95 TTFT exceeds 500ms budget - inspect slow database locks</span>
              </>
            )}
          </div>
        </div>

        {/* Route Distribution */}
        <div className="card" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Zap size={17} color="var(--cyan-light)" />
              <span style={{ fontSize: "15px", fontWeight: 700, color: "#FFFFFF" }}>
                Agentic Route Distribution
              </span>
            </div>
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              {totalRouteQueries} total routes
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {stats ? (
              Object.entries(stats.route_breakdown).map(([route, count]) => {
                const pct = totalRouteQueries > 0 ? (count / totalRouteQueries) * 100 : 0;
                const color = routeColors[route] ?? "#64687C";
                return (
                  <div key={route}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", marginBottom: "6px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: color }} />
                        <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>
                          {routeLabel[route] ?? route}
                        </span>
                      </div>
                      <span style={{ color: "#FFFFFF", fontWeight: 700 }}>
                        {count} <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>({pct.toFixed(0)}%)</span>
                      </span>
                    </div>
                    <div style={{ height: "6px", borderRadius: "5px", background: "rgba(255, 255, 255, 0.06)", overflow: "hidden" }}>
                      <div
                        style={{
                          width: `${pct}%`,
                          height: "100%",
                          borderRadius: "5px",
                          background: color,
                          transition: "width 0.6s ease",
                        }}
                      />
                    </div>
                  </div>
                );
              })
            ) : (
              <div style={{ color: "var(--text-muted)", fontSize: "13px" }}>Loading routes...</div>
            )}
          </div>
        </div>
      </div>

      {/* ── Recent Queries Log Table ──────────────────────────────── */}
      <section>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "16px",
            flexWrap: "wrap",
            gap: "10px",
          }}
        >
          <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Recent Queries Stream ({recentQueries.length})
          </div>

          <div style={{ position: "relative", width: "260px" }}>
            <Search
              size={14}
              color="var(--text-muted)"
              style={{ position: "absolute", left: "10px", top: "10px" }}
            />
            <input
              type="text"
              placeholder="Filter recent queries..."
              value={querySearch}
              onChange={(e) => setQuerySearch(e.target.value)}
              className="input-field"
              style={{ paddingLeft: "32px", height: "34px", fontSize: "12.5px" }}
            />
          </div>
        </div>

        <div className="card" style={{ overflow: "hidden" }}>
          {filteredQueries.length === 0 ? (
            <div style={{ padding: "48px", textAlign: "center", color: "var(--text-muted)", fontSize: "14px" }}>
              {loading ? "Loading query log..." : "No recent queries found."}
            </div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)", background: "rgba(255, 255, 255, 0.02)" }}>
                  {["Query Intent", "Routing Path", "TTFT", "Total Latency", "Tokens", "User Feedback", "Timestamp"].map((h) => (
                    <th
                      key={h}
                      style={{
                        padding: "12px 18px",
                        textAlign: "left",
                        fontSize: "11px",
                        fontWeight: 700,
                        color: "var(--text-muted)",
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
                {filteredQueries.map((q, i) => (
                  <tr
                    key={q.id || i}
                    onClick={() => setInspectQuery(q)}
                    style={{
                      borderBottom: i < filteredQueries.length - 1 ? "1px solid var(--border)" : "none",
                      transition: "background 0.15s ease",
                      cursor: "pointer",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255, 255, 255, 0.025)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  >
                    {/* Raw Query */}
                    <td
                      style={{
                        padding: "14px 18px",
                        fontSize: "13.5px",
                        color: "#FFFFFF",
                        maxWidth: "340px",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        fontWeight: 500,
                      }}
                    >
                      {q.raw_query}
                    </td>

                    {/* Route Pill */}
                    <td style={{ padding: "14px 18px", whiteSpace: "nowrap" }}>
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          padding: "3px 8px",
                          borderRadius: "5px",
                          fontSize: "11px",
                          fontWeight: 600,
                          background: `${routeColors[q.route_used] ?? "#64687C"}22`,
                          color: routeColors[q.route_used] ?? "#9FA4B8",
                          border: `1px solid ${routeColors[q.route_used] ?? "#64687C"}44`,
                        }}
                      >
                        {routeLabel[q.route_used] ?? q.route_used}
                      </span>
                    </td>

                    {/* TTFT */}
                    <td style={{ padding: "14px 18px", fontSize: "13px", whiteSpace: "nowrap" }}>
                      {q.ttft_ms != null ? (
                        <span style={{ color: q.ttft_ms < 500 ? "var(--emerald-light)" : "#F59E0B" }}>
                          {q.ttft_ms} ms
                        </span>
                      ) : (
                        <span style={{ color: "var(--text-muted)" }}>—</span>
                      )}
                    </td>

                    {/* Total Latency */}
                    <td style={{ padding: "14px 18px", fontSize: "13px", color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
                      {q.total_latency_ms != null ? `${q.total_latency_ms} ms` : "—"}
                    </td>

                    {/* Tokens */}
                    <td style={{ padding: "14px 18px", fontSize: "13px", color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
                      {q.prompt_tokens != null && q.completion_tokens != null
                        ? (q.prompt_tokens + q.completion_tokens).toLocaleString()
                        : "—"}
                    </td>

                    {/* User Feedback */}
                    <td style={{ padding: "14px 18px" }}>
                      {q.user_feedback === 1 ? (
                        <ThumbsUp size={15} color="#10B981" />
                      ) : q.user_feedback === -1 ? (
                        <ThumbsDown size={15} color="#F43F5E" />
                      ) : (
                        <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>—</span>
                      )}
                    </td>

                    {/* Timestamp */}
                    <td style={{ padding: "14px 18px", fontSize: "12px", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                      {q.created_at
                        ? new Date(q.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {/* ── Query Inspector Modal ─────────────────────────────────── */}
      <AnimatePresence>
        {inspectQuery && (
          <div
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: "rgba(0, 0, 0, 0.7)",
              backdropFilter: "blur(8px)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 999,
              padding: "24px",
            }}
            onClick={() => setInspectQuery(null)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="glass-panel"
              style={{
                width: "100%",
                maxWidth: "600px",
                padding: "28px",
                borderRadius: "16px",
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "18px" }}>
                <h3 style={{ fontSize: "17px", fontWeight: 700, color: "#FFFFFF" }}>
                  Query Execution Details
                </h3>
                <button
                  onClick={() => setInspectQuery(null)}
                  className="btn btn-ghost"
                  style={{ padding: "4px" }}
                >
                  <X size={18} />
                </button>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "14px", fontSize: "13.5px" }}>
                <div>
                  <span style={{ color: "var(--text-muted)", fontSize: "12px", display: "block", marginBottom: "4px" }}>
                    RAW QUERY
                  </span>
                  <div style={{ padding: "10px 14px", background: "rgba(255, 255, 255, 0.04)", borderRadius: "8px", color: "#FFFFFF" }}>
                    {inspectQuery.raw_query}
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div>
                    <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>ROUTING STRATEGY</span>
                    <div style={{ fontWeight: 600, color: "var(--accent-light)", marginTop: "2px" }}>
                      {routeLabel[inspectQuery.route_used] ?? inspectQuery.route_used}
                    </div>
                  </div>
                  <div>
                    <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>TIME TO FIRST TOKEN</span>
                    <div style={{ fontWeight: 600, color: "#FFFFFF", marginTop: "2px" }}>
                      {inspectQuery.ttft_ms != null ? `${inspectQuery.ttft_ms} ms` : "—"}
                    </div>
                  </div>
                  <div>
                    <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>TOTAL LATENCY</span>
                    <div style={{ fontWeight: 600, color: "#FFFFFF", marginTop: "2px" }}>
                      {inspectQuery.total_latency_ms != null ? `${inspectQuery.total_latency_ms} ms` : "—"}
                    </div>
                  </div>
                  <div>
                    <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>TOTAL TOKENS</span>
                    <div style={{ fontWeight: 600, color: "#FFFFFF", marginTop: "2px" }}>
                      {inspectQuery.prompt_tokens != null && inspectQuery.completion_tokens != null
                        ? `${inspectQuery.prompt_tokens} prompt + ${inspectQuery.completion_tokens} completion`
                        : "—"}
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
