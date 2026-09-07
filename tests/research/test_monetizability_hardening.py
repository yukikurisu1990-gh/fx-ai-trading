"""The monetizability package — the tests that had to exist after review.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

An independent review role mutated the package 25 ways and **ten survived all
209 tests** — four of them leakage mutants, and the whole of `volume_info`,
which no test in the repository imported. It also found a bypass in the reader
this package added, present identically in the three merged sibling readers.

Each test below names the mutation it kills, and every one asserts on behaviour.
"""

from __future__ import annotations

import importlib
import json

import numpy as np
import pandas as pd
import pytest

from scripts.research.exploratory_m15 import bars as bars_module
from scripts.research.exploratory_m15 import volume as volume_reader
from scripts.research.monetizability import driver, geometry, oracle, volume_info
from scripts.research.round_b_prime import nulls, retrace
from tests.research.test_monetizability import (
    _DECIDING,
    REFUSALS,
    _bloc_input,
    _geometry_input,
)


@pytest.fixture(scope="module")
def walk() -> pd.DataFrame:
    frame = nulls.random_walk_frame(20_000, np.random.default_rng(5))
    frame["roundtrip_cost"] = 2.5
    return frame


# --------------------------------------------------------------- the bypass


class _Sneaky(str):
    """A `str` whose value is the declared bound and whose ordering lies.

    It passes every guard, because the guards compare **parsed dates**. It
    defeated the scan in all four readers, which compared the caller's object.
    """

    def __lt__(self, other: object) -> bool:
        return False

    def __gt__(self, other: object) -> bool:
        return False

    def __le__(self, other: object) -> bool:
        return False

    def __ge__(self, other: object) -> bool:
        return True


#: one row inside each of the three authorised spans, and three that are not
_PROBE_DAYS = [
    "2016-06-02",  # the fresh pool
    "2021-04-26",  # momentum
    "2024-01-01",  # supplemental
    "2025-06-01",  # development
    "2025-12-29",  # the historical OOS slice
    "2026-05-20",  # the forward epoch
]


def _archive(tmp_path, days: list[str]):
    path = tmp_path / "candles_EUR_USD_M1_3650d_BA.jsonl"
    path.write_text(
        "".join(
            json.dumps(
                {
                    "time": f"{day}T00:00:00.000000000Z",
                    "volume": 1,
                    **dict.fromkeys(bars_module.PRICE_KEYS, 1.0),
                }
            )
            + "\n"
            for day in days
        ),
        encoding="utf-8",
    )
    return path


def test_the_scan_compares_the_parsed_bound_not_the_callers_object(tmp_path, monkeypatch) -> None:
    """Kills the `str`-subclass bypass in the reader this package added.

    The guards were hardened against exactly this and the **scans** were not: a
    subclass whose value is the declared span passes `route.guard` and then
    answers `False` to both `day < lo` and `day > hi`, so every row in the file
    is decoded. Measured before the fix: 6 of 6 rows returned, including the
    fresh pool, the OOS slice and the forward epoch.
    """
    path = _archive(tmp_path, _PROBE_DAYS)
    route = volume_reader.ROUTES["momentum_2021_2023"]
    monkeypatch.setitem(
        volume_reader.ROUTES, "momentum_2021_2023", route._replace(source=lambda _pair: path)
    )
    plain = volume_reader.read_m1_volume("momentum_2021_2023", "EUR_USD")
    sneaky = volume_reader.read_m1_volume(
        "momentum_2021_2023", "EUR_USD", start=_Sneaky(route.start), end=_Sneaky(route.end)
    )
    assert len(plain) == 1
    assert len(sneaky) == len(plain), (
        f"a str subclass read {len(sneaky)} rows where the plain bound reads {len(plain)}"
    )
    assert str(sneaky["ts"].iloc[0].date()) == "2021-04-26"


@pytest.mark.parametrize(
    ("module_name", "start_attr", "end_attr"),
    [
        ("bars", "DEVELOPMENT_START_UTC", "DEVELOPMENT_END_UTC"),
        ("supplemental", "SUPPLEMENTAL_START_UTC", "SUPPLEMENTAL_END_UTC"),
        ("momentum", "MOMENTUM_START_UTC", "MOMENTUM_END_UTC"),
    ],
)
def test_the_three_sibling_readers_compare_the_parsed_bound_too(
    tmp_path, monkeypatch, module_name: str, start_attr: str, end_attr: str
) -> None:
    """The same bypass was present in all three merged readers. It is closed."""
    module = importlib.import_module(f"scripts.research.exploratory_m15.{module_name}")
    path = _archive(tmp_path, _PROBE_DAYS)
    monkeypatch.setattr(module, "source_path", lambda _pair: path)
    start = getattr(module, start_attr)
    end = getattr(module, end_attr)
    plain = module.read_m1("EUR_USD", start=start, end=end)
    sneaky = module.read_m1("EUR_USD", start=_Sneaky(start), end=_Sneaky(end))
    assert len(sneaky) == len(plain), (
        f"{module_name}.read_m1 returned {len(sneaky)} rows for a str subclass "
        f"against {len(plain)} for the plain bound"
    )


def test_the_shape_check_is_not_merely_decorative(tmp_path, monkeypatch) -> None:
    """Kills the removal of `utc_date` from the reader.

    A malformed bound must not reach a file, and the **parsed** bound must be
    what the scan uses — so removing the call has to fail here whether or not
    the route guard is reached first.
    """
    path = _archive(tmp_path, _PROBE_DAYS)
    route = volume_reader.ROUTES["development_2025"]
    monkeypatch.setitem(
        volume_reader.ROUTES, "development_2025", route._replace(source=lambda _pair: path)
    )
    for bad in ("2025", "2025-12-2", "2025-04-25T00", " 2025-04-25", "２０２５-04-25"):
        with pytest.raises(REFUSALS):
            volume_reader.read_m1_volume("development_2025", "EUR_USD", start=bad, end=route.end)


def test_a_cached_parquet_is_validated_before_it_is_served(tmp_path, monkeypatch) -> None:
    """Kills an unvalidated cache branch in `build_cache`.

    A cached file is a file on disk like any other. Validating only the branch
    that just produced it means a stale or mislabelled cache is served
    unchecked — and a review role made `build_cache` report the OOS slice and
    the forward epoch as the development panel's data.
    """
    monkeypatch.setattr(volume_reader, "CACHE_DIR", tmp_path)
    poisoned = pd.DataFrame(
        {
            "ts": pd.to_datetime(["2025-12-29T00:00:00Z", "2026-05-20T00:00:00Z"], utc=True),
            "volume": [1.0, 1.0],
            "volume_bars": [1, 1],
            "volume_missing": [0, 0],
        }
    )
    poisoned.to_parquet(tmp_path / "volume_development_2025_EUR_USD.parquet", index=False)
    with pytest.raises(volume_reader.VolumeSpanError):
        volume_reader.build_cache("development_2025", pairs=("EUR_USD",))
    with pytest.raises(volume_reader.VolumeSpanError):
        volume_reader.load("development_2025", "EUR_USD")


# ------------------------------------------------------------------- leakage


def _ramp_after(frame: pd.DataFrame, bar: int) -> pd.DataFrame:
    """Displace every bar strictly after `bar`, by a growing amount."""
    out = frame.copy()
    pip = float(out["pip_size"].iloc[0])
    steps = np.maximum(np.arange(len(out)) - bar, 0) * pip
    for column in ("mid_o", "mid_h", "mid_l", "mid_c"):
        out[column] = out[column].to_numpy() + steps
    out["roundtrip_cost"] = out["roundtrip_cost"].to_numpy() + (steps > 0) * 7.0
    return out


def test_no_b3_feature_reads_the_bar_the_position_opens_on(walk: pd.DataFrame) -> None:
    """Kills a design matrix built at `index + 1`, and a lost entry latency.

    The original causality test perturbed the frame and checked `gross`, never
    the design matrix — so the eight features had no regression standing behind
    them at all, and a mutant that read them one bar late survived 209 tests.
    """
    horizon = 12
    base = oracle.basis(walk)
    events = oracle.horizon_events(base, horizon=horizon, phase=0)
    assert events is not None
    target = int(events["index"][40])

    after_basis = oracle.basis(_ramp_after(walk, target))
    after = oracle.horizon_events(after_basis, horizon=horizon, phase=0)

    design_before = oracle._features(base, events["index"][:41], events["move_sigma"][:41])
    design_after = oracle._features(after_basis, after["index"][:41], after["move_sigma"][:41])
    assert np.allclose(design_before, design_after), (
        "a B-3 feature moved when only bars strictly after the decision bar changed"
    )
    #: and the probe is live — that same event's outcome and cost both move
    assert not np.isclose(events["gross"][40], after["gross"][40])
    assert not np.isclose(events["unit_cost"][40], after["unit_cost"][40]), (
        "the cost is charged at the decision bar rather than at the bar the position opens on"
    )


def test_an_anchor_position_opens_after_the_anchor(walk: pd.DataFrame) -> None:
    """Kills an entry moved onto the anchor bar itself.

    A perturbation cannot separate the two candidates -- displacing the bars
    after the anchor moves the exit price either way -- so the entry price is
    recovered from the recorded `gross` by arithmetic and compared with both.
    """
    base = oracle.basis(walk)
    found = retrace.find_anchors(walk, 1.5)
    events = oracle.anchor_events(base, found)
    assert events is not None and len(events["gross"]) > 5
    close = walk["mid_c"].to_numpy()
    pip = float(walk["pip_size"].iloc[0])

    #: `anchor_events` drops anchors whose window is empty, so the expected
    #: arrays are filtered the same way rather than read off `found` directly
    anchors = found["anchor"].to_numpy(dtype=int)
    exits = np.minimum(anchors + 1 + found["observation_bars"].to_numpy(dtype=int), len(close) - 1)
    keep = (anchors + 1) < exits
    anchors, exits = anchors[keep], exits[keep]
    assert np.array_equal(anchors, events["index"])

    latent = np.abs(close[exits] - close[anchors + 1]) / pip
    immediate = np.abs(close[exits] - close[anchors]) / pip
    assert np.allclose(np.abs(events["gross"]), latent), (
        "the position appears to open at the anchor bar rather than the bar after it"
    )
    assert not np.allclose(np.abs(events["gross"]), immediate)


def test_a_horizon_position_opens_one_bar_after_the_decision(walk: pd.DataFrame) -> None:
    """Kills the removal of the one-bar entry latency.

    `gross` is recomputed from the closes for both candidate windows; only the
    latent one may match.
    """
    horizon = 12
    base = oracle.basis(walk)
    events = oracle.horizon_events(base, horizon=horizon, phase=0)
    assert events is not None
    close = walk["mid_c"].to_numpy()
    pip = float(walk["pip_size"].iloc[0])
    index = events["index"]

    latent = np.abs(close[index + 1 + horizon] - close[index + 1]) / pip
    immediate = np.abs(close[index + horizon] - close[index]) / pip
    assert np.allclose(np.abs(events["gross"]), latent), (
        "the held window does not start at the bar after the decision"
    )
    assert not np.allclose(np.abs(events["gross"]), immediate)


def test_the_horizon_grid_really_is_non_overlapping(walk: pd.DataFrame) -> None:
    """Kills a halved step, which would double-count every event."""
    base = oracle.basis(walk)
    for horizon in (1, 4, 12, 48):
        events = oracle.horizon_events(base, horizon=horizon, phase=0)
        assert events is not None
        assert set(np.diff(events["index"]).tolist()) == {horizon}


def test_panel_bounds_really_averages_over_distinct_phases(walk: pd.DataFrame, monkeypatch) -> None:
    """Kills a collapse of the phase offsets inside `panel_bounds` itself.

    Checking offsets a test computes for itself proves nothing about the call
    site, so the phases `panel_bounds` actually passes are recorded.
    """
    seen: list[int] = []
    original = oracle.horizon_events

    def record(built, *, horizon, phase):
        seen.append(phase)
        return original(built, horizon=horizon, phase=phase)

    monkeypatch.setattr(oracle, "horizon_events", record)
    oracle.panel_bounds(
        {"EUR_USD": walk.copy()}, trading_days=200, horizons=(48,), thresholds=(), phases=4
    )
    assert len(set(seen)) == 4, f"panel_bounds used phases {sorted(set(seen))}"
    assert max(seen) > 0


# ------------------------------------------------------------------ Stage 1C


def _volume_panel(seed: int = 2, *, informative: bool) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    panel: dict[str, pd.DataFrame] = {}
    for name in ("EUR_USD", "USD_JPY"):
        frame = nulls.random_walk_frame(20_000, rng)
        forward = np.abs(np.diff(frame["mid_c"].to_numpy(), append=np.nan))
        signal = np.nan_to_num(forward, nan=0.0) * 1e5 if informative else 0.0
        frame["volume"] = signal + rng.normal(500.0, 50.0, len(frame))
        frame["volume_bars"] = 15
        frame["volume_missing"] = 0
        panel[name] = frame
    return panel


def test_the_volume_forward_target_is_forward(walk: pd.DataFrame) -> None:
    """Kills a backward target. Nothing in the repository imported `volume_info`."""
    frame = walk.copy()
    frame["volume"] = 100.0
    index = np.arange(500, 600)
    targets = volume_info._forward_targets(frame, index)
    pip = float(frame["pip_size"].iloc[0])
    close = frame["mid_c"].to_numpy()
    expected = (close[index + 1] - close[index]) / pip
    assert np.allclose(targets["signed_next_return"], expected)
    assert np.allclose(targets["abs_next_return"], np.abs(expected))


def test_the_incremental_test_finds_a_planted_relation_and_not_a_missing_one() -> None:
    """Kills an inert `incremental`, and a backward target, behaviourally."""
    planted = volume_info.incremental(_volume_panel(informative=True), draws=30)
    assert planted["abs_next_return"]["studentized"] > 5.0
    assert planted["abs_next_return"]["pairs_same_sign"] == 2

    empty = volume_info.incremental(_volume_panel(informative=False), draws=30)
    assert abs(empty["abs_next_return"]["studentized"]) < 3.0


def test_the_conservative_null_is_the_one_reported() -> None:
    """A permutation understates its own spread on a serially dependent series."""
    row = volume_info.incremental(_volume_panel(informative=True), draws=30)["abs_next_return"]
    assert row["studentized"] == row["block_shift"]["studentized"]
    assert row["null_sd"] == row["block_shift"]["null_sd"]
    assert "permutation" in row


def test_the_redundancy_design_carries_every_control_the_plan_names() -> None:
    """Kills a dropped control, which would inflate the residual's content."""
    panel = _volume_panel(informative=True)
    built = volume_info._design(next(iter(panel.values())))
    assert built is not None
    _target, design, _index = built
    #: realised volatility, spread, |move|, and two harmonics of the session
    assert design.shape[1] == 7
    assert 0.0 <= volume_info.redundancy(panel)["median_r2"] <= 1.0


# ------------------------------------------------------------------- the gate


def _gate_input(b3_excess: float, jpy: float, non_jpy: float, tail: float = 0.2) -> dict:
    return {
        panel: {
            "horizon_48": {
                "real": {
                    "median_cost": 2.5,
                    "b3_top10_day_share": tail,
                    "b3_JPY_net_per_event": jpy,
                    "b3_non_JPY_net_per_event": non_jpy,
                    "b3_largest_pair_share": 0.3,
                },
                "null": {"b3_net_per_event": {"real_minus_null": b3_excess}},
            }
        }
        for panel in _DECIDING
    }


def test_e4_is_computed_and_can_kill_a_population() -> None:
    """The clause that was in the frozen plan and was not implemented.

    It is the clause that decides the only population which cleared E1′ on a
    point estimate, and the first version of the gate emitted E1 and E3 only
    while its docstring claimed all four.
    """
    passing = driver._economic_gate(_gate_input(2.0, jpy=+5.0, non_jpy=+3.0))["horizon_48"]
    assert passing["E1_excess_at_least_half_a_cost"] is True
    assert passing["E4_both_blocs_positive"] is True

    #: the measured split on the one population that cleared E1′
    split = driver._economic_gate(_gate_input(2.0, jpy=+17.3, non_jpy=-3.96))["horizon_48"]
    assert split["E1_excess_at_least_half_a_cost"] is True
    assert split["E3_tail_share_below_ceiling"] is True
    assert split["E4_both_blocs_positive"] is False


def test_every_clause_is_in_the_pass_predicate() -> None:
    """Kills a clause dropped from `passing` rather than from the gate.

    E4 was absent from the gate entirely at first. A conjunct inlined in the
    driver is a conjunct nothing can measure, so the predicate is its own
    function and each clause is switched off in turn here.
    """
    clean = {
        level: driver._economic_gate(_gate_input(2.0, jpy=+5.0, non_jpy=+3.0))
        for level in ("x1.0", "x2.0")
    }
    assert driver._passing(clean) == ["horizon_48"]

    for clause in (
        "E1_excess_at_least_half_a_cost",
        "E3_tail_share_below_ceiling",
        "E4_both_blocs_positive",
    ):
        broken = {level: {"horizon_48": dict(row["horizon_48"])} for level, row in clean.items()}
        broken["x1.0"]["horizon_48"][clause] = False
        assert driver._passing(broken) == [], f"{clause} is not read by the pass predicate"

    at_2c = {level: {"horizon_48": dict(row["horizon_48"])} for level, row in clean.items()}
    at_2c["x2.0"]["horizon_48"]["E1_excess_at_least_half_a_cost"] = False
    assert driver._passing(at_2c) == []


def test_the_gate_reports_single_pair_concentration() -> None:
    """A bloc mean can be positive while one pair carries more than the total."""
    row = driver._economic_gate(_gate_input(2.0, jpy=+5.0, non_jpy=+3.0))["horizon_48"]
    assert row["b3_largest_pair_share"] == dict.fromkeys(_DECIDING, 0.3)


def test_the_tail_share_is_taken_on_b3s_own_net() -> None:
    """Kills the positive-parts base, which is meaningless when B-3 loses.

    `_tail_share` returns NaN on a non-positive total, so a selection whose net
    is negative must report no share at all -- the first version reported 0.96
    for one whose net was -10.35, because it summed the winners and dropped the
    losers out of the base.
    """
    stamps = pd.to_datetime(
        ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"], utc=True
    ).to_numpy()
    net = np.array([+10.0, -30.0, +5.0, -1.0])
    taken = np.array([True, True, True, True])
    assert float(net[taken].sum()) < 0

    on_net = oracle._tail_share(stamps, np.where(taken, net, 0.0))
    on_positive_parts = oracle._tail_share(stamps, np.where(taken, np.maximum(net, 0.0), 0.0))
    assert on_net != on_net, "a tail share was reported on a non-positive base"
    assert on_positive_parts == 1.0


def test_bounds_passes_b3s_own_net_to_the_tail_share(walk: pd.DataFrame, monkeypatch) -> None:
    """The same, pinned at the **call site** rather than in the helper.

    `_linear_selection` is replaced by one that takes everything, so the taken
    net is exactly the population's net -- which is negative here, since take-all
    loses a spread per event on a random walk. A base built from the winners
    alone would report a share; B-3's own net must report none.
    """
    base = oracle.basis(walk)
    events = oracle.horizon_events(base, horizon=12, phase=0)
    assert events is not None

    def take_everything(_built, _events, net):
        return {
            "selected": int(len(net)),
            "net": float(net.sum()),
            "net_per_event": float(net.mean()),
            "taken": np.ones(len(net), dtype=bool),
        }

    monkeypatch.setattr(oracle, "_linear_selection", take_everything)
    row = oracle.bounds(base, events, trading_days=200, cost_multiplier=1.0)
    assert row["b3_selection_net"] < 0, "the fixture does not produce a losing selection"
    share = row["b3_top10_day_share"]
    assert share != share, (
        f"a tail share of {share} was reported for a selection whose net is "
        f"{row['b3_selection_net']}"
    )


def test_the_event_rate_uses_the_panels_own_calendar() -> None:
    """FX trades about 312 days a year, not the 252 of an equity calendar."""
    assert oracle.TRADING_DAYS_PER_YEAR == 312.0


def test_2025_cannot_reach_a_verdict_even_if_it_is_passed_in() -> None:
    """Kills a caller handing `PANELS` to the verdict instead of the deciding pair."""
    geometry_input = _geometry_input(+0.9, 9.0)
    geometry_input["development_2025"] = geometry_input[_DECIDING[0]]
    blocs = _bloc_input(+0.9)
    for k in blocs:
        blocs[k]["development_2025"] = blocs[k][_DECIDING[0]]
    two = geometry.verdict(geometry_input, blocs, driver.DECIDING_PANELS)
    three = geometry.verdict(geometry_input, blocs, driver.PANELS)
    assert two["surviving_thresholds"] == three["surviving_thresholds"]
    assert driver.DECIDING_PANELS == _DECIDING


def test_a_clause_that_cannot_be_evaluated_does_not_count_as_a_pass() -> None:
    """An unavailable clause must not silently let a threshold through."""
    bare = _geometry_input(+0.9, 9.0)
    for panel in bare:
        for cell in bare[panel].values():
            #: `_geometry_input` shares one cell object across the thresholds,
            #: so the key is gone after the first pop
            cell["null"].pop("median_retrace_sigma_excluding_top_10_days", None)
    verdict = geometry.verdict(bare, {}, _DECIDING)
    for row in verdict["per_threshold"].values():
        assert row["clause_4_day_trim"] is None
        assert row["clause_5_both_blocs"] is None
    assert verdict["surviving_thresholds"] == [], (
        "thresholds survived on clauses that were never evaluated"
    )
