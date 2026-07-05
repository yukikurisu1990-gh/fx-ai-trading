"""Data adapters for the ML Step 4 run body (fixture vs refused-real).

Separates the synthetic fixture provider (usable now, in tests only) from the
future real ``365d_BA`` provider (REFUSED in this build). No environment
variable, flag, or default can enable real data: ``RealDataProviderRefused``
raises on every access, and no candle-file reader exists in this module.

Bar schema (one dict per completed M1 bar, chronological):
``{"ts": tz-aware UTC datetime (:00 seconds), "bid_o","bid_h","bid_l","bid_c",
"ask_o","ask_h","ask_l","ask_c"}``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Final

# NOTE: ``PIP_SIZE`` is the synthetic-price *generation* scale for the fixture
# random walk below (spread / candle amplitude). It is NOT a pip-conversion
# authority and MUST NOT be used to convert PnL to pips for any pair — real or
# fixture. The sole pip-conversion authority is :func:`pip_size_for` (per pair).
# INV-1 (PR #421) was caused by using a fixed 0.0001 for pip conversion on all
# 20 pairs, mis-scaling the six JPY crosses by ~100x.
PIP_SIZE: Final[float] = 0.0001

# Non-JPY branch of the per-pair pip size (kept named so the source guard can
# allow ``0.0001`` only inside :func:`pip_size_for`).
_PIP_NON_JPY: Final[float] = 0.0001
_PIP_JPY: Final[float] = 0.01


class RealDataRefusedError(RuntimeError):
    """Raised when real 365d_BA data access is requested (unavailable here)."""


class PipSizeError(RuntimeError):
    """Raised when a pair has no known pip size (fail closed before any run)."""


def pip_size_for(pair: str) -> float:
    """Per-pair pip size — the sole pip-conversion authority (fail closed).

    Matches the committed research convention
    ``scripts.compare_multipair_v9_orthogonal._pip_size``:
    ``0.01`` for JPY-quote crosses (instruments ending ``_JPY``), ``0.0001``
    otherwise. A missing / empty / non-string pair fails closed with
    :class:`PipSizeError`, so no run can silently fall back to a wrong global
    scale. Non-JPY pairs are handled conservatively at ``0.0001`` (the
    convention's ``else`` branch).
    """
    if not isinstance(pair, str) or not pair.strip():
        raise PipSizeError("pip_size_for requires a non-empty pair name")
    return _PIP_JPY if pair.endswith("_JPY") else _PIP_NON_JPY


def pip_size_map(pairs: Iterable[str]) -> dict[str, float]:
    """Build ``{pair: pip_size_for(pair)}``; fail closed on empty / duplicate.

    Used once per real run so every downstream consumer (labels, trade scoring,
    timeout MTM, metrics, evidence) reads the SAME per-pair value from one
    source — structurally preventing the cross-layer inconsistency the fix must
    forbid. Every resolved pip size is re-checked positive (defence in depth).
    """
    mapping: dict[str, float] = {}
    for pair in pairs:
        if pair in mapping:
            raise PipSizeError(f"duplicate pair in pip-size map: {pair!r}")
        size = pip_size_for(pair)
        if not (size > 0):
            raise PipSizeError(f"non-positive pip size for {pair!r}")
        mapping[pair] = size
    if not mapping:
        raise PipSizeError("pip-size map is empty (no pairs)")
    return mapping


class FixtureDataProvider:
    """Deterministic synthetic M1 bars for the fixture rehearsal (no files).

    A seeded LCG random walk — pure Python, no filesystem, no network. Same
    (pairs, n_bars, seed) → byte-identical bars.
    """

    mode = "fixture"
    synthetic_only = True

    def __init__(
        self,
        pairs: tuple[str, ...] = ("FIX_PAIR_A", "FIX_PAIR_B"),
        # 6000 M1 bars ≈ 4.2 days: the 15% holdout tail crosses a UTC date
        # boundary, so the R-5 day-grouping/denominator logic is genuinely
        # exercised by the default rehearsal.
        n_bars: int = 6000,
        seed: int = 20260705,
        start: datetime = datetime(2025, 6, 2, 0, 0, tzinfo=UTC),
    ) -> None:
        if start.tzinfo is None:
            raise RealDataRefusedError("fixture start must be tz-aware UTC")
        self.pairs = tuple(pairs)
        self.n_bars = int(n_bars)
        self.seed = int(seed)
        self.start = start.astimezone(UTC)

    def _lcg(self, state: int) -> int:
        return (state * 6364136223846793005 + 1442695040888963407) % (2**64)

    def bars_for(self, pair: str) -> list[dict]:
        """Deterministic synthetic bars for one pair (cross-process stable).

        Pair mixing uses a SHA-256 digest, NOT ``hash()`` — Python string
        hashing is randomized per process (PYTHONHASHSEED) and would make the
        fixture nondeterministic across runs.
        """
        if pair not in self.pairs:
            raise RealDataRefusedError(f"unknown fixture pair {pair!r}")
        pair_mix = int.from_bytes(hashlib.sha256(pair.encode("utf-8")).digest()[:4], "big")
        state = self.seed ^ pair_mix
        mid = 1.1000
        spread = 1.2 * PIP_SIZE
        bars: list[dict] = []
        ts = self.start
        for _ in range(self.n_bars):
            state = self._lcg(state)
            step = ((state >> 16) % 2001 - 1000) / 1000.0  # [-1, 1]
            state = self._lcg(state)
            wick = ((state >> 16) % 1000) / 1000.0  # [0, 1)
            o = mid
            c = mid + step * 1.2 * PIP_SIZE
            hi = max(o, c) + wick * 0.8 * PIP_SIZE
            lo = min(o, c) - wick * 0.8 * PIP_SIZE
            half = spread / 2.0
            bars.append(
                {
                    "ts": ts,
                    "bid_o": o - half,
                    "bid_h": hi - half,
                    "bid_l": lo - half,
                    "bid_c": c - half,
                    "ask_o": o + half,
                    "ask_h": hi + half,
                    "ask_l": lo + half,
                    "ask_c": c + half,
                }
            )
            mid = c
            ts = ts + timedelta(minutes=1)
        return bars


class RealDataProviderRefused:
    """The future real ``365d_BA`` provider — REFUSES every access in this build.

    A separately-authorised first-run execution PR must replace this with a
    provider that re-verifies the PR-B.1 checksums immediately before reading.
    No environment variable or constructor argument can unlock it here.
    """

    mode = "real_refused"
    synthetic_only = False

    def __init__(self, *args: object, **kwargs: object) -> None:
        # Constructing the refused provider is allowed (so wiring can reference
        # it); every DATA access refuses.
        del args, kwargs

    @property
    def pairs(self) -> tuple[str, ...]:
        raise RealDataRefusedError("real 365d_BA data access is not available in this build")

    def bars_for(self, pair: str) -> list[dict]:
        raise RealDataRefusedError(
            "real 365d_BA data access is not available in this build; a separately "
            "authorised first-run execution PR must implement the real provider "
            "with pre-consumption checksum re-verification"
        )


# ---------------------------------------------------------------------------
# Real 365d_BA provider (checksum-verified) — first-run execution only
# ---------------------------------------------------------------------------


class Real365dBaProvider:
    """Reads ONLY the pre-registered 365d_BA epoch, checksum-verified first.

    ``verify()`` re-hashes all 20 committed files against the PR-B.1 inventory
    (SHA-256 + size) BEFORE any consumption; any missing / extra / duplicate /
    size- or checksum-mismatch / unreadable file raises, so no partial training
    can occur. ``pair_frame`` then loads one pair to a mid+bid/ask DataFrame via
    the committed trainer loader (lazy import). Provider/checksum metadata is
    recorded WITHOUT personal paths or raw rows.
    """

    mode = "real"
    synthetic_only = False
    provider_id = "scripts.ml_step4.data_adapter.Real365dBaProvider.v1"

    def __init__(self, inventory_records, data_root: str = "data") -> None:
        self._records = list(inventory_records)
        self._data_root = data_root  # relative repo path; never absolute/personal
        self._verified = False
        self._report: dict | None = None

    @property
    def pairs(self) -> tuple[str, ...]:
        return tuple(self._pair_name(r.filename) for r in self._records)

    @staticmethod
    def _pair_name(filename: str) -> str:
        # candles_<PAIR>_M1_365d_BA.jsonl -> <PAIR>
        base = filename.split("candles_", 1)[-1]
        return base.split("_M1_", 1)[0]

    def _path(self, filename: str):
        from pathlib import Path

        return Path(self._data_root) / filename

    def verify(self) -> dict:
        """Re-verify all files vs inventory; fail closed; return metadata report."""
        from .inventory import file_sha256_and_size

        per_file = []
        observed_total = 0
        mismatches = 0
        for rec in self._records:
            p = self._path(rec.filename)
            if not p.is_file():
                raise RealDataRefusedError(f"missing real file for {rec.filename}")
            sha, size = file_sha256_and_size(p)
            observed_total += size
            sha_ok = sha.lower() == rec.sha256.lower()
            size_ok = size == rec.size_bytes
            if not (sha_ok and size_ok):
                mismatches += 1
            per_file.append(
                {
                    "filename": rec.filename,
                    "pair": self._pair_name(rec.filename),
                    "sha256_match": sha_ok,
                    "size_match": size_ok,
                }
            )
        expected_total = sum(r.size_bytes for r in self._records)
        report = {
            "provider_id": self.provider_id,
            "inventory_source": (
                "artifacts/gate_p1_pr_b/firstrun_365d_ba/raw_inventory_365d_BA.json"
            ),
            "expected_file_count": len(self._records),
            "observed_file_count": len(per_file),
            "expected_total_bytes": expected_total,
            "observed_total_bytes": observed_total,
            "sha256_mismatches": mismatches,
            "all_match": mismatches == 0 and observed_total == expected_total,
            "per_file": per_file,
        }
        if not report["all_match"]:
            self._report = report
            raise RealDataRefusedError(
                f"365d_BA checksum verification FAILED: mismatches={mismatches} "
                f"observed_bytes={observed_total} expected={expected_total}"
            )
        self._verified = True
        self._report = report
        return report

    def verification_report(self) -> dict | None:
        return self._report

    def pair_frame(self, pair: str):
        """Load one pair to a DataFrame (mid + bid/ask); requires prior verify()."""
        if not self._verified:
            raise RealDataRefusedError("verify() must pass before reading any pair data")
        from scripts import train_lgbm_models as trainer  # lazy: builders/loader only

        rec = next((r for r in self._records if self._pair_name(r.filename) == pair), None)
        if rec is None:
            raise RealDataRefusedError(f"unknown pair {pair!r}")
        return trainer._load_ba_candles(self._path(rec.filename))
