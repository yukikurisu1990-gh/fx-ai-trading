"""INV-1 per-pair pip-size fix — mapping, mixed-scale, consistency, evidence,
regression, and source-guard tests.

Proves the PR #421 invalidator cannot recur: pip conversion is governed by a
single per-pair authority (``0.01`` for ``*_JPY``, ``0.0001`` otherwise), routed
identically into label generation, trade scoring, timeout MTM, metrics and
evidence. No real data is read, no model is trained here beyond the tiny
synthetic LightGBM end-to-end already used by the first-run tests, and no real
metrics are generated.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ml_step4 import evidence, manifest
from scripts.ml_step4.data_adapter import (
    PipSizeError,
    pip_size_for,
    pip_size_map,
)
from scripts.ml_step4.labels import bulk_labels, traded_direction_pnl_pips
from scripts.ml_step4.manifest import ManifestError

# Reuse the synthetic BA fixture builders from the first-run test module.
from tests.ml_step4.test_first_run import _provider

# ---------------------------------------------------------------------------
# 1. Per-pair pip-size mapping
# ---------------------------------------------------------------------------

_JPY_PAIRS = ("USD_JPY", "EUR_JPY", "GBP_JPY", "AUD_JPY", "NZD_JPY", "CHF_JPY")
_NON_JPY_PAIRS = ("EUR_USD", "GBP_USD", "AUD_CAD")


@pytest.mark.parametrize("pair", _JPY_PAIRS)
def test_jpy_pairs_pip_size_is_hundredth(pair: str) -> None:
    assert pip_size_for(pair) == 0.01


@pytest.mark.parametrize("pair", _NON_JPY_PAIRS)
def test_non_jpy_pairs_pip_size_is_ten_thousandth(pair: str) -> None:
    assert pip_size_for(pair) == 0.0001


def test_pip_size_map_all_20_style_pairs() -> None:
    pairs = _JPY_PAIRS + _NON_JPY_PAIRS
    mapping = pip_size_map(pairs)
    assert mapping == {**{p: 0.01 for p in _JPY_PAIRS}, **{p: 0.0001 for p in _NON_JPY_PAIRS}}


def test_pip_size_matches_committed_research_convention() -> None:
    # Parity with scripts.compare_multipair_v9_orthogonal._pip_size (the authority
    # cited by the PR #422 audit), referenced here only as a convention check.
    from scripts.compare_multipair_v9_orthogonal import _pip_size as research_pip_size

    for pair in _JPY_PAIRS + _NON_JPY_PAIRS:
        assert pip_size_for(pair) == research_pip_size(pair)


def test_pip_size_for_empty_or_bad_pair_fails_closed() -> None:
    for bad in ("", "   ", None, 123):
        with pytest.raises(PipSizeError):
            pip_size_for(bad)  # type: ignore[arg-type]


def test_pip_size_map_empty_and_duplicate_fail_closed() -> None:
    with pytest.raises(PipSizeError):
        pip_size_map([])
    with pytest.raises(PipSizeError):
        pip_size_map(["EUR_USD", "EUR_USD"])


def test_unknown_pair_format_handled_conservatively() -> None:
    # A non-empty but non-standard token is handled conservatively as non-JPY
    # (0.0001) — the convention's else-branch — never silently JPY-scaled.
    assert pip_size_for("GARBAGE") == 0.0001
    assert pip_size_for("FIXA") == 0.0001


# ---------------------------------------------------------------------------
# 2. Mixed-scale value-pinned fixture (JPY-like vs non-JPY)
# ---------------------------------------------------------------------------


def _timeout_pnl_pips(mtm_price: float, pip_size: float) -> float:
    """Score a LONG timeout trade (no barrier hit) -> pips, via the authority."""
    return traded_direction_pnl_pips(
        direction="long",
        tp_idx=-1,  # -1 = barrier never hit -> timeout mark-to-market path
        sl_idx=-1,
        tp_dist_price=1.0,
        sl_dist_price=1.0,
        mtm_exit_pnl_price=mtm_price,
        pip_size=pip_size,
    )


def test_mixed_scale_same_price_move_different_pip_magnitude() -> None:
    move = 0.10  # identical raw price move for both pairs
    jpy_pips = _timeout_pnl_pips(move, pip_size_for("USD_JPY"))  # 0.01
    non_jpy_pips = _timeout_pnl_pips(move, pip_size_for("EUR_USD"))  # 0.0001

    # Same raw move -> different pip magnitudes, pinned to exact values.
    assert jpy_pips == pytest.approx(10.0)
    assert non_jpy_pips == pytest.approx(1000.0)

    # The JPY pair is NOT 100x mis-scaled: the correct value is 10 pips, whereas
    # the old fixed-global 0.0001 behaviour would have produced 1000 pips (100x).
    old_global_bug = _timeout_pnl_pips(move, 0.0001)
    assert old_global_bug == pytest.approx(1000.0)
    assert jpy_pips * 100 == pytest.approx(old_global_bug)
    assert jpy_pips != pytest.approx(old_global_bug)

    # Non-JPY behaviour is unchanged from the previous fixed-0.0001 constant.
    assert non_jpy_pips == pytest.approx(old_global_bug)


def test_old_fixed_global_would_fail_for_jpy() -> None:
    # Guard-style: asserting the JPY pip size is not the old global proves the
    # bug (applying 0.0001 to a JPY cross) can no longer pass silently.
    assert pip_size_for("CHF_JPY") == 0.01
    assert pip_size_for("CHF_JPY") != 0.0001


# ---------------------------------------------------------------------------
# 3. Label / scoring consistency (one pip flows to TP/SL, timeout MTM, PnL)
# ---------------------------------------------------------------------------


def _ramp_bars(n: int = 80) -> list[dict]:
    """Deterministic upward BA ramp with enough amplitude to hit barriers."""
    bars: list[dict] = []
    mid = 1.0
    for _ in range(n):
        mid += 0.0009
        half = 0.00006
        o = mid
        c = mid + 0.0004
        hi = c + 0.0003
        lo = o - 0.0002
        bars.append(
            {
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
    return bars


def test_label_class_is_pip_agnostic_but_pnl_scales_with_pip() -> None:
    bars = _ramp_bars()
    kw = dict(horizon=20, tp_mult=1.5, sl_mult=1.0)
    jpy = bulk_labels(bars, pip_size=0.01, **kw)
    non_jpy = bulk_labels(bars, pip_size=0.0001, **kw)

    assert len(jpy) == len(non_jpy) == len(bars)
    for a, b in zip(jpy, non_jpy, strict=True):
        # Barrier geometry (the class + eligibility) is price-unit / index-based,
        # so it is IDENTICAL across pip scales — labels/training are unaffected.
        assert a["label"] == b["label"]
        assert (a["exit_long_offset"], a["exit_short_offset"]) == (
            b["exit_long_offset"],
            b["exit_short_offset"],
        )
        if a["pnl_long_pips"] is None:
            assert b["pnl_long_pips"] is None
            continue
        # PnL (TP/SL + timeout MTM all via the same pip arg) scales EXACTLY 100x.
        assert b["pnl_long_pips"] == pytest.approx(a["pnl_long_pips"] * 100.0)
        assert b["pnl_short_pips"] == pytest.approx(a["pnl_short_pips"] * 100.0)


def test_b2_eligibility_fix_preserved_across_pip_scales() -> None:
    # B-2: last eligible decision bar is n - horizon - 2 (range(n - horizon - 1)).
    n, horizon = 60, 20
    bars = _ramp_bars(n)
    recs = bulk_labels(bars, pip_size=0.01, horizon=horizon, tp_mult=1.5, sl_mult=1.0)
    last_eligible = max(i for i, r in enumerate(recs) if r["label"] is not None)
    assert last_eligible <= n - horizon - 2
    assert recs[n - horizon - 1]["label"] is None  # first ineligible tail bar


def test_bulk_labels_rejects_non_positive_pip() -> None:
    from scripts.ml_step4.labels import LabelContractError

    with pytest.raises(LabelContractError):
        bulk_labels(_ramp_bars(40), pip_size=0.0, horizon=20, tp_mult=1.5, sl_mult=1.0)


# ---------------------------------------------------------------------------
# 4. Evidence / manifest metadata
# ---------------------------------------------------------------------------


def test_manifest_records_per_pair_pip_map() -> None:
    mapping = {"EUR_USD": 0.0001, "USD_JPY": 0.01}
    m = manifest.build_run_manifest(
        mode="real_first_run", seeds={"data_ordering": "det"}, pip_size_by_pair=mapping
    )
    assert m["pip_size_by_pair"] == mapping
    assert m["global_pip_size_authoritative_for_all_pairs"] is False
    assert m["pip_size_convention"] == "0.01 if pair endswith _JPY else 0.0001"


def test_manifest_without_pip_map_omits_field() -> None:
    m = manifest.build_run_manifest(mode="fixture_rehearsal", seeds={"s": 1})
    assert "pip_size_by_pair" not in m


def test_manifest_rejects_bad_pip_map() -> None:
    with pytest.raises(ManifestError):
        manifest.build_run_manifest(mode="real", seeds={"s": 1}, pip_size_by_pair={})
    with pytest.raises(ManifestError):
        manifest.build_run_manifest(mode="real", seeds={"s": 1}, pip_size_by_pair={"EUR_USD": 0.0})


def test_end_to_end_records_mixed_scale_pip_metadata(tmp_path: Path) -> None:
    pytest.importorskip("lightgbm")
    from scripts.ml_step4.body import run_first_run_365d_ba

    # A mixed-scale provider: one non-JPY pair + one JPY-cross pair.
    prov = _provider(tmp_path / "data", pairs=("EUR_USD", "USD_JPY"), n=3000)
    prov.verify()
    out = tmp_path / "out"
    run_first_run_365d_ba(provider=prov, out_dir=str(out), code_sha="0" * 40, real=True)

    prov_report = json.loads((out / "ml_step4_leakage_provenance_report.json").read_text("utf-8"))
    assert prov_report["pip_size_by_pair"] == {"EUR_USD": 0.0001, "USD_JPY": 0.01}
    assert prov_report["global_pip_size_authoritative_for_all_pairs"] is False

    run_manifest = json.loads((out / "ml_step4_run_manifest.json").read_text("utf-8"))
    assert run_manifest["pip_size_by_pair"] == {"EUR_USD": 0.0001, "USD_JPY": 0.01}
    assert run_manifest["global_pip_size_authoritative_for_all_pairs"] is False

    metrics_report = json.loads((out / "ml_step4_metrics_report.json").read_text("utf-8"))
    per_pair = {
        d["pair"]: d for d in metrics_report["diagnostics"]["per_pair_data_summary"]["value"]
    }
    assert per_pair["USD_JPY"]["pip_size"] == 0.01
    assert per_pair["USD_JPY"]["pip_size_kind"] == "jpy_cross"
    assert per_pair["EUR_USD"]["pip_size"] == 0.0001
    assert per_pair["EUR_USD"]["pip_size_kind"] == "non_jpy"

    # All evidence remains scrub-clean; PR #421 invalid evidence is untouched
    # (this writes only to the tmp out dir).
    for name in evidence.EXPECTED_EVIDENCE_FILES:
        if name.endswith(".json"):
            evidence.assert_clean(json.loads((out / name).read_text("utf-8")))


# ---------------------------------------------------------------------------
# 5. Regression — real mode stays disabled; no run/train/holdout triggered here
# ---------------------------------------------------------------------------


def test_real_mode_still_refused_via_cli(capsys) -> None:
    from scripts.ml_step4 import execute_365d_ba

    # Neither the bare invocation nor --execute may run anything.
    assert execute_365d_ba.main([]) != 0
    assert execute_365d_ba.main(["--execute"]) != 0


# ---------------------------------------------------------------------------
# 6. Import / source guard
# ---------------------------------------------------------------------------

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "ml_step4"


def test_body_scoring_uses_per_pair_authority_not_fixed_global() -> None:
    src = (_SCRIPTS / "body.py").read_text(encoding="utf-8")
    # body.py must route pip conversion through the per-pair authority ...
    assert "pip_size_for" in src
    assert "pip_size_map" in src
    # ... and must NOT import or use the fixed-global PIP_SIZE constant, nor a
    # bare fixed pip literal, on the scoring path. (The only ``0.0001`` allowed
    # is inside the human-readable convention string recorded in evidence.)
    assert "PIP_SIZE" not in src
    assert "pip_size=PIP_SIZE" not in src
    assert "pip_size=0.0001" not in src
    assert "pip_size=0.01" not in src


def test_data_adapter_pip_literals_confined_to_authority() -> None:
    src = (_SCRIPTS / "data_adapter.py").read_text(encoding="utf-8")
    # The pip-conversion branches are the named constants inside the authority.
    assert "_PIP_JPY: Final[float] = 0.01" in src
    assert "_PIP_NON_JPY: Final[float] = 0.0001" in src
    assert "def pip_size_for(pair: str) -> float:" in src
    # PIP_SIZE survives ONLY as the fixture synthetic-price generation scale,
    # explicitly documented as NOT a pip-conversion authority.
    assert "NOT a pip-conversion" in src
