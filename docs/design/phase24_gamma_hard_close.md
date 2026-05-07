# Phase 24 / NG#10 β-Chain — γ Hard Close

Doc-only PR that formally invokes **γ hard close** as the routing
verdict for the Phase 24 path-B/path-β chain. This converts the
"recommended default" carried through PRs #276 / #277 / #278 into a
**declared closure** of the rule-based / classifier-based exit-side
research arc covered by Phases 22 / 23 / 24 + NG#10 β-chain, **under
the current data/execution assumptions**.

**This is NOT a permanent closure of FX scalping research.** γ
closure is bounded by the assumptions enumerated in §3 — it does not
foreclose future research under new data, new execution models, new
feature classes, or new envelope axes. If the user explicitly opens
a new chain (Option B / Option C / NG#11 review per §7), that chain
begins independent of this closure.

## §1. Purpose and framing

Phase 24 path β was opened (PR #274) to test whether NG#10 strict
close-only execution was the binding constraint on Phase 24's
exit-side REJECT verdicts. The β chain proceeded review (#275) →
envelope confirmation (#276) → implementation (#277) → final
addendum (#278). Empirical result: the C2 envelope (the most
realistic NG#10 relaxation among 6 audited candidates) **did not
rescue** Phase 24's REJECT — best Sharpe -0.1993, lift -0.022 vs
24.0b's -0.177, routing diagnostic H3.

PR #278 carried the recommendation "γ hard close under current
data/execution assumptions, awaiting user direction". This PR
records the user's direction: **γ is invoked.**

## §2. Scope

**In scope**:

- Formal γ hard-close declaration, bounded by current data/execution
  assumptions (§3).
- Consolidated cumulative finding from Phases 22 → 23 → 24 + NG#10
  β-chain (§4); 22 / 23 details are summary-only — the canonical
  conclusions live in their respective final synthesis docs.
- Enumeration of what is formally closed (§5).
- Production-readiness invariants (§6).
- Pointers to potential future axes (§7) — pointers only, not
  recommendations.
- Methodological lessons (§8).

**Explicitly out of scope**:

- Pursuing path α, NG#11 audit, or any new-data audit. Those are
  separate downstream PRs if/when the user explicitly requests them.
- Modifying any prior PR's verdicts. PRs #269-#278 stand as recorded.
- Modifying any existing 22.x / 23.x / 24.x docs/artifacts.
- Pre-approving any production deployment.
- Permanent closure of the FX scalping research domain.
- MEMORY.md update.

## §3. The γ declaration

Under the current data/execution assumptions —

- 730d OANDA-class M1 BA dataset, 20-pair canonical universe;
- M1 OHLC granularity (no sub-minute / tick data);
- NG#10 (close-only triggers) preserved or relaxed only within the
  rigorously-tested envelope (PR #276) — both-side touch with
  SL-first same-bar policy, TP=limit-exact, SL=stop-market with
  worst-of-bar slippage proxy at close;
- NG#11 (causal regime tags) preserved unchanged;
- Worst-of-bar slippage proxy on stop-side fills (no live-broker
  fill log);
- Phase 22 8-gate harness thresholds (Sharpe ≥ +0.082, ann_pnl ≥
  +180 pip, MaxDD ≤ 200, A4 ≥ 3/4 folds, A5 +0.5 pip stress > 0);
- Frozen entry streams = 24.0a top-3 (all 23.0d M15 first-touch
  Donchian h=4)

— the rule-based / classifier-based / regime-based / exit-rule-search
FX-scalping research arc covered by Phases 22 / 23 / 24 + NG#10
β-chain is **formally closed**. No further PR in this arc will
pursue another candidate exit rule, partial-exit policy,
regime-conditional exit policy, NG#10 relaxation envelope variant,
or trailing/breakeven variant within these assumptions.

γ closure is **bounded by current assumptions, not permanent**. If
the user explicitly opens a new axis (Option B / Option C / NG#11 —
see §7), a new chain begins independent of this closure. This γ doc
**does not pre-approve** any of those options.

## §4. Consolidated finding

The detailed findings live in each phase's final synthesis doc; this
section is a **summary-only** roll-up. Phase 22's and Phase 23's
canonical conclusions remain the authoritative records — see PR #268
(Phase 23 final synthesis) and `docs/design/phase22_main_design.md`
for the original prose.

### §4.1 Phase 22 / 22.0z (summary; canonical = `phase22_main_design.md`)

Data validation (22.0z-1), native M5 vs aggregated (22.0z-2),
7-config alternatives audit (22.0z-3 + 22.0z-3b/c/d/e), tick
prerequisite check (22.0z-4), and 22.0c breakout reference. Outcome:
B Rule baseline established at Sharpe +0.0822, ann_pnl +180/yr.
8-gate harness anchored. Phase 22 frozen-OOS gating discipline
codified.

### §4.2 Phase 23 (summary; canonical = PR #268 final synthesis)

Entry-axis search across 4 sub-stages: 23.0a outcome dataset, 23.0b
M5 Donchian breakout, 23.0c M5 z-score MR, 23.0d M15 first-touch
Donchian, 23.0c-rev1 signal-quality control. Outcome: every tested
M5 / M15 rule-based entry class **REJECT** under realised positive
EV with the 8-gate harness. Path A (different entry feature class)
remains as a parallel option but was deferred at PR #268.

### §4.3 Phase 24 path-B (summary; canonical = PR #274 final synthesis)

Inverted Phase 23: fixed the top-3 path-EV reservoirs (24.0a
H1 PASS) and searched the exit axis. Three exit-side mechanisms
tested under NG#10 strict close-only:

- 24.0b trailing-stop variants: REJECT 33/33 still_overtrading;
  best Sharpe -0.177.
- 24.0c partial-exit variants: REJECT 27/27 still_overtrading;
  best Sharpe -0.229.
- 24.0d regime-conditional variants: REJECT 27/27 still_overtrading;
  best Sharpe -0.180.

Same frozen rank1 cell (23.0d N=50 h=4 exit=tb) was best-of-stage
in all three — rules out per-stage entry-selection bias. PR #274
closed Phase 24 path-B with α/β/γ routing tree.

### §4.4 NG#10 β-chain (canonical = PR #278 final addendum)

Four-PR sequence under PR #274's β recommendation:

- **PR #275 β review**: 6 NG#10 relaxation candidates (C1-C6)
  audited. Verdict: 0 ADOPT / 3 DEFER (C1, C2, C6) / 3 REJECT (C3,
  C4, C5). C2 (both-side touch + SL-first) identified as
  most-promising.
- **PR #276 β envelope confirmation**: C2 escalated to
  `ADOPT_FOR_IMPLEMENTATION` (a label deliberately distinct from
  the strategy-evaluation `ADOPT_CANDIDATE` / `ADOPT` gates). 11-
  section binding contract: trigger semantics, fill semantics,
  SL-first invariant, negative list, required data, leakage
  demotion proof (MEDIUM → LOW), OANDA fill realism mapping,
  17-test contract, implementation-PR contract.
- **PR #277 Phase 24.1a**: C2 envelope implementation eval; 33
  cells (3 frozen × 11 trailing variants imported verbatim from
  stage24_0b). Verdict: REJECT 33/33 still_overtrading; best
  Sharpe -0.1993 vs 24.0b's -0.177; lift -0.022; routing
  diagnostic H3 (no rescue).
- **PR #278 final addendum**: empirical falsification recorded.
  Hypothesis "NG#10 close-only is the binding constraint"
  empirically falsified for the C2 envelope under current
  assumptions. C1/C6 priors downgraded; formal verdicts remain
  DEFER. C2 added to REJECT (empirical). Net: 0 ADOPT / 2 DEFER
  (downgraded priors) / 4 REJECT.

NG#10 candidate space exhausted under current data/execution
assumptions.

### §4.5 Mechanism interpretation (the load-bearing finding)

The C2 envelope INCREASED exit firing rate vs NG#10 close-only
(touched-but-reverted bars triggered exits NG#10 left running) but
fills landed at the trigger level or worse — less favorable than
NG#10's "let it run to next-bar close" outcome on average. **Net:
more exits + worse fills = small negative Sharpe lift.** This
mechanism, combined with the 87/87 unanimous `still_overtrading`
classification across 24.0b/0c/0d, indicates that the **per-trade
EV after spread cost** — not the exit-rule mechanics or the trigger
granularity — is the binding constraint under current assumptions.

## §5. What is formally closed

The following are **closed** under §3 assumptions:

1. NG#10 close-only relaxation as a route to converting 24.0a
   path-EV into realised PnL clearing the 8-gate harness.
2. Trailing-stop / partial-exit / regime-conditional exit rule
   search on 24.0a frozen entry streams under NG#10 strict
   close-only.
3. Trailing-stop search under the C2 envelope (NG#10 relaxed +
   SL-first same-bar + worst-of-bar SL slippage).
4. The 6 NG#10 relaxation candidates enumerated in PR #275 (C1-C6).
5. Path-EV vs realised-EV gap reconciliation via causal exit logic
   alone, on 23.0d's M15 first-touch Donchian REJECT cells.

## §6. Production-readiness invariants

**Phase 22 frozen-OOS gating discipline remains intact.** No 22.x /
23.x / 24.x cell graduated past `PROMISING_BUT_NEEDS_OOS` /
`ADOPT_CANDIDATE`; γ closure does not invalidate any cell, but it
also does not promote any cell. Any future cell that reaches
`ADOPT_CANDIDATE` (in any new chain opened post-γ) **still requires
an X-v2-equivalent frozen-OOS PR** before any production discussion.

γ closure does not pre-approve any production deployment. If a
future chain ever does reach ADOPT, the frozen-OOS contract is the
mandatory next step — not a live deploy.

## §7. Forward-looking pointers (pointers only, not recommendations)

The following routes remain available but are **not recommended**
by this γ doc and **not pre-approved**. They are listed solely so
the doc is self-contained.

- **Option B — new data/execution audit**. If the user explicitly
  requests, candidate audits include (per PR #278 §5.B): longer
  span (>730d); tick-level data; real broker fill logs; different
  broker / data source; or a separate NG#11 review. None of these
  is pre-decided; each would open its own chain.
- **Option C — Path α: Phase 25 entry-side return on a different
  feature class**. Realised volatility breakout, volume / order-book
  shape, cross-asset DXY/index, fundamental-calendar gate. Deferred
  at PR #274 and remains a parallel option independent of NG#10
  conclusions.
- **NG#11 separate review**. NG#11 (causal regime tags) was
  preserved unchanged through Phases 22 / 23 / 24 / β chain. A
  distinct audit chain analogous to NG#10's β PR could enumerate
  NG#11 relaxation candidates. Orthogonal to this γ closure.

The γ doc presents NO ranking or recommendation among these
options. Future direction is the user's judgment; γ does not
pre-approve any.

## §8. Methodological lessons (brief retrospective)

The following methodological practices proved load-bearing across
the 22-24 + β arc and should be retained for any future axis-shift
chain:

1. **8-gate harness worked**. Anchoring every cell-level verdict
   to the same A0-A5 thresholds (with Phase 22 inheritance) made
   cross-stage comparisons coherent. `still_overtrading` /
   `under_firing` / `path_ev_unrealisable` /
   `pnl_edge_insufficient` / `robustness_failure` reason codes
   exposed *why* cells failed, not just *that* they did.
2. **Frozen entry streams discipline worked**. Phase 24's strict
   reuse of 24.0a top-3 across 0b/0c/0d/1a ruled out per-stage
   entry-selection bias and made the empirical "best cell is the
   same in all four stages" observation possible.
3. **NG#10 / NG#11 disclosure prevented leakage**. The mandatory
   verbatim clauses in every eval_report.md kept the close-only /
   causal-tag invariants front-of-mind. The §3.4 negative-list
   pattern (PR #276) made it harder to silently relax constraints
   in implementation.
4. **Separating `ADOPT_FOR_IMPLEMENTATION` from `ADOPT_CANDIDATE` /
   `ADOPT` was effective**. The envelope-confirmation contract
   (PR #276) authorised a bounded implementation without conflating
   it with a strategy verdict. This kept the 8-gate harness as the
   sole verdict mechanism while still allowing a new fill model to
   be tested rigorously.
5. **Path-EV vs realised-EV separation was effective**. PR #270
   (24.0a H1 PASS) confirmed path-EV exists, which made the
   subsequent REJECTs interpretable as exit-side / spread-cost
   failures rather than entry-side failures. Without this
   separation, the chain would have ambiguously closed entry × exit
   together at 24.0b.

These are not closures themselves — they are practices to inherit
into any future chain.

## §9. PR chain reference (#269 → #278)

| PR | Stage | Purpose | Verdict / output |
|---|---|---|---|
| #269 | Phase 24 kickoff | Design contract; H1 / H2 hypotheses | merged |
| #270 | Phase 24.0a | Path-EV characterisation | H1 PASS; top-3 frozen (all 23.0d M15 h=4) |
| #271 | Phase 24.0b | Trailing-stop variants | REJECT 33/33 still_overtrading; best -0.177 |
| #272 | Phase 24.0c | Partial-exit variants | REJECT 27/27 still_overtrading; best -0.229 |
| #273 | Phase 24.0d | Regime-conditional variants | REJECT 27/27 still_overtrading; best -0.180 |
| #274 | Phase 24 final synthesis | Path-B closure; α/β/γ routing tree | merged; β recommended next |
| #275 | NG#10 β review | 6 candidates audited (C1-C6) | 0 ADOPT / 3 DEFER / 3 REJECT |
| #276 | NG#10 β envelope confirmation | C2 binding contract | C2 ADOPT_FOR_IMPLEMENTATION |
| #277 | Phase 24.1a | C2 envelope implementation eval | REJECT 33/33; best -0.1993; lift -0.022; H3 |
| #278 | NG#10 final addendum | Empirical falsification recorded; γ recommended | merged; γ recommended default |
| **this PR** | **γ hard close** | **Closure declaration** | **closed under current assumptions** |

(Master tips and full commit references live in each PR's individual
commit message; not duplicated here.)

## §10. What this doc does NOT do

- Does not declare permanent closure of FX scalping research.
- Does not declare any new phase open. No path α plan, no NG#11
  audit plan, no Option B audit plan in this doc.
- Does not modify PRs #269 / #270 / #271 / #272 / #273 / #274 /
  #275 / #276 / #277 / #278 — all stand as recorded.
- Does not modify Phase 22 frozen-OOS gating discipline (§6 reaffirms it).
- Does not pre-approve any production deployment.
- Does not update MEMORY.md.
- Does not relax NG#11.

## §11. Files

| Path | Status | Lines |
|---|---|---|
| `docs/design/phase24_gamma_hard_close.md` | NEW | this file |

**Single file. No `artifacts/` entry. No `tests/` entry. No
`scripts/` entry. No `src/` change. No DB schema change. No
MEMORY.md update. Existing 22.x/23.x/24.x docs/artifacts:
unchanged. NG#11: not relaxed.**

## §12. CI surface

- `python tools/lint/run_custom_checks.py` (rc=0 expected; doc-only)
- `pytest` (no test changes; existing tests untouched)

---

**Phase 24 / NG#10 β-chain — closed under current assumptions.**
