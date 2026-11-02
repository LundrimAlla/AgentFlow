# Public offline portfolio

The first public release uses GitHub Pages at
https://LundrimAlla.github.io/AgentFlow/ with only the Next.js static export.
No backend, database, Gemini, Redis or Turnstile service is connected to this release.
The local protected live preview remains available in normal builds. M6 live
evaluation is still incomplete; this deployment does not claim production AI readiness.

Build from `frontend` with `OFFLINE_EXPORT=true` and `npm run build`, then run
`node scripts/verify-offline.mjs`. The build uses `/AgentFlow` as its base path,
trailing-slash routes and a `.next-demo` export directory. Only `.next-demo` is
published. Source fixtures outside `frontend` are included at build time.

The manually dispatched `Deploy offline demo` GitHub workflow runs lint, type checks,
fixture tests, build, export assertions and the production dependency audit before
publishing. Actions are pinned to immutable revisions. It deploys only from main.
Use a reviewed commit and dispatch this workflow again to update or roll back the site.
No hosting credentials or provider secrets are required by the workflow.

GitHub Pages is free for this public portfolio repository, subject to its service
limits. No paid plan, domain or AI billing is enabled by this deployment.

GitHub Pages does not support our custom Next.js response headers. The static HTML
uses a meta CSP with same-origin connections and no external scripts; inline Next.js
bootstrap scripts/styles remain allowed. Meta CSP cannot enforce frame-ancestors,
and this deployment does not claim the local server's full security-header coverage.
No personal information input or live request form is available in the public build.

References:
- https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
