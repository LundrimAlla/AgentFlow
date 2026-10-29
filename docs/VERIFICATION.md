# Foundation verification

Run date: 27 October 2026. This records local evidence, not a production readiness claim.

| Check | Result |
| --- | --- |
| Backend Ruff lint and formatting | Passed |
| Backend strict mypy | Passed |
| Backend pytest with real PostgreSQL | 8 passed |
| Migration applied twice | Passed; second upgrade is a no-op |
| Restricted role reading knowledge table | Denied by RLS, verified inside rollback-only integration test |
| Backend Docker image build | Passed on Linux with hash-checked runtime dependencies |
| Python development lock installation | Passed with --require-hashes on Windows |
| Linux development lock and unit tests | Hash-checked install passed; 7 tests passed, database test skipped because no database URL was supplied in this container run |
| Python runtime dependency audit | No known vulnerabilities found by pip-audit |
| Compose migration command | Passed |
| Container health HTTP request | Healthy, version 0.1.0 |
| Redis readiness | Checked through Compose health check |
| Frontend ESLint and TypeScript | Passed |
| Frontend production build | Passed; home, architecture, workspace pages prerendered |
| Frontend clean lockfile installation | Passed with npm ci --ignore-scripts; lint and types passed afterward |
| Browser smoke check | Homepage layout inspected; workspace and architecture navigation passed |
| npm installation vulnerability report | Zero vulnerabilities reported |
| Secret-file ignore checks | .env, virtual environment, and node_modules excluded |

An existing local PostgreSQL service occupied port 5432. AgentFlow binds its separate development database to 127.0.0.1:55432. Existing services were left unchanged.

Tooling follow-ups: Next.js's current lint plugins declare ESLint 9 compatibility, so ESLint 9.39.5 is pinned despite its upstream deprecation notice. Upgrade the lint stack together when those plugins support the current major. Starlette's test client emits an httpx deprecation notice; tests currently pass. Address this test-client migration before expanding the HTTP suite.

Pending external evidence: GitHub-hosted CI/CodeQL/secret-scanning runs, branch protection, live Gemini generation and embeddings, model dimensions/free allowances, deployed security headers, and cloud smoke tests. No remote repository, PR, deployment, or provider configuration has been created. M0 remains incomplete until the provider spike is performed.

## M2 offline scenario slice

Implemented three preset scenarios and six fictional company documents. Fixture tests (4 cases), ESLint, TypeScript, and production static generation pass. With the API container stopped, all three scenarios produced their prepared answers and illustrative workflows. Source buttons opened canonical documents; keyboard activation and source focus, quote data, reset, switching scenarios, and refresh clearing state were checked in the browser. Mobile layouts were inspected at 390 px and 320 px; a navigation overflow and a run/reset focus issue were fixed.

The API is restored after outage testing. This is backend-independent Demo Mode, not an offline PWA. Initial loading still needs the frontend host. Missing source files and mismatched citations fail the build; defensive empty-scenario and missing-source messages are present but were not injected into the production bundle during UI verification. No live RAG or LLM calls ran. The sample invoice workflow and live-error fallback remain later work.

## M3 local protected live preview — 28 October 2026

- Backend Ruff lint/format and strict mypy passed; 27 deterministic tests passed, one unchanged database integration test skipped because TEST_DATABASE_URL was not supplied in this run.
- Frontend ESLint, TypeScript, four fixture tests and production build passed with /live included.
- Hash-locked runtime and development dependencies regenerated; Linux API image rebuilt successfully.
- Real Upstash concurrency smoke admitted exactly three of ten requests under a three-slot quota; real budgeted Gemini structured lead extraction passed. See live-integration-result.json.
- Running API health returned 200; invalid Turnstile returned 403 verification_failed and the correct explicit CORS origin.
- Live UI inspected on desktop and 320 px viewport without document overflow. Embedded browser challenge returned Cloudflare 300030; failure message appeared and Send stayed disabled. No successful real-browser submission is claimed. Regular-browser user check remains required.
- No deployment, remote repository or public exposure was performed. Full deployment and adversarial evaluation gates remain open; see LIVE.md.

Final M3 checks: Python runtime audit and npm production audit reported no known vulnerabilities. Exact-value checks for four configured server secrets found no matches in repository-visible source or built frontend JavaScript/HTML (88 candidate files). This supplements, but does not replace, hosted secret scanning.

## Customer-type regression and M4 preparation

The user confirmed real-browser live responses and correct company/quantity extraction. Server validation now removes unsupported B2B inference; the regression test deliberately simulates that provider error. Explicit declarations, corrections, conflicts and assistant-history isolation are tested.

M4 preparation adds allowlisted source loading and deterministic bounded chunks with exact text offsets, line locations, hashes and stable IDs. Tests cover all six sources, exact reconstruction, line-ending stability, long paragraphs and invalid/missing sources. Embedding ingestion, transactional activation, retrieval and live citations remain unimplemented.

Validation: 40 tests passed; the existing database integration test was skipped without TEST_DATABASE_URL. Ruff and strict mypy passed. The local API image was rebuilt and restarted. No live model requests were needed for these regressions.

## M4 implementation checkpoint

57 backend tests passed with real PostgreSQL, including an isolated disposable database for ingestion rollback, concurrency, historical sources and RLS/read-only checks. Six real Gemini embeddings were published as one corpus; the repeat ingestion made zero embedding calls. Frontend fixture tests and production build passed. Backend lint/type checks passed. The source/citation UI and generated OpenAPI contract are updated.

Automatic approval review blocked creation of the persistent read-only runtime login and saving its credentials. User approval is pending; runtime activation and real retrieval evaluation are not yet claimed. No administrator identity was substituted into the API. See RETRIEVAL.md.

## Reported 504 timeout follow-up

Reproduced a Gemini provider timeout inside the running API at about 13.2 seconds with the old 12-second read limit. A final budgeted synthetic router check passed in 14.6 seconds with the new 25-second provider limit. The workflow is capped at 60 seconds, the upload at 5 seconds, and the browser at 70 seconds. No automatic retries or quota increases were added. Safe failure logs include only request ID, allowlisted error code and elapsed time; the UI displays a validated reference ID and specific timeout category.

57 tests passed, two database tests skipped in this targeted run; cancellation and dedicated provider timeout regression tests passed. Backend lint/types and frontend lint/build/fixture tests passed. Both local services restarted successfully. Retrieval remains disabled pending the previously requested approval for its read-only login. Browser challenge warnings were not reproduced as a backend failure; no CSP or verification protection was relaxed.

## Approved retrieval activation

The user explicitly approved the local read-only login and credential storage. Provisioning completed; the runtime identity is agentflow_runtime, read-only transactions are enabled, and all six published chunks are visible. Retrieval is enabled in the running API. The published pricing source returned HTTP 200. The real products evaluation passed with source provenance validation. The remaining real evaluation cases are incomplete: the shared application budget has 197,838 of 200,000 units reserved, insufficient for another generation. No counters or limits were changed. See docs/retrieval-evaluation-result.json (or retrieval-evaluation-result.json from this directory) for the recorded reset time. M4 runtime activation is complete; full real evaluation acceptance remains pending.


## 29 October 2026 follow-up

Real retrieval evaluation: 4/4 pass after natural quota expiry. Real invoice extraction: exact fixture pass, 3,403 ms. Backend: 69 passed with TEST_DATABASE_URL configured locally; without database configuration, 67 pass and 2 skip. Ruff and mypy pass. Frontend lint/types, 4 fixture tests and production build pass. API and frontend rebuilt and restarted locally. Browser inspection confirms the invoice action renders and is disabled before verification; no real invoice HTTP submission was performed through CAPTCHA. See DOCUMENT.md for remaining M5 work.


## M5 metrics and offline invoice follow-up

Implemented typed content-free request/stage metrics, atomic writes, best-effort failure isolation, restricted RLS grants and a repeatable seven-day retention worker. Migration 0003 applied locally. All 75 backend tests including PostgreSQL pass; lint and mypy pass. Offline invoice fields and source inspection work with the API stopped; API restored afterward. Frontend lint, fixture tests and production build pass. Metrics activation remains blocked by automatic approval review: the persistent restricted login and its saved credential require explicit approval. No runtime login was created. See docs/TELEMETRY.md (TELEMETRY.md from docs) for privileges, retention limitations and activation steps.


## M5 activation after approval

On 29 October 2026, user approval enabled restricted metrics provisioning. API telemetry and the retention worker are active. Cleanup succeeded. A public invalid challenge returned 403 and persisted content-free metadata. A real internal invoice extraction matched every fixture field and persisted actual document/validation stages through the runtime login. No admission was claimed for that internal check. M5 implementation is complete; final regular-browser invoice submission remains pending because the embedded browser reports Turnstile 300030. See docs/m5-activation-result.json and docs/TELEMETRY.md.


## M5 acceptance closed

The user confirmed a successful live browser invoice extraction and supplied the validated DEMO-2026-001 fields, including EUR 357.00 total. This closes the remaining manual M5 acceptance check. Evidence provenance: user-provided UI output. M5 is complete; M6 broader evaluation, security and accessibility hardening remains outstanding. Embedded-browser Turnstile error 300030 remains a known limitation. See docs/m5-activation-result.json (m5-activation-result.json from docs).


## M6 hardening checkpoint

M6 remains in progress. Added a 40-case dataset (8 held out), resumable real evaluator, real Redis concurrency test and dependency failure matrix. 86 backend tests pass with PostgreSQL/Redis; frontend lint/types/tests/build pass. Production dependency audits report no known vulnerabilities. Mobile/keyboard checks found and fixed skip-link focus; added baseline CSP and verified offline hydration. Live M6 evaluation: 3 passed, 1 quota-blocked, 36 unattempted. Local example database password reuse is documented; no deployed-secret safety claim is made. Full accessibility, hosted scanning, representative latency/recall and real-browser CSP/citation checks remain. See docs/M6-REVIEW.md (M6-REVIEW.md from docs) for evidence, limits and continuation.
