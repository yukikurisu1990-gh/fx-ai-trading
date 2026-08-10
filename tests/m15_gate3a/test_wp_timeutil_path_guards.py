"""Workstream-A regressions: the timestamp, path and refusal-guard authorities.

Every test here pins one committed finding — audit blocker B-5, required fixes
RF-1, RF-2, RF-5, RF-12, RF-13, RF-14, RF-15, RF-20, and contract requirements
§12.18 and §12.23 — and each was confirmed to fail against the source it
replaces (or, for the test-layer findings, against the surviving mutation).

House rules observed throughout, each grounded in a defect the audit found in
this very suite:

* no ``pytest.raises(match=...)`` alternation — every ``match`` substring below
  occurs at exactly one ``raise`` site, so a passing test identifies *which*
  guard fired. Where two guards could fire, there are two tests with two inputs;
* the module's own exception types (``TimestampError``, ``PathAuthorityError``,
  ``RealDataRefusedError``), never bare ``Exception``/``ValueError``;
* no host state: the path tests build their trees under ``tmp_path`` and
  monkeypatch the authority root, so the verdict never depends on where the
  repository happens to sit or on which directory pytest was started from;
* no fail-open is frozen as expected behaviour. The one test that asserts a
  path is *allowed* (``artifacts/m15_gate3a``) pins an explicit ruling (D-7) and
  names the condition under which it must be changed.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.m15_gate3a import guards
from scripts.m15_gate3a.guards import (
    RealDataRefusedError,
    assert_no_forbidden_operation,
    assert_status_allowed,
    is_forbidden_status,
    refuse_real_path,
)
from scripts.m15_gate3a.path_authority import PathAuthorityError, resolve_candidate
from scripts.m15_gate3a.timeutil import TimestampError, format_utc_z, to_utc

# ==========================================================================
# RF-1 — the fractional-digit check saw one separator and one fraction
# ==========================================================================

# The instant one 100-nanosecond tick past DESIGN_END, spelled both legal ISO
# ways. Truncating either one rebuilds it to exactly DESIGN_END, which is the
# T-7 boundary fail-open the "refused, never truncated" invariant exists to stop.
_PAST_DESIGN_END_DOT = "2026-02-28T23:59:59.0000005+00:00"
_PAST_DESIGN_END_COMMA = "2026-02-28T23:59:59,0000005+00:00"


@pytest.mark.parametrize("spelling", [_PAST_DESIGN_END_DOT, _PAST_DESIGN_END_COMMA])
def test_rf1_both_iso_decimal_separators_refuse_a_sub_microsecond_digit(spelling: str) -> None:
    """ISO-8601 admits ``,`` as well as ``.``; ``fromisoformat`` accepts both.

    Lead-verified against the previous source: the ``.`` spelling was refused
    and the ``,`` spelling was **accepted and truncated** — the same instant,
    two answers, with the comma path being the fail-open one.
    """
    with pytest.raises(TimestampError, match="non-zero sub-microsecond remainder"):
        to_utc(spelling)


def test_rf1_the_two_separators_are_not_merely_both_rejected_for_other_reasons() -> None:
    """Six digits are representable and must still parse — on either separator.

    Without this, RF-1 could be "fixed" by refusing every fraction, which would
    refuse the microsecond resolution ``datetime`` genuinely has.
    """
    expected = datetime(2026, 2, 28, 23, 59, 59, 123456, tzinfo=UTC)
    assert to_utc("2026-02-28T23:59:59.123456+00:00") == expected
    assert to_utc("2026-02-28T23:59:59,123456+00:00") == expected


def test_rf1_a_fraction_hidden_in_the_offset_is_refused_too() -> None:
    """``.search`` stopped at the first fraction, so the offset's was never seen."""
    with pytest.raises(TimestampError, match="non-zero sub-microsecond remainder"):
        to_utc("2026-02-28T23:59:59.000000+00:00:00.9999999")


def test_rf1_a_fraction_hidden_in_the_offset_is_refused_on_the_comma_spelling() -> None:
    """Both defects compose: the second fraction, spelled with the second separator."""
    with pytest.raises(TimestampError, match="non-zero sub-microsecond remainder"):
        to_utc("2026-02-28T23:59:59+00:00:00,0000001")


# ==========================================================================
# §12.23 — canonical timestamp ingest and emission
# ==========================================================================

# Verbatim from the committed `artifacts/m15_gate3a/no_overlap_proof.json`:
# nine fractional digits, all of them zero. Inlined rather than read, so this
# test cannot pass or fail because of the state of a file on disk.
_COMMITTED_M1_TS_MIN = "2025-04-24T22:03:00.000000000Z"
_COMMITTED_M1_TS_MAX = "2026-04-24T20:59:00.000000000Z"


@pytest.mark.parametrize(
    ("committed", "expected"),
    [
        (_COMMITTED_M1_TS_MIN, datetime(2025, 4, 24, 22, 3, tzinfo=UTC)),
        (_COMMITTED_M1_TS_MAX, datetime(2026, 4, 24, 20, 59, tzinfo=UTC)),
    ],
)
def test_1223_zero_only_excess_fractional_digits_are_accepted(
    committed: str, expected: datetime
) -> None:
    """§12.23's ingest rule: all-zero excess digits lose nothing, so they parse.

    The previous digit-count test refused the committed M1 predecessor
    inventory's own timestamps, which carry nine zeros and no information.
    """
    assert to_utc(committed) == expected


@pytest.mark.parametrize(
    "spelling",
    [
        "2025-04-24T22:03:00.000000001Z",  # last digit only
        "2025-04-24T22:03:00.000000100Z",  # in the middle of the excess
        "2025-04-24T22:03:00.0000009Z",  # seven digits, one non-zero
        "2025-04-24T22:03:00,000000001Z",  # comma spelling of the same
    ],
)
def test_1223_any_non_zero_sub_microsecond_digit_is_refused_not_truncated(spelling: str) -> None:
    """ "Zero-only" means every excess digit, not just the first or the last."""
    with pytest.raises(TimestampError, match="non-zero sub-microsecond remainder"):
        to_utc(spelling)


def test_1223_format_utc_z_emits_the_canonical_artifact_spelling() -> None:
    """``YYYY-MM-DDTHH:MM:SSZ`` — literal ``Z``, no offset, no fractional part."""
    rendered = format_utc_z(datetime(2026, 2, 28, 23, 59, 59, tzinfo=UTC))
    assert rendered == "2026-02-28T23:59:59Z"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", rendered)


def test_1223_format_utc_z_never_emits_the_isoformat_offset_spelling() -> None:
    """§12.23 forbids ``datetime.isoformat()``'s ``+00:00`` reaching an artifact."""
    instant = datetime(2026, 2, 28, 23, 59, 59, tzinfo=UTC)
    assert instant.isoformat().endswith("+00:00")  # the spelling being replaced
    assert format_utc_z(instant) == "2026-02-28T23:59:59Z"


def test_1223_format_utc_z_normalises_a_non_utc_offset_to_the_same_instant() -> None:
    """The formatter emits UTC, whatever offset the input carried."""
    assert format_utc_z("2026-02-28T18:59:59-05:00") == "2026-02-28T23:59:59Z"
    assert format_utc_z(datetime(2026, 3, 1, 8, 59, 59, tzinfo=timezone(timedelta(hours=9)))) == (
        "2026-02-28T23:59:59Z"
    )


def test_1223_format_utc_z_refuses_a_microsecond_rather_than_truncating_it() -> None:
    """The output format has no fractional field, so rendering one would lie."""
    with pytest.raises(TimestampError, match="has no fractional field"):
        format_utc_z(datetime(2026, 2, 28, 23, 59, 59, 1, tzinfo=UTC))


def test_1223_format_utc_z_refuses_a_naive_datetime() -> None:
    """The emitter inherits every ingest refusal; it is not a second front door."""
    with pytest.raises(TimestampError, match="naive datetime rejected"):
        format_utc_z(datetime(2026, 2, 28, 23, 59, 59))


def test_1223_format_utc_z_refuses_a_sub_microsecond_iso_string() -> None:
    """Emission cannot be used to launder a refused ingest."""
    with pytest.raises(TimestampError, match="non-zero sub-microsecond remainder"):
        format_utc_z(_PAST_DESIGN_END_COMMA)


@pytest.mark.parametrize(
    "spelling",
    [
        "2026-02-28T23:59:59+00:00",
        "2026-02-28T23:59:59Z",
        _COMMITTED_M1_TS_MIN,
        "2026-02-28T18:59:59-05:00",
    ],
)
def test_1223_emission_round_trips_through_ingest(spelling: str) -> None:
    """Anything this package emits, it can read back to the identical instant."""
    assert to_utc(format_utc_z(spelling)) == to_utc(spelling)


# ==========================================================================
# RF-2 — a documented guarantee the code does not have
# ==========================================================================


def test_rf2_the_docstring_no_longer_claims_component_lies_are_caught_outright() -> None:
    """The defect *is* the sentence, so the sentence is what is asserted.

    This is not the RF-21 anti-pattern. RF-21 condemned asserting that a
    ``raise`` string appears in the source *as a proxy for* the invariant
    holding. Here the audit's finding is that a docstring states a guarantee the
    code does not provide ("catches [component lies] outright"), and its
    prescribed fix is that "the guarantee must be restated, not the code
    necessarily changed" — the documentation is the deliverable under test.
    Its behavioural companion is the test immediately below.
    """
    from scripts.m15_gate3a.timeutil import _reject_subclass_divergence

    doc = _reject_subclass_divergence.__doc__ or ""
    assert "catches the second class outright" not in doc
    assert "consistently" in doc, "the restated docstring must name the case that passes"


def test_rf2_the_guarantee_that_does_hold_is_the_consistency_of_the_two_views() -> None:
    """A subclass whose components and ``timestamp()`` disagree is refused.

    That — not "component lies are caught" — is what the cross-check buys, and
    it is worth having: it is the limb that stopped a two-line subclass
    reporting ``month == 1`` for a March instant from walking a dead-window
    timestamp past the dead-window predicate.
    """

    class ComponentLiar(datetime):
        @property
        def month(self) -> int:  # type: ignore[override]
            return 1

    liar = ComponentLiar(2026, 3, 15, 12, 0, 0, tzinfo=UTC)
    with pytest.raises(TimestampError, match="disagrees with its own components"):
        to_utc(liar)


# ==========================================================================
# RF-20 — the two-faced `str`-subclass defence, pinned against reversion
# ==========================================================================


def test_rf20_a_two_faced_str_subclass_parses_to_its_carried_instant() -> None:
    """``str.__str__(ts)`` reads the character data; ``str(ts)`` asks the liar.

    RF-20: the identical hardening in ``path_authority`` was tested, this one
    was not, so the mutation ``str.__str__(ts)`` -> ``str(ts)`` survived. Under
    that mutant this timestamp parses to 2026-12-25 — a *forward-epoch* instant
    presented as a design-span one.
    """

    class TwoFaced(str):
        def __str__(self) -> str:  # noqa: D105
            return "2026-12-25T00:00:00+00:00"

    carried = TwoFaced("2025-06-02T00:00:00+00:00")
    assert str(carried) == "2026-12-25T00:00:00+00:00"  # the face it shows
    assert to_utc(carried) == datetime(2025, 6, 2, 0, 0, tzinfo=UTC)  # the instant it carries


def test_rf20_the_two_faced_defence_also_covers_the_minute_and_emission_paths() -> None:
    """Every public entry point reads the carried data, not the rendered face."""
    from scripts.m15_gate3a.timeutil import to_utc_minute

    class TwoFaced(str):
        def __str__(self) -> str:  # noqa: D105
            return "2026-12-25T00:00:00+00:00"

    carried = TwoFaced("2025-06-02T00:00:00+00:00")
    assert to_utc_minute(carried) == datetime(2025, 6, 2, 0, 0, tzinfo=UTC)
    assert format_utc_z(carried) == "2025-06-02T00:00:00Z"


# ==========================================================================
# RF-5 — a `Path` subclass could show the guard one path and the writer another
# ==========================================================================


def _lying_path_class() -> type[Path]:
    """A ``Path`` subclass whose ``__str__`` renders something it does not carry."""

    class LyingPath(type(Path())):  # type: ignore[misc]
        shown = "unset"

        def __str__(self) -> str:  # noqa: D105
            return type(self).shown

    return LyingPath  # type: ignore[return-value]


def test_rf5_a_path_subclass_hiding_a_protected_tree_is_refused(
    protected_root: Path,
) -> None:
    """Lead-verified fail-open: ALLOWED as the subclass, REFUSED once wrapped.

    The object carries the consumed-holdout tree and renders a harmless name.
    ``__fspath__`` is defined as ``str(self)``, so an ``open()`` on this very
    object would have used the carried path while the guard read the rendered
    one.
    """
    lying = _lying_path_class()
    lying.shown = str(protected_root / "artifacts" / "harmless")  # type: ignore[attr-defined]
    candidate = lying(str(protected_root / "artifacts" / "ml_step4" / "365d_ba_v1"))

    with pytest.raises(RealDataRefusedError, match="disagrees with its own path data"):
        refuse_real_path(candidate)


def test_rf5_the_divergence_is_refused_in_the_other_direction_too(
    protected_root: Path,
) -> None:
    """A guard that only refuses one direction still lets the two views split."""
    lying = _lying_path_class()
    lying.shown = str(protected_root / "data")  # type: ignore[attr-defined]
    candidate = lying(str(protected_root / "harmless"))

    with pytest.raises(PathAuthorityError, match="disagrees with its own path data"):
        resolve_candidate(candidate)


def test_rf5_an_ordinary_path_is_unaffected(tmp_path: Path) -> None:
    """The pin must not refuse the plain ``Path`` every caller actually uses."""
    assert resolve_candidate(tmp_path) == tmp_path.resolve()
    assert resolve_candidate(tmp_path / "no" / "such" / "file.json").is_absolute()


def test_rf5_a_path_subclass_that_tells_the_truth_is_still_accepted(tmp_path: Path) -> None:
    """Subclassing is not itself the offence; disagreeing with yourself is."""

    class HonestPath(type(Path())):  # type: ignore[misc]
        pass

    honest = HonestPath(str(tmp_path / "x.json"))
    assert resolve_candidate(honest) == (tmp_path / "x.json").resolve()


# ==========================================================================
# §12.18 / B-5 — cwd independence and the protected tree set
# ==========================================================================


@pytest.fixture
def protected_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A synthetic repository root with every governance-named tree present.

    The authority root is monkeypatched rather than inherited from the host, so
    these tests cannot pass because of what happens to exist on this machine,
    and cannot fail because a real tree is absent from a checkout.
    """
    root = tmp_path / "synthetic_repo"
    for tree in (
        "artifacts/ml_step4/365d_ba_v1",
        "artifacts/gate_p1_pr_b/firstrun_365d_ba",
        "artifacts/gate_p1_pr_b/firstrun_730d_ba",
        "artifacts/gate_p1_pr_b/firstrun_3650d_ba",
        "artifacts/m15_gate3a",
        "data",
        "models",
        "docs",
        "harmless",
    ):
        (root / tree).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(guards, "repo_root", lambda: root)
    return root


_GOVERNANCE_PROTECTED_TREES = [
    "artifacts/ml_step4/365d_ba_v1",
    "artifacts/gate_p1_pr_b/firstrun_365d_ba",
    "artifacts/gate_p1_pr_b/firstrun_730d_ba",
    "artifacts/gate_p1_pr_b/firstrun_3650d_ba",
    "data",
    "models",
    "docs",
]


@pytest.mark.parametrize("tree", _GOVERNANCE_PROTECTED_TREES)
def test_b5_every_governance_named_tree_is_refused(tree: str, protected_root: Path) -> None:
    """B-5 / §12.18: five of these seven were ALLOWED.

    ``data/`` is the real M1 candle store and the default ``data_root`` of
    ``Real365dBaProvider``; ``models/`` holds twenty model binaries; ``docs/``
    is the governance tree itself, which the writer could target; the 730d and
    3650d trees are PR-B.1 evidence.
    """
    with pytest.raises(RealDataRefusedError, match="refused real/protected path"):
        refuse_real_path(str(protected_root / tree))


@pytest.mark.parametrize("tree", _GOVERNANCE_PROTECTED_TREES)
def test_b5_a_file_under_every_governance_named_tree_is_refused(
    tree: str, protected_root: Path
) -> None:
    """Naming the root is the easy case; the write target is a leaf under it."""
    with pytest.raises(RealDataRefusedError, match="refused real/protected path"):
        refuse_real_path(protected_root / tree / "sub" / "dir" / "target.json")


def test_b5_artifacts_m15_gate3a_is_deliberately_not_blanket_protected(
    protected_root: Path,
) -> None:
    """D-7's explicit trap, pinned so it is not "fixed" by accident.

    The audit's B-5 reproduction lists ``artifacts/m15_gate3a`` as ALLOWED, but
    D-7 rules that directory is populated **through a human-reviewed PR diff**
    and that the continuation's outputs go to a **separate output directory**;
    it names closing B-5 by adding this prefix, while §5 still names the
    directory as a write target, as a trap. Blanket-protecting it here would
    break the §5-mandated write.

    **When this test must change:** once the separate output directory is
    adopted, the prefix becomes safe to add and this test should be replaced by
    its refusal counterpart. Until then, allowing it is a ruling, not a gap.
    """
    refuse_real_path(protected_root / "artifacts" / "m15_gate3a")
    refuse_real_path(protected_root / "artifacts" / "m15_gate3a" / "design_m15_inventory.json")


def test_b5_an_unrelated_tree_is_still_allowed(protected_root: Path) -> None:
    """A guard that refuses everything proves nothing; both verdicts must occur."""
    refuse_real_path(protected_root / "harmless" / "output.json")


def test_1218_a_relative_candidate_is_refused_rather_than_resolved_against_the_cwd(
    protected_root: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """§12.18 / D-7, lead-verified: the same logical path, two verdicts.

    From the repository root ``"data"`` resolved into the protected tree and was
    REFUSED; from anywhere else it resolved elsewhere and was ALLOWED. The
    working directory is not an input this guard may take.
    """
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    with pytest.raises(RealDataRefusedError, match="containment would depend on the working"):
        refuse_real_path("data")


def test_1218_the_relative_refusal_holds_from_the_authority_root_too(
    protected_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refusal is a property of the spelling, not of where it happened to land."""
    monkeypatch.chdir(protected_root)
    with pytest.raises(RealDataRefusedError, match="containment would depend on the working"):
        refuse_real_path("data")


@pytest.mark.parametrize("subdir", ["elsewhere", "artifacts", "harmless"])
def test_1218_an_absolute_verdict_is_identical_from_every_working_directory(
    subdir: str, protected_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The positive half of cwd-independence: absolute verdicts never move."""
    cwd = protected_root / subdir
    cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(cwd)
    with pytest.raises(RealDataRefusedError, match="refused real/protected path"):
        refuse_real_path(str(protected_root / "models" / "usd_jpy.txt"))
    refuse_real_path(str(protected_root / "harmless" / "out.json"))


def test_1218_a_bare_filename_and_a_dot_relative_spelling_are_both_refused(
    protected_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every relative spelling, not only the obvious ``dir/child`` one."""
    monkeypatch.chdir(protected_root)
    for spelling in ("out.json", "./out.json", "../models", "sub/../models"):
        with pytest.raises(PathAuthorityError, match="containment would depend on the working"):
            resolve_candidate(spelling)


# ==========================================================================
# RF-12 — forbidden-status normalisation against playbook §10
# ==========================================================================


@pytest.mark.parametrize(
    "spelling",
    [
        "tier1",
        "TIER1",
        "productionready",
        "ProductionReady",
        "BYTEADMISSIBLE",
        "readyforlive",
        "newepochadopted",
        "formallyverified",
    ],
)
def test_rf12_run_together_spellings_of_a_forbidden_label_are_refused(spelling: str) -> None:
    """Playbook §10: "casing/whitespace variants ... are treated identically".

    ``normalise_status`` mapped a separator to ``_`` instead of removing it, so
    the run-together spellings compared unequal to the canonical keys and passed.
    """
    with pytest.raises(RealDataRefusedError, match="may not be asserted here"):
        assert_status_allowed(spelling)


@pytest.mark.parametrize(
    "spelling",
    [
        "validated",
        "VALIDATED",
        "proven profitable",
        "Proven-Profitable",
        "provenprofitable",
        "ready to deploy",
        "READY_TO_DEPLOY",
        "green-light",
        "green light",
        "greenlight",
        "cleared for live",
        "cleared for paper",
        "cleared for live/paper",
    ],
)
def test_rf12_playbook_near_synonyms_are_refused(spelling: str) -> None:
    """§10's near-synonym guidance had no representation in the set at all."""
    with pytest.raises(RealDataRefusedError, match="may not be asserted here"):
        assert_status_allowed(spelling)


@pytest.mark.parametrize(
    "spelling",
    [
        "PASSED",
        "COMPASS",
        "BYPASS",
        "ROBUSTNESS",
        "MEETS_PREREGISTERED_CRITERIA",
        "NOT_PRODUCTION_READY",
        "DOES_NOT_MEET",
        "VALIDATION_KILL_GATE",
        "PRE_VALIDATION_DESIGN_ONLY",
        "M15_AGGREGATION_DATASET_MACHINERY_TARGETED_FIXES_PROPOSED",
        "FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS",
    ],
)
def test_rf12_legitimate_labels_are_not_swept_up(spelling: str) -> None:
    """Separator removal must not turn the fold into substring matching.

    The comparison stays exact over the whole normalised string; claim-substring
    scanning belongs to the scrubber, not to this predicate.
    """
    assert is_forbidden_status(spelling) is False
    assert_status_allowed(spelling)


def test_rf12_the_predicate_reports_both_values() -> None:
    """R-1's negative-control rule: a one-valued report is not evidence."""
    assert is_forbidden_status("PASS") is True
    assert is_forbidden_status("PASSED") is False


@pytest.mark.parametrize(
    "label",
    [
        "PASS",
        "Tier 1",
        "FORMALLY_VERIFIED",
        "PRODUCTION_READY",
        "READY_FOR_LIVE",
        "M15_AUTHORISED",
        "H1_AUTHORISED",
        "H2_STARTED",
        "PHASE_C2_STARTED",
        "NEW_EPOCH_ADOPTED",
        "BYTE_ADMISSIBLE",
        "MEETS",
        "ROBUST",
        "DEPLOYABLE",
    ],
)
def test_rf12_every_label_named_in_playbook_section_10_is_refused(label: str) -> None:
    """Transcribed from the playbook §10 list, so drift in either shows up here."""
    with pytest.raises(RealDataRefusedError, match="may not be asserted here"):
        assert_status_allowed(label)


# ==========================================================================
# RF-13 — `assert_status_allowed` was fail-open on the type
# ==========================================================================


@pytest.mark.parametrize("value", [b"PASS", ["PASS"], ("PASS",), {"PASS": True}, None, 42, 1.0])
def test_rf13_a_non_str_status_is_refused_unread(value: object) -> None:
    """A guard whose job is to refuse cannot read "I cannot parse this" as "fine".

    Lead-verified: ``b"PASS"``, ``["PASS"]`` and ``None`` were all silently
    allowed, because the predicate this delegated to reports ``False`` for
    everything that is not a ``str``.
    """
    with pytest.raises(RealDataRefusedError, match="refused unread"):
        assert_status_allowed(value)


def test_rf13_the_predicate_itself_still_classifies_rather_than_refusing() -> None:
    """The scrubber walks arbitrary JSON, so the *predicate* must stay total."""
    assert is_forbidden_status(b"PASS") is False
    assert is_forbidden_status(None) is False


def test_rf13_a_str_subclass_is_still_read_as_a_status() -> None:
    """Fail-closed on type must not become fail-closed on every subclass."""

    class Label(str):
        pass

    with pytest.raises(RealDataRefusedError, match="may not be asserted here"):
        assert_status_allowed(Label("PASS"))


# ==========================================================================
# RF-14 — `assert_no_forbidden_operation` could be disarmed by a typo
# ==========================================================================


@pytest.mark.parametrize("flags", [{"training": False}, {"validation": False}, {"executes": 0}])
def test_rf14_an_unknown_flag_name_is_refused_whatever_its_value(flags: dict) -> None:
    """The likely typo ``training=False`` for ``train`` passed silently.

    An unknown *name* means the operation the caller meant to forbid was never
    checked, and that is true regardless of the value attached to it.
    """
    with pytest.raises(RealDataRefusedError, match="unknown operation flag"):
        assert_no_forbidden_operation(**flags)


def test_rf14_a_call_naming_no_operation_is_refused() -> None:
    """An empty call read exactly like an assertion while asserting nothing."""
    with pytest.raises(RealDataRefusedError, match="asserts nothing"):
        assert_no_forbidden_operation()


@pytest.mark.parametrize("value", [0, "", None, [], 1, "no"])
def test_rf14_a_non_bool_flag_value_is_refused(value: object) -> None:
    """Truthiness is not a disposition: ``train=0`` disarmed a real flag."""
    with pytest.raises(RealDataRefusedError, match="must be a bool"):
        assert_no_forbidden_operation(train=value)


def test_rf14_a_known_flag_set_true_is_still_refused_as_the_operation() -> None:
    """The name check must run first without swallowing the original refusal."""
    with pytest.raises(RealDataRefusedError, match="refused in synthetic-only gate 5"):
        assert_no_forbidden_operation(train=True)


def test_rf14_known_flags_set_false_still_pass() -> None:
    """The hardening must not refuse the one call shape that is legitimate."""
    assert_no_forbidden_operation(train=False, execute=False)


# ==========================================================================
# RF-15 — docstrings asserting containment properties the code lacks
# ==========================================================================


def test_rf15_the_module_docstring_does_not_claim_universal_routing() -> None:
    """``guards.py`` claimed "Every entry point ... routes through these guards".

    Three of its four public guards have zero non-test callers, so the claim was
    false, and a false containment claim in the module that *is* the containment
    story is the kind of thing a merge approval reads and believes. As with
    RF-2, the defect is the sentence; its behavioural companion is below.
    """
    doc = guards.__doc__ or ""
    assert "Every entry point" not in doc
    assert "no non-test caller" in doc, "the docstring must say which guards are unrouted"


def test_rf15_the_routing_the_docstring_does_claim_actually_exists(
    protected_root: Path,
) -> None:
    """The corrected docstring names one write routing; it has to be real.

    ``write_metadata_artifact`` must reach ``refuse_real_path`` for the output
    directory, and must do so *before* creating anything.
    """
    from scripts.m15_gate3a.artifacts import write_metadata_artifact

    target_dir = protected_root / "docs" / "governance"
    with pytest.raises(RealDataRefusedError, match="refused real/protected path"):
        write_metadata_artifact(target_dir, "sneaky.json", {"note": "x"})
    assert not target_dir.exists(), "a refused write must leave nothing behind"
