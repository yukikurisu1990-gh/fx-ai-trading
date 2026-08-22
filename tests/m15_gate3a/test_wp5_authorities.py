"""Fourth-re-check fixes for the gate-3a authority modules and containment.

Covers, from ``docs/design/m15_fourth_independent_source_audit_recheck.md``:

* **FB-4** — containment failed open on an *absent* protected root, and the
  *creating* write landed inside it (Win32 trims a trailing dot or space);
* **FB-5** — ``guards.normalise_status`` and ``pair_authority._normalise_key``
  read the caller's string through overridable methods, so a ``str`` subclass
  answered the forbidden-status and the PAIRS_20-universe questions itself;
* **FB-10** — ``WarmupPolicy.validate()`` swallowed the numeric authority's
  refusal, disarming the T-1 burn-in while reporting itself valid;
* **FR-5** — R-1 applied non-uniformly: four one-valued fields still emitted;
* **FR-10** — ``assert_per_file_bounds`` leaked ``TimestampError`` instead of its
  documented ``NoOverlapError``;
* **FR-13** — four of the five frozen boundary constants were not test-bound to
  the committed artifacts;
* **FR-14** — the dead window's inclusive lower boundary was unpinned;
* **FR-20** — ``# pragma: no cover - guarded above`` on reachable branches;
* **FR-21** — mutation survivors whose source is correct but unpinned.

Nothing here reads real market data, opens a committed evidence tree, or writes
anywhere outside ``tmp_path``. The three committed artifacts this module reads
are metadata-only boundary declarations, read for comparison and never modified.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from scripts.m15_gate3a.cost_schema import (
    ALL_IN_COST_FORMULA,
    CLAIM_SCOPE,
    DATA_SOURCE_RESTRICTION,
    EXECUTION_PADDING_PIP,
    FLAT_SLIPPAGE_CELL_PIP,
    SESSIONS_UTC,
    SPREAD_UNIT,
    STRESS_FORMS,
    CostSchemaError,
    validate_cost_table,
)
from scripts.m15_gate3a.guards import (
    RealDataRefusedError,
    assert_status_allowed,
    is_forbidden_status,
    normalise_status,
    refuse_real_path,
)
from scripts.m15_gate3a.no_overlap import (
    DEAD_END,
    DEAD_START,
    DESIGN_END,
    DESIGN_START,
    FORWARD_FLOOR,
    NoOverlapError,
    assert_no_dead_window,
    assert_per_file_bounds,
    is_dead_window_instant,
)
from scripts.m15_gate3a.numeric_authority import NumericAuthorityError, pin_int, pin_number
from scripts.m15_gate3a.pair_authority import (
    PAIRS_20,
    PairAuthorityError,
    canonical_pair,
    pip_size_for_pair,
)
from scripts.m15_gate3a.path_authority import PathAuthorityError, assert_outside
from scripts.m15_gate3a.timeutil import TimestampError, to_utc
from scripts.m15_gate3a.warmup import WarmupPolicy, WarmupPolicyError
from tests.m15_gate3a.roster_fixtures import design_roster

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "m15_gate3a"


# --------------------------------------------------------------------- helpers


class TwoFacedStr(str):
    """A ``str`` whose character data and whose *methods* disagree.

    Every method a fold might reach is overridden to return ``shown``; the real
    character data stays whatever ``str.__new__`` was given. ``str.__str__`` is
    deliberately *not* overridable — it is the unbound slot the fixed code reads
    through, and it returns the real data.
    """

    _shown: str

    def __new__(cls, real: str, shown: str) -> TwoFacedStr:
        obj = super().__new__(cls, real)
        obj._shown = shown
        return obj

    def strip(self, *_args: Any) -> str:  # type: ignore[override]
        return self._shown

    def lstrip(self, *_args: Any) -> str:  # type: ignore[override]
        return self._shown

    def rstrip(self, *_args: Any) -> str:  # type: ignore[override]
        return self._shown

    def upper(self) -> str:  # type: ignore[override]
        return self._shown

    def lower(self) -> str:  # type: ignore[override]
        return self._shown

    def replace(self, *_args: Any, **_kwargs: Any) -> str:  # type: ignore[override]
        return self._shown

    def __str__(self) -> str:
        return self._shown

    def __repr__(self) -> str:
        return repr(self._shown)


class SpoofInt:
    """Claims ``__class__ is int`` and answers every comparison favourably.

    ``isinstance`` consults ``__class__``, so this satisfies every
    ``isinstance(x, int)`` in the package, while ``int.__index__`` — the unbound
    slot the numeric authority reads through — refuses it. It is the object
    FB-10 was reproduced with.
    """

    @property  # type: ignore[misc]
    def __class__(self) -> type:  # noqa: D105
        return int

    def __le__(self, other: Any) -> bool:
        # `w_bars <= 0` must be False (looks positive) while
        # `index >= w_bars` -> `w_bars.__le__(index)` must be True from index 1,
        # so the burn-in appears to end at bar 1 instead of at `w_bars`.
        return isinstance(other, int) and other >= 1

    def __lt__(self, _other: Any) -> bool:
        return False  # never "shorter than the feature lookback"

    def __ge__(self, _other: Any) -> bool:
        return True

    def __gt__(self, _other: Any) -> bool:
        return True

    def __eq__(self, _other: Any) -> bool:
        return False

    def __hash__(self) -> int:
        return 0

    def __repr__(self) -> str:
        return "SPOOF"


class SpoofFloat:
    """Claims ``__class__ is float``; ``float.__float__`` refuses it."""

    @property  # type: ignore[misc]
    def __class__(self) -> type:  # noqa: D105
        return float

    def __le__(self, _other: Any) -> bool:
        return False

    def __lt__(self, _other: Any) -> bool:
        return False

    def __ge__(self, _other: Any) -> bool:
        return True

    def __gt__(self, _other: Any) -> bool:
        return False

    def __eq__(self, _other: Any) -> bool:
        return True

    def __hash__(self) -> int:
        return 0

    def __repr__(self) -> str:
        return "SPOOF_FLOAT"


class LyingFloat(float):
    """A real ``float`` holding one value whose ``__float__`` reports another."""

    def __float__(self) -> float:
        return 0.0

    def __lt__(self, _other: Any) -> bool:
        return False

    def __gt__(self, _other: Any) -> bool:
        return False

    def __le__(self, _other: Any) -> bool:
        return True

    def __ge__(self, _other: Any) -> bool:
        return True


def _cost_cell(pair: str, session: str) -> dict[str, Any]:
    pip = pip_size_for_pair(pair)
    return {
        "pair": pair,
        "session": session,
        "median_spread": 1.0 * pip,
        "p90_spread": 2.0 * pip,
        "p95_spread": 3.0 * pip,
        "pip_size": pip,
    }


def _cost_table(**overrides: Any) -> dict[str, Any]:
    """A complete synthetic 20x3 table. Spreads are invented test numbers."""
    table: dict[str, Any] = {
        "execution_padding_pip": EXECUTION_PADDING_PIP,
        "flat_slippage_cell_pip": FLAT_SLIPPAGE_CELL_PIP,
        "all_in_cost_formula": ALL_IN_COST_FORMULA,
        "spread_unit": SPREAD_UNIT,
        "claim_scope": CLAIM_SCOPE,
        "stress_forms": list(STRESS_FORMS),
        "data_source_restriction": DATA_SOURCE_RESTRICTION,
        "entries": [_cost_cell(p, s) for p in PAIRS_20 for s in SESSIONS_UTC],
    }
    table.update(overrides)
    return table


def _verdict(candidate: str, protected: Path) -> str:
    try:
        assert_outside(candidate, (protected,), (SYNTHETIC_PROTECTED_LEAF,))
    except PathAuthorityError:
        return "REFUSE"
    return "ALLOW"


# --------------------------------------------------------------- sanity floors


def test_the_synthetic_cost_table_is_the_complete_grid_the_refusal_tests_assume() -> None:
    """Non-vacuity floor: without this, every cost refusal below could be coverage."""
    table = _cost_table()
    assert len(table["entries"]) == len(PAIRS_20) * len(SESSIONS_UTC)
    assert validate_cost_table(table, max_spread_pips=None)["spread_unit"] == SPREAD_UNIT


def test_the_two_faced_string_really_is_two_faced() -> None:
    """Non-vacuity floor for every FB-5 test: the fixture must actually lie."""
    probe = TwoFacedStr("XXX_YYY", "GBP_CHF")
    assert str.__str__(probe) == "XXX_YYY"
    assert probe.strip() == "GBP_CHF"
    assert probe.upper() == "GBP_CHF"
    assert probe.replace("_", "-") == "GBP_CHF"
    assert str(probe) == "GBP_CHF"


def test_the_class_spoofing_int_really_is_a_spoof() -> None:
    """Non-vacuity floor for every FB-10 test: control on the numeric authority."""
    assert isinstance(SpoofInt(), int)  # `isinstance` consults `__class__`
    with pytest.raises(NumericAuthorityError, match="the int slot refuses"):
        pin_int(SpoofInt(), what="control")


# ============================================================ FB-4 containment
#
# The protected root is DELIBERATELY not created in these tests: `.gitignore`
# lists `models/`, so an absent protected root is the state of every fresh clone
# and of every CI run. That is the state in which the guard failed open.
#
# The synthetic root is NOT named after a real protected prefix. `test_recheck_
# fixes.test_rf4_the_suite_never_addresses_the_real_protected_tree` scans this
# suite for a write aimed at one, and a test that creates a directory literally
# called `models` trips a guard that exists for a good reason. The real
# `models/` tree is reached below through `refuse_real_path`, which creates
# nothing. The defect is a property of the *spelling*, not of the name.

SYNTHETIC_PROTECTED_LEAF = "synthetic_protected_tree"

# Every suffix Win32's trailing-trim removes, so the table states the family
# rather than the two spellings the audit printed.
WIN32_TRIM_SUFFIXES = (".", " ", "..", "...", ". ", " .", " . . ")

WIN32_ALIAS_SPELLINGS = tuple(SYNTHETIC_PROTECTED_LEAF + s for s in WIN32_TRIM_SUFFIXES) + (
    SYNTHETIC_PROTECTED_LEAF.upper() + ".",
    SYNTHETIC_PROTECTED_LEAF.capitalize() + " ",
)


@pytest.mark.parametrize("spelling", WIN32_ALIAS_SPELLINGS)
def test_fb4_a_win32_trimmed_spelling_of_an_absent_protected_root_is_refused(
    spelling: str, tmp_path: Path
) -> None:
    """Failing-before: every one of these was ALLOW while the root was absent.

    Win32 trims trailing dots and spaces, so each of these opens the protected
    directory itself. ``Path.resolve(strict=False)`` cannot canonicalise a component
    that does not exist, so the spelling survived, the name test compared
    unequal, and ``_protected_stat`` returned ``None`` because there was nothing
    to be identical to.
    """
    base = tmp_path.resolve()
    protected = base / SYNTHETIC_PROTECTED_LEAF
    assert not protected.exists()  # the condition the defect needed
    with pytest.raises(PathAuthorityError, match="win32-normalisable path component"):
        assert_outside(str(base / spelling), (protected,), (SYNTHETIC_PROTECTED_LEAF,))


def test_fb4_a_win32_trimmed_component_is_refused_anywhere_in_the_path(tmp_path: Path) -> None:
    """The family is the component, not the leaf: ``<protected>.\\weights`` was ALLOW too."""
    base = tmp_path.resolve()
    protected = base / SYNTHETIC_PROTECTED_LEAF
    candidate = str(base / (SYNTHETIC_PROTECTED_LEAF + ".") / "weights" / "final.bin")
    with pytest.raises(PathAuthorityError, match="win32-normalisable path component"):
        assert_outside(candidate, (protected,), (SYNTHETIC_PROTECTED_LEAF,))


@pytest.mark.parametrize(
    "spelling",
    [
        "harmless",
        "out/report.json",
        "a/./harmless",
        "sibling/../harmless",
        "with.dots/in.name.json",
    ],
)
def test_fb4_ordinary_spellings_are_still_allowed(spelling: str, tmp_path: Path) -> None:
    """Negative control: the guard discriminates, it does not refuse everything.

    ``.`` and ``..`` are navigation rather than names and stay admissible, and a
    dot *inside* a component (``report.json``) is untouched by the trailing trim.
    """
    base = tmp_path.resolve()
    protected = base / SYNTHETIC_PROTECTED_LEAF
    assert_outside(str(base / spelling), (protected,), (SYNTHETIC_PROTECTED_LEAF,))


def test_fb4_the_protected_root_itself_is_still_refused_by_the_name_test(tmp_path: Path) -> None:
    """Negative control on the *reason*: the plain spelling fires a different guard."""
    base = tmp_path.resolve()
    protected = base / SYNTHETIC_PROTECTED_LEAF
    with pytest.raises(PathAuthorityError, match="refused real/protected path"):
        assert_outside(str(protected), (protected,), (SYNTHETIC_PROTECTED_LEAF,))


def test_fb4_the_refusal_happens_before_anything_is_created(tmp_path: Path) -> None:
    """The audit's operative harm: the *creating* write landed in the real tree."""
    base = tmp_path.resolve()
    protected = base / SYNTHETIC_PROTECTED_LEAF
    with pytest.raises(PathAuthorityError, match="win32-normalisable path component"):
        assert_outside(
            str(base / (SYNTHETIC_PROTECTED_LEAF + ".")),
            (protected,),
            (SYNTHETIC_PROTECTED_LEAF,),
        )
    assert not protected.exists()


@pytest.mark.parametrize("spelling", WIN32_ALIAS_SPELLINGS)
def test_fb4_an_absent_protected_root_is_never_more_permissive_than_a_present_one(
    spelling: str, tmp_path: Path
) -> None:
    """The invariant FB-4 broke, stated as a property rather than as a case list.

    ``is_within``'s identity limb reads the filesystem and must. What makes that
    safe is monotonicity: presence of the protected root may only *add* refusals.
    FB-4 was the violation — with the root present ``resolve()`` canonicalised
    the trailing-dot spelling and the guard refused; with it absent the same
    string was allowed.
    """
    absent_base = (tmp_path / "absent").resolve()
    absent_base.mkdir()
    present_base = (tmp_path / "present").resolve()
    present_base.mkdir()
    (present_base / SYNTHETIC_PROTECTED_LEAF).mkdir()

    absent_verdict = _verdict(str(absent_base / spelling), absent_base / SYNTHETIC_PROTECTED_LEAF)
    present_verdict = _verdict(
        str(present_base / spelling), present_base / SYNTHETIC_PROTECTED_LEAF
    )
    if present_verdict == "REFUSE":
        assert absent_verdict == "REFUSE", (
            f"{spelling!r} is REFUSED when the protected root exists and "
            f"{absent_verdict} when it does not; containment became a function of "
            "filesystem state"
        )


def test_fb4_the_routed_guard_refuses_the_model_binary_tree_spelling() -> None:
    """Through ``refuse_real_path``, the one containment routing that has a caller.

    Host-independent: the refusal is decided on the spelling, so this asserts the
    same thing on a developer machine (where ``models/`` happens to exist) and on
    CI (where ``.gitignore`` guarantees it does not). Nothing is created.
    """
    with pytest.raises(RealDataRefusedError, match="win32-normalisable path component"):
        refuse_real_path(str(REPO_ROOT / "models."))


def test_fb4_the_routed_guard_still_admits_an_ordinary_output_directory(tmp_path: Path) -> None:
    """Negative control for the routed guard."""
    refuse_real_path(str(tmp_path.resolve() / "gate3a_out"))


# ================================================== FB-5 (guards) status pinning


FORBIDDEN_LABELS = ("PASS", "MEETS", "ROBUST", "PRODUCTION_READY", "Tier 1", "VALIDATED")


@pytest.mark.parametrize("label", FORBIDDEN_LABELS)
def test_fb5_a_two_faced_status_is_classified_on_its_character_data(label: str) -> None:
    """Failing-before: ``is_forbidden_status(S("PASS"))`` was ``False``.

    ``unicodedata.normalize("NFKC", s)`` returns *the same object* when the input
    is already NFKC-normal, so for a ``str`` subclass the ``.strip()`` and
    ``.upper()`` that followed were the subclass's own methods.
    """
    probe = TwoFacedStr(label, "TOTALLY_CLEAN")
    assert is_forbidden_status(probe) is True


@pytest.mark.parametrize("label", FORBIDDEN_LABELS)
def test_fb5_a_two_faced_status_cannot_be_asserted(label: str) -> None:
    """Failing-before: ``assert_status_allowed(S("PASS"))`` returned, i.e. ALLOWED."""
    probe = TwoFacedStr(label, "TOTALLY_CLEAN")
    with pytest.raises(RealDataRefusedError, match="may not be asserted here"):
        assert_status_allowed(probe)


def test_fb5_the_refusal_names_the_pinned_character_data_not_the_rendering() -> None:
    """A record of a refusal that names the wrong label is not a record of it."""
    probe = TwoFacedStr("PASS", "TOTALLY_CLEAN")
    with pytest.raises(RealDataRefusedError) as excinfo:
        assert_status_allowed(probe)
    assert "'PASS'" in str(excinfo.value)
    assert "TOTALLY_CLEAN" not in str(excinfo.value)


def test_fb5_normalise_status_folds_the_pinned_character_data() -> None:
    probe = TwoFacedStr("production ready", "TOTALLY_CLEAN")
    assert normalise_status(probe) == "PRODUCTION_READY"


def test_fb5_a_clean_status_wearing_a_forbidden_mask_is_still_allowed() -> None:
    """Negative control in the other direction: the predicate reads data, not class.

    A ``str`` subclass is not itself suspicious. This one's character data is
    clean while every method it exposes says ``PASS``; it must be ALLOWED, which
    is what distinguishes "pin the character data" from "refuse subclasses".
    """
    probe = TwoFacedStr("GATE3A_METADATA_ONLY", "PASS")
    assert is_forbidden_status(probe) is False
    assert_status_allowed(probe)


def test_fb5_a_plain_forbidden_status_is_still_refused() -> None:
    """Control: the plain value the two-faced object was compared against."""
    assert is_forbidden_status("PASS") is True
    with pytest.raises(RealDataRefusedError, match="may not be asserted here"):
        assert_status_allowed("PASS")


# ============================================ FB-5 (pair_authority) key pinning


@pytest.mark.parametrize("claimed", ["GBP_CHF", "USD_JPY", "EUR_USD"])
def test_fb5_a_two_faced_pair_cannot_be_certified_into_the_frozen_universe(
    claimed: str,
) -> None:
    """Failing-before: char data ``XXX_YYY`` was certified as ``GBP_CHF``.

    ``_normalise_key`` began ``pair.strip().upper()`` and then called
    ``.replace()`` on the result, so the whole fold was the caller's to answer.
    """
    probe = TwoFacedStr("XXX_YYY", claimed)
    with pytest.raises(PairAuthorityError, match="is not in the frozen PAIRS_20 universe"):
        canonical_pair(probe)


def test_fb5_a_two_faced_pair_cannot_obtain_a_pip_size() -> None:
    """The measured consequence: ``pip_size 0.0001`` for a pair that does not exist."""
    probe = TwoFacedStr("XXX_YYY", "GBP_CHF")
    with pytest.raises(PairAuthorityError, match="is not in the frozen PAIRS_20 universe"):
        pip_size_for_pair(probe)


def test_fb5_the_pair_refusal_names_the_real_character_data() -> None:
    probe = TwoFacedStr("XXX_YYY", "GBP_CHF")
    with pytest.raises(PairAuthorityError) as excinfo:
        canonical_pair(probe)
    assert "'XXX_YYY'" in str(excinfo.value)
    assert "GBP_CHF" not in str(excinfo.value)


def test_fb5_a_two_faced_pair_cannot_desynchronise_a_no_overlap_record() -> None:
    """The cross-module consequence the audit measured, pinned end to end.

    ``_roster_report`` pins ``filename`` and ``sha256`` of the same record while
    ``pair`` was left unpinned, so one record read ``pair: GBP_CHF`` beside
    ``filename: XXX_YYY.parquet``.
    """
    roster = design_roster()
    roster[-1] = {**roster[-1], "pair": TwoFacedStr("XXX_YYY", "GBP_CHF")}
    with pytest.raises(NoOverlapError, match="missing"):
        assert_per_file_bounds(roster, role="design")


def test_fb5_the_pair_fold_itself_reads_pinned_character_data() -> None:
    """The second limb, pinned in isolation — ``_normalise_key`` is the audit's site.

    ``canonical_pair`` pins before calling the fold, so with only that pin in
    place a revert of the fold's own pin is invisible to every public-API test.
    Both are pinned deliberately: unlike an ``isinstance``-then-pin pair, two
    applications of the same pin cannot disagree (it is idempotent), and the fold
    is a module-private helper a future caller could reach directly.
    """
    from scripts.m15_gate3a.pair_authority import _normalise_key

    assert _normalise_key(TwoFacedStr("xxx-yyy", "GBP_CHF")) == "XXX_YYY"
    assert _normalise_key("usd/jpy") == "USD_JPY"  # negative control: honest input


def test_fb5_an_honest_pair_subclass_still_normalises() -> None:
    """Negative control: the pin reads character data, it does not ban subclasses."""
    probe = TwoFacedStr("usd/jpy", "XXX_YYY")
    assert canonical_pair(probe) == "USD_JPY"
    assert pip_size_for_pair(probe) == 0.01


def test_fb5_a_plain_off_universe_pair_is_still_refused() -> None:
    """Control: the plain value the two-faced object was compared against."""
    with pytest.raises(PairAuthorityError, match="is not in the frozen PAIRS_20 universe"):
        canonical_pair("XXX_YYY")


# ================================================================ FB-10 warm-up


def test_fb10_a_class_spoofing_w_bars_no_longer_validates() -> None:
    """Failing-before: ``validate()`` PASSED and reported no refusal at all.

    The pin loop did ``except NumericAuthorityError: continue`` under a
    ``# pragma: no cover``, and the ``isinstance`` checks below could not recover
    because ``isinstance`` consults ``__class__``.
    """
    policy = WarmupPolicy(w_bars=SpoofInt(), longest_feature_lookback_bars=24)
    with pytest.raises(WarmupPolicyError, match="not plain int character data"):
        policy.validate()


def test_fb10_a_class_spoofing_lookback_no_longer_validates() -> None:
    policy = WarmupPolicy(w_bars=24, longest_feature_lookback_bars=SpoofInt())
    with pytest.raises(WarmupPolicyError, match="not plain int character data"):
        policy.validate()


def test_fb10_the_spoof_cannot_publish_itself_as_warm_up_metadata() -> None:
    """Failing-before: ``as_metadata`` emitted the spoof as ``w_bars`` *and* as
    ``first_eligible_bar_index`` — the T-1 burn-in boundary, published."""
    policy = WarmupPolicy(w_bars=SpoofInt(), longest_feature_lookback_bars=24)
    with pytest.raises(WarmupPolicyError, match="not plain int character data"):
        policy.as_metadata()


def test_fb10_the_spoof_cannot_declare_a_bar_event_eligible() -> None:
    """Failing-before: eligibility began at bar index 1 instead of at 24."""
    policy = WarmupPolicy(w_bars=SpoofInt(), longest_feature_lookback_bars=24)
    for index in (0, 1, 2, 23):
        with pytest.raises(WarmupPolicyError, match="not plain int character data"):
            policy.is_event_eligible(index)


def test_fb10_the_spoof_cannot_authorise_a_load() -> None:
    policy = WarmupPolicy(w_bars=SpoofInt(), longest_feature_lookback_bars=24)
    with pytest.raises(WarmupPolicyError, match="not plain int character data"):
        policy.assert_load_allowed(FORWARD_FLOOR + timedelta(days=1))
    with pytest.raises(WarmupPolicyError, match="not plain int character data"):
        policy.loads_pre_forward(FORWARD_FLOOR + timedelta(days=1))


def test_fb10_the_honest_policy_the_spoof_was_impersonating_still_works() -> None:
    """Negative control, and the honest answer the spoof displaced.

    With ``w_bars=24`` no bar below 24 is eligible; the spoof made bars 1..23
    eligible while publishing itself as the boundary.
    """
    policy = WarmupPolicy(w_bars=24, longest_feature_lookback_bars=24)
    assert {i: policy.is_event_eligible(i) for i in (0, 1, 2, 23)} == {
        0: False,
        1: False,
        2: False,
        23: False,
    }
    assert policy.is_event_eligible(24) is True
    assert policy.as_metadata()["first_eligible_bar_index"] == 24


def test_fb10_an_int_subclass_carrying_real_int_data_is_still_accepted() -> None:
    """Negative control: the pin refuses objects that are not ints, not subclasses."""

    class RealIntSubclass(int):
        pass

    policy = WarmupPolicy(w_bars=RealIntSubclass(24), longest_feature_lookback_bars=24)
    policy.validate()
    assert policy.as_metadata()["w_bars"] == 24
    assert type(policy.as_metadata()["w_bars"]) is int


# ====================================================== FR-20 reachable pragmas


def test_fr20_a_class_spoofing_bar_index_is_refused_as_a_warmup_error() -> None:
    """``warmup.py:96``'s ``# pragma: no cover - guarded above`` was on live code."""
    policy = WarmupPolicy(w_bars=24, longest_feature_lookback_bars=24)
    with pytest.raises(WarmupPolicyError, match="not plain int character data"):
        policy.is_event_eligible(SpoofInt())


def test_fr20_a_plain_negative_bar_index_fires_the_other_guard() -> None:
    """Negative control that discriminates the two refusals at the same site."""
    policy = WarmupPolicy(w_bars=24, longest_feature_lookback_bars=24)
    with pytest.raises(WarmupPolicyError, match="bar_index must be a non-negative integer"):
        policy.is_event_eligible(-1)


def test_fr20_a_class_spoofing_magnitude_bound_is_refused_as_a_cost_schema_error() -> None:
    """``cost_schema.py:161``'s pragma was likewise on a reachable branch.

    The refusal must also arrive as this module's own error class: a
    ``NumericAuthorityError`` escaping here is invisible to every caller
    documented to catch ``CostSchemaError`` (the RF-29 class).
    """
    with pytest.raises(CostSchemaError, match="must be a number or None"):
        validate_cost_table(_cost_table(), max_spread_pips=SpoofFloat())


def test_fr20_a_declared_numeric_field_that_spoofs_its_class_is_a_cost_schema_error() -> None:
    """The same conversion at ``_pin_numeric``, which had no wrapper at all."""
    with pytest.raises(CostSchemaError, match="is not plain numeric character data"):
        validate_cost_table(_cost_table(execution_padding_pip=SpoofFloat()), max_spread_pips=None)


def test_fr20_an_ordinary_magnitude_bound_is_still_accepted() -> None:
    """Negative control for both conversions above."""
    summary = validate_cost_table(_cost_table(), max_spread_pips=50.0)
    assert summary["max_spread_pips_declared"] == 50.0
    assert summary["magnitude_authority"] == "CALLER_DECLARED"


# ============================================ FR-5 R-1 applied uniformly


@pytest.mark.parametrize("field", ["entries_validated", "pairs_covered", "result"])
def test_fr5_the_cost_summary_no_longer_emits_a_one_valued_field(field: str) -> None:
    """R-1: a field that can hold only one value is deleted, not reported.

    Each of these was invariant on every returning path — coverage raises unless
    all 60 canonical cells are present and duplicates raise, so ``len(entries)``
    is 60, ``pairs_covered`` is ``sorted(PAIRS_20)``, and a returned dict already
    means the table validated.
    """
    assert field not in validate_cost_table(_cost_table(), max_spread_pips=None)


def test_fr5_the_no_overlap_record_no_longer_emits_files_checked() -> None:
    """``files_checked`` was always 20 on the only returning path (contract §8)."""
    assert "files_checked" not in assert_per_file_bounds(design_roster(), role="design")


def test_fr5_what_the_cost_summary_still_reports_is_two_valued() -> None:
    """Non-vacuity: the deletion left a summary of measured, variable quantities."""
    unbounded = validate_cost_table(_cost_table(), max_spread_pips=None)
    bounded = validate_cost_table(_cost_table(), max_spread_pips=50.0)
    assert unbounded["magnitude_checked_against_declared_bound"] is False
    assert bounded["magnitude_checked_against_declared_bound"] is True
    assert unbounded["magnitude_authority"] != bounded["magnitude_authority"]
    assert unbounded["max_spread_pips_declared"] is None
    assert bounded["max_spread_pips_declared"] == 50.0


def test_fr5_the_no_overlap_record_still_carries_the_per_record_evidence() -> None:
    """Non-vacuity: what replaced the tautology is the roster binding itself."""
    record = assert_per_file_bounds(design_roster(), role="design")
    spans = record["certified_spans"]
    assert len(spans) == len(PAIRS_20)
    assert {s["pair"] for s in spans} == set(PAIRS_20)
    assert len({s["sha256"] for s in spans}) == len(PAIRS_20)


# ============================================== FR-10 documented exception type


def test_fr10_a_sub_second_declared_bound_raises_the_documented_error() -> None:
    """Failing-before: ``TimestampError`` leaked out of ``assert_per_file_bounds``.

    The value clears ``_parse`` and every bound check and then fails inside
    ``format_utc_z`` at the publication step, which is the documented-type
    violation RF-29 names.
    """
    roster = design_roster()
    roster[0] = {**roster[0], "ts_max_utc": "2025-12-31T23:59:59.500000Z"}
    with pytest.raises(NoOverlapError, match="cannot be published in the canonical form"):
        assert_per_file_bounds(roster, role="design")


def test_fr10_the_lower_bound_is_converted_at_the_same_site() -> None:
    roster = design_roster()
    roster[3] = {**roster[3], "ts_min_utc": "2025-05-01T00:00:00.000001Z"}
    with pytest.raises(NoOverlapError, match="cannot be published in the canonical form"):
        assert_per_file_bounds(roster, role="design")


def test_fr10_the_timestamp_error_is_preserved_as_the_cause() -> None:
    """Converted, not swallowed: the emission layer's diagnosis must survive."""
    roster = design_roster()
    roster[0] = {**roster[0], "ts_max_utc": "2025-12-31T23:59:59.500000Z"}
    with pytest.raises(NoOverlapError) as excinfo:
        assert_per_file_bounds(roster, role="design")
    assert isinstance(excinfo.value.__cause__, TimestampError)


def test_fr10_a_whole_second_bound_still_publishes() -> None:
    """Negative control: the conversion did not turn the publication into a refusal."""
    record = assert_per_file_bounds(design_roster(), role="design")
    assert record["certified_spans"][0]["ts_max_utc"].endswith("Z")


# =========================== FR-13 the frozen constants vs the committed evidence


def _committed(name: str) -> dict:
    text = (ARTIFACT_DIR / name).read_text(encoding="utf-8")
    assert len(text) > 200, f"committed artifact {name} is missing or truncated"
    return json.loads(text)


def _iso_z(instant: datetime) -> str:
    return (
        f"{instant.year:04d}-{instant.month:02d}-{instant.day:02d}"
        f"T{instant.hour:02d}:{instant.minute:02d}:{instant.second:02d}Z"
    )


@pytest.mark.parametrize(
    "constant,committed_key",
    [
        (DESIGN_START, "design_start"),
        (DESIGN_END, "design_end"),
        (DEAD_START, "dead_window_start"),
        (DEAD_END, "dead_window_end"),
        (FORWARD_FLOOR, "forward_epoch_floor"),
    ],
)
def test_fr13_every_frozen_boundary_matches_the_committed_no_overlap_proof(
    constant: datetime, committed_key: str
) -> None:
    """Only ``design_end`` was bound by a test; the other four could drift silently."""
    boundaries = _committed("no_overlap_proof.json")["boundary_constants_utc"]
    assert _iso_z(constant) == boundaries[committed_key]


def test_fr13_the_design_span_matches_the_committed_derivation_manifest() -> None:
    """A second committed authority for the same two boundaries (R-2)."""
    cut = _committed("design_m15_derivation_manifest.json")["design_span_cut"]
    assert _iso_z(DESIGN_START) == cut["design_start_utc"]
    assert _iso_z(DESIGN_END) == cut["design_end_utc"]


def test_fr13_the_forward_floor_matches_the_committed_adoption_manifest() -> None:
    frozen = _committed("forward_epoch_adoption_manifest.json")["frozen_requirement"]
    assert _iso_z(FORWARD_FLOOR) == frozen["forward_epoch_start_floor_utc"]


def test_fr13_the_committed_boundary_block_is_the_shape_this_binding_assumes() -> None:
    """Non-vacuity floor: a renamed or emptied block must fail, not pass silently."""
    boundaries = _committed("no_overlap_proof.json")["boundary_constants_utc"]
    assert set(boundaries) == {
        "design_start",
        "design_end",
        "dead_window_start",
        "dead_window_end",
        "forward_epoch_floor",
    }


# ================================= FR-14 both dead-window limbs, pinned in isolation


def test_fr14_the_dead_windows_first_instant_is_inside_it() -> None:
    """Failing-before under mutation: ``<=`` to ``<`` survived the whole suite.

    No test anywhere used ``2026-03-01T00:00:00Z``; every dead-window test used a
    mid-window or post-window instant. Reachability matters — with no design-epoch
    limb in ``calendar_authority._normalise_slot``, this predicate is the only
    thing between an approved calendar and an expected slot at the dead window's
    first bucket.
    """
    assert is_dead_window_instant("2026-03-01T00:00:00Z") is True
    assert is_dead_window_instant(DEAD_START) is True


def test_fr14_the_instant_one_second_before_the_dead_window_is_outside_it() -> None:
    """Negative control for the lower limb, one second away from it."""
    assert is_dead_window_instant(DEAD_START - timedelta(seconds=1)) is False
    assert is_dead_window_instant("2026-02-28T23:59:59Z") is False


def test_fr14_the_dead_windows_final_second_is_inside_it() -> None:
    """The upper limb in isolation: the final second is deliberately dead."""
    assert is_dead_window_instant(DEAD_END) is True
    assert is_dead_window_instant("2026-04-24T23:59:59Z") is True


def test_fr14_the_forward_floor_is_outside_the_dead_window() -> None:
    """Negative control for the upper limb, at the contiguous boundary."""
    assert is_dead_window_instant(FORWARD_FLOOR) is False
    assert is_dead_window_instant("2026-04-25T00:00:00Z") is False


def test_fr14_a_span_starting_at_the_dead_windows_first_instant_is_refused() -> None:
    """The same limb through a public consumer, not only through the predicate."""
    with pytest.raises(NoOverlapError, match="span intersects dead window"):
        assert_no_dead_window(DEAD_START, DEAD_START, role="probe")


def test_fr14_the_warmup_load_gate_refuses_the_dead_windows_first_instant() -> None:
    """And through the T-1 load gate, which is what the boundary protects."""
    policy = WarmupPolicy(w_bars=24, longest_feature_lookback_bars=24)
    assert policy.loads_pre_forward(DEAD_START) is True
    with pytest.raises(WarmupPolicyError, match="pre-forward load forbidden"):
        policy.assert_load_allowed(DEAD_START)


# ================================================= FR-21 mutation survivors pinned


class MicrosecondLiar(datetime):
    """A ``datetime`` subclass whose ``timestamp()`` disagrees by well under 1 us."""

    def timestamp(self) -> float:
        return datetime.timestamp(self) + 1e-6


def test_fr21_a_sub_microsecond_component_lie_is_refused() -> None:
    """``timeutil.py:133``: ``drift != 0.0`` mutated to ``drift > 1e-6`` survived.

    The float64 second count near 2026 resolves about 4e-7 s, so this lie lands
    at ~9.5e-7 s of drift — under the mutated threshold and over exact equality.
    Exact equality is the guard; this is the input that tells the two apart.
    """
    with pytest.raises(TimestampError, match="disagrees with its own components"):
        to_utc(MicrosecondLiar(2026, 1, 1, tzinfo=UTC))


def test_fr21_an_honest_datetime_subclass_is_still_accepted() -> None:
    """Negative control: exact equality is not "refuse every subclass"."""

    class HonestSubclass(datetime):
        pass

    assert to_utc(HonestSubclass(2026, 1, 1, tzinfo=UTC)) == datetime(2026, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize("blank", ["   ", "\t", "\n", "   "])
def test_fr21_a_whitespace_only_filename_is_refused(blank: str) -> None:
    """``no_overlap.py:322``: the whitespace-only ``filename`` guard was unpinned.

    A blank identity would let twenty records describe one physical file while
    the duplicate-evidence guard saw twenty distinct names.
    """
    roster = design_roster()
    roster[0] = {**roster[0], "filename": blank}
    with pytest.raises(NoOverlapError, match="has no usable 'filename'"):
        assert_per_file_bounds(roster, role="design")


def test_fr21_a_filename_with_surrounding_whitespace_is_still_usable() -> None:
    """Negative control: the guard rejects *empty* identity, not untidy identity."""
    roster = design_roster()
    roster[0] = {**roster[0], "filename": "  candles_EUR_USD_M15.jsonl  "}
    assert_per_file_bounds(roster, role="design")


def test_fr21_a_lying_float_spread_cannot_validate_as_non_negative() -> None:
    """``cost_schema.py:257``: ``pin_number(v)`` mutated to ``float(v)`` survived.

    ``float(v)`` calls ``type(v).__float__``, so this object holding -50000.0
    would report 0.0 and validate — the exact N-1 defect that module's comment
    says it closed, and the audit measured
    ``min_observed_spread_pips = -50000.0`` from it.
    """
    entries = _cost_table()["entries"]
    entries[0] = {**entries[0], "median_spread": LyingFloat(-50000.0)}
    with pytest.raises(CostSchemaError, match="must be a finite non-negative number"):
        validate_cost_table(_cost_table(entries=entries), max_spread_pips=None)


def test_fr21_the_plain_negative_spread_control_is_also_refused() -> None:
    """Control: the plain value the lying subclass was impersonating."""
    entries = _cost_table()["entries"]
    entries[0] = {**entries[0], "median_spread": -50000.0}
    with pytest.raises(CostSchemaError, match="must be a finite non-negative number"):
        validate_cost_table(_cost_table(entries=entries), max_spread_pips=None)


def test_fr21_the_unbound_slot_is_what_reads_the_lying_float() -> None:
    """Isolates the mechanism the mutant removes, without the surrounding validator."""
    liar = LyingFloat(-50000.0)
    assert float(liar) == 0.0
    assert pin_number(liar, what="probe") == -50000.0
