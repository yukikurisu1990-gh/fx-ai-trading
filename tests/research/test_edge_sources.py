"""The reframing record: arithmetic, catalogue, evidence map, document and boundaries agree.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Reads committed documents and artefacts only; no market data.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import pytest

from scripts.research.edge_sources import WORKFLOW_STATUS, candidates, capacity, driver, render
from scripts.research.round_a.ledger import LEDGER

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "scripts/research/edge_sources"
DOCUMENT = ROOT / "docs/research/m15_next_edge_source_reframing.md"
ARTIFACT = ROOT / "artifacts/research/edge_sources/reframing.json"
AVAILABILITY = ROOT / "artifacts/research/edge_sources/public_data_availability.json"
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

    def test_the_drag_is_turnover_times_cost_over_vol(self) -> None:
        assert capacity.cost_ir_drag(20.0) == pytest.approx(
            20.0 * 3.406 / (capacity.VOL_PER_UNIT_GROSS * 10_000)
        )

    @pytest.mark.parametrize("half_life", capacity.HALF_LIVES_DAYS)
    def test_the_required_ic_solves_back_to_the_net_sharpe(self, half_life: float) -> None:
        law = capacity.band_law(half_life)
        ic = capacity.required_horizon_ic(0.5, half_life)
        gross = (
            capacity.TRANSFER_COEFFICIENT
            * law["capture"]
            * ic
            * math.sqrt(capacity.independent_bets_per_year(half_life))
        )
        assert gross - capacity.cost_ir_drag(law["turnover"]) == pytest.approx(0.5, abs=1e-9)

    def test_slower_forecasts_trade_less_and_need_more_horizon_ic(self) -> None:
        rows = capacity.continuous_book_table()["rows"]
        turnovers = [row["turnover_per_unit_gross"] for row in rows.values()]
        ics = [row["required_horizon_ic"]["0.5"] for row in rows.values()]
        assert turnovers == sorted(turnovers, reverse=True)
        assert ics[1:] == sorted(ics[1:])

    def test_return_is_sharpe_times_vol_and_leverage_is_vol_over_vol_per_gross(self) -> None:
        table = capacity.return_and_leverage_table()
        row = table["rows"]["vol_0.1"]
        assert row["annual_net_return"]["0.5"] == pytest.approx(0.05)
        assert row["gross_leverage"] == pytest.approx(0.10 / capacity.VOL_PER_UNIT_GROSS, abs=0.01)
        assert table["net_sharpe_needed_for_5pct"]["vol_0.1"] == 0.5

    def test_the_event_book_edge_reproduces_the_sharpe(self) -> None:
        row = capacity.event_book(150.0, 3.0, 0.5)
        over_cost = row["required_edge_bp_charged_cost"] - capacity.EVENT_ROUND_TRIP_CHARGED_BP
        sharpe = over_cost * math.sqrt(150.0) / row["sd_per_event_bp"]
        assert sharpe == pytest.approx(0.5, abs=0.01)
        assert row["required_edge_bp_pair_cost"] < row["required_edge_bp_charged_cost"]

    def test_the_sample_years_follow_t_equals_sharpe_root_years(self) -> None:
        assert capacity.sample_years_needed(0.5) == pytest.approx((1.645 / 0.5) ** 2, abs=0.01)


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

    def test_suspended_is_never_filed_as_closed(self) -> None:
        for item in candidates.EVIDENCE_MAP:
            if "NOT_DECISION_GRADE" in item.status or "SKIP" in item.status:
                assert item.klass in ("NOT_DECISION_GRADE", "SUSPENDED"), item


class TestTheCatalogue:
    def test_at_least_twenty_distinct_candidates(self) -> None:
        ids = [c.cid for c in candidates.CANDIDATES]
        names = [c.name for c in candidates.CANDIDATES]
        mechanisms = [c.mechanism for c in candidates.CANDIDATES]
        assert len(ids) >= 20
        assert len(set(ids)) == len(ids)
        assert len(set(names)) == len(names)
        assert len(set(mechanisms)) == len(mechanisms)

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

    def test_no_track_is_a_price_only_or_ml_first_hypothesis(self) -> None:
        by_id = {c.cid: c for c in candidates.CANDIDATES}
        for _, members in candidates.PROPOSED_TRACKS:
            for cid in members:
                assert by_id[cid].ml_role.startswith("不要")
                assert "price" not in by_id[cid].information


class TestTheBoundaries:
    def test_the_package_reads_no_market_data(self) -> None:
        for path in PACKAGE.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            for forbidden in (
                "read_parquet",
                "read_csv",
                "urlopen",
                "requests",
                "load_pair",
                "import oanda",
                "from oanda",
                "api-fxtrade",
                "api-fxpractice",
                "from src",
            ):
                assert forbidden not in source.lower(), (path.name, forbidden)
        capacity_source = (PACKAGE / "capacity.py").read_text(encoding="utf-8")
        assert capacity_source.count("read_text") == 1
        assert "TRACK_1_RECORD" in capacity_source

    def test_the_availability_record_holds_no_fx_series(self) -> None:
        record: dict[str, Any] = json.loads(AVAILABILITY.read_text(encoding="utf-8"))
        for series in record["fred"]:
            assert not series.startswith(("DEX", "EXUS", "EXJP", "EXCA", "EXSZ", "EXUK")), series
        assert "no FX series requested" in record["note"]
        for block in record["fred"].values():
            assert set(block) <= {
                "label",
                "http_status",
                "frequency_text",
                "declared_range",
                "observation_start_field",
                "error",
            }

    def test_the_document_does_not_adopt_the_withdrawn_pause(self, document: str) -> None:
        assert "FX_SPOT_ACTIVE_ALPHA_RESEARCH_PAUSED" not in document
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
