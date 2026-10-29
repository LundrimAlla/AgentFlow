# Local live preview

Implemented 28 October 2026. This is M3 implementation evidence, not a public-release approval. Real-browser Turnstile success remains an acceptance check.

## Configure and run

1. Preserve existing `.env` files. On a fresh checkout copy root `.env.example` to `.env` and `frontend/.env.example` to `frontend/.env.local`.
2. Root `.env` needs `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-3.5-flash-lite`, `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`, `TURNSTILE_SECRET_KEY`, and a random `RATE_LIMIT_HMAC_SECRET` of at least 32 characters. Generate the latter using `python -c "import secrets; print(secrets.token_hex(32))"` in your own terminal and save it privately. No secret belongs in a `NEXT_PUBLIC_` variable.
3. Configure a real Managed Turnstile widget for `localhost` and `127.0.0.1`. Set `TURNSTILE_HOSTNAMES` and `CORS_ORIGINS` to the explicit allowed hostnames/origins. Set `NEXT_PUBLIC_TURNSTILE_SITE_KEY` to its public site key and `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000` in the frontend file. Test secret keys are rejected for live AI.
4. Confirm the Gemini project is on the intended Free tier. The app cannot verify billing configuration. It has no alternate model/provider or automatic paid fallback; changing the cloud account's billing can still change provider charges.
5. Set `LIVE_ENABLED=true`, then run `docker compose up -d --build api`. In `frontend`, run `npm run build` and `npm run start -- --hostname 127.0.0.1`. Avoid another API/frontend occupying the same ports.
6. Open `http://127.0.0.1:3000/live` in a regular browser. Complete verification, then send “What can AgentFlow do?” and, in a fresh conversation, “Draft a request for 12 chairs for fictional Example Ltd.” Check the answer, draft fields and measured workflow. Nothing is submitted to a company or stored as a lead.

Stop live access by setting `LIVE_ENABLED=false` and recreating the API. The live endpoint is then absent. `/demo` continues to work independently.

## Admission and resource ceilings

| Scope | Limit | Expiry after first reservation |
| --- | --- | --- |
| Challenge attempts per HMAC socket peer | 20 | 60 seconds |
| Global challenge attempts | 200 | 60 seconds |
| Admitted requests per peer | 5 / 15 / 20 | 60 / 3,600 / 86,400 seconds |
| Global admitted requests | 20 | 86,400 seconds |
| Global generation calls | 40 | 86,400 seconds |
| Global conservative token reservations | 200,000 | 86,400 seconds |

These are fixed-duration windows starting at first use, not calendar-day resets. A Lua script checks every counter in a reservation before incrementing any. TTLs are set only on new counters. Counters use the environment namespace and contain no prompts or raw addresses. Reservations are not refunded after errors or cancellation. Each generation reserves once before calling the provider. Input UTF-8 bytes plus 8,192 units of output/schema overhead form a conservative application estimate, not provider billing accounting. Output is capped at 2,048 model tokens per call. There are at most two calls per request and no retries. Ingestion/embedding has no runtime route yet and must acquire its own budget before M4 integration.

Redis and Turnstile outages fail closed. Turnstile success must be boolean true with the expected hostname and `chat` action. Cloudflare validates token expiry and single use. The API ignores forwarded IP/request-ID headers, uses HMAC socket-peer identifiers, and generates its own request IDs. Behind Docker/NAT, peers may share an address and therefore a quota. Before public deployment, establish a trusted edge/proxy configuration; never trust arbitrary forwarded headers.

Requests are limited to 20,000 bytes before JSON parsing, 2,000 characters per message and ten user turns. Uploads have a five-second deadline; service work has a sixty-second deadline, with bounded HTTP connect/read timeouts. The browser uses a seventy-second timeout and does not retry automatically. Failed requests preserve the draft and require fresh verification.

## Workflow and privacy

The router returns typed JSON. Lead extraction shares that call; its trace stage records local validation/selection, not an independent agent call. General AgentFlow questions use a second structured response call. Knowledge, document and unsupported intents use explicit capability messages. RAG and document stages are marked skipped and no live citations are invented. The safety trace measures admission; schema validation occurs before it. It is not a prompt-injection guarantee. Model instructions and structured output constrain behavior but cannot guarantee semantic accuracy.

The server grants models no tools, filesystem, SQL, email or arbitrary-network capabilities. Client history is untrusted. React displays escaped text. Conversations remain in page memory and are resent with subsequent turns; there is no application prompt/lead persistence or raw access logging. Model output can be incorrect. Provider processing has separate terms: [Google Gemini terms](https://ai.google.dev/gemini-api/terms), [Cloudflare verification](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/). Only synthetic content should be used. Public availability, especially regional paid-service requirements, must be reviewed against provider terms before deployment.

## Verification and remaining gates

- Deterministic backend tests cover routing, limits, challenge failures, Redis outage, provider quota/timeout/malformed output, escaped error envelopes and untrusted forwarded headers. They use an injected HTTP transport with fabricated credentials, never a runtime bypass.
- Real Upstash concurrent smoke: ten attempts against a three-slot counter admitted exactly three. Its isolated smoke key expires after sixty seconds.
- Real Gemini structured lead extraction passed through the adapter and generation reservation. Model and result are recorded without secrets in `live-integration-result.json`.
- Running container rejects an invalid Turnstile token with HTTP 403 and correct CORS. No generation occurs on this path.
- Embedded-browser challenge failed with 300030; app showed verification unavailable and kept Send disabled. [Cloudflare documents 300xxx as a generic challenge failure](https://developers.cloudflare.com/turnstile/troubleshooting/client-side-errors/error-codes/). Try a regular supported browser. Do not replace real protection with test keys to get a live response.
- Still required: successful real-browser submission and token replay check, complete UI success/error automation, prompt/adversarial evaluation, deployment CSP/HSTS/trusted proxy configuration, production telemetry, hosted CI and review. M4 live retrieval is not implemented.

Regenerate API artifacts from `backend` with `.venv/Scripts/python export_contract.py`; CI rejects generated contract drift. All values used for export are placeholders and no provider request is made.

## Customer-type correction and browser acceptance

The user confirmed live replies and a draft with company Example Mtd and quantity 25 in a regular browser. This is user-reported end-to-end evidence, not an automated replay test. The same check exposed an unsupported B2B inference.

Customer type is now validated deterministically after the router call. Only a standalone user field `customer type: B2B` or `customer type: B2C` supplies it. Company names, model guesses and assistant history cannot. The latest explicit declaration wins; `customer type: unknown` or `customer type: unspecified` clears it. Conflicting declarations in one message clear it. Other natural-language descriptions are intentionally not classified by this narrow validator. Other lead fields still use model extraction and require review.
