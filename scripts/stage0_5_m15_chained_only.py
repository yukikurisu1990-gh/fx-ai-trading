"""stage0_5_m15_chained_only.py — M15_chained_best (small_boost+H=3) only, 4 Meta variants."""
from __future__ import annotations
import sys

sys.path.insert(0, "scripts")
import stage0_5_meta_layer_eval as s05  # reuse run_base function and helpers

# Override _BASES to just M15_chained_best
s05._BASES = [
    ("M15_chained_best", 15, "1825d", 3, {0: 1.2, 1: 1.0, 2: 1.2}),
]


if __name__ == "__main__":
    s05.main()
