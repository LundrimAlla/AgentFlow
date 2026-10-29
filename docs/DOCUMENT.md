# Sample invoice extraction

Implemented 29 October 2026 as the first M5 slice. This is extraction from one
repository-owned plain-text invoice, not OCR, invoice generation or arbitrary uploads.

Open `/live`, complete verification, then choose **Extract sample invoice**.
The action preserves the conversation and its draft, sends only the fixed sample
to Gemini, and displays the extracted fields and actual server stage timings.
No payment, order, message or document is created. Amounts are synthetic test prices,
not prices supported by the company knowledge corpus.

`POST /api/demo/document` accepts only `sample_id: "invoice-001"` and a
`turnstile_token`. It uses the existing `chat` verification action and shares the
chat attempt, request, generation and token budgets. No automatic retries occur.
Live-disabled deployments do not register the endpoint. The request body is bounded
to 20 KB; processing uses the existing total and provider deadlines.

The server reads `backend/app/samples/invoice-001.txt` only after admission.
No request-derived value becomes a path. The strict ID schema rejects invalid IDs
before file reads or service calls. Exactly one structured generation extracts the
invoice. Monetary amounts are integer euro cents. All extracted fields must match
the reviewed `invoice-001.expected.json` fixture, including item order. A mismatch
returns a safe error; the expected fixture is never substituted as a live result.
This exact-field check establishes correctness only for this fixed sample.

Results remain in browser memory. The endpoint does not write invoice content to a
database or application logs. Error logs contain only request ID, error code and
elapsed milliseconds. Provider data handling is disclosed on the live page.

## Verification

- 69 backend tests passed, including real local PostgreSQL integration tests.
- Invoice tests cover exact fields, invalid IDs before file reads, rejected verification,
  exhausted shared budgets, mismatched fields, bounded bodies and provider timeout.
- Frontend lint, type checking, four fixture tests and production build passed.
- Browser inspection confirmed the new control renders and remains disabled before verification.
- `backend/evaluate_document.py` passed one real Gemini extraction in 3,403 ms.
  It is an operator-only check using normal provider reservations; HTTP admission
  is tested separately. See `document-evaluation-result.json`.
- A real browser submission through Turnstile for this new invoice action remains
  a manual acceptance check. No CAPTCHA was bypassed during browser inspection.

Run the deterministic suite from `backend` with `.venv/Scripts/python -m pytest -q`.
With provider configuration and budget available, run
`.venv/Scripts/python evaluate_document.py` once for the real provider check.

## M5 follow-up

The offline invoice walkthrough is now available at `/demo`, using the same source
and expected fixture bundled at build time. Its prepared result and illustrative
stages are labeled explicitly. Source inspection, keyboard activation and reset were
verified with the API stopped; the API was restored afterward.

Execution metrics and seven-day cleanup are implemented, activated and covered by the
75-test backend suite. The runtime login persisted both rejected-request metadata and
successful internal real-extraction stages; see TELEMETRY.md. The user subsequently
confirmed successful live browser extraction of DEMO-2026-001, providing the validated
fields: 12 brackets, 5 plates, EUR 300.00 subtotal, EUR 57.00 tax and EUR 357.00 total.
This user-provided UI evidence closes the remaining M5 browser acceptance check.
The embedded-browser Turnstile 300030 limitation remains documented; it is not resolved
by the successful user test. M5 is complete; broader M6 hardening remains outstanding.
