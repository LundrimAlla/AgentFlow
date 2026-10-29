# Foundation threat model

Assets: provider allowance, secrets, knowledge integrity, availability, visitor privacy, and public repository integrity.

| Boundary or threat | Required control | Current state |
| --- | --- | --- |
| Browser to API and expensive request abuse | Byte limit before parsing, strict schema, Turnstile, atomic budgets, deadlines | Implemented for opt-in live route; tests in test_live.py and real atomic Redis smoke. |
| Client history impersonates policy | Only alternating user/assistant messages; no system or tool role | Contract tests implemented. |
| Model or retrieved instructions gain capabilities | Allowlisted application workflows, no shell/filesystem/arbitrary HTTP tools | Gemini structured router/response integrated; no tools granted. |
| AI output executes browser content | React escaping, safe link policy, no raw generated HTML | Live and demo output use React-escaped text; no generated HTML rendering. |
| Prompt, credential or IP appears in telemetry | Metadata allowlist, error redaction, disabled raw access logging | Live errors are sanitized, quota identities are HMACed, traces contain allowlisted stages/timing. No prompt persistence or access logging. |
| Database exposed directly | Loopback-only development ports, RLS, separate deployed runtime role | Local binding and RLS migration implemented; deployment grants deferred. |
| Secrets committed | Ignore files, example placeholders, automated secret scan, GitHub protection | Local ignore and CI scan configured; repository settings require remote creation. |
| Dependency compromise | Locked versions, hashes, audits, CodeQL, Dependabot | Pipeline configured; hosted checks require GitHub repository. |
| Public admin privilege escalation | No admin endpoints in V1; later verified JWT plus admin allowlist | No admin routes. |

Residual risks: public hosting can still be abused; CORS and bot challenges are not DDoS guarantees. RLS does not constrain superusers. Free-tier availability is not guaranteed. A safety classifier cannot guarantee rejection of every prompt injection. Hosting/provider logs may have different retention from the application and must be reviewed before publication.

Deployment gate: add and test CSP against actual scripts/Turnstile, TLS-only HSTS at the public edge, trusted proxy configuration, least-privilege database grants, quota review and a successful real-browser challenge before exposing live AI.
