# Execution metrics and retention

Implemented and activated 29 October 2026. Local migration `0003` is applied.
After the user's approval, the restricted `agentflow_telemetry` login was created
and its generated password saved in the ignored root `.env`. The API now runs with
telemetry enabled and the retention worker is running. Cleanup startup succeeded.

## Data boundary

`execution_metrics` contains a server-generated request UUID, server UTC timestamp,
workflow (`chat` or `document`), HTTP status, elapsed milliseconds and nullable
input/output token counts. Counts remain null because the current adapter does not
collect trustworthy usage values. Conservative budget reservations are not token usage.
`execution_stages` contains only request UUID, allowlisted stage name, status and duration.

No prompts, answers, lead or invoice fields, source text, IP addresses, session hashes,
credentials or exception strings are stored. The model never supplies metric fields.
There is no public metrics read endpoint. The existing knowledge-reader identity is
unchanged, and the API never receives the operator database credential.

Only parsed chat/document requests entering the workflow are recorded, including
admission failures. Parsing/body-limit rejections, source reads and health probes are
not recorded. Failed workflows record their HTTP status without invented stage timings;
partial failed-stage traces are not currently retained. Durations exclude the metrics
write itself. Successful workflow traces preserve actual stage status and timings.

Writes are atomic across the request and its stage records. They are best-effort,
bounded to 750 ms outside the workflow deadline; outages do not invalidate an answer.
A dropped write logs only `metrics_write_unavailable`. There is no retry queue and
metrics can be lost during outages or cancellation. The overall response may take up
to 750 ms beyond the workflow deadline for this operation.

## Privileges and retention

The `agentflow_metrics` NOLOGIN group can insert metadata, read only timestamps of
expired records, and delete only rows older than seven days. RLS is enabled and forced.
It cannot set timestamps, update records, read other metadata columns or company
documents. Stage rows are deleted through their parent foreign-key cascade. The login
will be non-superuser, without role/database creation or RLS bypass, limited to five
connections. API and retention worker share this narrowly scoped identity.

The retention service deletes expired rows at startup and every 60 seconds. Expected
database retention is seven days plus at most one cleanup interval during healthy
operation. During downtime, expired rows remain until the worker recovers; do not
claim an absolute seven-day deletion guarantee. The worker logs success/deleted count
or a generic failure, never a connection string or exception. Monitor these outcomes
operationally. Container log rotation is a separate deployment concern.

After explicit local provisioning approval:

1. From `backend`, run `.venv/Scripts/python provision_metrics.py`. It saves the
   generated credential locally and enables telemetry. It accepts only the local
   AgentFlow database.
2. From the project root, run
   `docker compose --profile telemetry up -d --build api retention`.
3. Verify `docker compose logs --tail 5 retention` reports cleanup success.
4. For a one-off repeatable cleanup, run from `backend`
   `.venv/Scripts/python -m app.telemetry --once`.

For other environments, provision equivalent restricted grants through the approved
secret manager; do not use the local helper or the operator identity in the API.
Disabling telemetry requires `TELEMETRY_ENABLED=false` and recreating the API. Keep
the retention worker running to expire existing data. Reverting application code does
not require dropping these additive tables.

## Evidence

75 backend tests passed with local PostgreSQL integration enabled. Tests cover
payload exclusion, null usage, successful chat/document traces, failed admission,
telemetry exceptions/timeouts, atomic rollback, RLS/grant restrictions, preservation
of recent rows, removal of expired rows and their stages, and repeatable cleanup.
The database checks use disposable databases and restricted role execution, not the
production runtime login. Runtime activation was subsequently verified: a public
invalid-challenge request returned 403 and persisted safe metadata; one real internal
invoice extraction persisted its actual document and validation stages. The internal
check did not run admission and did not record a fabricated safety stage. Runtime role
flags confirm no superuser, database/role creation or RLS bypass. See m5-activation-result.json.
