"""The reframing record: arithmetic, catalogue, evidence map, document and boundaries agree.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Reads committed documents and artefacts only; no market data.
"""

from __future__ import annotations

import ast
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from scripts.research.edge_sources import (
    WORKFLOW_STATUS,
    candidates,
    capacity,
    driver,
    leverage,
    render,
)
from scripts.research.feasibility.inventory import catalogue
from scripts.research.round_a.ledger import LEDGER

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "scripts/research/edge_sources"
DOCUMENT = ROOT / "docs/research/m15_next_edge_source_reframing.md"
ARTIFACT = ROOT / "artifacts/research/edge_sources/reframing.json"
AVAILABILITY = ROOT / "artifacts/research/edge_sources/public_data_availability.json"
PROBE = ROOT / "scripts/research/public_data_probe/availability_check.py"
INVENTORY = ROOT / "artifacts/research/feasibility/inventory.json"

#: Where each merged-PR reference is recorded on master.
PR_SOURCES: dict[str, str] = {
    "#471": "docs/research/m15_economic_edge_source_expansion_results.md",
    "#475": "docs/research/m15_track_3_execution_frontier.md",
    "#476": "docs/design/m15_feasibility_gate_v2.md",
    "#477": "docs/research/m15_track_2_non_usd_surprise_results.md",
    "#478": "docs/research/m15_decision_grade_research_inventory.md",
    "#482": "docs/research/m15_track1_continuous_portfolio_results.md",
}


@pytest.fixture(scope="module")
def document() -> str:
    return DOCUMENT.read_text(encoding="utf-8")


class TestTheDocumentTablesAreRenderedFromThePackage:
    @pytest.mark.parametrize("name", sorted(render.TABLES))
    def test_a_table(self, document: str, name: str) -> None:
        match = re.search(rf"<!-- table:{name} -->\n(.*?)\n<!-- /table -->", document, flags=re.S)
        assert match, name
        assert match.group(1).splitlines() == render.TABLES[name]()

    def test_the_artifact_is_the_build(self) -> None:
        committed = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        rebuilt = json.loads(json.dumps(driver.build(), ensure_ascii=False, sort_keys=True))
        assert committed == rebuilt


class TestTheCapacityArithmetic:
    def test_the_calibration_is_the_track_1_record(self) -> None:
        measured = capacity.calibration_from_record(ROOT)
        per_gross = measured["realized_annual_vol"] / measured["mean_currency_gross"]
        assert pytest.approx(per_gross, abs=1e-6) == capacity.VOL_PER_UNIT_GROSS
        assert (
            pytest.approx(measured["raw_to_neutralised_corr"], abs=0.01)
            == capacity.TRANSFER_COEFFICIENT
        )
        assert pytest.approx(3.406) == capacity.COST_PER_TURNOVER_UNIT_BP

    def test_the_drag_reproduces_track_1_gross_minus_net(self) -> None:
        measured = capacity.calibration_from_record(ROOT)
        drag = capacity.cost_ir_drag(measured["turnover_per_unit_gross"])
        assert drag == pytest.approx(measured["gross_sharpe"] - measured["net_sharpe"], abs=0.002)

    @pytest.mark.parametrize("breadth", [4.0, 2.0])
    @pytest.mark.parametrize("half_life", capacity.HALF_LIVES_DAYS)
    def test_the_required_daily_ic_solves_back_to_the_net_sharpe(
        self, half_life: float, breadth: float
    ) -> None:
        law = capacity.band_law(half_life)
        ic = capacity.required_daily_ic(0.5, half_life, breadth)
        gross = (
            capacity.TRANSFER_COEFFICIENT
            * law["capture"]
            * ic
            * math.sqrt(breadth * capacity.TRADING_DAYS)
        )
        assert gross - capacity.cost_ir_drag(law["turnover"]) == pytest.approx(0.5, abs=1e-9)

    def test_narrower_breadth_needs_root_two_more_ic(self) -> None:
        ratio = capacity.required_daily_ic(0.5, 20.0, 2.0) / capacity.required_daily_ic(0.5, 20.0)
        assert ratio == pytest.approx(math.sqrt(2.0))

    def test_the_horizon_ic_is_the_ar1_correlation(self) -> None:
        assert capacity.horizon_ic(0.03, 1.0) == pytest.approx(0.03)
        rho = 0.5 ** (1.0 / 20.0)
        expected = 0.03 * sum(rho**k for k in range(20)) / math.sqrt(20.0)
        assert capacity.horizon_ic(0.03, 20.0) == pytest.approx(expected)
        assert capacity.horizon_ic(0.03, 20.0) < 0.03 * math.sqrt(20.0)

    def test_slower_forecasts_trade_less(self) -> None:
        rows = capacity.continuous_book_table()["rows"]
        turnovers = [row["turnover_per_unit_gross"] for row in rows.values()]
        assert turnovers == sorted(turnovers, reverse=True)

    def test_return_is_sharpe_times_vol_and_leverage_is_vol_over_vol_per_gross(self) -> None:
        table = capacity.return_and_leverage_table()
        row = table["rows"]["vol_0.1"]
        assert row["annual_net_return"]["0.5"] == pytest.approx(0.05)
        assert row["risk_leverage_C"] == pytest.approx(0.10 / capacity.VOL_PER_UNIT_GROSS, abs=0.01)
        assert table["net_sharpe_needed_for_5pct"]["vol_0.1"] == 0.5

    def test_drawdown_falls_with_sharpe_and_scales_with_vol(self) -> None:
        low, high = capacity.gaussian_drawdown(0.3), capacity.gaussian_drawdown(0.8)
        assert high["median_max_drawdown_in_vol_units"] < low["median_max_drawdown_in_vol_units"]
        assert (
            high["simulated_probability_first_five_years_negative"]
            < low["simulated_probability_first_five_years_negative"]
        )
        rows = capacity.return_and_leverage_table()["rows"]
        assert (
            rows["vol_0.12"]["median_max_drawdown_10y"]["0.5"]
            > rows["vol_0.08"]["median_max_drawdown_10y"]["0.5"]
        )

    def test_the_event_book_edge_reproduces_the_sharpe(self) -> None:
        row = capacity.event_book(150.0, 3.0, 0.5)
        over_cost = row["required_edge_bp_charged_cost"] - capacity.EVENT_ROUND_TRIP_CHARGED_BP
        sharpe = over_cost * math.sqrt(150.0) / row["sd_per_event_bp"]
        assert sharpe == pytest.approx(0.5, abs=0.01)
        assert row["required_edge_bp_pair_cost"] < row["required_edge_bp_charged_cost"]
        assert (
            row["required_edge_bp_charged_cost_concentrated"] > row["required_edge_bp_charged_cost"]
        )
        assert row["gross_leverage_at_10pct_vol_concentrated"] < row["gross_leverage_at_10pct_vol"]

    def test_the_event_sd_uses_the_declared_event_day_multiple(self) -> None:
        assert capacity.EVENT_DAY_VOL_MULTIPLE == 1.5
        row = capacity.event_book(150.0, 3.0, 0.5)
        expected = capacity.DAILY_SD_ONE_SIDE_UNIT_BP * math.sqrt(1.5**2 + 2.0)
        assert row["sd_per_event_bp"] == pytest.approx(expected, abs=0.01)

    def test_share_of_days_is_poisson_not_currency_slots(self) -> None:
        row = capacity.event_book(34.4, 3.0, 0.5)
        concurrent = 34.4 * 3.0 / capacity.TRADING_DAYS
        assert row["share_of_days_with_a_position"] == pytest.approx(
            1.0 - math.exp(-concurrent), abs=1e-3
        )
        assert row["share_of_currency_slots"] < row["share_of_days_with_a_position"]

    def test_the_event_count_is_the_acquirable_banks_measured_rate(self) -> None:
        c01 = next(p for p in catalogue() if p.candidate_id.startswith("C01_"))
        assert (c01.events_per_year, 3.0) in capacity.EVENT_SCENARIOS
        assert c01.available_breadth == 4

    def test_the_probability_of_a_losing_window_is_the_closed_form(self) -> None:
        assert capacity.probability_negative(0.5, 5.0) == pytest.approx(0.132, abs=1e-3)
        simulated = capacity.gaussian_drawdown(0.5)[
            "simulated_probability_first_five_years_negative"
        ]
        assert simulated == pytest.approx(capacity.probability_negative(0.5, 5.0), abs=0.03)

    def test_the_sample_years_follow_t_equals_sharpe_root_years(self) -> None:
        assert capacity.sample_years_needed(0.5) == pytest.approx((1.645 / 0.5) ** 2, abs=0.01)
        assert capacity.sample_years_needed(0.5, 0.8) == pytest.approx(
            ((1.645 + 0.8416) / 0.5) ** 2, abs=0.01
        )


def _ledger_text(ref: str) -> str:
    entry = next(e for e in LEDGER if e["id"] == ref)
    return f"{entry['result']} {entry['status']}"


class TestTheEvidenceMap:
    def test_every_class_is_a_declared_one(self) -> None:
        assert {e.klass for e in candidates.EVIDENCE_MAP} <= set(candidates.EVIDENCE_CLASSES)

    @pytest.mark.parametrize("item", candidates.EVIDENCE_MAP, ids=lambda e: f"{e.ref}:{e.klass}")
    def test_every_status_is_quoted_from_its_source(self, item: candidates.Evidence) -> None:
        if item.ref == "—":
            assert item.klass == "UNTESTED"
            return
        if item.ref.startswith("H-"):
            source = _ledger_text(item.ref)
            if item.status.startswith(("CLOSED", "OPEN")):
                entry = next(e for e in LEDGER if e["id"] == item.ref)
                assert entry["status"].startswith(item.status.split(" ")[0])
                if item.status not in ("CLOSED", "OPEN"):
                    assert item.status in entry["status"]
                return
            assert item.status in source
            return
        if re.fullmatch(r"C\d\d", item.ref):
            inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
            match = next(
                c for c in inventory["candidates"] if c["candidate_id"].startswith(item.ref + "_")
            )
            assert match["verdict"] == item.status
            return
        source = (ROOT / PR_SOURCES[item.ref]).read_text(encoding="utf-8")
        assert item.status in source

    @pytest.mark.parametrize("item", candidates.EVIDENCE_MAP, ids=lambda e: f"{e.ref}:{e.klass}")
    def test_every_class_follows_its_source(self, item: candidates.Evidence) -> None:
        """An OPEN, SUSPENDED or underpowered record cannot be filed as something stronger."""
        if item.ref.startswith("H-"):
            entry = next(e for e in LEDGER if e["id"] == item.ref)
            if entry["status"].startswith("OPEN"):
                assert item.klass == "OPEN"
            else:
                assert item.klass in ("CLOSED", "NOT_SUPPORTED", "NOT_DECISION_GRADE")
            if "not a refutation" in entry["result"] or "UNRESOLVED" in entry["result"]:
                assert "検出力不足" in item.what, item.ref
            return
        if re.fullmatch(r"C\d\d", item.ref):
            plan = next(p for p in catalogue() if p.candidate_id.startswith(item.ref + "_"))
            expected = {
                "PRIOR_FAMILY_CLOSED": "CLOSED",
                "DATA_INTEGRITY_BLOCKED": "SUSPENDED",
                "OUT_OF_GATE_SCOPE": "UNTESTED",
                "NO_DECISION_GRADE_PASS_REGION": "NOT_DECISION_GRADE",
            }[item.status]
            if plan.suspended_by_decision:
                expected = "SUSPENDED"
            assert item.klass == expected, item.ref

    def test_the_inventory_conditions_are_disclosed(self) -> None:
        inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
        by_ref = {e.ref: e for e in candidates.EVIDENCE_MAP}
        for record in inventory["candidates"]:
            ref = record["candidate_id"][:3]
            if record["verdict"] != "NO_DECISION_GRADE_PASS_REGION" or ref not in by_ref:
                continue
            if record["conditions"]["economic_net_under_stress"] is False:
                assert "economic_net_under_stress" in by_ref[ref].what, ref

    #: Merged-PR references carry no machine-readable class, so each is pinned.
    PR_CLASSES: dict[tuple[str, str], str] = {
        ("#471", "EVENT_DAY_COST_ADVANTAGE_NOT_ESTABLISHED"): "NOT_SUPPORTED",
        (
            "#475",
            "passive 執行は、この 2 パネルで意味のあるコスト削減を与えられない。",
        ): "NOT_SUPPORTED",
        ("#475", "CLOCK_STRUCTURE_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER"): "SUSPENDED",
        ("#477", "NON_USD_SURPRISE_DATA_NOT_DECISION_GRADE_SKIP"): "SUSPENDED",
        ("#478", "CURRENT_SEEN_DATA_FX_RESEARCH_SPACE_EXHAUSTED"): "NOT_DECISION_GRADE",
        ("#482", "bundle は本来の目的（turnover 削減）は果たした"): "ENGINEERING_RESULT",
        ("#476", "FEASIBILITY_GATE_V2_PROSPECTIVE_ONLY"): "ENGINEERING_RESULT",
    }

    def test_the_merged_pr_references_keep_their_classes(self) -> None:
        found = {
            (e.ref, e.status): e.klass for e in candidates.EVIDENCE_MAP if e.ref.startswith("#")
        }
        assert found == self.PR_CLASSES

    def test_suspended_is_never_filed_as_closed(self) -> None:
        for item in candidates.EVIDENCE_MAP:
            if "NOT_DECISION_GRADE" in item.status or "SKIP" in item.status:
                assert item.klass in ("NOT_DECISION_GRADE", "SUSPENDED"), item

    def test_the_whole_inventory_is_mapped(self) -> None:
        refs = {e.ref for e in candidates.EVIDENCE_MAP}
        assert {p.candidate_id[:3] for p in catalogue()} <= refs


class TestTheCatalogue:
    def test_at_least_twenty_distinct_candidates(self) -> None:
        ids = [c.cid for c in candidates.CANDIDATES]
        names = [c.name for c in candidates.CANDIDATES]
        mechanisms = [c.mechanism for c in candidates.CANDIDATES]
        assert len(set(ids)) == len(ids)
        assert len(set(names)) == len(names)
        assert len(set(mechanisms)) == len(mechanisms)
        distinct = candidates.distinct_directions()
        assert len(distinct) >= 20
        by_id = {c.cid: c for c in candidates.CANDIDATES}
        assert all(not by_id[cid].increment_of for cid in distinct)
        assert all(by_id[cid].eligibility != candidates.EXCLUDED for cid in distinct)

    def test_the_renames_stay_excluded(self) -> None:
        excluded = {c.cid for c in candidates.CANDIDATES if c.eligibility == candidates.EXCLUDED}
        assert excluded == {"S11", "S19", "S23", "S24"}

    def test_a_candidate_on_a_suspended_family_is_not_eligible(self) -> None:
        suspended = {e.ref for e in candidates.EVIDENCE_MAP if e.klass == "SUSPENDED"}
        decided = {p.candidate_id[:3] for p in catalogue() if p.suspended_by_decision}
        for c in candidates.CANDIDATES:
            if set(c.overlap) & decided:
                assert c.eligibility == candidates.SUSPENDED_FAMILY, c.cid
        assert decided <= suspended

    def test_every_required_direction_is_evaluated(self) -> None:
        assert {c.direction for c in candidates.CANDIDATES} >= set("ABCDEFGHI")

    def test_every_overlap_reference_resolves(self) -> None:
        refs = {e.ref for e in candidates.EVIDENCE_MAP} | {c.cid for c in candidates.CANDIDATES}
        for c in candidates.CANDIDATES:
            for ref in c.overlap:
                assert ref in refs, (c.cid, ref)

    def test_an_excluded_candidate_overlaps_a_closed_or_unsupported_family(self) -> None:
        classes = {e.ref: e.klass for e in candidates.EVIDENCE_MAP}
        for c in candidates.CANDIDATES:
            if c.eligibility == candidates.EXCLUDED:
                assert any(classes.get(ref) in ("CLOSED", "NOT_SUPPORTED") for ref in c.overlap), (
                    c.cid
                )

    def test_scores_are_within_scale_and_computed_by_the_declared_weights(self) -> None:
        for c in candidates.CANDIDATES:
            for name in (*candidates.GAIN_WEIGHTS, *candidates.BURDEN_WEIGHTS):
                assert 1 <= getattr(c, name) <= 5, (c.cid, name)
        assert candidates.GAIN_WEIGHTS["p_real"] == candidates.GAIN_WEIGHTS["information_gain"] == 2

    def test_at_most_three_tracks_all_eligible_and_within_the_top_six(self) -> None:
        assert len(candidates.PROPOSED_TRACKS) <= 3
        ranks = {r["cid"]: r["rank"] for r in candidates.ranking()}
        by_id = {c.cid: c for c in candidates.CANDIDATES}
        for _, members in candidates.PROPOSED_TRACKS:
            for cid in members:
                assert by_id[cid].eligibility == candidates.ACTIVE
                assert ranks[cid] is not None and ranks[cid] <= 6
                assert not by_id[cid].increment_of

    def test_no_track_is_a_price_only_or_ml_first_hypothesis(self) -> None:
        by_id = {c.cid: c for c in candidates.CANDIDATES}
        for _, members in candidates.PROPOSED_TRACKS:
            for cid in members:
                assert by_id[cid].ml_role.startswith("不要")
                assert any(
                    word in by_id[cid].information
                    for word in ("金利", "CPI", "カレンダー", "利回り")
                ), cid


class TestTheBoundaries:
    #: Exact modules, and for project modules the exact names taken from them.
    ALLOWED_IMPORTS: dict[str, frozenset[str] | None] = {
        "__future__": None,
        "dataclasses": None,
        "functools": None,
        "json": None,
        "math": None,
        "pathlib": None,
        "sys": None,
        "typing": None,
        "numpy": None,
        "scripts.research.continuous_portfolio": frozenset({"CHARGED_ONE_WAY_BP", "construction"}),
        "scripts.research.feasibility.inventory": frozenset({"PAIR_ROUNDTRIP_BP"}),
        "scripts.research.edge_sources": frozenset(
            {
                "TARGET_NET_RETURN",
                "WORKFLOW_STATUS",
                "candidates",
                "capacity",
                "engineering_backlog",
                "leverage",
                "rerank",
            }
        ),
        #: the 2026-09-19 rerank reads the power arithmetic and the committed span day
        #: counts from its sibling; both are judgement and arithmetic modules that touch
        #: no market data. The day counts live in one module so the two cannot drift —
        #: an earlier draft duplicated them as literals and they disagreed.
        "scripts.research.edge_sources.rerank": frozenset(
            {
                "LONG_DECISION_DAYS",
                "RECENT_DECISION_DAYS",
                "TRADING_DAYS_PER_YEAR",
                "detectable_sharpe",
                "power_at",
            }
        ),
    }
    #: What the package may call on `construction`: signal-free calibration only.
    CONSTRUCTION_USES = frozenset(
        {
            "band_calibration",
            "BookConfig",
            "PAIRS_20",
            "CURRENCIES",
            "split_map",
            "capped_weights",
            "band_rebalance",
        }
    )
    FORBIDDEN_CALLS = frozenset(
        {
            "open",
            "urlopen",
            "build_opener",
            "read_table",
            "read_csv",
            "load",
            "loadtxt",
            "genfromtxt",
            "fromfile",
            "memmap",
            "__import__",
            "import_module",
            "eval",
            "exec",
            "run",
        }
    )

    def test_the_package_imports_nothing_that_reads_markets(self) -> None:
        for path in PACKAGE.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert self.ALLOWED_IMPORTS.get(alias.name, 0) is None, (
                            path.name,
                            alias.name,
                        )
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    assert module in self.ALLOWED_IMPORTS, (path.name, module)
                    names = self.ALLOWED_IMPORTS[module]
                    if names is not None:
                        for alias in node.names:
                            assert alias.name in names, (path.name, module, alias.name)

    def test_the_package_calls_no_reader_but_the_track_1_record(self) -> None:
        reads = 0
        for path in PACKAGE.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "construction"
                ):
                    assert node.attr in self.CONSTRUCTION_USES, (path.name, node.attr)
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
                assert name not in self.FORBIDDEN_CALLS, (path.name, name)
                if name == "getattr":
                    # a computed attribute name or target is how a denylist is evaded
                    assert not isinstance(node.args[0], ast.Call), path.name
                    assert isinstance(node.args[1], ast.Name), path.name
                assert not name.startswith(("read_parquet", "load_")), (path.name, name)
                if name.startswith("read"):
                    assert name == "read_text", (path.name, name)
                    reads += 1
        assert reads == 4
        leverage_source = (PACKAGE / "leverage.py").read_text(encoding="utf-8")
        assert leverage_source.count("read_text") == 3
        assert "MARGIN_RECORD" in leverage_source and "TRACK_1_RECORD" in leverage_source
        capacity_source = (PACKAGE / "capacity.py").read_text(encoding="utf-8")
        assert capacity_source.count("read_text") == 1
        assert "TRACK_1_RECORD" in capacity_source

    def test_importing_the_probe_touches_no_network(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import importlib.util
        import urllib.request

        attempts: list[object] = []

        def refuse(*args: object, **_: object) -> None:
            # recorded, because the probe's fetch swallows every exception it raises
            attempts.append(args)
            raise AssertionError("the probe reached the network on import")

        monkeypatch.setattr(urllib.request, "urlopen", refuse)
        monkeypatch.delenv("EDGE_SOURCES_PROBE_APPROVED", raising=False)
        spec = importlib.util.spec_from_file_location("availability_probe_under_test", PROBE)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert attempts == []
        assert module.main() == 2
        assert attempts == []

    FX_SERIES_PATTERN = re.compile(r"^(DEX|EX[A-Z]{2}US|EXUS|DTWEX|RBU|RNU|CCUS)", re.I)
    FX_SOURCE_PATTERN = re.compile(r"fx|eurofx|exchange|h10|spot_rate|forex", re.I)

    def test_the_availability_record_holds_no_fx_series(self) -> None:
        record: dict[str, Any] = json.loads(AVAILABILITY.read_text(encoding="utf-8"))
        for series in record["fred"]:
            assert not self.FX_SERIES_PATTERN.match(series), series
        for name, block in record["other"].items():
            assert not self.FX_SOURCE_PATTERN.search(name), name
            assert not self.FX_SOURCE_PATTERN.search(block["url"]), block["url"]
        assert "no FX series requested" in record["note"]
        assert record["probe_script"] == PROBE.relative_to(ROOT).as_posix()
        for block in record["fred"].values():
            assert set(block) <= {
                "label",
                "http_status",
                "frequency_text",
                "declared_range",
                "observation_start_field",
                "error",
            }

    def test_the_committed_probe_is_the_one_that_wrote_the_record(self) -> None:
        record: dict[str, Any] = json.loads(AVAILABILITY.read_text(encoding="utf-8"))
        tree = ast.parse(PROBE.read_text(encoding="utf-8"))
        literals: dict[str, Any] = {}
        for node in tree.body:
            if (
                isinstance(node, ast.Assign)
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id in ("FRED_SERIES", "OTHER_ENDPOINTS")
            ):
                literals[node.targets[0].id] = ast.literal_eval(node.value)
        assert set(literals["FRED_SERIES"]) == set(record["fred"])
        assert literals["OTHER_ENDPOINTS"] == {k: v["url"] for k, v in record["other"].items()}
        for series in literals["FRED_SERIES"]:
            assert not self.FX_SERIES_PATTERN.match(series), series

    def test_the_document_does_not_adopt_the_withdrawn_pause(self, document: str) -> None:
        assert "FX_SPOT_ACTIVE_ALPHA_RESEARCH_PAUSED" not in document
        assert "PAUSED" not in document.upper().replace(
            "FX_SPOT_ACTIVE_ALPHA_RESEARCH_CONTINUES", ""
        )
        assert f"`{WORKFLOW_STATUS}`" in document
        assert "**撤回された**" in document
        assert "研究は続く。Track 1 は失敗した。研究は終わっていない。" in document
        assert "**研究を止める提案ではない。**" in document
        assert "`FX_HAS_NO_EDGE` ではない" in document

    def test_the_protected_data_statement(self, document: str) -> None:
        assert (
            "fresh pool `2016-06-02 … 2021-04-25`、historical OOS、dead window、forward Formal Confirmation epoch は"  # noqa: E501
            in document
        )
        assert "一切読んでいない" in document
        assert "保護 span" in document and "**除外した**" in document

    def test_the_package_and_the_new_ledger_entries_carry_no_pause(self) -> None:
        for path in PACKAGE.glob("*.py"):
            source = path.read_text(encoding="utf-8").lower()
            assert "pause" not in source, path.name
            assert "reopen" not in source, path.name
        for ref in ("H-023", "H-024"):
            entry = next(e for e in LEDGER if e["id"] == ref)
            text = json.dumps(entry, ensure_ascii=False).lower()
            assert "pause" not in text and "reopen" not in text, ref

    def test_the_review_corrections_are_in_the_prose(self, document: str) -> None:
        assert "PR #483 は **merge せずに閉じた**" in document
        assert "`economic_net_under_stress` でも不合格（margin −0.63）" in document
        assert "**horizon だけで落ちたのは\n  C01 だけ**" in document
        assert "約 24.7 年" in document
        assert "**development screen**" in document
        assert "stop の条件に当たらなくても\n  stop とする" in document
        assert "Human + ChatGPT の新しい決定なしには行わず" in document
        assert "閉じた momentum" not in document and "（閉じた family）" not in document
        assert "上側信頼限界が年 5% 目標の net 0.5 を下回るとき" in document
        assert "検出力が足りる場合に限り" not in document
        assert (
            "C04（benchmark fix）・C05（month-end\n  rebalancing）が決定により停止・提案不可"
            in document
        )
        assert "取得要求そのものを終端 `< 2016-06-02` に制限する" in document
        assert (
            "**fitted model が unfitted rule に劣後するのは model の kill であって source の kill ではない**"  # noqa: E501
            in document
        )
        assert "**T-R の結果を読む前に凍結**" in document
        assert "**算術上の capacity はあるが、どの source にもそこに届く証拠は無い。**" in document
        assert "反証済み" not in document
        assert "取引開始は event の終了と利回り終値の遅い方より後" in document
        assert "保有データに臨時会合の flag は無く" in document
        assert "それができない系列は使わない" in document
        assert "全体を download してから filter" in document
        assert "decision-grade にならない" in document

    def test_the_conditional_track_says_so(self, document: str) -> None:
        assert "### T-V — 実質為替レート valuation（S13）— **D-1 が承認された場合のみ**" in document
        assert "D-1 が否決されれば T-V は外れ、提案は 2 track になる" in document


class TestTheLedgerRecordsTrackOneWithoutAPause:
    def test_h023(self) -> None:
        entry = next(e for e in LEDGER if e["id"] == "H-023")
        assert entry["status"].startswith("CLOSED")
        assert "PAUSE" not in entry["status"].upper()
        assert "not FX_HAS_NO_EDGE" in entry["status"]
        assert "TURNOVER_REDUCTION_MECHANISM_SUPPORTED, not ALPHA_SUPPORTED" in entry["status"]

    def test_h024_is_limited_to_five_twenty_sixty_days(self) -> None:
        entry = next(e for e in LEDGER if e["id"] == "H-024")
        assert entry["prespecified"] is False
        assert entry["horizon_family"] == "5, 20 and 60 days only"
        assert "not generalised to others" in entry["status"]
        assert "not to be revived as a next main research track" in entry["status"]
        assert "PAUSE" not in entry["status"].upper()


MARGIN_RECORD = ROOT / "artifacts/research/edge_sources/oanda_margin_rates.json"

#: Hand-verified against https://www.oanda.jp/course/currencypair (MT5 column) on
#: 2026-09-15 by the author and on 2026-09-16 by an independent review role.
VERIFIED_RATES: dict[str, float] = {
    **{
        pair: 0.04
        for pair in (
            "AUD_CAD",
            "AUD_JPY",
            "AUD_NZD",
            "AUD_USD",
            "CHF_JPY",
            "EUR_AUD",
            "EUR_CAD",
            "EUR_CHF",
            "EUR_JPY",
            "EUR_USD",
            "GBP_CHF",
            "NZD_JPY",
            "NZD_USD",
            "USD_CAD",
            "USD_CHF",
            "USD_JPY",
        )
    },
    **{pair: 0.05 for pair in ("EUR_GBP", "GBP_AUD", "GBP_JPY", "GBP_USD")},
}


def _independent_routing(rates: dict[str, float]) -> dict[str, float]:
    """The margin and exposure series recomputed here, not taken from the module."""
    pairs = leverage.construction.PAIRS_20
    currencies = leverage.construction.CURRENCIES
    pair_map = leverage.construction.split_map()
    incidence = np.zeros((len(pairs), len(currencies)))
    for row, pair in enumerate(pairs):
        base, quote = pair.split("_")
        incidence[row, currencies.index(base)] = 1.0
        incidence[row, currencies.index(quote)] = -1.0
    rate_vector = np.array([rates[p] for p in pairs])
    rho = 0.5 ** (1.0 / leverage.ROUTING_HALF_LIFE_DAYS)
    rng = np.random.default_rng(leverage.ROUTING_SEED)
    state = rng.standard_normal(len(currencies))
    held = None
    margin, exposure, gross = [], [], []
    for _ in range(leverage.ROUTING_DAYS):
        state = rho * state + math.sqrt(1 - rho * rho) * rng.standard_normal(len(currencies))
        target = leverage.construction.capped_weights(state, 0.25)
        held = (
            target.copy()
            if held is None
            else leverage.construction.band_rebalance(target, held, 0.10)
        )
        scale_ = np.abs(held).sum()
        signed = pair_map @ held / scale_
        margin.append(float(np.abs(signed) @ rate_vector))
        gross.append(float(np.abs(signed).sum()))
        exposure.append(float(np.abs(incidence.T @ signed).max()))
    return {
        "margin_mean": float(np.mean(margin)),
        "margin_p95": float(np.quantile(margin, 0.95)),
        "exposure_p95": float(np.quantile(exposure, 0.95)),
        "gross_mean": float(np.mean(gross)),
    }


class TestLeverageAndMargin:
    def test_the_broker_record_is_public_dated_and_covers_the_universe(self) -> None:
        record = json.loads(MARGIN_RECORD.read_text(encoding="utf-8"))
        assert record["retrieved_utc"].startswith("2026-")
        for source in record["sources"].values():
            assert source["url"].startswith("https://www.oanda.jp/")
        rates = {p: r["margin_rate"] for p, r in record["research_universe"].items()}
        assert rates == VERIFIED_RATES
        for pair, row in record["research_universe"].items():
            assert row["margin_rate"] == record["pairs"][pair]["margin_rate_mt5"]
            assert row["broker_hard_leverage"] == pytest.approx(1.0 / row["margin_rate"], abs=0.01)
        assert record["loss_cut_margin_maintenance_ratio"] == 1.0
        assert "証拠金維持率が100%以下" in record["quoted_rules"]["loss_cut"]
        assert "マージンコール、マージンカットはありません" in record["quoted_rules"]["margin_call"]
        assert "MetaTrader 5" in record["account_assumption"]["server_platform"]

    def test_the_margin_and_exposure_series_are_routed_notional_times_rate(self) -> None:
        route = leverage.routing_profile(ROOT)
        independent = _independent_routing(VERIFIED_RATES)
        assert route["margin_per_unit_currency_gross"]["mean"] == pytest.approx(
            independent["margin_mean"], abs=1e-5
        )
        assert route["margin_per_unit_currency_gross"]["p95"] == pytest.approx(
            independent["margin_p95"], abs=1e-5
        )
        assert route["largest_single_currency_exposure_per_unit_currency_gross"][
            "p95"
        ] == pytest.approx(independent["exposure_p95"], abs=1e-4)
        assert route["pair_gross_per_unit_currency_gross"]["mean"] == pytest.approx(
            independent["gross_mean"], abs=1e-4
        )
        assert independent["exposure_p95"] > 0.25, "routed exposure exceeds the weight cap"

    def test_the_pair_table_is_routed_notional_times_pair_rate(self) -> None:
        table = leverage.pair_margin_table(ROOT, 4.0)
        for row in table:
            assert row["required_margin_per_equity"] == pytest.approx(
                row["routed_notional_per_equity"] * VERIFIED_RATES[row["pair"]], abs=1e-4
            )
        total = sum(r["required_margin_per_equity"] for r in table)
        gross = sum(r["routed_notional_per_equity"] for r in table)
        assert gross / 25.0 < total < gross / 20.0

    def test_routing_reproduces_track_1_pair_gross(self) -> None:
        check = leverage.build(ROOT)["routing_check_against_track_1"]
        assert check["synthetic_mean"] == pytest.approx(
            check["track_1_pair_gross_per_currency_gross"], rel=0.03
        )

    def test_the_leverage_tail_is_track_1s_recorded_ratio(self) -> None:
        summary = json.loads((ROOT / capacity.TRACK_1_RECORD).read_text(encoding="utf-8"))[
            "primary"
        ]["summary"]
        assert leverage.leverage_tail_multiple(ROOT) == pytest.approx(
            summary["p95_uncapped_leverage"] / summary["mean_uncapped_leverage"], abs=1e-4
        )

    @pytest.mark.parametrize("lev", [1.0, 4.29, 6.44, 10.0])
    def test_every_stress_component(self, lev: float) -> None:
        row = leverage.scale(ROOT, lev, 0.5)
        route = leverage.routing_profile(ROOT)
        tail = lev * leverage.leverage_tail_multiple(ROOT)
        margin_tail = tail * route["margin_per_unit_currency_gross"]["p95"]
        gap = tail * route["largest_single_currency_exposure_per_unit_currency_gross"]["p95"] * 0.20
        assert leverage.STRESS_CURRENCY_GAP == 0.20
        assert row["risk_leverage_C_tail"] == pytest.approx(tail, abs=0.01)
        assert row["margin_utilisation_at_leverage_tail"] == pytest.approx(margin_tail, abs=1e-4)
        assert row["gap_loss_at_leverage_tail"] == pytest.approx(gap, abs=1e-4)
        assert row["equity_after_gap"] == pytest.approx(1.0 - gap, abs=1e-4)
        assert row["maintenance_ratio_after_gap"] == pytest.approx(
            (1.0 - gap) / margin_tail, abs=0.01
        )
        assert row["loss_cut_on_gap"] == ((1.0 - gap) / margin_tail <= 1.0)
        vol = lev * capacity.VOL_PER_UNIT_GROSS
        zero = capacity.gaussian_drawdown(0.0)["p95_max_drawdown_in_vol_units"]
        assert row["p95_max_drawdown_10y_at_zero_sharpe"] == pytest.approx(
            1.0 - math.exp(-zero * vol), abs=1e-3
        )
        assumed = capacity.gaussian_drawdown(0.5)["p95_max_drawdown_in_vol_units"]
        assert row["p95_max_drawdown_10y_at_assumed_sharpe"] == pytest.approx(
            1.0 - math.exp(-assumed * vol), abs=1e-3
        )
        assert row["largest_currency_gap_before_loss_cut"] == pytest.approx(
            (1.0 - margin_tail)
            / (tail * route["largest_single_currency_exposure_per_unit_currency_gross"]["p95"]),
            abs=1e-3,
        )
        fixed = 1.0 - zero * vol - gap
        assert row["fixed_notional_equity_after_drawdown_and_gap"] == pytest.approx(fixed, abs=1e-3)
        assert row["fixed_notional_loss_cut"] == (fixed <= margin_tail)

    def test_the_broker_bound_is_where_the_gap_flag_turns(self) -> None:
        bound = leverage.broker_feasible_mean_risk_leverage(ROOT)
        assert leverage.scale(ROOT, bound * 0.99, 0.5)["loss_cut_on_gap"] is False
        assert leverage.scale(ROOT, bound * 1.01, 0.5)["loss_cut_on_gap"] is True

    def test_the_fixed_notional_bound_is_lower_and_turns_its_own_flag(self) -> None:
        equity_bound = leverage.broker_feasible_mean_risk_leverage(ROOT)
        fixed_bound = leverage.broker_feasible_mean_risk_leverage(ROOT, equity_proportional=False)
        assert fixed_bound < equity_bound
        assert leverage.scale(ROOT, fixed_bound * 0.99, 0.5)["fixed_notional_loss_cut"] is False
        assert leverage.scale(ROOT, fixed_bound * 1.01, 0.5)["fixed_notional_loss_cut"] is True
        assert leverage.scale(ROOT, 4.29, 0.5)["fixed_notional_loss_cut"] is True

    def test_equity_proportional_sizing_is_stated_as_a_requirement(self, document: str) -> None:
        assert (
            "equity 比例の sizing は「実装への要求」であって、再利用する執行層の性質ではない"
            in document
        )
        assert "固定 notional（現在の執行層のまま" in document
        assert "run_book" in document
        assert any("REQUIREMENT" in step for step in leverage.RISK_BASED_POLICY["order"])

    def test_the_three_leverages_are_distinct_quantities(self) -> None:
        row = leverage.scale(ROOT, 4.0, 0.5)
        assert row["risk_leverage_C_mean"] == 4.0
        assert (
            row["portfolio_gross_leverage_B_mean"]
            < row["risk_leverage_C_mean"]
            < row["risk_leverage_C_tail"]
        )
        assert row["annual_vol"] == pytest.approx(4.0 * capacity.VOL_PER_UNIT_GROSS, abs=1e-4)
        assert "concept C" in leverage.PREVIOUS_FIVE_X["leverage_concept_capped"]

    def test_leverage_scales_return_but_never_the_sharpe_or_the_broker_flag(self) -> None:
        for lev in (1.0, 5.0, 10.0):
            row = leverage.scale(ROOT, lev, 0.5)
            assert row["annual_net_return"] == pytest.approx(0.5 * row["annual_vol"], abs=1e-4)
            assert row["loss_cut_on_gap"] == leverage.scale(ROOT, lev, 0.0)["loss_cut_on_gap"]
        assert leverage.scale(ROOT, 10.0, -0.2)["annual_net_return"] < 0

    def test_no_fixed_cap_decides_feasibility(self) -> None:
        assert leverage.RISK_BASED_POLICY["fixed_leverage_cap"] is None
        assert "WITHDRAWN" in leverage.PREVIOUS_FIVE_X["status"]
        assert "3ed3527" in leverage.PREVIOUS_FIVE_X["introduced_in"]
        assert not hasattr(capacity, "MAX_LEVERAGE")
        twelve = leverage.build(ROOT)["vol_target_scenarios"]["0.12"]["0.5"]
        assert twelve["risk_leverage_C_mean"] > 5.0 and twelve["loss_cut_on_gap"] is False

    def test_the_document_carries_the_correction(self, document: str) -> None:
        assert "上限 5 倍を超える" not in document
        assert "以前の内部 5 倍を超えるが、それだけでは OANDA 上で実行不能ではない" in document
        assert "`gross ÷ 25` では計算しない" in document
        assert "**ranking は変わらない**" in document
        assert "**固定の leverage 上限は適用しない**" in document
        assert "上限なしで要求した leverage は平均 5.08・p95 8.04" in document
        assert "この判定は\n   仮定した Sharpe に依存しない" in document
