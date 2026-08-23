# M15 Minimum Research Gate — decision packet

**Type.** Gate-decision PR (policy §14.2). **Risk tier.** Amber — doc-only, and
it defines a research boundary.

**Completion state.**
`M15_MINIMUM_RESEARCH_GATE_PENDING_HUMAN_CHATGPT_RULING`

**Statuses carried, unchanged.**
`M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES` ·
`M15_GATE3A_CONTINUATION_OUTPUT_SURFACE_CORE_RULED_PRODUCTION_DEPENDENCIES_DEFERRED`
(PR #450) · `M15_GATE3A_CONTRACT_AND_PROOF_DESIGN_DECISION_RULED` (PR #444) ·
`M15_GATE3A_D5_8_AND_SECTION12_25_CONTRACT_RULED` (PR #448) ·
`PRODUCTION_READINESS_NOT_CLAIMED` · `NO_EXECUTION_PERFORMED` ·
`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS` ·
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`.

**Forbidden-label note.** This document asserts none of `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `PRODUCTION_READY`, `READY_FOR_LIVE`, `M15_AUTHORISED`,
`H1_AUTHORISED`, `H2_STARTED`, `PHASE_C2_STARTED`, `NEW_EPOCH_ADOPTED`,
`BYTE_ADMISSIBLE`, `MEETS`, `ROBUST`, `DEPLOYABLE`; every occurrence of such a
label in this document sits inside this list or inside a prohibition sentence.

**Nothing here is executed.** No source, test or artifact is changed; no data is
read; no dataset is downloaded; no model is trained; no evaluation is run.

---

## 1. Why this gate exists

The programme's objective is to find out whether **M15 carries a
cost-inclusive, out-of-sample tradeable edge**. Completing production-grade
evidence infrastructure is a means, not the objective.

Four audit rounds have improved the evidence machinery substantially and have
also shown how much remains: PR #450 closed with **seven production dependencies
deferred** (§10 there), including reader-freedom scope, candidate payload schema
admission and status semantics. Requiring all of them before the first research
question is asked is disproportionate to the objective.

This gate therefore separates two things the programme has so far treated as one:

| | Production-grade evidence gate | **Minimum Research Gate** |
| --- | --- | --- |
| Question | may this output become authoritative evidence? | does M15 carry an edge worth pursuing? |
| Output | committed evidence | `RESEARCH_SCRATCH_NON_AUTHORITATIVE` |
| Blocked by | PR #450 §10's seven dependencies | the boundaries in §3, and nothing else |

**This gate is `READ_ONLY_RESEARCH_EXPLORATION_GATE`.** It is not a production
readiness gate, not a live-trading gate, not an evidence-promotion gate, and not
a substitute for the formal Gate-3a continuation.

---

## 2. What committed authority already supplies — and it is more than expected

**The exploratory role already exists in the frozen pre-registration.**
`docs/design/m15_first_cost_hurdle_aware_preregistration_design.md` §3.1 defines:

> | **Design (exploratory)** | 2025-04-25 → **2026-02-28** | M15 aggregate of the
> adopted `365d_BA` epoch's pre-holdout span (R-2a) | usable only after the §4
> derivation artifact exists; **results never citable as evidence** |

So the *role*, its *span*, and its *non-citability* are committed. This gate
invents none of them.

**The acceptance thresholds are frozen and are not this gate's to set.** §9 of the
same document, "FROZEN; design audit may only tighten":

| Criterion | Frozen threshold |
| --- | --- |
| net expectancy (empirical cost) | > 0 |
| gross expectancy vs cost | ≥ 1.5 × all-in cost |
| stressed-cost survival | net ≥ 0 at 2× cost **and** at p90 session spread |
| daily portfolio Sharpe (ann., UTC-day) | ≥ 0.8 |
| max equity drawdown (vs fixed notional) | ≤ 0.15 |
| trade count | ≥ 1,000 holdout trades **and** effective-N ≥ 400 |
| daily coverage | ≥ 0.60 |
| turnover | ≤ 40 trades/day portfolio-wide |
| pair trade concentration | ≤ 0.40 |
| pair positive-PnL concentration | ≤ 0.50 |

Plus the **validation kill gate**: net expectancy > 0 **and** gross ≥ 1.5 × cost
at ≥ 1 registered `ev_min` point, within the turnover budget; all-fail closes the
family with no holdout consumed. `N_EFF_HOLDOUT_FLOOR = 400` and
`RAW_HOLDOUT_TRADE_FLOOR = 1000` are in source at
`scripts/m15_gate3a/effective_n.py`.

**`Ruling 10` forbids loosening these.** This gate does not restate them as its
own criteria, does not soften them, and does not apply them to exploratory
results — see §6.

**The cost model is committed too**: `all_in_cost = median_spread(pair, session)
+ pad_exec + cell_slippage`, with `cell_slippage = 0.5 pip` primary (§5 of the
prereg). **A zero-cost result is not admissible as a primary finding anywhere in
this programme.**

**Other frozen frame:** `PAIRS_20`; M15; horizon frozen at **24 bars** (Ruling 6);
purge/embargo **≥ 25 M15 bars** at every role boundary; the dead window
2026-03-01 → 2026-04-24 excluded from every role.

**The M1 precedent is the reason to be sceptical, and it is committed.** The
365d_BA M1 flagship returned a valid `DOES_NOT_MEET`: expectancy **−3.49
pips/trade** at 0.5 cell, gross −2.99, **20 of 20 pairs negative**. M15 was chosen
over M1 because M1's spread/ATR ratio made a short-horizon edge structurally
implausible. **The prior is that there is no edge**, and this gate exists to test
that cheaply rather than to confirm it expensively.

---

## 3. Mandatory safety boundaries

These bind every stage. They are not negotiable by a Work PR.

### 3.1 Broker

**Forbidden:** live order · demo order · any broker write · position
modification · account action. **The research phase requires no broker connection
at all**, and none may be opened. Price data comes from an approved local
read-only source.

### 3.2 Database

**Preferred path: no database.** No DB write, no schema mutation, no
`INSERT`/`UPDATE`/`DELETE`, no migration, and no external DB dependency for
research execution.

If read-only DB access is genuinely required it needs **explicit separate human
authorisation**, a read-only transaction, and no credential display. This is a
live risk in this repository, not a hypothetical: an unscoped `pytest tests/`
once wrote to a live database because `.env` loaded at import, and PR #446
established that **presence of a credential is not authorisation to use it** —
route-independent enforcement (a `sys.addaudithook` on `open`) is what actually
holds, not patching a named loader.

### 3.3 Network

During research execution: **no arbitrary network, no DNS, no storage upload, no
external telemetry, no webhook, no Slack or email.** Any dataset must be prepared
locally and read-only beforehand.

### 3.4 Credentials

A normal research run does **not** read `.env`, needs no broker or database
credential, and displays no secret.

---

## 4. Minimum research-integrity requirements

Each is here because **its absence would materially mislead the conclusion**, not
because production wants it. §5 states that test explicitly.

**R-1 Frozen research question, registered before results are seen.** Target
pairs · timeframe M15 · label definition · prediction horizon · evaluation
periods · transaction-cost model · primary metrics · stop criteria. Registering
after seeing results is the failure this repository has already recorded once, in
the ML Step 4 corrected-run precedent.

**R-2 Train / validation / holdout separation.** Temporal split; no future
leakage; the holdout isolated until last; **no feature, threshold or model change
after looking at holdout**. The frozen purge/embargo of ≥ 25 M15 bars applies at
every boundary.

**R-3 M15 aggregation correctness**, on synthetic and reference cases: timestamp
ordering · bucket boundary · OHLC aggregation · duplicate handling ·
missing/rejected observation handling · timezone and epoch binding. **Full
production calendar-provenance machinery is not required here** — but an obvious
coverage defect is not ignored, and the six-field minute accounting (PR #444 §5)
is the vocabulary for reporting what is missing.

**R-4 Leakage controls.** Forbidden: future bars · target leakage · centred
rolling windows · post-event values · forward-filled future information ·
cross-split contamination. This repository's own history is the argument:
**every positive Phase-9 result was invalidated** by weekend-gap, partial-bin and
`min_periods` leakage, and the clean baseline came back at Sharpe −0.189.

**R-5 Cost realism.** Spread, slippage and fees where applicable, using the
committed cost model. **A zero-cost result is never a primary finding.**

**R-6 Reproducibility.** Code commit SHA · dataset identity · parameters and
config · random seed where applicable · the exact command · an environment
dependency summary. **Byte-level proof is not required here.** Note the recorded
infrastructure caveat: `uv.lock` is stale and `uv sync` against it is destructive,
so the environment summary records what was actually installed.

**R-7 No silent cherry-picking.** Every variant tried is recorded — pairs, models,
thresholds — with the selection rule stated in advance. Reporting only the best
result is forbidden.

**R-8 No promotion.** Every result under this gate is
`EXPLORATORY_NON_PROMOTED_RESEARCH_RESULT` and may not be promoted to production
evidence, gate evidence or live readiness. This matches the prereg's own
"results never citable as evidence".

---

## 5. The anti-overengineering test

For every candidate requirement, ask:

> **Absent this, would the research conclusion about whether M15 carries an edge
> be *materially wrong*?**

**Yes** → it belongs in the Minimum Research Gate.
**No**, and it is mainly for evidence promotion, hostile filesystems, arbitrary
attacker input, production deployment or forensic provenance → **defer to the
production gate.**

Applied, with the reasoning stated so it can be checked:

| Requirement | In or out | Why |
| --- | --- | --- |
| Leakage controls (R-4) | **IN** | A leaked feature produces a confident, entirely false edge. This has already happened here. |
| Cost realism (R-5) | **IN** | The M1 flagship was gross-negative *and* net-negative; a zero-cost result would have looked publishable. |
| Train/val/holdout separation (R-2) | **IN** | Without it there is no out-of-sample claim at all. |
| Aggregation correctness (R-3) | **IN** | A wrong bucket boundary changes every label and every feature. |
| Reproducibility basics (R-6) | **IN** | An unreproducible positive is not a finding. |
| No cherry-picking (R-7) | **IN** | Selection over 20 pairs × models × thresholds manufactures edges from noise. |
| Byte-level four-limb proof (D-11) | **OUT** | Protects evidence *authority*, not correctness of a conclusion. |
| Candidate → promotion lifecycle | **OUT** | Nothing is promoted under this gate. |
| Reserved-filename impersonation refusal | **OUT** | Hostile-input hardening; the researcher is not the attacker here. |
| Win32 namespace / junction / reparse handling | **OUT** | Hostile-filesystem hardening. |
| Single routing authority, closed-set root | **OUT** | Evidence-surface integrity, not research correctness. |
| Provenance binding to committed authority | **OUT** for exploratory; **IN** as R-6's lightweight record | The conclusion needs to be reproducible, not forensically attributable. |
| `_SCHEMAS` / typed registry separation | **OUT** | Write-permission architecture. |
| Calendar-provenance machinery, complete | **OUT** | But an obvious coverage defect is still a finding (R-3). |

---

## 6. What passing this gate does **not** mean

A `PROMISING` outcome here is **not**: a Gate-3a formal continuation pass · a
production-grade source-audit pass · artifact promotion permission · live or demo
execution permission · P/V reader completion · calendar approval · satisfaction
of the §9 frozen acceptance thresholds.

**The frozen thresholds are not applied to exploratory results.** They govern the
*validation kill gate* and the *one-shot frozen holdout* on the **forward epoch**,
which is not yet adopted. An exploratory result may not be described as having
met or failed them, and the tokens `MEETS` and `DOES_NOT_MEET` are reserved to
that formal evaluation.

**If M15 research FAILS**, stopping work on production-grade evidence
infrastructure becomes a live option, and that is the point of sequencing this
gate first. **If it is PROMISING**, the programme returns to PR #450 §10's
deferred dependencies with a reason to pay for them.

---

## 7. Proposed staged flow

| Stage | Content | Reads real data? |
| --- | --- | --- |
| **R0** | Synthetic correctness: aggregation, label, evaluation harness, leakage controls, on synthetic and reference cases | **No** |
| **R1** | Read-only descriptive pass over an approved local dataset — schema, date span, pair coverage, missingness, descriptive statistics. **No training** | Yes — needs §8 Q3 |
| **R2** | Naive and simple baselines — momentum / reversion / existing simple model — under the committed cost model | Yes |
| **R3** | M15 model research (the planned LightGBM family) | Yes |
| **R4** | Out-of-sample evaluation under the pre-registered conditions | Yes |
| **R5** | Decision: **clearly promising** / **inconclusive** / **failed** | — |

**R0 is available now** and needs no further authority.

**A constraint the committed frame imposes on R4.** The frozen holdout lives on
the **forward epoch**, which §3.1 records as "not yet adopted", and the forward
epoch is `..._ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`. So the
one-shot frozen holdout **is not available to this gate**, and R4's out-of-sample
evaluation must be an *exploratory* temporal split inside the design span. It
**must not** consume, touch or approach the frozen holdout, and its result is not
a holdout result.

---

## 8. Questions this gate cannot rule — human + ChatGPT required

Committed authority settles more than expected (§2), but not these. Each is a
genuine research or governance choice, so this packet **stops** rather than
inventing.

**Q1 — the derivation-artifact precondition, and it is the blocking one.** The
prereg makes the exploratory span "usable only after the **§4 derivation artifact**
exists". That artifact is the derived M15 dataset the gate-3a continuation
produces — and the continuation is unauthorised, its output surface's production
dependencies were just deferred (PR #450 §10), and its calendar approval is
outstanding. **So the committed path to exploratory M15 data runs through
machinery this programme has deliberately postponed.** Three readings, and the
choice is not derivable:

- **(a)** Read-only research may proceed on a **research-scratch M15 derivation**
  that is explicitly *not* the §4 artifact — non-promoted, non-citable, outside
  the evidence tree. This unblocks R1–R4 now but creates a second derivation path.
- **(b)** The §4 artifact must exist first, so R1–R4 wait on the production
  dependencies — which is the sequencing this gate was created to avoid.
- **(c)** An existing committed dataset is used directly at M1 or another
  timeframe for a cheaper preliminary read, deferring M15 derivation.

**Q2 — initial pair set.** `PAIRS_20` is frozen for the *formal* family. Whether
exploratory work may start on a subset — cheaper, and lower multiple-comparison
burden — is a research choice. If a subset is used, R-7's selection rule must be
registered before it is chosen.

**Q3 — which dataset, and whether reading it may begin.** The OANDA archive
snapshot is committed provenance (20 pairs × 6 timeframes × 10 years, 17.54 GB).
Reading it is a **real-data read** and therefore Red under policy §6 regardless of
being read-only. This gate does not authorise it.

**Q4 — historical period for exploratory work.** The design span 2025-04-25 →
2026-02-28 is committed for the exploratory role. Whether a longer history may be
used for a preliminary look — and whether doing so prejudices the later formal
family — is a research choice.

**Q5 — the exact cost model for exploratory work.** The committed model is
`median_spread(pair, session) + pad_exec + 0.5 pip`. Whether exploratory work uses
it unchanged, or a deliberately pessimistic variant, is a choice. **Zero cost is
not among the options.**

**Q6 — initial model family.** LightGBM is the planned family. Whether R2's
baselines must complete before R3 begins is a sequencing choice.

**Q7 — how many research iterations before the exploratory out-of-sample split is
consumed.** This is the researcher-degrees-of-freedom control, and it needs a
number nobody has set. Without it, R-7 records the variants but nothing bounds
them.

**Q8 — where exploratory outputs live.** §9 classifies them; the concrete
directory and writer are deliberately not invented here.

---

## 9. Output classification

Everything produced under this gate is
**`RESEARCH_SCRATCH_NON_AUTHORITATIVE`**, and separately
`EXPLORATORY_NON_PROMOTED_RESEARCH_RESULT` as a finding.

Normative, if this gate is ruled: such output is kept **separate from the
production evidence tree**; it is **never automatically promoted**; and it
**never overwrites committed evidence**. **This packet invents no directory and no
writer** — if one is needed, an implementation Work PR decides it under the
constraints PR #450 §2 already fixes for the production surface, or under a
narrower rule of its own.

---

## 10. Metrics to measure

Not acceptance thresholds — **the minimum set that must be reported** for a
conclusion to be interpretable:

trade count · gross return · **net return after costs** · Sharpe or an equivalent
risk-adjusted metric · maximum drawdown · hit rate · average trade expectancy ·
stability by period · stability by pair · sensitivity to transaction costs.

Reported alongside: every variant tried (R-7), the selection rule, and the
reproducibility record (R-6). A result reported without its net-of-cost figure is
not a result.

---

## 11. Non-authorisation

This packet authorises no operation. It permits no real-data read, no dataset
download, no derivation, no training, no inference, no validation, no holdout
evaluation, no execution, no broker or demo activity, no database access, no
network access, and no calendar generation. It adopts no epoch, promotes no
artifact, and grants no source-audit acceptance. It does not authorise the
gate-3a continuation and does not discharge
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`.

Nothing in its preparation used a forbidden operation: no source, test or artifact
change · no real-data read · no `.env` read · no DB · no network, DNS or socket ·
no credential use · no PR merged.

`PRODUCTION_READINESS_NOT_CLAIMED` · `NO_EXECUTION_PERFORMED`.

---

## 12. Completion state

**`M15_MINIMUM_RESEARCH_GATE_PENDING_HUMAN_CHATGPT_RULING`.**

The boundaries (§3), the integrity requirements (§4), the scope test (§5), the
non-implications (§6), the staged flow (§7), the output classification (§9) and
the metric set (§10) are derived from committed authority and are offered as
ruled text.

**Q1 blocks the gate from being useful without a ruling**, and Q2–Q8 are genuine
choices. An AI may not settle them: Q1 in particular decides whether M15 research
can begin before the deferred production dependencies are paid for, which is the
question this gate exists to put.
