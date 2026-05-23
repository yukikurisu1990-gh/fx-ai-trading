"""Stage 1 unit tests — F-4 D-1 PnL harness identity (static + functional)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts._verification_harness import pnl_identity as P  # noqa: N812

# ---------------------------------------------------------------------------
# Static-source inspection — synthetic functions
# ---------------------------------------------------------------------------


def _good_barrier_pnl(row):
    # Required tokens: bid_h, ask_l, ask_h, bid_l (all present in source)
    if row.get("direction") == "long":
        return row["bid_h"] - row["ask_l"]
    return row["ask_h"] - row["bid_l"]


def _good_precompute(df, pair_runtime_map):
    # Signature does NOT expose spread_factor or mid_to_mid
    return df.get("realised_pnl")


def _bad_barrier_pnl_missing_token(row):
    # Intentionally missing required identifiers.
    return row["bid_h"] - row["bid_l"]


def _bad_precompute_with_spread_factor(df, pair_runtime_map, spread_factor=1.0):
    return df.get("realised_pnl")


def _bad_precompute_with_mid_to_mid(df, pair_runtime_map, mid_to_mid=False):
    return df.get("realised_pnl")


def test_static_inspection_passes_on_good_pair():
    payload = P.verify_pnl_harness_source(_good_barrier_pnl, _good_precompute)
    assert payload["schema_version"] == "v2-expanded-1.0"
    assert payload["compute_realised_barrier_pnl"]["required_tokens_present"] == list(
        P.REQUIRED_BARRIER_TOKENS
    )


def test_static_inspection_halts_on_missing_token():
    with pytest.raises(P.PnLHarnessIdentityError):
        P.verify_pnl_harness_source(_bad_barrier_pnl_missing_token, _good_precompute)


def test_static_inspection_halts_on_spread_factor_param():
    with pytest.raises(P.PnLHarnessIdentityError):
        P.verify_pnl_harness_source(_good_barrier_pnl, _bad_precompute_with_spread_factor)


def test_static_inspection_halts_on_mid_to_mid_param():
    with pytest.raises(P.PnLHarnessIdentityError):
        P.verify_pnl_harness_source(_good_barrier_pnl, _bad_precompute_with_mid_to_mid)


def test_write_pnl_harness_identity_artifact(tmp_path: Path):
    payload = P.verify_pnl_harness_source(_good_barrier_pnl, _good_precompute)
    out = tmp_path / "pnl_harness_identity.json"
    P.write_pnl_harness_identity_artifact(payload, out)
    assert out.is_file()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == "v2-expanded-1.0"


# ---------------------------------------------------------------------------
# D-1 functional fixtures — long/short × TP/SL
# ---------------------------------------------------------------------------


def test_fixture_long_tp_pnl():
    entry, nxt, tp, expected = P.fixture_long_tp()
    # Bar-1 ask_h must reach TP for a long-TP fill
    assert nxt.ask_h >= tp
    # Long-fill at TP; PnL = TP - entry_ask
    assert (tp - entry.ask_o) == pytest.approx(expected, abs=1e-9)


def test_fixture_long_sl_pnl():
    entry, nxt, sl, expected = P.fixture_long_sl()
    # Bar-1 bid_l must reach SL for a long-SL fill (exit-sell at bid)
    assert nxt.bid_l <= sl
    # PnL = SL - entry_ask
    assert (sl - entry.ask_o) == pytest.approx(expected, abs=1e-9)


def test_fixture_short_tp_pnl():
    entry, nxt, tp, expected = P.fixture_short_tp()
    assert nxt.ask_l <= tp
    # PnL = entry_bid - TP
    assert (entry.bid_o - tp) == pytest.approx(expected, abs=1e-9)


def test_fixture_short_sl_pnl():
    entry, nxt, sl, expected = P.fixture_short_sl()
    assert nxt.bid_h >= sl
    # PnL = entry_bid - SL
    assert (entry.bid_o - sl) == pytest.approx(expected, abs=1e-9)


def test_fixture_non_zero_spread_distinguishes_executable_from_mid():
    case = P.fixture_non_zero_spread_executable_differs_from_mid()
    # Spread at entry: ask_o - bid_o = 100.0 - 99.5 = 0.5 > 0
    assert (case["entry"].ask_o - case["entry"].bid_o) == pytest.approx(0.5, abs=1e-9)
    # Executable bid/ask PnL != mid-price PnL
    assert case["discriminating"] is True
    assert case["executable_pnl_long"] != pytest.approx(
        case["mid_price_pnl_contaminated"], abs=1e-9
    )
    # The formal harness MUST return the executable value (+2.0), not the mid (+1.75)
    assert case["executable_pnl_long"] == pytest.approx(2.0, abs=1e-9)
    assert case["mid_price_pnl_contaminated"] == pytest.approx(1.75, abs=1e-9)
