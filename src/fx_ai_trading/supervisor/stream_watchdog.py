"""StreamWatchdog — PriceFeed / TransactionEvent stream health monitor skeleton (M8).

Responsibilities (full implementation: M9+):
  - Monitor heartbeat age of the PriceFeed stream.
  - Monitor heartbeat age of the TransactionEvent stream.
  - Trigger safe_stop if either stream goes silent beyond the threshold.

M8 scope: skeleton class with stub check_heartbeat() method.
  - Always returns True in M8 (stream assumed healthy).
  - No actual stream connectivity, no clock-based age check.
  - Called by Supervisor (step 11) once at startup; full integration M9+.
"""

from __future__ import annotations

import logging

from fx_ai_trading.common.clock import Clock

_log = logging.getLogger(__name__)

_DEFAULT_MAX_SILENCE_S = 30.0


class StreamWatchdog:
    """Skeleton stream health watchdog.

    Args:
        clock: Clock for heartbeat age computation (used in M9+).
        max_silence_s: Maximum allowed silence in seconds before raising (M9+).
    """

    def __init__(
        self,
        clock: Clock | None = None,
        max_silence_s: float = _DEFAULT_MAX_SILENCE_S,
    ) -> None:
        self._clock = clock
        self._max_silence_s = max_silence_s

    def check_heartbeat(self) -> bool:
        """Check whether the monitored streams are alive.

        M8 skeleton — always returns True.
        M9+: computes heartbeat age from clock.now() − last_heartbeat_at and
        returns False (triggering safe_stop) if age > max_silence_s.

        Returns:
            True if all streams are healthy (always True in M8).
        """
        _log.info("StreamWatchdog.check_heartbeat: stub — returning healthy (M8)")
        return True

    def record_heartbeat(self, stream_name: str) -> None:
        """Record a heartbeat event for *stream_name*.

        M8 skeleton — logs the call.
        M9+: updates the internal last_heartbeat_at timestamp.
        """
        _log.debug("StreamWatchdog.record_heartbeat: %s (M8 skeleton)", stream_name)
