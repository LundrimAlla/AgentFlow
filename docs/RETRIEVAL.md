# M4: grounded retrieval

## Architecture

Six allowlisted fictional Markdown sources are normalized to LF and split into deterministic chunks of at most 1,200 characters. IDs incorporate source content hashes, offsets and chunker version. The corpus hash also includes embedding model, dimension and prompt format. Gemini Embedding 2 produces 768-dimensional vectors; all values must be finite, nonzero and correctly sized before normalization.

The operator CLI computes embeddings before starting its publication transaction. The transaction acquires an advisory lock, rechecks idempotence, inserts the entire snapshot and switches the singleton active pointer. Any SQL failure rolls back all inserts and the pointer together. Provider failure occurs before publication. Reingesting the same snapshot performs zero embedding calls. Concurrent identical publications produce one snapshot; concurrent preparation can still consume separately reserved provider calls. An intentionally reingested older snapshot can reactivate that version. Existing published snapshots remain available so citations survive updates.

The runtime login belongs only to the read-only `agentflow_reader` group. It is not an administrator, has no bypass-RLS privilege and defaults to read-only transactions. SELECT policies expose published snapshots only. It has no table mutation grants. The earlier `knowledge_documents` baseline table is preserved but is not used by the corpus pipeline. Ingestion uses the separate operator URL, which is never passed to the API container.

After normal Turnstile/request admission, a knowledge question reserves an embedding call and queries the active snapshot using exact pgvector cosine search. The top four chunks above a 0.35 similarity floor are candidates, not proof that the question is answerable. This tiny corpus does not need an approximate index. Retrieval currently embeds the latest question as written; self-contained questions work best. Generation sees conversation context but has no tools.

The model selects up to three exact quotations. The server rejects unknown chunk IDs, altered quotations and duplicates. Supported answers are assembled from those verified excerpts and numbered citations, not free-form model paraphrases. Empty retrieval or rejected evidence produces an abstention without fabricated citations. This constrains factual invention; it does not prove that every selected passage is relevant or immune to misleading omission. Semantic relevance and prompt-injection resistance still require evaluation.

`GET /api/sources/{corpus_id}/{source_id}` exposes only published fictional source snapshots with strict identifier validation. Citations carry corpus/chunk IDs and exact excerpt line numbers. The frontend renders all content as escaped text and supports opening a source with keyboard focus, loading, timeout and error states.

## Local setup

Run from the project root, preserving existing credentials:

```powershell
docker compose run --rm --build migrate
Set-Location backend
.venv/Scripts/python provision_reader.py
.venv/Scripts/python -m app.ingest --dry-run
.venv/Scripts/python -m app.ingest
```

`provision_reader.py` is deliberately restricted to the local `agentflow` database. It creates the persistent `agentflow_runtime` login and saves a generated secret in ignored root `.env`; review/authorize that access grant before running. The helper prints no credentials. After successful ingestion, set `RAG_ENABLED=true` in root `.env`, then recreate the API with `docker compose up -d --build api`. Build/restart the frontend using the README commands.

For Windows host execution, the ingestion/evaluation CLIs select the event loop required by psycopg. Prefer the documented Linux API container. Use `127.0.0.1` for local database connection tests; this machine's synchronous `localhost` connection path stalled during testing. Database operations have connection and statement deadlines.

No application counter is cleared or bypassed for ingestion/evaluation. Embeddings share the global 200,000-unit daily reservation pool with generation and have a 60-call global ceiling, divided into 32 ingestion and 28 query calls. All windows expire after 86,400 seconds from first reservation. Failed attempts are not refunded. No automatic retries or paid fallback are implemented. Exact provider free-tier availability/quotas are independent of these application ceilings.

## Verification

- `python -m pytest`: deterministic provider/grounding tests; supply `TEST_DATABASE_URL` for real database tests. The test identity needs CREATE DATABASE permission to create and remove a uniquely named disposable database. Tests do not modify the active development corpus.
- Database tests cover migration idempotence, zero-call reingestion, provider failure, SQL rollback, concurrent publication, retained historical sources and read-only/RLS restrictions.
- `python evaluate_retrieval.py`: explicit real-provider evaluation of `demo-data/retrieval-evaluation.json`; consumes normal provider reservations. Requires activated read-only retrieval. Records citation provenance and product/pricing/unknown/injection cases in `docs/retrieval-evaluation-result.json`. It calls the internal workflow, not a CAPTCHA-bypassing HTTP route.
- Frontend: lint, typecheck, fixture tests and production build. Real-browser challenge/submission remains a separate smoke check; use a regular browser if the embedded browser is rejected by Cloudflare.

Local progress: six documents/six chunks published; immediate reingestion reused the corpus with zero embedding calls. 57 backend tests passed with a real isolated PostgreSQL database. Activation and real evaluation depend on approving/provisioning the dedicated read-only login; do not substitute administrator credentials in the API.

Provider references: [Gemini embeddings and task formatting](https://ai.google.dev/gemini-api/docs/embeddings), [pgvector cosine retrieval](https://github.com/pgvector/pgvector).

## Approved retrieval activation

The user explicitly approved the local read-only login and credential storage. Provisioning completed; the runtime identity is agentflow_runtime, read-only transactions are enabled, and all six published chunks are visible. Retrieval is enabled in the running API. The published pricing source returned HTTP 200. The real products evaluation passed with source provenance validation. The remaining real evaluation cases are incomplete: the shared application budget has 197,838 of 200,000 units reserved, insufficient for another generation. No counters or limits were changed. See docs/retrieval-evaluation-result.json (or retrieval-evaluation-result.json from this directory) for the recorded reset time. M4 runtime activation is complete; full real evaluation acceptance remains pending.
