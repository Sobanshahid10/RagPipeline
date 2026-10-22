<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

## Project-specific frontend notes

- The chat model list is defined in `lib/models.ts`; use it in both the chat dropdown and Settings panel. Send the selected model with each query through `lib/api.ts`. Never expose or store provider API keys in browser code.
- Settings save the default answer model in browser local storage. Other retrieval controls shown in Settings are not yet wired to backend request parameters; do not describe them as active runtime controls.
- `/chat` uses the tenant-uploaded-document API. `/public-book` uses the separate, already-indexed public-book pipeline and shows retrieved passages. Never ask users to re-upload the book to use that page.
