# Project guidance for agents

## Two distinct RAG paths

- `PUBLIC_KNOWLEDGE_BOOK.md` is the public-only learning corpus. Its explicit step 1–11 scripts, artifacts, and guides live in `backend/app/ingestion/`, `backend/app/retrieval/`, `backend/app/generation/`, `storage/knowledge/`, and `docs/STEP_*.md`. The `/public-book` browser page and `/api/v1/public-book/ask` endpoint now query this existing index without uploading the book. They perform structural answer/citation validation; semantic grounding and formal G-Eval are still incomplete.
- The existing FastAPI/Next.js app handles tenant-uploaded PDF/DOCX/TXT documents. `backend/app/api/documents.py` saves an upload and queues `backend/app/ingestion/pipeline.py` on Celery. That worker parses, masks PII, summarizes, chunks, embeds, indexes, and extracts graph triples. It is a different implementation from the public-book step scripts. Retrieval, prompt building, and generation happen when a user asks a question, not at upload time.
- Never claim that uploading a PDF automatically runs the public-book ten-step workflow or G-Eval. Inspect status and evidence before claiming an upload was indexed or an answer was grounded.

## Sources and privacy

- Keep `storage/private/` and personal chats outside the public book, public index, and public-book API calls. Do not copy private material into public artifacts.
- For Umar's projects, GitHub repository evidence takes precedence over portfolio-only listings. The portfolio is the preferred source for education, work experience, and skills. Preserve attribution and source conflicts.
- Do not print, commit, or put API keys in frontend code. Local credentials belong in the ignored repository-root `.env`; `.env.example` contains names only.

## Model configuration

- Gemini and Groq answer models are selected per chat request. The frontend model list is `frontend/lib/models.ts`; the backend allowlist is `QueryRequest.model` in `backend/app/api/query.py`. Keep them aligned.
- Current Gemini choices: `gemini-3.8-flash`, `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`, and `gemini-3.5-flash-lite`. Groq choices: `openai/gpt-oss-120b` and `openai/gpt-oss-20b`. Use current official provider docs when changing IDs.
- `.env` can hold both `GEMINI_API_KEY` and `GROQ_API_KEY`. `LLM_PROVIDER` and `LLM_MODEL` set the backend defaults; a model chosen in chat overrides final-answer generation for that request. Restart the backend after changing `.env`. The public-book step-eleven CLI uses Gemini only, while the public-book browser page supports both Gemini and Groq.
- The generic PDF-upload path uses `gemini-embedding-2` at 1536 dimensions when a Gemini key is configured. The public-book path uses a separate local MiniLM index. Changing an embedding model requires reindexing its documents; do not mix vectors from different models.

## Local verification

- Development frontend: `http://localhost:3005`; backend: `http://localhost:8001`. PostgreSQL and Redis are exposed on 5433 and 6380 in development Compose. The document worker must be running for uploads to finish.
- Check the chat route and API health, run focused Python tests and `frontend/node_modules/.bin/tsc --noEmit`, and use mocked provider responses before claiming model switching works. A live provider call requires a configured key and consumes quota.
- The public-book page works in the local development setup where the repository root, public-book artifacts, cached MiniLM model, and PostgreSQL index are present. The generic backend Docker image lacks those files and serves a 503 for this route; do not describe the Docker deployment as public-book ready.
