"""LearningOps service — training job management via system_jobs (M21 / M-LRN-1).

Iteration 2 design:
  - enqueue()      : INSERT a 'training' job into system_jobs (status=pending).
  - execute_stub() : Stub executor that immediately marks the job succeeded and
                     inserts a placeholder training_run.  The real executor is
                     Phase 7; callers reference it through the LearningExecutor
                     Protocol (docs/implementation_contracts.md §2.17).

Phase 9.8 additions:
  - register_challenger() : INSERT a training_run with status='challenger'.
  - get_champion()        : Return the most recent 'champion' training_run row.
  - promote()             : Retire current champion, elevate challenger to champion.
  - log_promotion_decision() : Append to promotion_decisions audit table.
  - ensure_promotion_schema(): CREATE TABLE promotion_decisions if not exists.

No SQL DELETE is used — status transitions use UPDATE (append-only model).
"""

from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy import Engine, text

from fx_ai_trading.common.clock import Clock, WallClock

log = logging.getLogger(__name__)

_JOB_TYPE = "training"

_PROMOTION_DECISIONS_DDL = """
CREATE TABLE IF NOT EXISTS promotion_decisions (
    decision_id       TEXT PRIMARY KEY,
    challenger_run_id TEXT NOT NULL,
    champion_run_id   TEXT,
    promoted          INTEGER NOT NULL,
    reason            TEXT NOT NULL,
    criteria_met      TEXT NOT NULL,
    created_at        TEXT NOT NULL
)
"""


class LearningOps:
    """Manage training job lifecycle in system_jobs (M21) and model promotion (Phase 9.8)."""

    def __init__(self, clock: Clock | None = None) -> None:
        self._clock: Clock = clock or WallClock()

    # ------------------------------------------------------------------
    # M21 — training job lifecycle
    # ------------------------------------------------------------------

    def enqueue(
        self,
        engine: Engine,
        input_params: dict | None = None,
    ) -> str:
        """INSERT a pending training job.  Returns the new system_job_id."""
        job_id = str(uuid.uuid4())
        now = self._clock.now().isoformat()
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO system_jobs"
                    " (system_job_id, job_type, status, input_params, created_at)"
                    " VALUES (:jid, :jtype, 'pending', :params, :now)"
                ),
                {
                    "jid": job_id,
                    "jtype": _JOB_TYPE,
                    "params": str(input_params or {}),
                    "now": now,
                },
            )
        log.info("LearningOps.enqueue: job_id=%s", job_id)
        return job_id

    def execute_stub(self, engine: Engine, job_id: str) -> None:
        """Stub executor: transition job to 'success' and record a training_run.

        Phase 7 replaces this with a real LearningExecutor implementation.
        """
        now = self._clock.now().isoformat()
        run_id = str(uuid.uuid4())
        experiment_id = f"stub_{job_id[:8]}"
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE system_jobs"
                    " SET status = 'success', started_at = :now, ended_at = :now"
                    " WHERE system_job_id = :jid"
                ),
                {"now": now, "jid": job_id},
            )
            conn.execute(
                text(
                    "INSERT INTO training_runs"
                    " (training_run_id, experiment_id, status, created_at)"
                    " VALUES (:rid, :eid, 'success', :now)"
                ),
                {"rid": run_id, "eid": experiment_id, "now": now},
            )
        log.info("LearningOps.execute_stub: job_id=%s → success, run_id=%s", job_id, run_id)

    # ------------------------------------------------------------------
    # Phase 9.8 — challenger / champion lifecycle
    # ------------------------------------------------------------------

    def register_challenger(
        self,
        engine: Engine,
        model_id: str,
        paper_stats: dict | None = None,
        artifact_path: str | None = None,
    ) -> str:
        """INSERT a training_run with status='challenger'.

        *paper_stats* should contain paper-run metrics (paper_days, trade_count,
        sharpe, max_drawdown) so that run_promotion_gate.py can evaluate promotion
        criteria without a separate metrics table.

        Returns the new training_run_id.
        """
        run_id = str(uuid.uuid4())
        now = self._clock.now().isoformat()
        params_json = json.dumps(paper_stats or {})
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO training_runs"
                    " (training_run_id, model_id, status, artifact_path,"
                    "  input_params, created_at)"
                    " VALUES (:rid, :mid, 'challenger', :path, :params, :now)"
                ),
                {
                    "rid": run_id,
                    "mid": model_id,
                    "path": artifact_path or "",
                    "params": params_json,
                    "now": now,
                },
            )
        log.info("LearningOps.register_challenger: run_id=%s model_id=%s", run_id, model_id)
        return run_id

    def get_champion(self, engine: Engine) -> dict | None:
        """Return the most recent training_run with status='champion', or None."""
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT training_run_id, model_id, input_params, artifact_path, created_at"
                    " FROM training_runs"
                    " WHERE status = 'champion'"
                    " ORDER BY created_at DESC"
                    " LIMIT 1"
                )
            ).fetchone()
        if row is None:
            return None
        return dict(row._mapping)

    def promote(self, engine: Engine, challenger_run_id: str) -> None:
        """Retire current champion and elevate *challenger_run_id* to 'champion'.

        The retired champion's status becomes 'retired' (append-only).
        """
        now = self._clock.now().isoformat()
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE training_runs SET status = 'retired', ended_at = :now"
                    " WHERE status = 'champion'"
                ),
                {"now": now},
            )
            conn.execute(
                text(
                    "UPDATE training_runs SET status = 'champion', started_at = :now"
                    " WHERE training_run_id = :rid"
                ),
                {"now": now, "rid": challenger_run_id},
            )
        log.info("LearningOps.promote: challenger_run_id=%s → champion", challenger_run_id)

    def log_promotion_decision(
        self,
        engine: Engine,
        challenger_run_id: str,
        champion_run_id: str | None,
        promoted: bool,
        reason: str,
        criteria_met: dict[str, bool],
    ) -> str:
        """INSERT a promotion_decisions row for audit purposes.

        Returns the new decision_id.
        Call ensure_promotion_schema() once before first use.
        """
        decision_id = str(uuid.uuid4())
        now = self._clock.now().isoformat()
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO promotion_decisions"
                    " (decision_id, challenger_run_id, champion_run_id,"
                    "  promoted, reason, criteria_met, created_at)"
                    " VALUES (:did, :chal, :champ, :prom, :reason, :criteria, :now)"
                ),
                {
                    "did": decision_id,
                    "chal": challenger_run_id,
                    "champ": champion_run_id,
                    "prom": 1 if promoted else 0,
                    "reason": reason,
                    "criteria": json.dumps(criteria_met),
                    "now": now,
                },
            )
        log.info(
            "LearningOps.log_promotion_decision: decision_id=%s promoted=%s reason=%s",
            decision_id,
            promoted,
            reason,
        )
        return decision_id

    def ensure_promotion_schema(self, engine: Engine) -> None:
        """CREATE TABLE promotion_decisions IF NOT EXISTS."""
        with engine.begin() as conn:
            conn.execute(text(_PROMOTION_DECISIONS_DDL))


_ops = LearningOps()
