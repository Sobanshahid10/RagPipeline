"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { askPublicBook, PublicBookAnswer } from "@/lib/api";
import { DEFAULT_MODEL, MODEL_OPTIONS } from "@/lib/models";
import { Footer } from "@/components/Footer";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import { ProjectOwnerCard } from "@/components/ProjectOwnerCard";
import { 
  BookOpen, 
  Search, 
  ArrowLeft, 
  Loader2, 
  CheckCircle2, 
  ChevronRight, 
  ExternalLink,
  ShieldCheck,
  FileCode,
  FileText,
  CornerDownRight,
  Database,
  Cpu,
  Layers,
  Sparkles
} from "lucide-react";

interface ChapterDef {
  id: string;
  number: string;
  title: string;
  scope: string;
  keyFacts: string[];
  suggestedQueries: string[];
}

const CHAPTERS: ChapterDef[] = [
  {
    id: "ch-01",
    number: "01",
    title: "People & Identity",
    scope: "Public identities, profile links, verified handles, and shared educational context for Muhammad Soban and Muhammad Umar Farooq.",
    keyFacts: [
      "Muhammad Soban (Muhammad Soban Shahid): Repository owner. AI & Frontend Engineer, UMT BS AI student.",
      "Muhammad Umar Farooq: AI & Autonomous Systems Engineer, Lahore. BS AI student at UMT.",
      "Both Soban and Umar are males (pronouns: he/him/his).",
      "Shared collaborative context on ChiefMind, ClarityHire, DocuStratum, and OS Pilot.",
    ],
    suggestedQueries: [
      "What are the names of the people who created this app?",
      "Who is Muhammad Soban and where does he study?",
      "Who is Muhammad Umar Farooq and what is his verified background?",
    ],
  },
  {
    id: "ch-05",
    number: "02",
    title: "Education & Skills (Soban)",
    scope: "Academic qualifications, Coding Caliber internship, 28 LinkedIn skills, and 20 certifications.",
    keyFacts: [
      "Soban: BS AI at UMT (3.36/4.00 CGPA, October 2023–July 2027).",
      "Automation Engineer intern at Coding Caliber (January–March 2026).",
      "20 certifications across Google ML Crash Course, IBM RAG, Neo4j, Anthropic, and OpenAI.",
    ],
    suggestedQueries: [
      "What are Soban's educational background and CGPA?",
      "What certifications and licenses are listed on Soban's LinkedIn?",
      "What practical work did Soban do at Coding Caliber?",
    ],
  },
  {
    id: "ch-06",
    number: "03",
    title: "Project Atlas (Soban)",
    scope: "10 public repositories including CodeLens, WebRAG Studio, ParallelWeb, and OS Pilot.",
    keyFacts: [
      "CodeLens: AI codebase intelligence with Tree-Sitter parsing across 8+ languages, hybrid retrieval, and line citations.",
      "WebRAG Studio: Local-first Chrome extension with MiniLM embeddings and block-level provenance.",
      "ParallelWeb: Multi-persona web journey testing with SHA-256 evidence chaining.",
    ],
    suggestedQueries: [
      "What is CodeLens and what architecture does it use?",
      "What is Soban's WebRAG Studio and how does it relate to DocuStratum?",
      "What public repositories are on Soban's GitHub?",
    ],
  },
  {
    id: "ch-02",
    number: "04",
    title: "Education & Experience (Umar)",
    scope: "Academic records, CGPA, merit scholarships, Techohub internship, and 5 non-public internship codebases.",
    keyFacts: [
      "Umar: BS AI at UMT (CGPA 3.85/4.0, 70% merit scholarship, Rector's & Dean's awards).",
      "Techohub Internship: Agentic AI Developer Intern (June 2026–present).",
      "Five non-public internship codebases: Docinsight, VidInsight, Aixam, AInsight, Spectra Live Studio.",
    ],
    suggestedQueries: [
      "What are the five non-public internship codebases and what do they do?",
      "What was Umar's role and practical work at Techohub?",
      "What educational milestones and grades are documented for Umar?",
    ],
  },
  {
    id: "ch-03",
    number: "05",
    title: "Project Atlas (Umar)",
    scope: "27 public GitHub repositories, commit chronologies, and verified technical architectures.",
    keyFacts: [
      "Earliest documented repository commits: 6 October 2025 (DSA_CPP, YOLO Vehicle Detection).",
      "Observed authored commits: 634 across reviewed public and internship Git histories.",
      "Key architectures: DocuStratum Studio, Gemma Claim Verification, Personal AI Employee, AutoResearch.",
    ],
    suggestedQueries: [
      "When did Umar start doing projects? What can the dates actually prove?",
      "How many projects has Omer pushed to GitHub?",
      "What is the best part of Omer's portfolio, based on the evidence?",
      "What is the worst part of Omer's portfolio, based on the evidence?",
    ],
  },
  {
    id: "ch-04",
    number: "06",
    title: "Credentials & Models (Umar)",
    scope: "18 portfolio certifications, Hugging Face models, Kaggle profiles, and competition results.",
    keyFacts: [
      "Gemma Claim Verification: 1st place in Gemma Hackathon (94.40% accuracy, 94.38% macro-F1).",
      "Hugging Face models: Gemma evidence verification QLoRA, FireWatch AI, Phi-3 phishing detector.",
      "18 credentials spanning DataCamp, Anthropic Claude, OpenAI Academy, and Kaggle.",
    ],
    suggestedQueries: [
      "What awards and measurable claims are documented for Umar?",
      "What models has Umar published on Hugging Face?",
      "What certifications are recorded in Umar's portfolio?",
    ],
  },
  {
    id: "ch-07",
    number: "07",
    title: "Collaboration Map",
    scope: "Cross-account joint work, corresponding repositories, and verified engineering overlaps.",
    keyFacts: [
      "ChiefMind (Soban) / Personal AI Employee (Umar): Local-first executive assistant.",
      "ClarityHire: AI resume screening with bias auditing and Fairlearn integration.",
      "Soban collaborated on OS Pilot with Umar (project lead), Haseeb, and Abdullah.",
    ],
    suggestedQueries: [
      "What projects did Soban and Umar collaborate on?",
      "What is the relationship between Soban’s ChiefMind and Umar’s Personal AI Employee?",
      "Who were the team members on OS Pilot?",
    ],
  },
  {
    id: "ch-08",
    number: "08",
    title: "Boundary & Abstention Protocol",
    scope: "Strict epistemic boundaries: what the knowledge book can answer vs. what it strictly abstains from.",
    keyFacts: [
      "Strict abstention on private WhatsApp, journals, personal chats, or unindexed code internals.",
      "Every answer must cite verifiable URLs or document IDs.",
      "Conflicts between portfolio and GitHub READMEs resolve in favor of the GitHub README.",
    ],
    suggestedQueries: [
      "What can this knowledge book answer and what can it not answer?",
      "What are the evidence rules between portfolio claims and GitHub READMEs?",
      "Why does the system abstain when asked about private journals or WhatsApp?",
    ],
  },
  {
    id: "ch-09",
    number: "09",
    title: "Source Catalog & Provenance",
    scope: "Review methodology, date snapshots (27–28 September 2026), and primary document inventories.",
    keyFacts: [
      "Snapshot date: 27–28 September 2026.",
      "10 public repositories reviewed in Soban's account; 27 public repositories in Umar's account.",
      "5 non-public internship codebases reviewed locally for professional work summaries.",
    ],
    suggestedQueries: [
      "When was the public knowledge book reviewed and what was the methodology?",
      "What primary sources were used to compile this knowledge book?",
    ],
  },
];

type Exchange = {
  id: string;
  question: string;
  chapterNumber?: string;
  result?: PublicBookAnswer;
  error?: string;
};

export default function PublicBookPage() {
  const { token } = useAuth();
  const [activeChapterIndex, setActiveChapterIndex] = useState<number>(0);
  const [question, setQuestion] = useState("");
  const [model, setModel] = useState<string>(DEFAULT_MODEL);
  const [busy, setBusy] = useState(false);
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [activeSourceMargin, setActiveSourceMargin] = useState<string | null>(null);

  const activeChapter = CHAPTERS[activeChapterIndex];

  async function ask(text: string, chapterNum?: string) {
    if (!token || !text.trim() || busy) return;
    const query = text.trim();
    setQuestion("");
    setBusy(true);
    const exchangeId = `pb-${Date.now()}`;

    try {
      const result = await askPublicBook(token, query, model);
      setExchanges((current) => [
        ...current,
        {
          id: exchangeId,
          question: query,
          chapterNumber: chapterNum || activeChapter.number,
          result,
        },
      ]);
      setActiveSourceMargin(exchangeId);
    } catch (error) {
      setExchanges((current) => [
        ...current,
        {
          id: exchangeId,
          question: query,
          chapterNumber: chapterNum || activeChapter.number,
          error: error instanceof Error ? error.message : "The request failed",
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
        backgroundColor: "var(--bg)",
        color: "var(--text)",
      }}
    >
      {/* ── Top Running Context Rail (Architectural Page Identifier) ── */}
      <header
        style={{
          borderBottom: "1px solid var(--border)",
          backgroundColor: "rgba(16, 18, 22, 0.95)",
          backdropFilter: "blur(12px)",
          padding: "10px 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "12px",
          zIndex: 20,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px", flexWrap: "wrap" }}>
          <Link
            href="/chat"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              fontSize: "12.5px",
              fontWeight: 500,
              color: "var(--text-secondary)",
              padding: "4px 8px",
              borderRadius: "4px",
              border: "1px solid var(--border)",
              backgroundColor: "var(--surface)",
            }}
          >
            <ArrowLeft size={13} />
            <span>Chat Workbench</span>
          </Link>

          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", fontFamily: "var(--font-mono)" }}>
            <span style={{ color: "var(--text-muted)" }}>CORPUS:</span>
            <span style={{ color: "#FFFFFF", fontWeight: 600 }}>PUBLIC_KNOWLEDGE_BOOK.md</span>
            <span style={{ color: "var(--border)" }}>//</span>
            <span style={{ color: "var(--text-muted)" }}>CHAPTERS:</span>
            <span style={{ color: "#FFFFFF", fontWeight: 600 }}>09_CHAPTERS</span>
            <span style={{ color: "var(--border)" }}>//</span>
            <span style={{ color: "var(--emerald-light)", display: "inline-flex", alignItems: "center", gap: "4px" }}>
              <span style={{ width: "6px", height: "6px", borderRadius: "50%", backgroundColor: "var(--emerald)" }} />
              MINILM-384D
            </span>
          </div>
        </div>

        {/* Model Selector & Status */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <label
            htmlFor="pb-model-select"
            style={{ fontSize: "12px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "4px" }}
          >
            <Cpu size={13} />
            <span>INFERENCE:</span>
          </label>
          <select
            id="pb-model-select"
            aria-label="Public book inference model"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            style={{
              backgroundColor: "var(--surface-raised)",
              color: "#FFFFFF",
              border: "1px solid var(--border)",
              borderRadius: "4px",
              padding: "4px 8px",
              fontSize: "12px",
              fontWeight: 500,
              outline: "none",
              cursor: "pointer",
            }}
          >
            {MODEL_OPTIONS.map((item) => (
              <option key={item.id} value={item.id} style={{ background: "#16181C" }}>
                {item.label}
              </option>
            ))}
          </select>
          <ProjectOwnerCard />
        </div>
      </header>

      {/* ── Main Workspace: Editorial Index + Document Plane ── */}
      <div
        style={{
          display: "flex",
          flex: 1,
          width: "100%",
          overflow: "hidden",
        }}
      >
        {/* ── Left Editorial Index Column (Table of Contents) ── */}
        <nav
          aria-label="Public Book Chapter Index"
          style={{
            width: "300px",
            minWidth: "280px",
            borderRight: "1px solid var(--border)",
            backgroundColor: "var(--surface)",
            display: "flex",
            flexDirection: "column",
            overflowY: "auto",
            padding: "20px 0",
          }}
        >
          <div style={{ padding: "0 20px 14px", borderBottom: "1px solid var(--border-subtle)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
              <BookOpen size={16} color="var(--text-secondary)" />
              <span style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-muted)" }}>
                Table of Contents
              </span>
            </div>
            <h2 style={{ fontSize: "14px", fontWeight: 600, color: "#FFFFFF", margin: 0 }}>
              Corpus Structure
            </h2>
          </div>

          <div style={{ display: "flex", flexDirection: "column", padding: "8px 0" }}>
            {CHAPTERS.map((ch, idx) => {
              const isSelected = activeChapterIndex === idx;
              return (
                <button
                  key={ch.id}
                  onClick={() => setActiveChapterIndex(idx)}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "12px",
                    padding: "12px 20px",
                    background: isSelected ? "var(--surface-raised)" : "transparent",
                    border: "none",
                    borderLeft: isSelected ? "3px solid #FFFFFF" : "3px solid transparent",
                    color: isSelected ? "#FFFFFF" : "var(--text-secondary)",
                    cursor: "pointer",
                    textAlign: "left",
                    transition: "all 0.12s ease",
                    width: "100%",
                  }}
                >
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "12px",
                      fontWeight: 600,
                      color: isSelected ? "#FFFFFF" : "var(--text-muted)",
                      paddingTop: "1px",
                    }}
                  >
                    {ch.number}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: "13px",
                        fontWeight: isSelected ? 600 : 500,
                        lineHeight: 1.35,
                      }}
                    >
                      {ch.title}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Chapter Metadata Summary Box */}
          <div
            style={{
              margin: "auto 16px 16px",
              padding: "14px",
              backgroundColor: "rgba(255, 255, 255, 0.02)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "6px",
              fontSize: "11.5px",
              color: "var(--text-muted)",
              lineHeight: 1.5,
            }}
          >
            <div style={{ fontWeight: 600, color: "var(--text-secondary)", marginBottom: "4px" }}>
              Grounding Rule
            </div>
            Claims require primary Git commit proof or official portfolio documentation. Abstains when evidence is missing.
          </div>
        </nav>

        {/* ── Center Content Plane & Document Stream ── */}
        <main
          id="main-content"
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            overflowY: "auto",
            backgroundColor: "var(--bg)",
          }}
        >
          <div
            style={{
              flex: 1,
              maxWidth: "1040px",
              width: "100%",
              margin: "0 auto",
              padding: "32px 36px 40px",
              display: "flex",
              flexDirection: "column",
              gap: "32px",
            }}
          >
            {/* Active Chapter Header & Briefing */}
            <section
              style={{
                borderBottom: "1px solid var(--border)",
                paddingBottom: "24px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  fontSize: "12px",
                  fontFamily: "var(--font-mono)",
                  color: "var(--text-muted)",
                  marginBottom: "8px",
                }}
              >
                <span>CHAPTER {activeChapter.number}</span>
                <span>/</span>
                <span>SECTION 1.0</span>
              </div>

              <h1
                style={{
                  fontSize: "26px",
                  fontWeight: 700,
                  letterSpacing: "-0.025em",
                  color: "#FFFFFF",
                  marginBottom: "10px",
                }}
              >
                {activeChapter.title}
              </h1>

              <p
                style={{
                  fontSize: "14.5px",
                  lineHeight: 1.65,
                  color: "var(--text-secondary)",
                  maxWidth: "800px",
                  margin: "0 0 18px",
                }}
              >
                {activeChapter.scope}
              </p>

              {/* Architectural Key Evidence Points (Typography-driven, no card spam) */}
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "8px",
                  borderLeft: "2px solid rgba(255, 255, 255, 0.15)",
                  paddingLeft: "14px",
                  margin: "14px 0 20px",
                }}
              >
                {activeChapter.keyFacts.map((fact, fIdx) => (
                  <div
                    key={fIdx}
                    style={{
                      fontSize: "13px",
                      lineHeight: 1.5,
                      color: "var(--text)",
                    }}
                  >
                    &bull; {fact}
                  </div>
                ))}
              </div>

              {/* Suggested Chapter Inquiries (Typographic list with direct trigger) */}
              <div>
                <div
                  style={{
                    fontSize: "11px",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    color: "var(--text-muted)",
                    marginBottom: "10px",
                  }}
                >
                  Suggested Chapter Questions
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  {activeChapter.suggestedQueries.map((q, qIdx) => (
                    <button
                      key={qIdx}
                      onClick={() => ask(q, activeChapter.number)}
                      disabled={busy}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "10px 14px",
                        backgroundColor: "var(--surface)",
                        border: "1px solid var(--border)",
                        borderRadius: "6px",
                        color: "var(--text)",
                        fontSize: "13px",
                        textAlign: "left",
                        cursor: busy ? "not-allowed" : "pointer",
                        transition: "all 0.12s ease",
                      }}
                    >
                      <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <CornerDownRight size={13} color="var(--text-muted)" />
                        {q}
                      </span>
                      <ChevronRight size={14} color="var(--text-muted)" />
                    </button>
                  ))}
                </div>
              </div>
            </section>

            {/* ── Document + Margin Composition: Answer Exchanges ── */}
            {exchanges.length > 0 && (
              <section style={{ display: "flex", flexDirection: "column", gap: "28px" }}>
                <div
                  style={{
                    fontSize: "12px",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    color: "var(--text-muted)",
                  }}
                >
                  Inquiry Records & Evidentiary Provenance
                </div>

                {exchanges.map((exchange) => {
                  const isMarginOpen = activeSourceMargin === exchange.id;
                  return (
                    <article
                      key={exchange.id}
                      style={{
                        backgroundColor: "var(--surface)",
                        border: "1px solid var(--border)",
                        borderRadius: "8px",
                        overflow: "hidden",
                      }}
                    >
                      {/* Query Header */}
                      <div
                        style={{
                          padding: "14px 20px",
                          borderBottom: "1px solid var(--border)",
                          backgroundColor: "rgba(255, 255, 255, 0.02)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: "12px",
                          flexWrap: "wrap",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span
                            style={{
                              fontFamily: "var(--font-mono)",
                              fontSize: "11px",
                              color: "var(--text-muted)",
                              backgroundColor: "var(--surface-raised)",
                              padding: "2px 6px",
                              borderRadius: "4px",
                            }}
                          >
                            CH.{exchange.chapterNumber || "00"}
                          </span>
                          <h3 style={{ fontSize: "14.5px", fontWeight: 600, color: "#FFFFFF", margin: 0 }}>
                            {exchange.question}
                          </h3>
                        </div>

                        {exchange.result && (
                          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "11.5px", color: "var(--text-muted)" }}>
                            <span>Answered by {exchange.result.model}</span>
                            <span>&bull;</span>
                            <span style={{ color: exchange.result.abstained ? "var(--amber-light)" : "var(--emerald-light)" }}>
                              {exchange.result.abstained ? "Abstained" : "Grounded"}
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Error Banner */}
                      {exchange.error && (
                        <div
                          role="alert"
                          style={{
                            padding: "14px 20px",
                            backgroundColor: "rgba(244, 63, 94, 0.1)",
                            color: "#FB7185",
                            fontSize: "13px",
                            borderBottom: "1px solid rgba(244, 63, 94, 0.2)",
                          }}
                        >
                          {exchange.error}
                        </div>
                      )}

                      {/* Main Reading Column + Evidentiary Ledger */}
                      {exchange.result && (
                        <div style={{ padding: "20px" }}>
                          <div style={{ fontSize: "14px", lineHeight: 1.7, color: "var(--text)", margin: "0 0 16px" }}>
                            <MarkdownRenderer content={exchange.result.answer} />
                          </div>

                          {/* Provenance Footnote & Citation References */}
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              borderTop: "1px solid var(--border-subtle)",
                              paddingTop: "12px",
                              flexWrap: "wrap",
                              gap: "8px",
                            }}
                          >
                            <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "var(--text-muted)" }}>
                              <CheckCircle2 size={13} color="var(--emerald-light)" />
                              <span>
                                Citations: {exchange.result.citations.length > 0 ? exchange.result.citations.join(", ") : "Grounded Syntheses"}
                              </span>
                            </div>

                            {exchange.result.sources.length > 0 && (
                              <button
                                onClick={() => setActiveSourceMargin(isMarginOpen ? null : exchange.id)}
                                style={{
                                  background: "transparent",
                                  border: "1px solid var(--border)",
                                  borderRadius: "4px",
                                  padding: "4px 10px",
                                  color: "var(--text-secondary)",
                                  fontSize: "12px",
                                  cursor: "pointer",
                                  display: "flex",
                                  alignItems: "center",
                                  gap: "6px",
                                }}
                              >
                                <FileText size={12} />
                                <span>
                                  {isMarginOpen ? "Hide Source Passages" : `Inspect ${exchange.result.sources.length} Evidentiary Passages`}
                                </span>
                              </button>
                            )}
                          </div>

                          {/* Unfolded Evidentiary Margin (Document + Margin Architecture) */}
                          {isMarginOpen && exchange.result.sources.length > 0 && (
                            <div
                              style={{
                                marginTop: "16px",
                                padding: "16px",
                                backgroundColor: "rgba(0, 0, 0, 0.25)",
                                border: "1px solid var(--border)",
                                borderRadius: "6px",
                                display: "flex",
                                flexDirection: "column",
                                gap: "12px",
                              }}
                            >
                              <div
                                style={{
                                  fontSize: "11px",
                                  fontWeight: 700,
                                  textTransform: "uppercase",
                                  letterSpacing: "0.06em",
                                  color: "var(--text-muted)",
                                }}
                              >
                                Verifiable Source Passages from PUBLIC_KNOWLEDGE_BOOK.md
                              </div>

                              {exchange.result.sources.map((s, sIdx) => (
                                <div
                                  key={s.source_id || sIdx}
                                  style={{
                                    borderLeft: "2px solid #FFFFFF",
                                    paddingLeft: "12px",
                                    backgroundColor: "rgba(255, 255, 255, 0.02)",
                                    padding: "8px 12px",
                                    borderRadius: "0 4px 4px 0",
                                  }}
                                >
                                  <div
                                    style={{
                                      fontFamily: "var(--font-mono)",
                                      fontSize: "11.5px",
                                      fontWeight: 600,
                                      color: "#FFFFFF",
                                      marginBottom: "4px",
                                    }}
                                  >
                                    [{s.source_id}] {s.section}
                                  </div>
                                  <p
                                    style={{
                                      fontSize: "12.5px",
                                      lineHeight: 1.6,
                                      color: "var(--text-secondary)",
                                      margin: 0,
                                      whiteSpace: "pre-wrap",
                                    }}
                                  >
                                    {s.text}
                                  </p>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </article>
                  );
                })}
              </section>
            )}

            {/* ── Input Bar (Sticky at bottom of reading plane) ── */}
            <div
              style={{
                position: "sticky",
                bottom: 0,
                backgroundColor: "var(--bg)",
                paddingTop: "12px",
                borderTop: "1px solid var(--border)",
              }}
            >
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void ask(question);
                }}
                style={{
                  display: "flex",
                  gap: "10px",
                  alignItems: "center",
                  backgroundColor: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  padding: "6px 8px 6px 14px",
                }}
              >
                <Search size={15} color="var(--text-muted)" />
                <input
                  id="public-question-input"
                  aria-label="Question for the public knowledge book"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder={`Ask anything about Chapter ${activeChapter.number}: ${activeChapter.title} or across the entire book...`}
                  disabled={busy}
                  style={{
                    flex: 1,
                    background: "transparent",
                    border: "none",
                    color: "#FFFFFF",
                    fontSize: "13.5px",
                    outline: "none",
                  }}
                />
                <button
                  type="submit"
                  disabled={busy || !question.trim()}
                  className="btn btn-primary"
                  style={{ padding: "8px 16px", borderRadius: "6px" }}
                >
                  {busy ? (
                    <>
                      <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
                      <span>Retrieving...</span>
                    </>
                  ) : (
                    <span>Ask Book</span>
                  )}
                </button>
              </form>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: "11px",
                  color: "var(--text-muted)",
                  marginTop: "6px",
                  padding: "0 4px",
                }}
              >
                <span>Queries use the local MiniLM index; inspect source passages to check answers</span>
                <span>Strict attribution &bull; No halluncinated claims</span>
              </div>
            </div>
          </div>
        </main>
      </div>

      <Footer />
    </div>
  );
}
