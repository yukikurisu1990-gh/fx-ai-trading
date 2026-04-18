"""Exception hierarchy for fx_ai_trading (M4 / D3 §2).

BaseError
├── ContractViolationError      — Interface契約違反（実装者向け）
├── AccountTypeMismatch         — 起動時account_type不一致（6.18）
├── AccountTypeMismatchRuntime  — 発注直前account_type不一致（6.18 safe_stop発火）
├── SignalExpired               — TTL超過シグナル（6.15）
├── DeferExhausted              — Defer上限到達（6.15）
├── FeatureUnavailable          — 特徴量計算不能（D3 §2.2.1）
├── RepositoryError             — Repository書込/読取失敗
│   ├── CriticalWriteError      — Critical tier書込失敗（safe_stop発火）
│   └── ArchiveVerifyError      — Archive検証失敗（D5 §2.9.3）
└── ConfigError                 — 設定不正

実装層は ValueError / RuntimeError を直接 raise せず、
本階層の例外を使うこと（development_rules.md §5）。
"""

from __future__ import annotations


class BaseError(Exception):
    """Root of the fx_ai_trading exception hierarchy."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message


# ---------------------------------------------------------------------------
# Contract / Invariant violations
# ---------------------------------------------------------------------------


class ContractViolationError(BaseError):
    """Raised when an implementation violates an Interface contract (D3)."""


# ---------------------------------------------------------------------------
# Account type safety (6.18)
# ---------------------------------------------------------------------------


class AccountTypeMismatch(BaseError):  # noqa: N818
    """Startup-time account_type mismatch (6.18).

    Raised by AccountTypeAssertion.verify_at_startup().
    Triggers: Notifier critical + process exit.
    Name is per D3 §2.13.3 specification.
    """


class AccountTypeMismatchRuntime(BaseError):  # noqa: N818
    """Runtime account_type mismatch detected before place_order (6.18).

    Raised by Broker._verify_account_type_or_raise().
    Triggers: safe_stop(account_type_mismatch_runtime).
    Name is per D3 §2.13.3 specification.
    """


# ---------------------------------------------------------------------------
# Signal / execution timing (6.15)
# ---------------------------------------------------------------------------


class SignalExpired(BaseError):  # noqa: N818
    """Trading signal exceeded its TTL (6.15).

    Raised by ExecutionGate when now() - signal.created_at > signal_ttl_seconds.
    Name is per D3 §2.6.2 specification.
    """


class DeferExhausted(BaseError):  # noqa: N818
    """ExecutionGate defer retry limit reached (6.15).

    Raised when a deferred signal cannot be approved within the defer window.
    Name is per D3 §2.6.2 specification.
    """


# ---------------------------------------------------------------------------
# Feature generation (D3 §2.2.1)
# ---------------------------------------------------------------------------


class FeatureUnavailable(BaseError):  # noqa: N818
    """FeatureBuilder cannot compute features due to missing input data.

    Caller must mark the affected instrument as no_trade for this cycle.
    Name is per D3 §2.2.1 specification.
    """


# ---------------------------------------------------------------------------
# Persistence (D3 §2.9)
# ---------------------------------------------------------------------------


class RepositoryError(BaseError):
    """Base class for Repository-layer failures."""


class CriticalWriteError(RepositoryError):
    """Critical-tier table write failed after retries.

    Triggers: safe_stop(db.critical_write_failed).
    """


class ArchiveVerifyError(RepositoryError):
    """Archive verification failed; delete must not proceed (D5 §2.9.3)."""


# ---------------------------------------------------------------------------
# Configuration (6.19)
# ---------------------------------------------------------------------------


class ConfigError(BaseError):
    """Invalid or missing configuration value."""
