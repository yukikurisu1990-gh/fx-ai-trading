"""Unit tests for CalendarService — Phase 9.X-H."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from fx_ai_trading.services.calendar_service import (
    CALENDAR_ZERO_FEATURES,
    POST_EVENT_HOURS,
    PRE_EVENT_HOURS,
    CalendarEvent,
    CalendarService,
    empty_calendar,
)


def _make(ts: str, ccy: str, name: str, imp: str) -> CalendarEvent:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return CalendarEvent(timestamp=dt, currency=ccy, event_name=name, importance=imp)


# ---------------------------------------------------------------------------
# Construction / loading
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_empty_calendar(self) -> None:
        svc = empty_calendar()
        assert svc.event_count("USD") == 0
        feats = svc.compute_features("EUR_USD", datetime(2026, 1, 1, tzinfo=UTC))
        assert set(feats.keys()) == set(CALENDAR_ZERO_FEATURES.keys())

    def test_skips_low_importance(self) -> None:
        svc = CalendarService(
            [
                _make("2025-09-17T18:00:00Z", "USD", "FOMC", "high"),
                _make("2025-09-18T12:00:00Z", "USD", "Some-low-event", "low"),
            ]
        )
        assert svc.event_count("USD") == 1

    def test_skips_unknown_currency(self) -> None:
        svc = CalendarService(
            [
                _make("2025-09-17T18:00:00Z", "USD", "FOMC", "high"),
                _make("2025-09-18T12:00:00Z", "XYZ", "Made-up", "high"),
            ]
        )
        assert svc.event_count("USD") == 1
        assert svc.event_count("XYZ") == 0

    def test_skips_invalid_importance(self) -> None:
        svc = CalendarService([_make("2025-09-17T18:00:00Z", "USD", "FOMC", "garbage")])
        assert svc.event_count("USD") == 0

    def test_csv_round_trip(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "events.csv"
        csv_path.write_text(
            "timestamp_utc,currency,event_name,importance\n"
            "2025-09-17T18:00:00Z,USD,FOMC Rate Decision,high\n"
            "2025-09-12T12:30:00Z,USD,Non-Farm Payrolls,high\n",
            encoding="utf-8",
        )
        svc = CalendarService.from_csv(csv_path)
        assert svc.event_count("USD") == 2

    def test_csv_skips_malformed(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "bad.csv"
        csv_path.write_text(
            "timestamp_utc,currency,event_name,importance\n"
            "not-a-date,USD,Garbage,high\n"
            "2025-09-17T18:00:00Z,USD,FOMC,high\n",
            encoding="utf-8",
        )
        svc = CalendarService.from_csv(csv_path)
        assert svc.event_count("USD") == 1


# ---------------------------------------------------------------------------
# Feature computation
# ---------------------------------------------------------------------------


_FOMC = "2025-09-17T18:00:00Z"


def _svc_with_fomc() -> CalendarService:
    return CalendarService([_make(_FOMC, "USD", "FOMC", "high")])


class TestFeatureComputation:
    def test_returns_all_nine_keys(self) -> None:
        svc = _svc_with_fomc()
        feats = svc.compute_features("EUR_USD", datetime(2025, 9, 17, 17, 0, tzinfo=UTC))
        expected = {
            "cal_h_to_next_base",
            "cal_h_since_last_base",
            "cal_h_to_next_quote",
            "cal_h_since_last_quote",
            "cal_in_pre_event",
            "cal_in_post_event",
            "cal_in_quiet",
            "cal_imp_next",
            "cal_imp_recent",
        }
        assert set(feats.keys()) == expected

    def test_pre_event_window_at_15min(self) -> None:
        svc = _svc_with_fomc()
        # 15 min before FOMC → in_pre_event = 1
        feats = svc.compute_features("EUR_USD", datetime(2025, 9, 17, 17, 45, tzinfo=UTC))
        assert feats["cal_in_pre_event"] == 1.0
        assert feats["cal_in_post_event"] == 0.0
        assert feats["cal_in_quiet"] == 0.0

    def test_post_event_window_at_30min_after(self) -> None:
        svc = _svc_with_fomc()
        # 30 min after → in_post_event = 1
        feats = svc.compute_features("EUR_USD", datetime(2025, 9, 17, 18, 30, tzinfo=UTC))
        assert feats["cal_in_post_event"] == 1.0
        assert feats["cal_in_pre_event"] == 0.0

    def test_quiet_window(self) -> None:
        svc = _svc_with_fomc()
        # 5 hours before FOMC → quiet (next event > 2h, no recent event)
        feats = svc.compute_features("EUR_USD", datetime(2025, 9, 17, 13, 0, tzinfo=UTC))
        assert feats["cal_in_quiet"] == 1.0
        assert feats["cal_in_pre_event"] == 0.0
        assert feats["cal_in_post_event"] == 0.0

    def test_pre_window_boundary_inclusive(self) -> None:
        svc = _svc_with_fomc()
        # Exactly 30 min before — should be IN pre-event window.
        feats = svc.compute_features(
            "EUR_USD",
            datetime(2025, 9, 17, 17, 30, tzinfo=UTC),
        )
        assert feats["cal_in_pre_event"] == 1.0

    def test_hours_to_next_correct(self) -> None:
        svc = _svc_with_fomc()
        # EUR_USD: base=EUR (no events), quote=USD (FOMC at 18:00).
        feats = svc.compute_features("EUR_USD", datetime(2025, 9, 17, 16, 0, tzinfo=UTC))
        # No EUR events → base sentinel.
        assert feats["cal_h_to_next_base"] >= 100.0
        # 18:00 - 16:00 = 2 hours to FOMC on USD (quote side).
        assert feats["cal_h_to_next_quote"] == pytest.approx(2.0, abs=0.01)

    def test_hours_since_last_correct(self) -> None:
        svc = _svc_with_fomc()
        feats = svc.compute_features("EUR_USD", datetime(2025, 9, 17, 21, 0, tzinfo=UTC))
        # 21:00 - 18:00 = 3 hours since FOMC
        assert feats["cal_h_since_last_quote"] == pytest.approx(3.0, abs=0.01)

    def test_no_event_returns_sentinel(self) -> None:
        svc = empty_calendar()
        feats = svc.compute_features("EUR_USD", datetime(2025, 9, 17, 18, 0, tzinfo=UTC))
        # Sentinel = 999.0 hours when no event in either direction.
        assert feats["cal_h_to_next_base"] >= 100.0
        assert feats["cal_h_since_last_base"] >= 100.0

    def test_importance_recorded(self) -> None:
        svc = CalendarService(
            [
                _make("2025-09-17T18:00:00Z", "USD", "FOMC", "high"),
                _make("2025-09-17T20:00:00Z", "USD", "Retail Sales", "medium"),
            ]
        )
        # 1 hour BEFORE FOMC → next event is FOMC (high)
        feats = svc.compute_features("EUR_USD", datetime(2025, 9, 17, 17, 0, tzinfo=UTC))
        assert feats["cal_imp_next"] == 1.0  # high
        # 30 min AFTER FOMC → recent is FOMC (high), next is Retail (medium)
        feats = svc.compute_features("EUR_USD", datetime(2025, 9, 17, 18, 30, tzinfo=UTC))
        assert feats["cal_imp_recent"] == 1.0
        assert feats["cal_imp_next"] == 0.5

    def test_naive_datetime_treated_as_utc(self) -> None:
        svc = _svc_with_fomc()
        # Naive datetime (no tzinfo) — should be coerced to UTC.
        # EUR_USD has FOMC on the quote side (USD).
        feats = svc.compute_features("EUR_USD", datetime(2025, 9, 17, 16, 0))
        assert feats["cal_h_to_next_quote"] == pytest.approx(2.0, abs=0.01)

    def test_pair_split_uses_correct_currencies(self) -> None:
        svc = CalendarService(
            [
                _make("2025-09-17T18:00:00Z", "USD", "FOMC", "high"),
                _make("2025-09-17T03:00:00Z", "JPY", "BOJ", "high"),
            ]
        )
        # USD_JPY at 12:00 UTC → both currencies have past+future events
        feats = svc.compute_features("USD_JPY", datetime(2025, 9, 17, 12, 0, tzinfo=UTC))
        # base=USD, FOMC at 18:00 → 6h to next
        assert feats["cal_h_to_next_base"] == pytest.approx(6.0, abs=0.01)
        # quote=JPY, BOJ at 03:00 → 9h since last
        assert feats["cal_h_since_last_quote"] == pytest.approx(9.0, abs=0.01)

    def test_invalid_pair_raises(self) -> None:
        svc = empty_calendar()
        with pytest.raises(ValueError, match="Invalid instrument"):
            svc.compute_features("XYZ", datetime(2025, 9, 17, 18, 0, tzinfo=UTC))

    def test_features_rounded(self) -> None:
        svc = _svc_with_fomc()
        feats = svc.compute_features("EUR_USD", datetime(2025, 9, 17, 17, 33, 12, tzinfo=UTC))
        for v in feats.values():
            # All values are floats with at most 4dp.
            assert isinstance(v, float)
            assert v == round(v, 4)

    def test_real_csv_loads(self) -> None:
        # Smoke test: real curated CSV should load without errors.
        path = Path("data/economic_calendar/events_2025_2026.csv")
        if not path.exists():
            pytest.skip("Curated CSV not present in this environment")
        svc = CalendarService.from_csv(path)
        # Expect at least 50 events across the 9-month window.
        total = sum(svc.event_count(c) for c in ("USD", "EUR", "JPY", "GBP", "AUD", "CAD"))
        assert total >= 50

    def test_const_zero_features_match_keys(self) -> None:
        svc = _svc_with_fomc()
        feats = svc.compute_features("EUR_USD", datetime(2025, 9, 17, 17, 0, tzinfo=UTC))
        assert set(feats.keys()) == set(CALENDAR_ZERO_FEATURES.keys())


class TestConstants:
    def test_pre_event_hours(self) -> None:
        assert PRE_EVENT_HOURS == 0.5

    def test_post_event_hours(self) -> None:
        assert POST_EVENT_HOURS == 1.0
