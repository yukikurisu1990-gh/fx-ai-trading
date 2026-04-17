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

This repository is in **Iteration 1** (MVP skeleton construction). Live OANDA
trading is not enabled; all work proceeds under `paper` mode only. See
[`docs/iteration1_implementation_plan.md`](docs/iteration1_implementation_plan.md)
for current milestones and progress.
