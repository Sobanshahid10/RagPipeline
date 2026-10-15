# Public-book live check — 29 September 2026

This run used the dedicated 161-chunk PostgreSQL public-book index. It did not upload the book to the general document library or read private storage. The question runner is `evaluation/live_public_book_chat.py`; its JSON traces include the actual retrieved passages and provider responses. Calls consume provider quota.

| Question type | Observed result |
| --- | --- |
| Basic hackathon fact | Groq GPT-OSS 120B and Gemini 3.5 Flash-Lite both named the AI Seekho Day 2026 Gemma fine-tuning hackathon and the README's 472 correct predictions and zero invalid outputs, with supporting source IDs. |
| Project-start chronology | Groq 120B identified 6 October 2025 as the earliest dated repository evidence and distinguished it from the unknown date Umar first learned or began coding. Gemini 3.5 Flash-Lite gave the same distinction. |
| Different wording | Both providers mapped “oldest dated footprint of Omer building software” to that same evidence. Some otherwise usable responses formatted citations as `【S3】` or `[S1, S4]`; the citation parser now normalizes these forms. |
| Commit-count trap | Gemini 3.5 Flash-Lite correctly distinguished 634 scoped authored commits from GitHub contributions. A Groq 120B response added the unsupported claim that the 1,011 contributions include commits by an excluded older identity. The book does not establish that composition. **This is a faithfulness failure despite valid-looking citations.** |
| Portfolio strength | Groq 120B gave a defensible opinion based on breadth of work and repeated source-traceability design. This is an interpretation of the indexed text, not an inspection of the live site's visual quality. |
| Portfolio weakness | Groq 120B and Gemini 3.5 Flash-Lite pointed to undefined self-reported “27+ shipped projects” and “14+ AI agents” labels. The indexed evidence supports that critique; it cannot establish an objective “worst” feature of the live site. |
| Cross-person attribution | Groq 120B abstained when asked whether Soban contributed to the private Docinsight codebase. The retrieved sources did not establish that attribution. |
| Unanswerable private fact | Gemini 3.8 Flash and Groq 120B abstained on a password question. Groq initially returned the correct abstention sentence with `abstained:false`; the parser now corrects that exact, citation-free form. |

**Provider status:** Both keys worked. Groq generated several full answers, although repeated requests reached HTTP 429 before later requests succeeded. Gemini 3.8 Flash returned a successful minimal generation and two valid abstentions, but several larger prompts returned HTTP 503. Gemini 3.5 Flash-Lite answered the basic, portfolio-critique, chronology, paraphrase, and commit-count questions in the live runs. Switching models is therefore useful, but availability and quota are provider controlled.

**What is validated:** The UI/API verifies the returned JSON shape, citation IDs against retrieved passages, and abstention consistency. It displays the passages for inspection. It does **not** verify that each cited passage semantically supports each claim. The Groq commit-count mistake demonstrates why a groundedness judge or human review remains necessary before calling this RAG pipeline accurate.

**Limits:** These are small manual spot checks, not a statistical benchmark. Responses and provider availability can vary between runs. The local `/public-book` page uses this dedicated index; the older `/chat` route uses tenant uploads. Questions on the Public Book page are currently answered independently rather than using previous turns as conversation memory.

## Broader API-route check

The authenticated-route code was exercised in process with its login dependency replaced by a test user; retrieval, source validation, provider calls, and answer parsing remained real. This avoided creating a throwaway account in the user's database. Full response and source traces are saved in `public_book_endpoint_groq_full.json`, `public_book_endpoint_gemini_full.json`, and the focused retest files beside this report.

- Groq GPT-OSS 120B: **14/16** requests returned answers. Two late requests hit HTTP 429. The ten reviewed answerable questions generally found their supporting passages; exact phrase coverage was complete for nine and partial for one source-policy case, whose answer still addressed the requested project-inclusion rule. Groq answered the portfolio strength and weakness questions after focused retesting with better evidence retrieval.
- Gemini 3.5 Flash-Lite: **11/11** selected requests returned an API response. It answered the factual, conflict, chronology, and paraphrase questions, but declined the exact portfolio-strength question even after relevant evidence and a clearer opinion instruction. It answered the portfolio-weakness question after the instruction change. A separate Gemini 3.5 Flash attempt returned HTTP 503.
- The public-book API now turns citation-bearing versions of the fixed abstention sentence into a citation-free abstention. An earlier run had accepted those responses with `abstained:false`.
- Both models initially omitted the book's explicit limitation that the separate summer-course claim was not independently verified. Gemini also initially omitted the warning that Docinsight's scheduler was not proven to run continuously in production. A stronger prompt caused Gemini to retain both caveats in focused retests; Groq still omitted the summer-course caveat on one retest. This remains a semantic-validation risk.
- The earlier Groq commit-count hallucination remains an observed failure. A later reviewed commit-count answer correctly distinguished 348 public-history authored commits from 634 authored commits including five internship histories.

The complete backend test suite passed (122 tests), frontend TypeScript checking passed, and ESLint passed for the new Public Book page, sidebar, and API client. Repository-wide ESLint still reports 21 errors in other frontend files; those were not introduced by the Public Book page. The local frontend, API, and Celery worker were stopped after testing; ports 3005 and 8001 were verified closed.
