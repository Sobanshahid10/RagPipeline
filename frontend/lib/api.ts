/**
 * Typed client API library for the Production RAG Pipeline.
 */

export const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001").replace(/\/api\/v1\/?$/, "");

export interface PublicBookSource {
  source_id: string;
  chunk_id: string;
  citation: string;
  section: string;
  text: string;
}

export interface PublicBookAnswer {
  question: string;
  model: string;
  answer: string;
  citations: string[];
  abstained: boolean;
  sources: PublicBookSource[];
}

export async function askPublicBook(token: string, question: string, model: string): Promise<PublicBookAnswer> {
  const response = await fetch(`${API_BASE}/api/v1/public-book/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ question, model }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(typeof error.detail === "string" ? error.detail : `Public-book request failed (${response.status})`);
  }
  return response.json();
}

export interface UserProfile {
  id: string;
  email: string;
  tenant_id?: string;
  tenant_name?: string;
  tenant?: {
    id?: string;
    name?: string;
  };
  roles?: string[];
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface BoundingBox {
  ymin?: number;
  xmin?: number;
  ymax?: number;
  xmax?: number;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  text?: string;
}

export interface CitationBlock {
  chunk_id: string;
  document_id?: string;
  page_number?: number;
  bounding_box?: BoundingBox;
  source_filename?: string;
  excerpt?: string;
}

export interface QueryMetadata {
  ttft_ms?: number;
  total_latency_ms?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  route_used?: string;
  chunks_retrieved?: number;
  source?: string;
  interaction_id?: string;
}

export interface DocumentItem {
  document_id: string;
  id?: string;
  filename: string;
  file_type: string;
  status: string;
  total_pages: number;
  chunk_count: number;
  created_at?: string;
}

export type SSEEvent =
  | { type: "token"; content: string }
  | { type: "citation"; citation: CitationBlock }
  | { type: "done"; answer?: string; metadata?: QueryMetadata }
  | { type: "error"; message: string };

/**
 * Log in with user credentials and obtain a JWT bearer token.
 */
export async function login(email: string, password: string): Promise<AuthResponse> {
  const params = new URLSearchParams();
  params.append("username", email);
  params.append("password", password);

  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: params.toString(),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Login failed with status ${res.status}`);
  }

  return res.json();
}

/**
 * Register a new user and tenant organization.
 */
export async function register(email: string, password: string, tenant_name: string): Promise<UserProfile> {
  const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, tenant_name }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Registration failed with status ${res.status}`);
  }

  return res.json();
}

/**
 * Fetch profile information for the authenticated user.
 */
export async function getMe(token: string): Promise<UserProfile> {
  const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    throw new Error("Failed to authenticate user profile.");
  }

  return res.json();
}

/**
 * Upload a document to the ingestion pipeline.
 */
export async function uploadDocument(file: File, token: string, tenantId?: string): Promise<DocumentItem> {
  const formData = new FormData();
  formData.append("file", file);
  if (tenantId) {
    formData.append("tenant_id", tenantId);
  }

  const res = await fetch(`${API_BASE}/api/v1/documents/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to upload document.");
  }

  return res.json();
}

/**
 * List all documents uploaded for the current tenant.
 */
export async function getDocuments(token: string, tenantId?: string): Promise<DocumentItem[]> {
  const url = tenantId 
    ? `${API_BASE}/api/v1/documents?tenant_id=${encodeURIComponent(tenantId)}`
    : `${API_BASE}/api/v1/documents`;

  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    // If backend doesn't have a list endpoint, return empty list gracefully
    return [];
  }

  return res.json();
}

/**
 * Retrieve status and metadata for a single document.
 */
export async function getDocumentStatus(id: string, token: string): Promise<DocumentItem> {
  const res = await fetch(`${API_BASE}/api/v1/documents/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch document status.");
  }

  return res.json();
}

/**
 * Generate a static URL to stream/fetch the PDF file.
 */
export function getDocumentFileUrl(docId: string): string {
  return `${API_BASE}/api/v1/documents/${docId}/file`;
}

/**
 * Permanently delete a document and its cascading chunks.
 */
export async function deleteDocument(id: string, token: string): Promise<{ status: string; document_id: string; filename?: string; message?: string }> {
  const res = await fetch(`${API_BASE}/api/v1/documents/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to delete document.");
  }

  return res.json();
}

/**
 * Stream a grounded SSE query response token-by-token.
 */
export async function* streamQuery(query: string, token: string, model?: string): AsyncGenerator<SSEEvent, void, unknown> {
  const response = await fetch(`${API_BASE}/api/v1/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ query, model }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    yield {
      type: "error",
      message: err.detail || `Server returned status ${response.status}`,
    };
    return;
  }

  if (!response.body) {
    yield { type: "error", message: "No response stream available." };
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let currentEvent = "message";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      if (trimmed.startsWith("event:")) {
        currentEvent = trimmed.slice(6).trim();
      } else if (trimmed.startsWith("data:")) {
        const jsonStr = trimmed.slice(5).trim();
        try {
          const parsed = JSON.parse(jsonStr);
          if (parsed.type === "token") {
            yield { type: "token", content: parsed.content };
          } else if (parsed.type === "citation") {
            yield { type: "citation", citation: parsed.citation };
          } else if (parsed.type === "done") {
            yield {
              type: "done",
              answer: parsed.answer,
              metadata: parsed.metadata,
            };
          } else {
            yield parsed as SSEEvent;
          }
        } catch {
          // Non-JSON SSE payload fallback
          yield { type: "token", content: jsonStr };
        }
      }
    }
  }
}

/** Save thumbs-up or thumbs-down feedback for a completed query. */
export async function submitFeedback(interactionId: string, feedback: 1 | -1, token: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/query/${interactionId}/feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ feedback }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Feedback failed with status ${response.status}`);
  }
}
