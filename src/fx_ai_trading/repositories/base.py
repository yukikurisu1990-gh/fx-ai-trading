"""RepositoryBase — engine holder with Common Keys propagation (D3 §2.9.1).

Common Keys contract (docs/schema_catalog.md §3.3):
  - Every write method must accept CommonKeysContext as a required argument.
  - _with_common_keys() merges context into the params dict.
  - Repositories must NOT commit or rollback — callers own the transaction.
  - Application code must NEVER write Common Keys columns directly.

DB column availability (M5 state):
  - accounts, orders, positions: no Common Keys columns yet (future migration).
    Repositories accept context for validation; keys are NOT in INSERT SQL.
  - app_runtime_state, supervisor_events: run_id + config_version exist (nullable).
    Those repos include only those two keys in INSERT SQL.
  - All other tables: same as accounts/orders/positions until schema is extended.
"""

from __future__ import annotations

from sqlalchemy import Engine

from fx_ai_trading.config.common_keys_context import CommonKeysContext


class RepositoryBase:
    """Base for all repositories.

    Provides:
      - self._engine: SQLAlchemy Engine for SQL execution
      - _with_common_keys(params, context): merge context into INSERT params dict

    Subclasses must:
      - Accept CommonKeysContext on all write (insert/update/upsert) methods
      - Call _with_common_keys() and include relevant keys in SQL
      - Never commit or rollback (caller owns the transaction boundary)
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def _with_common_keys(
        self,
        params: dict,
        context: CommonKeysContext,
    ) -> dict:
        """Return a copy of *params* enriched with all four Common Keys.

        The returned dict always contains run_id, environment, code_version,
        config_version. Callers include only the keys whose columns exist in
        the target table's current schema.

        Example — table with run_id and config_version columns:
            p = self._with_common_keys(params, context)
            conn.execute(
                text("INSERT INTO t (col, run_id, config_version)"
                     " VALUES (:col, :run_id, :config_version)"), p
            )
        """
        return {
            **params,
            "run_id": context.run_id,
            "environment": context.environment,
            "code_version": context.code_version,
            "config_version": context.config_version,
        }
