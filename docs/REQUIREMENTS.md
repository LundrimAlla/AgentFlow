# Requirements and evidence

| HLD sections | Requirement | Foundation evidence | Remaining work |
| --- | --- | --- | --- |
| 6–8, 38 | Frontend/backend structure | frontend/app, backend/app | Business workflows |
| 9–10, 21 | Typed agent contracts and input limits | schemas/chat.py, tests/test_foundation.py | M3 implemented in app/live.py, app/transport.py and tests/test_live.py; broader evaluation remains |
| 13, 30 | Database and RLS | migrations/versions/0001_foundation.py | Chunks, runtime grants, metrics |
| 16, 36–37 | Secrets and CI | .gitignore, CI, CodeQL, Dependabot | GitHub remote/settings and hosted check results |
| 24 | Explicit CORS origins | core/config.py and CORS tests | Deployment origin configuration |
| 28–29, 50 | Admin | ADR 0001 | Explicitly deferred to V1.1 |
| 33, 44 | Offline fallback | frontend/app/demo, demo-data, frontend/tests/demo.test.mjs | Live page links to demo on quota/outage; complete UI automation remains |
| 41 | Safe health endpoint | main.py and health test | Deployed smoke test |
| 49–51 | Complete public demo | Implementation plan | M2–M7 |

Provider spike: generation with gemini-3.5-flash-lite and 768-dimensional gemini-embedding-2 succeeded; user confirmed Free tier. Upstash read/write and atomic reservations passed. See smoke JSON records and LIVE.md. Full browser Turnstile success, exact project quota review and deployment region/provider-terms review remain acceptance gates.
