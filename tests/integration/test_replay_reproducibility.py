"""Integration test: end-to-end replay reproducibility (PRs #159-#163).

Asserts the contract of the replay/backtest pipeline: running
``scripts/run_paper_evaluation`` twice against the same recorded JSONL
file produces the same trading outcomes (trade count, gross pnl,
no-signal rate, ticks executed). This is what makes the replay rails
useful — if the same input does not yield the same result, the eval
loop cannot be used to A/B test signals or regression-guard signal
changes.

PR1 (#159) added ``ReplayQuoteFeed`` and PR3 (#161) wired the
``--replay`` flag into the runner; both shipped with unit tests of
their wiring.  This test exercises the full pipeline end-to-end:
``--replay file.jsonl`` → ``ReplayQuoteFeed`` → entry + exit ticks →
``positions`` / ``close_events`` rows → aggregated metrics dict.

Requires DATABASE_URL; auto-skipped otherwise.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

pytestmark = pytest.mark.skipif(
    not _DATABASE_URL,
    reason="DATABASE_URL not set — skipping integration tests",
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
_ACCOUNT_ID = "acct-replay-eval"
_INSTRUMENT = "EUR_USD"


def _load_eval() -> Any:
    alias = "_eval_under_replay_reproducibility_test"
    if alias in sys.modules:
        return sys.modules[alias]
    spec = importlib.util.spec_from_file_location(alias, _SCRIPTS_DIR / "run_paper_evaluation.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


def _load_seed() -> Any:
    alias = "_seed_under_replay_reproducibility_test"
    if alias in sys.modules:
        return sys.modules[alias]
    spec = importlib.util.spec_from_file_location(alias, _SCRIPTS_DIR / "seed_replay_account.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def engine():
    e = create_engine(_DATABASE_URL)
    yield e
    e.dispose()


@pytest.fixture(scope="module", autouse=True)
def replay_account(engine) -> Iterator[None]:
    """Seed ``acct-replay-eval`` once per module (idempotent via PR #163)."""
    seed_mod = _load_seed()
    seed_mod.seed_account(
        engine=engine,
        account_id=_ACCOUNT_ID,
        broker_id="paper",
        account_type="demo",
        base_currency="USD",
    )
    yield
    # Account row is shared across replay runs; do not drop on teardown.


def _clean_replay_state(engine) -> None:
    """Wipe rows the replay account may have left behind in prior runs.

    Order matters: outbox -> close_events -> positions -> orders, so FK
    references hold throughout.
    """
    with engine.begin() as conn:
        conn.execute(
            text(
                "DELETE FROM secondary_sync_outbox"
                " WHERE table_name IN ('positions', 'close_events')"
                "   AND payload_json::text LIKE :acct_like"
            ),
            {"acct_like": f"%{_ACCOUNT_ID}%"},
        )
        conn.execute(
            text(
                "DELETE FROM close_events"
                " WHERE order_id IN ("
                "   SELECT order_id FROM orders WHERE account_id = :aid"
                " )"
            ),
            {"aid": _ACCOUNT_ID},
        )
        conn.execute(
            text("DELETE FROM positions WHERE account_id = :aid"),
            {"aid": _ACCOUNT_ID},
        )
        conn.execute(
            text("DELETE FROM orders WHERE account_id = :aid"),
            {"aid": _ACCOUNT_ID},
        )


def _write_fixture(path: Path, *, n_quotes: int = 200) -> None:
    """Strictly monotonic-up EUR_USD quotes spaced 1 second apart.

    Generously over-sized: every tick may consume up to 2 quotes (entry
    policy + per-position exit gate + broker fill paths), so the buffer
    must comfortably exceed ``max_iterations × 2``.

    With ``MinimumEntrySignal`` (3-point monotonic momentum) and the
    eval timing chosen in ``_run_eval``, this stream produces multiple
    open/close cycles within the iteration budget so the reproducibility
    assertions bind on a non-trivial trade set.
    """
    base_ts = datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC)
    lines = [
        {
            "ts": (base_ts + timedelta(seconds=i)).isoformat(),
            "price": round(1.10000 + 0.00010 * i, 5),
            "source": "test_fixture",
        }
        for i in range(n_quotes)
    ]
    path.write_text("\n".join(json.dumps(ln) for ln in lines) + "\n", encoding="utf-8")


def _run_eval(replay_path: Path, output_path: Path) -> dict[str, Any]:
    """Invoke ``run_paper_evaluation.main`` and return the parsed metrics dict.

    Note on timing: ``--fast`` is intentionally NOT used.  The exit gate
    measures ``holding_seconds`` against the wall clock (``clock.now()``)
    rather than the replayed quote timestamps, so a fast loop never lets
    a position age past ``--max-holding-seconds`` and no close events
    fire — leaving ``trades_count == 0`` and the reproducibility check
    trivially passing.  A small inter-tick sleep advances the wall clock
    enough to exercise the close path within the iteration budget.
    """
    eval_mod = _load_eval()
    rc = eval_mod.main(
        [
            "--account-id",
            _ACCOUNT_ID,
            "--instrument",
            _INSTRUMENT,
            "--direction",
            "buy",
            "--strategy",
            "minimum",
            "--units",
            "1000",
            "--max-iterations",
            "60",
            "--max-holding-seconds",
            "1",
            "--stale-after-seconds",
            "99999",
            "--interval-seconds",
            "0.05",
            "--replay",
            str(replay_path),
            "--output",
            "json",
            "--output-path",
            str(output_path),
        ]
    )
    assert rc == 0, f"eval main() returned rc={rc}"
    with output_path.open("r", encoding="utf-8") as f:
        return json.load(f)


class TestReplayReproducibility:
    def test_same_input_produces_same_outcomes(self, engine, tmp_path: Path) -> None:
        fixture = tmp_path / "quotes.jsonl"
        _write_fixture(fixture)

        _clean_replay_state(engine)
        m1 = _run_eval(fixture, tmp_path / "metrics_1.json")

        _clean_replay_state(engine)
        m2 = _run_eval(fixture, tmp_path / "metrics_2.json")

        _clean_replay_state(engine)

        # The reproducibility contract: trade counts, gross pnl, and
        # signal-evaluation outcomes are deterministic given the same JSONL.
        # If any of these drift, the eval loop cannot be used to A/B test
        # signals or to regression-guard signal changes.
        assert m1["ticks_executed"] == m2["ticks_executed"], (
            f"ticks_executed drift: {m1['ticks_executed']} vs {m2['ticks_executed']}"
        )
        assert m1["trades_count"] == m2["trades_count"], (
            f"trades_count drift: {m1['trades_count']} vs {m2['trades_count']}"
        )
        assert m1["no_signal_rate"] == m2["no_signal_rate"], (
            f"no_signal_rate drift: {m1['no_signal_rate']} vs {m2['no_signal_rate']}"
        )
        assert m1["total_pnl"] == m2["total_pnl"], (
            f"total_pnl drift: {m1['total_pnl']} vs {m2['total_pnl']}"
        )
        assert m1["win_rate"] == m2["win_rate"], (
            f"win_rate drift: {m1['win_rate']} vs {m2['win_rate']}"
        )
        assert m1["avg_pnl"] == m2["avg_pnl"], f"avg_pnl drift: {m1['avg_pnl']} vs {m2['avg_pnl']}"

    def test_fixture_is_rich_enough_to_make_assertion_load_bearing(
        self, engine, tmp_path: Path
    ) -> None:
        """Smoke check — guards against a future fixture edit that
        accidentally produces zero trades, in which case the
        reproducibility assertions above would pass trivially (0 == 0)
        without exercising the open/close path.
        """
        fixture = tmp_path / "quotes.jsonl"
        _write_fixture(fixture)

        _clean_replay_state(engine)
        m = _run_eval(fixture, tmp_path / "metrics.json")
        _clean_replay_state(engine)

        assert m["trades_count"] >= 1, (
            f"fixture produced zero trades — reproducibility test would be trivial. metrics={m}"
        )
