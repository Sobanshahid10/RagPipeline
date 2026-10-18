"use client";

import React, { useState } from "react";
import { Copy, Check, Terminal, ExternalLink } from "lucide-react";

interface MarkdownRendererProps {
  content: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  // Parse blocks: code blocks, tables, blockquotes, lists, headings, and paragraphs
  const renderBlocks = () => {
    const lines = content.split("\n");
    const blocks: React.ReactNode[] = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];

      // 1. Code blocks: ```lang ... ```
      if (line.trim().startsWith("```")) {
        const lang = line.trim().slice(3).trim() || "text";
        const codeLines: string[] = [];
        i++;
        while (i < lines.length && !lines[i].trim().startsWith("```")) {
          codeLines.push(lines[i]);
          i++;
        }
        if (i < lines.length) i++; // skip closing ```
        const codeText = codeLines.join("\n");
        blocks.push(<CodeBlock key={`code-${i}-${lang}`} code={codeText} language={lang} />);
        continue;
      }

      // 2. Table detection: starts with | and next line has |---
      if (line.trim().startsWith("|") && i + 1 < lines.length && lines[i + 1].includes("---")) {
        const tableLines: string[] = [];
        while (i < lines.length && lines[i].trim().startsWith("|")) {
          tableLines.push(lines[i]);
          i++;
        }
        blocks.push(<TableBlock key={`table-${i}`} lines={tableLines} />);
        continue;
      }

      // 3. Headings
      if (line.startsWith("### ")) {
        blocks.push(
          <h3 key={`h3-${i}`} style={{ fontSize: "15px", fontWeight: 700, margin: "14px 0 6px", color: "#FFFFFF" }}>
            {renderInline(line.slice(4))}
          </h3>
        );
        i++;
        continue;
      }
      if (line.startsWith("## ")) {
        blocks.push(
          <h2 key={`h2-${i}`} style={{ fontSize: "17px", fontWeight: 700, margin: "16px 0 8px", color: "#FFFFFF" }}>
            {renderInline(line.slice(3))}
          </h2>
        );
        i++;
        continue;
      }
      if (line.startsWith("# ")) {
        blocks.push(
          <h1 key={`h1-${i}`} style={{ fontSize: "20px", fontWeight: 800, margin: "18px 0 10px", color: "#FFFFFF" }}>
            {renderInline(line.slice(2))}
          </h1>
        );
        i++;
        continue;
      }

      // 4. Blockquotes: > text
      if (line.startsWith("> ")) {
        const quoteLines: string[] = [];
        while (i < lines.length && lines[i].startsWith("> ")) {
          quoteLines.push(lines[i].slice(2));
          i++;
        }
        blocks.push(
          <blockquote
            key={`quote-${i}`}
            style={{
              borderLeft: "2px solid var(--border)",
              padding: "8px 14px",
              margin: "12px 0",
              background: "var(--surface-raised)",
              borderRadius: "0 4px 4px 0",
              color: "var(--text-secondary)",
              fontStyle: "italic",
            }}
          >
            {quoteLines.map((ql, qIdx) => (
              <p key={qIdx} style={{ margin: "3px 0" }}>
                {renderInline(ql)}
              </p>
            ))}
          </blockquote>
        );
        continue;
      }

      // 5. Unordered List items: - or *
      if (/^[\*\-]\s+/.test(line.trim())) {
        const listItems: string[] = [];
        while (i < lines.length && /^[\*\-]\s+/.test(lines[i].trim())) {
          listItems.push(lines[i].trim().replace(/^[\*\-]\s+/, ""));
          i++;
        }
        blocks.push(
          <ul key={`ul-${i}`} style={{ margin: "10px 0 12px 22px", display: "flex", flexDirection: "column", gap: "5px" }}>
            {listItems.map((item, idx) => (
              <li key={idx} style={{ color: "var(--text)", lineHeight: 1.55 }}>
                {renderInline(item)}
              </li>
            ))}
          </ul>
        );
        continue;
      }

      // 6. Ordered List items: 1. 2. 3.
      if (/^\d+\.\s+/.test(line.trim())) {
        const listItems: string[] = [];
        while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
          listItems.push(lines[i].trim().replace(/^\d+\.\s+/, ""));
          i++;
        }
        blocks.push(
          <ol key={`ol-${i}`} style={{ margin: "10px 0 12px 22px", display: "flex", flexDirection: "column", gap: "5px" }}>
            {listItems.map((item, idx) => (
              <li key={idx} style={{ color: "var(--text)", lineHeight: 1.55 }}>
                {renderInline(item)}
              </li>
            ))}
          </ol>
        );
        continue;
      }

      // 7. Empty line
      if (!line.trim()) {
        i++;
        continue;
      }

      // 8. Regular paragraph
      blocks.push(
        <p key={`p-${i}`} style={{ margin: "8px 0", lineHeight: 1.6, color: "var(--text)" }}>
          {renderInline(line)}
        </p>
      );
      i++;
    }

    return blocks;
  };

  return <div className="markdown-body">{renderBlocks()}</div>;
};

// ── Helper to sanitize link hrefs ────────────────────────────────────
function sanitizeHref(url: string): string {
  const trimmed = url.trim();
  if (/^https?:\/\//i.test(trimmed) || /^mailto:/i.test(trimmed) || trimmed.startsWith("/")) {
    return trimmed;
  }
  if (/^www\./i.test(trimmed)) {
    return `https://${trimmed}`;
  }
  return trimmed;
}

// ── Render Clickable Link Component ──────────────────────────────────
function renderLinkElement(
  key: string | number,
  href: string,
  displayText: string,
  isRawUrl: boolean = false
): React.ReactNode {
  const safeHref = sanitizeHref(href);
  const isExternal = /^https?:\/\//i.test(safeHref);

  return (
    <a
      key={key}
      href={safeHref}
      target={isExternal ? "_blank" : undefined}
      rel={isExternal ? "noopener noreferrer" : undefined}
      className="markdown-link inline-link"
      style={{
        color: "var(--cyan-light, #7DD3FC)",
        textDecoration: "underline",
        textUnderlineOffset: "3px",
        textDecorationColor: "rgba(125, 211, 252, 0.45)",
        wordBreak: "break-all",
        display: "inline-flex",
        alignItems: "center",
        gap: "3px",
        transition: "color 0.15s ease, text-decoration-color 0.15s ease",
      }}
    >
      <span>{displayText}</span>
      {isExternal && (
        <ExternalLink
          size={11}
          style={{ opacity: 0.75, flexShrink: 0, display: "inline-block", verticalAlign: "middle" }}
        />
      )}
    </a>
  );
}

// ── Inline Markdown Parser (Bold, Italic, Code, Links & Auto-URLs) ───
function renderInline(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let keyIndex = 0;

  while (remaining.length > 0) {
    // 1. Inline code `code`
    const codeMatch = remaining.match(/^`([^`]+)`/);
    if (codeMatch) {
      parts.push(
        <code
          key={`code-${keyIndex++}`}
          style={{
            background: "rgba(255, 255, 255, 0.08)",
            padding: "2px 6px",
            borderRadius: "4px",
            fontSize: "12px",
            color: "#A5B4FC",
            border: "1px solid rgba(255, 255, 255, 0.06)",
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          {codeMatch[1]}
        </code>
      );
      remaining = remaining.slice(codeMatch[0].length);
      continue;
    }

    // 2. Bold **text**
    const boldMatch = remaining.match(/^\*\*([^*]+)\*\*/);
    if (boldMatch) {
      parts.push(
        <strong key={`bold-${keyIndex++}`} style={{ fontWeight: 700, color: "#FFFFFF" }}>
          {boldMatch[1]}
        </strong>
      );
      remaining = remaining.slice(boldMatch[0].length);
      continue;
    }

    // 3. Italic *text*
    const italicMatch = remaining.match(/^\*([^*]+)\*/);
    if (italicMatch) {
      parts.push(
        <em key={`italic-${keyIndex++}`} style={{ fontStyle: "italic", color: "var(--text-secondary)" }}>
          {italicMatch[1]}
        </em>
      );
      remaining = remaining.slice(italicMatch[0].length);
      continue;
    }

    // 4. Markdown links: [text](url)
    const linkMatch = remaining.match(/^\[([^\]]+)\]\(([^)]+)\)/);
    if (linkMatch) {
      parts.push(
        renderLinkElement(`link-${keyIndex++}`, linkMatch[2], linkMatch[1], false)
      );
      remaining = remaining.slice(linkMatch[0].length);
      continue;
    }

    // 5. Bare/Raw URLs: https://... or http://... or www....
    const rawUrlMatch = remaining.match(/^(https?:\/\/[^\s<>"{}|\\^`]+|www\.[^\s<>"{}|\\^`]+)/i);
    if (rawUrlMatch) {
      let matchedUrl = rawUrlMatch[0];
      let trailing = "";

      // Strip trailing punctuation not belonging to URL
      while (/[.,;:!?)]$/.test(matchedUrl)) {
        if (
          matchedUrl.endsWith(")") &&
          (matchedUrl.match(/\(/g) || []).length >= (matchedUrl.match(/\)/g) || []).length
        ) {
          break;
        }
        trailing = matchedUrl.slice(-1) + trailing;
        matchedUrl = matchedUrl.slice(0, -1);
      }

      if (matchedUrl) {
        parts.push(
          renderLinkElement(`rawurl-${keyIndex++}`, matchedUrl, matchedUrl, true)
        );
        if (trailing) {
          parts.push(trailing);
        }
        remaining = remaining.slice(rawUrlMatch[0].length);
        continue;
      }
    }

    // 6. Plain text up to next special token or URL
    const nextSpecial = remaining.search(/[`\*\[]|https?:\/\/|www\./i);
    if (nextSpecial === -1) {
      parts.push(remaining);
      break;
    } else if (nextSpecial > 0) {
      parts.push(remaining.slice(0, nextSpecial));
      remaining = remaining.slice(nextSpecial);
    } else {
      // First char didn't match any rule, push single character and proceed
      parts.push(remaining[0]);
      remaining = remaining.slice(1);
    }
  }

  return <>{parts}</>;
}

// ── Code Block Component with Copy Button ────────────────────────────
const CodeBlock: React.FC<{ code: string; language: string }> = ({ code, language }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="code-block-wrapper">
      <div className="code-block-header">
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <Terminal size={13} color="var(--text-muted)" />
          <span>{language}</span>
        </div>
        <button
          onClick={handleCopy}
          style={{
            background: "transparent",
            border: "none",
            color: copied ? "var(--emerald-light)" : "var(--text-muted)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "5px",
            fontSize: "11px",
            fontWeight: 500,
            fontFamily: "inherit",
          }}
        >
          {copied ? <Check size={12} color="#10B981" /> : <Copy size={12} />}
          <span>{copied ? "Copied" : "Copy"}</span>
        </button>
      </div>
      <pre className="code-block-content">
        <code>{code}</code>
      </pre>
    </div>
  );
};

// ── Table Component ──────────────────────────────────────────────────
const TableBlock: React.FC<{ lines: string[] }> = ({ lines }) => {
  if (lines.length < 2) return null;

  const headerCells = lines[0]
    .split("|")
    .map((c) => c.trim())
    .filter((c, idx, arr) => idx !== 0 && idx !== arr.length - 1);

  const bodyRows = lines.slice(2).map((l) =>
    l
      .split("|")
      .map((c) => c.trim())
      .filter((c, idx, arr) => idx !== 0 && idx !== arr.length - 1)
  );

  return (
    <div style={{ overflowX: "auto", margin: "14px 0" }}>
      <table>
        <thead>
          <tr>
            {headerCells.map((h, i) => (
              <th key={i}>{renderInline(h)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {bodyRows.map((row, rIdx) => (
            <tr key={rIdx}>
              {row.map((cell, cIdx) => (
                <td key={cIdx}>{renderInline(cell)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
