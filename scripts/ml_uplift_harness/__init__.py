"""ML uplift experiment harness — implementation-only scaffolding.

This package is Step 2 of `docs/design/ml_accuracy_uplift_experiment_contract.md`:
the safe experiment-harness scaffolding needed for future ML research, with NO
real ML experiment. It validates experiment contracts, captures provenance,
plans artifact paths, and writes clearly-marked SYNTHETIC-ONLY reports.

It NEVER reads real market data, trains or runs a model, runs a backtest /
sweep / replay, generates real features / labels, or computes any trading
metric. It performs no network / broker / quote-feed / OANDA / credential
access and spawns no subprocess. It is research scaffolding, not production
runtime code.
"""
