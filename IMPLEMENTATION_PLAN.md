# AgentFlow implementation plan

Date: 27 October 2026  
Source: HLD.docx, version 1.0, proposed  
Status: Implementation started. Foundation code is in place; see docs/VERIFICATION.md for evidence and outstanding integration work.

Build a public portfolio application that demonstrates reliable AI workflows, grounded answers, safe document extraction, and observable execution. The reviewer should be able to reproduce the application, inspect the engineering decisions, and verify failure behavior. A polished interface alone is not sufficient evidence.

## 1. Scope and decisions

The following decisions resolve ambiguities in the HLD. They are recommendations for implementation, not changes already made to the source document.

| Area | V1 decision | Reason |
| --- | --- | --- |
| Architecture | One Next.js application and one modular FastAPI backend | Keeps deployment and debugging manageable. No microservices or agent framework required. |
| Agents | Explicit typed stages with bounded routing | Each stage has an input schema, output schema, deadline, and trace. Deterministic stages do not need an LLM call. |
| Admin | Defer dashboard, Auth integration, and all admin API routes to V1.1 | HLD section 50 defers these features. Use an operator-only ingestion CLI in V1; no public ingestion route. Record this scope decision for review. |
| Evaluation | Include a small versioned evaluation set in V1 | Retrieval and structured-output correctness must be demonstrated before release. Larger benchmarking remains later. |
| Response delivery | Return complete JSON with sanitized execution trace | Streaming adds complexity and can expose unvalidated output. Add it later if justified. |
| Demo Mode | Bundle synthetic scenarios with the frontend | It remains usable when the backend, database, or provider is unavailable. Show an explicit DEMO MODE label and illustrative trace label. |
| Documents | One repository-owned synthetic invoice, selected by an allowlisted ID | No request-supplied paths, URLs, or uploads. Other samples are later scope. |
| Knowledge | Versioned synthetic Markdown corpus and repeatable ingestion | Reviewable provenance, reproducible retrieval, and no private data. |
| Cost | Free-tier-only deployment with no automatic paid fallback | Zero spend is an operational constraint, not a promise of unlimited availability. |

Retain the HLD stack. Select and pin compatible supported dependency versions during setup. Select generation and embedding model IDs only after checking availability and free-tier eligibility in the actual project. Do not assume the example embedding model or quoted quotas remain applicable.

## 2. Request and data design

Live request flow: bounded request parsing -> schema validation -> server-side Turnstile verification -> atomic rate and budget admission -> safety stage -> router -> selected workflow -> response stage -> deterministic validation -> public response and trace.

Apply cheap rejection and a coarse pre-verification abuse limit before external calls. Turnstile is verified once for a request; every generation or embedding attempt must separately reserve provider budget. CORS is a browser control, not protection against direct API callers.

Use explicit intent values from the HLD: GENERAL_QUESTION, KNOWLEDGE_QUERY, QUOTE_REQUEST, LEAD, DOCUMENT_DEMO, UNSUPPORTED. Normalize the inconsistent REQUEST_QUOTE trace example to QUOTE_REQUEST. Quote requests may invoke both lead extraction and retrieval; routing must support this bounded combination.

Separate generation and embedding interfaces. Generation returns validated structured data plus usage metadata; embedding returns vectors plus model and dimension metadata. Provider adapters translate timeouts, rate limits, refusals, and malformed output into application errors. Initially implement Gemini and a deterministic test provider only.

Start with at most two generation calls and one query embedding per chat request, one generation call for the sample document, no automatic retries, and a 20-second overall processing deadline after backend admission. Confirm feasibility in the provider spike before finalizing these limits. Cold-start waiting is a separate frontend state. Add retries only with explicit attempt budgets and evidence that they help.

Conversation history remains client-side and is resent only within validated limits. Treat every supplied historical message as untrusted; reject client-supplied system/tool roles. Enforce 2,000 characters per message, a precisely documented ten-turn definition, and 20 KB for the complete request, including the challenge token. Bound retrieved context and output separately.

Define an API contract before UI integration:

- `GET /health`: minimal liveness and version, no dependency details or expensive probes.
- `GET /api/demo/scenarios`: scenario catalogue; frontend also has a bundled copy.
- `POST /api/chat`: bounded messages and Turnstile token; returns request ID, mode, answer, citations, optional structured lead, sanitized trace, and status.
- `POST /api/demo/document`: allowlisted sample ID and Turnstile token for live processing. Demo results come from bundled fixtures.
- `GET /api/architecture`: curated public metadata, never runtime configuration.

Use one error envelope with a stable code, safe message, request ID, and optional retry delay. Invalid input returns 422, oversized bodies 413, challenge rejection 403, exhausted limits 429, unavailable live dependencies 503, and deadlines 504. On live failure, the UI offers predefined Demo Mode scenarios; it must not present a recorded answer as the answer to arbitrary free text.

## 3. Persistence and retrieval

Use SQLAlchemy and versioned migrations. Add document content hashes, source/version identifiers, chunk uniqueness, embedding model/dimension/version, and foreign keys to the HLD tables. Use UTC timestamps and indexes justified by actual queries. Start with exact vector search for the small corpus; introduce approximate indexing only after measurement.

Ingestion must be idempotent: running it twice leaves no duplicate chunks. Stage a new corpus version, validate it, then activate it transactionally. A failed reindex leaves the previous version queryable. Model or vector-dimension changes require explicit re-embedding and migration; never mix incompatible vectors.

Return stable citation IDs that map to the exact retrieved chunks and public source documents. Check citation membership in code. If retrieval is weak or empty, ask for clarification or say the knowledge base cannot answer. A valid citation does not prove that a claim is supported; evaluate grounding separately.

Persist only allowlisted operational metadata. Do not store prompts, answers, lead fields, document extraction payloads, JWTs, raw IPs, or unrestricted exception text. Omit persistent session hashes unless a concrete need is established. Use short-lived HMAC identifiers only for rate limiting, with TTLs and a dedicated secret. Document trusted proxy handling so spoofed forwarding headers cannot bypass limits.

Proposed retention: seven days for per-request metrics and agent execution records, with repeatable cleanup and verification. Keep token counts nullable when unavailable rather than recording an invented zero. Telemetry write failures must not fail an otherwise valid answer.

Use a least-privilege database role for application queries and a separate migration/ingestion role. Enable RLS and explicitly deny public table access. Do not assume RLS protects queries made with a role that bypasses it.

## 4. Delivery milestones

Estimates are focused working days for one developer, not calendar promises. Re-estimate after the provider and hosting spike. Indicative total: 23–34 working days, plus account setup and reviewer turnaround.

| Milestone | Effort | Deliverables | Exit criteria |
| --- | --- | --- | --- |
| M0 Design baseline | 2–3 days | Scope decisions, threat model, API schemas, synthetic company outline, provider/hosting spike, requirements checklist | One generation and one embedding call validated within free-tier constraints; model dimensions and quotas recorded; unresolved blockers documented. |
| M1 Foundation | 2–3 days | Repository structure, lockfiles, local Docker setup with Postgres/pgvector and Redis, migrations, health endpoint, frontend shell, CI | Clean checkout starts locally without paid services; deterministic tests, lint, types, and builds pass; no secrets in tracked files. |
| M2 Complete demo slice | 2–3 days | Chat layout, bundled scenarios, citation display, trace UI, document sample screen, error/loading states | Recruiter can complete a clearly labeled scenario with backend network access disabled; keyboard and mobile flows work. |
| M3 Protected live AI | 4–5 days | Provider adapters, orchestrator, typed router/lead/response stages, validation, Turnstile, atomic Redis budgets, deadlines | Real synthetic chat and lead extraction work; invalid challenge, exhausted budget, dependency failure, malformed model output, and timeout tests pass. |
| M4 Grounded retrieval | 4–6 days | Six synthetic knowledge files, ingestion CLI, migrations, retrieval, source mapping, evaluation fixtures | Reingestion is idempotent; failed updates preserve active corpus; answerable questions cite retrieved evidence; unknown questions abstain. |
| M5 Document workflow and telemetry | 2–3 days | One sample invoice extraction flow, typed output, safe execution metadata, metrics retention | Extracted fields match fixture; invalid sample IDs fail before file access; no prompt/secret leakage in logs, traces, or DB. |
| M6 Hardening and evaluation | 4–6 days | End-to-end tests, adversarial cases, concurrency checks, accessibility pass, security scans, evaluation report | Release gates below pass with recorded commands and results; material defects fixed. |
| M7 Deployment and review | 3–5 days | Public deployment, configuration checklist, README, architecture docs, rollback/runbook, reviewer evidence | Fresh-machine setup and deployed smoke tests pass; quota/outage fallback verified; reviewer can map HLD requirements to implementation and tests. |

Work in small feature branches and reviewable PRs. Run an architecture checkpoint after M0 and a working-system checkpoint after M4 so fundamental issues surface before the final review. If the senior is only available at the end, preserve these checkpoint records for their review.

## 5. Security and availability gates

- Atomically enforce per-visitor minute/hour/day limits and global request, generation, embedding, and token budgets. HLD values are initial upper bounds; tune down to actual provider allowances. Concurrent requests must not overspend the remaining admission budget.
- When Redis or Turnstile verification is unavailable, fail closed for live AI and offer local Demo Mode. Include ingestion in the provider allowance; it must not silently consume the demo budget.
- Verify Turnstile server-side, including expected hostname/action and replay failure. Never ship test bypasses enabled in production.
- Treat model output and retrieved text as untrusted. No arbitrary network, filesystem, shell, SQL, or email tools. A safety classifier is not the security boundary.
- Render escaped text or Markdown with raw HTML disabled and safe link protocols. Test malicious links and markup. Apply and verify CSP with the actual Next.js and Turnstile deployment.
- Keep secrets server-side and out of public frontend environment variables. Redact SDK errors, access logs, trace payloads, and HTTP diagnostics. Document provider/host data handling separately from application storage behavior.
- CI uses minimum permissions; untrusted PRs get no production secrets. Include secret scanning, CodeQL, dependency checks, lint, type checks, deterministic tests, and build verification. Confirm that checks actually gate merging.
- Deploy only validated revisions. Run migrations intentionally with a recovery procedure; use backward-compatible schema changes so application rollback remains possible.

## 6. Test and evaluation evidence

Keep most tests deterministic and independent of live quotas. Integration tests use real local PostgreSQL/pgvector and Redis. A small manual live smoke test verifies actual provider compatibility before release.

Create a versioned set of at least 40 cases: 15 answerable knowledge questions with expected source IDs, 10 unknown or ambiguous questions, 10 routing/lead cases, and 5 adversarial cases. Add a separate exact-field invoice fixture. Keep a held-out subset so tuning is not scored only on the examples used to develop prompts.

Proposed release thresholds: retrieval recall@5 of at least 90% on answerable cases; at least 90% correct abstention on unknown cases; at least 90% correct intent routing; all returned citation IDs belong to retrieved evidence; every accepted structured response passes schema validation; invoice fields match the sample; all deterministic security boundary tests pass. Report raw counts alongside percentages. Review answer support manually with a written rubric; do not claim a validator or small test set eliminates hallucinations.

Test failures explicitly: provider 429/5xx, unavailable embeddings, database outage, Redis outage, expired challenge, duplicate submission, partial ingestion, fabricated citations, invalid JSON, oversized history, unsafe Markdown, and cancellation/deadline behavior. Check that observability failures do not break responses.

Record warm-request p50/p95 latency, cold-start behavior, provider call counts, and tokens per scenario. Set final latency targets after M0 measurement. The sample millisecond timings in the HLD are illustrations, not measured service objectives.

## 7. Senior reviewer handoff

Provide a requirements matrix mapping HLD sections to code, tests, and evidence, with deliberate deferrals clearly marked. Include architecture and trust-boundary diagrams, API specification, schema/migrations, threat model, short architecture decision records, evaluation results, known limitations, and deployment/rollback instructions.

The reviewer should be able to verify:

1. A clean checkout runs using documented commands and safe example configuration.
2. Live RAG retrieves actual stored chunks and cites them accurately.
3. Every public trace represents real operational stages; recorded traces are explicitly illustrative.
4. Quotas and authorization boundaries are enforced by backend code under concurrency.
5. Secrets and visitor content do not leak into bundles, logs, metrics, or public errors.
6. Model/dependency failures produce safe, usable behavior.
7. Tests demonstrate business behavior and failure boundaries, not merely implementation details.
8. Tradeoffs are explained honestly, including free-tier availability and remaining risks.

## 8. First implementation batch

Start with M0 and M1. Create the scope/ADR records and threat model; define request/response schemas and the synthetic company; initialize the monorepo, lockfiles, environment examples, Docker services, baseline migration, FastAPI health endpoint, and Next.js shell; add CI; verify local startup and a clean build. End this batch with a running foundation and a reviewable PR. Do not begin all agent implementations simultaneously.

Decisions needed before deployment, but not before local scaffolding: GitHub repository name/owner, license, cloud accounts and region eligibility, final free-tier model selection, and permission to publish the public deployment. Account credentials must be supplied through provider settings or local secret storage, never committed.

## 9. External constraints checked

Official documentation checked on 27 October 2026:

- Gemini pricing distinguishes free and paid availability by model and lists free-tier data-use conditions. Confirm the exact selected models and account eligibility during M0: https://ai.google.dev/gemini-api/docs/pricing
- Render describes free services as suitable for hobby/testing and documents idle spin-down and startup delays. Demo Mode must not depend on a warm backend: https://render.com/docs/free
- Review Vercel Hobby terms and limits before deployment: https://vercel.com/docs/plans/hobby

Supabase, Upstash, GitHub, and Turnstile account-specific limits and terms remain deployment checks. The HLD's numerical allowances are not treated as verified guarantees. Recheck all service limits before publication; never enable paid fallback to resolve an exhausted free allowance.

## Implementation checkpoint � 28 October 2026

M3 local implementation now includes the protected live route, typed Gemini router/lead/response workflow, atomic Upstash limits, Turnstile verification, bounded transport, deadlines, generated API types and /live UI. Adapter and failure checks pass. Acceptance is pending a successful real-browser Turnstile submission; the embedded browser was rejected by Cloudflare (300030). M4 live retrieval, M5 document workflow, M6 comprehensive hardening and M7 deployment remain open. See docs/LIVE.md and docs/VERIFICATION.md for evidence and exact limitations.

### Follow-up checkpoint

Regular-browser live success is confirmed by the user. Corrected inferred customer type with server-side validation and regression coverage. M4 has started with deterministic source/chunk preparation in backend/app/knowledge.py. Next: versioned chunk storage and transactional, budgeted embedding ingestion, followed by retrieval, citation validation and abstention evaluation. M4 remains incomplete.

### M4 implementation checkpoint

Implemented atomic versioned ingestion, bounded embeddings, exact cosine retrieval, quotation provenance validation, source snapshot endpoint and citation inspection UI. Local ingestion and 57 backend tests passed. Awaiting explicit approval for the read-only runtime login before activation and real retrieval evaluation. M4 acceptance is not complete until those steps pass.

## Approved retrieval activation

The user explicitly approved the local read-only login and credential storage. Provisioning completed; the runtime identity is agentflow_runtime, read-only transactions are enabled, and all six published chunks are visible. Retrieval is enabled in the running API. The published pricing source returned HTTP 200. The real products evaluation passed with source provenance validation. The remaining real evaluation cases are incomplete: the shared application budget has 197,838 of 200,000 units reserved, insufficient for another generation. No counters or limits were changed. See docs/retrieval-evaluation-result.json (or retrieval-evaluation-result.json from this directory) for the recorded reset time. M4 runtime activation is complete; full real evaluation acceptance remains pending.


## 29 October 2026 verification and M5 progress

The daily reservation expired naturally; no limits or counters were changed. All four real retrieval cases now pass (products, pricing, unknown CEO, adversarial unknown fact), including source snapshot checks. This completes the previously blocked small M4 live evaluation; broader M6 evaluation and browser citation acceptance remain outstanding. See docs/retrieval-evaluation-result.json.

M5 sample invoice extraction is implemented in the backend and live UI, with shared admission/budgets, one structured provider call, exact fixture validation and real stage timings. The real provider check passed in 3,403 ms. All 69 backend tests including PostgreSQL pass; frontend lint/types, four fixture tests and production build pass. Persistent metrics, retention, offline invoice presentation and manual invoice browser submission remain outstanding. See docs/DOCUMENT.md.


## M5 metrics and offline invoice follow-up

Implemented typed content-free request/stage metrics, atomic writes, best-effort failure isolation, restricted RLS grants and a repeatable seven-day retention worker. Migration 0003 applied locally. All 75 backend tests including PostgreSQL pass; lint and mypy pass. Offline invoice fields and source inspection work with the API stopped; API restored afterward. Frontend lint, fixture tests and production build pass. Metrics activation remains blocked by automatic approval review: the persistent restricted login and its saved credential require explicit approval. No runtime login was created. See docs/TELEMETRY.md (TELEMETRY.md from docs) for privileges, retention limitations and activation steps.


## M5 activation after approval

On 29 October 2026, user approval enabled restricted metrics provisioning. API telemetry and the retention worker are active. Cleanup succeeded. A public invalid challenge returned 403 and persisted content-free metadata. A real internal invoice extraction matched every fixture field and persisted actual document/validation stages through the runtime login. No admission was claimed for that internal check. M5 implementation is complete; final regular-browser invoice submission remains pending because the embedded browser reports Turnstile 300030. See docs/m5-activation-result.json and docs/TELEMETRY.md.


## M5 acceptance closed

The user confirmed a successful live browser invoice extraction and supplied the validated DEMO-2026-001 fields, including EUR 357.00 total. This closes the remaining manual M5 acceptance check. Evidence provenance: user-provided UI output. M5 is complete; M6 broader evaluation, security and accessibility hardening remains outstanding. Embedded-browser Turnstile error 300030 remains a known limitation. See docs/m5-activation-result.json (m5-activation-result.json from docs).


## M6 hardening checkpoint

M6 remains in progress. Added a 40-case dataset (8 held out), resumable real evaluator, real Redis concurrency test and dependency failure matrix. 86 backend tests pass with PostgreSQL/Redis; frontend lint/types/tests/build pass. Production dependency audits report no known vulnerabilities. Mobile/keyboard checks found and fixed skip-link focus; added baseline CSP and verified offline hydration. Live M6 evaluation: 3 passed, 1 quota-blocked, 36 unattempted. Local example database password reuse is documented; no deployed-secret safety claim is made. Full accessibility, hosted scanning, representative latency/recall and real-browser CSP/citation checks remain. See docs/M6-REVIEW.md (M6-REVIEW.md from docs) for evidence, limits and continuation.
