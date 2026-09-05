"""The committed R1 execution evidence, pinned.

**No test here touches real market data.** Every case reads a committed
governance file or a committed ledger. The corpus these ledgers describe is
`EXPLORATORY_SEEN_DATA`; nothing here reads it.

Why this file exists
--------------------

`docs/governance/m15_track_a_r1_execution_record.md` records an irreversible
operation, and the three ledgers beside it are the only record of a one-way
transition. A post-run review role mutated that evidence eighteen ways and the
full suite stayed green for **fourteen** of them — including widening the
committed seen declaration's span into the `EXPLORATORY_OOS_SLICE`, truncating
the grant ledger from 320 rows to 220, flipping the breadth record's
`result_observed` to `true`, deleting the driver, and rewriting the playbook back
to "Nothing has been read". Every one of those is exactly the failure this
programme keeps recording about itself: a tick, a hash or a sentence that nothing
checks.

The argument for fixing it here is the one the record already makes for
`required_outputs`: **tests are outside the fingerprint surface**, so pinning the
evidence costs nothing and moves no grant.

What this file does **not** do: re-derive the run, or claim the ledgers are
correct because they are consistent. It pins them to the values a human was shown
when the run was adjudicated, so a later edit has to be deliberate.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from scripts.m15_gate3a.pair_authority import PAIRS_20
from scripts.m15_track_a import containment, oos_slice, scratch

ROOT = Path(containment.__file__).resolve().parents[2]
LEDGER = ROOT / "artifacts" / "track_a_scratch" / "ledger"
RECORD = ROOT / "docs" / "governance" / "m15_track_a_r1_execution_record.md"
DRIVER = ROOT / "docs" / "governance" / "evidence" / "m15_track_a_r1_driver_2026_09_05.py.txt"

RUN_ID = "track-a-r1-authorized-historical-execution-2026-09-05"
APPROVED_HEAD = "0bb987e775658db3532affdc3992cad94382faa3"
APPROVED_FINGERPRINT = "e147542aec04f2cf781c5ecd062d8a08b1d058007634c54357f00756736b5e50"

#: sha256 of each committed artefact, as §7 of the record states it.
EVIDENCE = {
    LEDGER / "exploratory_seen_ledger.jsonl": (
        "e3b350de6b02dcbe7b418d65910a468d8d1a0ed79a070a2bff5456cd69425bba",
        795,
    ),
    LEDGER / "track_a_authorization_ledger.jsonl": (
        "cddc466849570a0a1ea30501f65d9fb7ae91531763793a53f0d8cf72932e9bc2",
        329_920,
    ),
    LEDGER / "exploration_breadth.jsonl": (
        "8f0e4f3b37cbb3787ecb33d8610a5fed2061f81bca0059b74a575acfb87e89d4",
        856,
    ),
    DRIVER: (
        "3a799236bdb38e3558e2131152de9881dd376acae9277c1a22f375fd9357a11d",
        9_276,
    ),
}


def _rows(path: Path) -> list[dict]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


# ---------------------------------------------------------------------------
# the artefacts are the ones that were adjudicated
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", sorted(EVIDENCE, key=str), ids=lambda p: p.name)
def test_the_committed_evidence_is_byte_for_byte_what_the_record_states(path: Path) -> None:
    expected_digest, expected_size = EVIDENCE[path]
    assert path.is_file(), f"{path.name} is gone; the record's §7 names it as evidence"
    body = path.read_bytes()
    assert len(body) == expected_size, f"{path.name} is {len(body)} bytes, not {expected_size}"
    assert hashlib.sha256(body).hexdigest() == expected_digest, (
        f"{path.name} does not hash to the value §7 records. An irreversible run's evidence "
        "changed; that needs a human, not a test update."
    )
    assert expected_digest in RECORD.read_text(encoding="utf-8"), (
        f"§7 no longer records {path.name}'s hash"
    )


def test_the_driver_blob_is_the_bytes_that_ran_not_a_normalised_copy() -> None:
    """`.gitattributes` has to keep git's hands off the archived bytes.

    Without `-text`, a CRLF host stores an LF-normalised blob and the recorded
    sha256 is unreproducible in a fresh clone — the only record of how an
    irreversible run was driven, uncheckable. A review role measured that
    exactly: blob `0d245922…`/9,049 against the recorded `3a799236…`/9,276.
    """
    blob = subprocess.run(  # noqa: S603 - fixed argv, this repository
        ["git", "cat-file", "blob", f"HEAD:{DRIVER.relative_to(ROOT).as_posix()}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    expected_digest, expected_size = EVIDENCE[DRIVER]
    assert len(blob) == expected_size
    assert hashlib.sha256(blob).hexdigest() == expected_digest


# ---------------------------------------------------------------------------
# the seen declaration is the one boundary that cannot be widened quietly
# ---------------------------------------------------------------------------


def test_the_committed_seen_declaration_does_not_reach_the_oos_slice() -> None:
    """The mutation that most needed catching, and did not have a test.

    `seen_ledger.assert_declared` asks only whether **some prior declaration**
    covers an interval — it does not compare run ids. So a committed declaration
    is a live input to that gate in every clone, and widening this one line into
    the slice would pre-satisfy the write-ahead gate for data nobody has
    authorised. A review role widened `span_end_utc` to `2026-02-28` and the full
    suite stayed green.
    """
    rows = _rows(LEDGER / "exploratory_seen_ledger.jsonl")
    assert len(rows) == 1, f"{len(rows)} seen declarations; R1 wrote exactly one"
    declaration = rows[0]["declaration"]
    assert declaration["span_start_utc"] == oos_slice.DEVELOPMENT_START_UTC
    assert declaration["span_end_utc"] == oos_slice.DEVELOPMENT_END_UTC
    assert declaration["span_end_utc"] < oos_slice.SLICE_START_UTC, (
        "the committed declaration reaches into the EXPLORATORY_OOS_SLICE, which would "
        "pre-satisfy the write-ahead gate for an unauthorised span in every clone"
    )
    assert tuple(declaration["pairs"]) == tuple(sorted(PAIRS_20))
    assert declaration["timeframe"] == "M1"
    assert rows[0]["identity"]["run_id"] == RUN_ID


def test_the_committed_grant_ledger_is_what_the_record_describes() -> None:
    rows = _rows(LEDGER / "track_a_authorization_ledger.jsonl")
    assert len(rows) == 320, f"{len(rows)} grant rows; the record says 320"
    distinct = {json.dumps(row, sort_keys=True) for row in rows}
    assert len(distinct) == 2, (
        f"{len(distinct)} distinct rows. The record says two, and says so because an earlier "
        "wording claimed per-window provenance the file does not carry."
    )
    operations = sorted(row["grant"]["operation"] for row in rows)
    assert operations.count("track_a_historical_read") == 160
    assert operations.count("track_a_m15_research_derivation") == 160
    for row in rows:
        grant = row["grant"]
        assert grant["approved_implementation_fingerprint"] == APPROVED_FINGERPRINT
        assert grant["approved_head_sha"] == APPROVED_HEAD
        assert (grant["span_start_utc"], grant["span_end_utc"]) == (
            oos_slice.DEVELOPMENT_START_UTC,
            oos_slice.DEVELOPMENT_END_UTC,
        )
        assert grant["timeframe"] == "M1"
        assert row["identity"]["run_id"] == RUN_ID


def test_the_committed_breadth_record_scored_nothing() -> None:
    rows = _rows(LEDGER / "exploration_breadth.jsonl")
    assert len(rows) == 1
    entry = rows[0]["entry"]
    assert entry["result_observed"] is False, (
        "R1 scores nothing, so K must not count this configuration. Flipping this flag to "
        "true would make a survey look like a scored result."
    )
    assert entry["run_id"] == RUN_ID
    assert set(entry["axes"].values()) == {"r1_survey_no_configuration"}


def test_one_run_identity_reaches_every_committed_ledger() -> None:
    identities = set()
    for name in (
        "exploratory_seen_ledger.jsonl",
        "track_a_authorization_ledger.jsonl",
        "exploration_breadth.jsonl",
    ):
        for row in _rows(LEDGER / name):
            identities.add(json.dumps(row["identity"], sort_keys=True))
    assert len(identities) == 1, "a run whose ledgers disagree about who ran is not one run"
    identity = json.loads(identities.pop())
    assert identity["run_id"] == RUN_ID
    assert identity["code_sha"] == APPROVED_HEAD


# ---------------------------------------------------------------------------
# the adjudication's polarity
# ---------------------------------------------------------------------------


def test_the_adjudicated_statuses_are_recorded_with_the_polarity_they_were_ruled() -> None:
    """Prose is what has gone wrong in this programme, repeatedly.

    A review role rewrote `..._PRISTINE_CLAIM_WITHDRAWN` to `..._UPHELD`, flipped
    the cost-table exclusion to "accepted as decision-bearing", claimed
    `TRACK_A_R1_EXECUTED_ON_AUTHORIZED_HISTORICAL_DEVELOPMENT_CORPUS` "is now
    recorded", and rolled the playbook back to "Nothing has been read" — four
    mutations, four green runs.
    """
    documents = {
        "CLAUDE.md": (ROOT / "CLAUDE.md").read_text(encoding="utf-8"),
        "record": RECORD.read_text(encoding="utf-8"),
        "playbook": (
            scratch.repo_root() / "docs" / "governance" / "m15_audit_playbook.md"
        ).read_text(encoding="utf-8"),
    }
    for name, text in documents.items():
        for token in (
            "TRACK_A_R1_CORE_EXECUTION_ACCEPTED_WITH_POST_EXECUTION_EXCLUSIONS",
            "HISTORICAL_EXPLORATORY_OOS_PRISTINE_CLAIM_WITHDRAWN",
            "R1_UNAUTHORISED_COST_TABLE_OUTPUT_EXCLUDED_FROM_DECISION_BEARING_RESULT",
            "TRACK_A_READY_TO_BEGIN_EXPLORATORY_STRATEGY_RESEARCH",
        ):
            assert token in text, f"{name} no longer records {token}"
        #: the opposite polarity, in any spelling, is a rewritten ruling
        for forbidden in (
            "PRISTINE_CLAIM_UPHELD",
            "COST_TABLE_OUTPUT_ACCEPTED_AS_DECISION_BEARING",
            "pristine historical OOS is intact",
        ):
            assert forbidden not in text, f"{name} contradicts the 2026-09-05 ruling: {forbidden}"

    #: the token the ruling deliberately left unclaimed stays unclaimed
    for name, text in documents.items():
        for claimed in (
            "`TRACK_A_R1_EXECUTED_ON_AUTHORIZED_HISTORICAL_DEVELOPMENT_CORPUS` is now recorded",
            "`TRACK_A_R1_EXECUTED_ON_AUTHORIZED_HISTORICAL_DEVELOPMENT_CORPUS` holds",
        ):
            assert claimed not in text, f"{name} claims a token §8.4 leaves unrecorded"


def test_the_governance_documents_do_not_say_the_corpus_is_unseen() -> None:
    """Every live claim, not the historical records that carry a dated note."""
    for relative in (
        "CLAUDE.md",
        "docs/governance/m15_audit_playbook.md",
        "docs/governance/autonomous_development_policy.md",
        "docs/prompts/m15_claude_operating_prefix.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "corpus is `UNSEEN`" not in text, f"{relative} still calls the corpus UNSEEN"
        assert "What is left is the run" not in text, f"{relative} still says the run is pending"
