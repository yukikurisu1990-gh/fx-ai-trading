"""Credential / environment-variable guard (plan §5 step 2).

Wraps ``os.environ`` lookups so any access to a credential-pattern key fails
closed — including the *presence* check via ``__contains__`` (Amendment 1 §3
corrected scope: presence-check itself is blocked). Non-credential keys pass
through unchanged so the inner process can still read benign vars such as
``PATH``.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final

from . import GuardViolationError

# Credential-pattern regex (plan §4 / §5; Amendment 1 §3).
_CREDENTIAL_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?i)(OANDA|TOKEN|SECRET|KEY|PASSWORD|CREDENTIAL|AWS|GCP|AZURE)"
)

_original_getitem = None
_original_get = None
_original_contains = None


def _check_key(key: object) -> None:
    if isinstance(key, str) and _CREDENTIAL_PATTERN.search(key):
        raise GuardViolationError(
            f"credentials guard: access to credential-pattern env var "
            f"'{key}' is prohibited (plan §5 step 2; Amendment 1 §3)."
        )


def install() -> None:
    """Wrap ``os.environ`` getitem/get/contains with credential blocking."""
    global _original_getitem, _original_get, _original_contains
    if _original_getitem is not None:
        return

    env_type = type(os.environ)
    _original_getitem = env_type.__getitem__
    _original_get = env_type.get
    _original_contains = env_type.__contains__

    def guarded_getitem(self, key):
        _check_key(key)
        return _original_getitem(self, key)

    def guarded_get(self, key, default=None):
        _check_key(key)
        return _original_get(self, key, default)

    def guarded_contains(self, key):
        _check_key(key)
        return _original_contains(self, key)

    env_type.__getitem__ = guarded_getitem
    env_type.get = guarded_get
    env_type.__contains__ = guarded_contains


def uninstall() -> None:
    """Restore the original ``os.environ`` lookup methods."""
    global _original_getitem, _original_get, _original_contains
    if _original_getitem is None:
        return
    env_type = type(os.environ)
    env_type.__getitem__ = _original_getitem
    env_type.get = _original_get
    env_type.__contains__ = _original_contains
    _original_getitem = None
    _original_get = None
    _original_contains = None


@contextmanager
def activate() -> Iterator[None]:
    """Context manager that installs the credential guard for its duration."""
    install()
    try:
        yield
    finally:
        uninstall()
