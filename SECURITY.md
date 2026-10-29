# Security

This repository is a portfolio application in development. Live AI, arbitrary uploads, URL fetching, shell tools, and administrative APIs are not enabled in the foundation.

Never submit real personal, confidential, or proprietary data. Never commit `.env` files or credentials. `.env.example` contains development-only values; these are not production passwords.

If a secret is exposed, revoke it at the provider first, replace it through secret settings, and then assess repository/history cleanup. Deleting a file is not key rotation.

Before public release, configure GitHub private vulnerability reporting and document its link here. Do not include exploit details or secrets in a public issue. See docs/THREAT-MODEL.md for control status and residual risks.
