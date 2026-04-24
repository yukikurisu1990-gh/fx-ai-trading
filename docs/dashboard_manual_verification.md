# Dashboard Manual Verification (M19-C / M26)

## Launch

```bash
DATABASE_URL=sqlite:///./dev.db streamlit run src/fx_ai_trading/dashboard/app.py
```

Open `http://localhost:8501` in a browser. The sidebar shows three pages:

- `app` — 10-panel home (M19-C)
- `Operator Console` — ctl 4-command wrapper (M26 P1)
- `Configuration Console` — Runtime / Bootstrap tabs (M26 P2 / P3)

## Panel Checklist (10 panels)

### Row 1 — 3 columns

| Panel | Expected (no DB) | Expected (with DB) |
|---|---|---|
| Market State | phase_mode/environment shown as "—" | shows phase6 / demo |
| Strategy Summary | "No orders" info | order count per status |
| Meta Decision | static placeholder text | static placeholder text (Iteration 2) |

### Row 2 — 2 columns

| Panel | Expected (no DB) | Expected (with DB) |
|---|---|---|
| Positions | "No open positions" info | table with open positions |
| Daily Metrics | zeros for all counts | today's filled/canceled/failed counts |

### Row 3 — 2 columns

| Panel | Expected (no DB) | Expected (with DB) |
|---|---|---|
| Supervisor Status | "No supervisor events" info | recent event list |
| Recent Signals | "No recent orders" info | last 20 orders |

### Row 4 — 3 columns (M19)

| Panel | Expected (no DB) | Expected (with DB, pre-M20) | Expected (with DB, post-M20) |
|---|---|---|---|
| Top Candidates | "No candidates available. (TSS mart populated after M20.)" | same (table absent) | ranked candidates table |
| Execution Quality | "No execution metrics recorded yet." | fill/slippage/latency table | fill/slippage/latency table |
| Risk State Detail | "No risk events recorded yet." | risk decisions table | risk decisions table |

## Verification Steps

1. Start without `DATABASE_URL` → all panels show graceful fallback messages (no exceptions, no red error boxes).
2. Start with `DATABASE_URL` pointing to a seeded dev DB → Row 1–3 panels show table data, Row 4 panels show data if tables exist.
3. Confirm no "Error" or Python traceback appears in the browser.
4. Confirm page title is "FX-AI Trading Dashboard" and caption shows "Iteration 2 · M19".
5. Confirm layout: 3 columns / divider / 2 columns / divider / 2 columns / divider / 3 columns.

## Notes

- `top_candidates` panel shows fallback until M20 migration creates `dashboard_top_candidates` mart.
- All panels use `@st.cache_data(ttl=5)` — data refreshes automatically every 5 seconds.

---

## M26 P1 — Operator Console walkthrough

Verifies that the Streamlit page wraps `ctl` 4 commands as a thin subprocess shell, and that `emergency-flat-all` is intentionally absent (CLI-only, operations.md §15.1 / phase6_hardening.md §6.18).

### Pre-conditions

- DB reachable via `DATABASE_URL` (any of the supported backends).
- `logs/supervisor.pid` is **absent** (Supervisor stopped).
- `scripts/ctl.py` is executable from the repo root with the active Python.

### Steps

1. Open `Operator Console` from the sidebar. The status banner shows **`Supervisor: STOPPED (no PID file)`**.
2. Confirm button enable/disable matches the PID-absent state:
   - `Run start` → enabled
   - `Run stop` → disabled
   - `Run reconciler` → enabled
   - `Run resume-from-safe-stop` → disabled (and stays disabled until a non-empty Reason is typed)
3. Click **Run start**. Wait for the spinner to clear. Expect:
   - Banner flips to **`Supervisor: RUNNING (PID=N)`** on the next rerun.
   - "Last invocation" panel shows `start exited 0` (or the actual returncode) with stdout/stderr tails.
   - `logs/supervisor.pid` exists on disk.
4. With Supervisor running, click **Run start** again — expect the page to refuse the click within the 1.5 s debounce window (warning: "Ignored rapid re-click on `start`"); after the window, the disabled state of `Run start` (`PID present`) prevents re-launch.
5. Trigger a SafeStop in another terminal (e.g. inject an exit-fire incident) so the Supervisor enters the safe-stop journal state. Then click **Run stop** in the UI — confirm the process exits within the default 30 s timeout.
6. Type a non-empty Reason (e.g. `manual P1 verification`) into the **resume-from-safe-stop** field, then click **Run resume-from-safe-stop**. Expect the subprocess to clear the safe-stop journal (returncode 0) and Supervisor to resume.
7. Verify the **`emergency-flat-all is CLI-only`** warning panel is visible at the bottom of the page and shows the exact CLI invocation string (`python scripts/ctl.py emergency-flat-all`). There must be **no button, link, or form** for this command anywhere on the page.

### Acceptance

- All 4 commands fire from the page; results render with returncode + stdout/stderr tails.
- Button enable/disable tracks PID-file presence (`start` only when stopped, `stop` only when running, `resume` only when both PID present **and** Reason non-empty).
- `emergency-flat-all` is absent from the UI; the operator-facing CLI hint is present.
- A timeout (default 30 s, env-overridable) is reported via `st.error` instead of hanging the UI.

---

## M26 P2 — Configuration Console / Runtime walkthrough

Verifies that runtime-mode `app_settings` changes are enqueued via `app_settings_changes` (never UPDATEd directly), that `expected_account_type` is read-only, and that secret-like keys are filtered out of the editable set (operations.md §15.2 / development_rules.md §10.3.1).

### Pre-conditions

- DB reachable, `app_settings` seeded with at least one editable row plus `expected_account_type` (Cycle 16 seed PR #8 is sufficient).
- Supervisor state does not matter for this walkthrough; the page operates on the queue table only.

### Steps

1. Open `Configuration Console` → **Runtime mode** tab.
2. Confirm the **Current values** dataframe lists every `app_settings` row with `name / value / type / description / updated_at`.
3. Open the **Key** dropdown — confirm:
   - `expected_account_type` is **not present** in the dropdown (read-only via UI; operations.md §11 L145).
   - No secret-like keys (`*_API_KEY`, `*_SECRET`, `*_PASSWORD`, `*_TOKEN`, `*_PRIVATE`, `*_CREDENTIAL`) appear.
4. Pick an editable key, leave **New value** blank — confirm the submit button label `キューに登録 (再起動で反映)` is **disabled**.
5. Type a New value, leave **Reason** blank — confirm the button is **still disabled**.
6. Fill both fields, click submit. Expect the success banner: `キューに登録しました。次の再起動 / hot-reload で反映されます。 (rows=1)`.
7. Verify in the DB that the row landed in `app_settings_changes` with all 6 columns populated and that `app_settings` itself is **unchanged**:

   ```sql
   SELECT name, old_value, new_value, changed_by, changed_at, reason
     FROM app_settings_changes
     ORDER BY changed_at DESC LIMIT 1;
   SELECT value FROM app_settings WHERE name = '<the key you edited>';
   ```

   `app_settings.value` must still be the *old* value until a Supervisor restart / hot-reload picks up the queue.
8. Restart the Supervisor (Operator Console **Run stop** → **Run start**, or `python scripts/ctl.py` from a terminal). After restart, re-load the Runtime tab — the new value is reflected in the **Current values** table.

### Acceptance

- Read-only and secret-like keys are absent from the editable dropdown.
- Submit produces exactly one `app_settings_changes` row with all 6 columns populated.
- `app_settings` body is **not** updated by the UI; the change becomes visible only after restart / hot-reload.
- Success copy unambiguously communicates the deferred-apply semantics ("キューに登録 (再起動で反映)").

---

## M26 P3 — Configuration Console / Bootstrap walkthrough

Verifies the `.env` sink is gated by Supervisor state, that the diff preview shows hash prefixes only, and that plaintext secrets never reach DB / log / `st.session_state` (operations.md §15.4 / development_rules.md §10.3.1).

### Pre-conditions

- A writeable `.env` at the repo root (or a tmp copy if testing destructively).
- Local `logs/supervisor.pid` is **absent** initially. Have a way to start Supervisor from another terminal for the race-test step.

### Steps

1. Open `Configuration Console` → **Bootstrap mode** tab. With Supervisor stopped, the form is rendered (text area + Reason field + submit button).
2. Confirm **Current `.env` keys** lists each existing key with an `old_hash` (8-character sha256 prefix) — never the plaintext value.
3. Submit an empty body — expect the warning `新しい .env 本文が空です。書込は実行しませんでした。` and **no** file change.
4. Paste a valid body (e.g. add one new `KEY=VALUE`, modify one existing value), leave Reason blank — expect the warning `Reason が空です。書込は実行しませんでした。` and **no** file change.
5. Paste a body, fill Reason, submit. Expect:
   - **Diff** panel renders three columns (`Added` / `Removed` / `Changed`) with `name + new_hash` / `old_hash` / `old_hash + new_hash` rows. **No plaintext appears.**
   - Success banner: `.env updated. 再起動後に新しい値が反映されます。`
   - On disk, the `.env` file has the new content; the previous `.env` is replaced atomically via `os.replace()` (not a partial overwrite).
6. Inspect `app_settings_changes` for the audit rows — each affected key has a row with `name='.env:<KEY>'` and `old_value` / `new_value` set to **hash prefixes only** (or `-` for removals). **No plaintext value appears in the table.**
7. Re-submit an unchanged body — expect `差分がありません。書込は実行しませんでした。` and no `.env` change.
8. **Race test**: restart the Supervisor from a separate terminal (`python scripts/ctl.py start`) so `logs/supervisor.pid` exists, then refresh the Bootstrap tab. The form is replaced by the warning `App is running — stop the Supervisor before editing .env.` and **no** input fields are rendered.
9. Restart any process consuming `.env` (Supervisor, dashboard) so the new values take effect.

### Audit / safety check (out-of-band)

- Tail the Streamlit / app logs while performing step 5 and `grep` for the plaintext value you typed — it must **not** appear.
- Inspect `st.session_state` via the in-app debug or by re-running the page after submit — the form is wrapped in `st.form(clear_on_submit=True)`, so the text-area / Reason fields reset to empty on the rerun (no plaintext retained).
- Confirm the temporary file produced by `atomic_write_env` lives in the same directory as `.env` (same filesystem) — required for `os.replace()` atomicity on Windows.

### Acceptance

- Form is hidden whenever `logs/supervisor.pid` exists; visible only when stopped.
- Diff and audit rows expose hash prefixes only (`hash_prefix` = first 8 hex chars of sha256).
- `.env` write follows the tmp-file → `os.replace()` atomic path; partial writes are not observed under failure injection.
- Plaintext values are absent from logs, `app_settings_changes`, and `st.session_state` after submit.
