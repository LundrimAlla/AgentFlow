# M6 hardening checkpoint

Date: 29 October 2026. Status: **in progress; not release-approved**.

## Evidence and limits

| Area | Result | Evidence / limit |
| --- | --- | --- |
| Backend regression | 86 passed with real local PostgreSQL and Redis enabled | Includes disposable database tests; no live quota reset |
| Atomic quota concurrency | Pass | 40 parallel reservations admitted exactly 7; rejected reservations changed neither counter; TTL was not extended |
| Dependency failures | Pass | Verification, generation and embedding timeout/429/503 matrix; no retries, leaked details or fabricated answers |
| Privacy and retention | Pass | Typed metadata, outage isolation, restricted grants, repeatable expiry and cascade tests |
| Evaluation corpus | 40 cases authored and structurally checked | 15 knowledge, 10 unknown, 10 routing, 5 adversarial; 8 designated held-out |
| Live M6 evaluation | 3 completed, all 3 passed; 1 quota-blocked; 36 unattempted | 37 cases still need completion. Do not equate authored cases with passed cases |
| Backend dependency audit | No known vulnerabilities reported | `m6-python-audit.json`; locked runtime dependencies only |
| Frontend dependency audit | No known production vulnerabilities reported | `m6-npm-audit.json`; development dependencies excluded |
| Exact configured-secret check | Finding requires attention | `m6-secret-check.json`; local database password equals the documented development example |
| Security headers | Baseline CSP and other headers present | `m6-header-check.json`; not a strict nonce CSP |
| Frontend checks | Lint, TypeScript, four fixture tests and production build passed | Production build remains statically rendered |
| Hosted security checks | Not executed | CodeQL and gitleaks configured; no Git remote/hosted run or branch protection verified |

The secret check scans Git-visible files and the public static bundle for exact
configured secret values of at least eight characters. It is not a general secret
scanner. The match is the documented local-only operator password in `.env.example`;
both real environment files are ignored. Database ports remain loopback-only. Use
distinct managed credentials for deployment; do not treat the development password
as a deployable secret. No credentials were rotated during this checkpoint.

## Evaluation rubric and continuation

The versioned dataset is `demo-data/m6-evaluation.json`. The runner
`backend/evaluate_m6.py` uses real Gemini and the read-only PostgreSQL store. It
checks intended routing, expected source membership, expected answer terms, selected
lead fields, exact abstention for unknown questions, and quotation membership in
the published source snapshot. These checks do not substitute for human review of
semantic support. Expected source membership in the returned answer is not retrieval
recall@5. Retrieval recall, full routing/abstention rates, and a manual grounding
rubric still need final evidence. The runtime currently retrieves at most four chunks.

The runner records dataset hash, model, actual answers, per-case checks, timings and
safe dependency errors. It writes after each case and makes no automatic retries.
Operationally blocked cases are distinct from semantic failures. The current results
are in `m6-evaluation-result.json`: products, unknown CEO and AgentFlow capabilities
passed; the first adversarial case was blocked by `budget_exhausted`. No conclusion
about that adversarial case can be drawn. The earlier M4 four-case smoke report is
separate evidence and must not be counted as additional completed M6 cases.

After normal quota recovery, from `backend` run:

```powershell
.\.venv\Scripts\python.exe evaluate_m6.py --limit 4 --retry-blocked
```

That flag explicitly retries previously blocked cases and preserves their old evidence.
Subsequent batches can omit it. The runner skips already attempted cases by default.
Never raise limits, refund reservations or enable paid fallback to finish evaluation.
At the final read, the token-reservation window had 68,454 seconds left; that was a
point-in-time value, not a scheduled promise. No automatic future run was created.
Keep held-out cases separate when reporting; do not tune prompts on those results.

## Browser and accessibility checks

Verified in the embedded browser:

- Demo at 390px and 320px, live workspace and architecture at 320px: no horizontal
  document overflow in the inspected states. This is not a complete device matrix.
- Keyboard activation of the offline scenario and citation; citation focus moved
  to the source panel. Invoice prepared fields, source and reset work.
- Live textarea has an associated label; inspected buttons have visible names.
- Found and fixed the skip-link target: `main` now has `tabIndex={-1}`. Keyboard
  activation was verified to focus `main` after rebuilding.
- Invoice interaction still works under the new CSP; no browser errors were captured
  on that demo check. Temporary mobile viewport override was reset afterward.

Not yet verified: a full automated accessibility audit, screen-reader announcements,
contrast compliance across all states, every page at desktop/mobile/zoom combinations,
and live source inspection in a successful real browser request. The embedded browser
still encounters Turnstile 300030; do not bypass it. M5's user-confirmed browser invoice
success predates the CSP change, so a fresh real-browser verification check is needed.

## CSP decision

The policy restricts origins, frames, objects, base URLs and form destinations. It
allows the configured API origin and Cloudflare challenges. Production excludes
`unsafe-eval`; development permits it for framework tooling. Inline scripts/styles
remain allowed for the statically generated Next bootstrap. React escaping and the
absence of raw model HTML remain important controls; this CSP does not eliminate XSS.

This follows the installed Next.js no-nonce static-rendering guidance and Cloudflare's
[documented Turnstile script/frame allowances](https://developers.cloudflare.com/turnstile/reference/content-security-policy/).
A strict nonce policy would require a separate rendering/caching decision. TLS/HSTS,
deployment origins and real Turnstile compatibility are release checks, not proven by
the localhost header test.

## Reproduction and remaining gates

Backend: `python -m pytest -q` with `TEST_DATABASE_URL` pointing to local test-capable
PostgreSQL and `TEST_REDIS_PORT=6379`. Database tests create disposable databases;
Redis tests use UUID-scoped keys and remove only those keys. CI now provisions Redis
and enables that test rather than silently skipping it. Ruff and mypy passed.

Before M6 can close: complete and review all 40 evaluation cases under normal budgets;
measure retrieval recall and representative warm/cold latency; complete accessibility
and real-browser CSP/live-citation checks; run general secret scanning and hosted
CodeQL; resolve material findings and document the final release gate decision.
