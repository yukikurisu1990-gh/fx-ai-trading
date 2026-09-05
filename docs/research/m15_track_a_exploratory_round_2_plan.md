# M15 Track A — Exploratory Strategy Research, Round 2: the pre-registered plan

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

**This file is written and committed before the Round 2 experiments are run.**
Its point is that the multiplicity correction at the end has a *fixed* family to
correct over. A family assembled after seeing the results is not a family, and
Round 1's own lesson was that a 1,078-fit search left uncorrected produces a
number nobody can interpret.

Base master: `8617f7a1aab054d8f01d3aae63a411bf0a467dda` (the PR #464 merge).
Span: `2025-04-25 … 2025-12-28` × `PAIRS_20` × M15. Corpus:
`EXPLORATORY_SEEN_DATA`. The historical `EXPLORATORY_OOS_SLICE`
(`2025-12-29` onward) is **not read** — the loader refuses it.

---

## 1. The question, and what a good answer looks like

Round 1 left exactly one thing standing: a **multi-day reversal** at a 4-to-6 day
lookback and hold. It passed a chronological walk-forward, 54/54 parameter
perturbations and 20/20 leave-one-pair-out, kept 74–84% of net at triple cost —
and did **not** clear a family-wise correction (`p = 0.304`), on a sample with
about 70 independent observations per pair and 6.5 effective independent pairs.

Round 2 answers three questions and nothing else.

* **Q1** — is the multi-day reversal *stable across time*, or is it the same
  first-half artefact the 24-hour version turned out to be?
* **Q2** — is there a regime where it lives that is economically nameable, found
  without a new search?
* **Q3** — **can this corpus decide the question at all**, or is the honest
  answer "insufficient power"?

Q3 is the one that matters most, and it is the one that cannot be improved by
looking harder at the data.

**A good answer is a classification, not a strategy.** The round ends in exactly
one of `MULTI_DAY_REVERSAL_EXPLORATORY_SIGNAL_WORTH_PURSUING`,
`MULTI_DAY_REVERSAL_UNRESOLVED_INSUFFICIENT_DETECTION_POWER` or
`MULTI_DAY_REVERSAL_LIKELY_EXPLORATORY_ARTIFACT`. **A is not the target.**

## 2. The bounded primary family — fixed here, before anything runs

The strategy is Round 1's `reversal_hold`, unchanged: fade the move over
`lookback` bars, decide on a grid every `hold` bars, hold to the next grid point,
enter only when the move's z-score against its own trailing distribution exceeds
`entry_z`.

| axis | values | why exactly these |
| --- | --- | --- |
| `lookback` | 384, 480, 576 | the 4-, 5- and 6-day neighbourhood Round 1 identified. Round 1 showed 288 is on the weak side of the cliff and 768 is where non-overlapping windows fall below 30 per pair |
| `hold` | 384, 480, 576 | matched to the lookback range; Round 1 found `hold ≈ lookback` is where the turnover arithmetic works |
| `entry_z` | 0.0, 1.0, 1.5 | 0.0 = take every grid point, 1.0 and 1.5 = the two selectivity levels Round 1 already used. No optimisation over this axis |

**3 × 3 × 3 = 27 configurations.** Under the 100 the instruction allows, and
deliberately so: the neighbourhood is what is being characterised, not searched.

Every configuration is evaluated **phase-averaged over 8 rebalance offsets**.
Round 1 established that a single phase is one draw from a distribution spanning
−171 to +713 pips/pair, and that the accidental hour-locking of `grid[::hold]`
made single-phase numbers a nuisance-parameter lottery. Phase is averaged, never
selected. The 8 phases are not 8 experiments.

**The primary family for multiplicity correction is these 27 and nothing else.**

## 3. The secondary family — also fixed here

One conditioning axis, because Round 1 produced a specific, testable claim about
it: the ATR-high filter improved *breadth* (6.5 → 12.6 effective independent
pairs) while lowering net.

| axis | values |
| --- | --- |
| ATR bucket | low / middle / high tercile, plus unconditioned |
| applied to | the three `entry_z` levels at `lookback = hold = 480`, the centre of the neighbourhood |

**4 × 3 = 12 configurations**, corrected as their own family. The ATR threshold
is a tercile of the pair's own trailing ATR distribution and is **not tuned**.

Total pre-registered: **39 configurations**. Anything else this round produces is
labelled `POST_HOC_EXPLORATORY` and may not be promoted into the main result.

## 4. What will be measured, per configuration

Net / gross / cost pips per pair, Sharpe-like, max drawdown, closed trades,
win rate, profit factor, average trade pips, turnover per year, exposure,
per-pair net, per-pair IC, pair concentration, session concentration, cost
sensitivity at ×1.25 / ×1.50 / ×2.0 / ×3.0.

## 5. Temporal stability — the Q1 analysis

The development span is cut into **8 chronological blocks of about 31 days**, and
for each block: the signal IC, gross, net, trades and the number of pairs with a
positive contribution. The question is which of these explains the Round 1 decay
from −14.6% to −1.9%:

* **monotonic decay** — the block series trends down;
* **regime shift** — a level change with a stable level either side;
* **sample noise** — block-to-block variation consistent with the null;
* **pair composition** — a changing subset of pairs carries it;
* **volatility** — block IC tracks block ATR;
* **cost** — block net tracks block spread while gross is flat.

These are distinguishable and will be reported as which one the data supports,
not as a list.

## 6. Regime — the Q2 analysis, in the priority the instruction sets

* **A. Volatility.** ATR terciles, as §3. First because Round 1 found a breadth
  effect there.
* **B. Trend vs range.** Does the reversal happen inside a strong multi-day trend
  or inside a range? One coarse split on the same trailing window as the
  lookback. Not an ADX rebuild — Round 1 showed ADX separates nothing.
* **C. Pair characteristics.** Thin/thick, JPY/non-JPY, per-pair IC — is the
  signal thin-and-everywhere or thick-and-somewhere?
* **D. Time as a regime** — §5.

**No regime combinations beyond A × the entry_z axis.** Generating a regime cross
product is how Round 1's roles produced results nobody could correct.

## 7. Why the ATR-high breadth improved — the §8 analysis

Not "is the filtered version better", which Round 1 already answered (it is not,
on net). The question is *mechanism*, and the candidate explanations are
measurable and mutually distinguishable:

trade frequency, pair concentration of PnL, dispersion of per-pair IC, cost per
trade, exposure duration, and whether it removes tail trades. Each is computed
for filtered and unfiltered at the same centre configuration. The ATR threshold
is **not** optimised.

## 8. Detection power — the Q3 analysis, and the round's main deliverable

With ~70 independent observations per pair and ~6.5 effective independent pairs,
the prior question is whether "no edge" and "a small edge" are separable at all.

* **Null distribution** — block sign-flip on pooled daily net, as Round 1, plus a
  block bootstrap of the per-pair series.
* **Observed effect and its confidence interval** — bootstrap CI on net pips per
  pair and on the pooled IC.
* **Minimum detectable effect** — the smallest true per-trade edge this sample
  would reject the null for, at 80% power and α = 0.05.
* **Power at the observed effect size** — if the observed effect were the truth,
  how often would this sample detect it?
* **Additional data** — how much more span, at the observed effect size and
  variance, would be needed to reach 80% power.

**This section is not permitted to search for a smaller p-value.** Its output is
a statement about the corpus, and "this corpus cannot decide" is a legitimate and
likely result.

## 9. Multiplicity

Family-wise block sign-flip permutation, one shared sign draw across every
variant so the null keeps the between-variant correlation, over:

* the **27** primary configurations, as one family;
* the **12** secondary configurations, as a second family.

Reported separately. No pooling of the two to make either look better, and no
post-hoc variant enters either.

## 10. What Round 2 will not do

No new strategy family — no trend, breakout, short-horizon reversion, broad
cross-pair search, session search or indicator sweep. **No ML.** No historical
OOS read, no forward epoch, no Formal Confirmation, no broker, no production
claim, no new governance gate and no new surface inventory. Round 1's families
are not re-run.

## 11. Integrity, carried forward from Round 1

Causal features only; the engine's one-bar shift stands; costs on every result;
per-pair and pooled; trade counts always shown; the same
`EXPLORATORY_ASSUMPTION` cost model — per-side `(observed spread + 0.5) / 2` on
mid-based returns. R1's `cost_table` is not a decision-bearing input, and neither
is the eligible-bar rate derived from it.

**A result below ~200 pooled closed trades is not evidence and will be said not
to be**, however good it looks.
