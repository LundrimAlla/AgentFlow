# AgentFlow

A portfolio application for grounded business AI workflows with synthetic data, explicit agent stages, and inspectable execution metadata.

**Current status: offline demo and protected local live preview.** `/demo` has three prepared scenarios, source excerpts and illustrative traces, with no keys required. `/live` adds Gemini intent routing, draft lead extraction and general AgentFlow answers behind Turnstile and atomic Upstash quotas. Live RAG, document extraction, authentication and public deployment remain later milestones. Successful real-browser Turnstile admission is still awaiting a user check; adapter and rejection tests pass.

## Run locally

Requirements: Node.js 22, Python 3.12, and Docker Desktop with Linux containers for database/Redis work. Commands below use PowerShell from the repository root.

```powershell
Copy-Item .env.example .env
docker compose up -d db redis
docker compose run --rm migrate
```

Start the backend in one terminal:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install --require-hashes -r backend/requirements-dev.lock
Set-Location backend
.venv/Scripts/python -m uvicorn app.main:app --reload --no-access-log --no-proxy-headers
```

Start the frontend in another terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open http://localhost:3000 for the application, http://localhost:8000/health for liveness, or http://localhost:8000/docs for development API documentation. The shell and health endpoint work even when Docker is stopped.

The local database binds only to `127.0.0.1:55432` to avoid conflicting with an existing PostgreSQL installation. Redis binds to `127.0.0.1:6379`. These services are for local development only.

Alternatively, `docker compose up --build -d api` runs the API in a container. Do not run it simultaneously with the local API on port 8000. `docker compose down` stops the local services while preserving database data. No automatic migration runs on API startup.

On Linux/macOS, use `backend/.venv/bin/python` (or `.venv/bin/python` inside backend), and `cp .env.example .env`. Application commands and the dependency locks are otherwise the same.

## Verify

For live setup, limits, data handling and troubleshooting, see [the live runbook](docs/LIVE.md). Copy `frontend/.env.example` to `frontend/.env.local` and supply only the public site key and API URL there. Keep all secret keys in root `.env`. Enable `LIVE_ENABLED=true` only after completing the root live settings. Rebuild/restart the frontend after changing public variables and recreate the API after changing server settings. The default example keeps live mode disabled.

From `backend`:

```powershell
.venv/Scripts/ruff check .
.venv/Scripts/ruff format --check .
.venv/Scripts/mypy app
.venv/Scripts/python -m pytest
.venv/Scripts/pip-audit -r requirements.lock
```

From `frontend`:

```powershell
npm test
npm run lint
npm run typecheck
npm run build
npm audit --omit=dev --audit-level=high
```

CI runs deterministic checks without provider credentials. GitHub-hosted CodeQL, secret scanning, and branch protection cannot be verified until a remote repository exists. Fixture tests run in CI and before each production build. Browser checks cover scenario selection, reset, citations, keyboard use, mobile layout, and operation with the API stopped.

## Dependency updates

Commit `frontend/package-lock.json`, `backend/requirements.lock`, and `backend/requirements-dev.lock`. Install Python dependencies with `--require-hashes`; do not hand-edit lockfiles. From backend, regenerate both locks with the installed pip-tools:

```powershell
.venv/Scripts/python -m piptools compile --generate-hashes --output-file requirements.lock pyproject.toml
.venv/Scripts/python -m piptools compile --extra dev --allow-unsafe --strip-extras --generate-hashes --output-file requirements-dev.lock pyproject.toml
```

After updates, run the full checks and the Linux container migration smoke test. Review vulnerability results before merging. CI action tags and Docker image tags must be pinned to reviewed immutable revisions before public deployment.

## Project guide

- [Implementation plan](IMPLEMENTATION_PLAN.md): milestones and acceptance gates.
- [Architecture](docs/ARCHITECTURE.md): boundaries and current implementation.
- [Architecture decision](docs/adr/0001-foundation-scope.md): scope choices and tradeoffs.
- [API contracts](docs/API.md): implemented endpoint and proposed contracts.
- [Threat model](docs/THREAT-MODEL.md): controls and remaining risks.
- [Requirements matrix](docs/REQUIREMENTS.md): HLD traceability.
- [Security policy](SECURITY.md): secrets and reporting guidance.

The original HLD.docx is preserved unchanged. License selection and public repository creation remain pending; no license is implied by this scaffold.

## Offline demo content

The canonical six Markdown sources and three JSON scenario fixtures live in `demo-data/`. Next.js includes them at build time in `/demo`; a content change requires a rebuild. Set the hosting build root to `frontend` while retaining access to the repository parent directory. No runtime backend or provider requests are needed for scenario interaction. The web frontend must still be reachable for the initial page load; this is not an installable offline PWA.

`npm test` verifies source provenance, fixture IDs, bounded content, and scenario-specific commitments. Missing source files or invalid citations fail the build. Scenario state is held in page memory only; switching or resetting clears the previous result and source. No prompts, requests, orders, or leads are submitted.

## M4 retrieval implementation

Versioned corpus ingestion, pgvector retrieval, verified quotation answers and source inspection are implemented. Six fictional documents are embedded locally; repeat ingestion makes zero provider calls. Activation still awaits approval to provision the dedicated read-only database login. Do not supply the operator database credentials to the API. See [retrieval setup and evidence](docs/RETRIEVAL.md).

## Approved retrieval activation

The user explicitly approved the local read-only login and credential storage. Provisioning completed; the runtime identity is agentflow_runtime, read-only transactions are enabled, and all six published chunks are visible. Retrieval is enabled in the running API. The published pricing source returned HTTP 200. The real products evaluation passed with source provenance validation. The remaining real evaluation cases are incomplete: the shared application budget has 197,838 of 200,000 units reserved, insufficient for another generation. No counters or limits were changed. See docs/retrieval-evaluation-result.json (or retrieval-evaluation-result.json from this directory) for the recorded reset time. M4 runtime activation is complete; full real evaluation acceptance remains pending.
