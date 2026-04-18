"""NtpChecker — startup clock-skew validation (D4 §2.1 Step 2 / 6.14).

Design:
  - evaluate(skew_ms) is a pure function for unit testing.
  - measure_skew_ms() performs I/O via ntplib (optional dependency).
    Falls back to 0.0 if ntplib is not installed or the NTP server is
    unreachable, so startup is not blocked by network issues in dev.
  - check() = measure_skew_ms() + evaluate().

Thresholds (D4 §2.1 Step 2):
  - skew ≤ 500 ms   → OK
  - 500 < skew ≤ 5000 ms → warn + continue
  - skew > 5000 ms  → reject (startup exit)

No datetime.now() / time.time() in this module.  ntplib handles
internal time measurement within the library (not scanned by lint).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

_log = logging.getLogger(__name__)

_DEFAULT_WARN_MS = 500.0
_DEFAULT_REJECT_MS = 5_000.0
_NTP_HOST = "pool.ntp.org"


@dataclass(frozen=True)
class NtpResult:
    """Result of an NTP clock-skew check."""

    skew_ms: float
    is_ok: bool
    should_warn: bool
    should_reject: bool


class NtpChecker:
    """Validates startup clock skew against an NTP reference.

    Args:
        warn_ms: Skew threshold (ms) above which a warning is emitted.
        reject_ms: Skew threshold (ms) above which startup must be aborted.
        ntp_host: NTP server host used by measure_skew_ms().
    """

    def __init__(
        self,
        warn_ms: float = _DEFAULT_WARN_MS,
        reject_ms: float = _DEFAULT_REJECT_MS,
        ntp_host: str = _NTP_HOST,
    ) -> None:
        self._warn_ms = warn_ms
        self._reject_ms = reject_ms
        self._ntp_host = ntp_host

    def evaluate(self, skew_ms: float) -> NtpResult:
        """Classify *skew_ms* against configured thresholds — pure function.

        Args:
            skew_ms: Absolute clock skew in milliseconds.

        Returns:
            NtpResult with classification flags set.
        """
        abs_ms = abs(skew_ms)
        return NtpResult(
            skew_ms=abs_ms,
            is_ok=abs_ms <= self._warn_ms,
            should_warn=self._warn_ms < abs_ms <= self._reject_ms,
            should_reject=abs_ms > self._reject_ms,
        )

    def measure_skew_ms(self) -> float:
        """Query the NTP server and return absolute skew in milliseconds.

        Returns 0.0 (no skew) if ntplib is not installed or the server
        is unreachable.  A warning is logged in that case.
        """
        try:
            import ntplib  # optional — add to dependencies for production

            client = ntplib.NTPClient()
            response = client.request(self._ntp_host, version=3)
            return abs(response.offset) * 1000.0
        except ImportError:
            _log.warning("ntplib not installed — NTP skew check skipped (skew=0.0 assumed)")
            return 0.0
        except Exception as exc:  # noqa: BLE001
            _log.warning("NTP check failed (%s) — skew=0.0 assumed", exc)
            return 0.0

    def check(self) -> NtpResult:
        """Measure skew and return a classified result."""
        return self.evaluate(self.measure_skew_ms())
