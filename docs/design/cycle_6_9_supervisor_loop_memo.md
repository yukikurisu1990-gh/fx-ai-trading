# Cycle 6.9 — Supervisor Loop / CadenceWatchdog Connection Memo

> **Status:** Design memo (informational). Adds no code, no schema, no test.
> **Audience:** Implementers of M8 (Reconciler / MidRunReconciler lifecycle) and M9 / M12 (1-minute trading cycle loop).
> **Authoring anchor:** master tip `f401629` (after Cycle 6.9b closure, 2026-04-22).

## 1. 目的と前提

**目的.** Cycle 6.9a (CadenceWatchdog) was *blocked* during Iteration 2 because the integration point it requires — a unified supervisor cadence loop — does not yet exist (`src/fx_ai_trading/supervisor/supervisor.py:9-13` defers it to M8/M9/M12). This memo records the contracts and decisions the 6.9a Designer Freeze already fixed, so when the loop lands the watchdog can attach without re-deriving them.

**現状の前提 (memo authoring time):**

- `Supervisor` provides one-shot lifecycle only — `startup()` / `is_trading_allowed()` / `trigger_safe_stop()` / `attach_metrics_loop()` + `record_metrics()` / `check_health()`.
- No running cadence loop. The 4 in-system runners (`meta_cycle_runner`, `execution_gate_runner`, `midrun_reconciler`, `sync/service`) plus `exit_gate_runner` are driven by external callers.
- Cycle 6.9a Designer Freeze monitored **4 components** (meta_cycle, execution_gate, midrun_reconciler, sync_worker). `exit_gate` is a 5th in-cycle component (added in Cycle 6.7c) but was *not* in the 6.9a contract — see §7.
- Cycle 6.9b (`ExitFireMetricsService`) is supervisor-loop independent and does not need this memo to be implementable.

**Scope of this memo.** Contracts (component_tick payload, cadence_violation detail), the wrapper integration point, in-cycle component ordering, exception-propagation rules, and safe_stop/degraded interaction — see §7 for what is intentionally left out.

## 2. 将来の supervisor loop の責務

When `Supervisor.run_cycle()` (or equivalent) is implemented, it must satisfy:

| Responsibility | Detail |
|---|---|
| **Single dispatch entry per cycle** | All in-cycle components are invoked from one place. No caller-side fan-out. |
| **try/finally tick emission** | Each monitored component dispatch is wrapped in `try / finally` so `component_tick` is emitted even on exception. Status = `ok` on normal return, `error` on exception (then re-raise per §5). |
| **Watchdog as terminal step** | After component dispatch, `CadenceWatchdog.check()` is invoked as a step in its own right (last in order). |
| **Idempotent under safe_stop / degraded** | Skip trading-side dispatch but keep `sync_worker` and (a subset of) reconciler running to honour safe-stop's data-completeness guarantees. See §6. |
| **Cycle id continuity** | A `cycle_id` (UUID) is generated at the start of each cycle and propagated into the `component_tick.cycle_id` field for `meta_cycle` only. Other components carry `cycle_id=null` (they have no strategy-cycle identity). |
| **`record_metrics()` migration** | The current caller-driven `record_metrics()` (M16) becomes loop-driven once the cycle exists. Existing `attach_metrics_loop()` API stays for backward compatibility. |
| **Zero schema migration** | Tick rows reuse `supervisor_events` (additive `event_type='component_tick'`). Violation rows reuse `reconciliation_events` (additive `trigger_reason='cadence_violation'`). |

## 3. cadence watchdog の接続ポイント

(All shapes copied verbatim from Cycle 6.9a Designer Freeze; do not redesign.)

### 3.1 component_tick contract

- **Storage:** `supervisor_events` row, `event_type='component_tick'` (additive value, no new column).
- **Detail JSON shape:**

  ```json
  {
    "component": "meta_cycle" | "execution_gate" | "midrun_reconciler" | "sync_worker",
    "status":    "ok" | "error",
    "duration_ms": <int >= 0>,
    "cycle_id":  "<uuid>" | null
  }
  ```

- **Emission point:** the supervisor wrapper, NOT the component itself (component bodies remain untouched — same constraint that blocked 6.9a's caller-side wrapper alternative).
- **`event_time_utc`:** stamped by the supervisor's existing injected `Clock` — never `datetime.now()` in component code (development_rules §13.1).
- **Retention:** 24–72h short retention, distinct from other `supervisor_events` rows (≥30d). Reason: high write frequency (≥1 per component per cycle × N cycles/min). Audit value lives in `cadence_violation` rows (long-retention table), not the ticks themselves. Implementation of the retention job is *not* part of this memo.

### 3.2 Wrapper helper signature

```python
# Inside Supervisor (or a small adjacent helper module).
def _emit_component_tick(
    self,
    component: str,
    status: str,            # 'ok' | 'error'
    duration_ms: int,
    cycle_id: str | None = None,
) -> None: ...
```

Wrapper pattern:

```python
start = perf_counter()
try:
    runner.run_one()
except Exception:
    self._emit_component_tick(component, "error",
                              int((perf_counter() - start) * 1000), cycle_id)
    raise
self._emit_component_tick(component, "ok",
                          int((perf_counter() - start) * 1000), cycle_id)
```

(The `try / finally` form with a status flag is equivalent and may be preferred for readability.)

### 3.3 cadence_violation contract

- **Storage:** `reconciliation_events` row with `trigger_reason='cadence_violation'`, `action_taken='cadence_violation_detected'`, `order_id=NULL`, `position_snapshot_id=NULL`.
- **Detail JSON shape:**

  ```json
  {
    "component": "meta_cycle" | "execution_gate" | "midrun_reconciler" | "sync_worker",
    "last_seen_at": "<ISO8601 UTC>" | null,
    "lag_seconds": <float, 2 dp>,
    "threshold_seconds": <int>,
    "cooloff_seconds": <int>,
    "grace_period_seconds": <int>,
    "supervisor_state": "running" | "degraded" | "safe_stop"
  }
  ```

- **Emitted by `CadenceWatchdog.check()` only.** No automated remediation.
- **False-positive suppression** (in-memory state on the watchdog instance):
  - Grace period from supervisor start: default 120s — no violation in this window.
  - Per-component cooloff after a violation: default 600s — second violation for the same component within cooloff is suppressed.
  - State guard: skip the check entirely when `supervisor_state` ∉ {'running'} (see §6).
- A quiet system writes nothing — read-many, write-one-per-actual-violation.

### 3.4 Threshold defaults (from 6.9a Freeze)

| Component | threshold_seconds |
|---|---|
| meta_cycle | 180 |
| execution_gate | 180 |
| midrun_reconciler | 2700 |
| sync_worker | 120 |

Stored as `app_settings` keys `watchdog.<component>.threshold_seconds`. Plus `watchdog.cooloff_seconds` and `watchdog.grace_period_seconds`. Seeding is part of the eventual 6.9a unblock PR, not this memo.

## 4. component 実行順序

Within one supervisor cycle:

```
1. meta_cycle           ← signal generation
2. execution_gate       ← entry decision
3. exit_gate            ← position close decision        (NOT a 6.9a-watched component — see §7)
4. midrun_reconciler    ← drift detection
5. sync_worker          ← secondary persistence drain    (may also live as a separate runner — see note)
6. watchdog.check()     ← cadence observation (terminal)
```

**Rationale:**

- `meta_cycle` first: produces the signals that the gates consume.
- `execution_gate` before `exit_gate`: new entries are evaluated before close evaluation. A same-cycle entry+exit (rare but possible in stress) stays internally consistent.
- `midrun_reconciler` after the trading gates: reconciles only after this cycle's writes have settled. Startup reconciler covers the post-restart window, so skipping this step in degraded states is acceptable.
- `sync_worker` after reconciler: any new audit rows from reconciliation drain to the secondary outbox in the same cycle.
- `watchdog.check()` last: observes the freshest set of `component_tick` rows. A violation surfaced at cycle N reflects an absent tick that should have arrived by cycle N-1 or earlier.

**Out-of-cycle exception for `sync_worker`.** The current architecture treats `sync_worker` as a separate background runner. If that stays true post-M9, it is *not* invoked from `run_cycle()`, but it still emits its own `component_tick` from inside its own loop wrapper (the contract is identical; the emission site moves). The watchdog continues to watch it the same way.

## 5. 各 step の例外伝播ポリシー

| Step | On exception | Tick status | Cycle continues? |
|---|---|---|---|
| meta_cycle | log + emit `component_tick(status='error')` | `error` | yes — downstream gates still run (no-op if no fresh signals) |
| execution_gate | log + emit `component_tick(status='error')` | `error` | yes — exit_gate must still run to honour stop-loss |
| exit_gate | log only (NOT a watched component per 6.9a) | n/a | yes — midrun_reconciler still runs |
| midrun_reconciler | log + emit `component_tick(status='error')` | `error` | yes — its per-order try/except is preserved |
| sync_worker | log + emit `component_tick(status='error')` | `error` | yes — next cycle re-attempts the drain |
| watchdog.check() | log only — do **not** emit a `component_tick` for the watchdog itself | n/a | yes — watchdog failure must never cascade |
| **Hard fail** (e.g. DB unreachable on every step) | the existing `Supervisor.trigger_safe_stop()` machinery fires (no new behaviour) | varies | no — safe_stop terminates the loop |

**Rule of thumb:** Component exceptions are *contained*. Repeated/cascading failures invoke the existing safe_stop pathway. The watchdog never triggers safe_stop directly — it only writes audit rows.

## 6. safe_stop / degraded 時の扱い

**State sources:**

- `Supervisor.is_trading_allowed()` — gate flag, becomes False on safe_stop or until startup completes.
- `supervisor_state` (string) carried in `cadence_violation.detail` — derived from supervisor lifecycle. Accepted values: `running` / `degraded` / `safe_stop`.

**Behaviour matrix:**

| supervisor_state | meta_cycle | execution_gate | exit_gate | midrun_reconciler | sync_worker | watchdog.check() |
|---|---|---|---|---|---|---|
| `running`  | run  | run  | run  | run  | run | run (full check) |
| `degraded` | run  | **skip** | run  | run  | run | **skip** (no violation emit) |
| `safe_stop`| **skip** | **skip** | **skip** | **skip** | run | **skip** (no violation emit) |

**Why watchdog skips when not `running`:**

- A halted system intentionally stops emitting ticks; treating that as a violation would generate noise that buries real signals.
- `degraded` is reserved for partial outages where the trading half is paused but observability + sync continue — incomplete tick coverage is by design.
- The cooloff dict (§3.3) is preserved across state transitions so a system that briefly degrades and recovers does not double-emit on resumption.

**Why `sync_worker` keeps running under safe_stop:**

- Secondary persistence drain is part of safe_stop's data-completeness guarantee. The outbox should reach acked state before the process exits. This holds regardless of where `sync_worker` lives (in-cycle or out-of-cycle).

## 7. 非対象 (このメモで決めないこと)

The following are explicitly outside this memo's scope and remain undecided:

1. **Concrete `Supervisor.run_cycle()` signature.** Async vs sync, how the loop is driven (asyncio task / thread / external scheduler), shutdown coordination, and how `run_cycle()` interacts with the existing `startup()` / `safe_stop()` methods. M8/M9/M12 implementer's call.
2. **Per-cycle wall time / pacing strategy.** Fixed 60s, drift-corrected, jitter, etc. The existing `attach_metrics_loop()` (M16) implies a 60s cadence but is not authoritative for the trading loop.
3. **Component back-pressure / queueing.** What happens when one component runs longer than the cycle period. Likely wants a separate "long-running detector" rather than overloading the cadence watchdog.
4. **Watchdog auto-remediation.** The 6.9a Freeze explicitly forbade it. This memo does not revisit the decision.
5. **Watching `exit_gate` via cadence_watchdog.** The 6.9a contract enumerates 4 components only. Whether to extend coverage to `exit_gate` (a 5th in-cycle component added in Cycle 6.7c) is a future decision — both the `component_tick` and `cadence_violation` enums would need to be widened, with corresponding new threshold key.
6. **Cycle-id propagation to non-meta components.** Current contract sets `cycle_id=null` for non-meta_cycle ticks. A future cycle-scoped trace id is an M9+ correlation concern, not 6.9.
7. **Retention enforcement code.** A 1-line addition to `docs/operations.md` documenting the 24–72h tick retention is a lightweight follow-up; the actual enforcement job (cron / archival) is its own deliverable.
8. **`app_settings` seed for the 6 new watchdog keys** (4 thresholds + cooloff + grace). Documented in 6.9a Freeze §1, but the seed migration is part of the 6.9a unblock PR, not this memo.
9. **6.9b service evolution.** `ExitFireMetricsService` (already merged) is independent of the supervisor loop. Future panels/alerts that consume it are tracked separately.

---

**References (not modified by this memo):**

- Current Supervisor source: `src/fx_ai_trading/supervisor/supervisor.py:9-13` (deferred-milestones docstring).
- Reconciler patterns: `src/fx_ai_trading/supervisor/reconciler.py`, `src/fx_ai_trading/supervisor/midrun_reconciler.py`.
- Audit row repository: `src/fx_ai_trading/repositories/reconciliation_events.py`.
- Forbidden time-source rule: `docs/development_rules.md` §13.1.
- Cycle 6.9a block status: memory file `project_cycle_6_9a_blocked.md`.
- Cycle 6.9b closure: memory file `project_cycle_6_9b_closure.md`.
