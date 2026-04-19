"""Operational concerns (process orchestration, service-mode abstraction).

Modules in this package implement the connection points between the
application core and the OS / orchestrator layer (M22 process manager,
M22 two-factor authenticator, M24 service mode). They are intentionally
thin wrappers — domain logic stays in `domain/` and `usecases/`.
"""
