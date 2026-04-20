"""Schema integrity test for secondary_sync_outbox (Phase 6 Cycle 6.1).

Verifies the alembic migration matches the freeze contract (F-2/F-3/F-12)
and that the SyncSinkProtocol module is importable with the expected
public surface.

DB-free: parses the migration file as text (same approach as
``test_schema_coverage.py``) so it runs in CI without PostgreSQL.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "0013_secondary_sync_outbox.py"
)


@pytest.fixture(scope="module")
def migration_source() -> str:
    return _MIGRATION_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Migration metadata
# ---------------------------------------------------------------------------


class TestMigrationMetadata:
    def test_file_exists(self) -> None:
        assert _MIGRATION_PATH.exists(), f"migration not found at {_MIGRATION_PATH}"

    def test_revision_id(self, migration_source: str) -> None:
        assert 'revision: str = "0013_secondary_sync_outbox"' in migration_source

    def test_chains_to_0012(self, migration_source: str) -> None:
        # Must follow the most recent merged migration without skipping.
        assert (
            'down_revision: Union[str, None] = "0012_dashboard_top_candidates_table"'
            in migration_source
        )

    def test_has_upgrade_and_downgrade(self, migration_source: str) -> None:
        assert "def upgrade() -> None:" in migration_source
        assert "def downgrade() -> None:" in migration_source


# ---------------------------------------------------------------------------
# Table shape
# ---------------------------------------------------------------------------


_REQUIRED_COLUMNS: tuple[str, ...] = (
    # Identity
    "outbox_id",
    # Routing / idempotency
    "table_name",
    "primary_key",
    "version_no",
    # Payload
    "payload_json",
    # Lifecycle
    "enqueued_at",
    "acked_at",
    "last_error",
    "attempt_count",
    "next_attempt_at",
    # Common Keys
    "run_id",
    "environment",
    "code_version",
    "config_version",
)


class TestTableShape:
    def test_create_table_present(self, migration_source: str) -> None:
        assert 'op.create_table(\n        "secondary_sync_outbox"' in migration_source

    @pytest.mark.parametrize("col", _REQUIRED_COLUMNS)
    def test_required_column_declared(self, migration_source: str, col: str) -> None:
        # Tolerant of multi-line sa.Column(...) formatting.
        pattern = re.compile(rf'sa\.Column\(\s*"{re.escape(col)}",')
        assert pattern.search(migration_source), f"column '{col}' missing in migration declaration"

    def test_outbox_id_is_pk(self, migration_source: str) -> None:
        # The outbox_id row carries primary_key=True; also assert no other
        # column does.
        pk_lines = [line for line in migration_source.splitlines() if "primary_key=True" in line]
        assert len(pk_lines) == 1, f"expected exactly one PK column, got {pk_lines}"
        assert "outbox_id" in pk_lines[0]

    def test_payload_is_json(self, migration_source: str) -> None:
        assert 'sa.Column("payload_json", sa.JSON, nullable=False)' in migration_source

    def test_version_no_is_bigint(self, migration_source: str) -> None:
        # Tolerant of multi-line formatting.
        assert re.search(
            r'sa\.Column\(\s*"version_no",\s*sa\.BigInteger',
            migration_source,
        ), "version_no must be sa.BigInteger"

    def test_enqueued_at_has_default_now(self, migration_source: str) -> None:
        # server_default=sa.func.now() pattern from existing migrations.
        # Greedy match across whitespace/newlines to the next sa.Column boundary.
        block = re.search(
            r'"enqueued_at",.*?server_default=sa\.func\.now\(\)',
            migration_source,
            re.DOTALL,
        )
        assert block is not None, "enqueued_at must default to sa.func.now()"
        # Sanity: the match must be reasonably tight (not stretch into a sibling column).
        assert "next_attempt_at" not in block.group(0), (
            "enqueued_at default match overshot into next_attempt_at"
        )

    def test_acked_at_nullable(self, migration_source: str) -> None:
        assert (
            'sa.Column("acked_at", sa.DateTime(timezone=True), nullable=True)' in migration_source
        )

    def test_no_foreign_keys(self, migration_source: str) -> None:
        # Outbox is intentionally FK-free: source rows may be from any table,
        # encoded via (table_name, primary_key) pair.
        assert "ForeignKey" not in migration_source


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------


class TestIndexes:
    def test_pending_index_present(self, migration_source: str) -> None:
        # Must support: WHERE acked_at IS NULL [AND next_attempt_at <= now()]
        #               ORDER BY enqueued_at LIMIT N
        block = re.search(
            r"op\.create_index\(\s*"
            r'"ix_secondary_sync_outbox_pending",\s*'
            r'"secondary_sync_outbox",\s*'
            r'\["acked_at",\s*"next_attempt_at",\s*"enqueued_at"\]',
            migration_source,
        )
        assert block is not None, "pending-poll index missing or wrong columns"

    def test_logical_key_index_present(self, migration_source: str) -> None:
        # Supports observability and de-dup queries.
        block = re.search(
            r"op\.create_index\(\s*"
            r'"ix_secondary_sync_outbox_logical_key",\s*'
            r'"secondary_sync_outbox",\s*'
            r'\["table_name",\s*"primary_key",\s*"version_no"\]',
            migration_source,
        )
        assert block is not None, "logical-key index missing or wrong columns"

    def test_downgrade_drops_indexes_then_table(self, migration_source: str) -> None:
        idx_logical_pos = migration_source.index(
            'drop_index(\n        "ix_secondary_sync_outbox_logical_key"'
        )
        idx_pending_pos = migration_source.index(
            'drop_index(\n        "ix_secondary_sync_outbox_pending"'
        )
        drop_table_pos = migration_source.index('drop_table("secondary_sync_outbox")')
        # Both indexes must be dropped before the table.
        assert idx_logical_pos < drop_table_pos
        assert idx_pending_pos < drop_table_pos


# ---------------------------------------------------------------------------
# SyncSinkProtocol module — Cycle 6.1 contract surface
# ---------------------------------------------------------------------------


class TestSyncProtocolModule:
    def test_module_importable(self) -> None:
        from fx_ai_trading.sync import sink_protocol  # noqa: F401

    def test_exports(self) -> None:
        from fx_ai_trading.sync.sink_protocol import (
            SyncEnvelope,
            SyncResult,
            SyncSinkProtocol,
            __all__,
        )

        assert set(__all__) == {"SyncEnvelope", "SyncResult", "SyncSinkProtocol"}
        assert SyncEnvelope is not None
        assert SyncResult is not None
        assert SyncSinkProtocol is not None

    def test_envelope_fields(self) -> None:
        from fx_ai_trading.sync.sink_protocol import SyncEnvelope

        assert set(SyncEnvelope.__dataclass_fields__.keys()) == {
            "table_name",
            "primary_key",
            "version_no",
            "payload",
        }

    def test_envelope_is_frozen(self) -> None:
        from dataclasses import FrozenInstanceError

        from fx_ai_trading.sync.sink_protocol import SyncEnvelope

        env = SyncEnvelope(
            table_name="positions",
            primary_key='["EUR_USD","2026-04-20T00:00:00Z"]',
            version_no=1,
            payload={"k": "v"},
        )
        with pytest.raises(FrozenInstanceError):
            env.version_no = 2  # type: ignore[misc]

    def test_result_fields(self) -> None:
        from fx_ai_trading.sync.sink_protocol import SyncResult

        assert set(SyncResult.__dataclass_fields__.keys()) == {
            "accepted",
            "error_message",
        }

    def test_result_default_error_message_is_none(self) -> None:
        from fx_ai_trading.sync.sink_protocol import SyncResult

        r = SyncResult(accepted=True)
        assert r.error_message is None

    def test_protocol_has_upsert(self) -> None:
        from fx_ai_trading.sync.sink_protocol import SyncSinkProtocol

        assert hasattr(SyncSinkProtocol, "upsert")

    def test_protocol_runtime_checkable(self) -> None:
        """Stub Sinks must satisfy isinstance() checks at runtime
        (used by Cycle 6.2 worker tests)."""
        from fx_ai_trading.sync.sink_protocol import (
            SyncEnvelope,
            SyncResult,
            SyncSinkProtocol,
        )

        class _StubSink:
            name = "stub"

            def upsert(self, envelope: SyncEnvelope) -> SyncResult:
                return SyncResult(accepted=True)

        assert isinstance(_StubSink(), SyncSinkProtocol)

    def test_module_has_no_db_imports(self) -> None:
        """Contract module must not depend on DB drivers or transports
        (separation guarantees Cycle 6.2 can introduce backends without
        re-shaping the contract)."""
        src = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "fx_ai_trading"
            / "sync"
            / "sink_protocol.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "import sqlalchemy",
            "from sqlalchemy",
            "import supabase",
            "from supabase",
            "import requests",
            "from requests",
        ):
            assert forbidden not in src, (
                f"sink_protocol.py must remain contract-only; found: {forbidden!r}"
            )
