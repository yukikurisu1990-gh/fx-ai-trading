"""Unit tests for enqueue_secondary_sync — F-12 gate (Cycle 6.2).

This is the ONLY place F-12 sanitize is enforced on the Primary side
(Sinks on the Secondary side trust the payload).  These tests make
the enforcement a hard contract:

  - sanitizer is a required kwarg (TypeError if omitted).
  - sanitizer IS called and its return value is what lands in the
    outbox — the original payload is discarded.
  - A sanitizer that returns non-dict fails loudly (guards against
    someone returning None by accident).

Uses an in-memory SQLite engine — no DATABASE_URL required.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.sync.enqueue import enqueue_secondary_sync

_DDL = """
CREATE TABLE secondary_sync_outbox (
    outbox_id        TEXT PRIMARY KEY,
    table_name       TEXT NOT NULL,
    primary_key      TEXT NOT NULL,
    version_no       BIGINT NOT NULL DEFAULT 0,
    payload_json     TEXT NOT NULL,
    enqueued_at      TEXT NOT NULL,
    acked_at         TEXT,
    last_error       TEXT,
    attempt_count    INTEGER NOT NULL DEFAULT 0,
    next_attempt_at  TEXT,
    run_id           TEXT,
    environment      TEXT,
    code_version     TEXT,
    config_version   TEXT
)
"""


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        conn.execute(text(_DDL))
    yield eng
    eng.dispose()


def _identity(p: dict) -> dict:
    return dict(p)


def _redact(p: dict) -> dict:
    """Contrived sanitizer: blanks anything with 'secret' in the key name."""
    return {k: ("<REDACTED>" if "secret" in k.lower() else v) for k, v in p.items()}


class TestF12SanitizeIsCalled:
    def test_sanitizer_invoked_with_payload(self, engine) -> None:
        """The sanitizer MUST see the raw payload exactly once."""
        seen: list[dict] = []

        def spy(p: dict) -> dict:
            seen.append(p)
            return dict(p)

        enqueue_secondary_sync(
            engine,
            table_name="positions",
            primary_key="pk1",
            version_no=1,
            payload={"a": 1, "b": 2},
            sanitizer=spy,
            clock=FixedClock(datetime(2026, 4, 20, tzinfo=UTC)),
        )
        assert len(seen) == 1
        assert seen[0] == {"a": 1, "b": 2}

    def test_sanitizer_result_is_what_is_stored(self, engine) -> None:
        """The sanitized dict — not the original — ends up in payload_json."""
        enqueue_secondary_sync(
            engine,
            table_name="positions",
            primary_key="pk1",
            version_no=1,
            payload={"api_secret": "hunter2", "user": "alice"},
            sanitizer=_redact,
            clock=FixedClock(datetime(2026, 4, 20, tzinfo=UTC)),
        )
        with engine.connect() as conn:
            raw = conn.execute(text("SELECT payload_json FROM secondary_sync_outbox")).scalar()
        stored = json.loads(str(raw))
        assert stored == {"api_secret": "<REDACTED>", "user": "alice"}
        assert "hunter2" not in json.dumps(stored)

    def test_sanitizer_is_required_kwarg(self, engine) -> None:
        """Omitting sanitizer must fail at call site (TypeError)."""
        with pytest.raises(TypeError):
            enqueue_secondary_sync(  # type: ignore[call-arg]
                engine,
                table_name="positions",
                primary_key="pk1",
                version_no=1,
                payload={"x": 1},
                clock=FixedClock(datetime(2026, 4, 20, tzinfo=UTC)),
            )

    def test_non_callable_sanitizer_raises(self, engine) -> None:
        with pytest.raises(ValueError, match="sanitizer must be callable"):
            enqueue_secondary_sync(
                engine,
                table_name="positions",
                primary_key="pk1",
                version_no=1,
                payload={"x": 1},
                sanitizer="not-a-function",  # type: ignore[arg-type]
                clock=FixedClock(datetime(2026, 4, 20, tzinfo=UTC)),
            )

    def test_sanitizer_returning_non_dict_raises(self, engine) -> None:
        with pytest.raises(ValueError, match="sanitizer must return a dict"):
            enqueue_secondary_sync(
                engine,
                table_name="positions",
                primary_key="pk1",
                version_no=1,
                payload={"x": 1},
                sanitizer=lambda p: None,  # type: ignore[return-value,arg-type]
                clock=FixedClock(datetime(2026, 4, 20, tzinfo=UTC)),
            )


class TestArgumentValidation:
    def test_empty_table_name_raises(self, engine) -> None:
        with pytest.raises(ValueError, match="table_name must be non-empty"):
            enqueue_secondary_sync(
                engine,
                table_name="",
                primary_key="pk1",
                version_no=1,
                payload={},
                sanitizer=_identity,
                clock=FixedClock(datetime(2026, 4, 20, tzinfo=UTC)),
            )

    def test_empty_primary_key_raises(self, engine) -> None:
        with pytest.raises(ValueError, match="primary_key must be non-empty"):
            enqueue_secondary_sync(
                engine,
                table_name="positions",
                primary_key="",
                version_no=1,
                payload={},
                sanitizer=_identity,
                clock=FixedClock(datetime(2026, 4, 20, tzinfo=UTC)),
            )

    def test_negative_version_raises(self, engine) -> None:
        with pytest.raises(ValueError, match="version_no must be >= 0"):
            enqueue_secondary_sync(
                engine,
                table_name="positions",
                primary_key="pk1",
                version_no=-1,
                payload={},
                sanitizer=_identity,
                clock=FixedClock(datetime(2026, 4, 20, tzinfo=UTC)),
            )


class TestRowShape:
    def test_returns_ulid(self, engine) -> None:
        rid = enqueue_secondary_sync(
            engine,
            table_name="positions",
            primary_key="pk1",
            version_no=1,
            payload={"x": 1},
            sanitizer=_identity,
            clock=FixedClock(datetime(2026, 4, 20, tzinfo=UTC)),
        )
        assert isinstance(rid, str) and len(rid) == 26

    def test_common_keys_persisted(self, engine) -> None:
        enqueue_secondary_sync(
            engine,
            table_name="positions",
            primary_key="pk1",
            version_no=1,
            payload={"x": 1},
            sanitizer=_identity,
            clock=FixedClock(datetime(2026, 4, 20, tzinfo=UTC)),
            run_id="run-001",
            environment="paper",
            code_version="abc1234",
            config_version="cv-5",
        )
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT run_id, environment, code_version, config_version"
                    " FROM secondary_sync_outbox"
                )
            ).fetchone()
        assert row == ("run-001", "paper", "abc1234", "cv-5")

    def test_default_attempt_count_is_zero(self, engine) -> None:
        enqueue_secondary_sync(
            engine,
            table_name="positions",
            primary_key="pk1",
            version_no=1,
            payload={"x": 1},
            sanitizer=_identity,
            clock=FixedClock(datetime(2026, 4, 20, tzinfo=UTC)),
        )
        with engine.connect() as conn:
            ac = conn.execute(text("SELECT attempt_count FROM secondary_sync_outbox")).scalar()
        assert ac == 0
