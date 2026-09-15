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

import pytest

from scripts.research.edge_sources import WORKFLOW_STATUS, candidates, capacity, driver, render
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

    def test_the_leverage_cap_is_the_reused_layers(self) -> None:
        assert capacity.MAX_LEVERAGE == 5.0
        rows = capacity.return_and_leverage_table()["rows"]
        assert rows["vol_0.1"]["within_reused_leverage_cap"] is True
        assert rows["vol_0.12"]["within_reused_leverage_cap"] is False

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
        assert row["gross_leverage"] == pytest.approx(0.10 / capacity.VOL_PER_UNIT_GROSS, abs=0.01)
        assert table["net_sharpe_needed_for_5pct"]["vol_0.1"] == 0.5

    def test_drawdown_falls_with_sharpe_and_scales_with_vol(self) -> None:
        low, high = capacity.gaussian_drawdown(0.3), capacity.gaussian_drawdown(0.8)
        assert high["median_max_drawdown_in_vol_units"] < low["median_max_drawdown_in_vol_units"]
        assert (
            high["probability_first_five_years_negative"]
            < low["probability_first_five_years_negative"]
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

    def test_at_most_three_tracks_all_eligible_and_from_the_top(self) -> None:
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
    ALLOWED_IMPORTS = frozenset(
        {
            "__future__",
            "dataclasses",
            "functools",
            "json",
            "math",
            "pathlib",
            "sys",
            "typing",
            "numpy",
            "scripts.research.continuous_portfolio",
            "scripts.research.feasibility.inventory",
            "scripts.research.edge_sources",
        }
    )

    def test_the_package_imports_nothing_that_reads_markets(self) -> None:
        for path in PACKAGE.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    continue
                for name in names:
                    assert name in self.ALLOWED_IMPORTS, (path.name, name)

    def test_the_package_calls_no_reader_but_the_track_1_record(self) -> None:
        reads = 0
        for path in PACKAGE.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
                assert name not in ("open", "urlopen", "build_opener", "read_table", "read_csv"), (
                    path.name,
                    name,
                )
                assert not name.startswith(("read_parquet", "load_")), (path.name, name)
                if name.startswith("read"):
                    assert name == "read_text", (path.name, name)
                    reads += 1
        assert reads == 1
        capacity_source = (PACKAGE / "capacity.py").read_text(encoding="utf-8")
        assert capacity_source.count("read_text") == 1
        assert "TRACK_1_RECORD" in capacity_source

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
