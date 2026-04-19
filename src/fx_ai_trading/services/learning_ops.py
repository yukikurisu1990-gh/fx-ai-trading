"""LearningOps service — training job management via system_jobs (M21 / M-LRN-1).

Iteration 2 design:
  - enqueue()      : INSERT a 'training' job into system_jobs (status=pending).
  - execute_stub() : Stub executor that immediately marks the job succeeded and
                     inserts a placeholder training_run.  The real executor is
                     Phase 7; callers reference it through the LearningExecutor
                     Protocol (docs/implementation_contracts.md §2.17).

No SQL DELETE is used — status transitions use UPDATE (append-only model).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import Engine, text

log = logging.getLogger(__name__)

_JOB_TYPE = "training"


class LearningOps:
    """Manage training job lifecycle in system_jobs."""

    def enqueue(
        self,
        engine: Engine,
        input_params: dict | None = None,
    ) -> str:
        """INSERT a pending training job.  Returns the new system_job_id."""
        job_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
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
        now = datetime.now(UTC).isoformat()
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


_ops = LearningOps()
