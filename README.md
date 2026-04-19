# fx-ai-trading

FX prediction and short-term trading system (MVP: paper mode only).

All design contracts, implementation plans, harness rules, and operations runbooks
live in [`docs/`](docs/). A good entry point is
[`docs/iteration1_implementation_plan.md`](docs/iteration1_implementation_plan.md).

---

## Requirements

- **Python 3.12** is required. The project declares
  `requires-python = ">=3.12,<3.13"` in `pyproject.toml`, so pip will **reject**
  any editable install attempted from a different Python version (including 3.11,
  3.13, and 3.14). If `py -3.12 --version` does not print `Python 3.12.x`, install
  Python 3.12 first (see "Installing Python 3.12" below).
- **Windows 10 / 11** is the primary development target. PowerShell is the primary
  shell. Git Bash / WSL / Linux / macOS are also supported (commands differ only
  in the activation path; see the "bash alternative" blocks below).
- **Git**.
- An existing `.venv/` created with a non-3.12 Python **must be deleted and
  recreated** — see "Troubleshooting".

### Installing Python 3.12

If Python 3.12 is not yet installed:

```powershell
winget install Python.Python.3.12
```

Verify:

```powershell
py -3.12 --version   # should print: Python 3.12.x
py -0                # lists all installed Python versions
```

---

## Initial Setup

All commands assume **Windows PowerShell** started at the project root
(`<your-path-to>\fx-ai-trading`).

```powershell
# 1. Move to the project root (adjust path as needed).
cd <your-path-to>\fx-ai-trading

# 2. Create a virtual environment using Python 3.12.
py -3.12 -m venv .venv

# 3. Activate the virtual environment.
.venv\Scripts\Activate.ps1

# 4. Install the project in editable mode with dev extras.
pip install -e ".[dev]"
```

After step 4 you should see a line similar to:

```
Successfully installed ... fx-ai-trading-0.0.1 ... pytest-8.x.x ruff-0.x.x ...
```

### bash alternative (Git Bash / WSL / Linux / macOS)

```bash
# Windows (Git Bash): use `py -3.12`
py -3.12 -m venv .venv
source .venv/Scripts/activate

# Linux / macOS: use `python3.12` and bin/
# python3.12 -m venv .venv
# source .venv/bin/activate

pip install -e ".[dev]"
```

---

## Verification

After setup, verify every version matches the `pyproject.toml` contract
(all commands must exit `0`):

```powershell
python --version
# expected: Python 3.12.x

ruff --version
# expected: ruff 0.x.x, within >=0.6,<1.0

pytest --version
# expected: pytest 8.x.x, within >=8.0,<9.0

python -c "import fx_ai_trading; print(fx_ai_trading.__version__)"
# expected: 0.0.1

ruff check .
# expected: All checks passed!
```

If any of the version outputs are outside the declared ranges, see
"Troubleshooting".

---

## Running the System (Demo Mode)

Iteration 2 runs demo-only against an OANDA practice account. Live trading is
disabled by the 4-defense gate (see [`docs/phase6_hardening.md`](docs/phase6_hardening.md)
§6.18) and is scheduled for Phase 7. The steps below take a fresh checkout to
a running Supervisor on `demo`.

### 1. Start PostgreSQL

The application requires a reachable PostgreSQL instance for `DATABASE_URL`.
Use any local install (Docker, native, etc.); SQLite is supported only for the
Dashboard fallback path, not for `ctl start`.

### 2. Configure `.env`

```powershell
Copy-Item .env.example .env
```

bash alternative:

```bash
cp .env.example .env
```

Edit `.env` and fill in at minimum:

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | yes | PostgreSQL DSN |
| `OANDA_ACCESS_TOKEN` | yes | OANDA practice (demo) token |
| `OANDA_ACCOUNT_TYPE` | yes | Set to `demo` for Iteration 2 |
| `SLACK_WEBHOOK_URL` | no | Enables Slack notifier path |
| `SMTP_*` | no | Enables Email notifier path (all six required together) |

`.env` is gitignored — never commit secrets. See [`docs/development_rules.md`](docs/development_rules.md) §10.3 for the secret-handling rules.

### 3. Apply database migrations

```powershell
alembic upgrade head
```

This creates / brings up to date the 43 physical tables and seeds
`app_settings` with Phase 6.5 defaults (`expected_account_type=demo` and
related runtime settings).

### 4. Start the Supervisor

```powershell
python scripts/ctl.py start
```

Leave the `--confirm-live-trading` flag off for demo runs. The flag is
required only when `OANDA_ACCOUNT_TYPE=live` and is one layer of the 4-defense.

### 5. Confirm startup succeeded

After `ctl start`, verify:

- `logs/supervisor.pid` exists and contains the running PID.
- `logs/notifications.jsonl` is being written (no `account_type.mismatch` line).
- The 16-step boot sequence (see [`docs/operations.md`](docs/operations.md) §2.1)
  reached "Step 16: Normal Operation"; check the `supervisor_events` table for
  the latest `event_type` row.

### 6. When you get stuck

- Operator quickstart (navigation cheat sheet): [`docs/operator_quickstart.md`](docs/operator_quickstart.md)
- Boot sequence and per-step failure handling: [`docs/operations.md`](docs/operations.md) §2.1
- demo ↔ live switching runbook: [`docs/operations.md`](docs/operations.md) §2.1 Step 9
- Failure recovery (F1–F15 runbooks): [`docs/operations.md`](docs/operations.md) §4
- Account-type 4-defense: [`docs/phase6_hardening.md`](docs/phase6_hardening.md) §6.18

### Stopping

```powershell
python scripts/ctl.py stop
```

`ctl stop` performs a graceful shutdown (SIGTERM, then SIGKILL on timeout).

---

## Pre-commit Setup

Pre-commit hooks run `ruff check --fix`, `ruff format`, `pytest`, and the
custom forbidden-pattern lint (`tools/lint/run_custom_checks.py`) before every
commit. This mirrors the quality gate described in
[`docs/development_rules.md`](docs/development_rules.md) 2. and
[`docs/automation_harness.md`](docs/automation_harness.md) 4.1.

Install once per clone (with the project `.venv` already activated):

```powershell
pip install pre-commit
pre-commit install
```

Manual run on the entire repository (useful after cloning or before pushing):

```powershell
pre-commit run --all-files
```

See [`.pre-commit-config.yaml`](.pre-commit-config.yaml) for the full hook list.

---

## Continuous Integration

Every push to `main` and every pull request triggers a GitHub Actions workflow
that runs `ruff check`, `ruff format --check`, `pytest`, and the custom
forbidden-pattern lint on Ubuntu with Python 3.12. This is the remote half of
the two-layer quality gate; the local half is the pre-commit hook above.

See [`.github/workflows/ci.yml`](.github/workflows/ci.yml) for the full job
definition.

---

## Dependency Lock

The repository pins exact versions of every direct and transitive dependency
through [`uv.lock`](uv.lock). This guarantees that every developer, CI run,
and future deployment resolves to the same set of packages.

### Installing uv (one-time, user-level)

`uv` is a development tool, not a project dependency. Install it once on your
machine (outside the project `.venv`):

```powershell
# PowerShell
pip install --user uv
# or: winget install astral-sh.uv
```

### Syncing a fresh environment from the lockfile (recommended)

```powershell
uv sync --all-extras --frozen
```

This creates / updates `.venv` with exactly the versions recorded in
`uv.lock`. No resolution happens at sync time; mismatches cause an error.

### Legacy path (pip-only, still supported)

```powershell
pip install -e ".[dev]"
```

This resolves against `pyproject.toml` version ranges (e.g. `ruff>=0.6,<1.0`)
and may pick newer patch versions than `uv.lock`. Use this only when `uv` is
unavailable; prefer `uv sync` for reproducibility.

### When to update the lockfile

Run `uv lock` **only when** `pyproject.toml` dependencies change:

```powershell
uv lock
git add uv.lock pyproject.toml
```

Commit `uv.lock` together with the `pyproject.toml` change in the **same PR**.
Never edit `uv.lock` by hand.

### Adding a new dependency (M2 and later)

Prefer:

```powershell
uv add sqlalchemy            # runtime dep
uv add --dev some-linter     # dev dep
```

`uv add` edits `pyproject.toml` **and** updates `uv.lock` atomically.
Manual `pyproject.toml` edits are allowed but must be followed by `uv lock`
before commit.

---

## Troubleshooting

### `.venv` was created with the wrong Python version

Symptom: `python --version` inside the activated `.venv` reports anything other
than `Python 3.12.x`, or `pip install -e ".[dev]"` fails with
`Package 'fx-ai-trading' requires a different Python`.

Fix: delete and recreate `.venv` with Python 3.12.

PowerShell:

```powershell
Remove-Item -Recurse -Force .venv
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

bash (Git Bash / Linux / macOS):

```bash
rm -rf .venv
py -3.12 -m venv .venv            # or python3.12 on Linux / macOS
source .venv/Scripts/activate     # or .venv/bin/activate on Linux / macOS
pip install -e ".[dev]"
```

### `pip install -e ".[dev]"` fails with `requires a different Python`

This means pip is attached to a Python outside `[3.12, 3.13)`. Recreate the
`.venv` as shown above, taking care to use `py -3.12` explicitly.

### `pytest --collect-only` exits with code 5

This is **expected at the current iteration** (Iteration 1, early M1). `exit 5`
means pytest collected no test cases because the test suite has not yet been
written. This is a known Minor finding tracked against the first test-addition
cycle. It is not a failure.

### `py -3.12` is not found

Python 3.12 is not installed. Run `winget install Python.Python.3.12` (Windows)
or install via your OS package manager (Linux / macOS). Then retry setup.

---

## Project Status

**Iteration 2 is Full Complete** (see
[`docs/iteration2_completion.md`](docs/iteration2_completion.md)). Live OANDA
trading remains disabled in Iteration 2 — only `demo` mode is supported and
the 4-defense gate (see [`docs/phase6_hardening.md`](docs/phase6_hardening.md)
§6.18) blocks any unintended live activation. Live trading is scheduled for
Phase 7. See [`docs/iteration2_implementation_plan.md`](docs/iteration2_implementation_plan.md)
for milestone details (M13–M26) and [`docs/phase7_roadmap.md`](docs/phase7_roadmap.md)
for the next phase.
