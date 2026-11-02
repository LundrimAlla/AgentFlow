# Public offline release security review

Date: 2 November 2026. Scope: GitHub repository, reachable local Git history,
published HTML and its ten directly referenced script/style assets, static export,
repository permissions and local service bindings. This is a targeted review, not
a penetration-test certification or a guarantee against every attack.

## Verified exposure

- The repository is intentionally public. Source and fictional fixtures can be
  downloaded and copied. Downloads do not grant write access or execute code on
  the owner's machine. Only LundrimAlla currently has repository write access.
- The website is static. No public FastAPI, database, Gemini, Upstash or Turnstile
  connection is configured. The live route contains an explanatory page, not a form.
- Published `.env`, `.git/config`, `HLD.docx` and `api/chat` paths returned 404.
  Both real environment files and HLD.docx are Git-ignored.
- Exact configured provider secrets were absent from inspected public responses
  and tracked history. General Gitleaks scans of history and the exported bundle
  also found no leaks. See the accompanying redacted JSON evidence.
- HTTPS is enforced; observed HSTS was max-age=31556952. Local API, Postgres and
  Redis Docker ports are bound to 127.0.0.1, not all network interfaces. This does
  not audit unrelated software, tunnels, router configuration or the entire PC.
- GitHub secret scanning and push protection are enabled. Open GitHub secret and
  CodeQL findings were zero at inspection. Workflow defaults are read-only and
  workflow PR approval permission is disabled. Pages deployment is main-only.

## Remediation

The local operator database URL matched the public development example. Its
password was replaced with a cryptographically random value, saved only in ignored
`.env`, and a fresh database connection succeeded. The example remains publicly
available but its password is no longer the local operator credential. The API's
separate reader/metrics credentials were not changed. No provider-key leak was found.

All CI/CodeQL action references now use resolved immutable commit hashes. Checkout
credentials are not persisted for subsequent build/test steps. Pages already used
pinned actions and separate minimal deploy permissions. Weekly Dependabot updates
include GitHub Actions; updates still require review and passing checks.

Main-branch hardening is completed through GitHub settings after this patch's push:
require a pull request and successful backend, frontend, secrets and both CodeQL
checks, require the branch to be current, and prohibit force pushes/deletion.
Administrator enforcement is intended; zero human approvals permits the sole owner
to merge after checks and is not a claim of independent peer review.

## Remaining limits

- The complete npm audit reports 16 moderate affected development-tool packages
  associated with minimatch glob amplification. The production-only audit reports
  zero vulnerabilities. They are lint/build dependencies, not shipped runtime
  packages. Do not run forced audit fixes: the offered changes include incompatible
  downgrades. Track compatible upstream fixes and review untrusted build changes.
- The token could not read Dependabot alert details (HTTP 403); the direct npm
  audit is separate evidence. Account two-factor status was unavailable through
  the API. The owner should verify a passkey or 2FA and secure recovery codes.
- GitHub Pages cannot configure our custom response headers. The meta CSP permits
  same-origin connections and inline Next bootstrap scripts/styles. It cannot
  enforce frame-ancestors; X-Frame-Options and X-Content-Type-Options were absent.
  No sensitive forms or external actions exist in this release. Stronger headers
  would require a hosting/proxy change; none was made.
- A compromised owner account or authorized malicious code change remains a risk.
  Public code cannot be made impossible to copy. Making the repository private
  is a separate product/hosting decision and was not performed.
- The live AI release remains gated by M6 evaluation and public-live verification.

Evidence: `public-exposure-audit.json`, `public-repository-security.json` (initial
settings snapshot), `public-history-secret-scan.json`, `public-bundle-secret-scan.json`,
`public-npm-audit.json`, and `public-npm-production-audit.json`.
