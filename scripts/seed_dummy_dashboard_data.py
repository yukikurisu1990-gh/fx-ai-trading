"""Seed dummy data into the dashboard tables for visual smoke-testing.

Inserts a "DUMMY" broker + two dummy accounts (one demo, one live) and
populates every table the dashboard reads from with a few rows so each
panel renders something visible.

Idempotent: rows are keyed by ULID; running twice creates two sets.
For a clean re-seed call ``--purge`` first.

Usage:
    .venv/Scripts/python.exe scripts/seed_dummy_dashboard_data.py
    .venv/Scripts/python.exe scripts/seed_dummy_dashboard_data.py --purge
"""

from __future__ import annotations

import argparse
import json
import os
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from fx_ai_trading.common.ulid import generate_ulid


def _now() -> datetime:
    return datetime.now(UTC)


def _purge(conn) -> None:
    # Order respects FK dependencies (children first).
    dummy_orders_subq = "SELECT order_id FROM orders WHERE account_id LIKE 'DUMMY-%'"
    statements = [
        f"DELETE FROM execution_metrics WHERE order_id IN ({dummy_orders_subq})",
        f"DELETE FROM close_events WHERE order_id IN ({dummy_orders_subq})",
        "DELETE FROM positions WHERE account_id LIKE 'DUMMY-%'",
        "DELETE FROM orders WHERE account_id LIKE 'DUMMY-%'",
        "DELETE FROM risk_events WHERE strategy_id = 'DUMMY_STRAT'",
        "DELETE FROM dashboard_top_candidates WHERE strategy_id = 'DUMMY_STRAT'",
        "DELETE FROM supervisor_events WHERE run_id LIKE 'dummy-run-%'",
        "DELETE FROM system_jobs WHERE system_job_id LIKE 'DUMMY-%'",
        "DELETE FROM accounts WHERE account_id LIKE 'DUMMY-%'",
        "DELETE FROM brokers WHERE broker_id = 'DUMMY'",
    ]
    for sql in statements:
        try:
            conn.execute(text(sql))
        except Exception as exc:
            print(f"  purge skipped ({sql[:50]}...): {exc}")


def _seed_reference(conn) -> tuple[str, str]:
    """Insert DUMMY broker + 2 accounts. Returns (demo_acct_id, live_acct_id)."""
    conn.execute(
        text(
            "INSERT INTO brokers (broker_id, name, api_base_url) VALUES (:bid, :name, :url)"
            " ON CONFLICT (broker_id) DO NOTHING"
        ),
        {"bid": "DUMMY", "name": "Dummy Broker", "url": "https://dummy.example.com"},
    )
    demo_id = "DUMMY-demo-001"
    live_id = "DUMMY-live-001"
    for aid, atype in ((demo_id, "demo"), (live_id, "live")):
        conn.execute(
            text(
                "INSERT INTO accounts (account_id, broker_id, account_type, base_currency)"
                " VALUES (:aid, :bid, :atype, 'JPY')"
                " ON CONFLICT (account_id) DO NOTHING"
            ),
            {"aid": aid, "bid": "DUMMY", "atype": atype},
        )
    # instruments (idempotent)
    for instr, base, quote, pip_loc in (
        ("USD_JPY", "USD", "JPY", -2),
        ("EUR_USD", "EUR", "USD", -4),
        ("GBP_USD", "GBP", "USD", -4),
        ("AUD_USD", "AUD", "USD", -4),
    ):
        conn.execute(
            text(
                "INSERT INTO instruments"
                " (instrument, base_currency, quote_currency, pip_location, min_trade_units)"
                " VALUES (:i, :b, :q, :pl, 1)"
                " ON CONFLICT (instrument) DO NOTHING"
            ),
            {"i": instr, "b": base, "q": quote, "pl": pip_loc},
        )
    return demo_id, live_id


_INSTRUMENTS = ["USD_JPY", "EUR_USD", "GBP_USD", "AUD_USD"]
_STRATEGIES = ["LGBM_v1", "MR_BO", "MOMENTUM"]
_AVG_PRICE = {"USD_JPY": 159.500, "EUR_USD": 1.07500, "GBP_USD": 1.27500, "AUD_USD": 0.66500}
_REASON_CODES = [
    ("TP_HIT", 0.45),
    ("SL_HIT", 0.30),
    ("TIME_STOP", 0.15),
    ("TRAIL_STOP", 0.07),
    ("MANUAL_CLOSE", 0.03),
]


def _weighted_choice(pairs: list[tuple]) -> object:
    """Choose from [(value, weight), ...]."""
    r = random.random() * sum(w for _, w in pairs)
    cum = 0.0
    for v, w in pairs:
        cum += w
        if r <= cum:
            return v
    return pairs[-1][0]


def _seed_orders_positions(
    conn, account_id: str, n_filled: int = 60, span_days: int = 30
) -> list[tuple[str, datetime]]:
    """Insert n_filled FILLED orders distributed over span_days.

    Returns list of (order_id, filled_at) tuples for use by _seed_close_events.
    """
    order_ids: list[tuple[str, datetime]] = []
    base_t = _now() - timedelta(days=span_days)
    for _ in range(n_filled):
        oid = generate_ulid()
        instr = random.choice(_INSTRUMENTS)
        strat = random.choice(_STRATEGIES)
        direction = random.choice(["buy", "sell"])
        units = random.choice([1000, 5000, 10000, 25000])
        offset_min = random.randint(0, span_days * 24 * 60)
        created = base_t + timedelta(minutes=offset_min)
        filled = created + timedelta(seconds=random.randint(1, 5))
        conn.execute(
            text(
                "INSERT INTO orders (order_id, client_order_id, account_id, instrument,"
                " account_type, order_type, direction, units, status, filled_at, created_at)"
                " VALUES (:oid, :cid, :aid, :i, :at, 'market', :d, :u, 'FILLED', :f, :c)"
            ),
            {
                "oid": oid,
                "cid": f"{oid}:{instr}:{strat}",
                "aid": account_id,
                "i": instr,
                "at": "demo" if "demo" in account_id else "live",
                "d": direction,
                "u": units,
                "f": filled,
                "c": created,
            },
        )
        avg_price = _AVG_PRICE[instr]
        conn.execute(
            text(
                "INSERT INTO positions (position_snapshot_id, order_id, account_id,"
                " instrument, event_type, units, avg_price, unrealized_pl, event_time_utc)"
                " VALUES (:psid, :oid, :aid, :i, 'open', :u, :p, :upl, :t)"
            ),
            {
                "psid": generate_ulid(),
                "oid": oid,
                "aid": account_id,
                "i": instr,
                "u": units if direction == "buy" else -units,
                "p": avg_price,
                "upl": round(random.uniform(-2000, 3000), 2),
                "t": filled,
            },
        )
        order_ids.append((oid, filled))
    return order_ids


def _seed_close_events(conn, order_ids: list[tuple[str, datetime]]) -> None:
    """Close most orders with realistic reason / PnL distribution."""
    for oid, filled in order_ids:
        if random.random() < 0.15:
            continue  # ~15% remain open
        rc = _weighted_choice(_REASON_CODES)
        # Realistic PnL: TP positive, SL negative, others mixed.
        if rc == "TP_HIT":
            pnl = round(random.uniform(400, 3500), 2)
        elif rc == "SL_HIT":
            pnl = round(random.uniform(-3000, -400), 2)
        elif rc == "TIME_STOP":
            pnl = round(random.gauss(-100, 500), 2)
        elif rc == "TRAIL_STOP":
            pnl = round(random.uniform(100, 1800), 2)
        else:  # MANUAL_CLOSE
            pnl = round(random.gauss(0, 800), 2)
        hold_min = random.randint(5, 480)
        closed_at = filled + timedelta(minutes=hold_min)
        conn.execute(
            text(
                "INSERT INTO close_events (close_event_id, order_id, reasons,"
                " primary_reason_code, closed_at, pnl_realized)"
                " VALUES (:ceid, :oid, :rs, :pr, :t, :pnl)"
            ),
            {
                "ceid": generate_ulid(),
                "oid": oid,
                "rs": json.dumps([{"priority": 1, "reason_code": str(rc), "detail": "dummy"}]),
                "pr": rc,
                "t": closed_at,
                "pnl": pnl,
            },
        )


def _seed_execution_metrics(conn, order_ids: list[tuple[str, datetime]]) -> None:
    for oid, _ in order_ids:
        conn.execute(
            text(
                "INSERT INTO execution_metrics (execution_metric_id, order_id,"
                " signal_age_seconds, slippage_pips, latency_ms, recorded_at)"
                " VALUES (:emid, :oid, :age, :slip, :lat, :t)"
            ),
            {
                "emid": generate_ulid(),
                "oid": oid,
                "age": round(random.uniform(0.5, 3.0), 3),
                "slip": round(random.uniform(-0.8, 1.2), 4),
                "lat": random.randint(80, 600),
                "t": _now() - timedelta(minutes=random.randint(1, 240)),
            },
        )


def _seed_risk_events(conn, n: int = 8) -> None:
    instruments = ["USD_JPY", "EUR_USD", "GBP_USD"]
    for _ in range(n):
        verdict = random.choice(["accept", "accept", "accept", "reject"])
        constraint = (
            None
            if verdict == "accept"
            else random.choice(["max_total_risk", "max_per_instrument", "max_same_direction"])
        )
        conn.execute(
            text(
                "INSERT INTO risk_events (risk_event_id, cycle_id, instrument,"
                " strategy_id, verdict, constraint_violated, detail, event_time_utc)"
                " VALUES (:rid, :cid, :i, :s, :v, :c, :d, :t)"
            ),
            {
                "rid": generate_ulid(),
                "cid": f"cycle-{random.randint(1000, 9999)}",
                "i": random.choice(instruments),
                "s": "DUMMY_STRAT",
                "v": verdict,
                "c": constraint,
                "d": json.dumps({"note": "dummy seeded"}),
                "t": _now() - timedelta(minutes=random.randint(1, 200)),
            },
        )


def _seed_top_candidates(conn) -> None:
    instruments = ["USD_JPY", "EUR_USD", "GBP_USD", "AUD_USD"]
    now = _now()
    for rank, instr in enumerate(instruments, start=1):
        conn.execute(
            text(
                "INSERT INTO dashboard_top_candidates (candidate_id, instrument,"
                " strategy_id, tss_score, direction, generated_at, rank)"
                " VALUES (:cid, :i, :s, :sc, :d, :t, :r)"
            ),
            {
                "cid": generate_ulid(),
                "i": instr,
                "s": "DUMMY_STRAT",
                "sc": round(random.uniform(0.3, 0.95), 4),
                "d": random.choice(["buy", "sell"]),
                "t": now,
                "r": rank,
            },
        )


def _seed_supervisor_events(conn) -> None:
    events = [
        ("startup", "dummy-run-001"),
        ("config_loaded", "dummy-run-001"),
        ("health_check_ok", "dummy-run-001"),
        ("safe_stop", "dummy-run-001"),
    ]
    for evt, run in events:
        conn.execute(
            text(
                "INSERT INTO supervisor_events (supervisor_event_id, event_type,"
                " run_id, config_version, detail, event_time_utc)"
                " VALUES (:sid, :e, :r, :cv, :d, :t)"
            ),
            {
                "sid": generate_ulid(),
                "e": evt,
                "r": run,
                "cv": "phase9.x-o",
                "d": json.dumps({"note": "dummy"}),
                "t": _now() - timedelta(minutes=random.randint(1, 120)),
            },
        )


def _seed_system_jobs(conn) -> None:
    for status in ("success", "running", "failed"):
        conn.execute(
            text(
                "INSERT INTO system_jobs (system_job_id, job_type, status,"
                " started_at, ended_at, result_summary)"
                " VALUES (:jid, 'training', :s, :st, :ed, :rs)"
            ),
            {
                "jid": f"DUMMY-{generate_ulid()}",
                "s": status,
                "st": _now() - timedelta(hours=random.randint(1, 24)),
                "ed": _now() - timedelta(minutes=random.randint(5, 60))
                if status != "running"
                else None,
                "rs": json.dumps({"sharpe": round(random.uniform(0.10, 0.20), 3)})
                if status == "success"
                else None,
            },
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purge", action="store_true", help="Delete dummy data first")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    load_dotenv(repo_root / ".env")
    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        print("ERROR: DATABASE_URL not set (check .env)")
        return 1
    engine = create_engine(db_url)

    with engine.begin() as conn:
        if args.purge:
            print("Purging dummy data ...")
            _purge(conn)

        print("Seeding reference (broker + accounts) ...")
        demo_id, live_id = _seed_reference(conn)

        print(f"Seeding orders + positions for {demo_id} (60 trades over 30d) ...")
        demo_orders = _seed_orders_positions(conn, demo_id, n_filled=60, span_days=30)

        print(f"Seeding orders + positions for {live_id} (40 trades over 30d) ...")
        live_orders = _seed_orders_positions(conn, live_id, n_filled=40, span_days=30)

        print("Seeding close_events ...")
        _seed_close_events(conn, demo_orders + live_orders)

        print("Seeding execution_metrics ...")
        _seed_execution_metrics(conn, demo_orders + live_orders)

        print("Seeding risk_events ...")
        _seed_risk_events(conn)

        print("Seeding dashboard_top_candidates ...")
        _seed_top_candidates(conn)

        print("Seeding supervisor_events ...")
        _seed_supervisor_events(conn)

        print("Seeding system_jobs ...")
        _seed_system_jobs(conn)

    print(f"Done. Accounts: {demo_id}, {live_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
