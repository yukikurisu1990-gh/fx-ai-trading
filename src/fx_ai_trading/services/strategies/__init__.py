"""Strategy implementations for M9 (D3 §2.4.1).

Available strategies:
  - AIStrategyStub: fixed-confidence stub (placeholder for real AI model).
  - MAStrategy: moving-average crossover (SMA20 vs SMA50).
  - ATRStrategy: ATR-based directional signal.

Each class implements the StrategyEvaluator Protocol.
"""
