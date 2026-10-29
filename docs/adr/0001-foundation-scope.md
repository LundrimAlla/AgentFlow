# 0001 Foundation scope and workflow boundaries

Status: Accepted for implementation following approval to start the implementation plan.

Use one frontend and one backend. Agents are typed modules coordinated by application code. Avoid a framework until a concrete requirement warrants one. Deterministic routing/validation does not require separate paid or quota-consuming model calls.

V1 excludes admin routes and authentication, matching HLD section 50. Operator-only ingestion will cover initial knowledge management. Admin authentication and authorization are delivered together in V1.1; hiding UI controls is never authorization.

Bundle Demo Mode in the frontend so a sleeping backend cannot prevent a portfolio demonstration. Recorded outputs and traces must be visibly labeled. Live errors must not silently substitute a canned answer for arbitrary input.

Ship a small AI evaluation suite in V1. This brings basic correctness evidence forward from the HLD's later benchmarking stage.

Do not choose vector dimensions before verifying the model. The baseline migration contains document metadata only. Authentication, runtime database roles, live API admission, streaming, and agents are deliberately absent from this first batch.

Tradeoff: this foundation does not yet satisfy the HLD's complete demo criteria. It establishes testable boundaries without pretending that unavailable integrations are functional.
