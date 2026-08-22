"""Lead-owned reconciliation items for the FB-1…FB-10 / FR-1…FR-21 Work PR.

Two kinds of thing land here, both of which fell between the implementation
workstreams' file ownership:

* **FR-21 in `effective_n.py`.** The merged audit's survivor table names two
  mutants in that module — `_require_count`'s `pinned < 0` → `< -1` and
  `_require_unit_fraction`'s `<= 1.0` → `<= 1.1`. The source is correct in both
  cases; nothing pinned the exact boundary, so both survived the whole suite.
  `effective_n.py` was in no workstream's ownership, so the lead closes them.
* **A pin on the one new capability the Work PR introduced.** Closing FR-7 gave
  `calendar_authority` a `hashlib` import. That is legitimate — its subject is
  caller-supplied in-memory values, not file bytes, so D-4's "hashing is a byte
  read" is not engaged — but a hash function inside a package that contractually
  never reads is exactly the sort of capability a later change could quietly
  point at a file. It is pinned here so that widening it fails a test.

Every refusal below is paired with a negative control immediately beside it, so
the test discriminates rather than merely refusing everything.
"""

from __future__ import annotations

import ast
import time
from pathlib import Path

import pytest

from scripts.m15_gate3a.effective_n import EffectiveNError, effective_n
from scripts.m15_gate3a.pair_authority import PAIRS_20

PACKAGE_DIR = Path(__file__).resolve().parents[2] / "scripts" / "m15_gate3a"


def _records(count: int = 1200, overlap: float = 0.5) -> list[dict[str, object]]:
    return [{"pair": p, "raw_event_count": count, "overlap_fraction": overlap} for p in PAIRS_20]


def _call(records: list[dict[str, object]]) -> dict:
    return effective_n(
        records,
        role="holdout",
        cross_pair_corr=0.3,
        count_quantity="raw_traded_event_count",
    )


# ---------------------------------------------------------------------------
# FR-21 · effective_n.py:113 — the exact negative boundary
# ---------------------------------------------------------------------------


def test_fr21_a_raw_event_count_of_minus_one_is_refused() -> None:
    """Kills `pinned < 0` → `pinned < -1`.

    Every existing test used a comfortably negative count (-100), which both the
    correct guard and the mutant refuse. Only `-1` separates them.
    """
    records = _records()
    records[0]["raw_event_count"] = -1
    with pytest.raises(EffectiveNError, match="must be a non-negative integer"):
        _call(records)


def test_fr21_a_raw_event_count_of_zero_is_accepted() -> None:
    """Negative control for the boundary above: zero is not negative."""
    records = _records()
    records[0]["raw_event_count"] = 0
    assert _call(records)["raw_event_count"] == 1200 * (len(PAIRS_20) - 1)


# ---------------------------------------------------------------------------
# FR-21 · effective_n.py:128 — the exact upper boundary of the unit fraction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("overlap", [1.0000001, 1.05, 1.1])
def test_fr21_an_overlap_fraction_just_above_one_is_refused(overlap: float) -> None:
    """Kills `<= 1.0` → `<= 1.1`.

    `1.1` is the mutant's own boundary and `1.05` sits inside it; both were
    accepted by the mutant and are refused by the correct guard.
    """
    records = _records(overlap=overlap)
    with pytest.raises(EffectiveNError, match=r"must be a finite number in \[0, 1\]"):
        _call(records)


@pytest.mark.parametrize("overlap", [0.0, 1.0])
def test_fr21_both_closed_ends_of_the_unit_interval_are_accepted(overlap: float) -> None:
    """Negative control: the interval is closed at both ends, and stays closed."""
    assert _call(_records(overlap=overlap))["raw_event_count"] > 0


# ---------------------------------------------------------------------------
# The one new capability this Work PR introduced
# ---------------------------------------------------------------------------


def _hashlib_importers() -> set[str]:
    found: set[str] = set()
    for path in sorted(PACKAGE_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imports_hashlib = (
                isinstance(node, ast.Import) and any(a.name == "hashlib" for a in node.names)
            ) or (isinstance(node, ast.ImportFrom) and node.module == "hashlib")
            if imports_hashlib:
                found.add(path.name)
    return found


def test_hashlib_is_confined_to_the_module_that_digests_declared_content() -> None:
    """FR-7 gave the package a hash function; pin where it may live.

    Not a contract violation — D-4's "hashing is a byte read" is about *raw
    source bytes*, and this digest's subject is the calendar artifact's own
    caller-supplied, already-parsed content. But the reason D-4 exists is that a
    digest is one argument away from being a file read, so the blast radius is
    bounded here rather than left to the next reader of the source.
    """
    assert _hashlib_importers() == {"calendar_authority.py"}, (
        "hashlib may be imported only by calendar_authority, which digests "
        "already-parsed declared content; a new importer needs its own ruling"
    )


def test_fr17_the_bucket_pattern_scans_a_long_run_in_linear_time() -> None:
    """FR-17's **root cause**, pinned where it lives.

    The artifacts workstream bounded what reaches the base scrubber, which fixes
    gate-3a. This pins the pattern itself, in `scripts/ml_step4/evidence.py`,
    because every other caller of that scanner had the same exposure.

    Why a timing assertion here when the artifacts workstream deliberately
    avoided one: at 32 000 characters the *old* pattern took ~5.6 s — finite, so
    this test **fails** rather than hanging the suite, which is what made a
    stopwatch unsafe at 306 KB. The margin is four orders of magnitude
    (measured: 5.5607 s before, 0.0008 s after), so the bound below is not a
    tight timing claim and will not flake on a slow host.
    """
    from scripts.ml_step4.evidence import _R2_PATTERNS  # noqa: PLC0415

    bucket = next(p for p in _R2_PATTERNS if "cloudflarestorage" in p.pattern)
    payload = "a" * 32_000
    started = time.perf_counter()
    assert bucket.search(payload) is None
    assert time.perf_counter() - started < 1.0, (
        "the bucket pattern has regained a quadratic left edge; a scanner that "
        "does not return is a gate that never closes"
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("bucket.r2.cloudflarestorage.com", True),
        ("MyBucket.R2.CloudflareStorage.COM", True),
        ("https://abc123.r2.cloudflarestorage.com/x", True),
        ("-bucket.r2.cloudflarestorage.com", True),
        ("x.r2.cloudflarestorage.co", False),
        ("no match here", False),
    ],
)
def test_fr17_the_linear_rewrite_changed_no_verdict(text: str, expected: bool) -> None:
    """Negative control for the rewrite: same answers, including mixed case."""
    from scripts.ml_step4.evidence import _R2_PATTERNS  # noqa: PLC0415

    bucket = next(p for p in _R2_PATTERNS if "cloudflarestorage" in p.pattern)
    assert bool(bucket.search(text)) is expected


def test_the_digest_subject_is_never_a_file() -> None:
    """The companion behavioural half: no hashing call takes a filesystem read.

    `test_wp5_reader_freedom.py` already pins that the package contains no read
    primitive at all, so a digest here *cannot* be fed file bytes. This asserts
    the narrower, directly-checkable property that the digest helper is called
    only with in-memory values.
    """
    source = (PACKAGE_DIR / "calendar_authority.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    hashing_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"sha256", "md5", "sha1", "blake2b"}
    ]
    assert hashing_calls, "non-vacuity: calendar_authority must contain the digest call"
    for call in hashing_calls:
        for arg in call.args:
            assert not (
                isinstance(arg, ast.Call)
                and isinstance(arg.func, ast.Attribute)
                and arg.func.attr in {"read_bytes", "read_text", "read"}
            ), "a digest in this package may never take file contents as its subject"
