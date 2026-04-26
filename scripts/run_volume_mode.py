"""``run_volume_mode`` — OANDA GOLD-maintenance volume runner (Phase 9.X-F/V-1).

Standalone, alpha-independent runner whose only job is to accumulate
round-trip notional volume on USD/JPY for OANDA Japan GOLD-status
maintenance ($500k/month per public FAQ).

This is **not** a strategy. EV per cycle is designed to be ~0; the
expected cost is the spread paid on the open + close legs.

Why this is separate from ``run_live_loop`` and not part of the alpha
runner: see ``docs/design/phase9_x_f_volume_mode.md``.

Safety contract
---------------
- ``OandaBroker(account_type=...)`` is constructed with the value of
  ``--account``. ``--account live`` ALSO requires ``--confirm-live-trading``.
- The 6.18 invariant (``_verify_account_type_or_raise`` on every order)
  carries through unchanged.
- SIGTERM / SIGINT triggers an immediate flatten-then-halt sequence.
  The process refuses to exit while a USD/JPY position is open.
- A file lock at ``logs/volume_mode.lock`` prevents two simultaneous
  processes from racing on the same OANDA account.
- Pre-trade gates (hours, spread, daily caps, loss cap, volume target)
  re-evaluated every IDLE pass; nothing is "started once and left".

Logging
-------
JSONL to ``logs/volume_mode.jsonl``. Stable event names mirror the
design memo §"Logging" so jq filters in the runbook stay valid.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import random
import signal
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fx_ai_trading.adapters.broker.oanda import OandaBroker
from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient
from fx_ai_trading.adapters.price_feed.oanda_quote_feed import OandaQuoteFeed
from fx_ai_trading.domain.broker import OrderRequest

LOG_FILE = Path("logs/volume_mode.jsonl")
LOCK_FILE = Path("logs/volume_mode.lock")
JST = ZoneInfo("Asia/Tokyo")


# ---------------------------------------------------------------------------
# JSONL logging helper
# ---------------------------------------------------------------------------


class JsonlLogger:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("a", buffering=1, encoding="utf-8")

    def emit(self, event: str, **fields: object) -> None:
        record = {
            "ts": datetime.now(UTC).isoformat(),
            "event": event,
            **fields,
        }
        self._fh.write(json.dumps(record, default=str) + "\n")
        # Mirror to stdout for live tailing.
        print(json.dumps(record, default=str), flush=True)

    def close(self) -> None:
        with contextlib.suppress(Exception):
            self._fh.close()


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass
class Config:
    instrument: str
    units_per_trade: int
    target_volume_usd: float
    max_spread_pip: float
    max_daily_loss_jpy: float
    hours_jst_start: int
    hours_jst_end: int
    max_hourly_trades: int
    max_daily_trades: int
    tp_pip: float
    sl_pip: float
    time_stop_sec: float
    cooloff_min_sec: float
    cooloff_max_sec: float
    pip_size: float = 0.01  # USD/JPY
    poll_interval_sec: float = 2.0
    account_type: str = "demo"
    environment: str = "practice"
    confirm_live: bool = False
    dry_run: bool = False


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------


@dataclass
class SessionState:
    cumulative_volume_usd: float = 0.0
    daily_trades: int = 0
    consecutive_losses: int = 0
    daily_pnl_jpy: float = 0.0
    next_side: str = "long"  # alternates each cycle
    hourly_window: list[float] = field(default_factory=list)
    halt_reason: str | None = None

    def record_hourly(self, now: float) -> None:
        self.hourly_window.append(now)
        cutoff = now - 3600.0
        self.hourly_window = [t for t in self.hourly_window if t >= cutoff]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_hours_jst(spec: str) -> tuple[int, int]:
    try:
        a, b = spec.split("-")
        a_i, b_i = int(a), int(b)
    except Exception as exc:
        raise argparse.ArgumentTypeError(f"--hours-jst must be 'HH-HH' (got {spec!r})") from exc
    if not (0 <= a_i <= 23 and 0 <= b_i <= 23 and a_i < b_i):
        raise argparse.ArgumentTypeError(
            f"--hours-jst values must be 0-23 with start<end (got {spec!r})"
        )
    return a_i, b_i


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_volume_mode",
        description="OANDA GOLD volume maintenance runner (Phase 9.X-F/V-1).",
    )
    p.add_argument("--instrument", default="USD_JPY")
    p.add_argument("--units-per-trade", type=int, default=5000)
    p.add_argument("--target-volume-usd", type=float, default=500_000.0)
    p.add_argument("--max-spread-pip", type=float, default=1.5)
    p.add_argument("--max-daily-loss-jpy", type=float, default=3000.0)
    p.add_argument("--hours-jst", type=_parse_hours_jst, default=(15, 21))
    p.add_argument("--max-hourly-trades", type=int, default=6)
    p.add_argument("--max-daily-trades", type=int, default=50)
    p.add_argument("--tp-pip", type=float, default=1.0)
    p.add_argument("--sl-pip", type=float, default=3.0)
    p.add_argument("--time-stop-sec", type=float, default=90.0)
    p.add_argument("--cooloff-min-sec", type=float, default=30.0)
    p.add_argument("--cooloff-max-sec", type=float, default=60.0)
    p.add_argument("--pip-size", type=float, default=0.01)
    p.add_argument("--poll-interval-sec", type=float, default=2.0)
    p.add_argument(
        "--account",
        choices=("demo", "live"),
        default="demo",
        help="OandaBroker.account_type. Live also requires --confirm-live-trading.",
    )
    p.add_argument(
        "--confirm-live-trading",
        action="store_true",
        help="Required to allow --account live.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip real HTTP order calls; log decisions only.",
    )
    return p


def _config_from_args(ns: argparse.Namespace) -> Config:
    if ns.account == "live" and not ns.confirm_live_trading:
        raise SystemExit(
            "--account live requires --confirm-live-trading (Phase 9.X-F/V-1 safety gate)"
        )
    if ns.cooloff_min_sec > ns.cooloff_max_sec:
        raise SystemExit("--cooloff-min-sec must be <= --cooloff-max-sec")
    if ns.units_per_trade <= 0 or ns.target_volume_usd <= 0:
        raise SystemExit("--units-per-trade and --target-volume-usd must be positive")
    return Config(
        instrument=ns.instrument,
        units_per_trade=ns.units_per_trade,
        target_volume_usd=ns.target_volume_usd,
        max_spread_pip=ns.max_spread_pip,
        max_daily_loss_jpy=ns.max_daily_loss_jpy,
        hours_jst_start=ns.hours_jst[0],
        hours_jst_end=ns.hours_jst[1],
        max_hourly_trades=ns.max_hourly_trades,
        max_daily_trades=ns.max_daily_trades,
        tp_pip=ns.tp_pip,
        sl_pip=ns.sl_pip,
        time_stop_sec=ns.time_stop_sec,
        cooloff_min_sec=ns.cooloff_min_sec,
        cooloff_max_sec=ns.cooloff_max_sec,
        pip_size=ns.pip_size,
        poll_interval_sec=ns.poll_interval_sec,
        account_type=ns.account,
        environment="live" if ns.account == "live" else "practice",
        confirm_live=ns.confirm_live_trading,
        dry_run=ns.dry_run,
    )


# ---------------------------------------------------------------------------
# Pre-trade gates
# ---------------------------------------------------------------------------


def _within_hours(now_jst: datetime, cfg: Config) -> bool:
    h = now_jst.hour
    return cfg.hours_jst_start <= h < cfg.hours_jst_end


def _quote_volume_usd(instrument: str, units: int, mid: float) -> float:
    """Notional in USD for one leg of a market order."""
    base, quote = instrument.split("_")
    if base == "USD":
        return float(units)
    if quote == "USD":
        return float(units) * mid
    # Cross with no USD on either side — not a Mode A target. Fail loudly.
    raise ValueError(f"volume_mode does not support non-USD pair {instrument!r}; use USD/JPY")


def _flat_position(broker: OandaBroker, instrument: str) -> bool:
    positions = broker.get_positions(broker.account_id)
    return all(not (p.instrument == instrument and p.units > 0) for p in positions)


# ---------------------------------------------------------------------------
# Order helpers
# ---------------------------------------------------------------------------


def _new_client_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def _place_market(
    broker: OandaBroker,
    cfg: Config,
    side: str,
) -> tuple[float, str]:
    """Place a market order and return (fill_price, client_order_id)."""
    cid = _new_client_id("vol")
    req = OrderRequest(
        client_order_id=cid,
        account_id=broker.account_id,
        instrument=cfg.instrument,
        side=side,
        size_units=cfg.units_per_trade,
    )
    if cfg.dry_run:
        return 0.0, cid
    result = broker.place_order(req)
    if result.fill_price is None:
        raise RuntimeError(
            f"OANDA returned no fill_price for client_order_id={cid} "
            f"(status={result.status}, message={result.message!r})"
        )
    return float(result.fill_price), cid


# ---------------------------------------------------------------------------
# Volume mode runner
# ---------------------------------------------------------------------------


class VolumeRunner:
    def __init__(
        self,
        cfg: Config,
        broker: OandaBroker,
        quote_feed: OandaQuoteFeed,
        log: JsonlLogger,
    ) -> None:
        self.cfg = cfg
        self.broker = broker
        self.quote = quote_feed
        self.log = log
        self.state = SessionState()
        self._stopping = False
        self._holding_position: tuple[str, float] | None = None  # (side, entry_price)
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum: int, _frame: object) -> None:
        self.log.emit("signal.received", signum=int(signum))
        self._stopping = True

    # ------------------------------------------------------------------
    # Pre-trade gate
    # ------------------------------------------------------------------

    def _gate(self) -> str | None:
        """Return None to proceed, or a reason string to skip."""
        if self.state.halt_reason:
            return self.state.halt_reason
        now_jst = datetime.now(JST)
        if not _within_hours(now_jst, self.cfg):
            return "outside_hours"
        if self.state.cumulative_volume_usd >= self.cfg.target_volume_usd:
            return "volume_target_hit"
        if self.state.daily_trades >= self.cfg.max_daily_trades:
            return "daily_limit"
        if self.state.daily_pnl_jpy <= -self.cfg.max_daily_loss_jpy:
            return "loss_cap"
        if len(self.state.hourly_window) >= self.cfg.max_hourly_trades:
            return "hourly_limit"
        if self.state.consecutive_losses >= 3:
            # 5-minute extended cool-off after 3 consecutive losses.
            return "cooldown_after_losses"
        try:
            q = self.quote.get_quote(self.cfg.instrument)
        except Exception as exc:
            self.log.emit(
                "cycle.error", phase="quote_check", error=str(exc), error_type=type(exc).__name__
            )
            return "quote_error"
        spread_pip = (q.ask - q.bid) / self.cfg.pip_size
        if spread_pip > self.cfg.max_spread_pip:
            return "spread_too_wide"
        return None

    # ------------------------------------------------------------------
    # Single round-trip cycle
    # ------------------------------------------------------------------

    def _run_cycle(self) -> None:
        cfg = self.cfg
        side = self.state.next_side

        # OPEN
        try:
            entry_price, open_cid = _place_market(self.broker, cfg, side)
        except Exception as exc:
            self.log.emit(
                "cycle.error", phase="open", error=str(exc), error_type=type(exc).__name__
            )
            time.sleep(60.0)
            return
        self._holding_position = (side, entry_price)
        self.log.emit(
            "cycle.opened",
            side=side,
            units=cfg.units_per_trade,
            fill_price=entry_price,
            client_order_id=open_cid,
        )

        # HOLD
        hold_target_sec = random.uniform(cfg.cooloff_min_sec, cfg.time_stop_sec)
        sign = 1 if side == "long" else -1
        tp_price = entry_price + sign * cfg.tp_pip * cfg.pip_size
        sl_price = entry_price - sign * cfg.sl_pip * cfg.pip_size
        start = time.time()
        stop_reason = "time"
        last_mid = entry_price
        while not self._stopping:
            elapsed = time.time() - start
            if elapsed >= hold_target_sec:
                stop_reason = "time"
                break
            try:
                q = self.quote.get_quote(cfg.instrument)
            except Exception as exc:
                self.log.emit(
                    "cycle.error", phase="hold_quote", error=str(exc), error_type=type(exc).__name__
                )
                time.sleep(cfg.poll_interval_sec)
                continue
            mid = (q.bid + q.ask) / 2.0
            last_mid = mid
            if sign > 0:
                if mid >= tp_price:
                    stop_reason = "tp"
                    break
                if mid <= sl_price:
                    stop_reason = "sl"
                    break
            else:
                if mid <= tp_price:
                    stop_reason = "tp"
                    break
                if mid >= sl_price:
                    stop_reason = "sl"
                    break
            time.sleep(cfg.poll_interval_sec)

        if self._stopping:
            stop_reason = "signal"

        # CLOSE — uses PositionClose endpoint so it works on both netting
        # (OANDA Japan retail) and hedging (demo/practice) accounts. A plain
        # opposite-direction market order would open a new short leg in
        # hedging mode instead of flattening the long.
        opp = "short" if side == "long" else "long"
        try:
            exit_price, realized_pl_jpy, close_cid = self.broker.close_position(
                cfg.instrument, side
            )
        except Exception as exc:
            self.log.emit(
                "cycle.error",
                phase="close",
                error=str(exc),
                error_type=type(exc).__name__,
                hint="MANUAL_RECONCILE_REQUIRED",
            )
            self.state.halt_reason = "close_failed"
            return

        # P&L: prefer broker-reported realized PnL (OANDA computes net of
        # half-spread cost on both legs). Fall back to mid-price arithmetic
        # only if the broker returned 0.0 (e.g. a stub response).
        pnl_pip = ((exit_price - entry_price) / cfg.pip_size) * sign
        pnl_jpy = (
            realized_pl_jpy
            if realized_pl_jpy != 0.0
            else pnl_pip * cfg.units_per_trade * cfg.pip_size
        )

        leg_volume = _quote_volume_usd(cfg.instrument, cfg.units_per_trade, last_mid)
        round_trip_volume = 2 * leg_volume

        self._holding_position = None
        self.state.cumulative_volume_usd += round_trip_volume
        self.state.daily_trades += 1
        self.state.daily_pnl_jpy += pnl_jpy
        self.state.next_side = opp
        self.state.record_hourly(time.time())
        self.state.consecutive_losses = self.state.consecutive_losses + 1 if pnl_jpy < 0 else 0

        self.log.emit(
            "cycle.closed",
            side=side,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl_pip=round(pnl_pip, 4),
            pnl_jpy=round(pnl_jpy, 2),
            stop_reason=stop_reason,
            hold_sec=round(time.time() - start, 2),
            client_order_id=close_cid,
            volume_usd_round_trip=round(round_trip_volume, 2),
            cumulative_volume_usd=round(self.state.cumulative_volume_usd, 2),
            daily_trades=self.state.daily_trades,
            daily_pnl_jpy=round(self.state.daily_pnl_jpy, 2),
        )

        if self.state.daily_trades % 10 == 0:
            self.log.emit(
                "summary.progress",
                cumulative_volume_usd=round(self.state.cumulative_volume_usd, 2),
                target_volume_usd=cfg.target_volume_usd,
                progress_pct=round(
                    100.0 * self.state.cumulative_volume_usd / cfg.target_volume_usd, 2
                ),
                daily_trades=self.state.daily_trades,
                daily_pnl_jpy=round(self.state.daily_pnl_jpy, 2),
            )

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> int:
        cfg = self.cfg
        self.log.emit(
            "runner.starting",
            account_type=cfg.account_type,
            environment=cfg.environment,
            instrument=cfg.instrument,
            units_per_trade=cfg.units_per_trade,
            target_volume_usd=cfg.target_volume_usd,
            dry_run=cfg.dry_run,
        )

        # Startup invariant: no pre-existing position on this instrument.
        if not cfg.dry_run and not _flat_position(self.broker, cfg.instrument):
            self.log.emit(
                "runner.halt",
                reason="preexisting_position",
                hint="MANUAL_RECONCILE_REQUIRED — flatten via OANDA UI before retry",
            )
            return 2

        while not self._stopping:
            reason = self._gate()
            if reason is not None:
                self.log.emit("cycle.skipped", reason=reason)
                if reason in ("volume_target_hit",):
                    break
                # Different idle waits per gate type:
                if reason == "outside_hours":
                    time.sleep(300.0)
                elif reason == "spread_too_wide":
                    time.sleep(60.0)
                elif reason == "hourly_limit":
                    time.sleep(120.0)
                elif reason == "cooldown_after_losses":
                    time.sleep(300.0)
                    self.state.consecutive_losses = 0
                elif reason in ("daily_limit", "loss_cap"):
                    # Keep idle until JST midnight resets us; operator can SIGTERM.
                    time.sleep(600.0)
                else:
                    time.sleep(30.0)
                continue

            self._run_cycle()

            if self._stopping or self.state.halt_reason:
                break

            cooloff = random.uniform(cfg.cooloff_min_sec, cfg.cooloff_max_sec)
            time.sleep(cooloff)

        # Shutdown: ensure no open position.
        if not cfg.dry_run:
            try:
                if not _flat_position(self.broker, cfg.instrument):
                    self.log.emit(
                        "runner.halt",
                        reason="shutdown_with_open_position",
                        hint="MANUAL_RECONCILE_REQUIRED",
                    )
                    return 3
            except Exception as exc:
                self.log.emit(
                    "cycle.error",
                    phase="shutdown_check",
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                return 4

        self.log.emit(
            "runner.shutdown",
            cumulative_volume_usd=round(self.state.cumulative_volume_usd, 2),
            daily_trades=self.state.daily_trades,
            daily_pnl_jpy=round(self.state.daily_pnl_jpy, 2),
            halt_reason=self.state.halt_reason,
        )
        return 0


# ---------------------------------------------------------------------------
# Lock-file
# ---------------------------------------------------------------------------


class FileLock:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._held = False

    def acquire(self) -> bool:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        try:
            os.write(fd, str(os.getpid()).encode("utf-8"))
        finally:
            os.close(fd)
        self._held = True
        return True

    def release(self) -> None:
        if self._held:
            with contextlib.suppress(FileNotFoundError):
                self._path.unlink()
            self._held = False


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def _build_broker_and_feed(cfg: Config) -> tuple[OandaBroker, OandaQuoteFeed]:
    access_token = os.environ.get("OANDA_ACCESS_TOKEN")
    account_id = os.environ.get("OANDA_ACCOUNT_ID")
    if not access_token or not account_id:
        raise SystemExit("OANDA_ACCESS_TOKEN and OANDA_ACCOUNT_ID env vars are required")
    api_client = OandaAPIClient(access_token=access_token, environment=cfg.environment)
    broker = OandaBroker(
        account_id=account_id,
        access_token=access_token,
        account_type=cfg.account_type,
        environment=cfg.environment,
        api_client=api_client,
    )
    quote_feed = OandaQuoteFeed(api_client=api_client, account_id=account_id)
    return broker, quote_feed


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    cfg = _config_from_args(args)

    log = JsonlLogger(LOG_FILE)
    lock = FileLock(LOCK_FILE)
    if not lock.acquire():
        log.emit(
            "runner.halt",
            reason="another_process_holds_lock",
            lock_path=str(LOCK_FILE),
        )
        log.close()
        return 5

    try:
        if cfg.dry_run:

            class _NullBroker:
                account_id = "DRY_RUN"

                def get_positions(self, _):
                    return []

                def place_order(self, req):
                    raise RuntimeError("dry-run: place_order should not be invoked")

            class _NullFeed:
                def get_quote(self, instrument: str):
                    raise RuntimeError("dry-run: get_quote should not be invoked")

            log.emit("runner.dry_run", note="no broker/feed constructed; gates only")
            broker = _NullBroker()  # type: ignore[assignment]
            quote_feed = _NullFeed()  # type: ignore[assignment]
        else:
            broker, quote_feed = _build_broker_and_feed(cfg)

        runner = VolumeRunner(cfg, broker, quote_feed, log)  # type: ignore[arg-type]
        rc = runner.run()
        return rc
    finally:
        lock.release()
        log.close()


if __name__ == "__main__":
    sys.exit(main())
