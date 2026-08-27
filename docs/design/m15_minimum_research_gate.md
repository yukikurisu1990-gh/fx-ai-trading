# M15 Minimum Research Gate — decision packet

**Type.** Gate-decision PR (policy §14.2). **Risk tier.** Amber — doc-only, and
it defines a research boundary.

**Completion state.** One, unchanged:
`M15_MINIMUM_RESEARCH_GATE_PENDING_HUMAN_CHATGPT_RULING`

**Zero-data feasibility disposition** (§0, a carried status — *not* a second
completion state, and not a verdict on family A):
`SAMPLE_FLOOR_REACHABILITY_NOT_DETERMINABLE_WITHOUT_MEASURED_INPUTS` ·
`ZERO_DATA_FEASIBILITY_BEFORE_REAL_DATA`

**Unified referral — RULED** (§8.1, human + ChatGPT):
`Q11_AND_SECTION0_RULED_FREEZE_D_AT_GATE3A_CONTINUATION_BEFORE_DATA` ·
`TWO_MONTH_HOLDOUT_IS_A_MINIMUM_NOT_THE_OPERATIVE_DURATION` ·
`HOLDOUT_DURATION_D_IS_FROZEN_ONCE_AT_GATE3A_CONTINUATION_BEFORE_DATA` ·
`POST_FREEZE_DURATION_RESELECTION_IS_FORBIDDEN_FOR_CURRENT_FAMILY_A` ·
`DURATION_SELECTION_MUST_BE_OUTCOME_BLIND` ·
`Q11_AND_SECTION0_RULED_ON_FREEZE_SEMANTICS`

**Q10 rulings — RULED** (§8.2.0, human + ChatGPT):
`Q10_A_RULED_ELAPSED_UTC_CALENDAR_SPAN` ·
`Q10_II_DAY_IDENTITY_RULED_UTC_CALENDAR_DATE_EXPECTED_SLOTS_FROM_APPROVED_CALENDAR_AUTHORITY` ·
`Q10_B_RULED_EXPLICIT_HUMAN_CHATGPT_UTC_WINDOW_DECLARATION_REQUIRED_BEFORE_CONTINUATION` ·
`UTC_WINDOW_DECLARATION_MUST_PRECEDE_GATE3A_CONTINUATION_AUTHORISATION` ·
`SAME_D_DIFFERENT_WINDOW_IS_RESELECTION` ·
`EMBARGO_IS_A_BAR_CONSTRAINT_NOT_A_CALENDAR_DERIVATION` ·
`D_IS_ELAPSED_UTC_TIME != SAMPLE_COUNT_IS_CALENDAR_TIME`

**Q10 is not closed** — limb **(iii)**, the annualisation factor, remains
**RULED** — limb **(iii)** covers the **Sharpe sampling index, the idle-day rule and the
annualisation factor** at §8.7.4
(`Q10_III_RULED_COMPLETE_UTC_CALENDAR_DATE_SHARPE_INDEX_IDLE_ZERO_ANNUALISED_BY_SQRT_365`),
and its **guard order** at §8.8.4
(`Q10_III_A_RULED_PRE_FILL_ACTIVE_OBSERVATION_GUARDS_PRECEDE_CALENDAR_ZERO_FILL`);
**where the two differ, §8.8.4 governs**. `Q10_III_PENDING_HUMAN_CHATGPT_RULING` is
**HISTORICAL**. Limb **(i)**, entry- vs exit-day PnL
attribution, is **RULED** (§8.5.0, bundled with NR-L).

**NR-K — RULED** (§8.3.0, human + ChatGPT):
`NR_K_RULED_P_EQUALS_FROZEN_REGISTERED_FAMILY_A_UNIVERSE` ·
`P_SHALL_NOT_BE_REDUCED_AFTER_FAMILY_A_PREREGISTRATION` ·
`P_MUST_NOT_COLLAPSE_TO_ONE_BY_POST_HOC_CONTRIBUTOR_SELECTION` ·
`REGISTERED_PAIR_FAILURE_DOES_NOT_AUTHORISE_P_SHRINKAGE` ·
`NEW_EXPLICIT_PREREGISTRATION_OR_CONTRACT_DECISION_REQUIRED`

For the current Family A, **`P = 20`**, and the authority is the frozen registered
`PAIRS_20` universe. **This does not mean all twenty pairs must trade** — see
§8.3.0, where that misreading is foreclosed first because it is the likeliest one.

**Mean overlap fraction — RULED** (§8.4.0, human + ChatGPT):
**`MEAN_OVERLAP_RULED_EVENT_LEVEL_SAME_HORIZON_CLOCK_EQUAL_WEIGHT_ROLE_LOCAL`** ·
`MEAN_OVERLAP_GAP_CLOCK_RULED_SAME_REGISTERED_M15_PREDICTION_CLOCK_AS_HORIZON` ·
`GAP_AND_HORIZON_MUST_USE_THE_SAME_REGISTERED_M15_PREDICTION_CLOCK` ·
`OMEGA_CLOCK_MUST_NOT_BE_SELECTED_TO_MINIMISE_RHO_H_OR_INCREASE_N_EFF` ·
`Q10_A_ELAPSED_UTC_DURATION_DOES_NOT_DEFINE_MEAN_OVERLAP_GAP_UNITS` ·
`MEAN_OVERLAP_USES_EVENT_LEVEL_TRANSFORM_THEN_ARITHMETIC_MEAN` ·
`MEAN_GAP_APPROXIMATION_IS_NOT_AN_ALLOWED_EFFECTIVE_N_AUTHORITY_FOR_CURRENT_FAMILY_A` ·
`MEAN_OVERLAP_WITHIN_PAIR_WEIGHTING_IS_EQUAL_PER_ADJACENT_EVENT_INTERVAL` ·
`ZERO_EVENT_PAIR_HAS_ZERO_RAW_CONTRIBUTION_AND_NO_SYNTHETIC_OVERLAP` ·
`SINGLE_EVENT_PAIR_HAS_ZERO_REALISED_NEXT_EVENT_OVERLAP` ·
`MEAN_OVERLAP_IS_COMPUTED_PAIR_LOCALLY` · `GLOBAL_CROSS_PAIR_GAP_POOLING_IS_FORBIDDEN` ·
`OMEGA_METHOD_IS_PRE_DATA_FROZEN_OMEGA_VALUE_IS_ROLE_LOCAL_MEASURED` ·
`MEASUREMENT_MAY_DETERMINE_THE_VERDICT_BUT_MUST_NOT_REDIRECT_THE_EXPERIMENT` ·
`MEAN_OVERLAP_RULING_DOES_NOT_AUTHORISE_REAL_DATA_ACCESS` ·
**`MEAN_OVERLAP_CLOCK_RULED_APPROVED_ELIGIBLE_M15_SLOT_SEQUENCE`** ·
**`MEAN_OVERLAP_CLOCK_SUBSTRATE_RULED_APPROVED_CALENDAR_ELIGIBLE_SLOTS`** ·
`OMEGA_CLOCK_SUBSTRATE_MUST_NOT_BE_CHOSEN_TO_MINIMISE_RHO_H` ·
**`MEAN_OVERLAP_SEMANTICS_RULED_EXCEPT_ROLE_SPAN_AND_ROLLOVER_PENDING_CALENDAR_INSTANTIATION`**
— **HISTORICAL under Ruling ω-13**; the operative status is
`MEAN_OVERLAP_MINIMUM_RESEARCH_CONTRACT_RULED_PENDING_CALENDAR_INSTANTIATION`, under
which the rollover/holiday membership outcome is a `RUNTIME_CALENDAR_INSTANTIATION_OUTCOME`
and the role-span boundary is the one genuinely-open `ω` semantic item

**`H` and `g` are both counted on the approved-calendar eligible M15 slot
sequence** — `H = 24` consecutive eligible slots, `g` in eligible-slot steps. No
continuous-grid fallback, no heuristic clock, no inferred market hours, and **no
market-hours semantics are authored here**. The ruling takes the branch that
**imports** `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` and that runs
**conservative relative to the continuous grid** (omitting *ineligible* slots
shortens `g`, raising `ω` and `rho_h`) — though **not** the `ω`-maximising candidate,
which is event-index and is foreclosed.
**No empirical readiness is claimed**: `ω` cannot be authoritatively instantiated
before that approval.

**Mean-overlap contract — CLOSED for Minimum Research Gate purposes** (§8.4.0,
Ruling ω-13, human + ChatGPT):
**`MEAN_OVERLAP_MINIMUM_RESEARCH_CONTRACT_RULED_PENDING_CALENDAR_INSTANTIATION`** ·
`WINDOW_IDENTITY_PREDECLARED_CALENDAR_MATERIALISED_WITHOUT_POST_CALENDAR_RESELECTION` ·
`CALENDAR_MATERIALISATION_MAY_NOT_REOPEN_WINDOW_SELECTION` ·
`OMEGA_EVENT_ELIGIBILITY_RULES_MUST_BE_PRE_DATA_FROZEN` ·
`LATER_EVENT_ELIGIBILITY_CALENDAR_MUST_NOT_RETROACTIVELY_CHANGE_CURRENT_FAMILY_A_EVENT_SEQUENCE` ·
`POST_OBSERVATION_EVENT_ELIGIBILITY_RECLASSIFICATION_FOR_CURRENT_FAMILY_A_IS_FORBIDDEN` ·
`PAIR_SPECIFIC_SLOT_VARIATION_MUST_BE_CALENDAR_DERIVED_NOT_RESEARCHER_SELECTED` ·
`PAIR_CALENDAR_VARIATION_MUST_NOT_BE_OPTIMISED_AGAINST_EFFECTIVE_N` ·
`NEW_OMEGA_FINDINGS_DO_NOT_AUTOMATICALLY_BECOME_RESEARCH_BLOCKERS` ·
`OMEGA_RECLASSIFICATION_AMENDMENT_CLASSIFICATION_NOT_SETTLED`

**The order, composed with Q10-B:** the exact window is **declared first**, Calendar A
is then **materialised for that declaration**, Calendar A is **frozen**, the window may
**not** be reselected because of calendar content, and only then may decision-bearing
data be observed. *This supersedes Ruling ω-12(d) and adopts §8.2.0's committed
placement — the packet's own ordering was the wrong one.* **No `T_v`, `T_h` or `D` value
is chosen.**

**Deferred outside the gate, documented and not closed:**
`FR_8_SECOND_LIMB_OPEN_MATERIALISED_SET_MAY_STILL_BE_DERIVATION_TRACKING` and
`NO_LOCUS_RECORDS_THE_FROZEN_CALENDAR_VERSION_IDENTITY`, both
**`DEFERRED_PRODUCTION_CHECKABILITY`**, subject to
`ONE_SELECTABLE_IMMUTABLE_CALENDAR_INSTANCE_WITH_RECORDED_IDENTITY_IS_AN_EXECUTION_PREREQUISITE`
and `CALENDAR_VERSION_IDENTITY_RECORDING_IMPLEMENTATION_PENDING`. **Where that
prerequisite does not hold the deferral lapses** and residual 5 is a
`MINIMUM_RESEARCH_GATE_BLOCKER`. What is **not** deferred is §5's own R-6 lightweight
record: any output consuming a calendar must record its `authority_version`,
`content_digest` and `target_epoch`. The concrete rollover/holiday membership set is a
**`RUNTIME_CALENDAR_INSTANTIATION_OUTCOME`**, a classification that **depends on
residual 5's deferral holding**.

**Calendar residuals — RULED** (§8.4.0, Ruling ω-12, human + ChatGPT):
**`OMEGA_CALENDAR_AUTHORITY_RULED_SINGLE_FROZEN_VERSION_REQUIRED`** ·
**`OMEGA_CALENDAR_AUTHORITY_RULED_PENDING_APPROVED_CALENDAR_INSTANTIATION`** ·
`OMEGA_SLOT_MEMBERSHIP_AUTHORITY_IS_THE_D6_CLOSURE_MARKET_CALENDAR_EXPECTED_M15_SLOTS` ·
`MEAN_OVERLAP_DOES_NOT_OWN_ROLLOVER_OR_HOLIDAY_RULES` ·
`OMEGA_SLOT_MEMBERSHIP_AUTHORITY_MUST_BE_SINGLE_VERSIONED_AND_FROZEN_BEFORE_WINDOW_DECLARATION`
(the single-versioned and frozen elements stand; the **`BEFORE_WINDOW_DECLARATION`**
element is **historical** — Ruling ω-13(a) materialises the forward-epoch artifact
**for** the declaration) ·
`CALENDAR_FREEZE_PRECEDES_WINDOW_FREEZE_PRECEDES_DATA_OBSERVATION` — **HISTORICAL,
superseded by Ruling ω-13(a)** ·
`OMEGA_CALENDAR_CONTENT_MUST_BE_OUTCOME_BLIND` ·
`POST_OBSERVATION_CALENDAR_MUTATION_IS_FORBIDDEN_FOR_CURRENT_FAMILY_A` ·
`T6_LATER_CALENDAR_MAY_NOT_RETROACTIVELY_CHANGE_OMEGA_SLOT_MEMBERSHIP_FOR_AN_ALREADY_FROZEN_FAMILY_A_WINDOW` ·
`ONE_FROZEN_CALENDAR_VERSION_GOVERNS_BOTH_OMEGA_AND_COVERAGE` ·
`CALENDAR_FREEZE_ORDER_IS_ADDED_HERE_NOT_IMPLIED_BY_Q10_B`

**Two concrete authorities, and they are different objects.** **A** — the D-6
closure/market calendar artifact, carrying `expected_m15_slots` (a *materialised* set;
the generating-rule spelling is refused by name), `authority_version`,
`content_digest`, `target_epoch` and the approval marker — governs **slot membership**
and is `ω`'s sole authority. **B** — Ruling 4's holiday / thin-liquidity calendar,
which T-6 re-pointed to "approved before gate 7" — governs **event eligibility** only,
and never membership. **No schema is invented**: the identity fields already exist in
the committed interface. **Neither artifact exists yet**, and no calendar is created
here.

**Four limbs were derived and are confirmed; six are explicit human + ChatGPT
choices** — the clock, the weighting, the zero-event and one-event dispositions, the
freeze semantics and the no-redesign rule (§8.4.0's own table says which is which).

**Q10(i) + NR-L — RULED as one bundled decision** (§8.5.0, human + ChatGPT):
**`Q10_I_RULED_REALIZED_PNL_ATTRIBUTED_TO_EXIT_UTC_DATE`** ·
**`NR_L_MINIMUM_RESEARCH_CONTRACT_RULED_PENDING_IMPLEMENTATION_AND_DESIGN_MEASUREMENT`**.
A trade's **entire** realised PnL goes to the UTC date of its registered **exit**
marker — no split, no mark-to-market allocation, no entry-day back-attribution — and
`c = mean_{p<q} |r_pq|`, equal-weight **Pearson** over the **190** unordered
off-diagonal entries of the frozen **`PAIRS_20`**, on per-pair daily **net realised**
PnL at `PRIMARY_COST_CELL_PIPS`, aligned to **one common complete DESIGN UTC
calendar-date index** (2025-04-25…2026-02-28, **310 dates**) with an **idle pair-date
carrying zero**, **failing closed** on any undefined required entry, measured **once**
on the **full DESIGN span**, method frozen now and never reselected after a downstream
observation. **No `c`, no correlation, no daily PnL and no `N_eff` is calculated.**
Closed by it: `NR_L_REQUIRES_HUMAN_CHATGPT_RULING` ·
`NR_L_PARTIALLY_DERIVED_BLOCKED_BY_Q10_I_AND_HUMAN_RULINGS` ·
`CORRELATION_SERIES_COST_LAYER_NOT_REGISTERED` ·
`CORRELATION_DATE_ALIGNMENT_NOT_REGISTERED` ·
`ALIGNMENT_MUST_NOT_CREATE_AN_UNREGISTERED_FAVOURABLE_SUBSET` ·
`UNDEFINED_CORRELATION_SEMANTICS_PENDING_HUMAN_CHATGPT_RULING` ·
`KEEP_P_20_BUT_COMPUTE_C_ON_A_FAVOURABLE_SUBSET` ·
`CORRELATION_SERIES_IS_A_STRATEGY_METRIC_AT_A_GATE_THAT_FORBIDS_THEM` (resolved by
reading: gate 3a fixes the **method**, the **measurement** happens later) ·
`NR_L_DAY_ATTRIBUTION_DEPENDS_ON_Q10_I` ·
`P_AND_CORRELATION_INDEX_SET_NOT_BOUND` ·
`OUTCOME_DRIVEN_CORRELATION_SET_IS_THE_SAME_LEVER_IN_THE_OTHER_FACTOR` — **all
HISTORICAL**. `MEAN_ABS_PAIRWISE_CORR_NOT_YET_ESTIMATED_DESIGN_DATA_ONLY` **survives**:
the contract is ruled, the value is not measured.

**The one blocker it left is now RULED — Ruling c-10** (§8.5.0, human + ChatGPT):
**`NR_L_C_PRECOMPUTED_FOR_ALL_REGISTERED_CONFIGURATIONS_BEFORE_VALIDATION_SELECTED_BY_CONFIG_ID_ONLY`**.
A DESIGN-only `c_design[config_id]` is computed for **every** preregistered candidate
configuration **before any validation observation**, the complete map is **frozen**,
the committed validation rule then selects one `config_id`, and the frozen `c` is
attached **mechanically**. One-way only —
**`C_MUST_NOT_BE_A_CONFIGURATION_SELECTION_CRITERION`** ·
**`VALIDATION_SELECTION_MAY_SELECT_CONFIG_ID_BUT_MAY_NOT_SELECT_OR_RECOMPUTE_C`** ·
**`SELECTED_CONFIG_USES_PREEXISTING_FROZEN_C_ONLY`**. An undefined `c` makes a
candidate **ineligible** and does **not** shrink the registered set
(`UNDEFINED_C_MAKES_A_CANDIDATE_INELIGIBLE_IT_DOES_NOT_SILENTLY_SHRINK_THE_REGISTERED_SET`);
the map's key set must equal the registered candidate set, an uncertifiable entry being
the recorded marker `C_UNCERTIFIABLE` and **never** a substituted number
(`AN_UNCERTIFIABLE_ENTRY_IS_A_RECORDED_MARKER_NEVER_A_NUMBER`). ⚠ Eligibility
filtering **is** a route by which `c`'s *certifiability* — not its value — reaches the
selection; it is nobody's choice, its direction is **conservative** (the sparsest
candidate is both the likeliest to be uncertifiable and the one with the lowest `c`),
and the filter-then-select versus select-then-check **order is unregistered**
(`SELECTION_VERSUS_CERTIFIABILITY_ORDER_NOT_REGISTERED`, carried with
**select-then-check** as the governing default, which refuses a rescue and so invents
no selection rule).

**Two blockers survived Ruling c-10 and are now CLOSED by §8.7.**
`C_DESIGN_SPAN_RUN_IN_SAMPLE_STATUS_NOT_REGISTERED` is ruled by **c-11** —
`DESIGN_C_SERIES_MUST_BE_GENERATED_WITHOUT_SAME_OBSERVATION_TARGET_LEAKAGE`, with the
Rulings c-6 and c-7 **unamended**: a structurally trade-free date is
carried as a zero, because a **common** trade-free prefix measurably **raises** `|r|`
rather than diluting it, which is the conservative arm — while c-7's economic
justification does not reach those dates and the generation method
**may not be selected for the span or sparsity it produces**. `C_MAP_INPUT_FREEZE_CONFLICTS_WITH_T6_HOLIDAY_CALENDAR_SCHEDULE`
is ruled by **c-12** — every decision-bearing input frozen before measurement, with the
Calendar B collision resolved by **scope, not schedule**: only the subset of eligibility
semantics that reaches current Family A is pre-`c` frozen, and a later Calendar B may
not retroactively alter a frozen `c_design`
(`POST_C_FREEZE_ELIGIBILITY_CHANGES_MUST_NOT_RETROACTIVELY_CHANGE_C_DESIGN`).
**`CLOSURE_CLAIM_WITHHELD`** — attempted a **third** time at §8.7.6 and grounded on a review section that did not yet exist; withheld then under **`CLOSURE_CLAIM_REQUIRES_COMPLETED_REVIEW_AND_NO_UNRESOLVED_MATERIAL_BLOCKER`** (§8.8.0 — the earlier same-round prohibition is **withdrawn as over-broad**). *The separate independent round has since run: §12.17 records **full coverage on the assigned scope, both roles returning**, so that rule's review condition is now **met**. Closure is still **NOT** taken, on a different ground — §8.9.6 records **seven live material blockers**, and **`M15_MINIMUM_RESEARCH_STATISTICAL_CONTRACT_NOT_CLOSED_MATERIAL_BLOCKERS_LIVE`**.*

**⚠ And c-10 corrects a premise this document carried.** §8.5.0 said the family
registers "three decision thresholds **and** three `ev_min` points", nine
configurations. `THRESHOLD_CANDIDATES` / `MAX_CONFIGURATIONS` are **M1-lineage**
(`scripts/ml_step4/contract.py`), and prereg **Ruling 9** says twice that "a raw
probability threshold alone is explicitly **not** a permitted decision rule". The
registered candidate set is **three `ev_min` points `{0.0, 0.25, 0.5}` and one
horizon — three configurations**, confirmed at prereg §8, §12 row 10 and §16 Ruling 9.
**`SECTION_8_5_0_NINE_CONFIGURATION_CLAIM_WITHDRAWN_THE_REGISTERED_SET_IS_THREE_EV_MIN_POINTS`.**
Also carried from c-10: `NR_L_CONFIGURATION_COVERAGE_IMPLEMENTATION_PENDING` ·
`C_DESIGN_SPAN_RUN_IN_SAMPLE_STATUS_NOT_REGISTERED` ·
`SELECTION_VERSUS_CERTIFIABILITY_ORDER_NOT_REGISTERED` ·
`C_10_AMENDMENT_CLASSIFICATION_NOT_SETTLED` ·
`CONFIGURATION_SET_AND_IDENTITIES_ARE_FROZEN_BEFORE_C_IS_MEASURED` ·
`C_PRODUCING_CONFIGURATION_REGISTRATION_IMPLEMENTATION_PENDING` ·
`NOTHING_BOUNDS_DESIGN_SPAN_ACTIVITY_AND_A_SPARSER_RUN_DILUTES_C` (**narrowed**: no
one may now select on it).

**Carried out of that ruling, none of them a research-result freedom:**
`C_INDEX_SET_NOT_RECORDED_IN_ANY_ARTIFACT` (`DEFERRED_PRODUCTION_CHECKABILITY`, with
§5's R-6 lightweight record **not** deferred) · `NR_L_PAIRWISE_COMPLETENESS_IMPLEMENTATION_PENDING` ·
`C_HAS_NO_PRODUCER_AND_NO_ARTIFACT` · `EXIT_DAY_ATTRIBUTION_BREAKS_ONE_COMMITTED_TEST_FIXTURE` ·
`SHARPE_DAY_SET_AND_CORRELATION_DAY_SET_ARE_DIFFERENT_OBJECTS` ·
`CORRELATION_DATE_INDEX_INCLUDES_NON_TRADING_CALENDAR_DATES` ·
`IDLE_ZERO_FILL_DILUTES_CORRELATION_IN_THE_SPARSE_REGIME` ·
`C_EQUAL_WEIGHTING_IS_EXACT_ONLY_UNDER_EQUAL_PER_PAIR_VARIANCES` ·
`CORRELATION_DATE_INDEX_COMMON_MODE_DIRECTION_NOT_ESTABLISHED` ·
`MEAN_ABS_ESTIMATOR_HAS_A_POSITIVE_NULL_FLOOR_AT_310_DATES` ·
`C_NEAR_DEGENERACY_IS_NOT_COVERED_BY_c_8_AND_MAY_NOT_BE_SILENTLY_REPAIRED` ·
`EXIT_DAY_ATTRIBUTION_REQUIRES_A_NEW_DAY_MAP_AT_THE_SECOND_CALL_SITE` ·
`Q10_I_REACHES_OPERATING_POINT_SELECTION_AND_THE_VALIDATION_KILL_GATE` ·
`Q10_I_RESTS_ON_OUTCOME_BLINDNESS_NOT_ON_A_SHOWN_TIGHTENING` ·
`Q10_I_EXIT_DISPERSION_MAY_WEAKLY_DILUTE_C` ·
`Q10_I_DOES_NOT_DEFINE_THE_TURNOVER_CEILING_DAY` ·
`NR_L_AND_Q10_I_AMENDMENT_CLASSIFICATION_NOT_SETTLED` ·
`MINIMUM_CALENDAR_IDENTITY_RECORD_REQUIRED_BEFORE_DATA_EXECUTION` (Ruling ω-13's
residual 5, carried unchanged and **not** reopened)

**Next decision — §8.6, one packet, three coupled questions** (Q10(iii) · the
duration boundaries · the exact `T_v`/`T_h`/`D` declaration): **complete, NOT ruled**.
**`Q10_III_RULED_COMPLETE_UTC_CALENDAR_DATE_SHARPE_INDEX_IDLE_ZERO_ANNUALISED_BY_SQRT_365`**
(§8.7.4) — the daily portfolio Sharpe is computed on the **complete UTC calendar-date
index of the evaluated role's span**, an idle date carrying **zero**, trades attributed
by Q10(i), annualised by **`√365`**. **maxDD is provably invariant** to that zero-fill,
and **coverage and turnover do not share the series**, so no other frozen row moves.
The material below is what the ruling was taken on: the only committed authority was prereg
§9's row label "**ann., UTC-day**"; `TRADING_DAYS_PER_YEAR = 252` is **M1 precedent**,
and because the committed Sharpe series is indexed on **active dates** it matches
neither a trading-day nor a calendar clock. Its **direction against `√252` is
conditional and unclaimed** — `C/B ≈ √(252/(365a))` at active share `a`, crossing 1 near
`a = 252/365 ≈ 0.690` — and establishing which side obtains needs the market-hours fact
this packet must not author
(`Q10_III_SQRT_252_IS_PERMISSIVE_ONLY_BELOW_252_ACTIVE_DATES_PER_YEAR`; the earlier
`…_IS_THE_PERMISSIVE_ARM` spelling and the "~1.9× in the sparse regime" figure are
**superseded and withdrawn**, §8.6.1). **No factor is adopted by convention.** The guard
order is ruled at §8.8.4 and the **exclusion** rule at §8.9.2.
**`EXACT_WINDOW_NOT_READY_FOR_DECLARATION_FORWARD_EPOCH_DOES_NOT_EXIST`** — and that is
**not a contract gap**: the committed forward-epoch adoption manifest carries
`ADOPTION_BLOCKED__FORWARD_DATA_NOT_YET_ACCRUED`,
`INSUFFICIENT_SAMPLE__ADOPTION_WAITS` and **zero forward-epoch bars in the repository**,
with `validation_span_utc` / `holdout_span_utc` / `forward_epoch_source` all `PENDING`.
The boundaries themselves are **reconstructed and largely committed** — design span,
dead window, forward floor, validation ≥ 3 months, holdout ≥ 2 months, purge/embargo
**25 M15 bars counted in bars never wall-clock**, and
`COMMITTED_EPOCH_CONSTANTS_ARE_CLOSED_AT_SECOND_GRANULARITY_DEAD_TO_FORWARD_IS_CONTIGUOUS`
(the constants are closed at second granularity; the dead→forward boundary is
**contiguous**, not gapped, and the endpoint convention for the two **undeclared**
forward roles stays
`DURATION_BOUNDARY_ARITHMETIC_AND_ENDPOINT_CONVENTION_PENDING_HUMAN_CHATGPT_RULING`).
Warm-up is already
regulated by gate 4's **T-1** (burn-in inside the forward epoch, event-ineligible), so
it cannot expand any role's sample; the numeric `W` is frozen at implementation. **Q10-B declares six objects**, not two — the validation start, `T_v`, the
**declared holdout start**, the holdout window, `T_h` and the operative `D` — and the
**holdout start is declared, never computed from the embargo**
(`EMBARGO_IS_A_BAR_CONSTRAINT_NOT_A_CALENDAR_DERIVATION`); `D` is the **holdout**
duration between the declared holdout start and `T_h`, expressly **not** `T_h − T_v`.
Also carried: `T_V_IS_THE_VALIDATION_END_INSTANT_T_H_IS_THE_HOLDOUT_END_INSTANT` ·
`SPAN_MINIMA_ARE_NOT_ELIGIBLE_EVENT_MINIMA` ·
`Q10_III_HAS_NO_COMMITTED_FACTOR_ONLY_AN_M1_PRECEDENT` ·
`Q10_III_OPTION_B_DEPENDS_ON_THE_CALENDAR_AUTHORITY` ·
**`TURNOVER_CEILING_COUNTS_TRADES_BY_ENTRY_UTC_DATE`** (§8.7.5 — each trade counted
**once**, on its **entry** date; `TURNOVER_CEILING_DAY_STILL_UNREGISTERED` is
**HISTORICAL**) ·
`TURNOVER_DAY_MUST_NOT_BE_BOUND_TO_THE_PNL_ATTRIBUTION_DAY_BY_INHERITANCE` (honoured:
Q10(i)'s **realised-outcome** date is the exit date, turnover's **initiation** date is
the entry date) · still unregistered and **not** ruled by it:
`TURNOVER_CEILING_MEAN_VERSUS_PER_DAY_CAP_STILL_UNREGISTERED` ·
`TURNOVER_DENOMINATOR_ACTIVE_VERSUS_CALENDAR_AXIS_STILL_UNREGISTERED`.

**Q10(i)+NR-L's two surviving blockers are CLOSED by §8.7**: **c-11**
(`DESIGN_C_SERIES_MUST_BE_GENERATED_WITHOUT_SAME_OBSERVATION_TARGET_LEAKAGE`, with the
Rulings c-6/c-7 **unamended** — a structurally trade-free date stays a
zero, since a **common** prefix measurably raises `|r|`, and the generation method may
not be selected for the span or sparsity it produces) and **c-12**
(`ALL_DECISION_BEARING_C_MAP_INPUTS_MUST_BE_FROZEN_BEFORE_C_MEASUREMENT` ·
`C_OBSERVATION_MUST_NOT_TRIGGER_UPSTREAM_RECONFIGURATION` ·
`POST_C_FREEZE_ELIGIBILITY_CHANGES_MUST_NOT_RETROACTIVELY_CHANGE_C_DESIGN`, the Calendar
B collision resolved by **scope, not schedule**).
**`CLOSURE_CLAIM_WITHHELD`** — attempted a **third** time at §8.7.6 and grounded on a review section that did not yet exist; withheld then under **`CLOSURE_CLAIM_REQUIRES_COMPLETED_REVIEW_AND_NO_UNRESOLVED_MATERIAL_BLOCKER`** (§8.8.0 — the earlier same-round prohibition is **withdrawn as over-broad**). *The separate independent round has since run: §12.17 records **full coverage on the assigned scope, both roles returning**, so that rule's review condition is now **met**. Closure is still **NOT** taken, on a different ground — §8.9.6 records **seven live material blockers**, and **`M15_MINIMUM_RESEARCH_STATISTICAL_CONTRACT_NOT_CLOSED_MATERIAL_BLOCKERS_LIVE`**.*

**§8.8 and §8.9 — five further rulings, registered here** (human + ChatGPT). §8.8:
**`C_13_RULED_CHRONOLOGICAL_EXPANDING_WINDOW_ONE_UTC_DATE_BLOCKS_WITH_THE_COMMITTED_25_BAR_PURGE`**
(the generator's shape, with `C_GENERATION_BLOCK_WIDTH_IS_ONE_UTC_DATE_SO_THE_PARTITION_HAS_ONE_PARAMETER`)
· **`C_14_RULED_THE_FREEZE_RULE_IS_NOT_A_WHITELIST_AND_FOLD_LOCALITY_IS_SCOPED`**
(`FOLD_LOCALITY_IS_REQUIRED_WHERE_A_FITTED_STATISTIC_REACHES_AN_OBSERVATION_IT_WAS_FITTED_ON`
· `THE_FOLD_THAT_PREDICTS_A_BAR_SUPPLIES_ITS_ELIGIBILITY_AND_BARRIER_GEOMETRY`
· `ONE_FIT_PER_PAIR_PER_BLOCK_SERVES_EVERY_CONFIG_ID`) ·
**`Q10_III_A_RULED_PRE_FILL_ACTIVE_OBSERVATION_GUARDS_PRECEDE_CALENDAR_ZERO_FILL`**
(membership filtering first, then the two committed guards, then the calendar zero-fill).
§8.9: **`C_15_RULED_FIRST_PREDICTED_DESIGN_DATE_IS_THE_25_PERCENT_PREFIX_BOUNDARY`**
(`n_initial_training_dates = ceil(0.25 × N_design_dates)` = **78** of **310**, first
predicted date **2025-07-12**, mechanically recomputed and not a literal;
`C_TRAINING_PREFIX_IS_AN_OUTCOME_BLIND_CONTRACT_CHOICE_NOT_AN_OPTIMALITY_CLAIM` ·
`C_TRAINING_PREFIX_MAY_NOT_BE_CHANGED_AFTER_ANY_MEASURED_QUANTITY_IS_SEEN` ·
`TWENTY_FIVE_PERCENT_IS_ANTI_CONSERVATIVE_RELATIVE_TO_EVERY_LARGER_PREFIX_AND_NO_ARM_IS_CLAIMED`)
· **`GUARD_FAILURE_EXCLUDES_CANDIDATE_FROM_VALIDATION_SELECTION`**
(`A_FIRED_GUARD_YIELDS_NO_SELECTABLE_VALUE` ·
`ALL_CANDIDATES_GUARD_FAILED_IS_FAIL_CLOSED_NOT_A_DEFAULT_SELECTION` ·
`NO_NEW_SHARPE_OBSERVATION_THRESHOLD_IS_CREATED`).

**And §8.9's own live blockers, registered with them** — these are why **no closure is
claimed** (§8.9.6): `C_GENERATION_CALIBRATION_SPLIT_IS_A_SECOND_UNREGISTERED_GENERATOR_PARAMETER_WITH_A_KNOWABLE_ANTI_CONSERVATIVE_LIMB`
· `C_MAP_INPUT_FREEZE_COLLIDES_WITH_THE_FEATURE_LIST_FIXED_AT_A_LATER_AUDIT_AND_SCOPE_CANNOT_RESOLVE_IT`
· `EXCLUSION_VERSUS_THE_COMMITTED_SWEEP_COMPLETENESS_CHECK_NOT_REGISTERED`
· `WHICH_VALIDATION_SELECTOR_GOVERNS_IS_UNREGISTERED_AND_DECIDES_WHETHER_Q10_III_B_BINDS`
· `PREREG_SECTION_6_BARRIER_RATIO_RECONSIDERATION_IS_AN_UNCLOSED_UPSTREAM_ROUTE`
· `SPARSE_CANDIDATE_CAN_CLEAR_THE_SHARPE_FLOOR_AT_VALIDATION_UNDER_ANY_INDEX_READING`
· `AN_IDENTICAL_INPUT_REBUILD_IS_A_RESELECTION_AND_THE_FIRST_BUILD_GOVERNS`. So
**`NO_NR_L_MINIMUM_RESEARCH_CONTRACT_BLOCKER_REMAINS` and
`M15_MINIMUM_RESEARCH_STATISTICAL_CONTRACT_CLOSED` are NOT recorded**, and
`C_DESIGN_GENERATOR_PENDING_ONE_EXACT_PARAMETER_DECISION` is discharged **only** as to
the first predicted DESIGN date.

**Still open after the ω ruling** — carried, not discharged:
`PAIR_LABEL_ASSIGNMENT_MUST_NOT_BE_REARRANGED_TO_REDUCE_OMEGA` (ruled as a
prohibition, **unenforced in code**) · `HORIZON_WALL_CLOCK_EXTENT_NOT_REGISTERED`
(**discharged as it bears on `ω`** by Ruling ω-11; survives wherever the frozen
horizon's wall-clock extent matters to something other than the overlap
arithmetic) ·
`OVERLAP_PER_RECORD_PROVENANCE_UNBOUND` · `NO_TURNOVER_DERIVED_GAP_BOUND` ·
`NO_CLIPPING_WITHOUT_COMMITTED_AUTHORITY` ·
`MEAN_OVERLAP_CLOCK_DEPENDS_ON_APPROVED_CALENDAR_AUTHORITY` ·
`CALENDAR_CONTENT_DETERMINES_OMEGA_SUBSTRATE` (the surface remains; the **prohibition
is now supplied** by Ruling ω-12(e)) ·
`LATER_EVENT_ELIGIBILITY_CALENDAR_MAY_STILL_MOVE_THE_EVENT_SET` — **closed for
current Family A by Ruling ω-13(b)**, and surviving for any later family ·
`WIDEN_ONLY_IS_CONSERVATIVE_FOR_THE_EVENT_COUNT_NOT_FOR_N_EFF` (removing an event
**merges gaps**, lowering `ω`, so the direction on `N_eff` is indeterminate) · `OMEGA_CALENDAR_AMENDMENT_CLASSIFICATION_NOT_SETTLED` ·
`CALENDAR_FREEZE_CHECKABILITY_IMPLEMENTATION_PENDING` ·
`POST_DECLARATION_PRE_OBSERVATION_CALENDAR_DEFECT_ROUTE_NOT_SETTLED` —
**enlarged** by Ruling ω-13(a), not classified by it: it now governs the **initial**
materialisation of the forward-epoch Calendar A and not merely a re-freeze, because
under (a) that artifact is first authored after the declaration is pushed, which makes
ω-12's case A structurally unreachable and this the **only** route ·
`ROLLOVER_AND_HOLIDAY_SLOT_ELIGIBILITY_RELATIVE_TO_THE_OMEGA_CLOCK_NOT_SETTLED` —
ownership ruled by ω-12(b); the **membership outcome** is classified
`RUNTIME_CALENDAR_INSTANTIATION_OUTCOME` by Ruling ω-13 and is therefore **documented
and not closed**, not discharged ·
`NO_PRE_DATA_FAMILY_A_EVENT_ELIGIBILITY_CONTRACT_EXISTS` ·
`PRE_DATA_FAMILY_A_EVENT_ELIGIBILITY_CONTRACT_REQUIRED_BEFORE_CONTINUATION` (Ruling
ω-13(b) states the obligation; **no such artifact exists and this packet creates
none**) ·
`ROLE_SPAN_HORIZON_TRUNCATION_RULE_NOT_REGISTERED` (the one genuinely-open `ω`
**semantic** item. Ruling ω-13 does **not** classify it — it is not among the six — and
it is **not** demoted: §8.4.0 says the ruling "does **not** fill it", committed
machinery "carries **no rule either way**", and `OVERLAP_PER_RECORD_PROVENANCE_UNBOUND`
leaves the arm selectable **at computation time**. Either the truncation rule is part of
the method `OMEGA_METHOD_IS_PRE_DATA_FROZEN_OMEGA_VALUE_IS_ROLE_LOCAL_MEASURED` requires
frozen before data — in which case it must be registered **before** `ω` is measured, and
it is not enumerated in ω-9's frozen-method list — or it is not, in which case the arm
is selectable **after** decision-bearing observation.
**`ROLE_SPAN_TRUNCATION_ARM_SELECTION_POINT_NOT_BOUND`**) ·
`ROUND_11_REVIEW_COVERAGE_PARTIAL_TWO_OF_THREE_ROLES_TERMINATED` ·
`MEAN_OVERLAP_CLOCK_AMENDMENT_CLASSIFICATION_NOT_SETTLED` ·
`M15_PREDICTION_HORIZON_CLOCK_IS_COINED_BY_THIS_RULING_NOT_REGISTERED` ·
`MEAN_OVERLAP_PAIR_SET_MUST_NOT_SHRINK` — **partly discharged only**: Rulings ω-5/ω-6
fix what value fills an excluded pair's slot, while its provenance half stays open as
`OVERLAP_PER_RECORD_PROVENANCE_UNBOUND` ·
`OMEGA_METHOD_MUST_NOT_BE_SELECTED_AFTER_OBSERVING_GAP_STRUCTURE_ON_ANY_SPAN` —
**now discharged for MO-2 specifically** by Ruling ω-11, which supplies the *reason*
A-ω-5 said a timestamp could not; it is carried for the limbs ω-11 does not reach ·
`MEAN_OVERLAP_AMENDMENT_CLASSIFICATION_NOT_SETTLED` ·
`MEAN_OVERLAP_FRACTION_IS_AN_EFFECTIVE_N_AUTHORITY_PARAMETER` ·
`Q10_A_DOES_NOT_RULE_THE_GAP_UNIT` ·
`DRAFT_AND_APPROVED_OVERLAP_FORMULATIONS_ARE_DIFFERENT_OBJECTS_AND_DIVERGE_INSIDE_THE_HORIZON`

**Still open:**
`EXACT_D_SELECTION_STILL_PENDING_UPSTREAM_AUTHORITIES` ·
`DURATION_BOUNDARY_ARITHMETIC_AND_ENDPOINT_CONVENTION_PENDING_HUMAN_CHATGPT_RULING` ·
`COVERAGE_DENOMINATOR_PAIR_TO_PORTFOLIO_LEVEL_NOT_RULED` ·
`P_AUTHORITY_RULED_IMPLEMENTATION_COMPLETENESS_PIN_PENDING` ·
`NR_K_AMENDMENT_CLASSIFICATION_OF_THE_TEST_INVALIDATING_LIMB_NOT_SETTLED` ·
`NO_FORWARD_SPAN_FULL_ROSTER_COVERAGE_GATE_COMMITTED` ·
`CONCENTRATION_CAP_DROP_MOTIVE_SURVIVES_NR_K` ·
`DURATION_WINDOW_FREEZE_REQUIRES_HUMAN_CHATGPT_DECISION` ·
`GATE3A_CONTINUATION_DATE_NOT_FROZEN_RESIDUAL_AFTER_Q11_SECTION0_RULING` ·
`REGISTERED_DATA_PLAN_REFERENT_AND_CONTENTS_NOT_DETERMINABLE` ·
`NO_GENERAL_CONTRACT_AMENDMENT_PROCEDURE_REGISTERED` ·
`SPAN_SIZING_BASIS_NOT_COMMITTED` ·
`VALIDATION_BRANCH_DISJUNCTION_HAS_NO_SELECTOR_RESIDUAL_AFTER_Q11_SECTION0_RULING` ·
`NEW_PREREGISTRATION_SUFFICIENCY_FOR_A_DIFFERENT_D_NOT_RULED` ·
`FREEZE_CHECKABILITY_WORDING_NOT_ADOPTED`

**FR-19** remains open and is **not** a residual of this ruling. Its committed
disposition is unchanged — `FR_19_SEPARATE_TEST_SAFETY_WORK_PR_OPEN` — and it is
carried here as a **precondition candidate for future research execution**, which
is a note about sequencing, not a change of disposition. §3.5's finding stands
undiluted: this gate "inherits no working `.env` defence and no working network
defence, and must supply its own".

**`NON_NORMATIVE_DIAGNOSTIC_ONLY` — document-wide.** Every duration, α, power,
false-positive, false-negative, deflator and standard-error figure in §0, §8.1,
§8.2, **§8.3, §8.4, §8.5, §8.6, §8.7, §8.8, §8.9** and §12 is a derived diagnostic
computed under stated modelling assumptions,
and appears in **no** committed source — notably ~1,065 / ~1,111 / ~1,312 weekday
days, 37%, 43%, 50%, the one-sided 5%, SE ≈ 2.4 / 3.10, the 4.36 budget, 5.90,
§8.3.0/§8.3.2's `×1.05 / ×1.29 / ×1.74 / ×1.81 / ×3.44 / ×6.70` and the 20.9× swing,
§8.4's `ω = 0.146`, the 6.25× divergence and every row of its comparison table, and
§8.6–§8.9's `≈ 1.07`, `1.38`, `2.45`, `3.49`, `−19,085.9 → −4.31`, the 61-date span and
every row of §8.7.2's and §8.9.1's synthetic tables — each computed on a generating
model stated inline so the figures are reproducible from the text, and none of them
read from data.
**None may be promoted to contract justification, cited as a required duration, or
used to size `D`** (Ruling B: the exact `D` is not ruled).

**And the *unit* those figures are stated in is diagnostic too.** "Weekday day"
appears nowhere in the repository outside this document; "trading day" is used in
gate-4 arithmetic and M1-lineage reports but is **defined nowhere** in the M15
contract. Every duration in §0, §8.1 and §12 stated in weekday days inherits that
status. The unit `D` is denominated in is now **ruled** — elapsed UTC calendar
time (`Q10_A_RULED_ELAPSED_UTC_CALENDAR_SPAN`, §8.2.0) — and it is expressly **not**
a weekday count, so every weekday-day figure here is a diagnostic stated in a unit
that is not `D`'s.

**Historical:** `MEAN_OVERLAP_PENDING_HUMAN_CHATGPT_RULING`,
`MEAN_OVERLAP_CORE_DERIVED_READY_FOR_REVIEW`,
`MEAN_OVERLAP_FRACTION_UNIT_NOT_REGISTERED`,
`GAP_AND_HORIZON_MUST_BE_READ_ON_THE_SAME_CLOCK` (subsumed by the stronger
same-*horizon*-clock token),
`OMEGA_SUBSTRATE_CALENDAR_IDENTITY_NOT_SETTLED`,
`NO_OUTCOME_BLINDNESS_REQUIREMENT_BINDS_CALENDAR_CONTENT` and
`OMEGA_DEPENDENCE_NOT_DISCLOSED_AT_CALENDAR_APPROVAL` (all three **ruled by
Ruling ω-12**; `ROLLOVER_AND_HOLIDAY_SLOT_ELIGIBILITY_RELATIVE_TO_THE_OMEGA_CLOCK_NOT_SETTLED`
was listed here in an earlier drafting and is **restored to the open list**, its
ownership ruled and its outcome still A's content), `OMEGA_SUBSTRATE_CONTENT_MAY_MOVE_AFTER_THE_METHOD_FREEZE` (closed by
ω-12 **for slot membership**; survives for the event set, and **not** conservatively),
`SAME_CLOCK_RULE_DOES_NOT_YET_IDENTIFY_THE_CLOCK_SUBSTRATE`
and `OMEGA_H_CONSTANCY_DISCHARGED_ONLY_ON_A_BARS_THAT_EXIST_READING` and
`MEAN_OVERLAP_UNIT_TIED_TO_AN_UNREGISTERED_HORIZON_CLOCK` (all three **discharged by
Ruling ω-11**, which names the substrate), `NO_ADJACENT_GAP_DOES_NOT_AUTOMATICALLY_MEAN_ZERO_OVERLAP`
and `ZERO_EVENT_OMEGA_MUST_NOT_HALT_A_NORMAL_OUTCOME` (both **satisfied** by Rulings
ω-5/ω-6 rather than dropped) — **SUPERSEDED BY HUMAN + CHATGPT RULING** (§8.4.0).
`NOTHING_PREVENTS_OVERLAP_BEING_MEASURED_ON_THE_SPAN_IT_JUDGES_WHILE_CORRELATION_IS_FROZEN_ON_DESIGN`
— **discharged** by Ruling ω-9, which records the reasoning §8.4.2 said nobody had
recorded and resolves the asymmetry deliberately, and which **mandates** the
measurement rather than merely permitting it, so "nothing prevents" is now the wrong
modality. `NR_K_PENDING_HUMAN_CHATGPT_RULING`,
`NR_K_REQUIRES_HUMAN_CHATGPT_RULING_AFTER_Q10`,
`P_DEFINITION_CONFLICT_SPEC_CONTRIBUTING_VS_UNIVERSE_FIXED` and
`PAIR_UNIVERSE_FREEZE_POINT_NOT_COMMITTED` — **discharged as to `P`'s binding
only** (§8.3.0, §8.3.4); its **forward-epoch limb survives** and is carried above
beside `NO_FORWARD_SPAN_FULL_ROSTER_COVERAGE_GATE_COMMITTED`, which may or may not
be the same gap — the coverage gate and the forward inventory schema are two
separate absences.
`DRAFT_AND_APPROVED_OVERLAP_ESTIMATORS_DIVERGE_AT_THE_FROZEN_CEILING` —
**superseded by**
`DRAFT_AND_APPROVED_OVERLAP_FORMULATIONS_ARE_DIFFERENT_OBJECTS_AND_DIVERGE_INSIDE_THE_HORIZON`
(§8.4.3): the two are **different objects** — a unit fraction multiplied by `(H − 1)`
against a divisor — they **diverge inside the horizon**, and the ceiling relationship
is **undetermined**, resting on a clamp this packet supplied and the prereg does not
write. Both the earlier "12.5× at the ceiling" reading **and** the replacement "they
agree at the ceiling" reading are **withdrawn**; Ruling ω-3 bars the draft as an
authority in any case. `Q11_AND_SECTION0_PENDING_HUMAN_CHATGPT_RULING` — **SUPERSEDED BY
HUMAN + CHATGPT RULING** (§8.1.0). `Q10_NEXT_HUMAN_CHATGPT_RULING_REQUIRED` —
renamed `Q10_PENDING_HUMAN_CHATGPT_RULING` (§8.2), then **SUPERSEDED** for Q10-A,
Q10(ii) and Q10-B by the rulings at §8.2.0; it does **not** carry over to
Q10(i)/(iii), which are recorded separately.

**Statuses carried, unchanged.**
`M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES` ·
`M15_GATE3A_CONTINUATION_OUTPUT_SURFACE_CORE_RULED_PRODUCTION_DEPENDENCIES_DEFERRED`
(PR #450) · `M15_GATE3A_CONTRACT_AND_PROOF_DESIGN_DECISION_RULED` (PR #444) ·
`M15_GATE3A_D5_8_AND_SECTION12_25_CONTRACT_RULED` (PR #448) ·
`M15_AGGREGATION_DATASET_MACHINERY_IMPLEMENTED_SYNTHETIC_ONLY_NO_RUN` ·
`M15_GATE3A_DATASET_EPOCH_ADOPTION_PROPOSED` · `PRODUCTION_CONTINUATION_NOT_READY` ·
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

## 0. Zero-data feasibility — the most upstream question

`ZERO_DATA_FEASIBILITY_BEFORE_REAL_DATA`. Before Q1–Q11 are ruled, a cheaper
question is asked: **using committed authority and no data at all, can M15
Family A ever reach the frozen sample floors?** If it provably could not, every
question below that presupposes a real-data read would not need answering.

**This is a derivation, not a gate.** It advances nothing, appears nowhere in the
playbook's gate order, and passing or failing it changes no research state. It is
arithmetic over committed constants, performed in this document: **no code is
executed, no stage is run, nothing is read.**

### 0.1 The committed quantities

| Quantity | Value | Committed source |
| --- | --- | --- |
| horizon `H` | 24 M15 bars (6 h) | Ruling 6; spec `frozen_parameters.H_m15_bars`; `effective_n.py:51` |
| raw trade floor | ≥ 1,000 holdout trades | prereg §9 H; `effective_n.py:53` |
| effective-N floor | ≥ 400 | prereg §9 H; `effective_n.py:52` |
| turnover ceiling | ≤ 40 trades/day portfolio-wide | prereg §9 H; also binds validation as "the turnover budget" (§9.V, Rulings 9 and 10) |
| pair universe | PAIRS_20 | Ruling 2 / R-2a |
| pair trade concentration | ≤ 0.40 — a **max single-pair share** (`metrics.py:154`) | prereg §9 H |
| `rho_h` | `1 + (H−1) × mean_overlap_fraction` | spec `horizon_overlap_factor` |
| `rho_x` | `1 + (P−1) × mean_abs_pairwise_corr` | spec `cross_pair_discount` |
| `N_eff` | `Σ(N_raw_p / rho_h_p) / rho_x` | spec `portfolio_effective`; `effective_n.py:283–302` |
| holdout span | ≥ 2 months, actual boundaries `[FIXED-AT gate-3a continuation]` — a **minimum**; no committed source states a maximum | Ruling 2; absence of a maximum verified across the prereg, the gate-4 audit, the gate-3a record and the playbook |

**The hinge.** The ceiling and `N_raw` constrain the same variable: the spec
defines `N_raw` as "eligible **traded** events … that **fire an EV-gated trade**",
and `effective_n.py:63–73` pins it against the two strictly larger confusable
counts, noting that feeding either "clears the frozen floors by orders of
magnitude and thereby **disarms `INSUFFICIENT_SAMPLE`**". Were `N_raw` the
eligible-*bar* count, the ceiling would not bind it and none of this would run.

### 0.2 Three inputs are empirical — and that is the result

`mean_overlap_fraction`, `mean_abs_pairwise_corr` and the event rate itself are
**not frozen**.

- The spec ties the correlation to "per-pair **daily PnL** series, estimated on
  **DESIGN data only** and frozen". A daily-PnL series does not exist until a
  strategy has been fitted and run on the design span — **the stages this
  derivation sits upstream of.** The input that most moves the answer is produced
  by the work it is meant to precede.
- `mean_overlap_fraction` is **not** in `frozen_parameters` and, unlike the
  correlation, is not even scoped to design data — on the plain reading it is
  measured on the evaluated role's own realised gaps, making it structurally
  unknowable in advance.
- No committed authority bounds the traded-event rate **from below**; the ceiling
  bounds it only from above.

### 0.3 The decisive arithmetic: the deflator budget

The sharpest zero-data statement available is not a duration but a **budget**. At
the ceiling `R = 40/day` over a 2-month holdout (61 calendar × 5/7 ≈ 43.6 weekday
days), the maximum attainable raw count is `40 × 43.6 = 1,744`, so `N_eff ≥ 400`
requires

> **`(1 + 23·ω) × (1 + 19·c) ≤ 4.36`**

*(The `19` is `P − 1`. It was an assumption when this was written; since §8.3.0 it
rests on **`NR_K_RULED_P_EQUALS_FROZEN_REGISTERED_FAMILY_A_UNIVERSE`**. **Two** terms
remain unpinned, not one — `ω` (§8.4) and `c` (NR-L) — and an earlier version of
this note said `ω` was "the last", which is **withdrawn**. At the diagnostic
`c = 0.3` used throughout this document, `rho_x = 6.70` exceeds the whole 4.36
budget on its own, just as `rho_h = 5.90` does under Poisson. Neither may be treated
as the residual of the other.)*

— the *entire* deflation budget, for both effects combined, at the frozen minimum
span and the maximum permitted rate. Equivalently: `c ≤ 0.177` when `ω = 0`, or
`ω ≤ 0.146` when `c = 0`. (Using gate 4's "~43 trading days" the budget is 4.30,
`c ≤ 0.174`, `ω ≤ 0.144`.)

**That budget is easily exceeded by ordinary trade arrival alone.** Under a
Poisson process at exactly the ceiling, `mean_overlap_fraction = 0.213` and
`rho_h = 5.90` — which **exceeds the whole 4.36 budget on its own**, giving
`N_eff = 296 < 400` even at zero cross-pair correlation. So a 2-month holdout at
the ceiling is infeasible under Poisson arrivals **at any correlation whatever**.

This is gate 4's already-recorded "intentionally demanding but narrow" corridor,
quantified.

### 0.4 Three corrections to earlier, more confident versions of this derivation

**(a) The turnover ceiling does not force `rho_h = 1`.** An earlier draft argued
that ≤ 40 trades/day over 20 pairs gives a mean same-pair gap of 48 bars against a
24-bar horizon, so `rho_h = 1` exactly. That computes `φ(mean gap)`; the spec asks
for the **mean of the overlap fraction** "estimated per pair from the realised
inter-event gaps". `φ` is convex, so by Jensen `E[φ(g)] ≥ φ(E[g])` — the mean-gap
argument bounds the mean overlap only from **below**, and that bound is vacuous
whenever the mean gap exceeds the horizon. `rho_h = 1` holds **iff no same-pair
trade ever fires within 6 hours of the previous one**, which is a claim about the
realised process, not a consequence of a rate ceiling. **Withdrawn.**

**(b) The ceiling is a holdout *mean*, so it bounds `rho_h` not at all.**
`turnover()` is `n_trades / n_trading_days` (`metrics.py:120`) — a portfolio
average over the span, not a per-day cap. A mean-only constraint admits arbitrary
clustering: `sup rho_h = 24`. Two trades an hour apart on one pair inside a London
session is not exotic and yields `rho_h ≈ 10.6` at exactly the frozen ceiling.

**(c) The concentration cap admits far worse than one hot pair, and accrual is
not monotone in concentration.** `≤ 0.40` bounds the *largest* pair's share, so
several pairs may sit near it. Under regular arrivals: one pair at 16/day with the
other 19 at 1.26/day accrues `Σ N_eff_pair = 24.9/day` — but **three pairs at
13.33/day each (share 0.333, equally legal) accrue 2.34/day**, roughly 10× worse,
because every active pair crosses the overlap threshold at once. An internal
review put this corner at ~4.3 years by applying `P = 20` to a three-pair
allocation; `P` is the *contributing* count, so recomputed consistently it is
~1.1 years. **Neither the 24.9/day figure nor the 4.3-year figure is adopted.**

### 0.5 The "3.3 years" figure — and why rejecting it was wrong

The figure appears **nowhere** in the repository: `3.3 year`, `33,500` and
`838 trading` return zero hits across `docs/`, `artifacts/` and `scripts/`.

Its arithmetic reproduces exactly: `ω = 0.5 → rho_h = 12.5`, `c = 0.3 → rho_x =
6.7`, `400 × 12.5 × 6.7 = 33,500` trades, `÷ 40/day = 838` weekday days ≈ 3.32
years.

An earlier version of this section **rejected** it on the ground that `ω = 0.5`
requires 8 trades/pair/day — 160/day portfolio-wide, four times the ceiling.
**That rejection was wrong, and the reason matters more than the figure.** It
holds only under regular arrivals. At exactly the frozen ceiling, `ω = 0.5` is
reached by one clustered doublet per pair per day — and, decisively, it is what
**the pre-registration's own draft estimator** yields. Prereg §9:

> Draft estimator (for the design audit to fix): block-adjust by horizon (events
> per pair thinned by **mean overlap factor ≈ horizon/mean inter-event gap**)

At the ceiling that is `24/48 = 0.5`, hence `rho_h = 12.5` — the inherited premise
exactly. **So the 3.3-year figure is the frozen turnover ceiling fed through a
committed formula, not an out-of-contract assumption.** — **HISTORICAL; WITHDRAWN at §8.4.3
and in the paragraph below**: `24/48` is the draft's *divisor*, not an `ω`, so this
is a unit-type splice rather than either committed formula. The figure survives as
reachable by **clustering**, not by this route.

The APPROVED spec supersedes the draft under T-6, and the spec's arithmetic is
what `INSUFFICIENT_SAMPLE` is computed from. But **the two committed formulas
disagree by 12.5× in `rho_h` at the frozen ceiling**, and an earlier version of
this section resolved that disagreement silently, in the direction that makes the
family look feasible. The divergence is recorded here as an open item, not
resolved: `DRAFT_AND_APPROVED_OVERLAP_ESTIMATORS_DIVERGE_AT_THE_FROZEN_CEILING`.

**Corrected at §8.4.3 — read that with this.** Taking each formulation on its own
terms, the ceiling relationship is **undetermined, not agreed**: under §8.4.3's
clamped-divisor repair the two read `1.00` and `1.00` at a 48-bar mean gap, under the
multiplier repair `1.00` against `2.00`, and **which repair applies is unruled**. An
intermediate reading that said the two "agree" at the ceiling is **withdrawn at
§8.4.3** — it rested on a clamp that packet supplied rather than on the prereg, and
it errs toward feasibility, since `rho_h = 1.00` at the ceiling frees the entire 4.36
budget for `c`. Inside the horizon they diverge by up to ~6.25× under the
clamped-divisor repair. The `12.5`
above came from feeding the draft's *divisor* into the spec's *fraction* slot, which
is a unit-type splice rather than either committed formula — the draft's quantity is
a thinning **factor** whose value exceeds 1 in the overlapping regime, and
`_require_unit_fraction` refuses anything above 1. **That leg is withdrawn.** The
clustering leg of this subsection stands: `ω = 0.5` is reachable at exactly the
ceiling by clustered arrivals (§0.4(b)), so the earlier rejection of the 3.3-year
figure was still wrong, for that reason and not this one. The figure remains **not
adopted**, and §0.4(a)'s Jensen withdrawal is unaffected. The token is superseded by
`DRAFT_AND_APPROVED_OVERLAP_FORMULATIONS_ARE_DIFFERENT_OBJECTS_AND_DIVERGE_INSIDE_THE_HORIZON`.

### 0.6 Two estimator routes that raise `N_eff` without breaking any rule

Both go **around** `effective_n()`, not through it — its internal hardening
(`count_quantity` pinning, per-pair rather than scalar-collapsed computation,
canonical pair identity, the frozen-horizon check) is real, and I found no way
past any of it.

**(a) `P` is caller-supplied, and a smaller universe is *faster* to the floors.**
The spec says `P = number of pairs **contributing**`; `effective_n.py:280` takes
`n_pairs = len(records)` with only an upper bound. Under a fixed portfolio
turnover budget the numerator is capped at 40/day regardless of how many pairs
share it, while `rho_x = 1 + (P−1)·c` falls as `P` falls. At the ceiling and
corr 0.3, with every pair below the overlap threshold:

| `P` | rate/pair | `rho_x` | `N_eff`/day | weekday days to the floors |
| --- | --- | --- | --- | --- |
| 20 | 2.00 | 6.70 | 5.97 | 67 |
| 12 | 3.33 | 4.30 | 9.30 | 43 |
| **10** | **4.00** | **3.70** | **10.81** | **37** |
| 9 | 4.44 | 3.40 | 3.57 | 112 |
| 5 | 8.00 | 2.20 | 1.45 | 275 |

**This route is now ruled shut** — §8.3.0 fixes `P` at the frozen registered
universe, so the table below is **historical arithmetic showing why the ruling was
needed**, not a live route. Read with that: **the fastest route to the sample floors
*through the estimator* was ten contributing pairs, not twenty** — 45% off the required span, at a 0.100 share,
far inside the 0.40 cap — until `P = 9` pushes each pair over the 4/day overlap
threshold and the gain reverses sharply. **The contract offers no such route:**
Ruling 2 / R-2a fix the universe at PAIRS_20, and prereg §3.2's
**R-2a-compliance clause** bars "inclusion/exclusion decisions anywhere in this
family" — §8.3.5 ground G records why the family-wide bar rests on that clause and
not on R-2a's own text, which reaches only design time. NR-K is therefore a defect in the
**estimator's caller contract**, not a permitted pair-universe remedy, and it must
not be merged with the duration limb (§8.1.9). Separately, a pair that fired no trades adds nothing to the numerator
while raising `rho_x`, so simply *omitting* it is a free gain. Nothing pins `P`
to `PAIRS_20`, and nothing ties the `P` used for `rho_x` to the pair set the
concentration cap is computed over.

**(b) `mean_abs_pairwise_corr` has no production rule and no defined freeze
point.** The spec fixes the symbol and the span and nothing else — not which
strategy's PnL, not whether idle pair-days enter the series, not the correlation
method, not entry- versus exit-day attribution (the same ambiguity Q10(i) recorded
for the Sharpe series, on the same daily series — **now ruled, §8.5.0**), not the
minimum observations behind the estimate. The same artifact asserts
`no_strategy_metrics_computed_at_gate3a: true` while defining the quantity on
per-pair **daily PnL**, which is a strategy metric — so the freeze point is
undefined and whoever computes it first sets it. And a daily correlation is the
wrong resolution for a 6-hour horizon: at the projected ~0.56 trades/pair/day most
pair-days are idle, and idle days pull `|corr|` toward zero, so the estimator
**understates dependence most in exactly the sparse regime this family expects**.
`PAIRS_20` also draws 40 currency legs from 8 currencies, so 88 of its 190
pair-pairs share a leg and a single scalar mean cannot carry that block structure.

Two referrals follow, in the playbook's register format:

| Referral | Disposition | Basis |
| --- | --- | --- |
| **NR-K** — `P` in `rho_x` is caller-controlled and is not pinned to `PAIRS_20` | **RULED** (§8.3.0) — `NR_K_RULED_P_EQUALS_FROZEN_REGISTERED_FAMILY_A_UNIVERSE`; `P = 20` for current Family A. The **implementation pin** and the forward-span roster gate remain open | Omitting zero-trade or tail pairs raises `N_eff` at no numerator cost and can flip the verdict with both the raw floor and the 0.40 cap satisfied — which is what the ruling forbids |
| **NR-L** — `mean_abs_pairwise_corr` has no production rule and no freeze point | **RULED** (§8.5.0, bundled with Q10(i)) — `NR_L_MINIMUM_RESEARCH_CONTRACT_RULED_PENDING_IMPLEMENTATION_AND_DESIGN_MEASUREMENT`; `MUST_RESOLVE_BEFORE_ANY_EFFECTIVE_N_VERDICT` **discharged as to the contract, not as to the value** | Method, idle-day handling, day attribution and the freeze gate were all unpinned, and the value sits in the denominator that decides `INSUFFICIENT_SAMPLE`. Minimum observations is now answered by construction — c-6 puts every pair on the same 310-date index, so `n = 310` for every entry. The producing-configuration blocker that survived the first ruling is **closed by Ruling c-10**: `c_design` is computed for **every** registered candidate configuration before validation, the map is frozen, and validation selects a `config_id` only. The two blockers that survived it — `C_DESIGN_SPAN_RUN_IN_SAMPLE_STATUS_NOT_REGISTERED` and `C_MAP_INPUT_FREEZE_CONFLICTS_WITH_T6_HOLIDAY_CALENDAR_SCHEDULE` — are **closed by §8.7** (c-11, c-12), and **`CLOSURE_CLAIM_WITHHELD_PENDING_A_SEPARATE_INDEPENDENT_ROUND`** — the claim was attempted a **third** time at §8.7.6 and grounded on a review section that did not yet exist; it is withheld, and the rule that follows is **`CLOSURE_CLAIM_REQUIRES_COMPLETED_REVIEW_AND_NO_UNRESOLVED_MATERIAL_BLOCKER`** (§8.8.0 — the earlier same-round prohibition is **withdrawn as over-broad**) |

Accordingly §12's earlier remark that "`rho_x` already carries the dependence the
edge question needs" is **withdrawn as unestablished**.

### 0.7 Verdict

**`SAMPLE_FLOOR_REACHABILITY_NOT_DETERMINABLE_WITHOUT_MEASURED_INPUTS`.** Of the
three dispositions this exercise could return, the answer is the third — and
**neither** of the other two is provable.

- **`STRUCTURALLY_INFEASIBLE` is not established.** A proof would need a
  committed lower bound on `mean_abs_pairwise_corr` and on `mean_overlap_fraction`
  — no committed source supplies either — and a committed **maximum** holdout span
  to rule a required duration out, where only a minimum exists. That is the whole
  of the argument. It is **not** a claim that a required duration is reachable:
  "adoption waits" fixes *when* adoption may happen, not that accrual continues or
  that the programme waits. Family A survives on zero-data grounds because
  infeasibility is unproven, not because a long enough holdout is available.
- **`STRUCTURALLY_FEASIBLE` is not established either, and this packet does not
  assert it.** What is established is narrower: the frozen criteria set is **not
  self-contradictory** — a non-empty satisfying region exists. That is a fact
  about the criteria, not about M15.
- **Three inputs are empirical, not two**, and an earlier version of this section
  declared the first of them settled at 1.00, which is the error the rest
  inherited: `mean_overlap_fraction`, `mean_abs_pairwise_corr`, and the realised
  event rate at each registered `ev_min`.
- **Missing authorities, named:** `EVENT_RATE_NOT_COMMITTED` ·
  `MEAN_OVERLAP_FRACTION_NOT_FROZEN_AND_ROLE_MEASURED` — **superseded at §8.4.2**,
  which records that nothing computes `ω` at all today, so "role-measured" overstates
  it ·
  `MEAN_OVERLAP_FRACTION_UNIT_NOT_REGISTERED` (§8.4) ·
  `MEAN_ABS_PAIRWISE_CORR_NOT_YET_ESTIMATED_DESIGN_DATA_ONLY` ·
  `DRAFT_AND_APPROVED_OVERLAP_FORMULATIONS_ARE_DIFFERENT_OBJECTS_AND_DIVERGE_INSIDE_THE_HORIZON`
  (§8.4.3, superseding the earlier at-the-ceiling token) · NR-L. **NR-K is no
  longer among them** — it is ruled at §8.3.0 — but the verdict is unchanged by
  that: `P` was never the term this verdict turned on, and the three empirical
  inputs are still empirical.

**So this calculation does not moot Q1 or Q3.** An honest grid spans roughly 25
weekday days to over a decade, and a range that wide decides nothing. The hope
recorded earlier in this packet — that the zero-data calculation might be
"decisive" and make the real-data questions unnecessary — is **withdrawn**.

**What it does establish is worth keeping, and it runs the other way.** It refutes
the *reverse* claim, that the floors are comfortably reachable at the frozen
minimum: §0.3's budget is 4.36 and an ordinary Poisson arrival process spends 5.90
on its own, and at the prereg's own projected ~11/day the **raw** floor alone needs
≈4.1 months before any deflator is applied. **The frozen 2-month minimum is very
likely the wrong span** — which is what gate 4 said, and why it **non-bindingly
preferred** that gate 3a size the holdout generously (its own label: "Feasibility
note (non-binding)", absent from T-1…T-7). And it converts the open question into the one a
human can actually rule on: *for each corner of the grid, what forward-accrual
date does `T_h` imply?* The committed record already places the earliest feasible
forward adoption at ≈ 2026-10 on a ~5-month requirement, so a central case of
~11 months of holdout puts `T_h` in mid-2027, and a 2.4-year holdout puts it near
the end of 2028. A long holdout is permitted; it is simply not free, and the price
is calendar time this packet should quote rather than elide.

**And what it cannot address at all.** The floors count **events, not
information**: at `ev_min = 0.0` a trade with `EV = +0.001` pip clears them
exactly as one with `EV = +2` pips does, and neither the spec nor `effective_n()`
weights by signal. "The frozen floors are reachable" is therefore not "the design
can detect an edge", and §7's R5 rule — "`failed` may not be returned on a sample
the design could not have detected an edge in" — reaches for a power calculation
the `N_eff` floors do not supply. Nothing here bears on whether an edge exists, in
either direction.

**This re-derives a committed note, it does not discover a constraint.** Gate 4
already computed the same corridor and already ruled on it: "with turnover ≤
40/day and ≥ 1,000 holdout trades, a 2-month holdout (~43 trading days) gives a
feasible corridor of [1,000 … ~1,720] trades — intentionally demanding but
narrow. **Gate 3a should prefer a holdout longer than the 2-month minimum when
accrued data allows**", and "a false rejection into `INSUFFICIENT_SAMPLE` is
**recoverable by adopting more forward data — acceptable by design**".

**Two scope caveats on every duration here.** They are **holdout-only**: prereg
§3.1 requires validation ≥ 3 months ahead of the holdout and §3.2 an embargo of ≥
25 M15 bars at the boundary, so the forward-epoch calendar requirement is
`3 months + embargo + D`, against an earliest feasible adoption of ≈ 2026-10. And
they price only the **holdout** leg: the spec's validation limb refers to "the
family's minimum" with no antecedent, and `effective_n.py` fails closed to
`NOT_EVALUATED_AT_THIS_ROLE` rather than inheriting the holdout floor. If a
validation floor is ever set at parity the requirement roughly doubles. That is an
open Ruling-11 referral, not a gap this derivation may fill.

### 0.8 What a negative result could and could not mean

Stated **in advance**, so a finding cannot later be read as an argument for
relaxation.

**It could not close Family A.** Prereg §1 closes the family on sample grounds
only for an `INSUFFICIENT_SAMPLE` "**that cannot be remedied by the registered
data plan**" — but that clause sits under the heading "**What closes the family
before any holdout touch**", so it governs a *pre-holdout* verdict only, and "the
registered data plan" is undefined (§8.1.4). An earlier version of this sentence
said "the registered plan *contains* the remedy"; that is **withdrawn** as
unsupported. On a holdout-role verdict the contract is simply silent — it neither
closes family A nor keeps it open. Demonstrating
unreachability at the frozen minimum establishes that **the minimum is the wrong
span**, not that no admissible span exists. Irremediability would require showing
that no holdout length reachable by forward accrual clears the floors — a far
stronger claim this arithmetic does not attempt. A family disposition is never
self-granted in any case.

**The admissible responses are exactly two, and Ruling C (§8.1.0) has since
narrowed the first of them:** a holdout longer than the frozen minimum —
admissible **only as a pre-freeze sizing choice at the forward-epoch adoption
continuation, never as a response to a measured result**, and in any case a
preference gate 4 recorded **non-bindingly**, outside its T-list, which the frozen
pre-registration does not express at all; or a human + ChatGPT ruling on Family
A's continuation or scope. **Lowering the raw or effective-N floors, and raising
the ≤ 40/day ceiling, are not among them** — Ruling 10 forbids loosening, and the
ceiling was considered and settled by gate 4, which recorded that it "is a budget,
**not a target**".

**And infeasibility may not be demonstrated by assuming operation at the
minimum.** Ruling 2 fixes a floor, not a duration, and `T_h` is `[FIXED-AT gate-3a
continuation]`. Every quantity computed at 43.6 weekday days in §0 and in Q11 is a
**conditional arithmetic identity at the floor**, never a property of the holdout
family A will actually be evaluated on. A minimum is a budget, not a target — in
the same sense, and for the same reason, as the ≤ 40/day ceiling.

**Feasibility may not be demonstrated by assuming operation at the ceiling.**
Every rate here is a conditional arithmetic identity, never a design target — and
the ceiling is an outcome, not a dial: Ruling 9 selects the operating point by
validation net expectancy subject to the budget, so nothing pushes the rate toward
40/day.

**And a reachable result authorises nothing.** It does not discharge Q1 or Q3,
does not permit a real-data read, does not shorten the forward-epoch WAIT or the
≈ 2026-10 earliest-accrual record, and does not discharge
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`. The symmetry is
deliberate: an unstated positive branch is where "feasible" gets read as
"proceed".

**`INSUFFICIENT_SAMPLE` is reserved and is not emitted here.** It is a *measured*
verdict of `effective_n()` at `role ∈ {validation, holdout}`; §4 R-9 and §6
reserve it, and a zero-data derivation cannot produce one. No token proposed by
this section contains it, `FAILED`, or `FAMILY_A`.

**Duration is not a free variable either.** Because "adopt more forward data" is a
pre-blessed remedy, "we need a longer holdout" could otherwise be invoked after
seeing a short one fail — a power calculation performed after the result, which
R-1 names as the failure mode. So: the span is **fixed at forward-epoch adoption,
before any validation or holdout computation**, together with the (rate, overlap,
correlation) assumption used to size it; prereg §3.2 already bars in-flight
extension, since the holdout is consumed "upon any decision-bearing observation of
it"; and re-running this grid after any real-data observation is a **post-hoc
power calculation**, recordable as a diagnostic and referable, never citable as
authority to extend.

**Conditionality disclosed.** Durations are in weekday UTC days — a convention
Q10 refers back as unfixed — and the arrival processes named here (regular,
Poisson, clustered doublet) are **modelling references, not committed authority**.
The "~43 trading days" figure is gate 4's. The 96-buckets/day figure is an
arithmetic ceiling, not an eligible-slot count: Ruling 4's rollover exclusion
removes at least two buckets and the holiday calendar is `[FIXED-AT design audit]`
and unfixed. No expected slot set is inferred from data or a self-generated rule
(§4 R-3).

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
| Blocked by | PR #450 §10's seven dependencies | §3's boundaries, §4's integrity requirements, the frozen frame in §2, policy §6 Red approval per stage, and PR #450 §10 rows **F** and **G**, which block a real read on either route |

**This gate is `READ_ONLY_RESEARCH_EXPLORATION_GATE`.** It is not a production
readiness gate, not a live-trading gate, not an evidence-promotion gate, and not
a substitute for the formal Gate-3a continuation. The token names **data access**;
R3 is a training run and R4 an evaluation, and neither is read-only in this
repository's sense (§7).

**PR #450 §2.2 binds this document by name:** "**A Minimum Research Gate is not a
lighter alternative to a Contract Gate-decision and confers no authority of its
own.**" Nothing here is lighter than a Contract Gate-decision — this *is* one, and
it confers only what a human + ChatGPT ruling on it confers.

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
| trade count lower bound | ≥ 1,000 holdout trades **and** effective-N ≥ 400, else `INSUFFICIENT_SAMPLE` |
| daily coverage | ≥ 0.60 |
| turnover upper bound | ≤ 40 trades/day portfolio-wide |
| pair trade concentration | ≤ 0.40 |
| pair positive-PnL concentration | ≤ 0.50 |
| class-frequency sanity | recorded; defect trigger only, not a standalone pass/fail gate |
| concurrency/exposure | recorded; caps **[FIXED-AT design audit]**, before implementation |

All twelve rows are reproduced. The last two are recorded-only items rather than
pass/fail gates, and are carried so this quotation cannot be read as the table
minus what did not suit it.

Plus the **validation kill gate**: net expectancy > 0 **and** gross ≥ 1.5 × cost
at ≥ 1 registered `ev_min` point, within the turnover budget; all-fail closes the
family with no holdout consumed. `N_EFF_HOLDOUT_FLOOR = 400` and
`RAW_HOLDOUT_TRADE_FLOOR = 1000` are in source at
`scripts/m15_gate3a/effective_n.py`.

**`Ruling 10` forbids loosening these.** This gate does not restate them as its
own criteria, does not soften them, and does not apply them to exploratory
results — see §6.

**The cost model's structure is committed; its numbers are not.**
`all_in_cost = median_spread(pair, session) + pad_exec + cell_slippage`, with
**`pad_exec = 0.3 pip`** and **`cell_slippage = 0.5 pip` (primary)** — both frozen
by Ruling 5, and the whole model scoped by Ruling 5 as a **quote-cost-validity
research claim, not a live-fill claim** (prereg §5). Omitting `pad_exec`'s value
understates modelled cost by a third, in a gate whose R-5 exists to prevent
exactly that.

**But the per-pair × session spread tables do not exist.**
`artifacts/m15_gate3a/cost_table_plan_or_metadata.json` records
`option_selected: "B__DEFER_COST_TABLE_PRODUCTION_TO_IMPLEMENTATION"`, and T-6
re-points their production to gate 3a or the implementation PR, from design-span
data only, with mandatory human approval. So "under the committed cost model" is
not a lookup — the tables must be estimated first, under Q5 and subject to R-10.
**A zero-cost result is not admissible as a primary finding anywhere in this
programme.**

**The design audit tightened, and the tightenings bind.** §9 is headed "FROZEN;
design audit **may only tighten**" — and gate 4 did tighten. PR #430 imposed
**T-1…T-7**, recorded in the playbook as "Gate 4 — Fable 5 design audit
(PR #430, tightenings T-1…T-7) | ✅ accepted for gate 3a". Four reach this gate
directly:

- **T-1** — dead-window data is **never loaded**, for any purpose, including
  indicator warm-up.
- **T-3** — if the **median eligible barrier/cost ratio on design data is < 3.0**,
  execution authorisation (gate 7) is **BLOCKED** pending a new human + ChatGPT
  ruling. Verbatim: "M15 must demonstrably escape the M1 cost regime before
  anything runs." This is measured **on design data**, needs **no model**, and is
  the direct test of the stated reason for preferring M15 to M1 — so it belongs
  in R1, not after a model exists (§7).
- **T-4** — timeout share is mandatory evidence, with a > 60% investigation trigger.
- **T-5** — max drawdown is measured against a **10,000-pip fixed notional**.

**T-6** re-points the cost tables and the effective-N estimator with mandatory
human approval; **T-7** requires the ts-bound / no-overlap proof in the gate-3a
artifacts.

**Other frozen frame:** `PAIRS_20`; M15; horizon frozen at **24 bars** (Ruling 6);
purge/embargo **≥ 25 M15 bars** at every role boundary; the dead window
2026-03-01 → 2026-04-24 excluded from every role.

**The M1 precedent is committed, and it is narrower than a prior.** The `365d_BA`
M1 flagship returned a valid `DOES_NOT_MEET`: expectancy **−3.49 pips/trade** at
the 0.5-pip cell, **−2.99** with the cell removed (spread stays embedded in the
bid/ask labels, so −2.99 is not a zero-cost figure), **20 of 20 pairs negative**.

Its reach is stated in the committed post-run audit: "**Does PR #425 prove all
possible M1 strategies cannot work? No.**" and "Is M1 structurally disadvantaged
**for this architecture and data**? Yes." The prereg localises the failure to four
mechanisms — barriers a few pips wide with embedded spread consuming them,
~20-minute timeouts, 168 trades/day, and feature information content — and **the
M15 design changes all four**. The prereg accordingly frames the M15 hypothesis as
one "under test (not an expectation)".

**So the honest position is equipoise, not a negative prior.** An earlier draft of
this packet asserted that M15 was chosen because "M1's spread/ATR ratio made a
short-horizon edge structurally implausible" and that "the prior is that there is
no edge". Neither is committed: the spread/ATR framing traces to Phase 23
material classified `REQUIRES_SEPARATE_EVIDENCE_RECONCILIATION`, which **C-8
(Ruling 13) bars from this family's priors** by name, and the post-audit refuses
the generality. Both claims are withdrawn.

**This matters in a specific direction.** A negative prior plus an undefined
`failed` verdict (§7) plus §6's consequence for `failed` is a route by which an
underpowered exploratory negative closes a programme. The first admissible
measurement that moves equipoise is **T-3's median eligible barrier/cost ratio on
design data**, which needs no model and no prior — which is the case for running
this gate cheaply rather than confirming a belief expensively.

---

## 3. Mandatory safety boundaries

These bind every stage. They are not negotiable by a Work PR.

### 3.1 Broker

**Forbidden:** live order · demo order · any broker write · position
modification · account action. **The research phase requires no broker connection
at all**, and none may be opened.

Price data comes from a local read-only source — but **no such source is approved
yet** (Q3), so this sentence constrains a future ruling rather than describing the
present state. Any reader used at R1–R4 is a **new byte-reading capability** over
`data/`: `scripts/m15_gate3a/**` is contract-bound reader-free (§12.14, pinned by
`tests/m15_gate3a/test_wp5_reader_freedom.py`), and `guards.py`'s
`_PROTECTED_PREFIXES` names `data` and `models` as trees that package may never
target. PR #450 §10 rules its deferrals are not preconditions for this gate, but
its row **E** defers the P/V reader because a new read capability "needs its own
audit". Whether that reasoning reaches the exploratory reader is part of Q3.

### 3.2 Database

**Forbidden: any database access.** No DB write, no schema mutation, no
`INSERT`/`UPDATE`/`DELETE`, no migration, and no external DB dependency for
research execution. "Preferred path" was the wrong register for a section headed
*not negotiable*.

A read-only exception is not available under this gate. If one is ever required it
needs **explicit separate human authorisation**, a read-only **role** — not merely
a read-only transaction, which is per-statement-scoped and is exactly the
named-route defence this subsection warns against — and no credential display. This is a
live risk in this repository, not a hypothetical: an unscoped `pytest tests/` once
wrote to a live local database because `.env` loaded at import, and PR #446
established that **presence of a credential is not authorisation to use it**.

**Two limits on that fix bind this gate, and an earlier draft of this packet
overstated it.** The claim that "route-independent enforcement (a
`sys.addaudithook` on `open`) is what actually holds" is **withdrawn as false**.
First, the guards live in `tests/conftest.py` and install at conftest import, so
they hold for a **pytest session only** — a research run is `python scripts/…`,
which they never see. Second, the `.env` guard is **not** route-independent:
`tests/conftest.py:253` prefilters with a case-sensitive `endswith(".env")` and
`:255` compares an `abspath` that strips neither trailing dots nor spaces, so
`.ENV`, `.Env`, `.env.` and `.env ` each read the file in full even inside a
guarded session — on Windows, where this repository runs, all four name the same
file. That is **FR-19(a)**, recorded by the fourth re-check and **deferred** by
PR #450 §10 row D; FR-19(b) records that the socket guard binds only
`connect`/`connect_ex`, leaving `send`, `sendall`, `sendto`, `getaddrinfo` and
`gethostbyname` — and the C base `_socket.socket.connect` — unguarded, so §3.3's
DNS clause has nothing behind it either.

**This gate therefore inherits no working `.env` defence and no working network
defence**, and must supply its own (§3.5).

### 3.3 Network

During research execution: **no arbitrary network, no DNS, no storage upload, no
external telemetry, no webhook, no Slack or email.** Any dataset must be prepared
locally and read-only beforehand.

### 3.4 Credentials

A research run **may not read `.env`**, may not read any credential-shaped
environment variable, and **may not test for the presence of one**. No stage needs
a broker or database credential, and none may be displayed, logged or written to
an artifact.

The word *normal* is deliberately absent from this rule. The run that caused the
recorded incident **was** a normal run — `pytest tests/`, no flags — and the
credential reached it at import time, without anyone classifying it as unusual.
The presence check is named because `_gate_p1_inspector/guards/credentials.py`
already blocks it: a run that can ask whether `OANDA_ACCESS_TOKEN` exists can
branch on it without ever displaying it.

### 3.5 What enforces §3.1–§3.4

§3.1–§3.4 are prohibitions on a **process**, and every guard this repository owns
installs in a **pytest session**. `sys.addaudithook` appears in exactly one
non-vendored file in the tree (`tests/conftest.py:264`); there is no
`sitecustomize.py`. A research run of the shape this repository already uses —
`python scripts/compare_multipair_v23_realism.py`, reading `data/*.jsonl` directly
and writing logs under `artifacts/` — is bound by nothing.

**Normative.** No stage R1–R4 runs outside a fail-closed guarded envelope, and a
guard violation is a **HALT**, not a logged warning. This is not new work and not
production hardening: `scripts/_gate_p1_inspector/guards/` is merged and was built
for exactly this — a read-only research inspection outside pytest — with network,
subprocess, credential (including presence-check), filesystem write-allowlist,
`python -B` and `sys.meta_path` import guards, driven by
`scripts/gate_p1_pr_b_launcher.py` with an outer/inner topology and a scrubbed
environment. The second precedent is `scripts/ml_step4/executor.py`'s
`guarded_execute`, which refuses any non-dry-run call and is what made "no
execution" *true* rather than promised for the programme's only completed research
gate. The implementation Work PR reuses that shape, or states why each guard is
unnecessary here.

**Subprocess spawning is named explicitly**, because it is the generic bypass for
every in-process guard and child interpreters inherit none of them. **Runtime
package installation is forbidden**: `uv sync` against the stale lock is
destructive, and the playbook already bars any Red operation that presumes a
frozen uv environment.

### 3.6 Data recency, and consumed data

Two hard date boundaries, derived rather than invented.

**No stage may read, aggregate, plot, summarise or otherwise observe any bar
timestamped at or after 2026-03-01.** The prereg makes 2026-03-01 → 2026-04-24 a
dead window "excluded from every role at every timeframe", and puts validation on
a forward epoch starting no earlier than 2026-04-25 whose boundaries `T_v`/`T_h`
are `[FIXED-AT gate 3a]` and not yet fixed. §7's instruction that R4 "must not …
approach the frozen holdout" **cannot be obeyed** by a researcher, because the
holdout's edges do not exist yet; a fixed date can be. The committed archive
snapshot (`artifacts/oanda_archive_2026-05-31/`, 3650 days) already contains
forward-epoch bars, so this is an access rule, not a hypothetical. Observing them
would be a decision-bearing observation of a holdout that has not been adopted.

**The dead window is the consumed `365d_BA` M1 holdout**, and exclusion reaches
**feature warm-up and every lookback**, not only labels (T-1; playbook §6). Every
span declared under this gate passes `scripts/m15_gate3a/no_overlap.assert_design_bounds`
and `assert_no_dead_window` — already committed, reader-free, fail-closed, and
usable today. `DEAD_START` is exactly one second after `DESIGN_END`, so a `<=`/`<`
slip pulls consumed-holdout bars into exploratory training; that is why the check
is a call, not a promise.

### 3.7 Writes

A research run writes only beneath a **single named research-scratch root**, and
creates nothing elsewhere. It may not write under `artifacts/m15_gate3a/`,
`artifacts/ml_step4/365d_ba_v1/`, `artifacts/gate_p1_pr_b/`, `data/`, `models/` or
`docs/`.

Neither existing protection reaches a research process: `tests/conftest.py`'s
`PROTECTED_TRACKED_ARTIFACTS` teardown hash is pytest-only, and
`scripts/m15_gate3a/guards.py::refuse_real_path` is routed from a single call
site — that module's own docstring states that containment of an *unrouted* caller
"is not a property this module has, and must not be cited as one." A research
runner is by definition an unrouted caller.

---

## 4. Minimum research-integrity requirements

Each is here because **its absence would materially mislead the conclusion**, not
because production wants it. §5 states that test explicitly.

**R-1 Frozen research question, registered before results are seen.** Target
pairs · timeframe M15 · label definition · prediction horizon · evaluation
evaluation periods · transaction-cost model · primary metrics · stop criteria.

**Where a frozen value already exists, the registration adopts it unchanged** —
pairs (Ruling 2), horizon and label geometry (Ruling 6), feature policy
(Ruling 7), model family, hyperparameters and calibration (Ruling 8), the `ev_min`
grid (Ruling 9), the cost model (Ruling 5). It may tighten; it may not loosen,
substitute or re-derive, and any departure is a **contract amendment requiring a
human + ChatGPT ruling**, not a registration.

**Correction to an earlier draft.** This requirement previously cited "the ML
Step 4 corrected-run precedent" as the recorded instance of registering after
seeing results. That is backwards: the corrected run is the **counter-example** —
"no tuning and no feedback loop", and the post-audit answers "Was there any tuning
after seeing results? **No**". It is the model of how a re-measurement is done
correctly, and the prereg carries its ceremony verbatim as the invalid-run rule.

**R-2 Split discipline, and the exploratory out-of-sample slice.** **No holdout
exists under this gate** (§7), so the vocabulary is fixed: the tested slice is the
**`EXPLORATORY_OOS_SLICE`**, and the words *holdout*, *validation* and
*out-of-sample evidence* stay reserved to the forward-epoch evaluation (§6).
Calling the exploratory slice "the holdout" is how a scratch number acquires an
evidence name.

- **Chronological only** — the final contiguous portion of the design span, the M1
  precedent's shape. No random split, no shuffled k-fold, no group-shuffle
  anywhere, including any internal early-stopping split.
- **Quarantined from R1 onward.** The boundary is chosen and recorded **before
  stage R1**, and no stage before R4 may read, describe, plot or compute a
  statistic over it — descriptive statistics included.
- **Purge counted in bars, never wall-clock.** ≥ 25 M15 bars (`horizon + 1`) of
  the design span immediately preceding the slice are dropped from training. A
  Friday-afternoon signal bar's 24-bar label reaches into Monday, so a 6h15m
  elapsed-time purge would not purge it. Note this is an **extension**: the frozen
  25 attaches to *role* boundaries, and an intra-span split is a new boundary
  type. Extending it is a tightening and therefore permitted.
- **A trailing edge needs a different, larger number.** If any design puts
  training data *after* a tested slice — walk-forward, rolling origin, repeated
  split — the trailing gap must be ≥ the **longest feature lookback in bars**, not
  `horizon + 1`. Prereg §7 permits H1/H4 completed-bar context, and an ATR-14 on
  H4 reaches 224 M15 bars. The single chronological cut above has no trailing edge
  and is the simplest conforming choice.
- **No statistic may straddle the slice.** Everything fitted is fitted on the
  training portion only and frozen before the slice is read: the per-pair/session
  spread tables, `W̄`/`L̄`, the isotonic calibration (prereg §8: "carved from the
  training span only"), and any scaler or pair encoding. **This is the subtlest
  leakage route in the whole gate**, because the labels themselves depend on cost —
  `TP_dist = max(1.5×ATR, 3.0×cost)`, `SL_dist = max(1.0×ATR, 2.0×cost)`, and the
  eligibility hurdle `1.5×ATR ≥ 2.0×cost` (Ruling 6). A cost table fitted over the
  whole design span means **the labels inside the slice were constructed using the
  slice**. That is target leakage in the strict sense and it is invisible to every
  acausal check. The prereg's "estimated on design data and frozen" was written
  when the whole design span was training; carving a slice out of it turns that
  phrase into a contamination instruction.
- **One split timestamp for all pairs**, since `rho_x` already records that the
  pairs are correlated.
- **Nothing changes after the slice is read** — no feature, threshold, model, cost
  assumption or pair set.

**R-3 M15 aggregation correctness**, on synthetic and reference cases: timestamp
ordering · bucket boundary · OHLC aggregation · duplicate handling ·
missing/rejected observation handling · timezone and epoch binding. Event and
label eligibility requires **`n_source_bars == 15`**, with incomplete buckets
diagnostics-only and **no imputation** (Ruling 3) — partial-bin handling is one of
the recorded defect classes in R-4, so the rule that prevents it belongs here.

**Full production calendar-provenance machinery is not required here** — it is
provenance for evidence authority, not correctness of a conclusion. But the
six-field vocabulary cannot simply be borrowed: **three of PR #444 §5's six
quantities are defined against the approved calendar artifact**, which does not
exist (`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`), and PR #448's
D-5.8 forbids inventing the expected slot set from observed data or a
self-generated rule. So under this gate only `observed_source_minute_count`,
`rejected_source_minute_count` and `usable_source_minute_count` are computable;
`expected_source_minute_count`, `absent_source_minute_count` and
`max_unavailable_gap_minutes` are reported as
`NOT_COMPUTABLE_WITHOUT_APPROVED_CALENDAR` and **never estimated**.

The three computable counts are reported **per pair × session × month**, because
eligibility requires a complete bucket and non-uniform missingness therefore thins
the event set non-randomly and biases the spread estimates drawn from the same
data. **Coverage completeness is unverified under this gate**, no exploratory
coverage figure carries certification meaning or may be cited in any later
calendar or admission argument, and R5 carries that as a stated limitation: a
result that varies by period or session may be a coverage artifact.

**R-4 Leakage and bar-integrity controls.** Two families, and **the second is the
one that has actually bitten this programme.**

**(a) Time-direction (acausal) controls.** Forbidden: future bars · target
leakage · centred rolling windows · post-event values · forward-filled future
information · cross-split contamination · any upper-timeframe context bar that is
not **completed** when it is used (prereg §7, "only completed upper bars, no
peek") · probability calibration fitted on anything but a split carved from the
**training** span (Ruling 8).

**(b) Causal-but-wrong controls.** An earlier draft of this requirement listed
only family (a) and cited this repository's history as the argument for it. That
was the wrong way round: **every item in (a) is a time-direction violation, and
the defects recorded here were strictly causal.** They would each pass (a)
unchanged. Three classes, none of them nameable as "leakage":

- **Session discontinuity.** No feature may compute a difference, return, true
  range or rolling statistic *across* a market closure as though the bars were
  adjacent. A `prev_close.shift(1)` that pulls Friday's close at Monday's open is
  causal and still wrong. The committed convention is the ML Step 4 lineage's
  **F8 warm-up guard** — "ATR-14 with `min_periods=14`, **no prev-close fillna**".
- **Bucket completeness.** Applied to context bars as well as to labels: the
  frozen `n_source_bars == 15` rule (R-3), and its analogue on any upper-timeframe
  bin. A partial bin is garbage before it is ever a peek.
- **Warm-up.** Every rolling feature declares its minimum window and enforces it —
  `min_periods` equal to the full window, **never 1** — and the researcher declares
  a single `w_bars` burn-in **≥ the longest feature lookback in the set, including
  H1/H4 context**, with bars inside the burn-in event-ineligible. The committed
  articulation is again the F8 guard and playbook §8's "warm-up burn-in applied
  (W bars event-ineligible)". An ATR computed from a single bar is not leakage in
  any direction; it is simply not an ATR.

**(c) At least one negative control, run and reported — not asserted.** A
prohibition list catches only the defect the author already imagined, and none of
the classes in (b) was on anyone's list before it fired. This is the repository's
own R-1 negative-control rule: `WarmupPolicy`'s docstring records a
`dead_window_loaded: False` field that "asserted the T-1 leakage claim while
measuring nothing". A list of forbidden things is exactly that shape. Minimum: a
**within-fold shuffled-target** run — shuffle `y`, retrain, re-evaluate, and treat
`|shuffled_sharpe| ≥ 0.10` as contamination regardless of every other number — and
a **train/test parity** check.

**On the evidence cited.** The earlier draft's supporting claims — "every positive
Phase-9 result was invalidated" and "the clean baseline came back at Sharpe
−0.189" — are **withdrawn**. The figure is not committed to this repository: it
lives on the unmerged branch `research/post-bug-fix-2026-05-03` and in untracked
local logs, where it is labelled the **M1_V2** baseline, not an M15 one. Even if it
were committed, **C-8 (Ruling 13)** bars any number from a fenced legacy route from
entering this family's design justification or priors, and it was doing exactly
that work here — it was the stated reason R-4 is IN. The defect *classes* in (b)
stand on committed, unfenced authority: the ML Step 4 F8 warm-up guard, the
`min_periods=14` convention pinned across that lineage, prereg §7's completed-bar
rule, and Ruling 3. R-4 needed no fenced numeric to justify it.

**R-5 Cost realism.** Spread, slippage and fees where applicable, using the
committed cost model — `median_spread(pair, session) + 0.3 pip execution padding
+ 0.5 pip cell slippage` — with **both** committed stresses reported: **2× cost**
and **p90 session spread** (prereg §5). Two committed exclusions are part of cost
realism rather than production nicety, because a trade scored in a window where
cost is unmodelled fabricates expectancy: the **rollover window 21:55–22:15 UTC
minimum** and low-liquidity holiday sessions are event-ineligible (Ruling 4;
widen-only). Pip conversion uses the per-pair map with
`global_pip_size_authoritative_for_all_pairs = false` — a 100× JPY pip error is a
recorded invalidation in this programme, not a hypothetical. **A zero-cost result
is never a primary finding**, and every cost claim carries Ruling 5's scope: a
quote-cost-validity claim, not a live-fill claim.

**R-6 Reproducibility.** Code commit SHA · dataset identity · parameters and
config · random seed where applicable · the exact command · an environment
dependency summary. **Byte-level proof is not required here.** Note the recorded
infrastructure caveat: `uv.lock` is stale and `uv sync` against it is destructive,
so the environment summary records what was actually installed.

**R-7 No silent cherry-picking.** Every variant tried is recorded — pairs, models,
thresholds — with the selection rule stated in advance. Reporting only the best
result is forbidden. Recording is disclosure, not control, so three limbs make it
bite:

- **Registered verifiably.** The question, the variant grid and the selection rule
  are committed to the branch **before** the run, and the run record cites that
  registration commit SHA, which must be an ancestor of the run's code SHA (R-6).
  A registration that cannot be shown to predate the result is not one.
- **Counted with a defined unit.** `K` is the number of evaluations whose result
  was **observed**, counted per configuration — pair set × feature set × model ×
  hyperparameters × threshold × split — not per script invocation. Narrowing a
  sweep after reading its output **adds** to `K`; it never resets it.
- **Compared against the right null.** The best result is reported against the
  null expectation for that `K`, never against zero, with the method named. The
  arithmetic is unforgiving: on ~221 weekday UTC days the standard error of an
  annualised Sharpe is ≈ 1.07, so under a true null one configuration clears 0.8
  about 23% of the time, at least one of 20 does so with probability ≈ 99%, and the
  **expected best of 60 configurations is an annualised Sharpe around 2.5 with no
  edge whatsoever**. A best-of-`K` figure without that comparison is not evidence.

Also not reopened: the five selection routes closed as 再試行禁止 in
`phase22_alternatives_postmortem.md` §4.

**R-8 No promotion.** Every result under this gate is
`EXPLORATORY_NON_PROMOTED_RESEARCH_RESULT` and may not be promoted to production
evidence, gate evidence or live readiness. This matches the prereg's own
"results never citable as evidence". R-8 is admitted on the **containment** ground
of §5's second limb, not the correctness ground — see §5.

**R-9 Effective-N, reported and never assumed.** At the frozen 24-bar horizon an
event initiated at every eligible bar overlaps its 23 successors, and PAIRS_20
returns are cross-correlated — so raw trade counts overstate independent evidence,
by up to two orders of magnitude in plausible regimes. Ruling 11 already requires
**both** the raw event count and the effective-N. Every exploratory result reports
both, at portfolio and per-pair granularity, using the committed arithmetic of
`artifacts/m15_gate3a/effective_n_estimator_spec.json` (`APPROVED_SPEC`):
`rho_h = 1 + 23 × overlap_fraction`, `rho_x = 1 + 19 × mean_abs_pairwise_corr`,
`N_eff = Σ(N_raw_pair / rho_h_pair) / rho_x`, with the overlap fractions and the
correlation shown. This costs nothing — the estimator is committed, pure, and
reads no data.

**The floors are not applied.** `RAW_HOLDOUT_TRADE_FLOOR = 1000` and
`N_EFF_HOLDOUT_FLOOR = 400` govern the forward-epoch evaluation; no exploratory
output passes `role="holdout"`, applies either floor, or carries
`SAMPLE_SUFFICIENT` or `INSUFFICIENT_SAMPLE` (§6). Reporting the number is not
applying the threshold. Implementation note: `effective_n()` fails closed outside
`role ∈ {"holdout", "validation"}`, so exploratory use calls the arithmetic
without a verdict rather than inventing a role.

**R-10 Exploratory results may not set the formal contract's free parameters.**
Several quantities family A will freeze are estimated **on the design span** — the
very span this gate opens to search: the per-pair/session spread tables, the EV
gate's `W̄`/`L̄`, the barrier/cost ratio distribution, the final feature list, the
warm-up `W`, and `mean_abs_pairwise_corr`, which the committed estimator spec fixes
as "estimated on DESIGN data only and frozen".

The last is the sharpest case and closes a route neither Ruling 10 nor R-7
catches: `rho_x = 1 + 19 × mean_abs_pairwise_corr` sits in the **denominator** of
`N_eff`, so a variant yielding a lower correlation estimate **raises** `N_eff` and
makes `INSUFFICIENT_SAMPLE` less likely. That disarms a frozen sample floor while
loosening no threshold and while listing every variant honestly. **No quantity
destined to be frozen into the family-A contract may be taken from an exploratory
variant chosen after its results were seen.** Each is either estimated by a rule
registered before the campaign starts, or left entirely to the design audit and
gate 3a, which own it. Exploratory estimates of these quantities are diagnostics
and are labelled as such.

**Three further levers, added after §0's derivation exposed them.**

- **The event rate.** §0 makes the traded-event rate the single unfrozen quantity
  governing whether a frozen sample floor is reached. Choosing an `ev_min`
  operating point, a variant or a threshold **in order to raise the event rate so
  a floor clears** is this requirement's own route applied to a different
  quantity: it disarms a frozen floor while loosening no threshold and while
  listing every variant honestly. Ruling 9's selection metric — validation net
  expectancy subject to the turnover budget — is not substitutable by trade count,
  and no feasibility corridor may become an input to `ev_min` selection.
- **The reported pair count `P`.** `rho_x = 1 + (P−1)·c` takes `P` from the
  caller, and §0.6 measures the effect: under a fixed turnover budget a smaller
  reported universe reaches the floors *faster*, and omitting a pair that fired no
  trades is a free gain. **`P` is reported over the full `PAIRS_20` universe,
  including pairs that fired nothing** — this half is now **RULED**
  (`NR_K_RULED_P_EQUALS_FROZEN_REGISTERED_FAMILY_A_UNIVERSE`, §8.3.0), and the
  earlier qualification that it "does not take effect unless the NR-K ruling adopts
  it" is discharged: the ruling adopted it. Two precisions the ruling requires here,
  because this bullet as originally drafted reached past what was ruled:

  - **`P = 20` does not mean all twenty must trade.** Reporting the full roster is a
    reporting and deflator obligation, not a trading obligation, and §10's "all pairs
    shown, not the survivors" is to be read that way.
  - **The concentration set is *not* ruled to be the same twenty.** This bullet
    originally required "the pair set used for `P`, the pair set the concentration cap
    is computed over, and `PAIRS_20`" to "be the same twenty". §8.3.0 rules the
    **first** of those three and expressly leaves the 0.40 cap as a **separate
    authority**; `pair_contribution` iterates the **traded** list, so the cap's set is
    the traded set by implementation. The requirement therefore splits into one ruled limb and one retained
    proposal: **ruled**, `P`'s set is the registered twenty (§8.3.0); **this packet's
    own proposal and not ruled**, that the three sets be reported together — §8.3.0
    says nothing about a joint report and §10 requires none. The claim that all three
    **must be** the same twenty is **withdrawn**, and the decisive reason is the
    ruling's own rather than the weak one of unruledness: the concentration set **is**
    the traded set by implementation, so requiring it to equal the registered twenty
    would impose exactly the all-twenty-must-trade obligation §8.3.0 forecloses. The
    withdrawal is therefore a *consequence* of the ruling, not a loosening beside it. Withdrawing it also
    withdraws the mitigation it would have supplied against §8.3.7's drop-motive,
    which is why that item is recorded as surviving rather than resolved — though the
    mitigation was narrow: adding zero-share members cannot move a maximum, so the
    requirement was arithmetically inert against the **zero-trade** route and bit only
    on the drop-the-highest-share route. `P_AND_CORRELATION_INDEX_SET_NOT_BOUND` and
    `CONCENTRATION_CAP_DROP_MOTIVE_SURVIVES_NR_K` are the open items behind it.
- **The holdout duration `D` (`T_h`).** It is a formal-contract free parameter
  `[FIXED-AT gate-3a continuation]`, and the only one that moves **both** frozen
  sample criteria at once — `N_eff` grows with the span while the annualised-Sharpe
  standard error falls as `1/√D`. It is also the parameter **this gate is most
  likely to set by accident**, because the only inputs a sizing calculation has —
  the traded-event rate, `mean_overlap_fraction` and `mean_abs_pairwise_corr` — are
  the design-span estimates this requirement already governs. **No duration may be
  derived from an exploratory estimate chosen after that estimate's result was
  seen.** Under this requirement's second branch `D` is left entirely to the
  gate-3a continuation, which owns it. Two of those three inputs are measured on
  the evaluated role itself, so the sizing input is a **declared assumption, never
  a measurement** (§8.1.3).

---

## 5. The anti-overengineering test

For every candidate requirement, ask:

> **Absent this, would the research conclusion about whether M15 carries an edge
> be *materially wrong*?**

**Yes** → it belongs in the Minimum Research Gate.
**No**, and it is mainly for evidence promotion, hostile filesystems, arbitrary
attacker input, production deployment or forensic provenance → **defer to the
production gate.**

**A second limb, because one is not enough.** *Absent this, could the exploratory
work damage, contaminate, or later be mistaken for committed evidence?* **Yes →
IN**, whatever the first answer. The first limb screens *correctness* and generates
R-1…R-7, R-9 and R-10. It cannot screen containment: **R-8 fails the first limb
outright** — the conclusion is exactly as right without it — and is in regardless,
because the cost of a wrong *use* of a right conclusion is not recoverable. §3's
safety boundaries are admitted on this limb too, which is why **§5 may never be
cited to strike a §3 boundary**: a missing broker guard would not make the
conclusion wrong, and that is not the test §3 answers to.

**The adversary this gate defends against is the researcher's own optimism and the
data's own defects — not a malicious actor and not a hostile filesystem.** That
sentence, not the question above, is what actually generates the OUT column.

**What OUT does not mean.** Every item marked OUT stays **fully binding wherever it
already binds** — on the gate-3a continuation, the continuation writer and the
committed evidence tree. Nothing here withdraws, narrows or defers PR #444's
D-series or §12, PR #448's rulings, or PR #450 §2. "OUT" means only "not
additionally imposed on a research-scratch route that touches none of those
surfaces".

Applied, with the reasoning stated so it can be checked:

| Requirement | In or out | Why |
| --- | --- | --- |
| Frozen research question (R-1) | **IN** | Registering after results is how a noise result becomes a finding. |
| Leakage controls (R-4), **both families** | **IN** | A leaked feature produces a confident, entirely false edge. And the causal-but-wrong family is the one that actually fired here — an acausal-only list would have caught none of it. |
| Effective-N reporting (R-9) | **IN** | The 24-bar horizon makes raw counts overstate independence by up to two orders of magnitude; a conclusion drawn on raw counts is wrong by that factor. The estimator is committed, pure and reads no data. |
| Contract-parameter contamination control (R-10) | **IN** | One of the design-estimated values sits in the denominator of `N_eff` and mechanically weakens a frozen sample floor. |
| Dead-window and design-bounds check, **by call not assertion** | **IN** | This is a leakage control wearing a provenance label: endpoints cannot exclude an interior bar, and `DEAD_START` is one second after `DESIGN_END`. `no_overlap.assert_design_bounds` / `assert_no_dead_window` are committed, reader-free and free to call. |
| No promotion (R-8) | **IN**, on the containment limb | Fails the correctness limb and is in anyway: an exploratory number entering the evidence tree is not recoverable. |
| Cost realism (R-5) | **IN** | The M1 flagship was gross-negative *and* net-negative; a zero-cost result would have looked publishable. |
| Train/val/holdout separation (R-2) | **IN** | Without it there is no out-of-sample claim at all. |
| Aggregation correctness (R-3) | **IN** | A wrong bucket boundary changes every label and every feature. |
| Reproducibility basics (R-6) | **IN** | An unreproducible positive is not a finding. |
| No cherry-picking (R-7) | **IN** | Selection over 20 pairs × models × thresholds manufactures edges from noise. |
| Byte-level four-limb proof (D-11), **as a proof with tokens** | **OUT** | Protects evidence *authority*, not correctness of a conclusion. The one limb with a correctness function — the dead-window scan — is taken above as a plain call, without the proof apparatus. |
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
of the §9 frozen acceptance thresholds · **evidence that T-3 is satisfied** (a
median eligible barrier/cost ratio < 3.0 is a T-3 finding however good the other
metrics look) · the continuation output-surface implementation Work PR · the FR-19
test-safety Work PR · the **fifth** independent source-audit re-check, which has
not been started · forward-epoch adoption · discharge of the prereg's gates 4–9,
which remain "none skippable" for family A.

**The frozen thresholds are not applied to exploratory results.** They govern the
*validation kill gate* and the *one-shot frozen holdout* on the **forward epoch**,
which is not yet adopted. An exploratory result may not be described as having
met or failed them, and the tokens `MEETS` and `DOES_NOT_MEET` are reserved to
that formal evaluation.

**And a `failed` outcome here is not a formal negative either.** This is the
asymmetry an earlier draft left open. The exploratory span is short and the
estimator imprecise — the standard error of an annualised Sharpe on ~221 weekday
UTC days is ≈ 1.07, the same order as the effects being looked for — so power to
detect a real but modest edge is low and **`inconclusive` is a likely honest
outcome**. An exploratory `failed` does **not** close family A, does not discharge
or pre-empt the validation kill gate, does not trigger Ruling 12's family-B branch
(which requires failure of the *formal* kill gate this gate cannot run), and is
not `DOES_NOT_MEET`.

**If M15 research fails**, stopping work on production-grade evidence
infrastructure becomes a live option, and that is the point of sequencing this
gate first — but that is a **human + ChatGPT business decision**, recorded as one,
into which the exploratory result enters as clearly-marked non-evidence background
under C-8. It decides nothing on its own, and it may not be taken on a sample the
design could not have detected an edge in. **If it is promising**, the programme
returns to PR #450 §10's deferred dependencies with a reason to pay for them.

---

## 7. Proposed staged flow

| Stage | Content | Reads real data? |
| --- | --- | --- |
| **R0** | Synthetic correctness: aggregation, label, evaluation harness, leakage controls, on synthetic and reference cases | **No** |
| **R1** | Read-only descriptive survey over an approved local dataset — schema, date span, pair coverage, missingness, descriptive statistics, **the distribution of `barrier_distance / cost` on eligible bars and its median (T-3), the eligible-bar rate per pair and session, and the per-pair × session spread distribution (median / p90 / p95)**. **No training** | Yes — Red, needs Q3 |
| **R2** | Naive and simple baselines — momentum / reversion / a rule with no fitted parameters — trained from scratch, on the **training portion only** | Yes — Red |
| **R3** | M15 model research (the planned LightGBM family), on the **training portion only** | Yes — Red |
| **R4** | Single evaluation on the quarantined `EXPLORATORY_OOS_SLICE` (R-2). **Not** the pre-registered holdout evaluation and **not** conducted under §9's frozen conditions (§6) | Yes — Red |
| **R5** | Decision: **clearly promising** / **inconclusive** / **failed**, on the rule below | — |

**Each Red stage is its own gate.** R1 (first real-data read), R3 (training) and
R4 (evaluation) are each Red under policy §6, and CLAUDE.md forbids chaining
distinct irreversible stages automatically. **A ruling on this packet authorises
none of them**; approval of one does not carry to the next; each stage reports and
stops.

**R0 is available now** and needs no ruling on a Red operation — but it is **not
free and not Green.** It touches M15 aggregation, labels, the cost model and
evaluation paths, all policy §3 protected paths, so the implementing Work PR is
**Amber** and is not self-mergeable; policy §8 forecloses the objection, since
"synthetic-only" describes the test data, not the risk of the code.

**R0 does not authorise a second aggregation implementation.** The committed
machinery in `scripts/m15_gate3a/**` is the aggregation authority even while its
source audit is blocked. A parallel harness built outside it is the same hazard
Q1(a) names for data, now for code — and code is where all four audit rounds found
every defect. If a promising result comes from a harness that aggregates
differently from the committed machinery, it is not a preview of the formal
family; if a failed result does, it may be a bug in the scratch code. If R0 must
aggregate independently, the divergence is declared and the two are cross-checked
on identical synthetic fixtures, with any disagreement a finding rather than a
preference.

**R2 completes and is recorded before R3 begins**, and its comparison is reported
(§10). A baseline run after the model is not a baseline, it is a post-hoc foil.
**No previously-trained or deployed model may be used as the baseline**, and no
model whose training data overlaps the exploratory slice, the dead window or the
consumed `365d_BA` holdout (Ruling 8: from-scratch only, no deployed-model reuse).
No number from a fenced legacy route may serve as the baseline (C-8).

**A zero-data calculation R0 must include — and §0 has now performed it.** §0 is
the authority for what follows; the paragraph below is retained because it
specifies the *stage* obligation, but its earlier claim that the calculation "may
moot Q1 and Q3" is **withdrawn** (§0.7): the honest grid spans roughly 25 weekday
days to over a decade and therefore decides neither question. Before any
real-data read is requested, establish from committed numbers alone whether the
frozen sample floors are reachable at all. The inputs are all committed: the M1
flagship fired **8,082 trades over 48 UTC days** (168.4/day portfolio); the prereg
projects the M15 event rate "~15× lower" (≈ 11/day); the turnover cap is ≤ 40
trades/day; the frozen holdout minimum is 2 months (≈ 43 weekday UTC days). Apply
the committed effective-N arithmetic (R-9) across a stated grid of overlap
fractions and mean absolute pairwise correlations, and report the raw count and
holdout length required for `N_eff ≥ 400`. **If the grid shows the floors
unreachable at the frozen horizon, universe and minimum holdout span, that is
reported to human + ChatGPT as a fresh ruling — **not** a Ruling-10 referral,
which does not reach Ruling 2's spans (§8.1.2), and for which
`NO_GENERAL_CONTRACT_AMENDMENT_PROCEDURE_REGISTERED` — before any real-data read is
authorised**. What such a finding would and would not mean is fixed in advance at
§0.8: it could **not** close family A, because prereg §1 closes on sample grounds
only for an `INSUFFICIENT_SAMPLE` "that cannot be remedied by the registered data
plan" — and that clause is scoped "**what closes the family before any holdout
touch**", so it reaches no holdout-role verdict, its referent is undetermined
(`REGISTERED_DATA_PLAN_REFERENT_AND_CONTENTS_NOT_DETERMINABLE`), and under Ruling C
(§8.1.0) it may **not** be read as registering a duration remedy. A lower event
rate is one of the
four mechanisms prereg §1 lists for preferring M15, and it is also the mechanism
that moves a fixed trade-count floor further away; recording that tension is a
statement about the interaction of two frozen criteria, **not evidence about
whether M15 carries an edge**. This calculation reads nothing and costs nothing.

**A constraint the committed frame imposes on R4.** The frozen holdout lives on
the **forward epoch**, which §3.1 records as "not yet adopted", and the forward
epoch is `..._ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`. So the
one-shot frozen holdout **is not available to this gate**, and R4's out-of-sample
evaluation must be an *exploratory* temporal split inside the design span. It
**must not** consume, touch or approach the frozen holdout, and its result is not
a holdout result. Because the holdout's edges do not exist yet, "must not
approach" is unfollowable as an instruction; the operative rule is §3.6's fixed
date ceiling.

**And the exploratory split is out-of-sample for the classifier only.** Under the
committed contract the design span is the **fitting surface** for the cost model,
the EV payoffs and the eligibility hurdle — which is exactly why the frozen frame
puts validation and holdout on a *different epoch*. A slice carved from the design
span shares those fitted quantities with its own test window, so an exploratory
positive is **optimistically biased at the system level even when the classifier's
split is clean**. That is a further reason its result is not a holdout result, and
a further reason the **R2 baseline comparison** is the load-bearing number rather
than the model's absolute metrics: run under the same fitted cost model, the bias
partly cancels in the comparison.

**The R5 decision rule, registered before R1 begins.** R-1 requires stop criteria,
and a three-way verdict with none is the failure R-1 names. These are deliberately
expressed in quantities that are **not** the §9 frozen thresholds, so nothing here
restates, softens or pre-empts them (§6):

- **failed** — the median eligible `barrier_distance / cost` is below **3.0**
  (T-3's own number, adopted here as an exploratory stop because it is the
  condition that makes M15 materially different from the failed M1 cost regime);
  **or** the best slice net-of-cost expectancy is negative with an interval
  excluding zero; **or** the R0 feasibility calculation shows the frozen sample
  floors unreachable.
- **clearly promising** — the best slice net-of-cost expectancy is positive, its
  interval computed on **effective-N** excludes zero, it survives the 2× cost
  stress, it beats the R2 baseline net of cost, and it exceeds the null expectation
  for the campaign's `K` (R-7).
- **inconclusive** — everything else, including every case where effective-N is
  too small to separate the two.

**`failed` may not be returned on a sample the design could not have detected an
edge in.** If the slice does not reach the same order as the frozen floors, the
verdict is `inconclusive`, never `failed`. The floors are not applied as
acceptance thresholds (§6); they are the committed scale reference for what this
programme already judges marginal. `inconclusive` is the expected outcome of a
short exploratory span, is a legitimate result, and is not a reason to extend the
iteration budget.

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
machinery this programme has deliberately postponed.**

**Only one of the options below is a reading of the contract; the others are
requests to amend it, and an earlier draft of this packet presented all three as
free choices.** The committed text points hard at (b): prereg §3.1 — "gate 3a must
complete **before any implementation PR reads or derives data**"; prereg §4 — the
design-data M15 aggregate "is a **new derived dataset** and requires a
Gate-P2-style adoption artifact **before any real read**"; playbook §2 stop rules
1 and 2 — refuse and redirect a real read or a real M15 derivation until the
machinery source audit is accepted, which it is not. Under CLAUDE.md's "the
stricter reading of a research restriction wins", (b) is the default and the
others cost an amendment. That is the human's call to make either way — but it
must be made with the price visible.

- **(a) — a contract amendment, not a reading.** Read-only research proceeds on a
  **research-scratch M15 derivation** that is explicitly *not* the §4 artifact —
  non-promoted, non-citable, outside the evidence tree. This unblocks R1–R4 now.
  It requires amending or referring back prereg §3.1, prereg §4 **and** playbook
  §2.1–§2.2, and it creates a second derivation path — the structure that produced
  the same weekend-gap defect independently in two scripts.
- **(b) — the reading the contract supports.** The §4 artifact exists first, so
  R1–R4 wait. But note (d): this is cheaper than it looks.
- **(c) — also a contract amendment.** An existing committed dataset used directly
  at M1 or another timeframe. Prereg §2 forbids a same-data M1 flagship retry and
  admits general M1 "only under a materially new microstructure-grade hypothesis
  and separate protocol"; Ruling 7 makes M1 aggregation input only; and H1/H4 are
  family B under Ruling 12, reachable only after family A fails validation.
- **(d) — derivable, and absent from the earlier draft.** Satisfy what Ruling 1
  actually requires of gate 3a — derivation artifact, forward-epoch artifact,
  inventory, checksums, ts-bounds, derivation and aggregation identity, retention
  binding — plus PR #450 §10 rows **F** and **G**, **without** paying rows A–E,
  because §10's own closing paragraph states those "are **not** preconditions for
  read-only research into whether M15 carries an edge at all". Option (b) as
  originally written overstated the cost and made (a) look more necessary than it
  is.

**What a ruling for (a) or (c) must also do.** Playbook §5 binds any design-span
derivation PR with "only after the source audit (re-check) is **accepted**", and
playbook §6 gates "**ANY** single run" on an adopted forward epoch. A ruling would
have to state that these govern the *production-evidence* path and do not reach a
non-authoritative research derivation — or amend them. This packet does not decide
which, and the stricter reading currently wins.

**Q2 — initial pair set, with the default already against a subset.** Ruling 2
freezes "design 2025-04-25→2026-02-28 (**exploratory only**, never evidence,
**fixed PAIRS_20**)" — PAIRS_20 is pinned to the exploratory role itself, not only
to the formal family — and prereg §3.2's **R-2a-compliance clause** bars
"inclusion/exclusion decisions **anywhere in this family**"; R-2a's own text reaches
only design time (§8.3.5 ground G). A subset is also not the multiple-comparison saving it looks like:
what controls selection is registering the set in advance (R-7), not shrinking it,
and the effect of pair count on effective-N **depends on what is held fixed — and
under a fixed turnover budget the committed estimator rewards a *smaller*
universe**. An earlier version of this packet asserted that "dropping pairs lowers
effective-N, since `N_eff` rises with the number of contributing pairs"; that is
**withdrawn as backwards**. It holds only with per-pair counts fixed. With the
*portfolio total* fixed — the regime the ≤ 40 trades/day ceiling creates — the
numerator is capped regardless of how many pairs share it while
`rho_x = 1 + (P−1)·c` falls with `P`: at the ceiling and corr 0.3 the frozen floors
are reached in 67 weekday days at `P = 20` and **37 at `P = 10`**, reversing only
below `P = 10` when each pair crosses the overlap threshold (§0.6). Dropping pairs
is an effective-N **inflation** route, so the case against a subset rests on
prereg §3.2's compliance clause and R-7 alone, never on an arithmetic penalty that
does not exist. The narrow question is therefore whether an explicitly
registered subset may be used for **cost** reasons without constituting a pair
selection within family A. **Default if unruled: `PAIRS_20`.**

**Q3 — which dataset, and whether reading it may begin.** The OANDA archive
snapshot is committed provenance (20 pairs × 6 timeframes × 10 years, 17.54 GB).
Reading it is a **real-data read** and therefore Red under policy §6 regardless of
being read-only. This gate does not authorise it.

**Q4 — historical period, and only one direction is open.** The design span
2025-04-25 → 2026-02-28 is committed for the exploratory role. The **forward**
direction is not a research choice and is not being asked: 2026-03-01 → 2026-04-24
is the consumed dead window, and anything at or after 2026-04-25 is the forward
epoch that will *become* validation and holdout, so reading it is a
decision-bearing observation of a holdout nobody has adopted (§3.6). The
**backward** direction is a genuine question but is also constrained: earlier data
leaves the adopted epoch and requires `730d_BA` or `3650d_BA`, both explicitly
non-authorised by Ruling 2 — so it would be a **new epoch-adoption decision**, not
a scope choice inside this gate. **Default if unruled: the design span only.**

**Q5 — the exact cost model for exploratory work.** The committed model is
`median_spread(pair, session) + pad_exec + 0.5 pip`. Whether exploratory work uses
it unchanged, or a deliberately pessimistic variant, is a choice — but Ruling 5
makes **both** stresses (2× and p90) mandatory rather than alternatives, so a
pessimistic variant is admissible only as an *additional* stress, never as a
substitute. Note also that the numeric spread tables **do not yet exist** (§2), so
exploratory work must estimate them from the design span itself; under R-10 that
estimate is a diagnostic and does not become the frozen table. **Zero cost is not
among the options.**

**Q6 — initial model family.** LightGBM is the planned family. Whether R2's
baselines must complete before R3 begins is a sequencing choice.

**Q7 — how many research iterations before the exploratory slice is consumed.**
The **rule** is derivable and is recorded here as the fail-closed default; only the
**number** needs a human choice.

*Default, in force unless a ruling raises it:* the `EXPLORATORY_OOS_SLICE` is
consumed at its **first decision-bearing observation** — the frozen contract's own
definition of consumption (prereg §3.2: "consumed at its single authorised
evaluation, **or upon any decision-bearing observation of it**"). Budget **N = 1**:
every R2/R3 iteration happens on the training portion, and the slice is read once,
at R4.

*What is asked:* whether to raise N above 1, to what, and what multiple-comparison
correction applies at that N. **Raising N is a loosening and needs the ruling;
N = 1 needs none.** Leaving Q7 blank is not a third option — an unbounded budget is
the widest reading of what the gate permits, and playbook §2.8 requires the
narrower reading of an ambiguous permission.

**Why this is not a small number.** The design span is not only the exploratory
arena; it is the source of the quantities family A will **freeze** (R-10). So
unbounded design-span search does not merely over-fit an exploratory figure — it
selects the contract family A commits to. Family A then meets the kill gate on the
genuinely disjoint forward epoch and the over-fit is paid for honestly there, but
the currency is scarce: Ruling 12 allows family A, then family B, then a mandatory
programme-level review, with no third family without a new roadmap arc and audit.
Burning family A on a design-span search artefact spends one of two committed
slots.

**Q8 — where exploratory outputs live.** §9 classifies them; the concrete
directory and writer are deliberately not invented here, and §9 now records that
only a Contract Gate-decision may fix them.

**Q9 — does exploratory work consume the C-7 multiple-comparison budget?** Prereg
§12 risk 10 records the budget as "families A then B only; small pre-registered
candidate sets (one horizon, three `ev_min`)". Because validation and the frozen
holdout live on a forward epoch the exploratory stage cannot touch, exploratory
search does not inflate the *formal* family's error rate — **provided** R-10 holds
and no frozen contract value is set from an exploratory variant. On that reading
C-7 bounds only the formal families. The alternative reading is that any search
over family A's own design role counts against C-7.

**Default if unruled, per playbook §2.8:** exploratory search over family A's own
design role **does** count against the C-7 budget. Where what a gate permits is
ambiguous the narrower reading governs until a ruling adopts the wider one —
exactly as Q7's `N = 1` does. An earlier version of this packet said only that it
"does not choose", which left the wider reading in force by omission.

**Q10 — three researcher degrees of freedom sit inside a frozen threshold.**
`daily portfolio Sharpe (ann., UTC-day)` is frozen at ≥ 0.8 and the sampling
convention is fixed, but committed authority nowhere fixes: (i) which timestamp
attributes a trade's PnL to a UTC day — at a 24-bar horizon a 20:00 UTC entry
closes the next UTC day, and entry- versus exit-day attribution changes the series
and its volatility; (ii) the denominator of `daily coverage ≥ 0.60` — calendar
days, weekday UTC days, or days with at least one eligible bar; (iii) the
annualisation factor, where `sqrt(252)` versus `sqrt(365)` moves a Sharpe by ~20%
*(**since ruled**: `√365` on the complete UTC calendar-date index, §8.7.4/§8.8.4/§8.9.2)*.
Settling these after results are seen is the R-1 failure. This gate does not settle
them; it **refers them back**, which Ruling 10 permits. Meanwhile every reported
Sharpe states which convention it used.

**Q11 — at what holdout length does the frozen Sharpe criterion discriminate,
must the adopted span reach it, and when is that span fixed?** **RULED together
with §0 as one referral — see §8.1**, which carries the ruling. In summary: the
two-month value is a **floor**, `D` is frozen **once at the Gate-3a continuation
boundary before any data**, and post-freeze reselection is forbidden. The **exact
numeric `D` is not ruled** and is blocked by Q10. The text below is the material
the ruling was taken on.

An earlier version asked whether the criterion is "measurable at the frozen
**minimum** holdout". That heading embedded the conflation the referral exists to
expose: the minimum is a floor on *adoption*, not the span the criterion will be
evaluated on. It is also the mirror of an error §0.8 already guards against for
the ceiling.

Ruling 2 fixes a holdout **minimum** of 2 months (≈ 43.6 weekday UTC days) and no
maximum; at that floor the SE of an annualised Sharpe is ≈ **2.4** — a figure
insensitive to Q10(iii)'s unfixed annualisation, since the day count moves with the
factor, and equivalent to `SE ≈ 1/√(holdout in years)`. It is a **best case**: at
Q10(ii)'s 0.60 coverage floor it is ≈ **3.10**, and positive lag-1 autocorrelation
— structurally expected in a continuation family whose 6-hour horizon straddles the
UTC-day boundary on ~25% of trades — inflates it further. Fat tails do not: at a
per-period Sharpe of 0.05 the skew and kurtosis terms move it under 3%.

At that floor a **no-edge** strategy is observed at Sharpe ≥ 0.8 about **37%** of
the time. (The companion figure — a target-edge strategy observed there ~50% of
the time — is **invariant in `D`** and is not a fact about the minimum; see
§8.1.5a.) For comparison, the M1 flagship's −18.91 was unambiguous on 48 days only
because it sat ≈ 8 standard errors from zero.

**The threshold is not in question.** Ruling 10 forbids loosening and this gate
neither changes nor proposes to change it. **Nor is a duration an acceptance
proof.** And unlike §0's limb, **this one has no verdict**: `INSUFFICIENT_SAMPLE`
is defined only on raw and effective counts, so an imprecise Sharpe on a
contract-compliant span yields an ordinary pass/fail. What is referred is `D`, the
α it is judged at — no error rate is committed anywhere — and the point at which
`D` is fixed. §8.1 carries the authority, the options and the recommendation.


---

### 8.1 Q11 + §0 — RULED. Holdout-duration freeze semantics

**`Q11_AND_SECTION0_RULED_FREEZE_D_AT_GATE3A_CONTINUATION_BEFORE_DATA`** ·
`Q11_AND_SECTION0_ARE_ONE_REFERRAL`

**Status change.** `Q11_AND_SECTION0_PENDING_HUMAN_CHATGPT_RULING` is
**HISTORICAL — SUPERSEDED BY HUMAN + CHATGPT RULING**, recorded here rather than
deleted.

§8.1.1–§8.1.6 are the material the ruling was taken on, and §8.1.7's option set is
historical — **but the demotion is not uniform, and getting it wrong would weaken
the defences while leaving the gaps.** **§8.1.3's four derivations are ratified by
Ruling C and are current authority**: the holdout branch is closed, the #422→#425
ceremony does not reach a duration change, the latest admissible freeze precedes
validation, and `INSUFFICIENT_SAMPLE` is a pre-declared outcome rather than a
defect. **§8.1.4's open items remain open**, except where §8.1.0 or the bullets
themselves now record otherwise.

#### 8.1.0 The ruling, as recorded

A human + ChatGPT ruling has been received on the unified Q11 + §0 referral and is
recorded here as **authority**. Three limbs.

**Ruling A — the two-month value is a floor, not the operative duration.**
The committed `holdout ≥ 2 months` is a lower bound. It is **not**
`holdout = 2 months`, and no part of this packet — §0, Q11, sample feasibility or
Sharpe measurability — may be reasoned as though it were.
**`TWO_MONTH_HOLDOUT_IS_A_MINIMUM_NOT_THE_OPERATIVE_DURATION`.**

**Ruling B — the exact `D` is frozen once, at the Gate-3a continuation boundary,
before data.** Option B of §8.1.7 is adopted. The freeze precedes, at minimum,
every one of: validation data observation · holdout data observation · empirical
`N_eff` · empirical overlap · empirical pair correlation · Sharpe · returns · hit
rate · signal strength · **any** model-performance outcome. Because validation and
the holdout share one forward epoch, *"just before the holdout is read"* is **too
late**; the freeze is at the **forward-epoch adoption** Gate-3a continuation — the event
prereg §3.1 names ("`T_v` / `T_h` … **[FIXED-AT gate 3a]** when the forward epoch
is adopted"), **not** the design-span derivation continuation. The playbook uses
"gate-3a continuation" for both, so the distinction is stated rather than assumed.
**`HOLDOUT_DURATION_D_IS_FROZEN_ONCE_AT_GATE3A_CONTINUATION_BEFORE_DATA`.**

**Scope of "any model-performance outcome".** It includes the design-span
exploratory outcomes of §7 R2–R5, which under this gate's own sequencing exist
*before* the forward-epoch continuation. The freeze may therefore follow R5 in
time — but neither `D`, nor the date on which the continuation boundary is
declared reached, may be informed by R4's slice result, R5's verdict, or any other
quantity produced by running a strategy on any span. §8.1.6 limb (i) is the
admissibility test for both.

**What "observation" means here, so the ruling is satisfiable.** Ruling B's bar is
prereg §3.2's **decision-bearing** observation of role data, not any byte touch.
The continuation's own availability metadata — per-file ts-bounds, inventory
checksums, the byte-level no-overlap proof — is §8.1.6 limb (i) and is admissible;
it is in fact the only basis on which `D` may now be sized. Hashing is a byte read
(PR #444) but is not a decision-bearing observation of validation or holdout
*values*. And there is no validation set and no holdout set until `T_v` and `T_h`
are written: **the partition is created by the freeze, not observed before it.**

**The freeze is of the window, not only of its length.** Prereg §3.1 fixes `T_v`
**and** `T_h` at the same moment, and its table starts validation at 2026-04-25.
The single freeze therefore pins the validation start, `T_v` and `T_h` as literal
UTC instants. Holding `D` constant while moving `T_v` — lengthening validation so
the holdout window slides later — changes what reaches the holdout and **is a
reselection within the meaning of Ruling C**.

**Ruling C — no post-freeze reselection.** After the freeze, `D` may not be
extended, shortened, reselected, rerolled or replaced. Specifically forbidden:
lengthening on seeing `N_eff` fall short · lengthening on seeing sample counts ·
changing on seeing correlation · changing on seeing Sharpe · lengthening on
negative performance · shortening on promising performance. **An
insufficient-sample outcome at the frozen `D` is accepted as the result.** A
different `D` is not a remedy and not a retry:
**`NEW_EXPLICIT_PREREGISTRATION_OR_CONTRACT_DECISION_REQUIRED`.**
**`POST_FREEZE_DURATION_RESELECTION_IS_FORBIDDEN_FOR_CURRENT_FAMILY_A`.**

**What this does to committed text: `RULING_C_IS_A_TIGHTENING_NOT_A_CONTRACT_AMENDMENT`.**
On the holdout branch Ruling C restates prereg §3.1's `[FIXED-AT gate 3a]` and
§3.2's consumption rule; nothing is amended. Its one substantive narrowing is on
the **validation branch**, where `effective_n_estimator_spec.json` resolves a
*measured* validation insufficiency to "family A closes **or adoption waits** … no
holdout is touched" — an unselected disjunction (§8.1.4). Ruling C forecloses that
disjunction's `D`-changing content: the trigger is a measured sample count, and
re-adopting later at a different `D` is a reselection. Selecting the stricter arm
of an unselected disjunction is a **permitted tightening** under CLAUDE.md's
stricter-reading rule and playbook §2.8 — not a contradiction of the spec, and no
pre-registration amendment is required. What Ruling C does **not** supply is the
spec's missing selector:
**`VALIDATION_BRANCH_DISJUNCTION_HAS_NO_SELECTOR_RESIDUAL_AFTER_Q11_SECTION0_RULING`**,
to be put with Q10. Nor does it decide family A's fate — "accepted as the result"
fixes what may be *done* with an insufficient-sample outcome, not whether the
family closes.

The token in `forward_epoch_adoption_manifest.json`
(`INSUFFICIENT_SAMPLE__ADOPTION_WAITS`) is a **pre-adoption availability status
about accrued data**, not a measured verdict. It is not a precedent for what
follows a measured `effective_n()` `INSUFFICIENT_SAMPLE` at `role = holdout`,
which Ruling C instructs be accepted as the result.

**Normative wording.** `HOLDOUT_DURATION_IS_A_MINIMUM_PLUS_A_SINGLE_PRE_DATA_FREEZE`

> The committed two-month value is a **lower bound, not the operative holdout
> duration**. The exact holdout duration `D` **SHALL** be fixed **once**, at the
> Gate-3a continuation boundary, **before** validation or holdout data, empirical
> sample quantities, correlation estimates, or research-performance outcomes are
> observed. Once fixed for Family A, `D` **SHALL NOT** be extended, shortened,
> reselected or rerun in response to measured sample sufficiency or research
> outcomes. Selecting a different `D` after the freeze requires a new explicit
> pre-registration or contract decision.

**What "once" means, so the freeze is checkable rather than narrated.** The
freeze is the **first commit that replaces
`forward_epoch_adoption_manifest.json`'s `validation_span_utc` and
`holdout_span_utc` `PENDING` values with literal UTC instants**. That commit is an
ancestor of the code SHA of the validation run, and no later commit alters either
value; a re-issued or amended continuation artifact must reproduce both instants
unchanged.

**Governing principle.** **`DURATION_SELECTION_MUST_BE_OUTCOME_BLIND`** — and it
is a rule about `D`, not a guarantee that the *adjudication* is outcome-blind; see
§8.1.9. The
purpose of the ruling is singular: the span may not be chosen, or re-chosen, in
the light of what the data turned out to say.

**And the closure clause is not a remedy.** The prereg's "cannot be remedied by
the registered data plan" **may not** be read as authorising an unregistered
duration extension. Committed text registers no extension rule, so there is: no
automatic extension remedy, no post-hoc remedy triggered by measured
insufficiency, and no open-ended "keep extending until `N_eff` passes". The
earlier phrasing "the registered data plan *contains* the remedy" is withdrawn and
is not current authority (§8.1.4).

##### What this ruling does **not** decide

- **The exact numeric `D`.** Not in days, weekday days, calendar months, bars or
  years. **`EXACT_D_SELECTION_BLOCKED_BY_Q10_AND_REMAINING_DURATION_AUTHORITY`** —
  Q10 is the upstream authority on day convention and duration semantics and is
  unruled, and no committed source supplies an α, a power target or a
  false-negative tolerance. None is invented here.
- **Family A's fate.** The Zero-Data verdict
  `SAMPLE_FLOOR_REACHABILITY_NOT_DETERMINABLE_WITHOUT_MEASURED_INPUTS` stands
  unchanged. Freeze *semantics* are settled; reachability is not, and this ruling
  neither passes nor fails family A.
- **NR-K, NR-L, Q1, Q3, Q8, Q9.** Untouched — see §8.1.9.

So the ruling is best read as: **`Q11_AND_SECTION0_RULED_ON_FREEZE_SEMANTICS`**.

##### The consequence the ruling creates, stated rather than left implicit

Ruling B bars observing **empirical pair correlation** before the freeze. That
**forecloses limb (ii)** of §8.1.6's sizing partition, whose only example was the
design-span `mean_abs_pairwise_corr`. So `D` may be sized on **availability
metadata alone** — calendar span, weekday and session counts, rollover and holiday
exclusions, pair inventory, source-minute completeness.

**Stated precisely, because an earlier draft of this paragraph overstated it in
three ways.** (a) The foreclosure is largely a **confirmation, not a creation**:
§8.1.6's own inadmissible row already excluded "every performance metric", and the
correlation *is* one — so limb (ii) contributed nothing to sizing `D` before the
ruling either. Ruling B resolves that contradiction in the strict direction and
makes it permanent. (b) It strikes limb (ii)'s **only named `D` input**, not the
limb as a class; no other limb-(ii) quantity has been registered for `D`. (c)
**Ruling B completes a foreclosure §8.1.3 had already established for two of the
three inputs** — `N_raw` and `rho_h` are produced by running the strategy on the
span being sized and were never available pre-freeze.

**The operative consequence:** `D` cannot be sized against a **measured** `N_eff`.
It may still be sized (i) against a **declared assumption** recorded in advance
(§8.1.3), or (ii) by the **Sharpe-SE route**, which §8.1.1 shows is a function of
the **day count alone** and is therefore fully limb-(i) and fully outcome-blind.
Route (ii) is blocked not by this ruling but by the absence of a committed α
(§8.1.5b) and by Q10. **Nothing here asserts the floors are unreachable, and
`SAMPLE_FLOOR_REACHABILITY_NOT_DETERMINABLE_WITHOUT_MEASURED_INPUTS` is
unchanged.**

#### 8.1.1 Why they are one referral

Not because they resemble each other. Because they share all four of:

| | |
| --- | --- |
| **Same authority** | Ruling 2's holdout span — not the §9 threshold table |
| **Same variable** | the holdout duration `D` (`T_h`), and both limbs relax monotonically in it |
| **Same remedy** | a longer `D`, **fixed at forward-epoch adoption** — never an extension of a measured span |
| **Same decision boundary** | *when* `D` may be set, and on what information |

And each makes the **same conflation**: each computes at "the frozen minimum" as
though the minimum were the operative duration. It is not — §8.1.2.

**Neither limb dominates the parameter space.** An earlier draft of this
subsection claimed the Q11 limb strictly dominates. **That claim is withdrawn.**
The limbs cross where `(1 + 23·ω)(1 + 19·c) > 106.5` — the same product form §0.3
budgets at 4.36 — and the crossover sits *inside* the regimes this document
already names:

**`NON_NORMATIVE_DIAGNOSTIC_ONLY` — every figure in this table is a derived
diagnostic, appears in no committed source, and may not be cited as a required
duration or used to size `D` (§8.1.5, and Ruling B's "exact `D` not ruled").**

| Holdout length each limb needs (weekday UTC days) | c = 0.054 | c = 0.3 | c = 0.5 |
| --- | --- | --- | --- |
| §0 limb — regular arrivals | 25 | 67 | 105 |
| §0 limb — Poisson at the ceiling | 120 | 395 | 620 |
| §0 limb — clustered doublet (§0.4b, "not exotic") | 215 | 709 | **1,111** |
| §0 limb — the prereg's own draft estimator (§0.5) | 253 | 838 | **1,312** |
| Q11 limb, at an α this contract never committed | 1,065 | 1,065 | 1,065 |

At the grid's own highest correlation the effective-N limb **overtakes** Q11. The
earlier table selected precisely the two regimes in which Q11 wins.

**So the unification does not rest on dominance. It rests on plannability, which
is a stronger ground.** The Q11 limb is a function of the **day count alone** —
untouched by `rho_h`, `rho_x`, `P` or the trade count — so it is computable from
calendar arithmetic at the moment the contract requires the duration to be fixed.
The effective-N limb depends on three quantities every one of which is produced by
running the strategy on the span being sized (§8.1.3), so **at gate 3a it cannot
be sized at all.** That asymmetry is the reason they must be ruled together: fix a
discrimination standard and gate-3a sizing becomes a calendar computation with no
research outcome in it; leave it unfixed and **no availability-only rule justifies
any duration whatsoever.**

#### 8.1.2 The exact 2-month authority — a floor, not a target

Verbatim, and it says *minimums* in both places:

> prereg §3.1 — "frozen minimum spans (Ruling 2): **validation ≥ 3 months and
> holdout ≥ 2 months**"
>
> Ruling 2 — "**minimums** validation ≥ 3 mo, holdout ≥ 2 mo; adoption waits if
> data insufficient"

There is **no committed maximum** anywhere, and this packet invents none. So
"2 months" is a floor; the operative duration is `T_h`, marked `[FIXED-AT gate
3a]` — and, precisely, **at the gate-3a *continuation***: gate 3a has run and
expressly did not fix it (`m15_gate3a_dataset_epoch_adoption.md`: the boundaries
"remain **[FIXED-AT gate-3a continuation]** when the data exists"; the manifest
carries `"holdout_span_utc": "PENDING"`).

**The minimum must not be read as the planned duration.** Gate 4 points the other
way — "gate 3a should prefer a holdout longer than the 2-month minimum when
accrued forward data allows" — but that sentence is labelled **"Feasibility note
(non-binding)"** in the audit itself and is absent from the binding T-1…T-7 list.
An earlier draft of this packet called it a direction; it is a preference, and the
frozen pre-registration expresses none. **The word "longer" appears nowhere in the
pre-registration.**

**And the minimum is not an acceptance criterion.** It is absent from §9's frozen
table, and failing it produces no verdict — only "adoption waits". Three things
must stay apart: a **span-admissibility floor at adoption** (Ruling 2); a **wait
rule** (prereg §3.1); and the **§9 count floors**, which are the only things that
produce a sample verdict. §0 and Q11 both compute at the first; what actually
binds is the third, on whatever span the first two produced.

**A scope correction this packet owes itself.** Ruling 10's loosening prohibition
binds "**the design audit**" over "**these thresholds**" — the §9 V/H tables. The
span minimums are Ruling 2, not §9. **Ruling 10 therefore does not reach the
duration**, and no argument here rests on pretending it does. Ruling 10 continues
to govern the Sharpe threshold, the sample floors and the turnover ceiling, none
of which this referral proposes to change.

#### 8.1.3 What is derivable

- **The holdout branch is closed, and more strongly than "barred".** The holdout
  is consumed "at its single authorised evaluation, or upon any decision-bearing
  observation of it **(including via an invalid run)**". Any longer window ending
  later still **contains** the consumed span, so an "extended holdout" is a window
  with an already-read prefix. And a genuinely disjoint later window is not an
  extension at all — prereg §3.1 already names it **Disjoint replication**, "a
  further, later or separately adopted span | future decision", a separate gate —
  and prereg §9 puts it out of reach as a remedy: replication is "required before
  any production-grade claim; **not part of this family's acceptance**". It follows
  an acceptance; it is not available as a response to a non-accepting verdict.
  **Post-measurement extension of a measured holdout has no coherent object.**
- **The invalid-run ceremony does not reach this case.** #422→#425 requires an
  invalidator proven *independently of the result*, a **code-only** fix, and a
  re-measurement of the *same* data with no feedback loop. A duration change
  satisfies none of the three: it changes the data, its trigger is the observed
  sample, and it is definitionally a change to the split. R-1 already cites that
  ceremony correctly as the **counter-example**; it must not be reached for here.
- **The latest admissible freeze is earlier than "before the holdout is read".**
  `T_v` and `T_h` are fixed at the **same moment** (prereg §3.1), and validation
  runs on the **same forward epoch** as the holdout. So a `T_h` still movable
  after validation would be sized on that epoch's own realised event rate — the
  best available predictor of the holdout's, from an adjacent span, same strategy,
  same regime. The freeze point is the forward-epoch **gate-3a continuation**.
- **Sizing can only ever be a declared assumption, never a measurement.** Of
  `N_eff`'s three inputs, `N_raw` and `rho_h` are produced by running the strategy
  on the span being sized, and `rho_h` is not even scoped to design data. **Two of
  three are unavailable in principle before the run.** It follows that
  `INSUFFICIENT_SAMPLE` at holdout is **not an error**: it is the contract's
  pre-declared output for a sizing assumption that was declared in advance and
  turned out wrong. Read as an error it invites remediation, and "we need more
  data" becomes a lever; read correctly there is nothing to remediate.

#### 8.1.4 What is **not** derivable — and one of these defeats an earlier claim

- **The validation branch is open, and an earlier statement in this packet was
  wrong about it.** §0.8 said post-hoc extension is "already barred". That is true
  of the **holdout** branch only. `effective_n_estimator_spec.json`
  (`APPROVED_SPEC`) resolves a **measured** validation insufficiency to: "family A
  closes **or adoption waits** per the frozen contract; **no holdout is touched**."
  A validation sample cannot be insufficient before adoption — there is no sample —
  so this is a post-measurement trigger with re-adoption as an authorised
  disposition, on a branch where consumption never fires. The disjunction has **no
  selector**, the validation floors are caller-supplied (`effective_n.py` fails
  closed to `NOT_EVALUATED_AT_THIS_ROLE`), "the family's minimum" has no
  antecedent, and the validation span is nowhere declared consumed or one-shot.
- **The closure clause does not reach a holdout-role verdict at all, and an
  earlier claim in this packet was wrong about it.** §0.8 said "the registered plan
  *contains* the remedy". **Withdrawn.** The clause sits under the heading "**What
  closes the family before any holdout touch:**", so it governs a *pre-holdout*
  verdict only. A holdout-role `INSUFFICIENT_SAMPLE` is governed by §9 H, Ruling 11
  ("an effective-N failure prevents holdout acceptance") and the estimator spec
  ("holdout acceptance cannot be granted") — **none of which states a remedy or a
  closure.** So the contract neither closes family A on this ground nor keeps it
  open; it is silent.
- **"The registered data plan" is undefined.** The phrase occurs **exactly once**
  in the pre-registration and once repo-wide — in the clause itself; `remed*`
  likewise occurs exactly once, on the same line. Two readings are available and
  they move the clause in **opposite** directions: the plan as prereg §3 (which
  contains a minimum, no maximum, and only pre-adoption freedoms), or the plan as
  the gate-3a adoption record (under which the remedy set is strictly narrower).
  Playbook §2.8 requires the narrower reading until a ruling adopts the wider one.
  **`REGISTERED_DATA_PLAN_REFERENT_AND_CONTENTS_NOT_DETERMINABLE`.**
- **No general amendment procedure is registered.** Ruling 10's tighten-or-refer
  clause is scoped to §9's acceptance thresholds; **Ruling 2 carries no such clause
  at all**, and the prereg's only amendment idiom is instance-scoped. So citing
  "a Ruling-10 referral" against a span change does not hold —
  **`NO_GENERAL_CONTRACT_AMENDMENT_PROCEDURE_REGISTERED`**, and the only route is a
  fresh human + ChatGPT ruling.
- **And this limb has no verdict.** `INSUFFICIENT_SAMPLE` is defined only on raw
  and effective **counts**, so an imprecise Sharpe on a contract-compliant span
  yields an ordinary pass/fail. §0's limb has a named verdict and a (pre-holdout)
  closure clause; Q11's limb has neither. **A ruling that supplies a remedy only
  for the counts limb would leave the Sharpe limb with no verdict, no remedy and no
  closure — silently standing**, which is precisely what merging the referral
  exists to prevent.
- **The remedy clause's scope is genuinely ambiguous, and the drift is recorded.**
  prereg §3.1 qualifies it — "if insufficient forward data has accrued **at
  adoption time**, adoption waits" — and its direction is anti-shrink only
  ("impatience cannot **shrink** the holdout"). But the one downstream place the
  rule is quoted, `m15_gate3a_dataset_epoch_adoption.md`, renders it as "if
  insufficient forward data has accrued, adoption waits" — **dropping the
  qualifier**, and introducing it as "the frozen contract's own rule". The
  de-qualified form is timeless, and it is the form the estimator spec then applies
  to a measured result.
- **Gate 4 §11 is the strongest foothold for the permissive reading**, and it is in
  an *accepted* audit: "a false rejection into `INSUFFICIENT_SAMPLE` is
  **recoverable by adopting more forward data — acceptable by design**." Read
  post-holdout it contradicts the consumption rule; read pre-adoption it merely
  restates "adoption waits". Both readings fit the words.
- **No error rate is committed anywhere.** The ≥ 0.8 threshold is frozen; the
  type-I and type-II rates it is meant to deliver are not — not in the prereg, not
  in gate 4, not in the estimator spec. So "measurable" has no fixed meaning, and
  any claim of the form "the criterion needs `D` = X" silently supplies one.
- **No committed artifact records the assumption a span was sized from.** The
  adoption manifest enumerates what gets fixed at the continuation — source, spans,
  inventory hash, retention binding, no-overlap proof — and **no sizing rationale**.
  So "we re-derived from a corrected assumption" has no baseline to be checked
  against.

#### 8.1.5 What the Sharpe limb does and does not say — three corrections

**`NON_NORMATIVE_DIAGNOSTIC_ONLY`.** Every number in this subsection — and in
§8.1.1's crossover table — is a derived diagnostic, not committed authority. None
of `~1,065`, `~1,111`, `~1,312`, `37%`, `43%`, the one-sided 5%, or any α or power
figure appears in any committed source. They are retained because they show *why*
the referral was needed; **none may be promoted to contract justification, cited
as a required duration, or used to size `D`.**

Stated because an earlier draft of this packet got each of them wrong, and each
error ran in the direction of making the case look stronger than it is.

**(a) The 50% figure is invariant in `D` and is not a fact about the minimum.**
`P(observed ≥ 0.8 | true = 0.8) = 0.5` at **every** holdout length — 43.6 days,
one year, ten years. It is a tautology of comparing an unbiased estimator with its
own true value under a symmetric sampling law. Only the false-positive limb moves:
≈ 37% at the minimum, 21% at one trading year, 5% at 1,065 days. An earlier draft
presented both as consequences of the frozen minimum; only one is.

**(b) Any stated "required duration" imports an error rate the contract never
committed.** A corpus search of the pre-registration, the gate-4 audit and the
estimator spec finds **no** significance level, confidence statement, power target
or standard-error requirement — for the Sharpe row or any other. The ≥ 0.8
criterion is a bare **point comparison** on a realised statistic, frozen "as
printed". So `1,065` is not a neutral consequence of the SE; it is the length at
which a no-edge strategy clears 0.8 only 5% of the time, and the answer swings
**12×** across plausible α:

| α (one-sided) | 0.25 | 0.20 | 0.10 | 0.05 | 0.01 |
| --- | --- | --- | --- | --- | --- |
| weekday days | 179 | 279 | 647 | 1,065 | 2,131 |

`1,065` additionally accepts a **50% false-negative rate at the target edge**; a
conventionally powered design (α = 0.05, power 0.80) needs ≈ 2,434 weekday days
≈ 9.7 years. **Choosing α is the ruling being asked for, not an input to it.**

**(c) The discrimination gap overstates the frame, and the real exposure is the
false negative.** 37% is the marginal false-positive rate of **one row of a
ten-row conjunction** — and the Sharpe row is *nested inside* the `net expectancy
> 0` row rather than additional to it, since an annualised Sharpe ≥ 0.8 > 0
implies positive mean daily PnL. Gate 4 §11 already ruled the conjunction
"demanding", validation must be passed first, and gates 8–10 plus mandatory
disjoint replication sit *after* holdout acceptance — **so a false positive is
caught.** This packet's own §10 and §7 R5 already make expectancy, not Sharpe, the
discriminating statistic.

A false negative is not caught. The holdout is consumed and unrepeatable. And this
is the part duration cannot fix: a strategy at a true annualised Sharpe of **1.2 —
50% above the frozen target — is vetoed by the Sharpe row alone 43% of the time at
the minimum and still 21% at 1,065 days**, and a strategy sitting exactly at 0.8
is vetoed 50% of the time **at every `D`**. That is an inherent property of a
point comparison. **It is emphatically not an argument to lower 0.8** — Ruling 10
forbids it, and tightening would make the false-negative rate worse.

#### 8.1.6 What information may set `D`

The intuitive split — "availability metadata yes, research outcomes no" — is the
wrong axis, because a trade **count** looks like metadata and is not.
`N_raw` counts events that "pass the cost-hurdle **and fire an EV-gated trade**",
so it is a monotone functional of how much positive expected edge the model
believes it sees. The operative rule is **self-reference**:

**Superseded in part by Ruling B (§8.1.0): limb (ii) is foreclosed.** The ruling
bars observing empirical pair correlation before the freeze, and the design-span
`mean_abs_pairwise_corr` was limb (ii)'s only example. **`D` is therefore sized on
limb (i) alone.** The partition is retained below because limb (ii) still governs
quantities other than `D`, and because the rule's *shape* — self-reference — is
what generalises.

> A quantity may inform the duration decision only if **(i)** it is computable
> without running any strategy on any span, or ~~**(ii)** it is a DESIGN-span
> quantity estimated under a rule registered before the estimate was produced and
> frozen before `D` is fixed~~ *(foreclosed for `D` by Ruling B)*. **No quantity
> realised in the span whose length is being chosen may inform that choice** — not
> its trade count, not its gaps, not
> its coverage, not its correlation.

**Superseded in part by Q10-A and Q10-B (§8.2.0).** The window is now
**declared**, not computed from availability metadata, and a set of data-derived
anchors is forbidden. Of the limb-(i) inputs below, a **weekday count is not `D`'s
unit** (Q10-A), and **holiday exclusions** and **source-minute completeness** are
`NOT_COMPUTABLE_WITHOUT_APPROVED_CALENDAR` (§4 R-3, D-6). The table is retained for
quantities other than `D`.

| | |
| --- | --- |
| **Admissible (limb i)** | calendar span; weekday and session counts; rollover and holiday exclusions; pair inventory; source-minute completeness |
| **Foreclosed for `D` (was limb ii)** | `mean_abs_pairwise_corr` — Ruling B bars observing empirical pair correlation before the freeze, so it may **not** inform `D`, whether or not NR-L is closed. It remains a limb-(ii) quantity for purposes other than `D`. |
| **Inadmissible** | `N_raw` · realised inter-event gaps and `rho_h` (also role-measured) · eligible-bar counts (cost-table dependent — limb ii at best, never on the sized span) · `daily coverage` (numerator is days with trades) · every performance metric |

#### 8.1.7 The options — HISTORICAL, superseded by Ruling B

**Historical record.** These are the four classes the ruling was taken on.
**Option B is adopted** (§8.1.0 Ruling B); A and C are refused; D survives only in
the form B already requires. The analysis is retained so the ruling can be checked
against what it chose between, not because any choice remains open.

**Option A — 2 months is only a floor, and extension after measurement is
permitted.**
*Authority:* Ruling 2's floor with no maximum; gate 4 §11's "recoverable by
adopting more forward data" — **a non-binding risk note, outside the T-list, never
carried into the pre-registration**; the estimator spec's validation branch.
*Benefit:* Family A is not lost to a sizing mistake.
*Risk:* **Destroys the holdout.** `N_eff` and the Sharpe SE are monotone in the
same `D`, so any `D` short enough to risk `INSUFFICIENT_SAMPLE` is short enough
that the Sharpe estimate is uninformative — the escape hatch and the failure fire
on the same knob. That is optional stopping with the stopping statistic coupled to
the test statistic by construction. At the minimum, an edgeless strategy clears
0.8 about **37%** of the time per look.
*Consequence:* On the holdout branch it has no coherent object (§8.1.3).
*Amendment:* Yes — prereg §3.2's consumption rule.

**Option B — the exact duration is frozen before any outcome inspection.**
*Authority:* prereg §3.1's `[FIXED-AT gate 3a]`; Ruling 1's "gate 3a must complete
before any implementation PR reads or derives data"; gate order §10 places
adoption four gates before the single run.
*Benefit:* Preserves the holdout. And it **forces the disclosure** — because the
SE falls only as `1/√D`, a human who must write `T_h` down in advance is
confronted with the real cost and rules on it knowingly. Under A that cost is
never quoted.
*Risk:* Freezing the *number* without freezing the *assumption* leaves it
re-derivable from a design-span estimate chosen after its result was seen; and
"before any outcome inspection" is an intention unless tied to a committed event.
*Consequence:* `INSUFFICIENT_SAMPLE` becomes a real possible outcome, accepted in
advance.
*Amendment:* **No.** This is what the contract already says, made checkable.

**Option C — exactly 2 months for family A.**
*Authority:* **none found.** No committed text makes the minimum a maximum.
*Risk:* Contradicts gate 4 §5's accepted "should prefer a holdout longer than the
2-month minimum". And §0 shows it is very likely the wrong span — the deflator
budget is 4.36 and ordinary Poisson arrival spends 5.90 alone. **C maximises the
probability of landing in `INSUFFICIENT_SAMPLE` on a one-shot holdout, i.e. it
manufactures the situation in which Option A gets argued for.**
*Amendment:* Yes — it would convert a floor into a ceiling.

**Option D — an authority-derived sizing rule.** `D` = the longest holdout the
accrued forward data supports at adoption, subject to ≥ 2 months and ≥ 3 months of
validation preceding it.
*Authority:* gate 4 §5 and §11 read as instruction — **though the audit labels
them non-binding**; Ruling 2's floor; prereg §3.1's `[FIXED-AT gate 3a]`. Every
limb committed **except one**.
*Risk:* The uncommitted limb is the **adoption decision date**, and that is exactly
where the lever migrates — "wait one more month before adopting" is arithmetically
identical to "extend the holdout by one month". Playbook §1 gives an *earliest*
(≈ 2026-10) and no latest.
*Consequence:* **D is safe iff the adoption decision date is frozen with the same
discipline the duration would otherwise need.** Unfrozen, D is A wearing a
different hat.
*Amendment:* No, if the adoption date is fixed; otherwise yes in effect.

#### 8.1.8 The recommendation that was offered — and what the ruling did with it

**Option B, or equivalently D with the adoption decision date frozen alongside
`D`** — **adopted by the ruling as Ruling B.** One limb of the recommendation was
*not* carried: the ruling fixes the freeze of `D` and does **not** state that the
Gate-3a continuation *date* is itself frozen. §8.1.9 records that as a live
residual, because a late adoption date is arithmetically equivalent to a longer
`D`.

*Authority:* it is what prereg §3.1, Ruling 1 and gate order §10 already provide;
no amendment is required. *Benefit:* it is the only class that preserves the
holdout's meaning, and it surfaces the true cost before it is paid rather than
after. *Research-integrity risk:* the residual is that the freeze is asserted
rather than checkable. The wording below would close it, and **the ruling adopted
Option B but not its enforcement wording** — so the residual stands as
`FREEZE_CHECKABILITY_WORDING_NOT_ADOPTED`, alongside §8.1.4's finding that no
committed artifact records the assumption a span was sized from. §8.1.0 carries
forward the two checks that need no new artifact field (literal UTC instants in
the committed adoption artifact; that commit an ancestor of the validation run's
code SHA). Its "(rate, overlap, correlation) assumption" limb is **not** carried in
that form — Ruling B bars an empirical correlation input, so what would be recorded
is the **availability basis**. Whether that becomes a required artifact field is an
evidence-schema change on a protected path, and is referred with Q10, not taken
here. *Operational consequence:* a
materially longer wait than ≈ 2026-10, and `INSUFFICIENT_SAMPLE` accepted in
advance as a real outcome. *Effect on family A:* it is **not** closed; it is sized
honestly, and a sizing that proves wrong yields a pre-declared verdict rather than
a remediation. *Contract amendment required:* **no** — which is itself the
strongest argument for it over A and C, both of which need one.

This recommendation is **not** chosen because it keeps family A alive. On the
contrary, it makes an unfavourable outcome more likely to be reached and recorded.

**Normative wording candidate** (for the ruling to adopt, amend or reject):

> `T_v` and `T_h` appear as literal UTC instants in the committed forward-epoch
> adoption artifact, together with the `(rate, overlap, correlation)` assumption
> used to derive them. That commit is an **ancestor of the code SHA of the
> validation run**, and no later commit alters either value. No quantity realised
> on the forward epoch informs either. `INSUFFICIENT_SAMPLE` is the pre-declared
> outcome of a wrong sizing assumption, not a defect, and is not remediated by
> lengthening a span that has been measured.

Three checks, all mechanical, all over committed objects. No new machinery, no
artifact, no threshold, no maximum.

#### 8.1.9 Dependencies and residuals

**The live residual: the Gate-3a continuation *date* is not frozen.** Ruling B
freezes `D` at the continuation boundary. It does not fix **when that boundary is
declared reached** — and because `D` is bounded by accrued data, choosing a later
adoption date is arithmetically equivalent to choosing a longer `D`. Committed
authority gives an *earliest* (≈ 2026-10) and no latest. The ruling therefore
closes the direct lever and leaves an indirect one open. It is not closed here,
because closing it would be ruling something the ruling did not rule:
**`GATE3A_CONTINUATION_DATE_NOT_FROZEN_RESIDUAL_AFTER_Q11_SECTION0_RULING`.**
The residual is narrower in **trigger** — a late date cannot be chosen in response
to a measured `N_eff`, since Ruling B puts the freeze before every measurement —
but **wider in authority**, because no committed source sets a latest date and the
ruling does not mention the date at all. And with limb (ii) foreclosed it is no
longer merely *an* indirect lever: availability at the adoption date is now the
entire sizing basis, so **the residual carries all of `D`, not part of it.**
Accrued calendar is limb-(i) metadata and observable without touching role data,
so the date can still be chosen to yield a longer `D`.

**Who declares it reached is, at least, settled.** Forward-epoch adoption is Red
and resumes "only as a gate-3a continuation **with its own approval**", with
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` outstanding — so the
declaration is held by human + ChatGPT, not self-declared by an implementing
session. It should be put with Q10.

**NR-K** (`P` caller-supplied) and **NR-L** (`mean_abs_pairwise_corr` has no
production rule or freeze point) were **both unruled when this subsection was
written**; NR-K has since been ruled at §8.3.0 and its row below is updated in
place. The Q11 + §0 ruling changed their **sequencing** rather than their
substance:

| | Status | Relation to the ruling |
| --- | --- | --- |
| **NR-K** | **RULED** (§8.3.0) — `NR_K_RULED_P_EQUALS_FROZEN_REGISTERED_FAMILY_A_UNIVERSE`. This row is **historical**: it read `NR_K_REQUIRES_HUMAN_CHATGPT_RULING_AFTER_Q10`, and that sequencing was met. Independent of `D`, as recorded. The freeze-point question it raised is answered — the universe is read from the registered set, so no separate `P` freeze point is needed and none precedes the `D` freeze. What survives is the **implementation pin**, not the authority. |
| **NR-L** | **RULED** (§8.5.0) — this row is **HISTORICAL** as to what it calls unpinned: the method, idle-day handling, day attribution and the freeze moment are all now fixed, and `NR_L_REQUIRES_HUMAN_CHATGPT_RULING` is superseded | Ruling B **moots its earlier role here**: the correlation may no longer inform `D` at all, since it is an empirical quantity and the freeze precedes every empirical observation. NR-L survives as its own question — but **the span is not open**: the APPROVED spec fixes it to "DESIGN span only … **never validation/holdout**; frozen once and recorded". What is unpinned is the method, idle-day handling, day attribution, minimum observations, and **when within the design stage** the frozen value is taken. An earlier draft of this row listed training / validation / holdout as candidate sources; that **reopened a committed prohibition and is withdrawn**. No value is invented. |

**They must not be merged into the duration question.** Three separate levers act
on the same floor, and collapsing them would let a ruling on one read as settling
the others. Both retain the disposition §0.6 gave them,
`MUST_RESOLVE_BEFORE_ANY_EFFECTIVE_N_VERDICT`; the ruling left their substance
untouched, and **this packet**, not the ruling, sequenced NR-K behind Q10 — a
sequencing since discharged (§8.3.0).

**And Ruling C protects the duration, not the verdict.** `P` is caller-supplied
and unpinned to the summation, and the correlation has no freeze point — so
`N_eff` remains adjustable *after* it has been measured, with `D` untouched by a
single day. Ruling C reaches neither, and neither is closed here.
**`DURATION_SELECTION_MUST_BE_OUTCOME_BLIND` is a rule about `D`; it is not a
guarantee that the adjudication is outcome-blind.**

**One route this ruling cannot close, recorded rather than papered over.** Ruling
C's escape hatch is a new pre-registration, and its prohibition token is scoped to
the *current* Family A. Nothing states what distinguishes a genuinely new
pre-registration from a relabelled retry of the same question at a longer `D`;
Ruling 12's family budget is the nearest committed constraint and is not this
packet's to interpret.
**`NEW_PREREGISTRATION_SUFFICIENCY_FOR_A_DIFFERENT_D_NOT_RULED`.**

Not ruled here and unaffected: **Q1** stays `REQUIRED_NOW`, default (b) — real-data
read remains unauthorised and read-only confers no exemption; permitting it needs
an explicit contract amendment. **Q3** depends on Q1. **Q8** blocks any stage that
writes. **Q9** keeps the playbook §2.8 narrower reading as its default.

**Q10 is now the next upstream ruling** — see §8.2.

**And `N = 1` is not reopened by this.** A different `D` **would be a second
research iteration in substance whatever it is called** — which is precisely why
Ruling C routes it through
`NEW_EXPLICIT_PREREGISTRATION_OR_CONTRACT_DECISION_REQUIRED` rather than leaving it
available as a retry or a confirmation run: **within the same Family A and the same
pre-registration, a post-freeze rerun is forbidden.** Note that the route Ruling C
names is not yet built — `NO_GENERAL_CONTRACT_AMENDMENT_PROCEDURE_REGISTERED`
stands — and constructing a lightweight one at the moment it is needed would defeat
the ruling.

---

### 8.2 Q10-A / Q10(ii) / Q10-B — RULED. Duration unit, day identity, window declaration

**`Q10_A_RULED_ELAPSED_UTC_CALENDAR_SPAN`** ·
**`Q10_II_DAY_IDENTITY_RULED_UTC_CALENDAR_DATE_EXPECTED_SLOTS_FROM_APPROVED_CALENDAR_AUTHORITY`** ·
**`Q10_B_RULED_EXPLICIT_HUMAN_CHATGPT_UTC_WINDOW_DECLARATION_REQUIRED_BEFORE_CONTINUATION`**

**Status change.** `Q10_PENDING_HUMAN_CHATGPT_RULING` is **HISTORICAL —
SUPERSEDED BY HUMAN + CHATGPT RULING** for these three questions only. **Q10 is
not closed**: limb **(iii)**, the annualisation factor, remains open and unruled
(§8.2.8). Limb **(i)**, entry- versus exit-day PnL attribution, was ruled later, at
§8.5.0, bundled with NR-L because `c` is defined on the same daily series. §8.2.1–§8.2.7
are the material the rulings were taken on and are retained as supporting record —
**§8.2.7 included, notwithstanding its own status line**, which §8.2.7 now marks
historical —
except where §8.2.0 supersedes them. Two precisions on that: §8.2.6's **Q10-A**
recommendation is what Ruling Q10-A adopted, but its **Q10-B** recommendation
(Option B-2, a pre-declared target date) is **not** what Ruling Q10-B says — the
ruling is stronger, supplying exactly the declaration deadline §8.2.4 found B-2
lacked, and B-2's weaker phrasing does not carry into it. §8.2.4's option set for
the date is historical.

#### 8.2.0 The rulings, as recorded

Three rulings received from human + ChatGPT and recorded here as **authority**.

**Ruling Q10-A — `D` is an elapsed calendar span on the UTC clock.**
The window is defined by UTC boundaries and the duration is that elapsed span. `D`
is **not** a weekday count, **not** a trading-day count, **not** an eligible-day
count, **not** a realised-event count and **not** an M15-bar count.
**`Q10_A_RULED_ELAPSED_UTC_CALENDAR_SPAN`.**

*Disposition: the **direction** is a derivation; the **foreclosure of Options B
and C** is a tightening. Neither is an amendment.* Every
role span in the contract is already denominated this way — prereg §3.1's table is
headed "Span (UTC)" and gives dates; Ruling 2 states the minimums in months;
prereg §4 commits "**No DST logic (UTC only)**"; prereg §3.2/§12 call `T_v`/`T_h`
the forward **calendar boundaries**. No committed source offers a competing
denomination for a role span, and none defines a weekday day, a trading day, an
eligible-day duration rule or separate DST duration semantics anywhere in the M15
contract. Nothing is contradicted. Latitude *is* removed — §8.2.3 offered
eligible-market-days and bar-count denominations as live options and the ruling
forecloses both — which is why the foreclosure is labelled a tightening rather
than folded into the derivation. §8.2.3's own caution stands: a taxonomy this
packet coined cannot by itself convert a choice into a derivation; the committed
denomination of role spans can, and does, for the direction.

**Ruling Q10(ii) — day identity is the UTC calendar date; expected slots come from
the approved calendar authority.**
**`Q10_II_DAY_IDENTITY_RULED_UTC_CALENDAR_DATE_EXPECTED_SLOTS_FROM_APPROVED_CALENDAR_AUTHORITY`.**
Responsibility is split and the split is the point:

> `DAY_IDENTITY = UTC_CALENDAR_DATE` · `EXPECTED_SLOT_MEMBERSHIP = APPROVED_CALENDAR_AUTHORITY`

**Scope, stated because the bare token would otherwise reach further than the
ruling.** `DAY_IDENTITY = UTC_CALENDAR_DATE` is scoped to **Q10(ii) as committed** —
the day whose coverage is measured against the `≥ 0.60` floor — together with the
UTC-day portfolio sum prereg §9 already names as the Sharpe sampling unit. It does
**not** define the "day" of the **`≤ 40 trades/day` turnover ceiling**, which
remains a §9 FROZEN row with an undefined day and is **not ruled here**. Reading
that ceiling in calendar days would widen gate 4's committed corridor by ~42%
(§8.2.2) — a loosening Ruling 10 forbids, and one that **citing this ruling must
not achieve**.

**This does not mean all 96 slots of a UTC date are expected**, and it authors no
weekend rule, no holiday rule, no closure rule and no DST rule.

*Disposition — and an earlier draft had this **backwards**.* The **day-identity
half confirms committed text**: prereg §9's frozen row is literally
`daily portfolio Sharpe (ann., **UTC-day**)`, and §9 adds "Sharpe is computed on
**UTC-day** portfolio sums (as in M1)". So "day identity = UTC calendar date"
restates the contract's own unit; it is the nearest thing to a derivation here.

The **expected-slot half is a tightening, not a confirmation**. D-5, D-6 and
`calendar_authority.py` bind the **gate-3a dataset-derivation coverage proof**
(`actual_certified_m15_slots == expected_m15_slots`), not the
`daily coverage ≥ 0.60` **acceptance row** — and the contract Gate-decision records
that twenty terms, **"coverage" among them**, "are currently used in incompatible
senses across committed documents". Applying the calendar authority to the
acceptance denominator therefore **extends** D-6 to a new quantity. It is a
*permitted* tightening — it forecloses the reverse-inferred "days with at least one
eligible bar", which **raises** the denominator and makes ≥ 0.60 harder, the
direction Ruling 10 allows — but it is not a confirmation, and the earlier draft's
claim that it was is withdrawn.

**And the denominator stays day-denominated.** It is the set of **UTC calendar
dates** the approved calendar authority recognises as carrying at least one
expected M15 slot. Read instead as re-denominating a frozen §9 row from days to
slots, it would be an **amendment**, which Ruling 10 forbids without a new ruling;
that reading is not adopted.

**Ruling Q10-B — the exact UTC window is declared explicitly by human + ChatGPT
before the continuation is authorised.**
**`Q10_B_RULED_EXPLICIT_HUMAN_CHATGPT_UTC_WINDOW_DECLARATION_REQUIRED_BEFORE_CONTINUATION`.**
Exact `T_v`, exact `T_h`, the exact holdout window and the exact operative `D` are
declared by human + ChatGPT **before** the forward-epoch adoption Gate-3a
continuation is authorised — together with the **validation start** and the
**declared holdout start**, per the two paragraphs below.

**Forbidden anchor rules**, because the anchor is a governance choice and not a
discovered property of the data: the first available date · the latest available
date · "today" · the maximum available dataset date · a date required to reach
`N_eff` · a date chosen after observing empirical **label** overlap
(`mean_overlap_fraction` / `rho_h`) · after empirical correlation · after a
**traded-event** sample count (`N_raw`, `N_eff`) · after Sharpe or returns · any
automatic "use all available history".

**Two of those need their scope stated, or they would forbid required steps.**
"Overlap" here means the *label* overlap that feeds `rho_h` — **never** the
byte-level **no-overlap proof**, which §8.1.0 admits as availability metadata and
playbook §6 requires before any run. "Sample count" means *traded events* — never
file inventory, checksums or source-minute completeness, all of which §8.1.0
admits.

**Sequence.** `UTC_WINDOW_DECLARATION_MUST_PRECEDE_GATE3A_CONTINUATION_AUTHORISATION`:
(1) upstream authorities resolved; (2) human + ChatGPT explicitly declare the exact
UTC window; (3) the declaration is frozen; (4) only then may the Gate-3a
continuation be separately authorised. **"Choose dates" and "inspect data" may not
be combined into one execution step.**

*Disposition: a **tightening**, not an amendment.* Forward-epoch adoption is
already Red and already requires an explicitly authorised PR; the ruling fixes
*when* the window is declared relative to that authorisation and bars a set of
data-derived anchors. It removes latitude that committed text left open; it
contradicts nothing. In particular it does not disturb "adoption waits", which
governs whether enough data has accrued — a precondition on **adoption**, conjoined
by playbook §2.3 with the separate requirement that an explicitly authorised
continuation PR exist. Accrual and authorisation are two preconditions of the same
event, not a sequence; **so the declaration may, and should, precede accrual
entirely**. An earlier draft called accrual "a precondition on *authorisation*",
which would have pushed the declaration to *after* accrual was sufficient — the
opposite of what Ruling Q10-B is for.

**The window, not merely its length.** Consistent with §8.1's ruling — which pins
"**the validation start**, `T_v` and `T_h` as literal UTC instants" — what freezes
is the whole window identity: **the validation start**, `T_v`, `T_h`, the holdout
start and end, and the inclusion/exclusion convention once an authority fixes it.
Two earlier enumerations here omitted the validation start; with it undeclared,
validation length could vary after the declaration with the holdout formally
untouched. Re-declaring a window of the *same* length at a *different* position is
a reselection: **`SAME_D_DIFFERENT_WINDOW_IS_RESELECTION`**, and it is not
silently permitted.

**What makes the declaration checkable, and what stays narrative.** The
declaration is recorded **as** the freeze commit §8.1.0 already defines — the first
commit replacing the adoption manifest's `validation_span_utc` and
`holdout_span_utc` `PENDING` values with literal UTC instants. That commit **SHALL**
be pushed to the continuation PR's branch strictly **before** human + ChatGPT
authorisation, and those instants **SHALL NOT** differ in any later head of that
PR: `SAME_D_DIFFERENT_WINDOW_IS_RESELECTION` applies **from that first push, not
from merge**, and CLAUDE.md's pre-approval "amend freely and push" licence does
**not** extend to those fields. A head that changes either voids the declaration.
Steps (2) and (3) of the sequence are therefore **one event with one artifact**.

What this does **not** make checkable is the declarer's *basis* — what had been
seen when the instants were chosen — and a window revised before any push leaves no
trace. No artifact records either, and creating one is an artifact-schema change
this packet has not taken (`FREEZE_CHECKABILITY_WORDING_NOT_ADOPTED`).

**The embargo is a bar offset, and the holdout start is declared, not computed.**
Prereg §3.1 writes the holdout as `T_v (+embargo) → T_h` while prereg §3.2
denominates the embargo in **25 M15 bars**, and §7 R-2 records that a bar purge is
not a wall-clock purge — "a Friday-afternoon signal bar's 24-bar label reaches into
Monday, so a 6h15m elapsed-time purge would not purge it." A bar offset therefore
does not convert to a fixed elapsed span, and **`D` is not derived by subtracting
one from `T_v`**. Under Q10-B the **holdout start is declared as a literal UTC
instant** alongside the validation start, `T_v` and `T_h`; the 25-bar embargo is a
**constraint verified against that declaration**, never a formula that produces it.
`D` is the elapsed UTC span between the declared holdout start and `T_h`. Were the
start computed instead, it would move whenever the calendar approval landed — the
same post-freeze lever §8.2.5 identifies for Options B and C, arriving through the
embargo. **`EMBARGO_IS_A_BAR_CONSTRAINT_NOT_A_CALENDAR_DERIVATION`.**

##### The distinction these rulings must not be read across

**`D_IS_ELAPSED_UTC_TIME != SAMPLE_COUNT_IS_CALENDAR_TIME`.** Defining `D` as a
calendar span does **not** count weekends as samples, does **not** make holidays
eligible events, and does **not** turn closed-market intervals into observations.
`D` is **window / time-axis authority only**. `N_eff`, raw observation counts,
overlap and every other sample-accounting quantity stay with their own registered
authorities, and the unit of `D` may not be borrowed for any of them.

**Named explicitly, because it is the live route:** the **`≤ 40 trades/day`
turnover ceiling's "day" is not fixed by Q10-A**. Reading that ceiling in `D`'s
unit would widen gate 4's committed corridor from ~1,720 to `61 × 40 = 2,440`
trades — a ~42% loosening reached by redefining a unit rather than a threshold,
which Ruling 10 forbids. The ceiling's day remains unruled, as does the day in
`daily coverage ≥ 0.60`'s numerator and in the daily Sharpe series.

**And one of those "own registered authorities" is incomplete — named rather than
assumed.** `mean_overlap_fraction`'s **unit is not registered**: the spec says only
"estimated per pair from the realised **inter-event gaps**". Measured in elapsed
time, a window padded with closed intervals lengthens those gaps, lowers
`rho_h = 1 + 23 × mean_overlap_fraction`, and therefore **raises `N_eff` with no
event added and no threshold touched** — the same trap §4 R-2 records for the purge
("a 6h15m elapsed-time purge would not purge it"). The contract's pattern
denominates model mechanics in bars (§8.2.3), but nothing rules it and **Q10-A does
not**. It joins the open list beside NR-K and NR-L:
**`MEAN_OVERLAP_FRACTION_UNIT_NOT_REGISTERED`.**

**This finding is now the subject of its own decision packet at §8.4**, where it is
put as MO-2 with the other six questions, and where the "Q10-A does not rule it"
half is carried as **`Q10_A_DOES_NOT_RULE_THE_GAP_UNIT`**. §8.4.4 reaches the same
conclusion from the horizon side — the unit also fixes `H`'s wall-clock extent — and
the elapsed-time direction recorded here is why: elapsed time is the reading that
**lowers** `rho_h`.

A concrete consequence worth stating, because it corrects an expectation this
packet once held: **the coverage row still does not catch a window padded with
closed days.** Under Q10(ii) the denominator is built from dates the approved
calendar recognises, so padding adds neither numerator nor denominator and the
ratio is unchanged. §8.2.5's earlier claim that coverage would catch it was already
withdrawn; the ruling **confirms** that withdrawal rather than reversing it. The
mitigation rests on the **sample floors**, which count events.

**What the ruling *does* close is the opposite defect, and it is worth naming.**
Under a presence-based denominator, a data outage on an *open* day removed that
date from the denominator too — so **missing data raised the coverage ratio**.
Under the approved-calendar denominator the date remains expected and the outage
**lowers** coverage, where it should. The padding case is unchanged; the outage
case is fixed.

**Two things the ruling does not supply.** The calendar authority declares a flat
expected **slot** set per pair and declares no dates, so a "recognised date" is the
*projection* of that slot set onto UTC dates — a derivation from the artifact, not
a field of it. And that projection is **per pair**, while `daily coverage ≥ 0.60`
is a **portfolio** row: whether the portfolio day set is the union or the
intersection over the twenty per-pair projections is **not ruled**.
**`COVERAGE_DENOMINATOR_PAIR_TO_PORTFOLIO_LEVEL_NOT_RULED`.**

##### What these rulings do **not** decide

- **No numeric `D`.** Not two months, not any month count, day count, weekday
  count or bar count. Two months remains a **lower bound only**, and
  **`EXACT_D_SELECTION_STILL_PENDING_UPSTREAM_AUTHORITIES`**.
- **No month arithmetic.** Q10-A settles the *unit*, not the boundary arithmetic
  inside "≥ 2 months". Whether that minimum is same-day-of-month addition, a fixed
  day count, or something else — and the end-of-month rule it would need — remains
  a downstream **duration-boundary** question (§8.2.3), together with the
  endpoint inclusion/exclusion convention:
  **`DURATION_BOUNDARY_ARITHMETIC_AND_ENDPOINT_CONVENTION_PENDING_HUMAN_CHATGPT_RULING`**.
  It is narrow in scope, not in magnitude — §8.2.3 quantifies it at 59–62 calendar
  / **41–45 weekday days**. No end-of-month convention is invented, and the ruling
  does not reopen Q10-A to settle it.
- **Q10(i) and Q10(iii).** Untouched **by these rulings** and not derivable from an
  elapsed-UTC `D` — *Q10(i) was ruled later, at §8.5.0*
  (§8.2.8).
- **Family A's fate.** The Zero-Data verdict
  `SAMPLE_FLOOR_REACHABILITY_NOT_DETERMINABLE_WITHOUT_MEASURED_INPUTS` stands.
  These rulings define **planning semantics**; they prove neither that
  `N_eff ≥ 400` is reachable nor that it is unreachable, and neither passes nor
  fails family A.
- **The calendar artifact.** `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`
  is untouched. **No coverage denominator may be measured before it is approved.**
  Its approval also has a place in the sequence that step list omits: it must
  precede the continuation, and the target epoch it declares is determined by the
  declared window — so it sits between (3) and (4).
- **When the declaration itself is made.** Q10-B fixes the declaration's position
  *relative to* the authorisation and bars a list of data-derived anchors. It fixes
  **no deadline, no latest date, and no bound on what the declarer may have seen**.
  Accrued calendar is availability metadata, computable by anyone at any time with
  no data access and no trace, so a longer `D` remains selectable **by declaring
  later**. `GATE3A_CONTINUATION_DATE_NOT_FROZEN_RESIDUAL_AFTER_Q11_SECTION0_RULING`
  is therefore **relocated, not discharged**: the lever moves from "when is the
  continuation declared reached" to "when is the declaration made". Closing it would
  need a declaration deadline or a latest date; the ruling ruled neither, and none
  is invented here.

#### 8.2.1 Scope — what Q10 is, and what these two questions are

**Q10 as committed (§8) has exactly three limbs, and none of them is the duration
unit or the continuation date.** Verbatim, it asks about researcher degrees of
freedom inside the **frozen Sharpe criterion**: (i) which timestamp attributes a
trade's PnL to a UTC day; (ii) the denominator of `daily coverage ≥ 0.60`;
(iii) the annualisation factor.

The two questions this packet puts — the unit `D` is measured in, and how the
continuation date is anchored — are **adjacent questions that §8.1's ruling newly
exposed**, not restatements of Q10. An earlier revision of this subsection folded
them into Q10 without saying so; that was the same silent-expansion defect this
packet criticises elsewhere, and it is corrected here. They are labelled **Q10-A**
and **Q10-B** for continuity with the referral, and Q10(i)–(iii) survive unchanged
and unruled alongside them.

**What is in scope:** duration unit · calendar convention · endpoint
inclusion/exclusion · the continuation event's identity and date anchoring ·
holdout start/end derivation as a *form*. **What is not:** any numeric `D`, any α
or power target, market hours, holiday rules, DST rules, and Q10(i)–(iii)
themselves.

**What a Q10 ruling must not do.** It may not loosen the ≥ 0.8 Sharpe threshold,
the `≥ 1,000` / `N_eff ≥ 400` sample floors, the `≥ 0.60` coverage floor or the
`≤ 40 trades/day` turnover ceiling. Ruling 10 permits tightening or referral only.
This guard was carried by the subsection this packet replaced and is restored
here, because it now matters more: **the `≤ 40 trades/day` ceiling is a §9 FROZEN
row whose "day" is undefined**, and gate 4 did its corridor arithmetic in trading
days ("a 2-month holdout (~43 trading days) gives a feasible corridor of
[1,000 … ~1,720] trades"). Reading that ceiling in calendar days would give
`61 × 40 = 2,440` and widen the committed corridor by ~42% — a loosening reached
by redefining a unit rather than a threshold.

#### 8.2.2 Authority inventory — what is fixed, and what is not

| Committed | Source | What it does **not** fix |
| --- | --- | --- |
| UTC clock; `floor(ts / 15 min)`; bar timestamp = bucket start; **"No DST logic (UTC only)"** | prereg §4 boundary convention | It fixes the **bucketing** basis. It does not, on its face, denominate a *duration*. |
| Sessions as UTC hour ranges (Asia 00:00–07:59 / Europe 08:00–15:59 / US 16:00–23:59); rollover exclusion 21:55–22:15 UTC **minimum**, widen-only | Ruling 4 | Holiday / thin-liquidity **event-eligibility** exclusion was `[FIXED-AT design audit]`; gate 4's **T-6 re-pointed it to "implementation, approved before gate 7"** — i.e. **after** the `D` freeze |
| Role spans as **calendar UTC dates**: design 2025-04-25 → 2026-02-28; dead window 2026-03-01 → 2026-04-24; forward epoch ≥ 2026-04-25 | prereg §3.1 | Nothing about eligible-day counts |
| Role minimums as **months**: "minimums validation ≥ 3 mo, holdout ≥ 2 mo"; recorded machine-readably as `validation_min_span_months` / `holdout_min_span_months` | Ruling 2; adoption manifest | Whether "month" means a **calendar** month — the word *calendar* is not in the source and is the reading Q10-A puts — and the month-arithmetic anchoring inside it |
| Purge/embargo as **bars**: "≥ horizon + 1 = **25 M15 bars** at every role boundary" | prereg §3.2 | — |
| `T_v` / `T_h` are the forward **calendar boundaries** ("Exact forward validation/holdout **calendar boundaries** … [FIXED-AT gate 3a]"), recorded as `validation_span_utc` / `holdout_span_utc`, both `PENDING`, `[FIXED-AT gate 3a **continuation**]` | prereg §3.1/§3.2; adoption manifest | Their values, and the date they are fixed on. "Instants" is this packet's word, offered in §8.2.3 as a reading, not as committed authority |

**Not committed anywhere, verified by search:**

- **"weekday day"** — appears nowhere in the tree outside this packet. It is a
  diagnostic unit of §0 and §8.1 and **is not authority**. Every duration figure
  in this document stated in weekday days inherits that status.
- **"trading day"** — used in gate 4's arithmetic ("~43 trading days") and in
  M1-lineage execution reports ("48 UTC trading days"), **defined nowhere** in the
  M15 contract.
- A holiday table, an eligible-day rule, a market-hours instant or a DST rule
  **anywhere in the M15 contract or in `scripts/m15_gate3a/**`**. Scoped, because
  the unscoped claim is false: `tools/generate_calendar_csv.py` authors an
  **economic-event** calendar on a legacy route (deferred by Ruling 7, fenced by
  C-8) and does hard-code a US DST rule — but it contains no market open/close
  instant and no market holiday, and nothing in family A may cite it.
  `scripts/m15_gate3a/calendar_authority.py` is explicit: it "validates an injected
  calendar. **It never authors one.** It contains no market open/close instant, no
  DST transition date, and no holiday."
- Any latest bound on the continuation date, any trigger rule for it, and any
  artifact field recording it.

**Committed in the M1 / ML-Step-4 contract, but nowhere bound to M15 — and it
bears on all three limbs of Q10 as committed.** `scripts/ml_step4/contract.py`
pins `TRADING_DAY_DEFINITION = "utc_calendar_date"`,
`DAILY_COVERAGE_DENOMINATOR = "distinct_utc_calendar_dates_in_holdout"` and
`TRADING_DAYS_PER_YEAR = 252`; `body.py` attributes each trade's day from its
**entry** bar. Prereg §11 lists "metric helpers (extended per C-5)" as **"Reusable
after audit/wrapping"**, and C-8's fenced list does not cover these constants — so
they are **precedent, not fenced legacy**. None binds family A. Two notes for the
ruling: the day unit this repository chose when forced to choose was a **UTC
calendar date**, which corroborates Option A's family; and the M1 coverage
denominator is derived **from observed bars**, which is the reverse-inference D-6
forbids, so it is not available to Q10(ii) unchanged. Whether "audit/wrapping"
permits family A to inherit it is undefined and is part of the ruling.

**The pattern the inventory reveals — refined, because the obvious version is
falsified.** An earlier draft said *spans* are calendar and *offsets* are bars,
"without exception". There are counter-examples in both directions: `warmup.py`
makes "the first `w_bars` forward bars event-ineligible" — a leading **sub-span**
in bars — and prereg §3.2 describes the dead window as "a natural **≥ 1-month
buffer** in addition to formal purge", a **gap** in calendar months. The
span/offset dichotomy is also this packet's own coinage, and a taxonomy the packet
invents cannot by itself convert a choice into a derivation.

**The rule that survives is stronger, because it gives a reason.** The contract
denominates by *what determines the quantity*. **Epoch and role geometry** — where
roles begin and end, how long each runs, and the buffers between them — is
denominated in **calendar UTC time**: dates (prereg §3.1), months (Ruling 2), the
dead window's ≥ 1-month buffer. **Model mechanics** — every quantity defined by the
label horizon or the feature lookback — is denominated in **M15 bars**: horizon 24
(Ruling 6), purge/embargo `horizon + 1 = 25`, warm-up `w_bars ≥ longest feature
lookback`. The bar-denominated quantities are all *derived from the horizon*, which
is why prereg §3.2 states the calendar buffer alongside the 25-bar purge rather
than in the same unit. **`D` is the length of the holdout role — epoch geometry,
not model mechanics.** That is strongly indicated by the contract's own stated
reasons, not merely by a tally.

#### 8.2.3 Q10-A — in what unit is `D` measured?

**Exact question.** `D` is a span. Every span in the frozen contract is
denominated in calendar UTC time and every offset in bars. Is `D` therefore
denominated in **elapsed calendar UTC time** as a matter of derivation — and if
so, what resolves the month-arithmetic ambiguity inside "2 months"?

**Options.**

**A — elapsed calendar UTC time.** `D` is the UTC interval `T_h − T_v(+embargo)`.
*For:* it is the only unit the contract uses for spans; it needs **no calendar
artifact**, no holiday table, no market-hours rule and no DST logic, and prereg §4
already commits "UTC only". It is exactly reproducible from two instants. The
adoption manifest already computes this way ("validation ~2026-04-25..2026-07-25 +
purge + holdout ~2026-07-25..2026-09-25"). *Against:* equal calendar spans carry
unequal evidence, because weekends carry no bars — a real objection, addressed
below.
*Amendment required:* **no**; on the reading above it is a derivation.

**B — eligible market days or sessions.** *For:* it tracks evidence more closely
than calendar time. *Against:* it requires the approved calendar artifact, which
does not exist and is gated by `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`.
It would make the Minimum Research Gate depend on precisely the production
dependency the gate exists to avoid, and the repository authors no calendar by
design. *Amendment required:* not to the prereg, but it imports an unbuilt
production gate.

**C — M15 bar or eligible-slot count.** *For:* closest to evidence. *Against:*
**circular** — eligible slots depend on the completeness rule and, through
`n_source_bars == 15`, on the data itself, so `D` would be defined by a quantity
the freeze forbids observing. It also needs the calendar artifact for the expected
slot set (D-6 forbids inferring it from the source). *Amendment required:* not to the prereg, but it collides with **Ruling B** —
`DURATION_SELECTION_MUST_BE_OUTCOME_BLIND` — because eligible-slot counts are
produced by observing the data the freeze must precede. (An earlier draft cited
"§8.1's `MEASURED_SAMPLE_BLIND` requirement". **§8.1 contains no such token** and
the string occurs nowhere else in the repository; the citation was fabricated and
is withdrawn.)

**D — a hybrid: calendar span for `D`, bars for offsets.** This is not a fourth
option so much as the pattern already in the contract, made explicit: `D` in
calendar UTC, the 25-bar purge unchanged in bars.

**The sub-ambiguity Option A does not by itself resolve, and it has three limbs,
not one.** "Two months" is anchored arithmetic. Under same-day-of-month addition —
the convention the adoption manifest itself uses — a nominal 2-month holdout is
**59 to 62 calendar days** depending on the anchor month, a 5.1% span variance.
**In the unit every figure in §0 and §8.1 is actually stated in it is larger**:
weekday count depends on the anchor's *day of week* as well as its month, so a
nominal 2 months spans **41 to 45 weekday days** against the 43.6 used throughout —
roughly **−6% / +3%**, five times the ~1.7% annualisation-clock inconsistency this
same subsection thinks worth referring.

So Option A needs **three** sub-decisions: (i) same-day-of-month arithmetic versus
a fixed day count; (ii) if same-day-of-month, the **end-of-month rule** — two
months after 31 December is either 28 February (clamp) or 3 March (overflow), no
committed source supplies it, and the repository implements month arithmetic
nowhere; and (iii) the **anchor**, which is the limb with teeth. **This packet does not choose**, and an earlier draft's note that "a fixed day
count would be a tightening of Ruling 2, not a loosening" is **withdrawn as wrong
twice over.** *On arithmetic:* same-day-of-month 2-month spans are 59, 60, 61 or
62 days, so only a fixed count of **≥ 62** is a tightening at every anchor — 59,
60 or 61 *shortens* the floor at the longest anchors, and the adoption manifest's
own worked plan (2026-07-25 → 2026-09-25) is exactly 62 days. *On authority, and
this is the deeper error:* **no committed tighten-only permission over Ruling 2
exists at all.** §8.1.2 records that Ruling 10 binds "the design audit" over "these
thresholds" — the §9 tables — and "does not reach the duration", and
`NO_GENERAL_CONTRACT_AMENDMENT_PROCEDURE_REGISTERED` stands. A fixed day count is
therefore a change to Ruling 2 with **no registered route**, not a tightening under
any authority this repository has.

**Endpoint convention.** `no_overlap.py` records that `DEAD_START` is exactly one
second after `DESIGN_END`, which implies **inclusive-end, disjoint-by-one-second**
boundaries for the committed spans. Whether that generalises to `T_v` / `T_h` is
not stated. It is a small fourth limb and is referred with Q10-A rather than
assumed.

#### 8.2.4 Q10-B — how is the continuation date anchored?

**Exact question.** §8.1's ruling freezes `D` *at* the forward-epoch adoption
Gate-3a continuation, but fixes nothing about **when that continuation happens**.
Since `D` is bounded by accrued data, the date determines the span. What rule
anchors it, and who owns it?

**The event's identity, stated precisely because the phrase names two things.**
The playbook uses "gate-3a continuation" for both the **design-span derivation
continuation** (its §5 template, which is barred from adopting the forward epoch)
and the **forward-epoch adoption continuation**. §8.1's freeze is the **second**.

**What is committed about it.** Playbook §2.3: "**No forward-epoch adoption**
before sufficient forward data accrues **AND** an explicitly authorised gate-3a
continuation PR exists — refuse and redirect." Forward-epoch adoption is **Red**
(policy §6), so approval is human + ChatGPT and no session self-declares it. The
adoption manifest's deferral block carries **five `PENDING` fields** —
source, validation span, holdout span, inventory hash, retention binding — plus a
**non-deferred** note on the no-overlap proof (the source-level proof "holds now").
Counting that sixth entry as deferred inverts its meaning. **No date field among
them**, and the manifest's only date is its own `as_of_utc`, which records when the
manifest was authored.

**What is not committed.** Any latest bound; any rule converting "sufficient data
accrued" into a date; any record of the date as evidence.

**What *is* already constrained — Q10-B does not sit in a vacuum.** §8.1.0 binds
the date already: "neither `D`, nor **the date on which the continuation boundary
is declared reached**, may be informed by R4's slice result, R5's verdict, or any
other quantity produced by running a strategy on any span." Q10-B therefore adds a
*positive selection rule* on top of an existing prohibition. No option below
replaces that prohibition, and B-3 means unfixed **subject to** it.

**Options.**

**B-1 — earliest-satisfying.** The continuation is declared at the first date on
which the frozen minimums are satisfiable. *For:* removes the lever entirely — the
date becomes a function, not a choice. *Against:* it forces the shortest admissible span. §0.3 shows that span failing
the `N_eff` floor **under Poisson arrivals at the turnover ceiling** — a conditional
identity, not a verdict; §0.7 remains
`SAMPLE_FLOOR_REACHABILITY_NOT_DETERMINABLE_WITHOUT_MEASURED_INPUTS` and nothing
here promotes it. It also collides with gate 4's (non-binding) preference for a
longer holdout.

**B-2 — pre-declared target date.** A target is registered in advance, before any
exploratory outcome exists, and the continuation occurs when both it and the
accrual condition are met. *For:* outcome-blind by construction, and it permits a
span longer than the minimum. *Against:* "in advance" needs a **named event**, or B-2 collapses into B-3.
Ruling B's bar is decision-bearing observation of *role data*, and accrued calendar
is not that — it is computable by anyone at any time with no data access and no
trace — so nothing in the ruling prevents the target being declared the week before
the continuation, after watching accrual. **B-2 is only as strong as its
declaration deadline**, and the only deadline that precedes accrual observation is
the Q10 ruling record itself.

**B-3 — leave it unfixed.** The status quo. *Against:* with correlation-based
sizing foreclosed by Ruling B, **availability at the adoption date is now the
entire sizing basis**, so an unfixed date carries all of `D`. That is the residual
§8.1.9 records and declines to close.

**Owner.** On committed authority the date is not an AI's to choose:
`DURATION_WINDOW_FREEZE_REQUIRES_HUMAN_CHATGPT_DECISION`. Forward-epoch adoption
is Red, requires an explicitly authorised PR, and
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` is outstanding.

#### 8.2.5 Calendar dependency, and the anti-overengineering judgement

The question worth asking plainly: **does defining the unit of `D` really require
a production-grade approved calendar artifact?**

**No — but not for the reason an earlier draft of this subsection gave.** That
draft said only Option A avoids
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`, and called it "the
production dependency this gate was created to sit upstream of". **Both halves are
wrong against committed text, and the claim contradicted §8.2.4 four paragraphs
earlier.** The contract Gate-decision §9 requires the calendar artifact for the
target epoch to be approved by human + ChatGPT **before the gate-3a continuation
runs** — and the freeze *is* that continuation — so an approved calendar exists at
the freeze under **every** option. The same section records it as "**a
real-data-independent approval item**: the artifact is a statement of market
hours, not a measurement of the dataset", so it is not a production dependency at
all. **Withdrawn.**

**The real asymmetry is what the artifact is *used for*, and it is stronger.**
Under Option A the calendar is consumed only by the coverage proof and **cannot
move `D`**. Under B or C its content *becomes the definition of `D`* — and gate 4's
T-6 schedules the eligibility calendar for approval **after** the freeze. An
eligible-day `D` would therefore freeze a number whose wall-clock span a later
calendar approval still moves, with **Ruling C unable to see it because `D` never
changes**. That is a post-freeze duration lever with a perfect alibi.

**And a weekday-derived rule is not merely unbuilt — it is actively refused.** A
committed test pins that a slot rule of `"generate the usual weekdays"` raises
`CalendarProvenanceError` with "no commit can carry it". Any unit that needs a
day-eligibility rule must therefore obtain a provenanced calendar; it may not
derive one, and this gate may not author one.

**And the simplification does not distort the conclusion — but only via one of
the two rows an earlier draft claimed.** The sample floors (`≥ 1,000` raw,
`N_eff ≥ 400`) count **events, not days**, so a calendar span that happens to
contain few tradeable days fails there, where it should. That half is sound.

**The coverage row is *not* part of this mitigation, and saying it was overstated
the case.** The only committed precedent for the denominator is the immediately
prior family's `TRADING_DAY_DEFINITION = "utc_calendar_date"` /
`DAILY_COVERAGE_DENOMINATOR = "distinct_utc_calendar_dates_in_holdout"`. On a
presence-based reading of that denominator, days with no bars leave both numerator
and denominator, and the ratio is **unchanged** by closure padding — the row would
be blind to exactly the defect it was credited with catching. Which reading the
M15 family takes is **Q10(ii)** — **now ruled** (§8.2.0): the denominator is
calendar-authority based, not presence-based. The conclusion is unchanged and the
grounds have moved: padding with closed days is invisible under *either* reading,
so the mitigation still rests on the sample floors alone. **This paragraph's
"presence-based" framing is historical**; §8.2.0 is the current statement.

**So `Q10_BLOCKED_BY_CALENDAR_AUTHORITY` does not apply to Q10-A under Option A.**
It would apply immediately under Option B or C, and that asymmetry is itself the
strongest argument for A.

#### 8.2.6 Recommendation — offered, not applied

**Q10-A: Option A (elapsed calendar UTC time), with the month-arithmetic
sub-decision referred.** *Authority:* every span in the contract is already
denominated this way; prereg §4 commits "UTC only"; the adoption manifest already
computes this way. *Benefit:* simplest, outcome-blind, exactly reproducible from
two instants, and the only option needing no unbuilt production infrastructure.
*Research-integrity risk:* equal calendar spans carry unequal evidence — mitigated,
not ignored, because coverage and the sample floors are separately frozen and
catch exactly that. *Operational consequence:* none beyond recording two instants.
*Contract amendment:* **none required** — this is closer to a derivation than a
choice, which is the main reason to prefer it.

**Q10-B: Option B-2 (pre-declared target date), with the owner as committed.**
*Authority:* it is the only option consistent with
`DURATION_SELECTION_MUST_BE_OUTCOME_BLIND` that does not force the shortest
admissible span. *Risk:* the target's basis must be availability metadata alone,
and nothing yet records what it was. *Contract amendment:* none; but recording the
target as evidence would be an artifact-schema change, which this packet does not
take (`FREEZE_CHECKABILITY_WORDING_NOT_ADOPTED`).

**Normative wording candidate** (for the ruling to adopt, amend or reject):

> `D` is denominated in **elapsed UTC calendar time**, measured between the two
> instants `T_v(+embargo)` and `T_h` recorded at the forward-epoch adoption
> Gate-3a continuation. Offsets — the 25-bar purge/embargo — remain denominated in
> M15 bars. The unit **SHALL** be fixed before, or at the same moment as, the `D`
> freeze, and never after any decision-bearing observation. No eligible-day,
> session or bar-count denomination is adopted for `D`, and no market calendar,
> holiday rule or DST rule is authored for this purpose.

**Neither recommendation is chosen for making Family A easier to pass.** Option A
is the unit under which a thin span most visibly fails the coverage and sample
rows, and B-2 does not license a longer span on demand — it requires the target to
be declared before anything is known.

#### 8.2.7 Compatibility, dependencies and status

**Q11 + §0 compatibility.** Nothing here loosens the ruling: two months stays a
**floor**; `D` and the window are still frozen **once**, before decision-bearing
data; post-freeze extension, shortening and reselection stay forbidden; a
different `D` still needs a new explicit pre-registration. **Ordering matters and
is stated:** the Q10-A unit must be fixed **no later than** the `D` freeze —
otherwise "the convention changed, so `D` must be recomputed" becomes a post-freeze
reselection route wearing a definitional label.

**Sharpe-SE route.** Q10-A changes the *unit* the SE is computed in, so it is a
dependency of that route. No α or power target is invented here and no numeric `D`
is derived from it.

**NR-K.** *Ruled since this paragraph was written — see §8.3.0; retained as the
record of Q10's relation to it.* Not ruled then, and sequenced after Q10 by §8.1.9.
**No token is proposed for
it here.** An earlier draft offered
`PAIR_UNIVERSE_MUST_BE_FROZEN_NO_LATER_THAN_D_FREEZE`; that **named the wrong
object and is withdrawn** — the *universe* is already frozen (prereg §3.2's
compliance clause bars pair selection family-wide; R-2a's own bar is design-time).
§4 of this document *proposes* that the pair set used for `P`, the concentration set
and `PAIRS_20` "must be the same twenty", but **§4 is this packet's own proposal,
not authority for a withdrawal** (§8.3.1) — the same defect §12.5 records elsewhere,
recurring here. *§8.3.0 has since ruled `P`'s set and §4 has withdrawn the
concentration limb as unruled; the withdrawal above stands, its reasoning is
corrected here.* NR-K is the estimator's *caller*
contract, not a universe freeze. Recorded
only as an ordering observation **for the NR-K ruling, not for this one**: a `P`
freeze-point, if adopted, would have the same shape as Q10-A's.

**Where fixing Q10-A moves the pressure** — historical, and now partly
discharged. This paragraph asked that Q10-A and Q10(ii) be ruled together; **they
were** (§8.2.0). What survives is the substance: no row is sensitive to how much of
a span was closed, because the denominator excludes closed dates under the ruled
reading too. The pressure that remains went to **NR-K** (§8.3), not to Q10(ii),
and NR-K has since absorbed it (§8.3.0).

**NR-L.** Not ruled. The committed constraint stands: correlation is estimated on
the **DESIGN span only, never validation/holdout**. Its within-design freeze point
remains unresolved, and under §8.1's ruling it may not influence `D` after the
freeze in any case.

**Unchanged:** Q1 (`REQUIRED_NOW`, default (b)) · Q3 (depends on Q1) · Q8 (blocks
any writing stage) · Q9 (narrower default) · Q10(i)–(iii) · FR-19 (open) ·
`NEW_PREREGISTRATION_SUFFICIENCY_FOR_A_DIFFERENT_D_NOT_RULED` ·
`FREEZE_CHECKABILITY_WORDING_NOT_ADOPTED` · the Zero-Data verdict.

**Status: superseded — see §8.2.0.** Q10-A, Q10(ii) and Q10-B are **RULED**; this
subsection's status line is historical and is retained only as the state the
rulings were taken from.

#### 8.2.8 What remains open after these rulings, and in what order

**Q10's two original limbs are now both ruled** — **(i)** at §8.5.0 and **(iii)** at
§8.7.4, with its guard order at §8.8.4 and the exclusion rule at §8.9.2. *An earlier
drafting of this sentence said "(iii) survives"; that predates §8.7.4 and is
**withdrawn**.* Neither was derivable from an elapsed-UTC `D`:

| Limb | Status | Why the Q10-A ruling does not settle it |
| --- | --- | --- |
| **Q10(i)** entry- vs exit-day PnL attribution | **RULED** (§8.5.0) — **`Q10_I_RULED_REALIZED_PNL_ATTRIBUTED_TO_EXIT_UTC_DATE`**; `REQUIRES_HUMAN_CHATGPT_RULING` is **HISTORICAL** | Choosing the *day identity* fixes what a day **is**; it did not fix **which** day a trade whose horizon straddles midnight is attributed to, and a 24-bar horizon makes that live whatever the identity. Ruled with NR-L in one bundled decision, because `c` is defined on a daily series that does not exist until this is fixed. The ruling reaches **seven** quantities through `MetricTrade.day` — `c`, the daily Sharpe, max drawdown, daily coverage and turnover at holdout, plus the **validation** daily Sharpe that selects the operating point and the **validation turnover** figure inside prereg §9.V's kill gate — and **loosens no frozen threshold**, while `Q10_I_MUST_NOT_BE_RESELECTED_AFTER_OBSERVING_ANY_METRIC_IT_MOVES` therefore binds validation observations too. It does **not** define the `≤ 40 trades/day` ceiling's day, which Ruling Q10(ii) leaves unruled. |
| **Q10(iii)** annualisation factor | **RULED** (§8.7.4) · `Q10_III_RULED_COMPLETE_UTC_CALENDAR_DATE_SHARPE_INDEX_IDLE_ZERO_ANNUALISED_BY_SQRT_365`; `Q10_III_PENDING_HUMAN_CHATGPT_RULING` is **HISTORICAL**. Complete UTC calendar-date index for the evaluated role's span · idle date = zero · Q10(i) attribution · **`√365`** | The unit of `D` and the constant that annualises a daily Sharpe are different objects. Fixing the first does not fix the second, and no committed source fixes the second for M15: the only authority is prereg §9's row label "**ann., UTC-day**", and `TRADING_DAYS_PER_YEAR = 252` is **M1 precedent**. §8.6.1 shows the committed Sharpe series is indexed on **active dates**, so `√252` is coherent with neither a trading-day nor a calendar clock; its direction against `√252` is **conditional**, crossing near `a = 252/365 ≈ 0.690` (§8.6.1's three corrections govern). Guard order at §8.8.4; **guard failure excludes the candidate** at §8.9.2. |

**And the exact `D` is still blocked.**
**`EXACT_D_SELECTION_STILL_PENDING_UPSTREAM_AUTHORITIES`.** The recorded ordering:

1. Q10-A / Q10(ii) / Q10-B — **ruled** (§8.2.0).
2. **NR-K** — pair-universe and `P` authority — **ruled** (§8.3.0).
3. **Mean-overlap contract** — **RULED for Minimum Research Gate purposes,
   instantiation pending** (§8.4.0, Rulings ω-1…ω-13). Method, clock, pair handling,
   window/calendar ordering, event-eligibility freeze and pair-calendar freedom all
   ruled; **instantiation waits on the approved calendar artifact**, and two items are
   deferred outside the gate as production checkability. *"Closed" is avoided: R-9
   requires every exploratory result to report `N_eff` with the overlap fractions shown,
   and no authoritative `ω` is measurable until an artifact that does not yet exist is
   approved.*
4. **NR-L** — correlation pair set, statistic, series, day attribution, idle days,
   undefined cases, common date alignment, source span and freeze point — **RULED**
   (§8.5.0), **bundled with Q10(i)** because `NR_L_DAY_ATTRIBUTION_DEPENDS_ON_Q10_I`
   made two of its limbs unclosable while Q10(i) was open. The **contract** is fixed;
   the **value** is unmeasured and implementation remains.
5. Remaining duration-sizing authority — the month-arithmetic boundary question
   (§8.2.3) and the endpoint convention. **Q10(i) and Q10(iii) are both ruled and no
   longer among them** (§8.5.0, §8.7.4); *an earlier drafting listed Q10(iii) here and
   called the whole step "not ruled", which predates §8.7.4 and is **withdrawn**.* What
   remains unruled in this step is
   `DURATION_BOUNDARY_ARITHMETIC_AND_ENDPOINT_CONVENTION_PENDING_HUMAN_CHATGPT_RULING`.
   §8.6.4 records that the declaration at step 6 **cannot yet be taken**, and why:
   `EXACT_WINDOW_NOT_READY_FOR_DECLARATION_FORWARD_EPOCH_DOES_NOT_EXIST`.
6. Human + ChatGPT declaration of the exact `T_v` / `T_h` / `D`.
   **6a.** *After step 6 and before step 8*: the declared window is frozen, **then** the
   **forward-epoch** Calendar A is materialised **for** that declaration, frozen and
   approved, and the window may **not** be reselected on calendar content (Ruling
   ω-13(a); §8.2.0's "between (3) and (4)"). This adds **no authorisation** and does not
   divide step 6, which §8.2.0 fixes as one event with one artifact. *Earlier draftings
   labelled this "5a", placed it "within step 6", and then attached it to ordering item
   3 — three numberings, none agreeing; it belongs here.*
7. The remaining Minimum Research Gate questions — Q1, Q8, FR-19 and the rest
   of §8.
8. Only after **every** *other* minimum-gate requirement is resolved may
   execution authorisation be considered at all. *(An intermediate draft of this
   step wrote "every **mandatory** … requirement". "Mandatory" is defined nowhere in
   this document and would be classified by whoever wished to proceed; the closed
   quantifier is restored, and the stricter reading governs.)*

Steps 2–5 precede step 6 deliberately: declaring the window before the pair
universe, the overlap authority and the correlation authority are settled would fix
`D` against a sample model still open to change. **Step 3 was inserted after the
NR-K ruling**, which left **`ω` and `c`** as the two unpinned terms in §0.3's
deflation inequality; `ω` is sequenced first because it carries neither a span scope
nor a freeze obligation, where `c` carries both (§8.4.2). **Step 8 is unconditional,
and no earlier step may be read as partial authorisation.** Step 6 is not an
authorisation either — but it **is** irreversible: the window declaration is a freeze
bound from the first push by `SAME_D_DIFFERENT_WINDOW_IS_RESELECTION`, and it is
taken before step 7's questions, Q1 included. That ordering is deliberate, since the
declaration must precede accrual (Q10-B), and it does not relax step 8.

### 8.3 NR-K — RULED. `P` and the pair-universe authority

**`NR_K_RULED_P_EQUALS_FROZEN_REGISTERED_FAMILY_A_UNIVERSE`**

**Status change.** `NR_K_PENDING_HUMAN_CHATGPT_RULING` and
`P_DEFINITION_CONFLICT_SPEC_CONTRIBUTING_VS_UNIVERSE_FIXED` are **HISTORICAL —
SUPERSEDED BY HUMAN + CHATGPT RULING** (§8.3.0). §8.3.1–§8.3.11 are the material
the ruling was taken on and are retained as supporting record, except where
§8.3.0 supersedes them — **§8.3.3's "`P` is not bound across roles" limb**,
**§8.3.4's freeze-point limb as to `P`'s binding**, **§8.3.9's option set** — the ruling selects
Option A's cardinality on Option B's authority object (all marked in place) — and **§8.3.10's recommendation is what the ruling
adopted**, extended in three places §8.3.10 did not reach (the enumerated forbidden substitutions, the `P = 1` bar, and the
narrowing of the word "contributing"). `MUST_RESOLVE_BEFORE_ANY_EFFECTIVE_N_VERDICT`
is **discharged for NR-K** and continues to bind NR-L and the mean-overlap unit.

#### 8.3.0 The ruling, as recorded

A ruling received from human + ChatGPT and recorded here as **authority**.

**Ruling NR-K — `P` is the frozen registered Family A pair universe.** For the
current Family A, **`P = 20`**, and the authority object is the **frozen
registered `PAIRS_20` universe** — the registered universe itself, not any count
observed downstream of it.
**`NR_K_RULED_P_EQUALS_FROZEN_REGISTERED_FAMILY_A_UNIVERSE`.**

**What `P = 20` does *not* mean.** Stated first, because it is the misreading this
ruling is most likely to be put to. It does **not** mean that all twenty pairs
must trade; that all twenty must produce non-zero samples; that all twenty carry
equal weight; or that all twenty must show a successful signal. A registered pair
that fires nothing is a **normal outcome**, not a contract violation, and this
ruling creates no obligation for it to fire.

**What it means.** The cross-pair deflator's `P` **may not be shrunk to an observed
contributor count**. `P` is read from the registered universe before anything is
observed, and no downstream observation may reduce it. The following are
**forbidden** as the value or the authority of `P`:

> `len(actual_nonzero_contributors)` · `len(pairs_with_trades)` ·
> `len(pairs_that_passed_performance_filters)` ·
> `len(pairs_remaining_after_correlation_filter)`

— and, generally, **any post-hoc contributor count used as `P` authority**. The
list enumerates a rule, not the spellings it can be written in.

**The word "contributing" is narrowed.** The APPROVED spec's only definition —
"`P` = number of pairs **contributing**" — is read, for the current Family A, as
**contribution eligibility to the registered evaluation universe**, not as later
trade or sample production. The three states are recorded together, because the
record of what changed is part of the ruling:

| | |
| --- | --- |
| **Previous ambiguity** | "Contributing" was undefined in every committed source (§8.3.1), and admitted both *eligible to contribute* and *observed to have contributed*. The second reading is what `effective_n.py` implements. |
| **The ruling** | For current Family A, "contributing" = **eligible to contribute to the registered evaluation universe**. |
| **Current interpretation** | `P` = the cardinality of the frozen registered Family A universe = **20**. Trade production, sample production, weight and signal quality are **downstream of** contribution eligibility and do not enter `P`. |

**The normative clause.**

> **`P SHALL NOT BE REDUCED AFTER FAMILY_A PREREGISTRATION FOR THE PURPOSE OF
> IMPROVING EFFECTIVE_N, CROSS_PAIR_DEFLATION, SAMPLE_SUFFICIENCY, OR RESEARCH
> PERFORMANCE`**

The grounds it covers, named so that none can be re-entered under a different
description: **zero trades · zero sample contribution · weak signal · poor Sharpe ·
poor returns · high correlation · low `N_eff` · sample-floor convenience ·
allocation convenience.** §8.3.5's ground table is the register these map onto;
grounds **E** (sample-floor-driven), **F** (correlation-driven), **G**
(performance-driven) and **H** (zero-contribution) are all closed by this clause.
Ground **H** is worth naming twice, because it is the packet's cheapest lever
(§8.3.2: dropping the zero-trade pairs multiplies `N_eff` by up to 6.70 at
`P = 20`, `c = 0.3`, with the raw floor unable to see the change) and because it
need not be framed as a removal at all — "I did not drop it; it was never
contributing" is exactly the sentence the narrowing above forecloses.

**`P` may not collapse to one.**
**`P_MUST_NOT_COLLAPSE_TO_ONE_BY_POST_HOC_CONTRIBUTOR_SELECTION`.** At `P = 1`,
`rho_x = 1 + (1−1)·c = 1.0` exactly and the cross-pair deflator **vanishes** —
§8.3.1 records that `effective_n()` accepts this today and that **four** committed
tests require a `P = 1` roster to return `SAMPLE_SUFFICIENT` — two at holdout and
two at validation. What is barred is the
**post-hoc route to it**, not `P = 1` as general mathematics: a family whose
registered universe is a single pair is not addressed here, and this ruling says
nothing about it.

**One further reason for the bar, which the recommendation did not reach.**
`effective_n()` echoes `rho_x` but not `cross_pair_corr`. At `P = 20`,
`c = (rho_x − 1)/19` is recoverable from the record; at `P = 1`, `rho_x = 1.0`
whatever `c` was, and the correlation becomes **unrecoverable from the artifact**.
The bar therefore buys auditability of `c`, not only arithmetic.

**Scope: "the current Family A" is meant literally.** A successor family inherits
none of this. Family B is reachable by contract (Ruling 12) after family A closes,
and it would need this ruling **re-taken**, not merely a new universe declared.

**A registered pair that fails does not authorise shrinkage.**
**`REGISTERED_PAIR_FAILURE_DOES_NOT_AUTHORISE_P_SHRINKAGE`.** Where a registered
pair fails, the response is the **existing fail-closed semantics** that already
govern that failure, or **adoption waits** — not a smaller `P`. No new fail-state
vocabulary is invented here, and none may be invented to route around this clause.

**The boundary between this clause and the "normal outcome" above, because both
readings would be damaging.** A registered pair that **fires nothing** is the normal
outcome named above: it triggers nothing in either direction — it neither shrinks
`P` nor halts the family. This clause addresses the different case of a pair that
cannot be **certified** (coverage, schema, cost-cell), and routes that to the
fail-closed semantics already governing it. **Zero trades is not such a failure**,
and may not be argued into this clause from either side: not as a licence (§8.3.5
ground H), and not as a halt.

**A different universe requires a new decision.**
**`NEW_EXPLICIT_PREREGISTRATION_OR_CONTRACT_DECISION_REQUIRED`.** There is to be no
silent transition from twenty to ten, to "available pairs only", to
"best-performing pairs", or to "lowest-correlation pairs". A different universe is
a new explicit pre-registration or contract decision, taken as such.

**Structural invalidity does not silently mutate the authority.** Where a pair is
structurally or contract-invalid, the committed fail-closed semantics apply; what
may **not** happen is that the invalidity quietly rewrites Family A's `P`
authority. §8.3.6 is the material here, and it leaves a residual this ruling does
not close — see "what the ruling does not settle" below.

**`PAIRS_20`, with its three roles kept apart.** It is (1) the frozen registered
universe, (2) the membership authority, and (3) — by this ruling — the `P`
authority for the current Family A. It is **not** an instruction that all pairs
must trade. Implementation flexibility and research authority stay separate: that
a function accepts a short roster is a fact about the function, and **never** a
source of contract authority.

**Disposition — classified, not asserted.** Per limb, and deliberately not
collapsed into one label:

| Limb | Classification | Basis |
| --- | --- | --- |
| `P` reads from the registered universe rather than an observed count | **Ambiguity resolution** | The universe rule already says "fixed, **no selection**" (`pair_authority.py`, Ruling 2), and **prereg §3.2's R-2a-compliance clause** bars inclusion/exclusion decisions "**anywhere in this family**" — the one committed sentence that reaches validation and holdout, since Ruling 2's "fixed PAIRS_20" sits in its design-span clause and R-2a's own bar is design-time. The spec's "contributing" was undefined; the ruling takes the reading that agrees with the universe rule rather than the one that contradicts it. **No committed *sentence* is reversed.** Committed *behaviour* is: this limb is what makes a four-pair roster non-conforming, so the test consequence — and the amendment question in the row below — attach to **this** limb as well as to the next one. |
| The forbidden-substitution list and the `P = 1` bar | **Tightening** | Latitude that existed is removed. `effective_n()` accepts any cardinality in `[1, 20]`, and **sixteen committed tests across four files positively require short rosters to be accepted with a live verdict** — four of them requiring a `P = 1` roster to return `SAMPLE_SUFFICIENT` (§8.3.1). Behaviour that passes today will not pass under this ruling. |
| Whether that tightening needs an amendment procedure | **NOT SETTLED HERE** | The ruling does not contradict the APPROVED spec's sentence — "contributing" is *narrowed*, not replaced — so on its face it is not an amendment of the spec text. But it **invalidates committed tests**, and **no general contract-amendment procedure is registered anywhere in this repository** — `NO_GENERAL_CONTRACT_AMENDMENT_PROCEDURE_REGISTERED` is this packet's own token for that absence, not a citation, and the lead confirmed the token and the phrase "amendment procedure" occur nowhere outside this document. Whether a binding interpretation carrying a test consequence must run an amendment procedure cannot be answered from committed governance, so this packet does **not** assert "not an amendment" **for either limb**. **`NR_K_AMENDMENT_CLASSIFICATION_OF_THE_TEST_INVALIDATING_LIMB_NOT_SETTLED`.** |

**What the ruling settles downstream, and it is more than `P`.** §8.3.8 recorded
that `rho_x = 1 + (P−1)c` is an equicorrelated variance-inflation factor whose `P`
and `c` are two statistics of **one** index set, and that a shrinking `P` would
apply a frozen `c₂₀` to a subset whose true `c_S` is larger — two errors compounding
toward a passing verdict. **A fixed `P = 20` removes that compounding horn
entirely.** What survives is the narrower question of whether `c`'s estimation set
*is* the registered twenty, which is NR-L's.

**What the ruling does not settle.**

- **`P_AUTHORITY_RULED_IMPLEMENTATION_COMPLETENESS_PIN_PENDING`.** No source and no
  test is changed by this packet. `effective_n()` still accepts `P = 1`, and four
  committed tests still require it to. Pinning the implementation is a **separate
  Work PR**; until it lands, the ruling is a contract statement with no code
  enforcement point.
- **`NO_FORWARD_SPAN_FULL_ROSTER_COVERAGE_GATE_COMMITTED`** (§8.3.6) is **not**
  closed. The ruling makes a short forward roster a contract violation; it does not
  supply the gate that would detect one, because `assert_full_coverage` raises for
  any slot outside the design span and `P` decides at holdout. Same residual as the
  pin above, seen from the coverage side.
- **`P_AND_CORRELATION_INDEX_SET_NOT_BOUND`** (§8.3.8) survives as an NR-L item —
  **now HISTORICAL: Ruling c-1 (§8.5.0) binds it to the frozen registered
  `PAIRS_20`.**
- **The purpose limb is not mirrored on the correlation side.** The normative clause
  is written about `P`. But `rho_x = 1 + (P − 1)c` falls in **`c`** as well as in
  `P`, and `corr` arrives as a bare scalar with no pair-set identity attached, so at
  a fixed `P = 20` a correlation-estimation set chosen to lower `c` raises `N_eff` by
  the very mechanism this clause forbids on the `P` side. NR-K does not close it and
  is not extended to close it — writing a `c` prohibition here would rule NR-L by the
  back door. **NR-L must**: an outcome-driven `c`-set is the same defect in the other
  factor. **`OUTCOME_DRIVEN_CORRELATION_SET_IS_THE_SAME_LEVER_IN_THE_OTHER_FACTOR`.**
  **And it is not the smaller residual.** With `P` fixed, `rho_x = 1 + 19c`, so `c`
  now carries the whole of the cross-pair deflator's variability. Against §8.3.2's
  closed form at this document's diagnostic `c = 0.3`: the **forbidden** `20 → 10`
  shrink bought `×1.81` on `N_eff`; a `c` of 0.15 buys `×1.74` and a `c` of 0.05 buys
  `×3.44` — **larger than the shrink just prohibited** — with `P` at twenty
  throughout and every clause of this ruling obeyed literally.
  *`NON_NORMATIVE_DIAGNOSTIC_ONLY`.* Note for NR-L that prereg §3.2's "no
  inclusion/exclusion decisions **anywhere in this family**" — the clause that closes
  §8.3.5 ground G — is on its face the same clause a correlation-estimation subset
  would have to answer to, so NR-L may be **confirming** a bar rather than deciding
  from a blank slate. Whether estimating a statistic over a subset *is* an
  inclusion/exclusion decision in that clause's sense is a contract reading and is
  NR-L's to make.
- **`PER_RECORD_COUNT_PROVENANCE_UNBOUND`** (§8.3.1), which this ruling **promotes**
  rather than closes. `canonical_pair` checks a record's **label**; nothing binds
  that record's `raw_event_count` and `overlap_fraction` to the pair it names, no
  committed test asserts provenance, and `effective_n()` has no production caller.
  With `P`, `rho_x` and the raw total all held constant, re-pairing the same counts
  against the same overlap fractions across the twenty labels moves `N_eff` **alone**.
  Taking the module's own audited B-3 shapes (`50 @ ω = 0.0`, `8000 @ ω = 1.0`,
  `c = 0`) and exchanging only which label carries which: `50/1 + 8000/24 = 383.33 →
  INSUFFICIENT_SAMPLE` becomes `8000/1 + 50/24 = 8002.08 → SAMPLE_SUFFICIENT`, a
  **20.9× swing** on an identical roster, an identical `P = 20`, an identical raw
  total and an identical multiset of reported overlap fractions.
  *`NON_NORMATIVE_DIAGNOSTIC_ONLY`.* No committed check can see it, and the
  implementation pin as described above would not close it — that pin is about roster
  **completeness**.
- **`CONCENTRATION_CAP_DROP_MOTIVE_SURVIVES_NR_K`.** §8.3.7's finding — that
  dropping the highest-share pair can convert a 0.40 cap failure into a pass — is an
  **allocation** question, not a `P` question: `max_trade_share` is computed over the
  **traded** set, so it still moves when a pair stops trading while `P` stays at 20.
  NR-K does not reach it. Recorded, not resolved.

**The correlation pair set is expressly not ruled.**
**`P_UNIVERSE_RULED_CORRELATION_PAIR_SET_STILL_UNRULED`** — **HISTORICAL: Ruling c-1
(§8.5.0) fixes the correlation pair set to the same frozen registered `PAIRS_20`.**
This ruling fixes `P`.
It does **not** fix which pairs `mean_abs_pairwise_corr` is estimated over, by what
method, on what day series, with what idle-day handling, or at what freeze point.
Those are NR-L, and NR-K may not be cited as having settled any of them — including
by the argument that a fixed `P` implies a matching correlation set.

**The concentration cap is unchanged and is a separate authority.** The ≤ 0.40 cap
stands exactly as frozen. It is **not** an authority over `P`, and `P` is not an
authority over it. §8.3.7's arithmetic — that the cap floors the **traded** count
rather than `rho_x`'s `P`, and that against the zero-trade route it is no brake at
all — is unaffected by this ruling and is not repaired by it.

#### 8.3.1 What the committed sources actually say

Reconstructed by reading the sources, not by inheriting a summary.

| Finding | Source |
| --- | --- |
| `n_pairs = len(records)`, bounded **above** by `len(PAIRS_20)` and below **only by non-emptiness** — `P ≥ 1`, with **no completeness requirement**. `rho_x = 1.0 + (n_pairs - 1) * corr`, so **at `P = 1` the cross-pair deflator is exactly 1.0 and disappears entirely** | `scripts/m15_gate3a/effective_n.py` |
| Membership **is** enforced — `canonical_pair` rejects anything outside the universe — and duplicates raise, at a *different* layer (`effective_n.py`, not `pair_authority.py`). **Neither layer enforces completeness** | `pair_authority.py`; `effective_n.py` |
| **Nothing binds a record's counts to the pair it names.** `canonical_pair` checks the *label*; no committed test asserts per-record provenance, and **`effective_n()` has no production caller** — every importer is a test. **`PER_RECORD_COUNT_PROVENANCE_UNBOUND`** | `effective_n.py`; `tests/m15_gate3a/**` |
| **No test pins completeness**, and **sixteen** committed tests across **four** files positively *require* short rosters to be accepted with a live verdict — every one calling `effective_n()` with a roster of fewer than twenty records and asserting a verdict token. **Four** of them require a `P = 1` roster to return `SAMPLE_SUFFICIENT`: two at holdout (`test_raw_floor_boundary_is_pinned`, `test_r2_the_traded_event_quantity_is_admissible`) and two at validation (`test_f3_validation_with_explicit_floors_applies_them`, `test_rf23_validation_is_sufficient_only_when_both_floors_are_cleared`). A ruling for the full roster is therefore **not an additive change**. *An earlier draft said "four committed tests" and cited two files; recounted at source by the lead.* | `tests/m15_gate3a/test_effective_n.py`, `test_recheck_fixes.py`, `test_source_audit_fixes.py`, `test_wp_cost_effn_warmup_status.py` |
| The **only committed definition**: "`P` = number of pairs **contributing**". What "contributing" means is defined **nowhere** | `effective_n_estimator_spec.json` |
| "the frozen PAIRS_20 universe (**Ruling 2 — fixed, no selection**)" | `pair_authority.py` |
| "pair universe fixed at **PAIRS_20** (the 20 inventory pairs — **no inclusion/exclusion decisions anywhere in this family**)" | prereg R-2a compliance clause |
| Coverage: "**Set equality for every pair in PAIRS_20, or raise (D-5, D-10)** … Returns only on the full 20-pair conjunction. There is **no report-only mode and no tolerance parameter**"; a short roster raises `CoverageMeasurementMissingError` | `scripts/m15_gate3a/coverage.py` |
| Concentration is the **max single-pair trade share**, capped at ≤ 0.40 | `scripts/ml_step4/metrics.py`; prereg §9 |

**So the conflict is precise, and it is not a hole in the universe rule.** The
*universe* is fixed at twenty with no selection, in two independent places. The
*estimator's* `P` says "contributing" and its implementation accepts fewer than
twenty without complaint. **Only completeness is unbounded** — membership and
uniqueness are enforced.

**A caution this packet owes itself.** §4 of *this document* proposes that the
pair set used for `P`, the concentration set and `PAIRS_20` "must be the same
twenty". **That is this packet's own proposal, not committed authority** — the
phrase occurs nowhere else in the repository and §13 records §4 as "offered as
ruled text" in a still-`PENDING` packet. An earlier draft of this subsection cited
it as committed; that is withdrawn and must not recur.

#### 8.3.2 The adversarial property, confirmed and quantified

`rho_x = 1 + (P − 1)·c` falls monotonically in `P`, and `N_eff = Σ(N_raw_p/rho_h_p)/rho_x`.
So **smaller `P` → smaller `rho_x` → larger `N_eff`**, mechanically.

**Dropping a zero-trade pair is a strict free gain whenever `c > 0`**: the
numerator and the raw total are summed over the *same* records, so a pair
contributing nothing removes nothing from either while `rho_x` falls. Nothing in
the estimator objects — a zero record is a first-class, test-exercised shape, since
`_require_count` admits `raw_event_count = 0` and only a negative count raises.

**Closed form.** With `P` declared records of which `z` have zero events, dropping
the `z` multiplies `N_eff` by `1 + zc / (1 + (P − 1 − z)c)`. At `P = 20` and the
diagnostic `c = 0.3`: `z = 1 → ×1.05`, `z = 5 → ×1.29`, `z = 10 → ×1.81`,
`z = 19 → ×6.70` — the last being `rho_x = 1.0`, no cross-pair discount at all.
**And the raw ≥ 1,000 floor cannot see any of it**, because the total is
identical; only the `N_eff ≥ 400` floor moves, and it moves toward passing.

(§8.1.9's "`P` is unpinned to the summation" is about the **caller**, not the
function: inside `effective_n` both `n_pairs` and the sums come from one record
list. What is unpinned is each record's counts against the pair it names.)

Earlier measurement in this packet, `NON_NORMATIVE_DIAGNOSTIC_ONLY`: at the
turnover ceiling and corr 0.3, the floors are reached in **67 weekday days at
`P = 20` against 37 at `P = 10`** (§0.6).

#### 8.3.3 NR-K1 — what exactly is `P`?

Candidate readings, none of which committed text uniquely selects:

full registered `PAIRS_20` count · design-universe count · available-data pair
count · valid-schema pair count · coverage-passing pair count · pairs producing
trades · pairs contributing non-zero samples · portfolio allocation count · pairs
surviving some filter · another committed concept.

**Recorded as a definition conflict, not silently merged:** the spec says
"contributing"; `pair_authority.py` and R-2a say the universe is fixed at twenty
with no selection; the implementation accepts any cardinality from 1 to 20.
**`P_DEFINITION_CONFLICT_SPEC_CONTRIBUTING_VS_UNIVERSE_FIXED`.**

**And `P` was not bound across roles.** The spec requires reporting
`per_role: ["validation","holdout"]` but nowhere requires the *same* roster at
each, and `effective_n` is a separate call per role with its own record list. A
validation run at `P = 20` and a holdout at `P = 10` violated nothing committed
**when this was written**.

**Superseded by §8.3.0.** `P` is read from the registered universe *before anything
is observed*, so it is the same registered twenty at design, at validation and at
holdout, and a short **holdout** roster is a contract violation whatever the
validation roster was — which matters because holdout is where `P` decides. The
spec's `per_role` reporting requirement does not license a different roster per
role. What survives is that **nothing detects it**:
`NO_FORWARD_SPAN_FULL_ROSTER_COVERAGE_GATE_COMMITTED` and
`P_AUTHORITY_RULED_IMPLEMENTATION_COMPLETENESS_PIN_PENDING`. Two of the ten
readings have no committed referent at all — "portfolio allocation count" is
defined nowhere in the M15 contract. "Pairs surviving some filter" has no per-pair
*filter* — **but the frozen cost-hurdle threshold is `cost(pair, session)`, a
per-pair-parameterised condition** (Ruling 6). Its *test* is per-event, so a
structurally wide-spread pair can reach **zero eligible events over the whole span
with no pair decision taken by anyone**. That is the mechanism behind ground H, so
this reading is **live**, not dismissed. Note also that "pairs producing trades"
and "pairs contributing non-zero samples" are the **same set**, the only admissible
count quantity being `raw_traded_event_count`.

#### 8.3.4 NR-K2 — when must the universe be frozen?

Candidate boundaries: Family A pre-registration · the design audit · Gate-3a
adoption · the Gate-3a continuation · before any real-data read · after a
structural availability check · before validation · before holdout.

**One of these cannot be the default under this gate.** "After a structural
availability check" requires observing the data, and a real-data read is
**unauthorised** (Q1, default (b)). It is also NR-K3's lever wearing a
freeze-point label: it lets a measured property of the span set `P`.

**The registered universe needs no freeze point — it already has one.** Prereg
§3.2's R-2a-compliance clause and Ruling 2 fixed it at Family A pre-registration and
`pair_authority.PAIRS_20` value-pins it. *(Scope, because the two authorities differ
in reach: Ruling 2's "fixed PAIRS_20" sits inside its **design-span** clause and
R-2a's own bar is design-time, so the one committed sentence reaching validation and
holdout — the roles at which `P` decides — is prereg §3.2's compliance clause. The
stricter reading governs.)* **What is unpinned is the forward epoch**, and the artifacts locate
the gap exactly: the design manifest records `source_pairs = "PAIRS_20 (fixed; no
inclusion/exclusion)"` and the design inventory requires `pair: "one of PAIRS_20"`
with `file_count: 20`, while the forward adoption manifest carries **no pair field**
and omits the pair universe from its deferral block, and the forward inventory's
schema has **no `pair` field and no 20-file assertion**. The spec reports per role
`["validation","holdout"]` — the two roles nothing pins. So the remedy available to
the ruling is a **mirror of an existing committed pin**, not an invention.
**`PAIR_UNIVERSE_FREEZE_POINT_NOT_COMMITTED`**, scoped to the forward epoch and to
`P`'s binding — not to the universe. **Partly discharged by §8.3.0**: `P`'s binding
is ruled — `P` is read from the registered universe, so no separate `P` freeze point
is needed and none precedes the `D` freeze. The **forward-epoch limb survives**, and
the header's Historical list must not be read as retiring more than that.

**And the all-20 posture is committed in more places than §8.3.1 named.** D-5
normative 1–3 ("The roster **exactly equals** the canonical `PAIRS_20`"; "**All 20
pairs are measured**"; "a missing measurement is false/unsatisfied"); D-10's rule
that all `20 × 3 = 60` `(pair, session)` cost cells be present "or
`validate_cost_table` refuses" — a **second independent fail-closed all-20 path**;
and the design inventory's `file_count: 20`. None defines `P`; together they are
the strongest evidence of the contract's posture.

#### 8.3.5 NR-K3 and NR-K4 — which removals are legitimate?

**Eight** grounds, kept distinct, with what committed text says about each. An
earlier draft of this table said "seven" above six rows, merging schema-invalid
with insufficient-coverage — two grounds with **different committed authorities**
(D-2 rules the rejection tolerance; D-5/D-10 rule coverage) — and omitted the
zero-contribution ground entirely, which is the packet's own strongest lever:

| Ground | Committed disposition |
| --- | --- |
| **A. Pre-registered exclusion** | **Empty for family A.** R-2a fixes the registered scope at the twenty, so there is no pre-registered exclusion to invoke. |
| **B. Structurally unavailable** | Not silent — see §8.3.6. The coverage path is **fail-closed**. |
| **C. Schema-invalid observation** | D-2 rules the rejection tolerance **zero and structural**: a rejected minute makes its bucket "**coverage loss**", "visible as a coverage deficit, **not as a silently smaller count**", and a non-zero tolerance "requires a separate contract Gate-decision". **Note the scope**: D-2 speaks to *observation counts*, not to the *pair roster*. Extending it to `P` is an inference, and it is marked as one. |
| **D. Insufficient coverage** | D-5 requires the roster to equal `PAIRS_20` and a missing measurement to be unsatisfied; D-10 makes insufficient coverage **raise**. Fail-closed — but see §8.3.6 for its **span limit**. **And which "coverage" matters**: the contract Gate-decision pins "coverage" among terms "used in **incompatible senses**". Only D-5 set-equality coverage is structural; prereg §9's `daily coverage ≥ 0.60` has a **trades-based numerator** and is an *outcome*, so a removal justified by it belongs with the outcome-driven grounds below, not here. |
| **E. Sample-floor-driven** | Forbidden in substance by `DURATION_SELECTION_MUST_BE_OUTCOME_BLIND`'s sibling logic, but **not by any committed clause naming `P`**. This is the gap NR-K exists for. |
| **F. Correlation-driven** | Same gap, and entangled with NR-L, whose source is fixed to the DESIGN span but whose method and freeze point are unregistered. |
| **G. Performance-driven** | **Barred in text** by the one clause broad enough to reach it — prereg §3.2's R-2a-**compliance** bullet, "no inclusion/exclusion decisions **anywhere in this family**". R-2a's *own* text is narrower: "the pair universe is fixed at PAIRS_20 **by convention** — no pair inclusion/exclusion decisions **at design time**". The family-wide bar therefore rests on prereg §3.2 alone; the stricter reading governs. No clause names `P`. |
| **H. Zero-contribution** — a pair fired no eligible or EV-gated events | **No committed disposition, and the fail-closed defences do not reach it.** Coverage certifies M15 **slots**, not **events**, so a zero-trade pair is *fully certified*, nothing halts, and the roster is complete. `raw_event_count = 0` removes nothing from the numerator while `rho_x` falls. This is the only ground on which the spec's own word "contributing" reads as *licence* rather than as a gap, and it is the **cheapest route to the floors**. It need not even be framed as a removal: "I did not drop it; it was never contributing." |

**The adversarial default, stated because the table would otherwise read as a
menu.** Under committed authority the number of legitimate `P`-reducing removals
for family A may be **zero**, and each row must be argued *against* a fail-closed
halt rather than assumed available. If the first continuation halts because a pair
cannot be certified, **that is the contract working** — a `P`-reducing remedy would
be a relaxation needing its own Gate-decision, not a reading of the word
"contributing".

#### 8.3.6 The structural-invalid consequence — three semantics, and what committed text supports

If one pair cannot satisfy required coverage or schema:

1. **Family A fails closed.**
2. The pair is excluded and `P` shrinks.
3. The pair is excluded but the deflator keeps the original universe count.

**For the coverage path, committed text supports (1) and only (1).**
`assert_full_coverage` "Returns only on the full 20-pair conjunction. There is no
report-only mode and no tolerance parameter", a short roster raises
`CoverageMeasurementMissingError`, and D-10 rules that insufficient coverage
**raises rather than being recorded as a flag**. A pair that cannot be certified
**halts the continuation**; it is not dropped, and `P` does not shrink.

**And the halt is span-limited — which is the more serious limitation.**
`assert_full_coverage` raises for **any** expected slot outside
`[DESIGN_START, DESIGN_END]`, unconditionally and with **no role parameter**, so as
committed it can certify only the **design** span. But `P` decides
`INSUFFICIENT_SAMPLE` at **holdout**. **There is therefore no committed full-roster
coverage gate on the forward spans at all**: "an uncertifiable pair halts" is
established for the design derivation and **unestablished at the roles where `P`
bites**. **`NO_FORWARD_SPAN_FULL_ROSTER_COVERAGE_GATE_COMMITTED`.**

**Nor does the forward artifact supply one.** The *design* inventory pins
`"pair": "one of PAIRS_20"`; the **forward** inventory's
`required_schema_when_populated` is `filename · sha256 · size_bytes · ts_min_utc ·
ts_max_utc · role` — **no pair field, no universe constraint, no cardinality
requirement**. A forward inventory shipped with ten files yields `P = 10` with no
committed rule broken. "The universe is fixed at twenty in two independent places"
is true of the **design** span and has **no artifact enforcement forward**.

**What is *not* settled** is whether that fail-closed semantics reaches the
effective-N estimator at all. Coverage and `effective_n` are different modules with
different rulings — D-5/D-10 govern coverage, not `rho_x` — and the estimator
accepts a short roster silently. **Two modules of one gate package therefore take
opposite roster positions over the same universe.** Semantics (3) is coherent and
is nowhere considered in committed text; it is put here because it is the option
that preserves the deflator's meaning while allowing a pair to be uncertifiable.

#### 8.3.7 Interaction with the concentration cap

Shrinking `P` does not move `N_eff` in isolation — **but the cap constrains a
different pair set, and an earlier draft of this subsection missed that.**
`pair_contribution` iterates the **trade list**, so only pairs that actually traded
get an entry and the maximum is taken over the **traded** set. Shares sum to one,
so `max ≥ 1/P_traded` unconditionally (no uniform-allocation assumption needed) and
`max ≤ 0.40` forces **`P_traded ≥ 3`** — a floor on the *traded* count, **not** on
the `len(records)` `P` that enters `rho_x`. The two coincide only under §8.3.8's
Option C, so treating the cap as a floor under `P` silently presumes the reading
this packet says is unruled.

**And against the zero-trade route it is not a weak brake but no brake at all.** A
pair with no trades produces no `pair_contribution` entry, so declaring it or
omitting it leaves `max_trade_share` **identical**. The cap binds nothing between
`P = 20` and `P = 3`, *and* nothing whatever on §8.3.2's free-gain route. Recorded
as an interaction, not a control, and **this packet does not change the 0.40 cap.**

**It can also be a motive to drop, not only a brake.** Because the maximum is taken
over a smaller set, dropping the highest-share pair can turn a cap failure into a
pass — illustratively `0.45 / 0.20 / 0.20 / 0.15` fails, and dropping the 0.45 pair
gives `0.364 / 0.364 / 0.273`, which passes. That is an outcome-driven removal
wearing a **frozen acceptance criterion** as its justification, and it belongs with
the outcome-driven grounds in §8.3.5.

**One authority caveat.** The **0.40 value** is committed for family A (prereg §9);
the **quantity** is not. "Pair trade concentration" is defined in no family-A
document, and its only implementation is M1-lineage — which prereg §11 admits only
"reusable after **audit/wrapping**" and which PR #444's D-1 bars from being cited
as authority for a family-A design semantic. `scripts/m15_gate3a/` contains no
concentration metric. A consequence for §4's proposal: "the same twenty" is **not
implementable as that metric stands**, because it never consults `PAIRS_20`.

#### 8.3.8 The distinction the readings list does not draw — and why the form cares

**`rho_x` has *two* pair sets, and nothing binds them.** `P = len(records)` is the
set whose **events enter the numerator**. `c` arrives by a wholly separate route —
a bare scalar keyword validated only as a finite number in `[0,1]`, with **no
pair-set identity attached, neither in the call nor in the returned record** — and
the spec defines it over "per-pair **daily PnL** series … estimated on **DESIGN**
data only and frozen", a different object on a different span. The one committed
sentence juxtaposes `P` and `c` and never says they index the same set.
**`P_AND_CORRELATION_INDEX_SET_NOT_BOUND`** — assigned to neither NR-K nor NR-L
when this was written; **§8.3.0 and §8.3.11 assign it to NR-L**, `P` being ruled.

**Why that matters for the formula.** `rho_x = 1 + (P−1)c` is the classical
**equicorrelated variance-inflation factor**: for a sum over an index set `S`,
`Var(Σ) ∝ P[1 + (P−1)c_S]` where `c_S` is the mean off-diagonal correlation **over
`S`**. `P` and `c_S` are two statistics of **one** set. The code treats them as
independent inputs. Three consequences:

- **Applying a frozen `c₂₀` to a smaller `P` is correct only under exchangeability —
  and §0.6 already records that PAIRS_20 is not exchangeable**: 40 currency legs
  from 8 currencies, 88 of 190 pair-pairs sharing a leg, "a single scalar mean
  cannot carry that block structure". So under a shrinking `P` the form is not
  merely under-specified; it applies a stale `c` to a subset whose true `c_S` is
  different.
- **The direction is not neutral.** Any plausible `P`-reducing rule retains the
  actively-traded, more leg-sharing core, so `c_S > c₂₀` while the formula keeps
  `c₂₀`: `P` falls **and** `c` is stale-low, two errors compounding toward a
  passing verdict. *A structural argument about sign, not a measurement.*
- **The deflator is a conservative bound, not an estimate** — the spec uses mean
  **absolute** correlation and negatives are refused, so `rho_x` overstates the true
  inflation by construction. Within a construction conservative by design, the
  coherent way to resolve an ambiguity is the one that stays conservative: the
  **larger** `P`. **An argument for Options A/B and against C — not a derivation.**

**None of this rules NR-K.** It changes what the ruling is choosing between: not
"which population is `P`" alone, but "which population is `P`, **given that `c` was
frozen over a population nobody has recorded**".

#### 8.3.9 The options — HISTORICAL, superseded by Ruling NR-K

Retained as the material the ruling was taken on. The ruling takes **Option A's
cardinality on Option B's authority object**: `P` is the cardinality of the frozen
*registered* universe, which for current Family A is twenty. Option C is
**refused**, and refused explicitly rather than by omission — it is the implemented
behaviour, so the refusal is what §8.3.0 classifies as a tightening.

**Option A — `P` = registered `PAIRS_20`, permanently (always 20).**
*For:* strongest against sample-shopping; simple; exactly reproducible; matches
`pair_authority.py`'s "fixed, no selection" and R-2a. *Against:* if a pair is
genuinely uncertifiable, the deflator counts a pair that contributed nothing.
An earlier draft answered that the case "**halts** rather than proceeding, so the
objection may be moot" — **that dismissal is unsound**: the halt is bounded to the
design span (§8.3.6) and `P` decides at holdout, where no full-roster gate exists.
The objection stands, and the honest answer is that the resulting error is
**conservative** — `rho_x` too large, `N_eff` too small, `INSUFFICIENT_SAMPLE`
firing more readily — where Option C's error runs the other way. Collides verbally
with the spec's word "contributing".

**Option B — the universe is frozen pre-data; `P` is that frozen cardinality.**
*For:* handles structural exclusions **before** anything is observed; outcome-blind
by construction. *Against:* needs an eligibility authority that does not exist, and
the boundary against availability-driven judgement is exactly where the lever
lives.

**Option C — `P` = the actual contributing count.**
*For:* the estimator's own word, and arguably its natural semantics. *Against:*
every disappearance — no trades, weak signal, high correlation, failed coverage —
shrinks `P` and **improves** `N_eff`. This is the largest researcher degree of
freedom in the estimator and it is currently the *implemented* behaviour.

**Option D — an authority-derived alternative**, if the ruling finds one this
packet did not.

#### 8.3.10 The recommendation that was offered — and what the ruling did with it

**Adopted, and extended.** Ruling NR-K adopts this recommendation's substance: the
universe is frozen outcome-blind and `P` is taken from it, and a pair that later
shows no trades, a weak signal, high correlation or a low sample contribution does
not shrink `P` on that ground alone. Three things the ruling supplies that the
recommendation did not:

- an **enumerated** list of forbidden `P` substitutions, closing the spellings as
  well as the rule;
- an explicit **`P = 1`** bar, which the recommendation's wording did not reach and
  which matters because `rho_x` vanishes exactly there;
- a **narrowing of the word "contributing"** itself, rather than leaving the spec's
  term standing beside a rule that contradicts its natural reading.

**And one thing the ruling closed that the recommendation left open.** The
recommendation deferred the structurally- or contract-invalid case to the ruling.
The ruling answers it: existing fail-closed semantics or adoption waits, never a
smaller `P`, and no new fail-state vocabulary. What remains open is not the rule
but its **enforcement point** (§8.3.0, `NO_FORWARD_SPAN_FULL_ROSTER_COVERAGE_GATE_COMMITTED`).

The subsection below is the recommendation as it was offered, retained unedited as
the record of what was put to the ruling.

##### 8.3.10a Recommendation as offered

**Freeze the registered Family A pair universe outcome-blind, and take `P` for the
`N_eff` computation from that frozen universe authority.** A pair that later shows
no trades, a weak signal, high correlation or a low sample contribution **does not
shrink `P`** on that ground alone. Whether a *structurally or contract-invalid*
pair is excluded from `P` is left to the ruling, because §8.3.6 shows committed
text answers it for coverage and is silent for the estimator.

*Authority:* R-2a and `pair_authority.py` both fix the universe with no selection;
`coverage.py` shows the contract's full-roster posture. *Benefit:* it closes the
arithmetic lever without touching the universe rule or the concentration cap.
*Risk:* it does not by itself pick between §8.3.3's readings, and it needs the
freeze point §8.3.4 says nobody has fixed. *Contract amendment:* likely none for
Option A or B; Option C would need one to be *constrained*, since it is what the
code does today.

**Proposed normative wording** (for the ruling to adopt, amend or reject):

> `PAIR_UNIVERSE_SELECTION_MUST_BE_OUTCOME_BLIND`, and **`P` SHALL NOT be reduced
> after the pair-universe freeze for the purpose of improving `N_eff`, cross-pair
> deflation, sample sufficiency, or research performance.** Structural or
> contract-invalid pairs are handled by the fail-closed semantics that already
> govern them, not by silently shrinking `P`.

**This was a recommendation, not a ruling, and may not be cited as one** — cite
§8.3.0, which is the authority, and which differs from it in the three respects
listed above.

#### 8.3.11 Why it was not derivable, and what stays separate

**Why it needed a ruling — HISTORICAL, now discharged by §8.3.0.** There was
**one** committed definition of `P` — "contributing" — and it was undefined; the
universe rule and the estimator's implementation pointed opposite ways; and no
committed source fixed a freeze point. The `coverage.py` asymmetry was *evidence of
the contract's posture*, not a definition of `P`, because D-5/D-10 rule coverage and
not `rho_x`. That is why an AI could not settle it, and it is why the ruling was
required rather than derived. Retained as the record of the referral's basis.

**Kept separate, and not ruled by §8.3.0.** **NR-L** — correlation source fixed to
the **DESIGN span only, never validation/holdout**; method, idle-day handling, day
attribution, freeze point and **pair set** all unregistered
(`P_UNIVERSE_RULED_CORRELATION_PAIR_SET_STILL_UNRULED` — **historical since Ruling
c-1**). **The mean overlap
fraction** — `rho_h`, not `rho_x`; a different deflator and a different question,
now carried as its own packet at **§8.4**. The ruling decided only whether the pair
universe may be changed to advantage, whatever the correlation turns out to be.

**The seam is now assignable.** Whether `c`'s estimation pair set must equal `P`'s
pair set was an NR-K1 question by subject and an NR-L question by object. With `P`
ruled, only the correlation side is still free, so
**`P_AND_CORRELATION_INDEX_SET_NOT_BOUND` is assigned to NR-L**, which **closed it at
Ruling c-1** — and §8.3.0 records
what that ruling bought: a fixed `P` removes the compounding case where a stale
`c₂₀` would be applied to a shrinking subset with a larger true `c_S`.

**Order** (refining §8.2.8 steps 2–3 and carrying its step 8 forward): NR-K —
**ruled** (§8.3.0) → **mean-overlap unit and aggregation — ruled** (§8.4.0) →
**NR-L** (§8.5, **ruled** with Q10(i)) → Q10(iii) → duration-boundary arithmetic → the exact
`T_v` / `T_h` / `D` declaration → the remaining Minimum Research Gate questions
(Q1, Q8, FR-19 and the rest of §8) → **and only after every *other* minimum-gate
requirement is resolved may execution authorisation be considered at all.** This is
the recorded order; it is restated at §13 and it is not a suggestion about
convenience.

### 8.4 Mean overlap fraction — RULED. Clock, formula, aggregation, freeze

**`MEAN_OVERLAP_RULED_EVENT_LEVEL_SAME_HORIZON_CLOCK_EQUAL_WEIGHT_ROLE_LOCAL`** ·
**`MEAN_OVERLAP_CLOCK_SUBSTRATE_RULED_APPROVED_CALENDAR_ELIGIBLE_SLOTS`** ·
**`OMEGA_CALENDAR_AUTHORITY_RULED_SINGLE_FROZEN_VERSION_REQUIRED`** ·
**`OMEGA_CALENDAR_AUTHORITY_RULED_PENDING_APPROVED_CALENDAR_INSTANTIATION`** ·
**`MEAN_OVERLAP_FULL_SEMANTICS_RULED_PENDING_CALENDAR_INSTANTIATION`**

**The semantics are near-complete; the instantiation is not.** The substrate, the
unit, the transform order, the weighting, the endpoint cases, the aggregation, the
pair identity, the freeze and the no-redesign rule are now ruled. **One limb is
not**: the horizon's behaviour at a role-span boundary
(`ROLE_SPAN_HORIZON_TRUNCATION_RULE_NOT_REGISTERED`). The rollover/holiday **membership
outcome** was the second such limb — Ruling ω-12(b) rules its *ownership* (A decides,
`ω` derives no rule) and leaves the outcome to A's content — until Ruling ω-13
classified that outcome a `RUNTIME_CALENDAR_INSTANTIATION_OUTCOME`; it is **documented
and not closed**. The operative status is therefore
**`MEAN_OVERLAP_MINIMUM_RESEARCH_CONTRACT_RULED_PENDING_CALENDAR_INSTANTIATION`**
(Ruling ω-13) — the contract semantics are **ruled for Minimum Research Gate purposes,
with instantiation pending**; "closed" is avoided, because R-9 requires the overlap
fractions to be shown with every reported `N_eff` and no authoritative `ω` is
measurable before the artifact exists. The earlier
`MEAN_OVERLAP_SEMANTICS_RULED_EXCEPT_ROLE_SPAN_AND_ROLLOVER_PENDING_CALENDAR_INSTANTIATION`
is **historical** as to its rollover limb only. The **role-span truncation limb** is
**not** classified by ω-13 — it is not among the six residuals — and it is carried
**unclassified**, with `ROLE_SPAN_TRUNCATION_ARM_SELECTION_POINT_NOT_BOUND` recording
that nothing binds *when* the arm is chosen.
Historically, and retained because it records what the earlier rounds held: **two**
limbs remained semantic. Ruling ω-12(b) rules the rollover limb's **ownership**
(A decides membership; `ω` derives no rule), and its **outcome** stays A's content, so
the limb is not discharged. *An intermediate drafting recorded it as ruled outright and
dropped "AND_ROLLOVER" from the token; **withdrawn**.* `MEAN_OVERLAP_FULL_SEMANTICS_RULED_PENDING_CALENDAR_INSTANTIATION`
is the ruling's own wording and is retained beside it, qualified rather than dropped,
because a review found the word "full" would bury a semantic residual inside an
instantiation token.

**No empirical readiness is claimed**: `ω` cannot be authoritatively computed until the
approved calendar artifact exists (`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`),
and this packet creates no calendar.

**Status change.** `MEAN_OVERLAP_PENDING_HUMAN_CHATGPT_RULING` and
`MEAN_OVERLAP_CORE_DERIVED_READY_FOR_REVIEW` are **HISTORICAL — SUPERSEDED BY HUMAN +
CHATGPT RULING** (§8.4.0). `MEAN_OVERLAP_FRACTION_UNIT_NOT_REGISTERED` is
**discharged** — Ruling ω-1 ties the gap's unit to `H`'s and **Ruling ω-11 names that
substrate**: the approved-calendar eligible M15 slot sequence. The intermediate token
`MEAN_OVERLAP_UNIT_TIED_TO_AN_UNREGISTERED_HORIZON_CLOCK` is therefore **also
historical**. What replaces it is not a residual freedom but a **precondition**:
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` binds `ω`, so the semantics
are ruled and the **instantiation waits** —
**`MEAN_OVERLAP_FULL_SEMANTICS_RULED_PENDING_CALENDAR_INSTANTIATION`**. *An
intermediate version of this line said "discharged — the unit is ruled" before the
substrate was named, which was wrong then and is right now for a different reason;
the correction history is kept at §12.9.*
`MUST_RESOLVE_BEFORE_ANY_EFFECTIVE_N_VERDICT` is **discharged for the mean overlap
fraction** and continues to bind **NR-L** (§8.5). §8.4.1–§8.4.15 are the material the
ruling was taken on and are retained as supporting record, except where §8.4.0
supersedes them: **§8.4.13's option set is historical** (Option B is refused),
**§8.4.14's recommendation is what the ruling largely adopted** — with the
differences recorded at §8.4.0 — and the pending-status paragraphs of §8.4.15 are
superseded by §8.4.0's own status block.

#### 8.4.0 The ruling, as recorded

A ruling received from human + ChatGPT and recorded here as **authority**. It is set
out limb by limb, and each limb is marked with **what actually backs it** — because
four limbs were *derived from committed text and are here confirmed*, and six are
**explicit human + ChatGPT choices that no committed source makes**. §18 of the
instruction is explicit that not every limb may be labelled "derived", and this
section does not.

##### Ruling ω-1 — the gap clock is the horizon's clock

**`MEAN_OVERLAP_GAP_CLOCK_RULED_SAME_REGISTERED_M15_PREDICTION_CLOCK_AS_HORIZON`** ·
**`GAP_AND_HORIZON_MUST_USE_THE_SAME_REGISTERED_M15_PREDICTION_CLOCK`**

`g` and `H` are measured on **the same registered M15 prediction-horizon clock**.
Because `H` is frozen at **24 M15 bars**, the gap may **not** be switched — **as a
clock different from `H`'s** — to elapsed UTC wall-clock hours, to a weekday count, to
a trading-day count, to an event-index count, or to an arbitrary continuous-grid
count while `H` stays in bars. *The qualifier is load-bearing: a **shared**
continuous-grid reading of both quantities is arithmetically identical to a shared
elapsed-hours reading, since `g/H` is scale-invariant, and this list does not exclude
it — §8.4.4 keeps the continuous grid live as a reading of `H`. What is barred is a
**mismatch**, not a spelling.*

*Backing: **explicit human + ChatGPT choice.*** §8.4.2 and §8.4.4 record that no
committed source fixed the gap's unit. What **was** derivable is only the weaker
`GAP_AND_HORIZON_MUST_BE_READ_ON_THE_SAME_CLOCK` (D-ω-2a) — that a *fraction of a
horizon* needs both lengths on one clock. The ruling goes further and names **which**
clock: the horizon's. That is new normative content.

**It authors no market-hours semantics.** No holiday rule, no weekend rule, no
closure rule, no DST rule and no session calendar is created here. The clock is
whatever **already-approved bar/bucket/calendar authority gives `H = 24` its
meaning** — this ruling adopts that authority, it does not constitute one. Where that
clock cannot be instantiated without the approved calendar artifact,
**`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` remains binding**, and no
calendar artifact is created by this packet.

**The name is the ruling's own coinage, and "registered" is a reference and not a
registration.** No committed source names an "M15 prediction clock": the phrase
occurs nowhere in this repository outside this document. §8.4.14 withdrew the
near-identical phrase from *this packet's* recommendation as "a coined unit this
packet may not introduce", and **that withdrawal stands** — the distinction being
that a ruling may coin a term where the packet may not. What the term refers to
ostensively is real in part and absent in part: prereg §4's bucket rule exists
(`floor(timestamp / 15 min)` on the UTC clock, bar timestamp = bucket start, no DST),
while `scripts/m15_gate3a/` carries `HORIZON_M15_BARS = 24` and **no counting rule at
all**, and the slot set needs an approved calendar artifact that does not exist. So
this limb binds `g` to an authority that is **partly unregistered**.
**`M15_PREDICTION_HORIZON_CLOCK_IS_COINED_BY_THIS_RULING_NOT_REGISTERED`.**

**And it *narrows* the favourable-reading route §8.4.11 A-ω-5 records — it does not
close it. An earlier version of this paragraph said it closed the route, and that is
withdrawn.**
**`OMEGA_CLOCK_MUST_NOT_BE_SELECTED_TO_MINIMISE_RHO_H_OR_INCREASE_N_EFF`.** A-ω-5
recorded that a continuous-grid reading is weakly `ω`-minimising *for every dataset*,
so the feasibility-favourable end of the unit question was knowable with no data at
all and a pre-data freeze alone did not protect it. Tying the gap clock to the
horizon's removes the **mixed** readings and the non-bar ones. **It does not remove
the choice**, because which clock the horizon's *is* remains unregistered: `H = 24`
on either surviving bar reading, so `g` on the continuous grid is `≥` `g` over bars
that exist for **every** consecutive pair, and under `max(0, 1 − g/H)` the
continuous-grid reading stays weakly `ω`-minimising for every dataset. §8.4.4's own
leverage illustration — one contribution at `0` against near `1` across a closure — is
a contrast between **two clocks this ruling leaves live**, so the full width of that
lever survives. What is removed is taking the favourable clock for `g` against a
differently-read `H`. **A-ω-5's conclusion therefore stood at this limb: it bars the
motive, and A-ω-5 already recorded that "outcome-blindness is necessary and not
sufficient — MO-2 needs a reason, not merely a timestamp."**
**Ruling ω-11 supplies that reason** by naming the substrate and binding it to an
external authority; this paragraph records what ω-1 alone did and did not achieve,
and ω-11 is where the route is closed.

**Q10-A is expressly not the authority for this.**
**`Q10_A_ELAPSED_UTC_DURATION_DOES_NOT_DEFINE_MEAN_OVERLAP_GAP_UNITS`.** `D` is an
elapsed UTC calendar span; that governs the **duration axis** and may not be carried
across to the **event-spacing axis**, which is what §8.2.0's own guard-rail
(`D_IS_ELAPSED_UTC_TIME != SAMPLE_COUNT_IS_CALENDAR_TIME`) says by naming *overlap*
among the quantities that keep their own authorities.

**One consequence worth stating, because it repairs *part* of a derivation — and two
limits on it.** §8.4.10's D-ω-2 was conditional on three things, the third being that
`H` is a **constant, contiguous length on the chosen clock**. Under this ruling `g`
and `H` are read on one clock, so the **mixed-unit** half of that condition is
removed — which D-ω-2a had already derived.

**The rest is not discharged in general, and an earlier version of this paragraph
said "discharged by construction", which is withdrawn.** The committed horizon is 24
M15 **bars**, so `H` is 24 *units of the clock* only where the clock's unit is the
bar — the **bars-that-exist** reading. On the **continuous UTC grid** reading, prereg
§4's "no synthetic bars across market close" means 24 bars occupy **more than 24 grid
slots** wherever a slot carries no bar, so `H` in grid units is neither constant nor
contiguous and varies with where in the week the horizon opens. On the **complete
buckets only** reading, §8.4.4 records that "whether such bars consume horizon is
unregistered", so 24 bars is not 24 complete buckets. §8.4.10 names exactly these
clocks as the ones where the condition fails. **Ruling ω-1 alone** expressly did
**not** register which of the three `H` counts, so on ω-1 alone the third condition
was discharged **only on a bars-that-exist reading**, and there only for events whose
horizon lies wholly inside the role span. **Ruling ω-11 registers the substrate and
discharges it except at the role-span boundary** — on the eligible-slot sequence `H`
is 24 *consecutive* units of that index for every event. Where it is not discharged, §8.4.10's flat-then-linear
`max(0, min(L_i − g, L_{i+1}))/L_i` governs and `max(0, 1 − g_i/H)` stands as the
**stipulation** §8.4.10 labels a reading — not as a derivation.
**`OMEGA_H_CONSTANCY_DISCHARGED_ONLY_ON_A_BARS_THAT_EXIST_READING`.**

**It is not discharged at the role-span boundary, and that is stated rather than
glossed.** An event firing within `H` of the end of its role span has a horizon that
is either **truncated** — shorter than 24 units, so the equal-length premise fails for
that interval — or **excluded**, in which case the event is not in the index at all.
Committed M15 machinery carries **no rule either way**: the only positional
implementation, `scripts/ml_step4/labels.py`, *excludes* such bars
(`if … i + horizon + 1 >= n: continue`), but it is unadopted M1-lineage code that
prereg §11 admits only "after audit/wrapping". §8.4.15 records this as an adjacent
gap; the ruling does **not** fill it, and D-ω-2's discharge is scoped accordingly.
**`HORIZON_TRUNCATION_AT_ROLE_SPAN_BOUNDARY_NOT_REGISTERED`** — and it bears on MO-5's
last-event limb, since at the small `n` §8.4.12 shows is decisive one truncated
horizon is not negligible.

##### Ruling ω-2 — event-level transform, then arithmetic mean

**`MEAN_OVERLAP_USES_EVENT_LEVEL_TRANSFORM_THEN_ARITHMETIC_MEAN`**

For each registered same-pair **adjacent** event interval:

> `overlap_i = max(0, 1 − g_i / H)`

and then

> `ω_p = arithmetic_mean(overlap_i)` over **every** adjacent same-pair event interval
> of pair `p`, exhaustively — all `n − 1` of them for a pair with `n` events

— that is **`E[f(g)]`, and not `f(E[g])`**.

*Backing: **derived, and here confirmed.*** The transform is D-ω-2 (interval
arithmetic on two equal-length horizons; the `max(0, ·)` is the arithmetic, not a
clamp). The order is D-ω-3 + D-ω-4 (the spec's "**mean fraction**", with the draft
placed as superseded). The **adjacent / next-event** restriction, which §8.4.6 carried
as the open limb MO-1(b), is **confirmed** by this ruling rather than varied.

##### Ruling ω-3 — the mean-gap approximation is not an allowed authority

**`MEAN_GAP_APPROXIMATION_IS_NOT_AN_ALLOWED_EFFECTIVE_N_AUTHORITY_FOR_CURRENT_FAMILY_A`**

The draft formulation `horizon / mean inter-event gap`, and any equivalent mean-gap
shortcut, is **not** the governing Family A estimator and is **not** available as an
alternate implementation choice. It is retained in this document as
**historical / illustrative, marked non-normative**, for traceability only (§8.4.3).

*Backing: **derived, and here hardened.*** D-ω-3 established the draft is superseded
(prereg §9 defers the method "[FIXED-AT design audit or gate 3a]" and labels its own
formula "for the design audit to fix"; T-6 records the APPROVED spec as that fixing).
The ruling adds the **prohibition on re-adopting it as an implementation option**,
which supersession alone did not supply.

##### Ruling ω-4 — equal weight per adjacent event interval

**`MEAN_OVERLAP_WITHIN_PAIR_WEIGHTING_IS_EQUAL_PER_ADJACENT_EVENT_INTERVAL`**

Within a pair, **every adjacent same-pair event interval receives equal weight** in
the arithmetic mean — all `n − 1` of them for a pair with `n` events, **with none
excluded on any ground**. Weighting by **interval length**, by **elapsed time**, by
**trade PnL**, by **the sample count an interval represents**, by **signal strength**,
by **pair performance**, or by **convenient overlap magnitude** is forbidden.

**And no interval-eligibility filter may be introduced, because exclusion *is*
weighting.** A `{0, 1}` weight vector is a weighting, and §8.4.5 records that a
degenerate one reaches the whole of `[1.00, 23.04]` — the very range this limb exists
to close. This clause therefore reaches **exclusion** as well as weighting. *An
earlier drafting of Rulings ω-2 and ω-4 said "applicable" and "eligible" intervals
without defining either; that is corrected, and note that "eligible" is **not** used
here in prereg §6's sense — that term denotes `cost_hurdle_eligible_bar_count`, a
quantity `_require_count_quantity` refuses by name.*

*Backing: **explicit human + ChatGPT choice.*** The spec says "mean fraction" and
stops; an unqualified "mean" reads naturally as the unweighted one, but no committed
source says so, and §8.4.5 records that this limb was **the packet's largest
unquantified lever**: with everything else fixed, weighting alone put `rho_h` anywhere
in the whole admissible range. **This ruling closes that freedom.** The numeric range
recorded at §8.4.5 is `NON_NORMATIVE_DIAGNOSTIC_ONLY` and is **not** the authority for
the ruling — it is the reason the question was put.

**A consequence the review flagged, now settled.** A pair with `n` events has `n − 1`
adjacent intervals, so an equal-weight arithmetic mean over intervals has **`n − 1` in
the denominator**. §8.4.12 recorded that an `n`-denominator reading would answer the
one-event case by arithmetic accident (`0/1 = 0`); under this ruling it does not, and
the one-event case is disposed of explicitly by Ruling ω-6 instead.

##### Ruling ω-5 — zero-event pairs

**`ZERO_EVENT_PAIR_HAS_ZERO_RAW_CONTRIBUTION_AND_NO_SYNTHETIC_OVERLAP`**

For a registered pair with **zero** realised events in the role being assessed:
`N_raw,p = 0`; there are **no** adjacent intervals; `ω` **must not create synthetic
sample contribution**; and `ω` is **inert** for that pair's effective-N contribution.
"No gaps" may **not** be converted into a favourable artificial effective sample.
**The pair is not removed from `P` — NR-K stands, `P = 20`.**

*Backing: **explicit human + ChatGPT choice, consistent with a derivation.*** §8.4.12
derived the *arithmetic* — `0 / rho_h = 0` for every admissible `rho_h` — and derived
from §8.3.0 that a flatly fail-closed reading would **halt the family on a normal
outcome** (`ZERO_EVENT_OMEGA_MUST_NOT_HALT_A_NORMAL_OUTCOME`). What the ruling adds is
the positive disposition: inert, no synthetic contribution, pair retained.

##### Ruling ω-6 — one-event pairs

**`SINGLE_EVENT_PAIR_HAS_ZERO_REALISED_NEXT_EVENT_OVERLAP`**

For a pair with **exactly one** realised event: `N_raw,p = 1`; **no** adjacent
same-pair event interval exists; **no** realised horizon overlap with a next
same-pair event exists; therefore

> `ω_p = 0` for that pair's overlap deflator.

**Four things this is not.** The pair **remains** in the frozen `PAIRS_20` universe.
`P` **remains 20**. One event is **not** thereby equivalent to a large effective
sample — the raw contribution remains **one**. And it is **not** permission to shrink
`P` or to cherry-pick sparse pairs.

*Backing: **explicit human + ChatGPT choice** — and the packet says so plainly.* With
zero intervals the arithmetic mean of Ruling ω-4 is `0/0`, **undefined**; the ruling
**stipulates** the value rather than deriving it. §8.4.11's A-ω-2
(`NO_ADJACENT_GAP_DOES_NOT_AUTOMATICALLY_MEAN_ZERO_OVERLAP`) is **satisfied, not
overridden**: it demanded that the value be *decided* rather than reached by the
absence of an alternative, and it has been, on a stated ground — that the realised
next-event overlap is zero because no next event was realised. The residual is
recorded rather than hidden: a one-event pair contributes `1 / (1 + 23·0) = 1.000`
to `Σ N_eff_pair`, the largest value that record can take, and §8.4.12's bound on the
whole lever (**≤ ~4.5% of the 400 floor at `c = 0`, ≤ 0.7% at the diagnostic
`c = 0.3`**, `NON_NORMATIVE_DIAGNOSTIC_ONLY`) is what sizes it.

##### Ruling ω-7 — pair-local aggregation, and no pooling

**`MEAN_OVERLAP_IS_COMPUTED_PAIR_LOCALLY`** ·
**`GLOBAL_CROSS_PAIR_GAP_POOLING_IS_FORBIDDEN`**

For each registered pair `p`: `rho_h,p = 1 + 23·ω_p`, and effective-N uses the
existing pair-level structure. **No single global pooled `ω` across all pairs.**

*Backing: **derived, and here confirmed.*** D-ω-5: the spec's own "estimated **per
pair** from the realised inter-event gaps", `per_pair_effective`, `granularity:
[portfolio, per_pair]`, and B-3 as a **recorded defect**. The ruling adds the explicit
prohibition, which matters because §8.4.11 A-ω-6 records that the rule was committed
while its **enforcement** was not — one shared `ω̄` in twenty slots reproduces the
pre-B-3 collapse exactly.

##### Ruling ω-8 — registered pair identity

**`PAIR_LABEL_ASSIGNMENT_MUST_NOT_BE_REARRANGED_TO_REDUCE_OMEGA`**

Events remain assigned to their **registered pair labels**. Forbidden: re-pairing
events between labels; reassigning event counts to lower `ω`; pairing across
currencies to minimise overlap; relabelling intervals after observing gaps.

*Backing: **rule derived; the prohibition and its scope are the ruling's.*** The rule
is the same spec sentence Ruling ω-7 rests on. What was missing was any enforcement —
`canonical_pair` checks a **label** — and §8.3.0 records the counterpart lever on the
count side. The **20.9×** swing recorded at §8.3.0 and §8.4.11 remains
**`NON_NORMATIVE_DIAGNOSTIC_ONLY`** and **may not be used as contract authority**.

##### Ruling ω-9 — method frozen pre-data; value measured role-locally

**`OMEGA_METHOD_IS_PRE_DATA_FROZEN_OMEGA_VALUE_IS_ROLE_LOCAL_MEASURED`**

Two things are separated and disposed of differently:

| | |
| --- | --- |
| **Method / formula authority** | **Frozen before data.** This covers the **clock**, the **overlap function**, the **`E[f]` order**, the **equal weighting**, the **pair-local aggregation**, the **zero- and one-event semantics**, and the **pair-identity rule** — every limb above. |
| **The realised `ω` value** | **Mechanically calculated** from the registered realised event sequence of **the role whose `N_eff` is being evaluated**. |

*Backing: **explicit human + ChatGPT choice.*** §8.4.2 records that `ω` carries **no
span scope at all**, where the correlation carries "DESIGN span only … frozen once and
recorded". Nothing committed said when `ω`'s method is fixed or which role supplies
its value. This ruling supplies both, and it resolves the asymmetry in the *opposite*
direction from `c`: `c` is frozen on DESIGN and reused; `ω` is a **role-local**
measurement under a **pre-frozen** method. The two are different objects and the
difference is deliberate — `ω` describes the sample structure of the span being
judged, `c` describes a dependence estimated before it.

**Holdout use, and what it does not authorise.** The frozen numeric floors are
holdout floors — the spec's `failure_handling` puts `N_eff < 400` and the `≥ 1000 raw`
conjunction at holdout, while the validation branch reads "insufficient … per the
frozen contract" against a *family minimum* that is itself unregistered. Where the
acceptance floor is the holdout one, its effective-N verdict uses `ω` measured
mechanically from the **frozen holdout event sequence**.
**`MEAN_OVERLAP_RULING_DOES_NOT_AUTHORISE_REAL_DATA_ACCESS`** — this defines a future
calculation for after every access gate is authorised, and authorises nothing now.

##### Ruling ω-10 — measurement determines the verdict, never the design

**`MEASUREMENT_MAY_DETERMINE_THE_VERDICT_BUT_MUST_NOT_REDIRECT_THE_EXPERIMENT`**

Once measured, `ω` may decide the registered effective-N verdict. It may **not** be
used to change `D`, `T_v`, `T_h`, the window anchor, `P`, the pair universe, the
event assignment, the overlap method, the weighting, the research iteration, or the
model design.

*Backing: **explicit human + ChatGPT choice**, and the direct sibling of
`DURATION_SELECTION_MUST_BE_OUTCOME_BLIND` (§8.1.0) and of §8.3.0's non-reduction
clause. Nothing committed states it for `ω`.*

##### Ruling ω-11 — the clock substrate

**`MEAN_OVERLAP_CLOCK_RULED_APPROVED_ELIGIBLE_M15_SLOT_SEQUENCE`** ·
**`MEAN_OVERLAP_CLOCK_SUBSTRATE_RULED_APPROVED_CALENDAR_ELIGIBLE_SLOTS`**

**The problem this closes, stated first because the previous ruling did not close
it.** Ruling ω-1 required `g` and `H` to share a clock. The review found that
insufficient: **at least two shared clocks remained possible** — the continuous UTC
15-minute grid, and the approved-calendar eligible M15 slot sequence — and they
differ materially for events spanning a market closure, so a deterministic
researcher choice survived.
**`SAME_CLOCK_RULE_DOES_NOT_YET_IDENTIFY_THE_CLOCK_SUBSTRATE`** is recorded as that
issue, and this ruling resolves it. *The token is coined here rather than inherited:
the **gap** was recorded at §12.9 ("the ruling removes the **mixed** readings, not the
choice") but carried no name, so a reader will not find this spelling in an earlier
head.*

**The ruling.** For current Family A the mean-overlap prediction clock is

> `MEAN_OVERLAP_CLOCK = APPROVED_ELIGIBLE_M15_SLOT_SEQUENCE`

— **both** `H` and `g` are measured on the **ordered sequence of M15 slots that are
eligible under the approved calendar authority**.

**`H = 24` means 24 consecutive eligible M15 prediction slots on that sequence.** It
does **not** mean 360 elapsed wall-clock minutes unconditionally, 24 arbitrary UTC
grid cells counted through closures, 24 event-index steps, or 24 weekday-derived
slots — except where those happen to coincide with the approved eligible-slot
sequence.

**`g_i` is the distance between two adjacent same-pair event slots, counted in
eligible M15-slot steps on that same sequence.** Elapsed wall-clock closure
duration, an unapproved continuous grid, a weekday or trading-day heuristic, and
event-index spacing detached from the prediction-slot sequence are each **excluded**.

**Why, recorded as substance rather than as preference.**
**`OMEGA_CLOCK_SUBSTRATE_MUST_NOT_BE_CHOSEN_TO_MINIMISE_RHO_H`.** The previous
same-clock ruling removed the mixed-unit readings and left a **deterministic
researcher choice between several shared clocks**, one that can materially alter `ω`
and therefore `N_eff`. The clock is therefore bound to an **external approved
authority** rather than selected. That is the "reason, not merely a timestamp" that
§8.4.11's A-ω-5 said MO-2 required, and it is what a pre-data freeze alone could not
supply.

**The ruling takes the costly branch and the conservative one — both worth saying.**

- **Costly:** §8.4.15 recorded that only the calendar-dependent readings import
  `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`, so the `ω`-minimising
  continuous-grid reading was the **only one instantiable without an unbuilt
  approval**. This ruling selects a calendar-dependent reading, and therefore
  **accepts that approval as a precondition** rather than avoiding it.
- **Conservative:** the eligible-slot sequence is a **subset** of the continuous grid,
  so for **every** pair of adjacent events `g` counted on it is **smaller than or
  equal to** the same gap counted on the grid — with equality wherever no ineligible
  slot intervenes. Since `H` is 24 units of whichever sequence is used, a smaller `g`
  gives a larger `overlap_i`, a larger `ω`, a larger `rho_h` and therefore **smaller
  `N_eff`**. The ruling picks a substrate strictly **more `ω`-conservative than the
  continuous grid**. It is **not** the `ω`-maximising candidate on §8.4.4's table — the
  event-index substrate is, and it is foreclosed (see the amendment table) — so this
  is a direction against the grid, not an extremality claim. *Direction only, and it is a subset argument rather than a claim about any
  closure schedule: `NON_NORMATIVE_DIAGNOSTIC_ONLY`, no magnitude claimed, and no
  market hours presupposed — "ineligible" is whatever the approved calendar says, and
  this packet does not say.*

- **And the substrate is immune to data presence, which matters more than it looks.**
  The eligible-slot sequence is **calendar-derived**, not data-derived: a slot's
  eligibility is a property of the approved artifact, so a data outage does not move
  the clock — it shows up as a **coverage deficit**, where D-5 puts it. That is the
  difference between this substrate and a "bars that exist" reading, which would make
  `ω` a function of data presence and so re-enter the inference D-6 forbids —
  `calendar_authority.py` "never reverse-infers 'there is no data, therefore the market
  was closed'". The ruling therefore avoids that inference rather than merely declining
  it.

**It aligns `ω` with the authority the contract already uses for slots.** D-5 makes
coverage a set equality against an **expected** M15 slot set, and D-6 rules that
expected set "**never inferred from the raw source** — the authority is a versioned,
committed closure/market calendar artifact for the target epoch". This ruling puts
`ω`'s clock on that same authority. *That alignment is supporting reasoning, not a
derivation: D-5/D-6 govern the coverage layer, and extending their authority to `ω`
is the ruling's act.*

**It authors no market-hours semantics, and none may be read into it.** No holiday
list, no closure schedule, no DST behaviour beyond the existing UTC authority, no
exchange sessions, no weekend eligibility rule and no market hours are defined here.
`calendar_authority.py` "**validates an injected calendar. It never authors one**",
and that stands. Those remain the calendar authority's to supply.

**Consequences, and the residual that changes shape rather than disappearing.**

- **`HORIZON_WALL_CLOCK_EXTENT_NOT_REGISTERED` is discharged *as it bears on `ω`*.**
  The substrate is now named for both `g` and `H`. What remains is not a researcher
  choice but an **external dependency**: the artifact that fixes the sequence does
  not exist. **`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` is therefore
  binding on `ω` in terms** — before an approved calendar authority exists, an
  empirical `ω` **cannot be authoritatively instantiated**. There is **no fallback
  continuous-grid clock, no temporary heuristic clock and no inferred market-hours
  clock.** No calendar is generated here.
- **`OMEGA_H_CONSTANCY_DISCHARGED_ONLY_ON_A_BARS_THAT_EXIST_READING` is discharged.**
  On the eligible-slot sequence `H` is 24 **consecutive** units of that index for
  every event, so two horizons are equal-length and contiguous **in that index** by
  construction — which is D-ω-2's third condition. The role-span limb survives
  untouched: `ROLE_SPAN_HORIZON_TRUNCATION_RULE_NOT_REGISTERED`.
- **The lever moves from the researcher to the artifact — and it moves to a place
  with strictly weaker protection.** Whoever authors and approves the calendar now
  determines the sequence `ω` is measured on. That is the right *place* — D-6 puts the
  expected slot set there deliberately — but the move is **not protection-neutral**,
  and this is recorded rather than softened.
  `OMEGA_CLOCK_SUBSTRATE_MUST_NOT_BE_CHOSEN_TO_MINIMISE_RHO_H` binds the **choice of
  substrate**; **nothing binds the calendar's content**. No committed source requires
  calendar authorship or approval to be blind to its `ω` effect, and the approval D-6
  contemplates is an approval **for coverage** — an approver is nowhere told that the
  same artifact now sets `rho_h` and `N_eff`. The prohibition the ruling relies on
  therefore does **not follow the lever to where the lever went**.
  **`CALENDAR_CONTENT_DETERMINES_OMEGA_SUBSTRATE`** ·
  **`NO_OUTCOME_BLINDNESS_REQUIREMENT_BINDS_CALENDAR_CONTENT`** ·
  **`OMEGA_DEPENDENCE_NOT_DISCLOSED_AT_CALENDAR_APPROVAL`**. Whether to attach an
  outcome-blindness clause and a disclosure requirement to the calendar approval is for
  the ruling; this packet names the gap and closes none of it. — **Both are now
  supplied by Ruling ω-12(e)**: `OMEGA_CALENDAR_CONTENT_MUST_BE_OUTCOME_BLIND` and the
  disclosure obligation. The prohibition now follows the lever.
- **The timing asymmetry §8.2.5 named for `D` applies here, and is recorded rather
  than left to be found.** Binding `ω`'s substrate to calendar content makes `ω` a
  function of an artifact's contents. **§8.2.5 rejected an eligible-day `D` on exactly
  this ground** — "a post-freeze duration lever with a perfect alibi", because gate 4's
  T-6 schedules the eligibility calendar for approval *after* the freeze while the
  frozen number never changes. Ruling ω-9 freezes `ω`'s **method**, not the calendar's
  content, so if the rollover/holiday limb resolves toward *calendar*-ineligibility, a
  later approval still moves every `ω` with the frozen method unchanged.
  **`OMEGA_SUBSTRATE_CONTENT_MAY_MOVE_AFTER_THE_METHOD_FREEZE`** — **closed for slot
  membership by Ruling ω-12(a)/(f)**, structurally rather than by prohibition alone,
  since the post-freeze artifact is B and B does not govern membership. It **survives
  for the event set**: `LATER_EVENT_ELIGIBILITY_CALENDAR_MAY_STILL_MOVE_THE_EVENT_SET`,
  bounded conservative by Ruling 4's widen-only clause.
- **And "the approved calendar authority" is itself ambiguous between two artifacts
  with different approval timings.** §8.2.2 records both: the **D-6 closure/market
  calendar**, approved *before* the continuation
  (`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`); and **Ruling 4's holiday /
  thin-liquidity event-eligibility exclusion calendar**, which was `[FIXED-AT design
  audit]` and which "gate 4's **T-6 re-pointed to 'implementation, approved before
  gate 7'** — i.e. **after** the `D` freeze". Ruling ω-11 cites the first and leaves the
  second's relation open, so **which artifact the substrate depends on is not
  determined**, and one branch is a post-freeze artifact. The ruling should say which.
  **`OMEGA_SUBSTRATE_CALENDAR_IDENTITY_NOT_SETTLED`** — **RULED by ω-12(a)**: Authority
  **A**'s `expected_m15_slots` governs, B never does.
- **What the discharge does and does not remove.** Naming the substrate removes the
  *choice between* substrates. It does **not** remove the width:
  `ROLLOVER_AND_HOLIDAY_SLOT_ELIGIBILITY_RELATIVE_TO_THE_OMEGA_CLOCK_NOT_SETTLED`
  carries the same `0`-to-near-`1` leverage on a single contribution that
  `HORIZON_WALL_CLOCK_EXTENT_NOT_REGISTERED` carried — §8.4.4's own illustration,
  now sitting **inside** the ruled substrate rather than between two candidate
  substrates — and the rollover window is **daily**, so it reaches gaps that no closure
  reaches. The discharge is a **relocation** of the residual, not its retirement.
- **"Eligible" here means *calendar*-eligible, and nothing else.** It is **not**
  prereg §6's cost-hurdle sense — "a bar is an **eligible event** only if
  `1.5 × ATR14_M15 ≥ 2.0 × cost`" — which names `cost_hurdle_eligible_bar_count`, a
  quantity `_require_count_quantity` refuses by name. The collision is stated because
  it has already caused one defect in this packet.
- **Whether Ruling 4's event-ineligible windows are also calendar-ineligible slots is
  NOT settled here.** Prereg §5 (Ruling 4, FROZEN as minimum) makes the
  **21:55–22:15 UTC** rollover window and low-liquidity holiday sessions
  **event-ineligible**, and marks the holiday / thin-liquidity exclusion calendar
  `[FIXED-AT design audit]` — which the playbook records as never fixed. Whether
  those slots are absent from the *calendar-eligible* sequence, or present in it but
  barred from carrying events, is a property of the approved artifact and of Ruling 4,
  and this ruling decides neither.
  **`ROLLOVER_AND_HOLIDAY_SLOT_ELIGIBILITY_RELATIVE_TO_THE_OMEGA_CLOCK_NOT_SETTLED`.**

**Amendment classification — per limb.**

| Limb | Classification |
| --- | --- |
| That one substrate governs both `g` and `H`, rather than a choice among several | **Ambiguity resolution.** Ruling ω-1 already required a shared clock; naming which one removes an ambiguity that ruling left rather than reversing anything committed. |
| Foreclosing the continuous grid, elapsed time and weekday/trading-day substrates | **Tightening.** Latitude that existed is removed, toward the conservative end. Nothing committed is reversed. |
| Foreclosing the **event-index** substrate | **NOT a tightening, and recorded as such.** Under MO-1(b) the event-index gap is **identically 1**, so that substrate gives `ω = 23/24` and `rho_h = 23.04` — the **top** of §8.4.5's band and the most `N_eff`-hostile candidate on §8.4.4's table. Foreclosing it therefore removes the **conservative endpoint**. It is foreclosed on the substantive ground that `ω` would be a constant independent of the data, **not** on a conservatism ground, and an earlier drafting folded it into the row above as "removed toward the conservative end", which is false of this limb. |
| Binding `ω` to the **approved calendar authority**, and with it to `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` | **NOT SETTLED.** D-5/D-6 place the expected slot set with that authority for **coverage**; extending it to `ω` adds a requirement no committed source carries, and it makes an empirical `ω` conditional on an artifact that does not exist. Whether such an addition needs a contract-amendment procedure cannot be answered, because **no general contract-amendment procedure is registered anywhere in this repository** (`NO_GENERAL_CONTRACT_AMENDMENT_PROCEDURE_REGISTERED`). **`MEAN_OVERLAP_CLOCK_AMENDMENT_CLASSIFICATION_NOT_SETTLED`.** |

**No favourable classification is asserted here.** The one limb that could have been
called a mere tightening — the external binding — is the one sent to NOT SETTLED.

##### Ruling ω-12 — the four calendar residuals, ruled as one

**`OMEGA_CALENDAR_AUTHORITY_RULED_SINGLE_FROZEN_VERSION_REQUIRED`** ·
**`OMEGA_CALENDAR_AUTHORITY_RULED_PENDING_APPROVED_CALENDAR_INSTANTIATION`**

Ruling ω-11 named the substrate and left four residuals. They are ruled here **as one
question**, because they are one question: *which* calendar authority defines `ω`'s
eligible-slot sequence, *when* it must be frozen, and *what* may change afterwards.

###### The candidates, enumerated before anything is called "the approved calendar"

| # | Candidate | What it is | Status / timing |
| --- | --- | --- | --- |
| **A** | **The D-6 closure/market calendar artifact** — "a **versioned, committed** closure/market calendar artifact for the target epoch" | Carries `authority`, `authority_version`, `timezone`, **`market_open_close_rule`**, **`dst_rule`**, **`exceptional_closure_handling`**, `target_epoch`, `content_digest`, `approval`, a committed **provenance** block, and — decisively — **`expected_m15_slots`**, a *materialised* slot set. The generating-rule spelling `expected_m15_slot_rule` is **refused by name** (FR-8) **by the reader-free interface** — a callable carries no committed provenance — so the only route reaching `ω` today is the materialised set. *D-5.8 requirement 1 itself admits a generating rule **where it arrives with the approved artifact's committed provenance**; what is refused is materialising it inside the run, and an earlier drafting inverted that direction.* *(Two of the fields listed here are interface encodings rather than D-6 §9 bullets: `approval` encodes D-6.2, and the `provenance` block is D-5.8 requirement 1.)* | **Approved before the continuation** — `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`. **Does not yet exist.** |
| **B** | **Ruling 4's holiday / abnormal-thin-liquidity event-eligibility exclusion calendar** | Governs whether a trade may be **scored** in a window: "Rollover windows and low-liquidity holiday sessions are **event-ineligible** (cost there is unmodelled, so no trade may be scored there)". The rollover window itself is frozen at **21:55–22:15 UTC minimum**, "**widen only for conservatism; it must not be narrowed**" | `[FIXED-AT design audit]`, then **T-6 re-pointed to "implementation, approved before gate 7"** — i.e. **after** the window freeze. **Does not yet exist.** |
| — | `scripts/m15_gate3a/calendar_authority.py` | An **interface**, not an artifact: it "validates an injected calendar. **It never authors one**" | Committed; **not a candidate** — it supplies no slot |
| — | Prereg §4's M15 bucket convention (`floor(ts / 15 min)`, UTC, no DST) | The **grid**, not the slot set. §8.2.2: it "fixes the **bucketing** basis … does not, on its face, denominate a *duration*" | Committed; **not a candidate** for membership |
| — | Prereg §5's session partition (Asia / Europe / US UTC hour ranges) | A partition of the **whole UTC day** — `cost_schema.py`'s `_check_session_partition()` refuses unless the three windows tile 00:00–23:59 exactly once — used for **cost attribution**. It labels every minute and declares no slot and no market state. *An earlier drafting called it "a partition **within** open hours", which imputes open-hours knowledge to a source that has none.* | Committed; **not a membership authority** |

###### The distinction that resolves the whole question

**A governs slot *membership*; B governs event *eligibility*.** They are different
objects, and once that is seen the four residuals fall out together:

- A's own field list carries `market_open_close_rule`, `dst_rule` and
  `exceptional_closure_handling`, and its `expected_m15_slots` **is** the slot set.
  A therefore already owns weekend, holiday and exceptional closure — as *membership*.
- B removes **events from slots**, not slots from the sequence. **Whether a rollover
  slot is a member of `expected_m15_slots` is A's to declare, and this packet does not
  declare it** — no committed source states the market's state at 21:55–22:15 UTC, and
  §8.2.2 records that no market-hours instant exists anywhere in the M15 contract. What
  is ruled is the **ownership**: if A declares the slot, it is in `ω`'s sequence and
  prereg §5 removes the **event**, not the slot; if A's `market_open_close_rule` or
  `exceptional_closure_handling` declares it closed, it was never a member and B never
  reached it. *(An earlier drafting asserted flatly that "a rollover slot is a slot the
  market is open in", which authors a market-hours fact this packet may not author;
  **withdrawn**. Prereg §5's "cost there is unmodelled" presupposes quotes in the
  window, which is a reason to expect A to declare it open — reasoning, never a
  determination.)*
- **And prereg §4 supplies the strongest committed backing for the split, which an
  earlier drafting did not cite**: "no synthetic bars across market close; buckets
  spanning the weekend boundary are terminated at close; **the session/rollover
  exclusion windows for *event eligibility* are defined in §5/§6, not by deleting
  data**." That is the contract's own voice putting the rollover exclusion in the
  eligibility layer and not the membership layer — which moves part of (a)/(b) from
  ruling toward derivation.

**(a) Authority selection — binding to an external authority object, on committed
grounds.** *(Not called "the Option-B structure": within §8.4 "Option B" names the
mean-gap approximation that Ruling ω-3 **refuses by name**, and reusing the label on
the most load-bearing limb here invites the reading that the refused estimator is being
reinstated.)*
**`OMEGA_SLOT_MEMBERSHIP_AUTHORITY_IS_THE_D6_CLOSURE_MARKET_CALENDAR_EXPECTED_M15_SLOTS`.**
`ω`'s eligible-slot sequence is **Authority A's `expected_m15_slots`, and nothing
else**. B refines only event eligibility and **never** slot membership. "Whichever
approved calendar is latest" is **not** a valid rule and is refused by name.

**(b) Rollover and holiday ownership.**
**`MEAN_OVERLAP_DOES_NOT_OWN_ROLLOVER_OR_HOLIDAY_RULES`.** `ω` follows the selected
artifact's **exact slot membership** and derives no rollover, weekend, holiday,
session-break, early-close or exceptional-closure rule of its own. Market-hours
semantics stay inside the calendar authority — where `calendar_authority.py` puts
them and where this packet authors none. *Consequence, stated **conditionally**
because the membership outcome is A's content and A does not exist: **if** A declares
the slot, it is in `ω`'s sequence and prereg §5 removes the **event**, not the slot;
**if** A's `market_open_close_rule` or `exceptional_closure_handling` declares it
closed, it was never a member. An earlier drafting asserted flatly that "a rollover
slot is **in** `ω`'s sequence, because it is a slot" — and, at the head of this
subsection, that "a rollover slot is a slot the market is open in". Both **author a
market-hours fact this packet may not author**, and both are **withdrawn**; Ruling
Q10(ii) makes the point for the same artifact — it "authors no weekend rule, no holiday
rule, no closure rule and no DST rule".*

**The direction is recorded rather than left to be found.** For a fixed wall-clock
separation, keeping such slots **in** lengthens `g`, which lowers `max(0, 1 − g/H)`,
lowers `ω` and `rho_h`, and therefore **raises `N_eff`** — the mirror of this ruling's
own "omitting *ineligible* slots shortens `g`". The rollover window is **daily**, so the
effect is not isolated, and the arm the withdrawn drafting had chosen was the
**feasibility-favourable** one. `NON_NORMATIVE_DIAGNOSTIC_ONLY`. Two live tokens bind
exactly this — `OMEGA_CLOCK_SUBSTRATE_MUST_NOT_BE_CHOSEN_TO_MINIMISE_RHO_H` and
`OMEGA_CLOCK_MUST_NOT_BE_SELECTED_TO_MINIMISE_RHO_H_OR_INCREASE_N_EFF` — and they bind
the calendar author as much as this packet.

**So the residual survives.**
**`ROLLOVER_AND_HOLIDAY_SLOT_ELIGIBILITY_RELATIVE_TO_THE_OMEGA_CLOCK_NOT_SETTLED`** is
**not** discharged by this ruling: its **ownership** is ruled — A decides, `ω` does not —
and its **outcome** is A's content, unknowable before A exists. ω-11's `0`-to-near-`1`
daily lever therefore **relocates into A's content**, bound only by (e).

**(c) One authority, one version — SUPERSEDED IN PART BY RULING ω-13(a) as to
ordering.**
**`OMEGA_SLOT_MEMBERSHIP_AUTHORITY_MUST_BE_SINGLE_VERSIONED_AND_FROZEN_BEFORE_WINDOW_DECLARATION`.**
Exactly **one** artifact, at exactly **one** version, with exactly **one**
slot-membership declaration — **scoped to a single `target_epoch`**, because committed
code refuses reuse across epochs ("a calendar is never reused across epochs") and
`target_epoch` sits inside the `content_digest`, so the design span and the forward
epoch necessarily carry **different** artifacts at different digests. "Exactly one"
means one **per epoch**, binding `ω` and coverage *within* that epoch; it is not a
claim that Family A has a single artifact. *The single-versioned and frozen elements
stand; the **ordering** element — "before the window declaration" — is **historical**,
reversed by Ruling ω-13(a), which materialises the forward-epoch artifact **for** the
declaration.* *(The declaration is also **per pair**: the
validated calendar carries one `expected_m15_slots` set for each of `PAIRS_20`.)* Fixed
**before** the exact `T_v`/`T_h`/`D` declaration, and not swappable after any
result or metadata is observed. **No schema is invented here**: the identity fields
already exist in the committed interface — `authority_version`, `content_digest`
("a digest/version field is one token, never prose"), `target_epoch` with a
fail-closed epoch-mismatch check, and the approval marker. The requirement is
therefore **conceptual and already expressible**; where the producing/verifying
implementation is deferred, the status is
**`CALENDAR_FREEZE_CHECKABILITY_IMPLEMENTATION_PENDING`**, which is **not** a blocker
to this ruling.

**(d) Ordering — SUPERSEDED BY RULING ω-13(a).**
**`CALENDAR_FREEZE_PRECEDES_WINDOW_FREEZE_PRECEDES_DATA_OBSERVATION`** is **historical**:
it put the calendar freeze *before* the window declaration, which a review found both
conflicting with §8.2.0 and circular. Ruling ω-13(a) reverses it —
**declaration → materialisation → calendar freeze → no reselection → data** — adopting
§8.2.0's committed placement. The paragraph below is retained as the material the
correction was taken on. The order is:
**1.** calendar authority selected → **2.** its content/version frozen → **3.** `ω`
slot-membership semantics fixed → **4.** the exact UTC window declared → **5.** the
continuation separately authorised → **6.** and only then may real-data-dependent
calculation occur.

**This list is an *insertion into*, not a replacement for, the recorded order — and
its mapping is HISTORICAL under Ruling ω-13(a).** *As written here:* steps 1–3 precede
§8.2.8's step 6; step 4 **is** §8.2.8's step 6. *Under ω-13(a) the mapping is instead:
§8.2.8's **step 6 is the declaration**, and the forward-epoch Calendar A's
materialisation, freeze and approval fall **after step 6 and before step 8**.* Either
way, and §8.2.8's **step 7** —
the remaining Minimum Research Gate questions, Q1, Q8, FR-19 and the rest of §8 — and
**step 8**, execution authorisation, unconditional, are unchanged and still stand
between the declaration and any run. An earlier drafting of this six-step list omitted
step 7, which is readable as authorising the continuation straight off the
declaration. The three restatements of the recorded order (§8.2.8, §8.3.11, §13) are
**not amended here** — *and §8.2.8 is subsequently amended by Ruling ω-13(a), which
inserts step 6a; §8.3.11 and §13 are not*.

**And a committed source *does* state a conflicting placement, surfaced rather than
smoothed.** §8.2.0 — a recorded ruling section of this document — says of the calendar
artifact: "Its approval also has a place in the sequence that step list omits: it must
precede the continuation, and **the target epoch it declares is determined by the
declared window — so it sits between (3) and (4)**." On Q10-B's own four-step sequence
that is **after** the declaration is frozen, i.e. the reverse of this limb. An earlier
drafting asserted that no committed source states a conflicting order; **withdrawn**.

**The conflict carries a circularity that must be resolved before (d) is
satisfiable.** `target_epoch` is *digested* content — `calendar_content_digest()`
covers it, and `validate_calendar` fails closed with "a calendar is never reused across
epochs" — so if the target epoch is determined by the declared window, the artifact's
digest **cannot** be frozen before the window is declared. Either the calendar's
`target_epoch` is the committed forward epoch and independent of `T_v`/`T_h`, in which
case §8.2.0's placement was about *approval* and not about *content freeze* and the two
are compatible; or they cannot both hold. **This packet does not choose**, because the
choice is a ruling and neither artifact exists.
**`OMEGA_CALENDAR_FREEZE_ORDER_CONFLICTS_WITH_SECTION_8_2_0_TARGET_EPOCH_DEPENDENCY`**
— classified `MINIMUM_RESEARCH_GATE_BLOCKER` and **discharged by Ruling ω-13(a)**, in
§8.2.0's favour.

**(e) Outcome-blindness and post-observation mutation.**
**`OMEGA_CALENDAR_CONTENT_MUST_BE_OUTCOME_BLIND`** ·
**`POST_OBSERVATION_CALENDAR_MUTATION_IS_FORBIDDEN_FOR_CURRENT_FAMILY_A`.** Calendar
content — **A's slot membership and B's event-eligibility content alike** — may not be
**authored, selected, revised or re-versioned** in response to realised `N_eff`,
realised `ω`, realised overlap, correlation, sample count, model performance, Sharpe,
returns, pair failures, convenience in reaching a threshold, **or the known analytic
sign of the effect**. *Three widenings over an earlier drafting, each of which left a
hole: it said "modified", but neither artifact exists, so **every** instance of this
lever is a first **authoring**; it said "realised", but the sign is computable **with no
data at all**, so "nothing has been observed" is not blindness; and it was scoped to
`ω`'s calendar, i.e. **A**, while **B** is the artifact that can still move.* This is the clause the previous round recorded
as **missing** — `NO_OUTCOME_BLINDNESS_REQUIREMENT_BINDS_CALENDAR_CONTENT` and
`OMEGA_DEPENDENCE_NOT_DISCLOSED_AT_CALENDAR_APPROVAL` — and it is supplied here: the
prohibition now **follows the lever to where the lever went**. The `ω` dependence is to
be disclosed at the calendar approval, so that an approver approving a *coverage*
calendar is told the same artifact sets `rho_h` and `N_eff`.

**(f) The T-6 re-pointing, addressed rather than papered over.**
**`T6_LATER_CALENDAR_MAY_NOT_RETROACTIVELY_CHANGE_OMEGA_SLOT_MEMBERSHIP_FOR_AN_ALREADY_FROZEN_FAMILY_A_WINDOW`.**
T-6's exact wording is "concurrency/exposure caps + **holiday calendar** deferred to
implementation, **approved before gate 7**". Under limb (a) that later artifact is **B**,
which governs event eligibility and **not** slot membership, so on the ruled structure
it **cannot** retroactively move `ω`'s sequence — the alibi the previous round
identified is closed **structurally**, not merely by prohibition. The rule above is
retained anyway, to close the residual **pointer-update** route: a later artifact must
not be re-designated as `ω`'s membership authority for a window already frozen.

###### Amendment after freeze — the four cases kept apart

| Case | Disposition |
| --- | --- |
| **A. Defect correction found *before* the window declaration is pushed** | Permitted: re-freeze at a **new stated version**, with the superseded version and its identity retained. *The ground is **not** "nothing is observed yet, so nothing is selected on its effect" — that was an earlier drafting and it is **withdrawn**, because the sign of a membership change is knowable with no data at all. The ground is that no window is fixed and the superseded version stays traceable.* **After the declaration is pushed but before decision-bearing observation, case A does not apply**: §8.1.0 fixes the declaration at the first push and `SAME_D_DIFFERENT_WINDOW_IS_RESELECTION` binds from it, so a re-freeze there is made against a **known window** and re-opens the lever (d) closes. That routes to **B**, and whether the declaration must then be re-taken is **`POST_DECLARATION_PRE_OBSERVATION_CALENDAR_DEFECT_ROUTE_NOT_SETTLED`**. Repeated pre-declaration re-freezing toward a membership set that raises `N_eff` is a violation of **(e)**, not an exercise of case A. **Under Ruling ω-13(a) this case is structurally unreachable for the forward-epoch Calendar A**, because that artifact is materialised *from* the pushed declaration, so no version of it exists before the push. Every forward-epoch defect correction therefore routes to **B**, and `POST_DECLARATION_PRE_OBSERVATION_CALENDAR_DEFECT_ROUTE_NOT_SETTLED` is promoted from a corner case to **the only route** — a missing **route**, not a missing prohibition: the substantive lever stays barred by **(e)**, including on "the known analytic sign of the effect", and by `CALENDAR_MATERIALISATION_MAY_NOT_REOPEN_WINDOW_SELECTION` on the window side. *The clause "re-opens the lever (d) closes" above is historical; (d) is superseded.* |
| **B. Defect correction found *after* data observation** | **The current Family A window may not silently continue.** A corrected membership set changes `ω` for results already observed, which is `POST_OBSERVATION_CALENDAR_MUTATION_IS_FORBIDDEN_FOR_CURRENT_FAMILY_A`. It requires a **new explicit pre-registration or contract decision**, and the old version and old result stay **traceable**. |
| **C. Semantic change to eligibility** (membership actually differs) | Same as B, whenever the window is frozen: **no silent replacement**. Before the freeze it is case A. |
| **D. Administrative rename or pointer change**, membership byte-identical | Permitted **only where nothing digest-covered moves**, and **must not be used to smuggle C**. *An earlier drafting gave the ground as "identity is the `content_digest`, not the name" — which is **inverted**: `calendar_content_digest()` covers `committed_artifact` and `committed_revision` as well as the slot sets, and `committed_artifact` **is** a name ("looks like a path … a name a human reviewer resolves"). The name is **inside** the identity.* So a rename with byte-identical membership still yields a **different `content_digest`**, and is therefore a **new stated version** under case A or B by timing — never a silent pointer swap. |

*This defines no evidence lifecycle and no artifact schema beyond the fields already
committed.*

###### Interactions, stated because two of them are ordering constraints

- **Q10-B.** The exact `T_v`/`T_h`/window is declared by human + ChatGPT **before**
  continuation authorisation. *Historical:* limb (d) put the **calendar freeze before that
  declaration** — reversed by Ruling ω-13(a). *And Q10-B does not itself presuppose
  either order, though an earlier drafting said it presupposed (d)'s.* Under Ruling Q10-A `D` is an elapsed UTC span and expressly "**not** an
  eligible-day count", and Q10-B declares **literal UTC instants**, so the declared
  object is not denominated on the slot universe; Q10-B's own embargo paragraph in fact
  *contemplates* the approval landing later and defends by declaring the holdout start
  literally rather than by ordering. The dependency (d) actually relies on is **§8.1.0's**
  sizing basis, which admits "rollover and holiday exclusions" as availability metadata
  for `D`. And the lever has a **mirror image** — a window chosen knowing the slot
  universe — which Q10-B's forbidden-anchor list, not this limb, restrains. `CALENDAR_FREEZE_ORDER_IS_ADDED_HERE_NOT_IMPLIED_BY_Q10_B`.
- **Q10(ii).** Coverage's expected-slot membership already comes from the approved
  calendar authority. **The same frozen version governs both** `ω`'s eligible-slot
  sequence and coverage's expected-slot membership — one Family A evaluation may not
  contain two incompatible slot universes. Nothing committed distinguishes them, and
  both point at A's `expected_m15_slots`.
  `ONE_FROZEN_CALENDAR_VERSION_GOVERNS_BOTH_OMEGA_AND_COVERAGE`.
- **D-5.8.** Unchanged and consistent: **no numeric floor**, trusted calendar
  provenance plus **set equality**, and the runtime may not invent expected slots.
  This ruling adds nothing to that — it makes `ω` a **consumer** of the same
  materialised `expected_m15_slots`, and `ω` invents no slot independently. The
  generating-rule route stays refused.

###### No fallback

If the required frozen calendar authority is unavailable or unapproved: `ω` is **not
authoritatively measurable**; coverage's expected-slot membership is likewise not
authoritatively measurable insofar as it depends on the same authority; and there is
**no fallback to the continuous UTC grid and no inference of market hours**.
Continuation is then **barred, not discretionarily blockable**:
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` already conditions the
continuation on the approved artifact — the playbook lists it as "**Not discharged by
an accepted source audit**", followed by "**Only then** may a separately-authorised
gate-3a continuation read/derive design-span data" — and this ruling adds that `ω` is
not authoritatively measurable without it. *An earlier drafting wrote "may block
formal continuation", which softens a committed bar into a judgement call with no named
judge; the stricter reading governs.* It authorises creating **no calendar** here.

*One bypass, named where the limb is stated: `effective_n()` takes `overlap_fraction`
as a bare per-pair scalar with no provenance, so a caller may supply an `ω` computed on
the continuous grid and the machinery cannot tell. The no-fallback limb is defeated by
the estimator's own signature, not merely unenforced in general
(`OVERLAP_PER_RECORD_PROVENANCE_UNBOUND`).*

###### What this ruling does not settle

- **B can still change the *event set* after its later approval, and — correcting a
  claim this ruling first made — that residual is NOT conservative.** Widening
  event-ineligibility removes events, which moves both `N_raw` and the gap sequence.
  **And Ruling 4's widen-only clause does not bind B at all** — a second error in the
  same bullet. Prereg §5's "may **widen it** only for conservatism; it must not be
  narrowed" attaches to *"the **rollover exclusion window** is 21:55–22:15 UTC
  minimum"*; the next sentence, which defers "the holiday / abnormal-thin-liquidity
  exclusion calendar" to `[FIXED-AT design audit]`, carries **no direction clause**. B
  is therefore bounded in **neither** direction and may narrow as freely as widen.
  **`NO_DIRECTION_BOUND_BINDS_THE_LATER_EVENT_ELIGIBILITY_CALENDAR`** — classified
  `MINIMUM_RESEARCH_GATE_BLOCKER` and **ruled by ω-13(b)**: the direction bound was
  never the remedy; the remedy is that eligibility semantics affecting the Family A
  event sequence must be **pre-data frozen** and may not be changed retroactively. *(The rollover
  clause also names gate 3a / the design audit as the widening authority — both
  pre-freeze — so it gives no post-freeze bound to anything.)* Even where the clause
  did apply, it would be conservative only for the **event count**: fewer events makes
  the raw ≥ 1,000 floor harder. It is **not** conservative for `N_eff`, because
  removing an event **merges two gaps into one**, and a longer gap
  gives a *smaller* overlap, a *smaller* `ω`, a *smaller* `rho_h` and therefore a
  *larger* `N_eff_pair`. The two effects oppose and neither dominates in general.
  Lead-verified, `NON_NORMATIVE_DIAGNOSTIC_ONLY`: a pair with events at slots
  `0, 10, 20` has `ω = 0.583`, `rho_h = 14.42`, `N_eff_pair = 0.208`; drop the middle
  event and it becomes `ω = 0.167`, `rho_h = 4.83`, `N_eff_pair = 0.414` — a **rise**.
  On a denser sequence the same operation lowers it (`0.274 → 0.240`). The direction is
  therefore **indeterminate and sometimes anti-conservative**, and an earlier drafting
  of this bullet calling the residual "bounded conservative by Ruling 4's widen-only
  clause" is **withdrawn**.
  **`LATER_EVENT_ELIGIBILITY_CALENDAR_MAY_STILL_MOVE_THE_EVENT_SET`** ·
  **`WIDEN_ONLY_IS_CONSERVATIVE_FOR_THE_EVENT_COUNT_NOT_FOR_N_EFF`.**
- **The approval marker is artifact-declared, not evidence.** The committed interface
  says so in terms: `APPROVAL_DECLARED_BY_ARTIFACT__NOT_EVIDENCE_THAT_APPROVAL_OCCURRED`.
  A frozen, approved-looking artifact is checkable only as far as its own declaration.
- **`CALENDAR_FREEZE_CHECKABILITY_IMPLEMENTATION_PENDING`** — no source or test is
  changed here, so nothing enforces limbs (c)–(f) in code.
- **A materialised slot set is not proof that the set is calendar-derived.** FR-8's
  second limb is open and the committed interface says so: refusing a callable "**does
  not close FR-8's second limb**", because "a caller who evaluates the same closure a
  line earlier and passes the materialised set reaches a satisfied coverage result —
  **and an audit did exactly that**". Since (a) makes that set `ω`'s clock, `ω` inherits
  the residual: ω-11's "immune to data presence" holds of the artifact's *declaration*,
  not of anything a reader-free package can verify. A membership set that tracks the
  derivation makes `ω` a function of the very data it deflates.
  **`FR_8_SECOND_LIMB_OPEN_MATERIALISED_SET_MAY_STILL_BE_DERIVATION_TRACKING`** —
  classified **`DEFERRED_PRODUCTION_CHECKABILITY`** by Ruling ω-13: the rule against it
  exists, the *verification* does not, and a reader-free package cannot supply one.
  Subject, like residual 5, to
  `ONE_SELECTABLE_IMMUTABLE_CALENDAR_INSTANCE_WITH_RECORDED_IDENTITY_IS_AN_EXECUTION_PREREQUISITE`.
- **The freeze has no recorded anchor.** `content_digest` is recomputed from the content
  the artifact carries, so it is self-consistent for **any** artifact and cannot by
  itself distinguish the frozen version from a substitute; and the approval marker is
  artifact-declared. This ruling names **no locus** at which the frozen version's
  identity is recorded, so limbs (c), (d), (f) and case D state a requirement with
  nothing to check it against. `CALENDAR_FREEZE_CHECKABILITY_IMPLEMENTATION_PENDING`
  covers the absence of *code*, not the absence of a *record*.
  **`NO_LOCUS_RECORDS_THE_FROZEN_CALENDAR_VERSION_IDENTITY`** — classified
  **`DEFERRED_PRODUCTION_CHECKABILITY`** by Ruling ω-13, subject to
  `ONE_SELECTABLE_IMMUTABLE_CALENDAR_INSTANCE_WITH_RECORDED_IDENTITY_IS_AN_EXECUTION_PREREQUISITE`
  — **the deferral lapses where that prerequisite does not hold**, and the R-6
  reproducibility record is **not** part of it.
- **Membership is per pair, and nothing constrains how the sets may differ.**
  `expected_m15_slots` maps each of the twenty registered pairs to its own slot set, and
  `ω_p` is measured on pair `p`'s set — so a calendar author holds **twenty** independent
  levers on `rho_h`, not one. `PAIR_LABEL_ASSIGNMENT_MUST_NOT_BE_REARRANGED_TO_REDUCE_OMEGA`
  does not reach this: it binds the labels **events** carry, not the slot sets pairs are
  measured against. **`PER_PAIR_SLOT_MEMBERSHIP_VARIATION_UNBOUND`** — classified
  `MINIMUM_RESEARCH_GATE_BLOCKER` and **ruled by ω-13(c)**: per-pair variation is
  admissible only where **calendar-derived and deterministic**, never researcher-chosen.
- **This ruling inherits round 11's coverage gap.** It builds on Ruling ω-11, whose
  **calendar-semantics** review perspective §12.10 records as never run
  (`ROUND_11_REVIEW_COVERAGE_PARTIAL_TWO_OF_THREE_ROLES_TERMINATED`). That gap is
  inherited, not cured.
- Neither artifact **exists**. This ruling fixes *which* authority and *when*; it does
  not instantiate one, and `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`
  stands.

###### Amendment classification — per limb

| Limb | Classification |
| --- | --- |
| (a) A governs membership, B governs event eligibility | **Ambiguity resolution.** Both roles are already what the committed field lists and prereg §5 say; the ruling names which one `ω` consumes. Nothing committed is reversed. |
| (b) `ω` owns no rollover/holiday rule | **Ambiguity resolution as to ownership.** Confining `ω` to consuming membership narrows this packet, and prereg §4's "the session/rollover exclusion windows for *event eligibility* are defined in §5/§6, **not by deleting data**" is the contract's own voice for it. *An earlier drafting also decided the **membership outcome** here, in the feasibility-favourable direction; that is withdrawn, so no arm is chosen and none is classified.* |
| (c) single versioned frozen authority | **Tightening as to authority selection; NOT SETTLED as to the single-version obligation.** Refusing "whichever approved calendar is latest" removes latitude. But **no committed source binds two consumers to one `content_digest`** — this ruling's own Q10(ii) interaction says "nothing committed distinguishes them", and nothing committed *binds* them either, so `ONE_FROZEN_CALENDAR_VERSION_GOVERNS_BOTH_OMEGA_AND_COVERAGE` is an **addition**. That no schema is added is a separate and true point; it does not convert an added obligation into a tightening. |
| (d) ordering — **HISTORICAL, the limb is superseded by Ruling ω-13(a), which restores §8.2.0's placement** | **NOT SETTLED — an addition that also reversed a committed placement.** §8.2.0 puts the calendar approval "between (3) and (4)", i.e. after the declaration; this limb puts it before. Reversing a committed placement is not removing latitude, and by the criterion the last row applies it adds a requirement no committed source carries. *An earlier drafting classified (c) and (d) together as a plain tightening on the ground that the freeze was "unordered"; it was not.* |
| (e) outcome-blindness · (f) T-6 non-retroaction | **NOT SETTLED.** Each adds a requirement no committed source carries — a blindness obligation on calendar authorship and approval, a disclosure obligation, and a non-retroaction rule. Whether such additions need a contract-amendment procedure cannot be answered, because **no general contract-amendment procedure is registered anywhere in this repository** — `NO_GENERAL_CONTRACT_AMENDMENT_PROCEDURE_REGISTERED` being **this packet's own token for that absence, not a citation**. **`OMEGA_CALENDAR_AMENDMENT_CLASSIFICATION_NOT_SETTLED`.** |

**No favourable classification is asserted anywhere in this table.** The sentence
sits here rather than inside one row, because an earlier drafting scoped it to the last
row while three other rows — (b), (c) and (d) — carried classifications a review found
favourable. All three are corrected above.

##### Ruling ω-13 — the six residuals reclassified, and the three that move results, ruled

**`MEAN_OVERLAP_MINIMUM_RESEARCH_CONTRACT_RULED_PENDING_CALENDAR_INSTANTIATION`**

**The governing test, applied before anything is called a blocker.** *Can this
unresolved freedom materially change the research result, the event sequence, `ω`,
`N_eff`, or experiment selection **after decision-bearing information is
available**?* If yes, it is a research-blocking contract issue and is ruled here. If
it concerns only **evidence provenance, auditability, production verification,
implementation checkability or artifact-identity recording**, it is documented and
**deferred outside** the Minimum Research Gate, **recorded against a named later
gate**. This packet exists to make research **safe**, not to complete production-grade
evidence infrastructure.

**This test is §5's first limb and does not replace §5.** §5's **second limb** governs
unchanged — *absent this, could the exploratory work damage, contaminate, or later be
mistaken for committed evidence?* **Yes → IN, whatever the first answer** — and **§5 may
never be cited to strike a §3 boundary**. Nor does *after decision-bearing information
is available* narrow the first limb: §8.4.11's A-ω-5 records that **"a pre-data freeze
does not by itself protect MO-2, because the favourable direction is known in
advance"**, and ω-12's case A withdrew the same defence because "the sign of a
membership change is knowable with no data at all". A freedom whose favourable arm is
knowable with **no data** is therefore IN even though it is exercised before any
observation. Where the classification is unclear the item is a **blocker**, not a
deferral: the stricter reading of a research restriction governs.

*An earlier drafting of this paragraph said the previous rounds "had begun promoting
every discovered defect into a gate blocker regardless of whether it moved a result".
That is **withdrawn as false**: at the head this ruling was taken on, the word "blocker"
occurred **twice** in the whole document, and one of the two was ω-12 declining to call
an item one. No round did this, and the test needs no such premise.*

###### The six residuals, classified explicitly

**Six are *selected* for classification, not enumerated exhaustively.** The other items
ω-12 left open are unchanged and are **not** classified here — including
`POST_DECLARATION_PRE_OBSERVATION_CALENDAR_DEFECT_ROUTE_NOT_SETTLED`, which (a)
**enlarges**, and `ROLE_SPAN_HORIZON_TRUNCATION_RULE_NOT_REGISTERED`, which ω-13 does
not reach at all. ω-12's amendment cases A–D were derived on the superseded (d) order
and are **not** re-derived here.

| # | Residual | Classification |
| --- | --- | --- |
| 1 | `OMEGA_CALENDAR_FREEZE_ORDER_CONFLICTS_WITH_SECTION_8_2_0_TARGET_EPOCH_DEPENDENCY` | **`MINIMUM_RESEARCH_GATE_BLOCKER`** — a circular order leaves either the window reselectable after seeing calendar content, or the calendar authorable after the window is known. Both are post-declaration levers. **Ruled at (a).** |
| 2 | `NO_DIRECTION_BOUND_BINDS_THE_LATER_EVENT_ELIGIBILITY_CALENDAR` | **`MINIMUM_RESEARCH_GATE_BLOCKER`** — changing event eligibility after the freeze changes which events exist, hence the adjacent-event gaps, hence `ω`, `N_raw` and `N_eff`. **Ruled at (b).** |
| 3 | `PER_PAIR_SLOT_MEMBERSHIP_VARIATION_UNBOUND` | **`MINIMUM_RESEARCH_GATE_BLOCKER`** — a researcher-chosen per-pair slot universe is twenty independent levers on `rho_h`. **Ruled at (c).** |
| 4 | `FR_8_SECOND_LIMB_OPEN_MATERIALISED_SET_MAY_STILL_BE_DERIVATION_TRACKING` | **`DEFERRED_PRODUCTION_CHECKABILITY`** — see the qualification below. |
| 5 | `NO_LOCUS_RECORDS_THE_FROZEN_CALENDAR_VERSION_IDENTITY` | **`DEFERRED_PRODUCTION_CHECKABILITY`** — see the qualification below. |
| 6 | The concrete rollover / holiday **membership outcome** | **`RUNTIME_CALENDAR_INSTANTIATION_OUTCOME`** — see below. |

**(a) Freeze order — the circularity is removed, and §8.2.0 was right.**
**`WINDOW_IDENTITY_PREDECLARED_CALENDAR_MATERIALISED_WITHOUT_POST_CALENDAR_RESELECTION`.**
The order is:

> **1.** the experiment/window identity is declared **without reading decision-bearing
> data** → **2.** that frozen declaration is the **input** from which Calendar A is
> mechanically materialised → **3.** Calendar A is frozen **and approved** → **4.** the
> declared window may **not** be changed or reselected because of calendar content →
> **5.** only after *both* the declaration and the calendar are frozen may
> decision-bearing data observation occur — and **only** subject to §8.2.8's **step 7**
> (the remaining Minimum Research Gate questions) and **step 8**, which is
> unconditional. **This list is an insertion into the recorded order, never a
> replacement for it, and no step of it is an authorisation.**

**Scope: the forward epoch only.** This order governs the **forward-epoch** Calendar A
— the artifact whose `target_epoch` §8.2.0 says "is determined by the declared window".
It does **not** reach the **design-epoch** Calendar A, which ω-12(c)'s "one **per
epoch**" already separates and which the audit playbook's prerequisite 5 requires
*before* the design-span continuation may "read/derive design-span data". Nothing here
reorders that artifact, and an unqualified reading of this limb would have forbidden
what the playbook requires.

*This **supersedes Ruling ω-12(d)**, which put the calendar freeze **before** the
window declaration and which a review found both conflicting and circular.* §8.2.0
placed the calendar approval "between (3) and (4)" of Q10-B's sequence because "the
target epoch it declares is determined by the declared window" — and that is exactly
where step 2 above puts it. **The committed placement was right and ω-12(d) was
wrong**; the circularity dissolves because the declaration is an *input* to
materialisation rather than an output of it, and `target_epoch` — which sits inside
the `content_digest` — can then be fixed without depending on anything the calendar
itself produces. `OMEGA_CALENDAR_FREEZE_ORDER_CONFLICTS_WITH_SECTION_8_2_0_TARGET_EPOCH_DEPENDENCY`
is **discharged**.

**What the ordering does *not* permit.**
**`CALENDAR_MATERIALISATION_MAY_NOT_REOPEN_WINDOW_SELECTION`.** It is **not** licence
to inspect calendar density, the expected slot count, the overlap implications, `ω` or
`N_eff`, and then choose a more favourable `T_v`/`T_h`/`D`. The predeclared window
identity **binds** for current Family A unless a new explicit pre-registration or
contract decision is taken — a route whose **sufficiency is itself unruled**
(`NEW_PREREGISTRATION_SUFFICIENCY_FOR_A_DIFFERENT_D_NOT_RULED`), so it is named here as
the *only* route and not as an available one. `SAME_D_DIFFERENT_WINDOW_IS_RESELECTION`
and `POST_FREEZE_DURATION_RESELECTION_IS_FORBIDDEN_FOR_CURRENT_FAMILY_A` apply to this
step, and §8.2.0 binds the declaration **from the first push**, so there is **no
interval in which the window is mutable and calendar content is visible**. **No `T_v`, `T_h` or `D` value is chosen here.**

**Relation to Q10-B, restated so the two read as one sequence.** Q10-B still requires
the exact human + ChatGPT declaration **before continuation authorisation**. The
composed order is: **declaration → Calendar A materialised for that exact declaration →
Calendar A frozen and approved → §8.2.8's step 7, then its unconditional step 8 →
(later) continuation may be considered.** Q10-B is unchanged, and the earlier claim
that it *presupposed* a frozen calendar stays withdrawn.

**(b) Event eligibility must be frozen before data.**
**`OMEGA_EVENT_ELIGIBILITY_RULES_MUST_BE_PRE_DATA_FROZEN`** ·
**`LATER_EVENT_ELIGIBILITY_CALENDAR_MUST_NOT_RETROACTIVELY_CHANGE_CURRENT_FAMILY_A_EVENT_SEQUENCE`.**
Any calendar or rule that can affect whether a candidate event is **eligible for
inclusion in the `ω` / `N_eff` event sequence** must have its **operative semantics**
frozen before decision-bearing data observation. This is the limb that made residual 2
a blocker: slot membership being fixed is not enough, because eligibility decides which
events exist at all.

**And "semantics" here means *closed* semantics — without this the limb does not
bind.** A rule may not **delegate** its content to an artifact, table or calendar that
is not itself frozen before decision-bearing observation. Otherwise a rule of the form
*"ineligible if the slot falls in a low-liquidity holiday session **as listed in the
calendar approved before gate 7**"* would have complete operative semantics, frozen
pre-data, and would therefore satisfy this limb **and** fall inside the carve-out
below — while its content arrived after the freeze and moved the event set. Where a
rule delegates, **the delegated content is part of the pre-data freeze and the rule is
not frozen until that content is**.
**`FAMILY_A_ELIGIBILITY_SEMANTICS_MAY_NOT_DELEGATE_TO_A_POST_FREEZE_ARTIFACT`.**

**The freeze moment is named, because the non-retroaction limb needs something to
protect.** The **current Family A event sequence is frozen at the moment the last such
semantic *and its content* are frozen**, which is before any decision-bearing
observation. The non-retroaction limb protects the sequence from that moment, and the
carve-out below reaches only rules frozen **in that complete sense**.

**Calendar B is not thereby pulled forward wholesale.** Two classes are separated:
**(A) semantics affecting current Family A event inclusion** — must be frozen before
data; **(B) semantics used only for later operational or production purposes** — may
remain later. B may continue to evolve; it simply **cannot retroactively alter the
frozen Family A event sequence**.

**And no post-hoc filtering.**
**`POST_OBSERVATION_EVENT_ELIGIBILITY_RECLASSIFICATION_FOR_CURRENT_FAMILY_A_IS_FORBIDDEN`.**
Events may not be added or removed after observation on grounds of holiday
classification, rollover classification, thin liquidity, low or high spread, overlap,
`N_eff`, correlation or model performance — **unless that rule was already frozen
before data observation**.

**The committed architecture *does* place Calendar B's approval after the freeze** —
T-6 re-points it to "implementation, approved before gate 7" — so this is not a
conditional: the conflict is **not** dissolved by the split alone, and a narrow
**pre-data Family A eligibility contract** must be frozen separately, before any
decision-bearing observation, with the later Calendar B unable to override it
retroactively. *An earlier drafting wrote this as an "if", which leaves a reader
entitled to hold the antecedent unestablished and skip the separate freeze.*

**Its content is bound like the others.** ω-12(e)'s outcome-blindness names "A's slot
membership and B's event-eligibility content"; this contract is a **third** object, and
it is bound on the same terms — **`OMEGA_CALENDAR_CONTENT_MUST_BE_OUTCOME_BLIND` reaches
it too**, because a pre-data freeze is not by this packet's own standard sufficient
when the favourable sign is computable with no data. Its declaration is a **human +
ChatGPT** act, as Q10-B's is, and no decision-bearing observation may occur before it:
**`PRE_OBSERVATION_FAMILY_A_EVENT_ELIGIBILITY_CONTRACT_REQUIRED`**. Only the required
semantics are ruled here; **no such artifact is created**, and who authors it, where it
is recorded and how it is checked are `DEFERRED_PRODUCTION_CHECKABILITY` alongside
residual 5.

**And its absence is registered, not assumed away.** No such contract exists, nothing in
committed text requires one to be produced, and Calendar B's committed approval point is
after the freeze — so until one is frozen, the Family A event sequence is still fixed by
an artifact approved after the freeze, and (b) is satisfiable in principle and
unsatisfied in fact. **`NO_PRE_DATA_FAMILY_A_EVENT_ELIGIBILITY_CONTRACT_EXISTS`** ·
**`PRE_DATA_FAMILY_A_EVENT_ELIGIBILITY_CONTRACT_REQUIRED_BEFORE_CONTINUATION`**, carried
on the open list beside `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`.

**(c) Pair-specific slot variation must be calendar-derived, never researcher-chosen.**
**`PAIR_SPECIFIC_SLOT_VARIATION_MUST_BE_CALENDAR_DERIVED_NOT_RESEARCHER_SELECTED`.**
Per-pair slot membership is admissible **only** where it is deterministically produced
by frozen Calendar A, from the registered pair identity, under pre-data rules, and
**not selected or adjusted manually per pair**.

**This does not require the twenty sets to be identical.** Legitimate differences may
exist wherever Calendar A derives them deterministically from pair identity and
calendar rules — the prohibition is on **choice by any party, the calendar author no
less than the researcher, and they may be the same person**, not on deterministic
pair-specific calendars.

**Determinism is not itself the safeguard, and the ruling does not pretend otherwise.**
**Any fixed per-pair table is deterministic**, so twenty hand-written sets indexed by
pair identity would satisfy the words while constraining nothing. The operative bar is
therefore the anti-optimisation clause below, not the word "deterministic". And the
property is **not expressible in the route that reaches `ω` today**: FR-8 refuses the
generating-rule spelling, so A carries a *materialised* set, and a derived set and a
hand-tuned set are **byte-identical objects**. The one route that could express it is
D-5.8 requirement 1's — a generating rule arriving **with the approved artifact's
committed provenance**. Until that route is used, **(c) inherits FR-8's second limb**,
and its verification is deferred with residual 4 rather than supplied here. Forbidden accordingly:
**`PAIR_CALENDAR_VARIATION_MUST_NOT_BE_OPTIMISED_AGAINST_EFFECTIVE_N`** — choosing a
broader calendar for one pair and a narrower one for another, altering closure
treatment by pair after seeing counts, choosing a per-pair clock to minimise `ω`, or
tuning pair calendars to pass `N_eff`.

###### The two deferred items, with the qualification that makes the deferral honest

**4 — FR-8's second limb.** The concern is that a *materialised* slot set could still
have been produced by evaluating a derivation-closing rule one line earlier, which
would make `ω` a function of the data it deflates. **The rule against it already exists,
and it is committed rather than added here** — D-6 places the expected slot set with an
authority from which it is "**never inferred from the raw source**", and
`calendar_authority.py` "never reverse-infers 'there is no data, therefore the market
was closed'"; ω-11 relies on exactly that when it calls the substrate "immune to data
presence". ω-12(e)'s outcome-blindness sits on top of it, and (b) and (c) freeze the
eligibility semantics and the pair variation. *An earlier drafting grounded this on
ω-12(e) and (a) alone: (e)'s enumerated triggers do not reach a set derived from **data
presence** rather than from an outcome, and (a) orders the **researcher's** observation,
not the calendar author's access.*
What is missing is the **verification**, which a reader-free package cannot supply and
which the interface itself says is deferred to the byte-reading gate. **That deferral is
not new here**: PR #449 recorded it as **`SECOND_LIMB_DEFERRED_TO_GATE4_BYTE_READER`**,
on the authority of §12.14 plus the open gate
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` — *not* §4.7.3, a misattribution
that PR #449 §2.3 corrected and which is not reintroduced. So residual 4's
classification agrees with a committed deferral rather than creating one, and it is
subject to the same qualification as residual 5 below. So this is
**provenance checkability, not a remaining statistical freedom** —
**provided** one frozen calendar set is used, its semantics are pre-data fixed, and the
researcher cannot mutate or substitute it after observation, all of which (a)–(c) now
require. **FR-8 is not closed globally**, it stays visible, and it is **not the reason** any
read-only exploratory research is unavailable — **nothing here makes such research
available**: §11's non-authorisation, and Q1, Q3 and Q8, continue to govern whether it
may begin at all.

**5 — no locus records the frozen version identity.** The conceptual contract already
requires **one frozen version**; the absence of a storage or schema locus to record
*which* version was used is an implementation and checkability matter.
**`CALENDAR_VERSION_IDENTITY_RECORDING_IMPLEMENTATION_PENDING`.** No schema field and no
artifact machinery is invented here.

**What is *not* deferred.** §5's own OUT table already puts provenance **IN as R-6's
lightweight record** — "the conclusion needs to be reproducible, not forensically
attributable" — so any output that consumes a calendar **SHALL** record that calendar's
`authority_version`, `content_digest` and `target_epoch` in its R-6 reproducibility
record. That is a record, not a schema; it invents no field; and it is the research-side
half of this residual, which the classification would otherwise have deferred along with
the rest. What **is** deferred is the **production locus** — a committed storage or
schema anchor a later audit can verify against.

**The qualification, stated because the deferral depends on it.** Both deferrals hold
**only if the research execution path can operate against one explicitly selected,
immutable calendar instance *and that instance's identity is recorded with any result it
produces*** — selectability alone does not distinguish a second run against a
**substituted** instance from the first, which is exactly the post-observation route
`POST_OBSERVATION_CALENDAR_MUTATION_IS_FORBIDDEN_FOR_CURRENT_FAMILY_A` bars normatively
and nothing detects. If the implementation cannot do both, that is a **future
implementation prerequisite before execution**, not documentation polish —
**`ONE_SELECTABLE_IMMUTABLE_CALENDAR_INSTANCE_WITH_RECORDED_IDENTITY_IS_AN_EXECUTION_PREREQUISITE`**.

**The negative branch is stated, because otherwise the "only if" carries no
consequence.** Where the prerequisite holds, the residual verification is deferred and
becomes an execution prerequisite. Where it does **not** hold — where the implementation
cannot select one immutable instance, or cannot record which one it used — the deferral
**lapses** and residual 5 is a **`MINIMUM_RESEARCH_GATE_BLOCKER`**, because the freeze
then has nothing to check it against and the bar on post-observation substitution
becomes unfalsifiable. *Recorded as a deliberate split: blocker 2's **remedy** is a gate
matter, and the **record** of that remedy is production checkability.* What must not
happen is the reverse: turning a schema or recording gap into a **statistical contract
question**.

###### 6 — the rollover / holiday membership outcome

**`RUNTIME_CALENDAR_INSTANTIATION_OUTCOME`.** The contract-level rules are already
fixed: Calendar A owns slot membership; Family A invents no rollover or holiday rule;
and, from (b), any eligibility rule affecting the event sequence must be pre-data
frozen. The concrete slot set is therefore an **output of approved calendar
instantiation**, not a contract choice, and this packet decides none of it.

*Why this is a classification and not a dodge.* The **freedom** the residual carried —
that the membership outcome could be settled later, after observation, in a favourable
direction, on a daily window — is closed **as to timing** by (a) and (b), which put the
calendar freeze and the eligibility freeze before any decision-bearing observation, and
**as to motive** by ω-12(e)'s outcome-blindness. What remains unknown is the **value**,
and an unknown value that nobody may choose on its effect is an instantiation outcome,
not a lever.

**Three things recorded rather than softened.** First, **(a) does not narrow the
outcome**: ω-12(d) and ω-13(a) both freeze the calendar before data, and what (a)
changes is that Calendar A is now materialised **for an already-declared window** — so
its author knows `T_v`, `T_h` and `D`, and therefore the **magnitude** of the rollover
lever as well as its sign, where ω-12's rejected arm would have kept the author
window-blind. That is a real cost of adopting §8.2.0's placement, and it is stated
rather than presented as a gain. Second, the closure is **by prohibition, not
structural**, and the prohibition it rests on — ω-12(e) — is itself classified **NOT
SETTLED** and enforced by no code
(`CALENDAR_FREEZE_CHECKABILITY_IMPLEMENTATION_PENDING`). Third, and consequently, this
classification **depends on residual 5's deferral holding**: (e) has no locus to be
checked against, so if that deferral lapses under the qualification above, residual 6
reverts to a lever. **`RESIDUAL_6_OUTCOME_CLASSIFICATION_DEPENDS_ON_RESIDUAL_5_DEFERRAL_HOLDING`.**

**And no market-hours semantics is authored here.** No Friday close, no Sunday open, no
DST time, no broker rollover window, no holiday table and no exceptional closure date.
Those are calendar **inputs**, not contract choices for this PR.

###### The boundary, stated to stop the audit expanding without end

**`NEW_OMEGA_FINDINGS_DO_NOT_AUTOMATICALLY_BECOME_RESEARCH_BLOCKERS`.** A future finding
about `ω` or the calendar reopens the Minimum Research Gate **only** if it demonstrates
a remaining freedom capable of **materially changing the research result after
decision-bearing information is available**. Otherwise it is classified as
implementation, evidence, checkability or production-hardening, recorded **against a
named later gate**, and the gate stays closed. *This is a rule about classification, not
about severity: a serious implementation defect is still serious, and still not a gate
blocker.*

**Four things bind it, so it cannot be used to dismiss findings.** *Who decides* —
classifying a contested finding is a **human + ChatGPT** act on the same footing as this
ruling; an AI session may **propose** a classification and may never adopt one, and **the
implementing session may not classify its own finding out of the gate**.
**`OMEGA_FINDING_CLASSIFICATION_IS_A_HUMAN_CHATGPT_CALL`.** *What "material" means* —
any capacity to change `ω`, `N_eff`, the event sequence or experiment selection **at
all**; §0's verdict is
`SAMPLE_FLOOR_REACHABILITY_NOT_DETERMINABLE_WITHOUT_MEASURED_INPUTS`, so no margin exists
from which a threshold could be derived. *What "available" means* — decision-bearing
**observation** in the committed sense, by any party in the research path, **the
calendar author included**. *And what happens when it is unclear* — the item is treated
as a **`MINIMUM_RESEARCH_GATE_BLOCKER`** until ruled otherwise.
**`UNCLEAR_OMEGA_FINDING_CLASSIFICATION_DEFAULTS_TO_BLOCKER`.**

**This rule does not licence a pre-data freedom whose favourable direction is knowable
with no data.** ω-12(e) already refuses "nothing has been observed" as a defence, and
§5's second limb governs alongside this test — otherwise the boundary would
auto-classify out of the gate exactly the class (e) had to be widened to catch.

###### Status

**`MEAN_OVERLAP_MINIMUM_RESEARCH_CONTRACT_RULED_PENDING_CALENDAR_INSTANTIATION`** — the
mathematical method, the clock, the pair handling, the window/calendar ordering, the
event-eligibility freeze and the pair-calendar freedom are all ruled; **no empirical
value is calculated**; and the actual calendar must still be instantiated and approved.
**This is not a claim of production readiness**, and
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` stands.

**Amendment classification.** (a) **withdraws a limb of a previously recorded human +
ChatGPT ruling.** ω-12(d) is recorded at §8.4.0 as *received authority*, not as this
packet's own proposal, so (a) is not a self-correction of drafting: **superseding a
recorded ruling is itself a ruling only human + ChatGPT may take**, and it is taken here
as one. Its *content* is nonetheless the least-amending option available — ω-12(d) was
classified **NOT SETTLED — an addition that also reversed a committed placement** — so
withdrawing it and restoring §8.2.0's committed placement moves no committed
requirement. *But (a) carries a further effect beyond the reversal, a **tightening**,
stated rather than left silent:* `CALENDAR_MATERIALISATION_MAY_NOT_REOPEN_WINDOW_SELECTION`
adds a forbidden anchor — calendar density and expected slot count — that **Q10-B's
forbidden-anchor list does not carry**. Under CLAUDE.md's stricter-reading rule the
tighter reading governs; it is not an amendment, and it is not an inconsistency-removal
either.

**And the mirror image is named, because (a) does not close it.** §8.1.6's limb (i)
admits "rollover and holiday exclusions" among the availability metadata `D` may be
sized on, so the declarer at step 1 may lawfully know the *shape* of the exclusions even
though the forward-epoch Calendar A does not yet exist to be read. What (a) forecloses
is reliance on **that artifact's content**; it bars **reselection** on calendar content,
not an **initial** declaration informed by the exclusion shape. What restrains that is
Q10-B's forbidden-anchor list — in particular "a date required to reach `N_eff`" —
together with `DURATION_SELECTION_MUST_BE_OUTCOME_BLIND`, not this limb. *An earlier
drafting said (a) forecloses limb (i) outright; that overstated it, since limb (i)'s
admissible inputs are availability metadata, not the artifact.*
**`INITIAL_WINDOW_DECLARATION_MAY_KNOW_THE_EXCLUSION_SHAPE_BOUND_ONLY_BY_Q10_B_AND_OUTCOME_BLINDNESS`.**
(b) and
(c) are **NOT SETTLED**: each adds a requirement no committed source carries — a
pre-data freeze obligation on eligibility semantics, a non-retroaction rule, and a
determinism obligation on per-pair variation — and whether such additions need an
amendment procedure cannot be answered, because **no general contract-amendment
procedure is registered anywhere in this repository**
(`NO_GENERAL_CONTRACT_AMENDMENT_PROCEDURE_REGISTERED`, this packet's own token for that
absence). **`OMEGA_RECLASSIFICATION_AMENDMENT_CLASSIFICATION_NOT_SETTLED`.** The
reclassification itself is a **judgement about scope**, not a contract change: it moves
no committed requirement, and every deferred item stays documented.

**No favourable classification is asserted anywhere in this ruling.** Three of the six
residuals are classified downward — two deferred and one an instantiation outcome — and
each is stated with the ground that would defeat it: the two deferrals **lapse** under
the qualification above, and residual 6's disposition depends on residual 5's. A reader
must be able to see which classifications would not survive a disagreement. *The
sentence sits here rather than inside the table because an earlier round scoped the
equivalent sentence to one row while other rows carried favourable classifications.*

##### Carried forward unchanged, and restated because they are still live

**No turnover-derived gap.** The `≤ 40 trades/day` ceiling is a **portfolio mean over
the span** (`turnover()`'s own docstring: "Portfolio-average trades per day") and is
**not** a hard constraint on any individual gap. Forbidden: `40/day → a fixed gap`;
`40/day → a minimum gap`; `mean turnover → each event gap`; and deriving a mean
inter-event spacing **solely** from the turnover ceiling. Turnover remains a separate
criterion.

**No invented clamps.** No `ω` cap, `ω` floor, gap clamp, arbitrary `0.5` cap,
arbitrary minimum overlap or synthetic conservative multiplier may be introduced
unless already committed. `max(0, 1 − g/H)` is the **overlap geometry**, not a licence
to add bounds beside it. The committed bounds remain exactly two: `ω ∈ [0, 1]` and
non-overlapping events ⇒ `rho_h → 1`.

##### What is derived and what is chosen — stated in one place

| Limb | Backing |
| --- | --- |
| Overlap is **same-pair**, against the **next** event (MO-1(a),(b)) | (a) **derived** from the spec sentence; (b) was open, **confirmed** by Ruling ω-2 |
| Event **ordering** (MO-8) | **Derived** — D-ω-1, on `raw_event_count`'s bucket denomination, prereg §6's "a bar is an eligible event", and prereg §8's frozen per-bar EV gate with its strict `>` |
| The **clock** (MO-2) | **FULLY RULED — HUMAN + CHATGPT CHOICE.** Ruling ω-1 fixes that `g` is read on `H`'s clock; **Ruling ω-11 names that clock** — the approved-calendar eligible M15 slot sequence. Only the *same-clock* requirement was ever derivable; the substrate is a choice, and it is bound to an external authority rather than selected |
| The **clock substrate** | **HUMAN + CHATGPT CHOICE** — Ruling ω-11. No committed source names `ω`'s substrate; D-5/D-6 place the expected slot set with the calendar authority for **coverage**, and extending that authority to `ω` is the ruling's act |
| The overlap **function** (MO-3) | **Derived — conditionally, and not independently of a chosen limb.** D-ω-2 holds where `H` is a constant contiguous 24 on the ruled clock. Ruling ω-1 removes the mixed-unit failure and **Ruling ω-11 discharges the rest**, since `H` is 24 *consecutive* eligible slots for every event — leaving only `HORIZON_TRUNCATION_AT_ROLE_SPAN_BOUNDARY_NOT_REGISTERED`. But both ω-1 and ω-11 are **choices**, so MO-3 **still would not survive a disagreement about them**; what changed is that its remaining condition is now met, not that it became independent |
| **MO-1(b)**, the next-event restriction | **An open limb resolved by confirming the spec's own words** — counted in neither the four derived nor the six chosen, and recorded here because it has a direction: next-event-only **understates** dependence under clustering (§8.4.1, §8.4.6), which is anti-conservative |
| **`E[f]` over `f(E)`** (MO-4) | **Derived** — D-ω-3 + D-ω-4; **confirmed** by Ruling ω-2 |
| The draft's **status** | **Derived** (superseded); the **prohibition on re-adoption** is Ruling ω-3's addition |
| **Weighting** (MO-1(c), MO-6-within) | **HUMAN + CHATGPT CHOICE** — Ruling ω-4 |
| The `n − 1` **denominator** | **Consequence** of Ruling ω-2's index set (adjacent **intervals**, not events) together with Ruling ω-4's equal weighting. Under equal weighting over an *event* index the denominator would be `n`; an earlier version of this row attributed it to ω-4 alone |
| MO-5's **last-event** limb | **Disposed of as a consequence, not separately ruled.** With the index over intervals, the last event contributes no term, so the `n`-denominator reading MO-5 offered — "letting the last event contribute a zero term" — is foreclosed. The direction is **conservative**: `ω_{n−1} = ω_n · n/(n−1) ≥ ω_n`. Recorded rather than left as an arithmetic by-product, per §8.4.12's own warning that one MO-5 limb must not be settled by settling another |
| **Role separation** (MO-6, per-role limb) | **HUMAN + CHATGPT CHOICE** — Ruling ω-9. The spec requires `per_role: [validation, holdout]` **reporting** and never says `ω` is role-separate |
| **Zero-event** (MO-5a) | **HUMAN + CHATGPT CHOICE** — Ruling ω-5; the inertness and the no-halt limb were derived |
| **One-event** (MO-5b) | **HUMAN + CHATGPT CHOICE** — Ruling ω-6; a stipulation filling an undefined `0/0` |
| **Cross-pair** aggregation (MO-6-across) | **Derived** — D-ω-5; **confirmed**, with the pooling prohibition added |
| **Pair identity** | Rule **derived**; the prohibition and its scope are Ruling ω-8's |
| **Source / freeze point** (MO-7) | **HUMAN + CHATGPT CHOICE** — Ruling ω-9 |
| **Measurement may not redesign** | **HUMAN + CHATGPT CHOICE** — Ruling ω-10 |

**Four derived and confirmed — one of them, MO-3, only *given* Ruling ω-1's choice —
and six explicit choices, plus MO-1(b) resolved by confirmation and two limbs disposed
of as consequences.** Stating it this way is the point of the table: a reader must be
able to see which limbs would survive a disagreement about the ruling and which would
not. MO-3 would not.

##### Amendment classification — per limb, and not resolved where it cannot be

| Limb | Classification |
| --- | --- |
| Rulings ω-2, ω-7, and the derived halves of ω-3 and ω-8 | **Confirmation of a derivation.** No committed sentence is contradicted; the APPROVED spec's own words are restated. Not an amendment. |
| Ruling ω-1 (the clock) | **Tightening as to the mixed readings; NOT SETTLED as to its prohibition.** Of §8.4.4's **six** candidate readings the mixed and non-bar ones are removed, while the **three bar readings of `H` survive**, so latitude is **narrowed, not removed** — an earlier version of this row said "five candidate readings" and "is removed", both corrected. `OMEGA_CLOCK_MUST_NOT_BE_SELECTED_TO_MINIMISE_RHO_H_OR_INCREASE_N_EFF` adds a requirement no committed source carries and falls in the last row's class. Nothing committed is reversed. |
| Ruling ω-4 (equal weighting) | **Ambiguity resolution as to direction** — "mean" unqualified reads as unweighted, which is also the `ω`-**maximising** end of the readings §8.4.5 spans — and **NOT SETTLED as to foreclosure**, since barring every other weighting, and exclusion with it, adds a requirement no committed source carries. |
| Ruling ω-5 (zero event) | **Tightening.** Consistent with a derivation from §8.3.0; retaining the pair keeps `P = 20` and the larger `rho_x`, and "no synthetic contribution" is restrictive. |
| Ruling ω-6 (one event) | **NOT SETTLED — an addition, and not a tightening.** An earlier version of this table classified ω-5 and ω-6 together as a tightening; that is **withdrawn for ω-6**. It stipulates a value where the arithmetic is undefined, so it adds content the spec does not carry, **and the value it stipulates is the feasibility-favourable end** — a one-event record then contributes `1.000`, the largest value that record can take. Calling a permissive stipulation a tightening would be exactly the favourable classification this table exists to refuse. |
| Rulings ω-3's prohibition, ω-8's prohibition, ω-9, ω-10 | **NOT SETTLED.** Each adds a requirement no committed source carries — a bar on re-adopting a superseded formula, an enforcement obligation on pair identity, a freeze point and role locality, and a bar on redirecting the experiment. Whether such additions require a contract-amendment procedure cannot be answered, because **no general contract-amendment procedure is registered anywhere in this repository** (`NO_GENERAL_CONTRACT_AMENDMENT_PROCEDURE_REGISTERED`, this packet's own token for that absence). **`MEAN_OVERLAP_AMENDMENT_CLASSIFICATION_NOT_SETTLED`.** |

**No favourable classification is asserted anywhere in this table** — the sentence sits
here rather than inside one row, because an earlier version scoped it to the last row
while three other rows carried classifications a review found favourable. The
substantive ruling stands as human + ChatGPT authority within this PR pending merge
and review.

##### What the ruling does not settle

- **`ROLE_SPAN_HORIZON_TRUNCATION_RULE_NOT_REGISTERED`.** D-ω-2 treats every horizon
  as the full frozen `H`; nothing in `scripts/m15_gate3a/` carries a rule for an event
  whose horizon runs past the end of its role span, and the only positional
  implementation is unadopted M1-lineage code (§8.4.14). **Ruling ω-9's role-locality
  is what makes this live**, since it puts the boundary inside the ruled calculation.
  The direction is conservative — a truncated horizon makes the ruled formula
  *over*-state overlap — but it is unregistered.
- **`HORIZON_WALL_CLOCK_EXTENT_NOT_REGISTERED` is discharged *as it bears on `ω`*
  by Ruling ω-11**, which names the substrate for both `g` and `H`. What replaces it
  is **not** a researcher choice but an **external dependency**:
  `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` now binds `ω` in terms, and
  no empirical `ω` can be authoritatively instantiated before that approval — with no
  fallback grid, no heuristic clock and no inferred market hours. The token survives
  **outside `ω`**, wherever the wall-clock extent of the frozen horizon matters to
  something other than the overlap arithmetic. **`CALENDAR_CONTENT_DETERMINES_OMEGA_SUBSTRATE`**
  is the new surface: whoever authors and approves the calendar determines the
  sequence `ω` is measured on. D-6 puts that authority there deliberately and the
  approval is a human + ChatGPT gate, so it is the right place — but it is recorded
  rather than left implicit.
- **`ROLLOVER_AND_HOLIDAY_SLOT_ELIGIBILITY_RELATIVE_TO_THE_OMEGA_CLOCK_NOT_SETTLED`**
  (Ruling ω-11) — **ownership ruled by ω-12(b); the token itself SURVIVES.** Authority
  A governs slot *membership* and Ruling 4 governs event *eligibility*, and `ω` derives
  no rollover or holiday rule of its own — but **whether** such a slot is a member is
  A's content, unknowable before A exists. *An earlier drafting recorded this as "RULED
  … present in the sequence", which decides A's content and authors a market-hours fact;
  **withdrawn**.* ω-11's `0`-to-near-`1` **daily** lever therefore relocates into A's
  content, bound only by (e).
- **The paragraph below is HISTORICAL for `ω`**, retained because it records what
  Ruling ω-1 alone achieved and because the token still has force outside the overlap
  arithmetic:
  §8.4.4 records that "24 M15 bars" is itself unregistered as between the continuous
  UTC grid, bars that exist, and complete buckets only, and that prereg §6 glosses the
  same frozen horizon both as "(6 hours)" and, seven lines later, as a "4–8 h horizon".
  Ruling ω-1 does **not** register which; what it does is bind `g` to whatever `H`
  turns out to be, so the remaining unknown is **one**, not two, and it can no longer
  be exploited **differentially**. That is a genuine reduction and it is not a closure.
  **And the surviving unknown is not a residue — it is MO-2's full-width lever under a
  different name.** The three admissible bar readings are **totally ordered in `ω`**
  (complete buckets ≤ bars that exist ≤ continuous grid, as gaps; the reverse, as
  `ω`), so §8.4.4's own `0`-against-near-`1` illustration survives the ruling intact.
  **The incentive on it also runs one way**: only the *bars-that-exist*,
  *complete-buckets* and *elapsed-excluding-closures* readings import
  `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` (§8.4.15), so the
  `ω`-**minimising** continuous-grid reading is also the only one instantiable without
  an unbuilt approval. That asymmetry is recorded here so a later choice cannot present
  it as a convenience.
- **`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` remains binding** wherever
  instantiating the ruled clock needs the approved calendar artifact (§8.4.4). No
  calendar is generated here.
- **`OVERLAP_PER_RECORD_PROVENANCE_UNBOUND` and the implementation pin.** No source
  and no test is changed by this packet. `effective_n()` still takes `ω` as a bare
  caller scalar with no gaps attached, so **nothing in code enforces any limb above** —
  neither the clock, nor the transform order, nor the weighting, nor pair identity.
  §8.3.0's `P_AUTHORITY_RULED_IMPLEMENTATION_COMPLETENESS_PIN_PENDING` is the same
  residual on the `P` side, and both belong to a **separate Work PR**.
- **A-ω-8 stands:** neither frozen floor can detect a violation of any limb — the raw
  floor contains no `ω`, and the concentration cap is invariant under a permutation of
  counts across labels. Ruling ω-9's producer and freeze point are therefore the only
  place enforcement could live.
- **The correlation `c` is untouched.** Ruling ω-1's clock, ω-4's weighting and ω-9's
  freeze semantics say nothing about `c`'s pair set, method, series, idle days, day
  attribution or freeze point. Those are **NR-L** (§8.5), and this ruling may not be
  cited into any of them.

##### NR-K is untouched

`NR_K_RULED_P_EQUALS_FROZEN_REGISTERED_FAMILY_A_UNIVERSE` stands unchanged: `P = 20`,
no post-hoc shrinkage, an invalid pair does not silently reduce `P`, and a different
universe requires a new explicit decision. **Nothing in the ω aggregation creates a
back-door active-pairs-only universe**: Rulings ω-5 and ω-6 keep zero- and one-event
pairs in the registered universe, Ruling ω-7 forbids pooling, and Ruling ω-8 forbids
re-pairing. §8.4.11's A-ω-7 recorded that `rho_h` carries no pair count at all, so the
`ω` side never had a cardinality to shrink — what it had was the question of what
value fills an excluded pair's slot, and Rulings ω-5 and ω-6 answer it.

#### 8.4.1 What the committed sources actually say

`ω` is used throughout as shorthand for the spec's `mean_overlap_fraction`.

**Scope — the eight objects this packet is about, and nothing else.** (1) what `ω`
means; (2) the overlap **unit**; (3) the overlap **function**; (4) **per-event**
aggregation, i.e. `E[f(gap)]` versus `f(E[gap])`; (5) **per-pair** aggregation;
(6) **cross-pair** aggregation; (7) **zero/one-event** semantics; (8) **measurement
source and freeze point**. Event **ordering** is carried as a ninth because (1) and
(3) are undefined without it.

**Expressly outside it, and untouched:** NR-L and the correlation's pair set,
method, idle-day handling, day attribution, DESIGN-span rule and freeze point;
Q10(i)/(iii); the exact `D`; the actual `T_v`/`T_h`; Q1; Q8; FR-19; and
implementation detail of any kind. A ruling on `ω` may not be cited into any of
them, and §8.4.15 is the handoff.

Reconstructed by reading the sources, not by inheriting a summary.

| Finding | Source |
| --- | --- |
| `rho_h = 1 + (H − 1) · mean_overlap_fraction`, `H = 24`; `N_eff_pair = N_raw_pair / rho_h_pair`; `N_eff = (Σ N_eff_pair) / rho_x` | `effective_n_estimator_spec.json`, `definitions` |
| The **only committed characterisation of `ω`**: "`mean_overlap_fraction` in [0,1] = **mean fraction of a trade's horizon that overlaps the next same-pair trade's horizon**, estimated **per pair** from the **realised inter-event gaps**. Non-overlapping events ⇒ `rho_h → 1`." | same |
| **`ω` is not in `frozen_parameters`.** That block holds exactly three entries — `H_m15_bars: 24`, `N_eff_holdout_floor: 400`, `raw_holdout_trade_floor: 1000` | same |
| **`ω` is not span-scoped at all.** The spec carries `correlation_estimation_data` — "DESIGN span only …; never validation/holdout; frozen once and recorded" — and there is **no counterpart key for the overlap**, in this artifact or any other | same; repo-wide grep |
| `ω` is a **caller input**, validated only as a finite number in `[0, 1]`; the module's own docstring says "the raw counts, **overlap fractions** and correlation are **supplied by the caller**" | `effective_n.py` `_require_unit_fraction` (118–130), module docstring |
| A **second committed formulation**, textually different: "Draft estimator (for the design audit to fix): block-adjust by horizon (events per pair **thinned by mean overlap factor ≈ horizon/mean inter-event gap**)" | prereg §9 |
| The horizon: "**Horizon (Ruling 6 — FROZEN): 24 M15 bars (6 hours)**. No horizon … search"; purge/embargo "≥ horizon + 1 = **25 M15 bars**" | prereg **§6**, §3.2 |
| The event domain: `raw_event_count` = "eligible **traded** events (`n_source_bars == 15` buckets that pass the cost-hurdle and fire an EV-gated trade)", and `effective_n()` refuses `complete_bucket_count` and `cost_hurdle_eligible_bar_count` **by name** | spec; `effective_n.py` `_require_count_quantity` |
| The grid: "bars bucketed by `floor(timestamp / 15 min)` on the **UTC** clock … **No DST logic (UTC only)**"; and "**no synthetic bars across market close**" | prereg §4 |
| The 400 floor "bounds a derived real whose inputs — **realised inter-event gaps** and daily-PnL correlations — are undefined for a slot set" | PR #448 contract Gate-decision |
| **What an event *is*, stated twice and in the same terms.** `raw_event_count` counts "`n_source_bars == 15` **buckets** that pass the cost-hurdle and fire an EV-gated trade", and prereg §6 says "**a bar is an eligible event** only if `1.5 × ATR14_M15 ≥ 2.0 × cost(pair, session)`" | spec `definitions`; prereg §6 |
| The label geometry: entry on the **next bar**, "timeout scored at **horizon-end** mark-to-market", horizon "**24 M15 bars**", no horizon search | prereg §6 |
| **The draft estimator's status.** prereg §9 says the effective-N method is "**[FIXED-AT design audit or gate 3a]**" and labels its own formula "Draft estimator (**for the design audit to fix**)"; the epoch-adoption record places it at T-6 — "**Effective-N estimator approved here**" — and the artifact carries `status: APPROVED_SPEC (T-6 requires the effective-N estimator to be fixed at gate 3a)` | prereg §9; `m15_gate3a_dataset_epoch_adoption.md` §6, T-6 row; spec `status` |
| `turnover()` is documented in its own docstring as "**Portfolio-average trades per day**" | `scripts/ml_step4/metrics.py` |

**So the shape of the gap is partly determinate, and the shape of the measurement
is not.** The spec's *wording* points at a per-pair mean, over trades, of a fraction
of one trade's horizon overlapped by **the next same-pair trade's** horizon,
computed from realised inter-event gaps. **That reading is put to the ruling as
MO-1, not assumed here** — an earlier draft called it "textually determinate" and
then asked MO-1 whether it held, which is the two positions a packet may not hold at
once. Each of MO-1's three limbs is *suggested* by the sentence and *compelled* by
none, and MO-1(b) in particular runs **anti-conservative**: counting only the next
trade understates dependence exactly when horizons stack three deep, which §0.4(b)
shows is admissible at the frozen ceiling. Beyond MO-1, what is undetermined is the
**unit** the gap is measured in, the treatment of **endpoints** (zero-event,
one-event, last-event), the **within-pair** weighting, and **who fixes the value and
when**. The **function** that maps a gap to a fraction and the **order** of the mean
and that function are **derived** at §8.4.10 (D-ω-2, D-ω-4) and are offered for
confirmation, not as choices.

#### 8.4.2 The asymmetry that makes this an authority question

**Against the correlation, `ω` is the unprotected twin.** Both are deflator inputs;
both are unit fractions; both decide `INSUFFICIENT_SAMPLE`. But `c` is span-scoped
("DESIGN span only; never validation/holdout"), **frozen once**, and **recorded**;
`ω` has none of the three. **Nothing prevents `ω` being measured on the very span whose verdict it decides** —
the holdout — while `c` may not be. Stated that way deliberately: MO-7 records that
**nothing computes `ω` at all** today, so the present tense would overstate it, and
the older token `MEAN_OVERLAP_FRACTION_NOT_FROZEN_AND_ROLE_MEASURED` (§0.7) likewise
asserts a role-measurement that MO-6 records as unregistered — it is superseded here.
**`NOTHING_PREVENTS_OVERLAP_BEING_MEASURED_ON_THE_SPAN_IT_JUDGES_WHILE_CORRELATION_IS_FROZEN_ON_DESIGN`.**
Whether that asymmetry is correct is a question, not a defect claim: `ω` is a
statistic of *sample structure*, not of performance, and a structural statistic
arguably must come from the span it describes. **But nobody has recorded that
reasoning, and nothing stops it being read the other way.**

**Against the horizon, the omission is sharper, and it has a committed precedent.**
`rho_h = 1 + (H − 1)·ω` has exactly two inputs. `H` is frozen at 24 *and pinned in
code*: R-1 hardened `horizon_bars` from a caller-settable input into a value that
raises on any value other than the frozen 24, the recorded reason being that the pin
means "an override **can no longer** flip the verdict invisibly" (`effective_n.py`
module docstring, R-1) — and the in-code note widening it records that "pinning it
only for the holdout role still let a validation verdict be flipped by an override,
so it is now frozen for every role". `ω` multiplies `(H − 1)` **in the same expression**, spans
the full `[0, 1]`, and is a free caller input with no producer, no formula, no span
and no freeze point. **R-1's own rationale applies to `ω` verbatim and was never
applied.** This is the same argument §12.6 recorded in NR-K's favour, pointed at the
other input.

**Sensitivity, so the question is not abstract.** *`NON_NORMATIVE_DIAGNOSTIC_ONLY`.*
`rho_h` runs from 1.00 at `ω = 0` to 24.00 at `ω = 1`. §0.3's entire two-effect
deflation budget at the frozen minimum span and the maximum permitted rate is
**4.36**, which `rho_h` alone exhausts at **`ω = 0.146`**. So the admissible band is
roughly the **bottom 15% of `ω`'s domain**, and every question below can move `ω`
across it. Now that §8.3.0 fixes `P = 20`, the `(P − 1) = 19` in that budget rests on
a ruling rather than on an assumption. **`ω` is not thereby the last unpinned
term** — an earlier draft said so and it is **withdrawn**. `c` is unruled too
(NR-L), and by the same budget its admissible band is the bottom **17.7%** of its
domain against `ω`'s 14.6%. What the ruling changed is that `rho_x`'s **cardinality**
is fixed while its **value** is not, so **both** deflators still turn entirely on an
unruled caller-supplied scalar. `ω` is sequenced first because it carries **neither**
a span scope nor a freeze obligation, where `c` carries both — "DESIGN span only …
frozen once and recorded" — even though `c`'s method, pair set and freeze *moment*
are unregistered.

#### 8.4.3 The two committed formulations are different objects — and §0.5 mislocated the divergence

**`MEAN_GAP_APPROXIMATION_IS_NOT_AN_ALLOWED_EFFECTIVE_N_AUTHORITY_FOR_CURRENT_FAMILY_A`
— everything in this subsection about the draft's `horizon / mean inter-event gap` is
`NON_NORMATIVE`, retained for traceability only.** Ruling ω-3 (§8.4.0) forbids its
adoption as an alternate implementation choice; it is neither the governing estimator
nor an option, and nothing here may be cited as making it one.

**They are not two estimators of one quantity.** The spec's `ω` is a **fraction in
[0, 1]** that gets multiplied by `(H − 1)`. The prereg's "mean overlap factor" is,
by its own sentence, what events are "**thinned by**" — a **divisor**, whose value
`H/ḡ` exceeds 1 exactly when the mean gap falls inside the horizon. They have
different ranges and different positions in the arithmetic.

**One consequence is decisive and mechanical.** The APPROVED spec's own definition
says `mean_overlap_fraction` is "**in [0,1]**", and `_require_unit_fraction` enforces
it — a committed test refuses a fraction "just above one" by name. *(Contract first,
code second: the bar is the spec's, and the implementation only holds it.)* So the
prereg draft's quantity is **inadmissible as `overlap_fraction` throughout the
overlapping regime**, which is the only regime the adjustment exists for. The
draft's number lands inside `[0, 1]` only when `ḡ ≥ H` (it is exactly `1` at
`ḡ = H`), i.e. precisely where the
spec says the answer is `rho_h → 1` anyway.

**And the draft's sentence is incoherent at one end whichever way it is read.** As a
**divisor**, `H/ḡ < 1` at `ḡ > H` would *inflate* the count; as a **multiplier**,
`H/ḡ > 1` inside the horizon would do the same. Each reading needs a repair, at
opposite ends. Everything below applies `max(1, H/ḡ)` — the divisor reading with the
sub-unit end clamped — and **that clamp is this packet's, not the prereg's**, which
writes `H/ḡ` and no clamp. The clamp is near-forced by the word "thinned by", but it
is a reading, and it must be labelled as one.

**Which forces a correction to §0.5, and it runs against this packet's earlier
convenience.** §0.5 wrote that at the frozen ceiling the draft "yields" `0.5`,
"hence `rho_h = 12.5`", and concluded that "the two committed formulas disagree by
12.5× in `rho_h` at the frozen ceiling". The `12.5` was produced by feeding the
*draft's divisor* into the *spec's fraction slot*, where it is multiplied by
`(H − 1)`. That is a unit-type splice under any reading, and it is **withdrawn**.

**But the ceiling relationship is *undetermined*, not agreed — and an intermediate
draft of this subsection said "they agree", which is also withdrawn.** Under the
clamped-divisor repair the two give `1.00` and `1.00` at a 48-bar mean gap — the
value the frozen ceiling implies **only under equal allocation across the twenty
pairs**, which §0.4(c) shows the concentration cap does not require — while under the
multiplier repair the draft thins by 0.5 there, an effective `rho_h` of `2.00`
against the spec-style `1.00`. **Which repair applies is unruled**, so the agreement
rests on the packet's own clamp. Recording "they agree" would resolve — in the
feasibility-favourable direction §0.5 itself names, since `rho_h = 1.00` at the
ceiling frees the entire 4.36 budget for `c` — a divergence this packet exists to
keep open.

**The divergence is real, and inside the horizon it is large under either repair.**
Taking the spec's two pinned endpoints with the natural fraction `max(0, 1 − g/H)` —
labelled as a *reading*, since §8.4.1 records that the spec never writes a formula —
and the draft's `max(1, H/ḡ)` — a *reading* too, per the clamp caveat above — under
regular arrivals: *`NON_NORMATIVE_DIAGNOSTIC_ONLY`.*

| mean gap (M15 bars) | spec-style `rho_h`, i.e. `1 + 23·max(0, 1 − ḡ/H)` at the **mean** gap (`φ(E[g])`, the quantity §0.4(a) withdrew as an *argument*) | draft divisor `max(1, H/ḡ)` | ratio |
| --- | --- | --- | --- |
| 48 | 1.00 | 1.00 | **1.00×** |
| 24 | 1.00 | 1.00 | **1.00×** |
| 18 | 6.75 | 1.33 | 5.06× |
| **12** | **12.50** | **2.00** | **6.25×** |
| 6 | 18.25 | 4.00 | 4.56× |
| 3 | 21.12 | 8.00 | 2.64× |
| 1 | 23.04 | 24.00 | 0.96× |

Under this repair they coincide at both ends, diverge by up to ~6.25× **inside**
the horizon — the true maximum of the ratio is `6.261` at `ḡ ≈ 12.52` — and even
**cross** at the dense end — the crossover sitting just **above** `ḡ = 1`, at
`ḡ ≈ 1.043`, which matters because D-ω-1 derives a **one-bar minimum gap**, so the
crossing region is narrowly *inside* the reachable domain rather than beyond it.
Under the
multiplier repair the ceiling row instead reads `1.00` against `2.00`. The open item is therefore renamed:
`DRAFT_AND_APPROVED_OVERLAP_ESTIMATORS_DIVERGE_AT_THE_FROZEN_CEILING` is
**superseded** by **`DRAFT_AND_APPROVED_OVERLAP_FORMULATIONS_ARE_DIFFERENT_OBJECTS_AND_DIVERGE_INSIDE_THE_HORIZON`**.

**What survives of §0.5, and what does not.** The rescue of the 3.3-year figure
rested on two legs. The **clustering leg stands**: at exactly the frozen ceiling,
`ω = 0.5` is reachable by clustered arrivals, as §0.4(b) independently shows
(`sup rho_h = 24` at the ceiling, a mean-only constraint bounding nothing). The
**committed-formula leg is withdrawn**: the draft does not yield `ω = 0.5` at the
ceiling, because its output is not an `ω`. The figure remains **not adopted**, as
§0.5 already said, and §0.4(a)'s withdrawal of the `rho_h = 1` claim is
**unaffected** — it turned on Jensen, not on either formula's identity.

#### 8.4.4 Why the *unit* is decisive — and why Q10-A does not transfer

The gap has no committed unit. The candidates are not stylistic:

| Candidate | What it counts | Where it bites |
| --- | --- | --- |
| **M15 bars on the continuous UTC grid** | grid slots, including closed periods | the grid is committed (`floor(timestamp / 15 min)`, UTC, no DST) — but §8.2.2 records that it fixes the **bucketing basis** and "does not, on its face, denominate a *duration*", and `calendar_authority.py` calls it "the frozen derivation contract, **not a market-hours decision**". It does not by itself say which slots carry bars |
| **M15 bars that exist** | buckets actually produced — "**no synthetic bars across market close**" | a weekend contributes **zero** bars, so two trades either side of it can be adjacent |
| **Complete buckets only** (`n_source_bars == 15`) | the eligibility unit | a bucket short of fifteen source minutes exists as a bar but is never an event; whether such bars consume horizon is unregistered |
| **Elapsed time, including closed periods** | minutes or hours on the wall clock | any closure longer than the horizon's wall-clock extent puts every gap across it beyond the horizon, so the contribution is `0` |
| **Elapsed time, excluding closed periods** | wall-clock time with closures removed | behaves like the bars-that-exist reading, and additionally needs the approved calendar artifact to say what is excluded |
| **Approved-calendar eligible M15 slots** | slots the approved calendar authority declares eligible | calendar-derived and **immune to data presence**; this is the substrate **Ruling ω-11 selects**, and it was absent from this table when the table was written |
| **Event index** | "the k-th trade", ignoring time | under MO-1(b)'s *next-event* reading the index gap is **identically 1**, so `ω` collapses to a constant independent of the data; it varies only if MO-1(b) is varied too |

**A closed-market interval separates the candidates by the full width of the
band**, and the argument needs no session boundary to make it. Take two same-pair
trades separated by a market closure, one shortly before it and one shortly after.
In **elapsed calendar time** the gap contains the whole closure, so any closure of
material length puts the gap far beyond a 6-hour horizon and the contribution is
**0**. Counted in **bars that exist**, the closure contributes **nothing at all** —
prereg §4 commits "**no synthetic bars across market close**" — so the gap is only
the open bars on either side, and two trades placed near the close and near the
reopen are **near-adjacent in that unit**. On the spec's own characterisation —
"the fraction of a trade's horizon that overlaps the next same-pair trade's
horizon" — two near-coincident horizons overlap almost entirely, so the contribution
is near **1**. *That upper endpoint is a reading of the characterisation, not one of
the two endpoints §8.4.7 records as pinned.* One pair of trades, one unit choice,
and the two answers sit at opposite ends of `ω`'s whole domain — one inside
§8.4.2's admissible band and one roughly seven times beyond its top. (A single
contribution is not `ω`, which is a mean over events; the point is the leverage,
not the resulting mean.)

**One committed constraint already bears on the route, without closing the
question.** The merged D-5.8 Gate-decision — ruling a different question two lines
below the sentence §8.4.1 quotes from it — records that where a quantity turns on
the closed-market fraction, "any admissible answer must be
**market-hours-independent, or carried by the approved calendar artifact**". Two
candidates here, *bars that exist* and *complete buckets only*, are neither: they
need no calendar to compute, but they make `ω` a function of **data presence** and
cannot distinguish a data outage from a closure — which is in effect the inference
`calendar_authority.py` refuses ("never reverse-infers 'there is no data, therefore
the market was closed'"). **That foreclosure's scope is D-5.8 and it does *not* rule
MO-2.** It is recorded because a ruler choosing either candidate thereby imports
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`, the same unbuilt dependency
§8.2.3 weighed against Option B for `D`.

**Two committed sources and one of this packet's own readings point at the bar
family, and none of them rules it.** §8.2.2's reason-giving rule — "**Model
mechanics** — every quantity defined by the label horizon or the feature lookback —
is denominated in **M15 bars**" — is **this document's own distillation from the
contract, not a committed sentence**, and §8.2.0 says of it in terms that "nothing
rules it and **Q10-A does not**"; an earlier draft of this paragraph listed it as
committed, which is withdrawn. The two that are committed: `warmup.py`'s `bar_index`,
"Zero-based over forward-epoch **bars**"; and prereg §9's `horizon / mean
inter-event gap`, whose quotient is dimensionless only if the gap shares `H`'s unit.
Recorded as evidence, **not as a ruling** — the prereg draft is expressly "for the
design audit to fix" and §8.4.3 shows it is a different object.

**And one committed source of structural gaps needs no calendar at all.** Prereg §5
(Ruling 4, **FROZEN as minimum**) makes the rollover window **21:55–22:15 UTC
minimum** event-ineligible, "widen it only for conservatism; it must not be
narrowed". That guarantees a break in every pair's event sequence every day without
any market closure and without importing the approved calendar — so closures are not
the only source of structural gaps, and the MO-2 candidates differ on this one too.
No length or widening is assumed here beyond the committed minimum.

**And §8.2.3's Option-C circularity objection does not transfer here.** `D` is a
pre-freeze *planning* quantity, so defining it by observed slots is circular; `ω` is
a *measured statistic*, so data-dependence is not circularity. Option C may not be
cited to foreclose the bars-that-exist or complete-buckets candidates.

*An earlier draft of this paragraph made the point with a concrete Friday-evening
to Monday-morning example and a 0.5 contribution. **Withdrawn**: that arithmetic
required a weekly close instant and a reopen instant, and **this repository authors
neither**. `calendar_authority.py` "validates an injected calendar. **It never
authors one**" and "contains no market open/close instant, no DST transition date,
and no holiday", because D-6 makes the expected slot set the approved artifact's
property and never an inference. No closure length, boundary or reopen time is
asserted here, and none may be inferred from this illustration — the leverage comes
from a closure **existing**, which prereg §4 already commits, not from where it
falls. `NON_NORMATIVE_DIAGNOSTIC_ONLY`.*

**And the horizon's own wall-clock extent is unfixed too — separately.** The
contract's gloss is "24 M15 bars **(6 hours)**", exact only where the counted bars
are contiguous grid slots; prereg §4 forbids synthetic bars across market close, so
a 24-bar horizon opened shortly before a closure is 6 hours on the continuous-grid
reading and reaches past the closure on the bars-that-exist reading. The contract
does not settle which — seven lines after the "(6 hours)" gloss, **prereg §6
describes the same frozen horizon as a "4–8 h horizon (vs 20 min)"**, and no
committed source reconciles the two. Nor does the machinery: `scripts/m15_gate3a/`
carries `HORIZON_M15_BARS = 24` as a pinned scalar and **no counting rule at all**,
and the only positional implementation anywhere — `scripts/ml_step4/labels.py`'s
`bars[i + 1 : i + 1 + horizon]` — is M1-lineage code prereg §11 admits only "after
audit/wrapping", not adopted here.
**`HORIZON_WALL_CLOCK_EXTENT_NOT_REGISTERED`.**

**This is adjacent to the gap unit, not produced by it, and an earlier claim that it
was is withdrawn.** The gap unit cannot reach the horizon the label machinery
applies, so it does not "re-scale `H` by the back door" — that earlier wording
claimed a causal path that does not exist. What is true is narrower: "fraction **of
a trade's horizon**" is well defined only if the gap and `H` are read in the **same**
unit, so answering MO-2 fixes how `H` is read **inside `ω`'s arithmetic**, and
nowhere else.

**Q10-A does not answer this, and must not be cited as if it did.** Ruling Q10-A
fixes `D` as an elapsed UTC calendar span — that is authority over the **duration
axis**, the length of a role window. The gap unit is authority over the
**event-spacing axis**, the spacing between two events inside a window. §8.2's own
guard-rail is exactly this distinction:
`D_IS_ELAPSED_UTC_TIME != SAMPLE_COUNT_IS_CALENDAR_TIME`, recorded there because
defining `D` as a calendar span "does **not** count weekends as samples, does
**not** make holidays eligible events, and does **not** turn closed-market intervals
into observations" — and because that same guard-rail names **overlap** among the
quantities that "stay with their own registered authorities", so that "the unit of
`D` may not be borrowed for any of them". Reading Q10-A across into `ω` would do the
thing the guard-rail forbids by name, and would do it in the direction that lowers
`ω`. **`Q10_A_DOES_NOT_RULE_THE_GAP_UNIT`.**

#### 8.4.5 What the form assumes, and nobody registered

Recorded as structural observations. **None of these is a question this packet
answers, and none is a defect claim.**

- **`(H − 1) = 23` counts the other bars in a horizon; `ω` is defined against the
  *next trade only*.** The form linearly interpolates `rho_h` from 1 to `H` using a
  single scalar taken from one neighbour. Under regular arrivals "overlap with the
  next trade" and "how many horizons are open at once" track each other; **under
  clustering they do not**, and §0.4(b)/§0.4(c) show clustering is admissible at the
  frozen ceiling. Whether `ω` should be the next-trade overlap or the mean count of
  concurrently open horizons is a **modelling choice the spec's wording suggests,
  that nobody has examined, and that is put as MO-1(b)** — not one the spec settles.
- **The spec's wording reads as an unweighted mean** ("mean fraction … of a trade's
  horizon"), weighting every event equally regardless of how much of the span it sits
  in. Whether it *is* unweighted is **MO-1(c)**, and MO-6 lists the within-pair
  weighting as open.
- **`rho_h` enters as a divisor of a count**, so a per-pair `ω` measured with error
  does not average out across pairs — it is a ratio, and errors compound with the
  numerator. **And the bias runs anti-conservatively**: `1/(1 + 23ω)` is convex in
  `ω`, so mean-zero error in a per-pair `ω` raises expected `N_eff`. Same Jensen
  argument as MO-4, in the other variable.
- **The weighting limb spans the whole range, and it is this packet's largest
  unquantified lever.** Every other open limb here carries a magnitude; this one had
  none. For any weights `wᵢ ≥ 0` summing to 1, `ω` lies in
  `[minᵢ overlap(gᵢ), maxᵢ overlap(gᵢ)]`. **With all four of §8.4.10's derivations
  confirmed and the realised gap sequence held fixed**, a pair carrying one
  adjacent-event gap and one gap at or beyond the horizon has `rho_h` reachable
  anywhere in `[1.00, 23.04]` by the weighting choice alone — the entire admissible
  range. And the direction is unconditional: `overlap` is non-increasing in `g`, so a
  weighting that puts more mass on longer intervals lowers `ω` for **every** gap
  sequence. On §0.3's own Poisson diagnostic at the frozen ceiling, interval-length
  weighting gives `ω = 0.033` and `rho_h = 1.75` against the unweighted `0.213` and
  `5.90` — a 3.37× move in `N_eff`, and the difference between §0.3's infeasibility
  conclusion and `N_eff = 996` at `c = 0`. *`NON_NORMATIVE_DIAGNOSTIC_ONLY`. No
  weighting is proposed or recommended; the point is the span of MO-1(c) and MO-6's
  within-pair limb, which §0.3 does not record that its headline turns on.*

#### 8.4.6 The questions

**MO-1…MO-7 keep the identifiers they were committed under**, and **MO-8** is added
for event ordering, which the earlier draft assumed rather than asked. The eight
decision objects in §8.4's scope map onto them as follows, so that a ruling can be
given against either list:

| Decision object | Question |
| --- | --- |
| 1. what `ω` means | MO-1 |
| 2. overlap **unit** | **MO-2** |
| 3. overlap **function** | MO-3 |
| 4. **per-event** aggregation — `E[f(gap)]` vs `f(E[gap])` | MO-4 |
| 5. **per-pair** aggregation | MO-6, *within-pair* limb |
| 6. **cross-pair** aggregation | MO-6, *across-pairs* limb |
| 7. **zero/one-event** semantics | MO-5 |
| 8. **measurement source and freeze point** | MO-7 |
| (9.) event **ordering** | **MO-8** |

§8.4.10 records which of these are **derivable from committed authority** and which
are genuine choices; the questions below are stated in full regardless, because a
derivation offered to a ruling must be checkable against the question it answers.


**MO-1 — the mean of what, exactly, over what index?** The spec says "mean fraction
of a trade's horizon that overlaps **the next same-pair trade's** horizon".
(a) The index is the pair's **traded events** — settled by that sentence, since the
objects being spaced are trades, and restated here only so the mean's index is stated
in full; **not offered for variation** (§8.4.7). Confirm or vary: (b) the overlap is
against the **immediately next** event only, not against all events whose horizons
intersect; (c) the mean is **unweighted**. Limb (b) is the one with a direction:
next-event-only **understates** dependence under clustering, which is
anti-conservative.

**MO-2 — in what unit is the inter-event gap measured?** M15 bars on the continuous
UTC grid · M15 bars that exist (no synthetic bars across market close) · complete
buckets only (`n_source_bars == 15`) · elapsed wall-clock time · calendar time
**including** closed periods · elapsed time **excluding** closed periods · event
index · other. The two elapsed readings are separated because they behave like the
first and second bar readings respectively, and the exclusion reading additionally
needs the approved calendar artifact to say what is excluded; an earlier list wrote
"elapsed wall-clock time · calendar time including closed periods" without saying
which was which. §8.4.4 shows the choice can move a single pair of trades from an
`ω`-contribution of `0` to one near `1`, and that the wall-clock extent of `H` is
separately unregistered. Note also that "gap" already has a **different** committed
referent in this machinery: `aggregation.py` emits a `gap_report` with
`max_gap_minutes` / `max_unavailable_gap_minutes`, a **missing-minute** diagnostic
denominated in minutes. That is a term collision of the kind the contract
Gate-decision flags, and its minute denomination is **not** precedent for an
elapsed-time inter-event gap.

**MO-3 — what is the exact overlap formula?** The spec pins two endpoints — the
result lies in `[0, 1]`, and non-overlapping events give `rho_h → 1` — and writes no
formula — but the endpoints are not the basis. **§8.4.10's D-ω-2 derives the
function from the spec's characterising sentence**, "the fraction of **a trade's
horizon** that overlaps **the next same-pair trade's horizon**", which fixes it
uniquely once `H` is a constant contiguous length on the gap's clock. Convex and
step-shaped alternatives satisfy the two endpoints but are **not** admissible
readings of that sentence — with one exception D-ω-2 names: where the two horizons
are *not* of equal length on the chosen clock, the true form is
`max(0, min(L_i − g, L_{i+1}))/L_i`, which is step-shaped, and that is a consequence
of MO-2 rather than a free choice of functional form. **This packet therefore
chooses none by preference; it offers a derivation for confirmation (§8.4.10),
conditional on MO-2's clock and on MO-1(b).**

**MO-4 — `mean(overlap_i)` or `overlap(mean_gap)`?** Separating the mathematics from
the authority, because the two answers differ:
*The mathematics.* For any convex overlap function, Jensen gives
`E[f(g)] ≥ f(E[g])`, so computing the overlap of the mean gap is **the smaller
number** — a smaller `rho_h`, a larger `N_eff`, and a verdict closer to passing.
Where the mean gap exceeds the horizon, `f(E[g]) = 0` while `E[f(g)]` may be
substantially positive: §0.3's Poisson diagnostic at the frozen ceiling gives
`E[f(g)] = 0.213` against `f(E[g]) = 0`. *That is a fact about convex functions, and
it holds whatever the ruling says.*
*The authority.* The spec's phrase "estimated per pair from the realised inter-event
**gaps**" (plural) reads naturally as the per-event mean, and §0.4(a) already
**withdrew** the mean-gap argument on exactly this ground. "Estimated from the gaps"
is *literally* satisfied by averaging the gaps first, which is why the reading was
carried this far — but **§8.4.10's D-ω-4 forecloses it from the spec's own words**:
"mean **fraction**" makes *fraction* the object and *mean* its operator, and
reversing them to "fraction at the mean gap" inverts the two. Its only textual
support was the draft, which D-ω-3 places as superseded. **MO-4 is offered as a
derivation for confirmation, not as an open choice**; Option B is retained at
§8.4.13 only so the ruling can refuse it by name, and the anti-conservative reading
is what a rejection of D-ω-4 would reinstate.

**MO-5 — zero-event, one-event and idle-day handling.** A pair with **no** events
has no gaps, so `ω` is undefined — yet `_require_unit_fraction` demands a number and
`_require_count` admits `raw_event_count = 0`, so the caller must supply something.
A pair with **one** event likewise has no gap, and there `ω` is not cosmetic: it
divides a real count. In a pair with `n` events there are `n − 1` gaps, so whether
the **last** event contributes a term, and with what value, is an `n` versus `n − 1`
question that matters most at small `n` — which is the regime the floors are
contested in. And whether **idle days** enter at all is the same ambiguity NR-L
records for the correlation, on a different series.

**MO-6 — aggregation.** Two levels, and they have different statuses.
*Across pairs — **settled, and must not be reopened.*** The spec fixes
`N_eff_pair = N_raw_pair / rho_h_pair` with `granularity: [portfolio, per_pair]`;
B-3 was a recorded **defect** precisely because the implementation collapsed this
into one portfolio scalar from a single aggregate `overlap_fraction`, a substitution
that was "not equivalent when overlap varies across pairs and … not conservative"
(audited counter-example: `383.33 → INSUFFICIENT_SAMPLE` under the spec against
`644.00 → SAMPLE_SUFFICIENT` under the collapse). `ω` is **per pair**. This question
is **settled by committed text and is not reopened by this packet.**

**But what is settled is the rule, not its enforcement.** The per-pair *form* is
enforced — `_normalise_pairs` requires an `overlap_fraction` on every record — while
**nothing binds a record's `overlap_fraction` to that pair's realised gaps**, exactly
as `PER_RECORD_COUNT_PROVENANCE_UNBOUND` (§8.3.1) records for the counts. One
portfolio-mean `ω̄` supplied in all twenty slots reproduces the collapsed arithmetic
**identically**, since `Σ Nₚ/(1 + 23ω̄) = (Σ Nₚ)/(1 + 23ω̄)`; on the audited
counter-example that is `50/12.5 + 8000/12.5 = 644.00` — the pre-B-3 number, through
the post-B-3 signature, with every guard satisfied. *`NON_NORMATIVE_DIAGNOSTIC_ONLY`.*
**`OVERLAP_PER_RECORD_PROVENANCE_UNBOUND`.** This reopens no aggregation rule; it is
why MO-7's producer and freeze point are load-bearing.
*Within a pair — open.* Over which events, with what weighting, with `n` or `n − 1`
in the denominator, and whether `ω` is measured **separately per role**. The spec
requires reporting `per_role: [validation, holdout]` but never says `ω` is
role-separate, and — unlike `c` — never says it is not.

**MO-7 — freeze point and measurement source.** Who computes `ω`, from which
artifact, and at what moment is it frozen? Today: no producer function exists
(§8.3.1 records that `effective_n()` has **no production caller**); `ω` arrives as a
caller argument; no artifact records it; no span is fixed; and the natural default
is measurement on the holdout itself (§8.4.2). Whether `ω` must be frozen before the
span it judges — as `c` is — or measured on it, is the question, and it must be
answered **before** any continuation, because after the fact the choice is
unfalsifiable.

**And *whose* `ω` is it?** `PER_RECORD_COUNT_PROVENANCE_UNBOUND` (§8.3.1) binds a
record's label but not its numbers, and `overlap_fraction` rides the **same record**
as `raw_event_count`. A producer rule that does not also bind `ω_p` to pair `p`
leaves the pairing of counts with overlaps free — the one degree of freedom `P = 20`
does not remove (§8.3.0), and worth up to a 20.9× swing on the audited shapes.

**MO-8 — event ordering.** By what timestamp are a pair's events ordered; can two
events of one pair be simultaneous; can a gap be zero or negative; and does a
day or week boundary raise an ordering question? §8.4.10 answers all four **from
committed text** and adds no implementation specification. The question is stated
because MO-1 and MO-3 are undefined without it, and because a *supplied* `ω` carries
no gaps at all, so nothing in the estimator can check that any of it held
(`OVERLAP_PER_RECORD_PROVENANCE_UNBOUND`).

#### 8.4.7 What is already fixed, and must not be reopened under cover of this packet

- **`H = 24` M15 bars** — Ruling 6, FROZEN, pinned in code for every role (R-1).
- **`ω ∈ [0, 1]`** — the APPROVED spec's own definition, enforced by
  `_require_unit_fraction`; and **non-overlapping events ⇒ `rho_h → 1`**. These two
  are the **only** committed bounds on `ω`; **A-ω-4 forbids adding any other cap,
  floor, clamp or winsorisation without committed authority**, and records why
  D-ω-2's `max(0, ·)` is interval arithmetic rather than a clamp.
- **Per-pair granularity** — `rho_h` is per pair; the portfolio-scalar collapse is a
  closed defect (B-3), not an option **in the function's signature** — though nothing
  yet binds each record's `ω` to its own pair (MO-6,
  `OVERLAP_PER_RECORD_PROVENANCE_UNBOUND`).
- **The count domain** — `raw_traded_event_count` only; `complete_bucket_count` and
  `cost_hurdle_eligible_bar_count` are refused **by name**. *That the **gap** also
  runs between **trades** rather than between slots is sourced to the spec's own
  sentence — "a **trade's** horizon … the **next same-pair trade's** horizon" — and
  **not** to `_require_count_quantity`, which governs which *count* is fed and says
  nothing about the spacing domain. Two roles split on this: one held the gap domain
  fixed, the other that it was unsourced. Both are half right, and the resolution is
  the re-sourcing above — MO-1(a) is settled by the spec's sentence, and the
  `count_quantity` refusal is not the authority for it. It fixes what the gap runs
  **between**; it does not fix the unit it is **counted in**, which is MO-2 and stays
  open, the grid-slot unit included.*
- **`P = 20`** — §8.3.0. `ω` and `P` are inputs to **different** deflators, and
  nothing in this packet reaches `rho_x`.
- **`ω` may not anchor the window.** Ruling Q10-B forbids anchoring on "a date
  chosen after observing empirical **label** overlap (`mean_overlap_fraction` /
  `rho_h`)". Whatever MO-7 decides, no answer may make the declared validation start,
  `T_v`, `T_h` or the holdout window responsive to a measured `ω`;
  `SAME_D_DIFFERENT_WINDOW_IS_RESELECTION` applies unchanged. This is the one ruled
  clause that names `ω` by name.
- **The turnover ceiling is not a gap bound.** `turnover()` is
  `n_trades / n_trading_days` — a **portfolio mean over the span**, not a per-day cap
  and not a lower bound on any individual inter-event gap. §0.4(b) records that a
  mean-only constraint admits arbitrary clustering, with `sup rho_h = 24` at exactly
  the frozen ceiling. **No answer to MO-1…MO-8 may be derived from `≤ 40 trades/day`,
  and no bound on `ω` may be inferred from it.**

#### 8.4.8 Why this is an authority parameter, not an implementation detail

`ω` is **`MEAN_OVERLAP_FRACTION_IS_AN_EFFECTIVE_N_AUTHORITY_PARAMETER`**, on the same
footing as `P` and `c`, for four reasons that are all matters of record: it is one of
the two inputs to `rho_h`, and the other one is **frozen and pinned in code**; it
spans a range within which roughly the bottom 15% is admissible against §0.3's
budget **at the frozen minimum span and the maximum permitted rate**; it has **no producer, no artifact, no span and no freeze point**, so whoever
computes it first sets it; and the **eight** questions above are choices or
derivations between committed readings, not implementation conveniences — **four are
derived (§8.4.10)**, and each of MO-2, MO-3 and MO-4 can move the verdict on its own.

The parallel with NR-K is exact and is the reason this was the next decision rather
than a note: NR-K existed because a verdict-deciding input was caller-supplied with
one undefined word of specification. So does this.

#### 8.4.9 What this packet does not do

It **rules nothing**, and the distinction §8.4.10 turns on is not a qualification of
that. A **derivation** reconstructs what committed text already says and offers it
for confirmation; a **ruling** chooses where committed text is silent. §8.4.10
derives four of the nine objects and offers them under
`MEAN_OVERLAP_CORE_DERIVED_READY_FOR_REVIEW`; it decides none of the five that are
genuine choices, and a derived limb that the ruling rejects is simply a derivation
that was wrong. It invents no gap unit, no overlap formula, no aggregation rule, **no
clipping** (A-ω-4) and no freeze point, and where committed text is silent it says so
rather than supplying a default. It performs **no empirical measurement** of any kind — no gaps,
no overlaps, no event rates, no `N_eff` — reads no data, and touches no source, test
or artifact. Every numeric in it is `NON_NORMATIVE_DIAGNOSTIC_ONLY` under the
document-wide rule, computed under stated modelling assumptions, appearing in no
committed source, and usable neither to size `D` nor to justify a contract position.


#### 8.4.10 What is derivable from committed authority — four of the nine

Stated separately from the questions, because a packet that mixes derivation with
preference is the defect §8.4.1 already had to withdraw once. Each derivation below
runs from quoted committed text; where a step is a reading, it is labelled.

**D-ω-1 — an event *is a bar*, so ordering is total, ties cannot arise, and the
minimum gap is one bar. (MO-8.)** The count is over **buckets**: `raw_event_count`
is "`n_source_bars == 15` **buckets** that pass the cost-hurdle and fire an EV-gated
trade". Prereg §6 indexes the wider set the same way — "**a bar is an eligible
event** only if `1.5 × ATR14_M15 ≥ 2.0 × cost(pair, session)`" — and the two are
**not** the same set: traded events are the subset of eligible events that fired,
and the gap here is between **traded** events (§8.4.7's count domain). The step used
below is only the containment `traded ⊆ eligible ⊆ that pair's buckets`, which both
sentences give — and the containment is all that is taken, because the *eligible*
set is `cost_hurdle_eligible_bar_count`, a quantity `_require_count_quantity`
**refuses by name**. Prereg §6 corroborates the **type** of the index, never its
extension. Prereg §4
fixes the bar's identity — `floor(timestamp / 15 min)` on the UTC clock, bar
timestamp = bucket start, "**No DST logic (UTC only)**". Four consequences follow
without adding anything:

- a pair's events are a **subset of that pair's buckets**, ordered by bucket start;
  the order is **total and deterministic**, since bucket starts are distinct;
- **at most one event per pair per bucket** — the committed quantity counts buckets,
  so the bucket is the unit of count, and two same-pair events in one bucket are not
  representable in `raw_event_count`. **And prereg §8 is the direct authority, which
  an earlier draft of this bullet missed**: the frozen EV gate is stated "for each
  eligible **bar** and direction `d ∈ {long, short}` … **Trade direction `d` iff
  `EV_d ≥ ev_min` and `EV_d > EV_{−d}`**" (Ruling 8/9, FROZEN). The rule is per
  **bar**, and its strict `>` lets at most one direction fire. *(An execution layer
  emitting two orders inside one bucket would therefore be **contract-non-conforming
  for family A**, not a free implementation choice. Were it to happen, the committed
  count would under-count by its own definition and `ω` would **under**-state
  overlap — the anti-conservative direction. Concurrency and exposure caps are
  `[FIXED-AT design audit]` and can only restrict this further.)*
- therefore **ties and simultaneous same-pair events cannot arise**, the **minimum
  gap is one bucket step** — one bar in MO-2's bar readings, and the corresponding
  minimum in whichever unit MO-2 fixes — a **zero gap is impossible**, and a
  **negative gap is impossible**. Jointly with D-ω-2 this also gives
  `overlap_i ≤ 23/24` and **`sup rho_h = 23.04`** for any `ω` computed *from realised
  gaps*, which refines the `sup rho_h = 24` written at §0.4(b), §8.4.2 and A-ω-3;
  it does **not** bound a *conventional* `ω` supplied under MO-5 for a pair with no
  gaps, so §8.4.12's 24× range at one event stands as written;
- a **day or week boundary raises no ordering question**, because the grid is one
  UTC clock with no DST logic. *(It does raise the MO-2 unit question — how far
  apart two events across a closure are — which is a different matter.)*

**D-ω-2 — the overlap function is interval arithmetic, not a modelling choice.
(MO-3.)** The spec's own words are "the fraction of **a trade's horizon** that
overlaps **the next same-pair trade's horizon**". Both horizons have the *same*
frozen length `H = 24` bars (Ruling 6, FROZEN, no horizon search). Two intervals of
equal length `H` whose starts are `g` apart intersect in `max(0, H − g)`. As a
fraction of one horizon:

> `overlap_i = max(0, H − g_i) / H = max(0, 1 − g_i / H)`

Three things worth stating precisely:

- **The `max(0, ·)` is not an invented clamp.** An intersection length cannot be
  negative; the `max` *is* the arithmetic, not a bound added to taste. This is the
  distinction §8.4.11 makes normative, and it is exactly what separates this from
  the `max(1, H/ḡ)` of §8.4.3, which **is** a clamp this packet had to supply for
  the draft and which is labelled as one there.
- **The offset convention cancels.** Whether the horizon runs `i … i+H−1` or
  `i+1 … i+H`, both horizons use the same convention, so the intersection is
  `max(0, H − g)` either way. The label geometry's "entry on the next bar,
  timeout scored at horizon-end" does not change it.
- **It satisfies both pinned endpoints** — the result lies in `[0, 1]`, and
  `g ≥ H` gives `0`, hence "Non-overlapping events ⇒ `rho_h → 1`".

*Conditional on **three** things, and on no statistical assumption:* MO-2's unit
(`g` and `H` must be read on the same clock — see D-ω-2a); MO-1(b)'s next-event
restriction; and **that `H` is a constant, contiguous length on that clock**.

**The third condition is not free, and an earlier draft of this derivation said
"two things and no more".** §8.4.4 is why: `HORIZON_WALL_CLOCK_EXTENT_NOT_REGISTERED`,
"whether such bars consume horizon is unregistered" for incomplete buckets, and
prereg §4's "no synthetic bars across market close" together mean that on the
continuous-grid, complete-buckets and elapsed-time clocks two horizons need **not**
have equal length and a horizon need not be contiguous. Where the lengths differ,
interval arithmetic gives `max(0, min(L_i − g, L_{i+1})) / L_i`, which is **flat then
linear** — *not* `max(0, 1 − g/H)`, *not* linear in `g`, and *not* a function of `g`
alone — while the spec requires `ω` to be estimated "from the realised inter-event
**gaps**". §8.4.4's rule that answering MO-2 "fixes how `H` is read inside `ω`'s
arithmetic" restores a constant `H` **by stipulation**, at the cost of detaching
`ω`'s `H` from the label machinery's; **that step is a reading, and is labelled as
one here.** So D-ω-2 is derived **for any clock on which `H` is a constant contiguous
24** — which is §8.4.14 limb 1's *recommended* half, not its derived half.

*One further assumption, and it runs the safe way.* D-ω-2 treats every trade's
horizon as the full frozen `H`. Prereg §6's geometry lets TP or SL end a trade early,
so an information-window reading would give a **shorter** overlap. That direction is
**conservative** — larger `ω`, smaller `N_eff` — so it strengthens the derivation
rather than qualifying it, and no reading is proposed here.

**D-ω-2a — the same-unit requirement is itself derivable, even though the unit is
not.** "Fraction of a trade's horizon" is a ratio of two lengths, so `g` and `H`
must be measured on **one clock**; a `g` in minutes against an `H` in bars is not a
fraction of anything. **`GAP_AND_HORIZON_MUST_BE_READ_ON_THE_SAME_CLOCK`.** This
does **not** choose the clock — MO-2 stays open — but it removes the mixed readings
from the option set, and it is why §8.4.4's candidates are candidates for *both*
quantities at once.

**One candidate it appears to eliminate, recorded rather than removed.** MO-2's
**event index** requires reading `H` in *events*; `H` is committed only as 24 M15
**bars**, so on its face D-ω-2a excludes it. It is left in MO-2's list because the
elimination is a consequence of a derivation still awaiting confirmation, and
because the direction matters: event index is the `ω`-**maximising** candidate
(`overlap ≡ 23/24`, `rho_h ≡ 23.04` under MO-1(b)), so removing it silently would
narrow the option set at the **conservative** end. §8.4.4's own objection to it —
that `ω` collapses to a constant — is a different one.

**D-ω-3 — the draft estimator is illustrative and superseded; it is not a competing
normative formulation. (Bears on MO-3 and MO-4.)** Determined from text rather than
assumed. Prereg §9 states that the effective-N **method** is
"**[FIXED-AT design audit or gate 3a]**", and labels its own formula "Draft
estimator (**for the design audit to fix**)" — i.e. the draft is expressly the
object *to be fixed*, and it names the event that fixes it. The epoch-adoption
record is that event: T-6, "**Effective-N estimator approved here**", and the
artifact carries `status: APPROVED_SPEC (T-6 requires the effective-N estimator to
be fixed at gate 3a)`. So the draft's status is **illustrative, superseded,
non-normative** — and, by §8.4.3, a different *object* as well.

**Two things this does and does not settle.** It **does** settle which text
governs where the two differ: the APPROVED spec. It does **not** retire
`DRAFT_AND_APPROVED_OVERLAP_FORMULATIONS_ARE_DIFFERENT_OBJECTS_AND_DIVERGE_INSIDE_THE_HORIZON`
— that item records *what the two objects are*, which stays true, and §8.4.3's
withdrawal of both the "12.5× at the ceiling" reading and the "they agree" reading
stands unaffected. A superseded draft is still evidence of what was intended; it is
simply not the operative rule.

**D-ω-4 — `E[f(gap)]`, not `f(E[gap])`. (MO-4.)** With the draft placed, the
governing wording is the spec's alone: "**mean fraction** of a trade's horizon that
overlaps the next same-pair trade's horizon, estimated per pair from the realised
inter-event **gaps**". A *fraction* is the per-event quantity of D-ω-2; a **mean
fraction** is the mean of that quantity; the plural "gaps" is the set it is taken
over. That is `ω = mean_i(overlap(g_i))` — **Option A**. `f(E[g])` requires reading
"mean fraction" as "fraction at the mean gap", which inverts the two words, and its
only textual support was the superseded draft.

**Which mean is *not* derived here.** D-ω-4 fixes the **order** of the transform and
the average — a claim that holds under any weights, since `Σ wᵢ f(gᵢ)` versus
`f(Σ wᵢ gᵢ)` is the same distinction whatever the `wᵢ` — and fixes **nothing** about
the weights themselves, which are **MO-1(c)** and MO-6's within-pair limb and stay
open. §8.4.5's third bullet records how large that residual is. The `0.213` cited
below is §0.3's **unweighted** value.

**Direction, stated because it is the reason this is not a detail.** `f` is convex,
so by Jensen `E[f(g)] ≥ f(E[g])` always: **Option B is the anti-conservative one**,
uniformly. §0.3's Poisson diagnostic at the frozen ceiling is `E[f(g)] = 0.213`
against `f(E[g]) = 0` — the whole of `rho_h = 5.90` versus none of it.
*`NON_NORMATIVE_DIAGNOSTIC_ONLY`.* And §0.4(a) already **withdrew** the mean-gap
argument on exactly this ground, so adopting Option B now would reinstate a
withdrawn claim.

**D-ω-5 — cross-pair aggregation is settled: `rho_h` is per pair. (MO-6,
across-pairs limb.)** Unchanged from MO-6 and restated here so the derivable set is
in one place. Its most direct authority is the spec's own sentence — `ω` is
"estimated **per pair** from the realised inter-event gaps" — which forecloses
pooling by itself; the spec then fixes `N_eff_pair = N_raw_pair / rho_h_pair` with
`granularity: [portfolio, per_pair]`, and the portfolio-scalar collapse is a
**recorded defect** (B-3) with an audited counter-example, not an option. **Pooling
all inter-event gaps across all twenty pairs into one `ω` is therefore foreclosed**
— it is the collapse in another spelling, and §8.4.11 records why it is also the
route with the largest quiet gain. What remains open is the **within-pair**
weighting, not this.

**So four of the nine are derivable** — MO-8, MO-3, MO-4 and MO-6's across-pairs
limb, with D-ω-2a removing the mixed-unit readings — and **five are genuine
choices**: MO-2 (the unit), MO-1's (b) and (c) limbs, MO-5, MO-6's within-pair and
per-role limbs, and MO-7.

#### 8.4.11 Adversarial properties — the routes a ruling must close by name

Each raises `N_eff` while obeying the letter of everything already committed. They
fall into **two kinds**, and an earlier draft of this sentence defined the class as
"ways to lower `ω`", which reaches only the first kind and misses the two largest.
Some **lower `ω` itself** — A-ω-2, A-ω-3, A-ω-4, A-ω-5, A-ω-7. Others leave **every
reported `ω` value unchanged** and move `N_eff` by re-pairing or sharing them —
A-ω-1, A-ω-6 — so **no check that inspects the reported overlap fractions can see
them**. They are recorded as **first-class properties**, not as accusations, and none
of the arithmetic below is normative.

**A-ω-1 — `PAIR_LABEL_ASSIGNMENT_MUST_NOT_BE_REARRANGED_TO_REDUCE_OMEGA`.** An
event belongs to the registered pair it occurred on; a pair's `ω` is computed from
**that pair's** gaps. Nothing committed enforces it — `canonical_pair` checks the
**label** — and §8.3.0 records the consequence: re-pairing counts against overlaps
across the twenty labels moves `N_eff` alone, by up to 20.9× on the audited shapes.
*The magnitude is a diagnostic and is not the authority; the property is.* This is
the `ω` face of `PER_RECORD_COUNT_PROVENANCE_UNBOUND` and of
`OVERLAP_PER_RECORD_PROVENANCE_UNBOUND`.

**A-ω-2 — `NO_ADJACENT_GAP_DOES_NOT_AUTOMATICALLY_MEAN_ZERO_OVERLAP`.** A pair with
no adjacent pair of events has **no gap**, and `ω = 0` is the reading that makes
`rho_h = 1` and costs nothing. It must be a **decision**, not a default reached by
the absence of an alternative. See MO-5 and §8.4.13 limb 7 — and note the
interaction §8.4.12 records with the NR-K ruling.

**A-ω-3 — `NO_TURNOVER_DERIVED_GAP_BOUND`.** `turnover()` is documented as
"**Portfolio-average trades per day**". A portfolio average over a span is not a
per-day cap, not a per-pair rate, and **not a lower bound on any individual gap**.
Three specific conversions are forbidden: `≤ 40/day` → a fixed gap; a mean turnover
→ every gap; a turnover ceiling → a minimum gap. §0.4(b) records why: a mean-only
constraint admits arbitrary clustering, right up to the supremum of `rho_h` at
exactly the frozen ceiling (see the refinement of that supremum at D-ω-1). **No
answer to MO-1…MO-8 may be derived from it.**

**A-ω-4 — `NO_CLIPPING_WITHOUT_COMMITTED_AUTHORITY`.** No cap, floor, clamp,
winsorisation or `0.5`-style ceiling may be applied to `g`, to `overlap_i` or to
`ω` unless committed text supplies it. **Two** bounds are committed: `ω ∈ [0, 1]`
(the spec's own definition, enforced by `_require_unit_fraction`) and
**non-overlapping events ⇒ `rho_h → 1`**. A third expression is not a bound at all:
D-ω-2's `max(0, ·)` is **interval arithmetic** — an intersection length cannot be
negative — but D-ω-2 is a **derivation offered for confirmation**, conditional on
MO-2 and MO-1(b), so it **may not be cited as committed authority until confirmed**.
An earlier draft of this bullet listed it as committed, which is the promotion this
very property exists to forbid.
Everything else is invention — and this packet has already had to withdraw one
clamp of its own (§8.4.3's `max(1, H/ḡ)`), which is why the prohibition is written
down rather than assumed.

**A-ω-5 — `OMEGA_METHOD_MUST_NOT_BE_SELECTED_AFTER_OBSERVING_GAP_STRUCTURE_ON_ANY_SPAN`.**
Because `ω` carries no span scope (§8.4.2), the method, the unit, the aggregation
weighting and the pair set could each be chosen after the fact, and the choice would
be **unfalsifiable** afterwards. This is the `ω` analogue of
`DURATION_SELECTION_MUST_BE_OUTCOME_BLIND` (§8.1.0) and of §8.3.0's non-reduction
clause, and it is what MO-7 must answer.

**Outcome-blindness as to the *judged* span is not sufficient, and the earlier token
said only that.** The DESIGN span is not the span `ω` judges, is fully informative
about gap structure, and carries no bar on `ω` at all — so a method chosen on DESIGN
gap structure and then applied to holdout obeys every word of the old token while
retaining the whole of the informativeness. The property must reach **any** span,
which is what §8.4.14 limb 6's "frozen before data" means; the token is renamed
accordingly and the old spelling is **superseded**.

**And a pre-data freeze does not by itself protect MO-2, because the favourable
direction is known in advance.** §8.2.0 already records it — an elapsed reading
"lengthens those gaps, lowers `rho_h` … and therefore **raises `N_eff` with no event
added and no threshold touched**". Structurally, for every consecutive pair of events
`g` measured on the continuous grid is **≥** `g` measured over bars that exist, with
equality only where no closed period intervenes, so under any non-increasing overlap
function the continuous-grid reading is **weakly `ω`-minimising for every dataset**.
A ruler who has seen no data at all can therefore still take the feasibility-favourable
end of MO-2. §8.4.4 records the *magnitude* of that lever but presents the candidates
symmetrically; the ordering being fixed in advance is recorded here. **Outcome-blindness
is necessary and not sufficient: MO-2 needs a reason, not merely a timestamp.**

**A-ω-8 — neither frozen floor can see any of this, which is why MO-7 is the only
enforcement point.** The raw ≥ 1,000 floor is `Σ raw_event_count` and contains no
`ω` at all. The ≤ 0.40 concentration cap is computed over the **traded** set and is
invariant under A-ω-1, since permuting counts across labels leaves the multiset and
hence the maximum share unchanged. So **neither floor detects A-ω-1, A-ω-2, A-ω-4,
A-ω-5, A-ω-6 or A-ω-7**. §8.3.0 makes the same point for the `P` lever ("with the raw
floor unable to see the change"); it holds here for every route above, and it is the
reason MO-7's producer and freeze point are the only place enforcement could live.

**A-ω-6 — the pooled route.** Pooling gaps across pairs (D-ω-5) is foreclosed by the
spec and by B-3, and it is worth naming *why* it would be attractive: pooling
replaces a per-pair `ω_p` with one portfolio `ω̄`, and §8.4's MO-6 records that a
shared `ω̄` in all twenty slots reproduces the pre-B-3 collapsed arithmetic exactly
(`Σ Nₚ/(1+23ω̄) = (Σ Nₚ)/(1+23ω̄)`). The rule is committed; the enforcement is not.

**A-ω-7 — `MEAN_OVERLAP_PAIR_SET_MUST_NOT_SHRINK`.** §8.3.0 fixed `P` at the frozen
registered twenty for `rho_x`. It ruled nothing about `ω`, so the same *motive*
exists one deflator over — **but the lever has a different shape, and an earlier
draft of this property named the wrong object.** `rho_h = 1 + (H − 1)·ω` carries
**no pair count** at all; `P` appears in `rho_x` and nowhere else, so there is no
cardinality in `rho_h` for a shrink to act on. And §8.4.12 records that a fixed
`P = 20` forces all twenty records to be present with an `overlap_fraction` on each,
which `_normalise_pairs` requires. So "computing `ω` over **active pairs only**,
**pairs with trades only**, or **the lowest-overlap pairs only**" cannot remove a
slot: it can only decide **what value fills the slot of a pair excluded from the
measurement**, which is **MO-5 together with `OVERLAP_PER_RECORD_PROVENANCE_UNBOUND`**.
The property a ruling must close is therefore *which pairs' realised gaps produce
which record's `overlap_fraction`, and what an excluded record carries* — **not** the
cardinality of a set. Recorded as a property for the ruling to close — **not**
asserted as already ruled, and §8.4.14 keeps it out of the derived set for exactly
that reason.

#### 8.4.12 Zero- and one-event pairs — and the collision with the NR-K ruling

MO-5's sharpest case is **not** the zero-event pair, and an earlier draft had this
the wrong way round.

**At zero events `ω` is arithmetically inert.** `N_eff_pair = N_raw_pair / rho_h_pair
= 0 / rho_h`, which is `0` for **every** admissible `rho_h ≥ 1`. Whatever `ω` is
supplied changes nothing in the numerator, and the raw total is unaffected.

**At one event it is not inert at all.** `N_eff_pair = 1 / (1 + 23ω)`, which runs
from `1.000` at `ω = 0` to `0.042` at `ω = 1` — a 24× range on that record. The same
holds, less starkly, for any small `n`: `ω` comes from `n − 1` gaps, and §8.4.5
records that the estimation bias runs **anti-conservative** because
`ω ↦ 1/(1 + 23ω)` is convex. *`NON_NORMATIVE_DIAGNOSTIC_ONLY`.*

**And there is a collision the ruling must not walk into.** §8.3.0 rules that a
registered pair which fires nothing is a **normal outcome, not a contract
violation**, and §8.3.0 fixes `P` at twenty — so all twenty records must be present,
including zero-event ones, and each must carry an `overlap_fraction`, which
`_require_unit_fraction` requires to be a number. A flatly fail-closed reading of
MO-5 — "no adjacent gap ⇒ `ω` undefined ⇒ refuse" — would therefore **halt the
family on a normal outcome**, which is precisely what §8.3.0's carve-out exists to
prevent. **`ZERO_EVENT_OMEGA_MUST_NOT_HALT_A_NORMAL_OUTCOME`.**

The two properties are compatible, and the packet says how without ruling it: the
inert case (zero events) and the load-bearing case (one or few events) can be
disposed of **differently**, because they differ arithmetically. A-ω-2 bites on the
second; the first needs a value that is recorded as **conventional and inert** rather
than measured. Which convention, and whether the one-event case is refused, deferred
or given a stated value, is **MO-5 and is not decided here**.

**Three qualifications this needs, and the last is uncomfortable.**

- **The twenty-slot obligation runs through the current signature.** `effective_n()`
  derives `n_pairs = len(records)` and takes no separate `P`, so `P = 20` implies
  twenty records implies twenty `overlap_fraction` values. `P_AUTHORITY_RULED_IMPLEMENTATION_COMPLETENESS_PIN_PENDING`
  (§8.3.0) means the pin has **not landed**: `effective_n()` still accepts `P = 1`,
  so today the cheapest evasion of a zero-event pair's `ω` is not any convention but
  **omitting the record**, which no code prevents. An estimator taking `P` separately
  would dissolve the collision entirely. The collision is real under the committed
  signature; it is not unavoidable in principle.
- **The one-event lever is bounded, and saying so helps the ruling.** A one-event
  record contributes at most `1.000` and at least `1/23.04 = 0.043`, so each such
  pair is worth **≤ 0.957** units of `Σ N_eff_pair`. With `k ≤ 19` such pairs the whole
  lever is `≤ 0.957k / rho_x` — **≤ 18.2 units of `N_eff`, about 4.5% of the 400 floor
  at `c = 0` and 0.7% at the diagnostic `c = 0.3`**. *`NON_NORMATIVE_DIAGNOSTIC_ONLY`.*
  That cuts **for** a strict disposition: refusing or deferring the one-event case
  costs almost nothing, which strengthens A-ω-2 rather than weakening it.
- **MO-6's denominator limb can decide MO-5's one-event limb by accident.** In a pair
  with `n` events there are `n − 1` gaps. Dividing `n − 1` overlap terms by `n` —
  equivalently letting the last event contribute a zero term, a reading MO-5 itself
  offers — multiplies `ω` by `(n−1)/n`, which the raw floor keeps above 0.98 wherever
  the budget binds. But **at `n = 1` it yields `ω = 0/1 = 0` automatically**, answering
  the one-event limb without ever confronting A-ω-2. The two limbs are listed
  separately and the ruling should not settle the second by settling the first.

**And the split's own basis is worth naming rather than assumed.** It is principled
**on arithmetic** — at `n = 0` the value provably cannot move anything. But the two
cases are **evidentially identical**: neither pair has observed a single gap. So the
rule "the convention may be chosen freely where it has no effect, and must be decided
where it does" is, at exactly one event, the same criterion as *choosing a convention
by its effect* — the shape A-ω-5 exists to forbid. **Whether the arithmetic effect or
the evidential state governs is part of MO-5, and this packet does not choose.**

#### 8.4.13 The options — HISTORICAL, superseded by the ruling

Retained as the material the ruling was taken on. **Option A is what Rulings ω-1,
ω-2, ω-4, ω-7 and ω-8 adopt** (with the clock ruled rather than recommended).
**Option B is refused by name** under Ruling ω-3, which is why it was kept in the
list. Option C was recorded as empty and remains so; Option D was not taken.

Stated for the limbs that were choices when this was written. §8.4.10's four derivations are **not**
re-offered as open options — offering a derived limb as a choice is itself a way of
reopening it. **Option B is the single exception**, and is listed as the derivation's
*negation* so the ruling can refuse it by name rather than by omission, not as a live
alternative.

**Option A — realised event-level overlap mean.** Same pair; deterministic event
ordering (D-ω-1); one clock for `g` and `H` (D-ω-2a); the interval-arithmetic
fraction (D-ω-2); transform each event, then average (D-ω-4); per-pair `rho_h`
(D-ω-5). *For:* it is what the APPROVED spec's own words describe, and every step is
sourced. *Against:* it needs MO-2's clock chosen, and it inherits MO-5, MO-6's
within-pair weighting and MO-7.

**Option B — mean-gap approximation.** `ω = overlap(mean gap)`. *For:* simpler, and
it is what the superseded draft's shape suggests. *Against:* it is the
**anti-conservative** side of Jensen at every gap distribution (D-ω-4), it discards
the dispersion that overlap is *about*, its only textual support is a superseded
illustrative formula (D-ω-3), and §0.4(a) already withdrew the argument that rests
on it. **This packet does not recommend it and records it so the ruling can refuse
it explicitly rather than by omission.**

**Option C — a conservative structural bound.** Only admissible if committed text
supplies one. **None was found**: no committed source supplies a lower bound on
`ω`, an upper bound below 1, or a structural substitute. Recorded as **empty**,
not as available.

**Option D — another committed formulation.** Held open for the ruling. This packet
searched and found the APPROVED spec and the superseded draft, and nothing else.

#### 8.4.14 The recommendation that was offered — and what the ruling did with it

**Adopted in substance, on all seven limbs, and hardened on three.** The ruling takes
limb 1's *recommended* half — the bar clock — and makes it **ruled**, and further ties
it to the horizon's own clock rather than merely to "an M15 bar clock" (Ruling ω-1);
it turns limb 4's enforcement half and limb 5's analogy into **explicit prohibitions**
(Rulings ω-8 and ω-5/ω-6, without extending NR-K); and it converts limb 7's "decided,
not defaulted" into a **stated value with a stated ground** (Ruling ω-6). Limbs 2, 3
and 6 are adopted as they stand.

The table below is the recommendation **as it was offered**, retained as the record of
what was put to the ruling. **Only the limbs marked *derived* carried authority then;
the rest were preferences.** For what carries authority **now**, see §8.4.0's own
derived-versus-chosen table.

| # | Limb | Backing |
| --- | --- | --- |
| 1 | `g` and `H` read on **one clock**, and that clock an **M15 bar** clock (*which* bar sequence is MO-2's and stays open) | **`GAP_AND_HORIZON_MUST_BE_READ_ON_THE_SAME_CLOCK` is derived** (D-ω-2a); *that the clock is bars* is **recommended, not derived** — the pull is real (events are bar-identified per D-ω-1; `warmup.py` counts by `bar_index`; §8.2.2 *reads* the contract as denominating model mechanics in bars, which is this document's distillation and **not** committed text) but no committed source rules it, and **which** bar sequence remains open (§8.4.4). An earlier version of this cell named an "M15 prediction clock" — a term that occurs nowhere in the repository outside it, and therefore a coined unit this packet may not introduce; **withdrawn** |
| 2 | Overlap computed **per adjacent event interval**, by interval arithmetic | **Derived *given* limb 1's recommended half** (D-ω-2) — also conditional on MO-1(b), and on `H` being a **constant contiguous** length on the chosen clock, which is limb 1's open half. Not derived independently of limb 1 |
| 3 | Average the **event-level overlaps**, never transform the average gap | **Derived** (D-ω-3 + D-ω-4) |
| 4 | Preserve **registered pair identity**; an event's gaps belong to its own pair | **Rule derived, enforcement not committed.** The rule is the same spec sentence D-ω-5 rests on — `ω` is "estimated **per pair** from the realised inter-event gaps". What is uncommitted is its **enforcement**: `OVERLAP_PER_RECORD_PROVENANCE_UNBOUND` / A-ω-1, which is the half that stays recommended |
| 5 | **No post-hoc pair dropping** on the `ω` side | **Recommended by analogy, and expressly not derived.** §8.3.0 ruled the *`rho_x`* pair set; extending it to `ω` is the natural reading of the same principle but is **not** what was ruled (A-ω-7) |
| 6 | Formula, unit and aggregation weighting **frozen before data**; only the value computed afterwards | **Recommended** — A-ω-5; `ω` has no committed span scope, and `c`'s "DESIGN span only … frozen once and recorded" is the nearest committed analogue, not an authority over `ω` |
| 7 | The no-adjacent-gap case **decided, not defaulted to `ω = 0`** | **Recommended** — A-ω-2, and **scoped by §8.4.12**: it must not become a halt on a zero-event pair, which §8.3.0 rules a normal outcome |

**What limb 6 means and does not mean.** It fixes the *method* before the data and
lets the *value* be computed mechanically from the registered event sequence of
whichever role span the ruling names. It does **not** choose that role span: whether
`ω` comes from DESIGN only (as `c` does), from each role separately, or from the
span being judged, is MO-7, and **no committed source answers it**. This packet does
not supply one.

**Is a contract amendment required?** For limbs 2 and 3 — **no**: they restate the
APPROVED spec's own words, and the text they displace is expressly a draft "for the
design audit to fix". For limb 1's derived half — **no**, for the same reason.
**And one branch of a question, not of the recommendation, is an amendment branch:**
MO-1(b) invites the ruling to "confirm or vary" the spec's own explicit words, "the
**next same-pair trade's** horizon". *Varying* committed spec text falls under the
same unsettled classification as the limbs below. For limbs 1-bars, 4-enforcement,
5, 6 and 7 — **not determinable here**, on the same ground
§8.3.0 recorded for NR-K: they add requirements the spec does not carry, and
**no general contract-amendment procedure is registered anywhere in this
repository** (`NO_GENERAL_CONTRACT_AMENDMENT_PROCEDURE_REGISTERED`, this packet's
own token for that absence). **`MEAN_OVERLAP_AMENDMENT_CLASSIFICATION_NOT_SETTLED`.**

#### 8.4.15 Status, and the handoff — status HISTORICAL, handoff live

**The status paragraphs below are superseded by §8.4.0.**
`MEAN_OVERLAP_PENDING_HUMAN_CHATGPT_RULING` and
`MEAN_OVERLAP_CORE_DERIVED_READY_FOR_REVIEW` are historical; the operative status is
`MEAN_OVERLAP_RULED_EVENT_LEVEL_SAME_HORIZON_CLOCK_EQUAL_WEIGHT_ROLE_LOCAL`. The
**carried-open list and the NR-L handoff below remain live**, less the items §8.4.0
discharges — the unit, the transform order, the weighting, the zero/one-event
semantics and the freeze point are ruled; the horizon-extent residual, the calendar
dependency, the provenance gap and the amendment classification are not.

**`MEAN_OVERLAP_PENDING_HUMAN_CHATGPT_RULING`** — because five of the nine objects
are genuine choices no committed source **settles**: the **unit** (MO-2), MO-1's
next-event and unweighted limbs, **zero/one-event** semantics (MO-5), **within-pair
weighting and role separation** (MO-6), and the **measurement source and freeze
point** (MO-7). An AI may not settle any of them, and this packet invents no
statistical formula.

**One partial exception, and it is a derivation rather than a choice.**
`ZERO_EVENT_OMEGA_MUST_NOT_HALT_A_NORMAL_OUTCOME` (§8.4.12) follows from §8.3.0's
**recorded ruling**, and it removes the flatly fail-closed answer to MO-5's
**zero-event** limb from the option set. It is offered for confirmation on the same
footing as §8.4.10's four. Everything else in MO-5 — the convention itself, and the
whole of the **one-event** limb — remains open. Recorded because a removal of a
fail-closed option runs in the `ω`-permissive direction and must not pass as a
by-product.

**`MEAN_OVERLAP_CORE_DERIVED_READY_FOR_REVIEW`** — for the four that are derivable
and are offered for confirmation rather than choice: **MO-8** event ordering
(D-ω-1); **MO-3** the overlap function (D-ω-2 — conditional on **three** things, all
of which are in the pending list above: MO-2's clock, **MO-1(b)'s next-event
restriction**, and `H` being a **constant contiguous** length on that clock);
**MO-4** `E[f(gap)]` over `f(E[gap])` (D-ω-3 + D-ω-4, which fixes the **order** of
the transform and the average and **not** the weights); and **MO-6's across-pairs
limb** (D-ω-5). Plus `GAP_AND_HORIZON_MUST_BE_READ_ON_THE_SAME_CLOCK` (D-ω-2a).

**And what the four derivations do *not* buy, stated because the count invites the
opposite reading.** They settle the **shape** of the arithmetic; they narrow the
reachable range of `rho_h` **scarcely at all**, which the five open limbs still span
in full — the weighting limb alone reaches `[1.00, 23.04]` with all four confirmed
and the gap sequence fixed (§8.4.5), MO-2 moves a single contribution from `0` to
near `1` in a direction known in advance (A-ω-5), and A-ω-1/A-ω-6 move `N_eff` by up
to 20.9× with **every reported `ω` unchanged**. "Four of nine derived" is a count of
**objects**, not progress on the deflator's range, and must not be read as the
latter.

**Carried open, and named:** `MEAN_OVERLAP_FRACTION_UNIT_NOT_REGISTERED` ·
`MEAN_OVERLAP_CLOCK_DEPENDS_ON_APPROVED_CALENDAR_AUTHORITY` — **now realised**:
Ruling ω-11 picks a calendar-dependent substrate, the **approved-calendar eligible
M15 slot sequence**, which is a *seventh* candidate and none of the three this token
originally enumerated. *An earlier version listed only "bars that exist", "complete
buckets only" and "elapsed time excluding closed periods", so it would not have fired
on the substrate the ruling actually chose — the same defect this token had once
before, corrected again.* If the ruling picks any calendar-dependent candidate, then `ω` acquires
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` as a dependency (§8.4.4); the
continuous-grid, elapsed-**including**-closures and event-index candidates do not
carry it, and an earlier version of this token said only "a bar sequence", which
would not have fired on the third · `OVERLAP_PER_RECORD_PROVENANCE_UNBOUND` ·
`PER_RECORD_COUNT_PROVENANCE_UNBOUND` · `MEAN_OVERLAP_PAIR_SET_MUST_NOT_SHRINK` ·
`ZERO_EVENT_OMEGA_MUST_NOT_HALT_A_NORMAL_OUTCOME` ·
`MEAN_OVERLAP_AMENDMENT_CLASSIFICATION_NOT_SETTLED` ·
`HORIZON_WALL_CLOCK_EXTENT_NOT_REGISTERED` ·
`DRAFT_AND_APPROVED_OVERLAP_FORMULATIONS_ARE_DIFFERENT_OBJECTS_AND_DIVERGE_INSIDE_THE_HORIZON`
— which D-ω-3 expressly does **not** retire · `Q10_A_DOES_NOT_RULE_THE_GAP_UNIT` ·
`NOTHING_PREVENTS_OVERLAP_BEING_MEASURED_ON_THE_SPAN_IT_JUDGES_WHILE_CORRELATION_IS_FROZEN_ON_DESIGN` ·
`OMEGA_METHOD_MUST_NOT_BE_SELECTED_AFTER_OBSERVING_GAP_STRUCTURE_ON_ANY_SPAN`.

**One adjacent gap, recorded and not filled.** D-ω-2's equal-length premise also
assumes no event's horizon is cut short by the **end of its role span**. The only
positional implementation, `scripts/ml_step4/labels.py`, *excludes* such bars rather
than truncating them — but that is unadopted M1-lineage code (prereg §11, "after
audit/wrapping"), and nothing in `scripts/m15_gate3a/` carries a rule. At the small-`n`
regime §8.4.12 shows is decisive, one truncated horizon is not negligible. It sits
beside MO-5's last-event limb; **no rule is proposed here**.

**Handoff — NR-L was next, and is now ruled; this packet touched none of it.** After
the mean-overlap ruling, NR-L decided the correlation's **pair set**, **statistic**,
**series**, **day attribution**, **idle days**, **undefined pairwise cases**, the
**source span and freeze point** (NR-L1…NR-L7) and **common date alignment** (NR-L8)
— §8.5.0, bundled with Q10(i) — together with
`P_AND_CORRELATION_INDEX_SET_NOT_BOUND` and
`OUTCOME_DRIVEN_CORRELATION_SET_IS_THE_SAME_LEVER_IN_THE_OTHER_FACTOR`, both assigned
to it at §8.3.0 and both **closed** by Ruling c-1. Nothing in §8.4 may be cited into NR-L: `ω` and `c` sit in
**different deflators**, and the fact that `c` is span-scoped while `ω` is not is
recorded here as an *asymmetry*, never as a rule for either.

### 8.5 NR-L — RULED. The cross-pair correlation `c`, bundled with Q10(i)

**`NR_L_MINIMUM_RESEARCH_CONTRACT_RULED_PENDING_IMPLEMENTATION_AND_DESIGN_MEASUREMENT`**
· **`Q10_I_RULED_REALIZED_PNL_ATTRIBUTED_TO_EXIT_UTC_DATE`** ·
`MUST_RESOLVE_BEFORE_ANY_EFFECTIVE_N_VERDICT` (satisfied as to the **contract**;
the **value** is still unmeasured).

**Status change.** `NR_L_REQUIRES_HUMAN_CHATGPT_RULING` and
`NR_L_PARTIALLY_DERIVED_BLOCKED_BY_Q10_I_AND_HUMAN_RULINGS` are **HISTORICAL —
SUPERSEDED BY HUMAN + CHATGPT RULING** (§8.5.0). §8.5.1–§8.5.11 are the material the
ruling was taken on and are retained as supporting record, superseded wherever they
say a limb is open; **§8.5.10 is a recommendation the ruling replaces** and may not be
cited as authority. With `P` ruled (§8.3.0) and `ω`'s method ruled (§8.4.0),
`rho_x = 1 + 19c` for current Family A, so **`c` alone carries the whole cross-pair
deflator**.

**It is not the last freedom in the effective-N arithmetic, and an earlier drafting
said so — withdrawn.** §0.3 withdrew "the last unpinned term" once already, in the
other variable, and the same correction applies here:
`ROLLOVER_AND_HOLIDAY_SLOT_ELIGIBILITY_RELATIVE_TO_THE_OMEGA_CLOCK_NOT_SETTLED` still
moves a single overlap contribution across `ω`'s whole domain — the `0`-to-near-`1`
width §8.4.4 illustrates, now sitting **inside** the ruled substrate rather than
between two candidate substrates (§8.4.0) — and `OVERLAP_PER_RECORD_PROVENANCE_UNBOUND`
still moves `N_eff` by up to 20.9× **with every reported `ω` unchanged**. `c` is the last
unruled **decision packet**, which is a different statement.

**Scope.** **Eight** questions. NR-L1…NR-L7 keep the identifiers they were committed
under — the **pair set**, the **statistic**, the **input series**, **day
attribution**, **idle days**, **undefined pairwise cases**, and the **source span and
freeze point** — and **NR-L8**, **common date alignment**, is added, because NR-L5 and
NR-L6 are both under-determined without it. Expressly outside it: `P` and the pair
universe (ruled), `ω` (ruled), Q10(i)/(iii), the exact `D`, `T_v`/`T_h`, Q1, Q8,
FR-19, and implementation detail. **No real data, no empirical correlation, no
measurement of any kind.**

#### 8.5.0 The bundled ruling — Q10(i) and NR-L, as recorded

A ruling received from human + ChatGPT and recorded here as **authority**. It closes
**Q10(i)** and all eight NR-L limbs in **one** decision, because they are not
separable: `c` is defined on per-pair **daily** PnL, and a daily series does not exist
until a trade whose horizon crosses a UTC midnight has a defined attribution day.

**`Q10_I_RULED_REALIZED_PNL_ATTRIBUTED_TO_EXIT_UTC_DATE`** ·
**`NR_L_MINIMUM_RESEARCH_CONTRACT_RULED_PENDING_IMPLEMENTATION_AND_DESIGN_MEASUREMENT`**

**What is *not* ruled here**, stated first because a bundled ruling is where scope
creep hides: **no empirical `c`, no correlation matrix, no daily PnL and no `N_eff`
is calculated**; no data is read; **Q10(iii)** (annualisation) is untouched and is not
forced by anything below; no `T_v`, `T_h` or `D` value is chosen; Q1, Q3, Q8, Q9 and
FR-19 are unchanged; §0's verdict is unchanged; and `ω`, its arithmetic, its clock and
its calendar semantics are **not reopened**.

##### The committed authority, re-read at source for this ruling

Nothing below is taken from an earlier summary. Each row was re-read on `origin/master`
at `2a25279`.

| What committed text actually says | Where |
| --- | --- |
| `rho_x = 1 + (P - 1) * mean_abs_pairwise_corr`, and `mean_abs_pairwise_corr` = "mean **absolute** pairwise correlation of per-pair **daily PnL** series, estimated on **DESIGN data only** and **frozen**. Independent pairs => `rho_x -> 1`" | `artifacts/m15_gate3a/effective_n_estimator_spec.json`, `definitions.cross_pair_discount` (`APPROVED_SPEC`) |
| "**DESIGN span only (2025-04-25..2026-02-28); never validation/holdout; frozen once and recorded.**" | same artifact, `correlation_estimation_data` |
| "Daily portfolio Sharpe is computed on **UTC-day portfolio sums**; days are treated as the Sharpe sampling unit but are **correlated across pairs**. **`rho_x` captures the cross-pair term**" | same artifact, `daily_aggregation_dependence_note` |
| `no_strategy_metrics_computed_at_gate3a: true` — in the **same** artifact that defines `c` on daily PnL | same artifact |
| The design-span boundaries are committed constants, not prose: `DESIGN_START = 2025-04-25 00:00:00+00:00`, `DESIGN_END = 2026-02-28 23:59:59+00:00` | `scripts/m15_gate3a/no_overlap.py:38-39` |
| `cross_pair_corr` is validated only as "a finite number in `[0, 1]`" — **no pair-set identity, no date index and no day rule is attached in the call or in the returned record** | `scripts/m15_gate3a/effective_n.py` `_require_unit_fraction` (118-130), `effective_n()` (220-345) |
| `P` is `n_pairs = len(records)`, bounded **above** by the frozen twenty and **not below** | `scripts/m15_gate3a/effective_n.py:280-282` |
| "discount cross-pair by an average-correlation factor estimated on design data" — expressly inside "**Draft estimator (for the design audit to fix)**" | prereg §9 |
| "Sharpe is computed on UTC-day portfolio sums (**as in M1**), acknowledged as correlated across pairs" | prereg §9, the daily-aggregation sentence |
| Metric helpers are "**Reusable after audit/wrapping** … metric helpers (extended per C-5)" — not adopted authority | prereg §11 |
| `TRADING_DAY_DEFINITION = "utc_calendar_date"`; `DAILY_COVERAGE_DENOMINATOR = "distinct_utc_calendar_dates_in_holdout"`; `PRIMARY_COST_CELL_PIPS = 0.5` | `scripts/ml_step4/contract.py:86, 101-102` |
| `MetricTrade.day: str  # UTC calendar day 'YYYY-MM-DD'` — **entry or exit is not stated**; `net_pnl = gross_pnl_pips - cell_pips` with the spread "embedded once" already in `gross_pnl_pips` | `scripts/ml_step4/metrics.py:29-40` |
| `daily_portfolio_pnl` sums net per-trade PnL by UTC day **across all pairs** into one series, and **emits only days that carry a trade** | `scripts/ml_step4/metrics.py:42-48` |
| The accepted-trade record carries **both** markers — `{"pair", "entry", "exit", "direction", "pnl_pips"}` — and `TradeSignal` validates `exit_ > entry` | `scripts/ml_step4/simulator.py:25-38, 75-83` |
| The repository's **only two** `MetricTrade` constructors both take the **entry** marker | `scripts/ml_step4/body.py:118, 406` |
| **No correlation is computed anywhere in the M15 packages.** Every `.corr` / `corrcoef` / `pearsonr` / `spearmanr` call sits in C-8-fenced stage/compare lineage | repo-wide grep |
| The one pairwise-correlation precedent that exists does **all four** of the forbidden things at once: pairwise finite-mask intersection, `< 5` shared observations → `0.0`, zero variance → `0.0`, non-finite → `0.0`, on "**per-bar mean gross PnL**" | `scripts/compare_multipair_v13_ensemble.py:1255-1269` and its v14/v15/v16/v19 siblings |
| A **merged** contract Gate-decision already names the harm: "A degenerate design set makes the per-pair daily-PnL series length-1, the correlation undefined, and **every degenerate resolution drives ρ_x → 1** … at P = 20 that removes the entire cross-pair discount … so a missing coverage criterion can **disarm `INSUFFICIENT_SAMPLE`**" | `docs/design/m15_d58_and_section1225_contract_gate_decision.md:369-379` |
| No settlement or realisation timestamp is defined anywhere in `scripts/ml_step4/` or `scripts/m15_gate3a/` | repo-wide grep |

**`NO_SETTLEMENT_TIMESTAMP_IS_DEFINED_ANYWHERE`** — so Q10(i)'s option C is not
available to be chosen; the exit **marker** is the only realisation instant the
contract carries.

##### Ruling Q10-i — realised PnL is attributed to the exit UTC date

**`Q10_I_RULED_REALIZED_PNL_ATTRIBUTED_TO_EXIT_UTC_DATE`.**

The **entire** realised PnL of a trade is attributed to the UTC calendar date
containing that trade's registered **exit** marker. **No split across dates, no
mark-to-market allocation over intervening days, and no entry-day back-attribution**,
unless a committed authority explicitly requires otherwise for a named metric.

**Committed authority does not decide this, and the ruling says exactly why.** Ruling
Q10(ii) fixes what a day *is* — the UTC calendar date — and
`TRADING_DAY_DEFINITION = "utc_calendar_date"` agrees; neither says **which** day a
straddling trade belongs to. The one candidate that could reach further is prereg §9's
"(as in M1)", and it does not: the parenthetical modifies "**Sharpe is computed on
UTC-day portfolio sums**", inside a sentence whose subject is *dependence across
pairs*; it carries the **aggregation shape**, not the attribution rule. The load-bearing argument is that grammatical one.
Prereg §11's classification of those metric helpers as reusable **"after
audit/wrapping"** and of all M1 flagship evidence as **historical-only** is
**corroboration, not proof**: "after audit/wrapping" *contemplates* reuse, and a
wrapped helper could preserve M1 semantics, so §11 does not on its face contradict a
semantic carry-over — it treats the helpers as material to be audited rather than as
adopted authority. *An earlier drafting presented §11 as defeating the wholesale
reading outright; that overstated it.* **The whole of this is a contract reading, not
a source fact, and it is labelled as one.**

**The precedent runs the other way, and it is recorded rather than buried.** Both
`MetricTrade` constructors that exist take the **entry** marker. They are unadopted
M1-lineage code, so they are a **precedent and not an authority** — but a ruling for
the exit day **departs from every constructor in the repository**, and that is stated
plainly rather than left for a reader to discover.

**Why the exit date, on research-integrity grounds.** A trade's PnL is not known at
entry; attributing it to the entry date books an outcome to a day before that outcome
exists. Exit-date attribution is the reading under which each daily figure is the PnL
**realised** on that date, which is what makes a *daily* correlation a statement about
co-movement of realised outcomes rather than about co-timing of decisions. It also
keeps an open position from contaminating a day whose result is not yet determined.

**The magnitude is bounded in bars, and only in bars.** The frozen horizon is 24 M15
bars, so an exit is at most 24 registered M15 slots after its decision bar. Converting
that to wall-clock is **not available to this document**:
`HORIZON_WALL_CLOCK_EXTENT_NOT_REGISTERED` survives outside `ω`, and §8.4.9's own
derivation already concludes from it and from prereg §4's "**no synthetic bars across
market close**" that a horizon **need not be contiguous** — so a decision bar near a
closure has its exit bar on the far side of that closure and may cross **more than
one** UTC midnight. *An earlier drafting said "24 M15 bars — six hours — so no trade
can straddle two"; that is the very wall-clock conversion this document refuses
elsewhere, and it is **withdrawn**.*
**`Q10_I_STRADDLE_EXTENT_IS_BOUNDED_IN_BARS_NOT_IN_CALENDAR_DATES`** ·
**`NON_NORMATIVE_DIAGNOSTIC_ONLY`**; no share of straddling trades is estimated,
because that would require data.

**No *unconditional* analytic favourable direction is established either way**, which
is what distinguishes this limb from `c`'s absolute-value placement below: nothing
makes entry or exit the `N_eff`-favourable arm for **every** dataset, where
`mean|ρ| ≥ |mean ρ|` holds with no data at all.
**`Q10_I_HAS_NO_UNCONDITIONALLY_KNOWABLE_FAVOURABLE_DIRECTION`** — named as a **search
that came back empty**, not as a proof that no such direction exists.

**One *conditional* direction is recorded rather than denied, on the same standard c-7
is held to.** Entries sit on one shared registered decision grid, so they cluster
across pairs; exits are TP/SL/timeout, and only the timeout arm preserves that
clustering as a fixed 24-bar shift while barrier exits disperse it. Exit-date sets are
therefore weakly **more dispersed** across pairs than entry-date sets, which weakly
lowers co-occurrence, `|r|`, `c` and `rho_x` and weakly **raises `N_eff`** — the
anti-conservative direction. It is conditional and unquantified, and no share is
estimated because that would require data; but by §8.4.11's A-ω-5 standard *"chosen
before the data"* is **not a complete defence** for it, and it is **carried, not
discharged**. **`Q10_I_EXIT_DISPERSION_MAY_WEAKLY_DILUTE_C`.**

##### What Q10-i reaches, and what it does not

`MetricTrade.day` is a **single field with three direct readers** —
`daily_portfolio_pnl`, `daily_coverage`, and `compute_all`'s `n_days` — and through
them **seven** quantities, so this ruling is confined neither to `c` nor to holdout
acceptance. Re-read at source, it reaches:

| Consumer | How the day rule enters | Frozen threshold |
| --- | --- | --- |
| `c` / `rho_x` | the per-pair daily series this ruling's NR-L limbs build | `N_eff >= 400` |
| daily portfolio Sharpe | `daily_portfolio_pnl` buckets by `t.day` | `>= 0.8` |
| max equity drawdown | same series | `<= 0.15` |
| daily coverage | `days = {t.day for t in trades}` — the **numerator** | `>= 0.60` |
| turnover | `n_days = len({t.day for t in trades})` — the **denominator** | `<= 40 trades/day` — **but see the guard below** |
| **the validation daily Sharpe** | `body.py:228` and `:535` build the **validation** series the same way and feed `select_threshold` | none of its own — **it selects the operating point carried to the holdout** |
| **the validation turnover figure** | the same `n_days`, inside prereg §9.V's kill-gate clause "**within the turnover budget**" | the budget, at the gate that decides **whether the holdout is consumed at all** |

`cost_sensitivity` re-derives the daily Sharpe at each of the three cost cells off the
**same** `daily_portfolio_pnl` series, so it moves too; it carries no frozen threshold
of its own, because the stressed-cost acceptance row is denominated in **expectancy**,
which is day-independent.

**The validation side is named because it is the part that reaches beyond
measurement.** Prereg §8's committed selection metric is "validation net expectancy
**subject to the turnover budget**" — expectancy is day-independent, the turnover
budget is not — and the committed implementation selects on the **validation daily
Sharpe**, which is day-dependent outright. Prereg §9.V's kill gate is evaluated
"within the turnover budget", and failing at every registered `ev_min` point means
"**family A closed, no holdout consumed**". So Q10-i can change **which operating
point reaches the holdout** and **whether the holdout is reached**. That engages
`MEASUREMENT_MAY_DETERMINE_THE_VERDICT_BUT_MUST_NOT_REDIRECT_THE_EXPERIMENT`, and it
is discharged only by the pre-data freeze together with
`Q10_I_MUST_NOT_BE_RESELECTED_AFTER_OBSERVING_ANY_METRIC_IT_MOVES` — **which therefore
binds validation observations too, not only the four holdout rows**.
**`Q10_I_REACHES_OPERATING_POINT_SELECTION_AND_THE_VALIDATION_KILL_GATE`.**

**So the ruling changes measured values under four frozen holdout acceptance rows and
two validation-side quantities, and it loosens none of them.** Ruling 10 bars
*loosening a threshold*; no threshold is touched here. What is fixed is a **measurement convention**, and it is fixed **before**
any of those quantities is observed, outcome-blind, exactly as `D` and `ω`'s method
are. **`Q10_I_IS_A_MEASUREMENT_CONVENTION_NOT_A_THRESHOLD_CHANGE`** ·
**`Q10_I_MUST_NOT_BE_RESELECTED_AFTER_OBSERVING_ANY_METRIC_IT_MOVES`.**

**And the test §8.2.0 applied to the same manoeuvre is *not* met here, which is stated
rather than skipped.** When Ruling Q10(ii) moved a frozen row's measured value by
fixing its denominator, it did not stop at "no threshold is touched" — it
**established the direction** and showed the move was a *tightening*, which is what
Ruling 10 permits. No direction is establishable for Q10-i, so this ruling rests on
the **weaker** ground of outcome-blindness plus a pre-data freeze. That is a real
difference from §8.2.0's footing and is recorded as one.
**`Q10_I_RESTS_ON_OUTCOME_BLINDNESS_NOT_ON_A_SHOWN_TIGHTENING`.**

**What it does not reach.** The day **identity** (Q10(ii), unchanged); the coverage
**denominator**, which **Ruling Q10(ii)** fixed as *the set of UTC calendar dates the
approved calendar authority recognises as carrying at least one expected M15 slot*
(§8.2.0 — **not** the ml_step4 constant string
`distinct_utc_calendar_dates_in_holdout`, and citing that string here would silently
displace a ruled limb), and which is a property of the **window**, not of any trade —
both committed implementations build it from bar timestamps, never from trades; `D`,
which is an elapsed UTC span; `ω`'s event timestamps and eligible-slot sequence,
which are a different clock on a different substrate; and the annualisation factor
(Q10(iii), untouched).

**And it must not be read onto the turnover *ceiling's* day.** Q10-i moves the
**measured** `n_days` the implementation computes from `MetricTrade.day`. It does
**not** define the "day" of the `≤ 40 trades/day` ceiling, which Ruling Q10(ii)
expressly leaves "a §9 FROZEN row with an undefined day … **not ruled here**", warning
that reading it in calendar days would widen gate 4's corridor by ~42% — "a loosening
Ruling 10 forbids, and one that **citing this ruling must not achieve**". **Q10-i does
not rule it either, and may not be cited as ruling it.**
**`Q10_I_DOES_NOT_DEFINE_THE_TURNOVER_CEILING_DAY`.**

##### The implementation consequence, stated because it is real

Exit-day attribution is constructible from data the record **already carries** — the
accepted-trade record carries `"exit"` and `TradeSignal` validates `exit_ > entry` —
but it is **not** a one-marker change at both call sites, and saying so understates
the implementing PR. `_trades_from_accepted` (`body.py:116-118`) indexes the bars list
and **is** a one-marker change; the label machinery's eligibility rule
(`labels.py:214`, with `exit_window_offset` capped at `horizon - 1`) keeps the exit
index in range. `_trades_with_days` (`body.py:403-407`) is **not**: it reads
`day_by_index[pair][…]`, a dict populated **only** at label-eligible validation and
holdout decision-bar indices (`body.py:486-501`), so an exit index landing in the
purge or embargo gap, or in the trailing label-ineligible tail, raises `KeyError`.
Populating that map for exit indices is **new machinery on a protected path**.
**`EXIT_DAY_ATTRIBUTION_REQUIRES_A_NEW_DAY_MAP_AT_THE_SECOND_CALL_SITE`** —
implementation and checkability, and **this doc-only PR changes no source.**
*An earlier drafting said "no new machinery … a one-marker change at two call sites";
that is withdrawn as false at the second site.*

But one **committed test fixture** would fail under it:
`tests/ml_step4/test_b1_b2_fixes.py::test_b1_validation_and_holdout_charge_identically`
passes a one-element bars list with `{"entry": 0, "exit": 4}`, so indexing the exit
marker raises `IndexError`. The test's *subject* is cost charging, not day attribution
— it pins entry indexing only incidentally — but it would break.
**`EXIT_DAY_ATTRIBUTION_BREAKS_ONE_COMMITTED_TEST_FIXTURE`** — classified
**implementation and checkability**, not a research-result freedom, and **this
doc-only PR changes no test**. Recorded so the implementing PR is not surprised.

##### Ruling c-1 … c-9 — the NR-L limbs

**c-1 — the correlation universe is the frozen registered `PAIRS_20`.**
**`NR_L_CORRELATION_UNIVERSE_EQUALS_FROZEN_REGISTERED_PAIRS_20`.** Not active pairs,
not traded pairs, not non-zero-variance pairs, not a subset with a favourable
correlation, and not a set chosen after any series is seen. This **closes**
`KEEP_P_20_BUT_COMPUTE_C_ON_A_FAVOURABLE_SUBSET` and
`OUTCOME_DRIVEN_CORRELATION_SET_IS_THE_SAME_LEVER_IN_THE_OTHER_FACTOR` as contract
questions.

*And it follows from the only reading on which the committed form is the quantity it
resembles.* `1 + (P − 1)c` is the equicorrelated
variance-inflation factor of a sum of `P` elements: from
`Var(Σx_i) = Σσ_i² + 2·Σ_{i<j} ρ_ij σ_i σ_j`, at equal `σ` this is
`σ²·P·[1 + (P − 1)·ρ̄]` where `ρ̄` is the **equal-weight mean of ρ_ij over the
`P(P−1)/2` unordered off-diagonal pairs of the *same* `P` elements**. A `c` estimated
over a subset while `P` stays at twenty is therefore **not a permitted reading of the
committed formula** — it is a different quantity substituted into it. §8.5.3's
"whether prereg §3.2's compliance clause already bars it" no longer has to be answered
for NR-L1 to close.

**c-2 — Pearson, over the 190 unordered off-diagonal entries, equal-weighted.**
**`C_STATISTIC_IS_EQUAL_WEIGHT_PEARSON_OVER_UNORDERED_OFF_DIAGONAL_ENTRIES`.**
All three follow from the same identity **under the reading that
`mean_abs_pairwise_corr` occupies the identity's `ρ̄` slot** — the reading c-3 then
knowingly departs from. The identity appears in **no** committed source: the APPROVED
spec names no variance, no inflation factor and no equicorrelation. These are
therefore **derived-under-a-stated-reading**, not derived from committed text, and the
reading is this ruling's. *An earlier drafting called them derived without the
qualifier.* On that reading:

- **Pearson**, because the identity above is an identity about *covariance*; a rank
  correlation does not make it hold, so no other coefficient reproduces the committed
  formula. Function naming carries none of this weight and is not relied on.
- **The 190 unordered off-diagonal entries.** The diagonal is the `P` term in
  `1 + (P − 1)ρ̄`; including `ρ_pp = 1` in `ρ̄` would count it twice. The 380 ordered
  off-diagonal entries give the *same* mean, since `r_pq = r_qp`, so that reading is
  not excluded — it is simply the same number.
- **Equal weight per unordered entry**, because that is the weighting the identity
  uses. **`C_EQUAL_WEIGHTING_IS_EXACT_ONLY_UNDER_EQUAL_PER_PAIR_VARIANCES`** — the exact
  weighting is `w_pq ∝ σ_p·σ_q`, so equal weighting is exact only if the twenty
  per-pair **daily-PnL volatilities** are equal, which no committed source asserts.
  *An earlier drafting grounded this on §0.6's "88 of 190 entries share a leg"; that
  is a statement about the correlation matrix's **block structure**, which does not
  bear on variance equality at all — the identity is exact for **any** correlation
  matrix at equal `σ`. That citation is **withdrawn** and the correct ground stated.*
  The exposure is **anti-conservative when variance is concentrated**: eighteen pairs
  at unit `σ` and independent, plus two at `σ = 50` perfectly correlated, gives a true
  variance-inflation factor of `2.00` against a surrogate `1 + 19·mean|ρ| = 1.10`.
  **`NON_NORMATIVE_DIAGNOSTIC_ONLY`**; synthetic arithmetic, no data read. The ruling
  adopts the committed form's own weighting and **records the assumption as false**
  rather than repairing the form, which would be an amendment.

Sample-count, trade-count, PnL, volatility and performance weighting are **forbidden**;
none is committed and each makes the weight a function of the outcome.

**c-3 — the absolute value goes inside.**
**`C_IS_THE_MEAN_OF_ABSOLUTE_PAIRWISE_COEFFICIENTS_NOT_THE_ABSOLUTE_VALUE_OF_THE_MEAN`.**
For every required unordered entry take `r_pq`, then `|r_pq|`, then average:
`c = mean_{p<q} |r_pq|`. **Not** `|mean_{p<q} r_pq|`.

This limb is a **human + ChatGPT choice, not a derivation**, and it is the limb §8.5.2a
ranks joint-first. By the triangle inequality `mean(|ρ|) ≥ |mean(ρ)|` with equality
only if all **non-zero** entries share a sign, so `|mean(·)|` is the `N_eff`-favourable
reading
**for every dataset** — the A-ω-5 property, knowable with **no data at all**, which is
why a pre-data freeze alone would not have protected it. The ruling takes the
conservative arm, and it matches the committed phrase's own word order ("mean
**absolute** pairwise correlation"). It also **departs from the identity in c-1**,
which takes the *signed* mean: `mean|ρ| ≥ mean(ρ)`, so the ruled `c` is
weakly larger than the exact VIF's `ρ̄` and `rho_x` is weakly larger — a deliberate
conservative departure, stated rather than presented as the same object.
**`C_STATISTIC_MUST_NOT_BE_SELECTED_TO_MINIMISE_RHO_X`** is the token
`NO_PROHIBITION_BINDS_THE_CHOICE_OF_CORRELATION_STATISTIC` recorded as missing; it is
supplied here.

**c-4 — the series is per-pair daily *net realised* PnL at the primary cost cell.**
**`C_SERIES_IS_PER_PAIR_DAILY_NET_REALISED_PNL_AT_THE_PRIMARY_COST_CELL`.** For each
registered pair and each date in c-6's index, the sum of the realised PnL of every
trade attributed to that date under Q10-i, **net of the registered trading-cost
model** — the spread already embedded once in `gross_pnl_pips`, and the flat slippage
cell subtracted **once per trade** — never once per date — at
`PRIMARY_COST_CELL_PIPS = 0.5`. *The two readings give different series: the per-trade
reading injects a `−0.5 × daily trade count` common-activity term into every pair,
which is itself correlation-bearing, and it is the reading `net_pnl(trade, cell_pips)`
implements.* Multiple trades on one date are
**summed**, never averaged.

*The cost layer is ruled on a reading, and the cell is ruled outright — an earlier
drafting called the cost layer derived, and c-6 is why it cannot be.* The committed
dependence note says
`rho_x` **captures the cross-pair term** of the daily portfolio sum the Sharpe is
computed on; `c` must therefore be the correlation of the **per-pair components of
that same sum**, and that sum is net of the cell. Choosing the gross series would make
`c` a statistic of an object nothing aggregates. **But c-6 then rules an index that is
not that sum's date set**, so the note is followed where it yields the conservative
arm and departed from where the frame is concerned; the net series is the **better
reading** of the note, not a derivation from it. What is *ruled* rather than derived is
**which** cell: the series exists at three cells (0.0 / 0.5 / 1.0), and the primary one
is selected because the primary metric is denominated in it — **`c` is not recomputed
per cost-sensitivity cell**, and `rho_x` does not vary across the sensitivity grid, so
the sufficiency verdict computed at the primary cell is imported unchanged into the
stress cell.

*And the cell has a direction, stated because every other choosable limb here gets
one.* Writing a pair's daily series as `X_p(d) = G_p(d) − k·n_p(d)` with `k` the cell
and `n_p(d)` that date's trade count, a larger `k` pulls each series toward
`−k·n_p(d)`, so `r_pq` moves toward `corr(n_p, n_q)` — positive wherever activity
co-occurs. **The lower cell is therefore the likelier `N_eff`-favourable arm, and this
ruling takes the middle one.** The direction is conditional on the activity
correlation, so it is recorded rather than claimed as a proof.
**`NON_NORMATIVE_DIAGNOSTIC_ONLY`**.
**`CORRELATION_SERIES_COST_LAYER_NOT_REGISTERED` is closed.**

No new normalisation is introduced. Pearson correlation is invariant to positive
affine rescaling of each series, so a fixed per-pair pip-value scaling cannot change
any `r_pq`; a **time-varying** exposure scaling or a sign-changing transform could, and
both are **forbidden** absent a committed authority.
**`C_SERIES_MAY_NOT_BE_RESCALED_BY_ANY_TIME_VARYING_OR_SIGN_CHANGING_TRANSFORM`.**

**c-5 — day attribution follows Q10-i.** The exit UTC date, for every pair, with no
per-metric or per-pair variation. **`C_DAY_ATTRIBUTION_IS_Q10_I`** — and the coupling
runs the other way too: this ruling settles `c`'s day rule **because** Q10-i settles it
for the family, not by choosing one for `c` alone. §8.5.6's warning against settling
the Sharpe series' day rule by the back door is honoured by ruling the front door.

**c-6 — one common, complete DESIGN UTC calendar-date index for all twenty pairs.**
**`NR_L_USES_COMMON_FULL_DESIGN_UTC_DATE_INDEX_WITH_IDLE_ZERO`.** The index is every
UTC calendar date from `DESIGN_START`'s date through `DESIGN_END`'s date inclusive —
**2025-04-25 … 2026-02-28**, which is **310 dates** (derived from two committed
constants; no data is read and no boundary is invented). Every pair rests on **that
index**, identically. Forbidden: pairwise intersections of active dates, per-entry
deletion, union-with-zeros, and any index whose membership depends on activity.
**`CORRELATION_DATE_ALIGNMENT_NOT_REGISTERED` and
`ALIGNMENT_MUST_NOT_CREATE_AN_UNREGISTERED_FAVOURABLE_SUBSET` are closed.**

*And the right edge is ruled rather than assumed — a hole exit attribution creates
and entry attribution did not have.* Q10-i places a trade by its **exit**, so a
DESIGN-span decision bar near 2026-02-28 can have an exit date outside the index; the
next date is `DEAD_START = 2026-03-01`, inside the fenced dead window, where a
design-span observation may not be placed. The label machinery's eligibility rule
would keep every exit in range, but that rule is **unadopted M1-lineage precedent**,
so it is not leaned on. **Membership is decided by the attributed date**: a trade
whose Q10-i exit date falls outside `2025-04-25 … 2026-02-28` is **not part of the
series** — not clamped to the nearest in-index date, and the index is **not** extended
to 311.
**`C_SERIES_MEMBERSHIP_IS_DECIDED_BY_THE_ATTRIBUTED_DATE_AND_THE_INDEX_IS_NEVER_EXTENDED`.**

*This is not the drop c-8 forbids, and the difference is stated so it cannot be cited
as licence.* c-8 forbids removing a **pairwise entry** because it is inconvenient —
a choice made on the entry's effect. This is a **frame-membership rule**: deterministic,
declared before the data, bounded by two committed constants, reaching at most one
horizon's worth of decision bars at one edge, and with no favourable direction anyone
can select. *Two review roles proposed different dispositions here — one fail-closed,
one exclusion. Fail-closed is rejected on the evidence: an exit spilling past the span
end is a **normal** outcome, near-certain to occur, so a fail-closed rule would halt
`c` essentially always — the same defect §8.5.10 limb 8 identified in a flatly
fail-closed NR-L6.*

*Two consequences, both recorded rather than smoothed.* First, the index contains
**89 Saturday/Sunday dates of the 310 (28.7%)** — a fact about the calendar, and
nothing more. **Whether any of them carries a registered M15 slot, and therefore
whether any can carry an exit-attributed trade, is a calendar-authority question this
document may not answer and does not answer**; no weekend, closure or reopen rule is
authored here. *An earlier drafting said those dates are ones "on which the FX market
is closed and every pair is necessarily idle" — a market-hours fact stated in the very
paragraph that declines to author one, and the fourth time this document has done it.
Withdrawn.* Excluding those dates would require exactly such a calendar, so the plain
calendar index is taken **as the price of not inventing market hours**, not as the
statistically ideal frame, and **not** on any assumption about which dates are idle.
**`WEEKEND_IDLENESS_IS_NOT_ASSERTED_BY_THIS_RULING`.** A later trading-day index **derived from the approved
Calendar A** is **not established to be a tightening** — an earlier drafting said it
was, and that is **withdrawn**. By c-7's own mechanism the common-idle block moves
`|r|` toward the uncentred cosine similarity, so with non-zero per-pair daily means it
makes `|r|` **larger** where co-active PnL is non-negatively correlated and **smaller**
where it is negatively correlated, and it is neutral only at zero mean. Whether
removing those dates tightens or loosens therefore depends on the sign of the induced
common-mode term, which is a property of the measured run.
**`CORRELATION_DATE_INDEX_COMMON_MODE_DIRECTION_NOT_ESTABLISHED`** — so c-6's frame is
a **third** limb whose direction is not conservative-by-construction, and it is
neither claimed conservative nor claimed anti-conservative. It is **not** taken here
and NR-L is **not** routed through `ω`'s eligible-slot clock.
**`CORRELATION_DATE_INDEX_INCLUDES_NON_TRADING_CALENDAR_DATES`.** Second, this index is
**not** the day set the Sharpe is computed on: `daily_portfolio_pnl` emits only dates
that carry a trade. `c` and the daily Sharpe are therefore two statistics of two
different date sets, which is a coherence gap in the committed dependence note, not an
arithmetic error in either. **`SHARPE_DAY_SET_AND_CORRELATION_DAY_SET_ARE_DIFFERENT_OBJECTS`**
— recorded, **not** repaired here, because repairing it would change a frozen
acceptance row's measured value for reasons unrelated to this ruling.

**c-7 — an idle pair-date carries zero.**
**`IDLE_PAIR_DATE_CARRIES_ZERO_REALISED_PNL`.** A pair-date with no trade attributed to
it under Q10-i is **0.0**, never missing, never excluded, never carried forward. A day
on which the strategy did not trade is a realised daily outcome of zero, and any
"missing" treatment reintroduces exactly the activity-dependent date deletion c-6
forbids.

**And the ruling accepts a known anti-conservative direction, in the open — with the
mechanism stated exactly, because the loose version of it is wrong.** As the
common-idle share of the index grows, both means fall toward zero and the Pearson
coefficient converges to the **uncentred cosine similarity of the two active-date
vectors** over that index. Where activity is close to **exclusive** the two supports
are near-disjoint, that cosine is near zero, and `|r|` collapses — which lowers `c`,
lowers `rho_x` and **raises `N_eff`**. §0.6 projects roughly **0.56 trades per pair per
day**, so a large idle share is exactly the expected regime and this is the direction
that matters here. But it is **not unconditional, and the ruling does not claim it
is**: where activity **co-occurs**, common zeros can leave `|r|` unchanged, can flip
its sign, and can make it **larger** than the centred coefficient on active dates —
`p = [1, 2, 3]`, `q = [3, 2, 3]` has a centred `r` of exactly `0` on its
active dates and a zero-limit `r` of `16/√308 ≈ 0.912`. **`NON_NORMATIVE_DIAGNOSTIC_ONLY`**; the example is synthetic
arithmetic and reads no data. *An earlier drafting said common zeros "dilute `|r|`
toward zero", which names the sparse-exclusive case as though it were the rule; the
mechanism above replaces it.* What survives unchanged is that the direction **is
analytically knowable in the regime this family expects**, so by §8.4.11's A-ω-5
standard *"chosen before the data"* is **not** a defence for it. Two things make it the ruling anyway, and both are
stated as reasons rather than as derivations: every alternative is an
activity-dependent selection route, which is a *larger* and **invisible** freedom; and
the committed dependence note points `rho_x` at the correlation of the daily portfolio
sum's components, whose value on an idle date genuinely is zero — so the zero-filled
series is the object the note names, not an approximation to a latent trade-level
correlation. **`IDLE_ZERO_FILL_DILUTES_CORRELATION_IN_THE_SPARSE_REGIME`** — carried,
and **no one may cite a small measured `c` as evidence of independence beyond what
this construction measures.**

**And the ruled statistic cannot reach the spec's own limiting case — recorded because
the spec quotes it as authority.** `mean|r|` is a **positively biased** estimator of
zero: for independent series of length `n` its expectation is
`√(2/π)/√(n − 1)`, which at `n = 310` is about **0.045**. So twenty genuinely
independent pairs still give `rho_x ≈ 1 + 19 × 0.0454 ≈ 1.86` and lose about 46% of
`N_eff`, and the spec's "Independent pairs ⇒ `rho_x → 1`" is **finite-sample false by
construction of the ruled statistic**. The direction is **conservative**, so this is
not a lever; it is a fourth accepted cost, and it runs opposite to c-7's, so the net
of the two is **not signed**. **`MEAN_ABS_ESTIMATOR_HAS_A_POSITIVE_NULL_FLOOR_AT_310_DATES`**
· **`NON_NORMATIVE_DIAGNOSTIC_ONLY`**.

**c-8 — an undefined required entry fails closed. It is never dropped and never
substituted.**
**`UNDEFINED_REQUIRED_PAIRWISE_CORRELATION_FAILS_C_CALCULATION_FOR_CURRENT_FAMILY_A`.**
If any of the 190 required entries is undefined, `c` **cannot be authoritatively
calculated**, and therefore no `N_eff` verdict may be issued from it. Forbidden:
dropping the pair, dropping its 19 entries, substituting `0`, substituting any other
packet-supplied number, and shrinking the universe — the last being barred by c-1
regardless.

*The reason is direction, not tidiness.* Every degenerate resolution drives `rho_x`
toward 1, and at `P = 20` that removes the **entire** cross-pair discount — the harm a
**merged** Gate-decision already records as able to "**disarm `INSUFFICIENT_SAMPLE`**".
The only pairwise-correlation precedent in the repository does all of it at once —
`< 5` shared observations → `0.0`, zero variance → `0.0`, non-finite → `0.0`, on a
pairwise finite-mask intersection of *per-bar gross* PnL — and it is **refused by
name**, not adopted.

*And under c-6 and c-7 the case collapses to one.* With all twenty series on the same
310-date index, "insufficient overlapping observations" and "no common dates" **cannot
arise**. Pearson is undefined exactly when a leg has zero sample variance, and a
zero-filled daily series is constant only if the pair's daily net PnL is identical on
all 310 dates — so, if that pair has at least one idle date, the constant is
**zero** and the pair produced no DESIGN-span trade with a non-zero daily net sum —
in practice, no DESIGN-span trade at all. The only other way in is fully degenerate:
a pair whose daily net sums are **exactly equal on every one of the 310 dates**. *No
claim is made here about which dates are idle: that would be a market-hours fact, and
this ruling authors none.* So the fail-closed trigger is narrow and nameable, and
§8.5.8's four cases reduce to it.

*Two things that trigger is deliberately **not** stretched to cover.* A pair with
exactly **one** DESIGN-span trade has a defined series, so c-8 never fires on it — its
19 entries come out at `|r| ≈ 1` if the other leg's single trade shares that date and
`≈ 1/309` if it does not, two-sided and pinning 10% of `c` either way. And **near**
degeneracy is not degeneracy: a leg with variance of order `1e-30` is *defined*, and
c-8 reaches only exact zero variance. Both are accepted costs of a narrow trigger, and
**neither licenses a silent repair**: clamping an `|r|` that floating-point returns
marginally above 1 is forbidden — `_require_unit_fraction` rejects it, and that
rejection is the correct fail-closed outcome, not a defect to be patched around.
**`C_NEAR_DEGENERACY_IS_NOT_COVERED_BY_c_8_AND_MAY_NOT_BE_SILENTLY_REPAIRED`.** **`UNDEFINED_CORRELATION_SEMANTICS_PENDING_HUMAN_CHATGPT_RULING`
is closed.**

*Fail closed is not permanent failure, and it coins no new state.* It means that **for
the frozen evaluation being assessed** the cross-pair deflator cannot be certified
under the registered method. It routes into the committed `failure_handling` — an
insufficient **validation** sample means "family A closes **or adoption waits** per the
frozen contract; no holdout is touched", and **holdout** acceptance "cannot be
granted". No production-like status is invented.

*But that routing is a **reading**, not a quotation, and two things about it are
recorded rather than smoothed.* The spec's validation branch is triggered by an
insufficient **sample** — "raw or effective below the family's minimum" — and it
carries **no branch for an uncomputable deflator**; this ruling reads the uncomputable
case into it rather than coining a state, and labels the reading as one. *An earlier
drafting called it "the committed one, unchanged".* And the branch it routes into is a
**disjunction this document already records as having no selector**
(`VALIDATION_BRANCH_DISJUNCTION_HAS_NO_SELECTOR_RESIDUAL_AFTER_Q11_SECTION0_RULING`):
"closes **or** adoption waits" does not say which. So a c-8 halt reaches an unselected
pair of outcomes, and **any party able to zero one registered pair's DESIGN-span
activity can reach it**. Recorded, not resolved. **`C_UNCERTIFIABLE_ROUTES_TO_THE_COMMITTED_FAILURE_HANDLING_NOT_TO_A_NEW_STATE`.**

*The collision §8.5.10 limb 8 named is not dissolved, and is not pretended away.* A
registered pair that fires nothing is a **normal outcome** under §8.3.0, and it is
exactly what triggers c-8. The ruling accepts that: a pair with zero DESIGN-span
trades supplies **no evidence of independence**, and the alternative — treating absence
as `r = 0` — rewards missing information at the point where the frozen floor bites.
**`NOTHING_BOUNDS_DESIGN_SPAN_ACTIVITY_AND_A_SPARSER_RUN_DILUTES_C`** — recorded
because it compounds with the open blocker above. Every activity floor the contract
carries is a **holdout** quantity: raw `>= 1000`, `N_eff >= 400`, and daily coverage
`>= 0.60` against a holdout-denominated denominator. `c` is a **DESIGN**-span
quantity, and §4's R-10 writes its event-rate lever **one-directionally** — it bars
choosing an operating point "in order to **raise** the event rate so a floor clears"
and is silent on lowering it. So on the span where `c` is measured there is **no floor
on activity at all**, and a sparser operating point dilutes `|r|` in the regime §0.6
projects. It becomes a *free* lunch only under
`NR_L_GENERATING_CONFIGURATION_NOT_REGISTERED`; where one configuration governs both
spans, sparsity trades `c` against the raw floor. The two compound, which is a further
reason the blocker below was a blocker — **and Ruling c-10 closes that half**: with
`c_design` computed and frozen for every registered `ev_min` point before the selector
runs, no party can prefer the sparser one *for its `c`*. What survives is that the
committed selection metric is itself activity-correlated, which is Ruling 9's design.

**`C_FAIL_CLOSED_CAN_BE_TRIGGERED_BY_A_NORMAL_OUTCOME_AND_THAT_IS_ACCEPTED`** — carried
as an accepted cost, not as a defect, and the route out is a new explicit
pre-registration, never a silent substitution — **a route whose sufficiency is itself
unruled (`NEW_PREREGISTRATION_SUFFICIENCY_FOR_A_DIFFERENT_D_NOT_RULED`), so it is
named here as the *only* route and not as an available one**, on the same terms
Ruling ω-12 states it.

**c-9 — DESIGN span only; method frozen now, value measured once.**
**`C_IS_MEASURED_ON_THE_FULL_FROZEN_DESIGN_SPAN_ONLY`** ·
**`C_METHOD_PRE_DATA_FROZEN_C_VALUE_DESIGN_MEASURED_ONCE`.**

- **Span — committed, and not reopened.** "DESIGN span only (2025-04-25..2026-02-28);
  never validation/holdout; frozen once and recorded." **The full span**, not a
  favourable sub-window, not a recent slice, not active days only, and not a
  pair-specific range. c-6's index **is** the full span, so this limb and c-6 are the
  same object seen from two sides.
- **Method — frozen by this ruling**, before any DESIGN-span correlation is observed.
  That is a fact about the record, not an assumption: no design-span derivation has
  run, and `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` still bars it.
- **Value — measured once**, mechanically, from the frozen series, at the
  implementation stage. This is also what reconciles the artifact's
  `no_strategy_metrics_computed_at_gate3a: true` with its defining `c` on daily PnL:
  gate 3a fixes the **method**, and the **measurement** happens later. That is the only
  reading on which both clauses are true, and it is recorded as a reading.
  **`CORRELATION_SERIES_IS_A_STRATEGY_METRIC_AT_A_GATE_THAT_FORBIDS_THEM` is resolved
  by that reading**, not by amendment.
- **No recalculation to improve `N_eff`.**
  **`C_MUST_NOT_BE_RECALCULATED_OR_ITS_METHOD_RESELECTED_AFTER_ANY_DOWNSTREAM_OBSERVATION`**
  — not the day attribution, the idle rule, the pair set, the coefficient, the entry
  set, the weighting, the absolute-value placement, the date index, the cost layer or
  the span. §8.5.9 recorded that "nothing committed says it is forbidden" and that
  NR-K's non-reduction clause and Ruling ω-10 both stop short of `c`; this supplies it.

##### The one thing §8.5.0 did not close — the producing configuration — CLOSED BY RULING c-10

**`NR_L_GENERATING_CONFIGURATION_NOT_REGISTERED`** — **HISTORICAL, closed by Ruling
c-10 below.** The subsection is retained as the material that ruling was taken on.

**⚠ And one sentence of it was wrong at source.** It said the family carries "three
registered decision **thresholds** … and three registered `ev_min` operating points",
nine configurations. `THRESHOLD_CANDIDATES` and `MAX_CONFIGURATIONS` are **M1-lineage**
(`scripts/ml_step4/contract.py`), and prereg Ruling 9 states twice that "**a raw
probability threshold alone is explicitly not a permitted decision rule**". The
registered candidate set for current Family A is **three `ev_min` points and one
horizon — three configurations**. Ruling c-10 records the correction; the blocker
survived it, narrowed.

**c-1…c-9 fix how `c` is computed from a series. They do not fix which run produces
the series.** `c` is a statistic of the trades a *particular* DESIGN-span
configuration generated — its feature list, warm-up, model, EV-gate `W̄`/`L̄`, cost
hurdle and operating point. *(As written, and wrongly:)* the family carries three
registered decision thresholds (`THRESHOLD_CANDIDATES = (0.35, 0.40, 0.45)`,
`MAX_CONFIGURATIONS = 3`) and three registered `ev_min` operating points, and each
combination yields a different trade set, a different daily series and a different
`c`. **The true registered variation is the three `ev_min` points alone**, and the
conclusion is unchanged: three trade sets, three daily series, three values of `c`.

**The route obeys every ruled word.** Run several exploratory design-span variants,
read each variant's `c`, declare `c` from the lowest. c-1 is satisfied — all twenty
pairs, all 190 entries. c-6, c-7, c-4 and c-5 are satisfied. c-9 is satisfied: `c` is
measured **once**, from the frozen method, and its bar reads "after any **downstream**
observation" while variant selection is an **at-stage** observation. c-9's own
enumeration confirms the hole — it bars reselecting the day attribution, the idle
rule, the pair set, the coefficient, the entry set, the weighting, the absolute-value
placement, the date index, the cost layer and the span, and **the producer is not in
the list**.

**§4's R-10 forbids exactly this, names this exact quantity as its sharpest case, and
hands the remedy to this gate.** "`rho_x = 1 + 19 × mean_abs_pairwise_corr` sits in
the **denominator** of `N_eff`, so a variant yielding a lower correlation estimate
**raises** `N_eff` … That disarms a frozen sample floor while loosening no threshold
and while listing every variant honestly. **No quantity destined to be frozen into the
family-A contract may be taken from an exploratory variant chosen after its results
were seen.** Each is either estimated by **a rule registered before the campaign
starts**, or left entirely to the **design audit and gate 3a, which own it**." §5 puts
R-10 **IN**. **§8.5.0 is the gate-3a decision R-10 hands it to, and it registers no
producer rule** — so the second disposition is unexercised and the first does not
exist.

**Why it cannot simply be "the evaluated configuration".** The decision threshold is
**selected on validation** (`select_threshold`), which is *after* the design span, so
the configuration family A ultimately evaluates does not exist when `c` must be
measured. That is what makes this a genuine choice rather than a wording gap.

**Candidate dispositions, enumerated and none chosen here.** (a) A single
**pre-declared** design-span configuration — for instance the committed
`PRODUCTION_DEFAULT_THRESHOLD` with a named `ev_min` — fixed before any design-span
observation. (b) The **conservative arm**: `c` is the **maximum** over the registered
candidate grid, which forecloses the favourable direction outright, on the same shape
c-3 uses, at the cost of computing the matrix once per candidate. (c) A rule that
makes `c` a function of the grid as a whole in some other declared way. **This ruling
picks none of them**: a producer rule is a human + ChatGPT choice, and inventing one
here would be this session deciding a contract question it may not decide.

**Classified by this ruling's own test.** It is a remaining freedom capable of moving
`c` and `N_eff`, exercisable by a party in the research path, with an analytically
knowable favourable direction (lower `c` always raises `N_eff`). Under §8.4.13 that is
**IN**, and an unclear classification defaults to blocker in any case. So it is a
**`MINIMUM_RESEARCH_GATE_BLOCKER`**, not a residual, and it is stated as the **one**
thing left rather than used to reopen the packet.

**`C_PRODUCING_CONFIGURATION_REGISTRATION_IMPLEMENTATION_PENDING`** is the separate,
lesser point: even once a producer rule is registered, no artifact today binds the
configuration identity behind `c` to the configuration identity behind the evaluated
run.

##### Ruling c-10 — the producing configuration, and the correction of a premise this document carried

**`NR_L_C_PRECOMPUTED_FOR_ALL_REGISTERED_CONFIGURATIONS_BEFORE_VALIDATION_SELECTED_BY_CONFIG_ID_ONLY`**

A ruling received from human + ChatGPT and recorded here as **authority**. It closes
`NR_L_GENERATING_CONFIGURATION_NOT_REGISTERED`, the one blocker §8.5.0 left open.

###### First, the registered configuration set — and it is not what §8.5.0 said

**§8.5.0 said "three registered decision thresholds and three registered `ev_min`
points", nine configurations. That is WRONG and is withdrawn.** It imported the
**M1** threshold grid into M15. Re-read at source:

| What committed text says | Where |
| --- | --- |
| **`ev_min ∈ {0.0, 0.25, 0.5}` pips; chosen on validation only; tie rule: smallest passing `ev_min`; selection metric: validation net expectancy subject to the turnover budget. The selected operating point is evaluated on the holdout exactly once.** Ruling 9, **FROZEN** | prereg §8, operating-point selection |
| "**A raw probability threshold alone is explicitly not a permitted decision rule**", stated twice | prereg §8 (EV-gate mechanism, and again in Ruling 9) |
| Multiple-comparison budget: "small pre-registered candidate sets (**one horizon, three `ev_min`**)" | prereg §12 risk register, row 10 |
| `ev_min ∈ {0.0, 0.25, 0.5}` pips; validation-only selection; tie = smallest passing; selected point evaluated on holdout exactly once; **raw probability threshold alone forbidden** | prereg §16, **Ruling 9** |
| `THRESHOLD_CANDIDATES = (0.35, 0.40, 0.45)`, `MAX_CONFIGURATIONS = 3` ("3 validation threshold variants; 1 on holdout"), `THRESHOLD_TIE_RULE`, `PRODUCTION_DEFAULT_THRESHOLD = 0.40` — all in the **M1 flagship** module, beside `HORIZON_M1_BARS` and M1's `COMMON_WINDOW_*` instants | `scripts/ml_step4/contract.py:70-83` |

So the registered candidate set for current Family A is **three `ev_min` operating
points and one horizon — three configurations, not nine**, and the probability
threshold M1 searched over is **forbidden** here as a decision rule. The M1 constants
are unadopted M1-lineage (prereg §11), and citing them as M15's candidate grid was the
same class of error §8.5.6 records for the day-attribution precedent.
**`SECTION_8_5_0_NINE_CONFIGURATION_CLAIM_WITHDRAWN_THE_REGISTERED_SET_IS_THREE_EV_MIN_POINTS`.**

**The blocker survives the correction, narrowed.** Three `ev_min` points still give
three different eligible-trade sets — `EV_d ≥ ev_min` admits strictly fewer events as
`ev_min` rises — hence three different per-pair daily series and **three different
`c`**. Nothing in c-1…c-9 said which one.

**The corrected set was checked for exhaustiveness, not just for the threshold
error.** Prereg §8 freezes the **model family** (LightGBM, `learning_rate = 0.05`,
`num_leaves = 31`, `n_estimators = 200`; "no model-family search", "no post-result
model changes"), the **class-weighting** default ("weights are never changed post
hoc"), and the **calibration** ("isotonic regression … **no calibration-method
search**"); §7 freezes the **feature list** "at the design audit and hashed into the
contract"; Ruling 6 freezes the **horizon** at 24. So `ev_min` is the **only**
registered multiplicity, which is exactly what §12 row 10's "one horizon, three
`ev_min`" says.

**And everything else in the pipeline is a single frozen value, not a candidate set.**
The cost table is frozen from design-span spreads (§5); `W̄`/`L̄` are "estimated on
design data and **frozen** (never re-fit on validation/holdout)"; calibration is
fitted on train-only with **"no calibration-method search"**; the feature list and the
warm-up `W` are design-span estimates the design audit and gate 3a own. Those are
governed by §4's **R-10** and are **not** re-opened here: R-10 already bars taking any
of them "from an exploratory variant chosen after its results were seen".

###### The ruling

**`c` is not one value from one reference configuration.** A DESIGN-only `c` is
computed **separately for every preregistered candidate configuration**, before any
validation observation, using the method already ruled at c-1…c-9 unchanged:

> `c_design[config_id]` for **every** `config_id` in the registered candidate set —
> for current Family A, the three `ev_min` operating points `{0.0, 0.25, 0.5}`.

**The sequence, in order, and no step of it is an authorisation.**

> **1.** the complete candidate configuration set is preregistered → **2.** every
> configuration identity is frozen → **3.** before any validation observation, the
> DESIGN-only per-pair daily series is built for **each** configuration → **4.**
> `c_design[config_id]` is computed for each by the c-1…c-9 method → **5.** the
> complete mapping `config_id → c_design` is **frozen** → **6.** the committed
> validation selection rule is applied → **7.** validation selects exactly one
> `config_id` → **8.** the already-frozen `c_design[config_id]` is attached
> **mechanically** → **9.** only then may later gates use that `c` → **10.** the
> holdout remains later, and untouched.

**Why this closes the freedom rather than relocating it.** The map is **complete** and
**frozen before** anything downstream is seen, so there is nothing left to choose: the
only remaining act is a lookup, and the key is supplied by a selection rule that never
sees `c`. Variant-shopping needs a chooser, and after step 5 there is none.

###### One-way selection — the limb the ruling turns on

**`C_MUST_NOT_BE_A_CONFIGURATION_SELECTION_CRITERION`** ·
**`VALIDATION_SELECTION_MAY_SELECT_CONFIG_ID_BUT_MAY_NOT_SELECT_OR_RECOMPUTE_C`.**

Permitted direction: **validation result → selected `config_id` → the already-frozen
`c_design[config_id]`**. Forbidden direction: **`c_design` → configuration
selection**, in any form — directly, through `rho_x`, through `N_eff`, through a
sample-floor verdict, or through a count of undefined pairwise entries.

**And `c` may not become a tie-breaker.** The committed tie rule is already fixed and
`c` is not in it: Ruling 9 fixes the selection metric as **validation net expectancy
subject to the turnover budget** and the tie rule as **the smallest passing
`ev_min`** — deterministic, and blind to `c`. Choosing a configuration for a lower
`c`, a higher `N_eff`, a more favourable `rho_x`, or fewer undefined pairwise entries
is **forbidden**, and none of them may be introduced as a secondary criterion.
*Where tie semantics are unregistered elsewhere, they stay their own question: this
ruling does not repair them through `c`, and may not be cited as doing so.*

###### No post-selection recomputation

**`SELECTED_CONFIG_USES_PREEXISTING_FROZEN_C_ONLY`.** Once validation has selected a
`config_id`, the attached `c` is the one frozen at step 5. It may **not** be
recomputed on a different DESIGN sub-window, nor under a changed idle-day rule, pair
universe, cost treatment, Q10(i) attribution, coefficient or absolute-value placement;
it may **not** be recomputed "for the selected configuration only" after validation is
seen; and alternative `c` versions may **not** be compared. This is c-9's bar with the
producer now inside its scope — the omission §12.13 recorded.

###### One candidate whose `c` is undefined

If a preregistered candidate configuration cannot yield an authoritative `c` because
c-8 fires on it, **that candidate is ineligible to become the final selected
configuration for current Family A** — and **its failure does not delete it from the
registered candidate set**, and does not shrink the preregistered universe before the
committed validation process runs.

*The three levels are kept apart deliberately.* **Candidate-level invalidity** — one
`config_id` cannot carry a certified deflator. **Validation-selection eligibility** —
that candidate cannot be the selected one. **Whole-family invalidity** — reached only
where the committed `failure_handling` reaches it, unchanged: at validation, family A
closes **or adoption waits**; at holdout, acceptance cannot be granted. Silently
dropping the candidate to preserve the search would be the same shape c-8 refuses at
the entry level and c-1 refuses at the pair level, so it is refused here at the
configuration level too.
**`UNDEFINED_C_MAKES_A_CANDIDATE_INELIGIBLE_IT_DOES_NOT_SILENTLY_SHRINK_THE_REGISTERED_SET`.**

**And this limb has to be reconciled with the completeness property below, because as
first drafted the two contradicted each other.** Completeness requires the map to
carry an entry for **every** registered `config_id`; ineligibility says a candidate
whose `c` is undefined is skipped. If an undefined candidate simply had no entry, the
map would be incomplete and no selection could be authoritative — which is whole-family
blocking, not candidate-level ineligibility. The reconciliation: **the map carries an
entry for every registered `config_id`, and an entry may be the recorded marker
`C_UNCERTIFIABLE` instead of a number.** That is **not** the substitution c-8 forbids —
c-8 refuses a *numeric* stand-in that would enter the arithmetic; a recorded
uncertifiability marker enters no arithmetic, produces no `rho_x`, and makes the
candidate ineligible rather than cheap.
**`AN_UNCERTIFIABLE_ENTRY_IS_A_RECORDED_MARKER_NEVER_A_NUMBER`.**

**And the honest consequence is stated rather than buried: eligibility filtering *is* a
route by which `c` reaches the selection.** If the committed rule would have selected a
candidate that is ineligible, the selected candidate changes — so `c`'s
*certifiability*, though not its *value*, has moved the outcome. Three things bound it
and none of them dissolve it. It is **not a freedom**: nobody chooses it, the marker is
a determined consequence of a frozen construction, and no party may induce or avoid it
on its effect (ω-12(e)'s outcome-blindness reaches the calendar; `C_MUST_NOT_BE_A_CONFIGURATION_SELECTION_CRITERION`
reaches this). Its **direction is derivable on one limb and a reading on the other**. Derivable:
`EV_d ≥ ev_min` is nested and the second condition `EV_d > EV_{−d}` is
`ev_min`-independent, so admitted signals at `0.5` ⊆ `0.25` ⊆ `0.0` and "this pair has
at least one trade" is monotone non-increasing in `ev_min`. Eligibility can therefore
only remove a **suffix** of the `ev_min` ordering, and c-8 firing at `ev_min = 0.0`
means it fires at all three — **whole-family, not candidate-level**. A reading: that
the removed candidate also carries the **lowest** `c` is c-7's recorded *tendency*, not
a theorem, and it does not survive a concurrency cap, under which **executed** sets are
not nested even though admitted sets are. So the interference runs conservative **on a
reading**, not on a bound — and this document has already had to withdraw one flat
"bounded conservative" claim (ω-12), which is why this one is labelled.

**The order is unregistered, and which order is *stricter* is derivable without
inventing a selection rule.** Select-then-check can only route a case into the
committed `failure_handling`; filter-then-select can only convert a case that
select-then-check would have closed into a **live selected configuration**. So
filter-then-select is **never** the stricter reading. Under CLAUDE.md's rule that the
stricter reading of a research restriction governs, **select-then-check is the
governing default**, and adopting filter-then-select requires an explicit human +
ChatGPT ruling. *This adds no selection rule: it refuses a rescue, which is the one
direction a default can move without choosing anything.*
**`SELECTION_VERSUS_CERTIFIABILITY_ORDER_NOT_REGISTERED`** is carried with that default
attached, so it is **not** a live lever — but it is **not discharged** either, because
a default installed here is not the ruling the question deserves.

**And the kill gate is untouched, expressly.** Prereg §9.V's floor is met "at at
least one registered `ev_min` operating point" — it reads the **registered** set, not
the eligible subset, and `c` may not tighten it, because §9.V is a Ruling-10-frozen
criterion the design audit alone may tighten. A candidate whose `c` is uncertifiable
may therefore still satisfy the kill gate, which leaves a state with **no committed
disposition**: a family that passes §9.V with no selectable configuration. That is
`SELECTION_VERSUS_CERTIFIABILITY_ORDER_NOT_REGISTERED` seen from the kill-gate side,
and the select-then-check default above is what keeps it from being a lever.
**`KILL_GATE_READS_THE_REGISTERED_SET_NOT_THE_ELIGIBLE_SUBSET`.**

**No new validation metric is invented**, and the committed selection metric is not
touched. Nothing committed sequences "selection" against "deflator certifiability", and
inventing an order would be inventing a selection rule — so the order is **not** ruled
here, it is **not** a licence to pick whichever order is favourable, and where it
matters the stricter reading governs and the case is a human + ChatGPT question.

###### Configuration completeness

**`set(c_design.keys()) == the registered candidate configuration set`** must hold
before any validation selection is treated as authoritative. A partial map is a
partial search, and a partial search is a chooser. **Every registered `config_id` has
an entry**; an entry is either a `c` value or the recorded marker `C_UNCERTIFIABLE`
(above), never nothing and never a substituted number.

This is a **contract property**, not a test and not a schema: no artifact machinery is
created here, and none is required to state it.
**`NR_L_CONFIGURATION_COVERAGE_IMPLEMENTATION_PENDING`** — nothing in code or evidence
binds the key set of the map to the registered candidate set, or binds the `config_id`
behind a reported `c` to the `config_id` behind the evaluated run. Classified
**implementation and checkability**, and the R-6 lightweight record §8.5.0 already
requires is extended by one field: **the `config_id`** the reported `c` was measured
under. That is a record, not a schema, and it invents no field.

###### Freeze semantics

The **method** (c-1…c-9) and the **configuration set** are frozen **before data**. The
`c` **values** are DESIGN-measured, once each. After they are measured: no
configuration may be added or removed, no `ev_min` value may change, no horizon may
change, no `config_id` may be aliased or renamed, and no reordering may be used to
obscure which value belongs to which configuration.
**`CONFIGURATION_SET_AND_IDENTITIES_ARE_FROZEN_BEFORE_C_IS_MEASURED`.**

###### What this ruling does not fix, stated rather than left implicit

- **Whether the DESIGN-span series behind `c` is in-sample.** Producing design-span
  trades needs a model, and no committed source says whether that model is fitted on
  the whole design span and predicted back onto it, or under an internal design-span
  split. The two give different daily series and therefore different `c`, and the
  direction is not established. **`C_DESIGN_SPAN_RUN_IN_SAMPLE_STATUS_NOT_REGISTERED`**
  — it is **not a chooser among configurations**, since every configuration is built
  the same way; but by this document's own §8.4.13 test it **is** a remaining freedom
  capable of moving `c` and `N_eff`, exercisable by a party in the research path
  (prereg §3.1 defines **no training-span role** — the roles are design, dead window,
  validation, holdout, replication — and §8's "a split carved from the training span
  only" pins the **calibration** split, not the classifier's design-span protocol),
  with a direction that is **not established** — and an unclear classification
  **defaults to blocker**. *An earlier drafting called it "a residual of the committed
  design"; that is not a category the test recognises, and it was unavailable to this
  ruling in particular, which is the ruling that pulled the producing run inside NR-L's
  scope. Withdrawn.* Carried as a **`MINIMUM_RESEARCH_GATE_BLOCKER`**.
- **The other design-span inputs — and the freeze binds the map's *keys*, not its
  *values*, which is a hole this ruling has to close rather than record.** Four inputs
  are frozen by **committed prereg text** and are not re-opened: the cost table (§5),
  `W̄`/`L̄` ("estimated on design data and **frozen**", §8), the calibration method
  ("**no calibration-method search**", §8), and the feature list ("frozen at the design
  audit and hashed into the contract", §7). **Four are not yet fixed, and every one of
  them changes which DESIGN-span bars become trades and therefore changes *every*
  `c_design` value**: the warm-up `W`; **Ruling 4's rollover exclusion window**, which
  prereg §5 leaves at "21:55–22:15 UTC **minimum** — gate 3a / the design audit may
  **widen it** only for conservatism"; the **holiday / thin-liquidity exclusion
  policy**, `[FIXED-AT design audit]` at prereg §16 row 4 and which §8.2.2 records
  gate 4's **T-6 as re-pointing to "implementation, approved before gate 7"**; and the
  **concurrency / exposure caps**, `[FIXED-AT design audit]` at prereg §9.

  **So the ruling adds the limb it was missing.**
  **`C_DESIGN_SERIES_INPUTS_MUST_BE_FROZEN_BEFORE_THE_MAP_IS_BUILT`** ·
  **`THE_MAP_IS_BUILT_ONCE_AND_A_CHANGED_INPUT_IS_NOT_A_NEW_MEASUREMENT_IT_IS_A_RESELECTION`.**
  `CONFIGURATION_SET_AND_IDENTITIES_ARE_FROZEN_BEFORE_C_IS_MEASURED` binds identities;
  this binds inputs, and without it "measured once each" is satisfied by rebuilding the
  whole map after moving an input — variant-shopping in the one place steps 1–5 left
  open, with a **knowable favourable direction**, since each of the four unfixed levers
  thins design-span activity and a sparser run dilutes `|r|`.

  **And that limb collides with the committed schedule, which is surfaced rather than
  smoothed.** T-6 puts the holiday / thin-liquidity calendar's approval at "before gate
  7" — **after** any point at which the map could be built. So the requirement is
  satisfiable in principle and **unsatisfied in fact**, exactly as Ruling ω-13(b)'s
  pre-data eligibility contract is.
  **`C_MAP_INPUT_FREEZE_CONFLICTS_WITH_T6_HOLIDAY_CALENDAR_SCHEDULE`** —
  a `MINIMUM_RESEARCH_GATE_BLOCKER`, and **not** one this ruling closes.
  *And `config_id` does not by itself determine the model*: prereg §8's seed policy
  records `bounded_not_bitwise_guaranteed` reproducibility, so two runs of one
  `config_id` need not yield the same trade set. "Once each" is the only bar, and no
  artifact stands behind it.
- **`NOTHING_BOUNDS_DESIGN_SPAN_ACTIVITY_AND_A_SPARSER_RUN_DILUTES_C`** survives in a
  **narrowed** form: a sparser *registered* `ev_min` still dilutes `|r|`, but no one
  may now select on it, because all three values are computed and frozen before the
  selector runs and the selector is blind to `c`. What remains is that the **committed
  selection metric itself** — validation net expectancy subject to the turnover budget
  — is correlated with activity; that is Ruling 9's design, not a freedom this ruling
  creates.

###### Amendment classification

**Addition on both halves — and an earlier drafting of this paragraph got that
wrong.** §4's R-10 forbids taking a frozen contract parameter "from an exploratory
variant chosen after its results were seen" and offers two dispositions, the second
being "the design audit and **gate 3a, which own it**"; this ruling **is** gate 3a
exercising it. *But R-10 is **this packet's own proposed text, not committed
authority***: §12.5 records that calling §4's R-10 "committed text" is **False** —
"§4 is *this packet's* proposal … offered as ruled text in a PENDING packet" — and
§8.3 adds that citing it as committed "is withdrawn and **must not recur**". It
recurred here, in the classification paragraph, and is withdrawn again. So the
*prohibition* is **not** confirmed from committed authority either: both the
prohibition and the mechanism are **additions**, which weighs on
`C_10_AMENDMENT_CLASSIFICATION_NOT_SETTLED` rather than mitigating it. The
**mechanism** —
compute for all, freeze the map, select by `config_id` only — is an **addition** no
committed source carries, as are the completeness property and the
undefined-candidate disposition. Whether such additions need a contract-amendment
procedure cannot be answered, because **no general contract-amendment procedure is
registered anywhere in this repository**
(`NO_GENERAL_CONTRACT_AMENDMENT_PROCEDURE_REGISTERED`, this packet's own token for
that absence). **`C_10_AMENDMENT_CLASSIFICATION_NOT_SETTLED`.**

**No favourable classification is asserted here.** The ruling **increases** the work —
three DESIGN-span correlation matrices instead of one — and it removes an arm that
would have been available under any single-reference-configuration reading. Its one
recorded cost is that it says nothing about the in-sample question above, and its
premise correction reduced the registered set from a claimed nine to a committed
three, which **narrows** the multiple-comparison surface rather than widening it.

###### Status after c-10

**`NR_L_MINIMUM_RESEARCH_CONTRACT_RULED_PENDING_IMPLEMENTATION_AND_DESIGN_MEASUREMENT`**
· the two blockers that survived c-10 are **closed by §8.7** (c-11, c-12), and
**`CLOSURE_CLAIM_WITHHELD`** — attempted a **third** time at §8.7.6 and grounded on a review section that did not yet exist; withheld then under **`CLOSURE_CLAIM_REQUIRES_COMPLETED_REVIEW_AND_NO_UNRESOLVED_MATERIAL_BLOCKER`** (§8.8.0 — the earlier same-round prohibition is **withdrawn as over-broad**). *The separate independent round has since run: §12.17 records **full coverage on the assigned scope, both roles returning**, so that rule's review condition is now **met**. Closure is still **NOT** taken, on a different ground — §8.9.6 records **seven live material blockers**, and **`M15_MINIMUM_RESEARCH_STATISTICAL_CONTRACT_NOT_CLOSED_MATERIAL_BLOCKERS_LIVE`**.*

`P` authority fixed (§8.3.0) · `c`'s formula, universe, entries, weighting,
absolute-value placement, series, cost layer, date index, idle rule and undefined-case
disposition fixed (c-1…c-9) · day attribution fixed (Q10-i) · **configuration-to-`c`
generation fixed (c-10)** · **no empirical `c` measured, no correlation computed, no
daily PnL constructed, no data read** · implementation and checkability remain ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

*The claim `NO_NR_L_MINIMUM_RESEARCH_CONTRACT_BLOCKER_REMAINS` was made here on the
strength of the corrected candidate set, and was **withdrawn** — for the second time,
and on the same test both times.* The two blockers that survived c-10 — the **in-sample
status** of the DESIGN-span run and the **collision** between c-10's input-freeze
requirement and T-6's schedule — are **closed by §8.7's Rulings c-11 and c-12**, and the
claim is made there instead, after that round's review returned. *Recorded rather than
smoothed: a closure claim made in the same round as the ruling that earns it was wrong
twice, and the second time the correcting evidence was already in the document.*

##### What is derived, what is ruled, and what stays open

Each limb is marked with **what actually backs it**. No limb is called derived because
it is convenient.

| Limb | Backing |
| --- | --- |
| Q10-i, exit-date attribution | **Human + ChatGPT ruling.** Committed authority fixes the day *identity* only; "(as in M1)" carries the aggregation shape, and reading it further would defeat prereg §11. **The repository's only precedent points the other way** and is departed from knowingly. |
| c-1, universe = `PAIRS_20` | **Derived** from the equicorrelated identity `1 + (P−1)ρ̄`, whose `P` and `ρ̄` index one set; the ruling confirms it. |
| c-2, Pearson / 190 unordered / equal weight | **Derived** from the same identity — with `C_EQUAL_WEIGHTING_IS_EXACT_ONLY_UNDER_EQUAL_PER_PAIR_VARIANCES` recorded as a **false** assumption of the committed form, not repaired. |
| c-3, `mean|r|` not `|mean r|` | **Human + ChatGPT ruling**, and the one limb whose favourable arm is knowable **unconditionally** — for every dataset, by the triangle inequality — where c-7's is knowable only **conditionally**, in the regime this family expects. It is a **conservative departure** from c-1's signed-mean identity, stated as such. |
| c-4, net realised PnL | **Cost layer ruled, on a reading of the dependence note**, and **which cell is ruled**. The note points `rho_x` at the cross-pair term of the daily portfolio sum, and that sum is net of the cell — but **c-6 rules a date index that is not that sum's date set** (`SHARPE_DAY_SET_AND_CORRELATION_DAY_SET_ARE_DIFFERENT_OBJECTS`), so the note cannot be carrying full derivational weight. The net series is adopted as the **better reading** of the note, and the departure c-6 makes from the same note is recorded rather than smoothed. *An earlier drafting called this limb derived.* |
| c-5, day rule | **Follows Q10-i**; no independent choice. |
| c-6, common full DESIGN date index | **Boundaries derived** from `DESIGN_START` / `DESIGN_END`; **the choice of a plain calendar index over a calendar-derived trading-day index is ruled**, with the 89 weekend dates recorded as its price. |
| c-7, idle = zero | **Human + ChatGPT ruling**, taken **with a knowable anti-conservative direction accepted in the open**. |
| c-8, fail closed | **Human + ChatGPT ruling** on the disposition; the **routing** into `failure_handling` is committed, and the collapse to a single trigger case is **derived** from c-6 + c-7. |
| c-9, span / freeze / no recalculation | **Span committed**; **freeze point and the no-recalculation bar are ruled**; the gate-3a reading is a **reading**. |
| c-10, the producing configuration | **Prohibition confirmed** — §4's R-10 already bars variant-shopping and hands the remedy to gate 3a. **Mechanism ruled**: compute `c_design` for **every** registered configuration before validation, freeze the map, select by `config_id` only. The registered set is **three `ev_min` points**, re-read at source, and §8.5.0's "nine configurations" is **withdrawn**. |

**Amendment classification.** c-1, c-2, c-4's cost layer, c-6's boundaries and c-9's
span are **derivations or confirmations** — they move no committed requirement.
Q10-i, c-3, c-4's cell, c-6's index choice, c-7, c-8 and c-9's freeze and
no-recalculation bars are **additions no committed source carries**, and whether such
additions need a contract-amendment procedure cannot be answered, because **no general
contract-amendment procedure is registered anywhere in this repository** —
`NO_GENERAL_CONTRACT_AMENDMENT_PROCEDURE_REGISTERED` being this packet's own token for
that absence, not a citation.
**`NR_L_AND_Q10_I_AMENDMENT_CLASSIFICATION_NOT_SETTLED`.**

**No favourable classification is asserted anywhere in this ruling.** **Three** limbs
are recorded as running **against** conservatism or as unestablished — c-7's
mechanism, c-2's false equal-variance assumption, and **c-6's common-idle frame**,
whose direction is not established either way; one, Q10-i, departs from the
repository's only precedent, breaks a committed test fixture, needs new machinery at
one of its two call sites, and rests on a **weaker** footing than §8.2.0 used for the
same manoeuvre; and **one whole limb is left open as a blocker**. Each is stated with
the ground that would defeat it.

##### What stays open, classified

Nothing below reopens the statistical contract; each is named against where it binds.

- **`C_INDEX_SET_NOT_RECORDED_IN_ANY_ARTIFACT`** — `effective_n()` still takes `c` as a
  bare `[0, 1]` scalar with no pair set, no date index and no day rule attached, and
  §10's R-9 requires the correlation **used**, not the set behind it. So c-1, c-6 and
  c-7 are **rules with no check**. Classified **`DEFERRED_PRODUCTION_CHECKABILITY`** —
  with the same carve-out Ruling ω-13 made for the calendar: **§5 already puts
  provenance IN as R-6's lightweight record**, so any output that reports `c` or
  `rho_x` **SHALL** record, in its R-6 reproducibility record: the **pair universe by
  name**; the date index's **membership rule and its cardinality** — every UTC calendar
  date from `DESIGN_START`'s date through `DESIGN_END`'s date inclusive, **310**; the
  **count of defined pairwise entries**, which must be **190**; the **per-pair count of
  non-idle dates**; the day-attribution rule; and the cost cell. **Bounds alone are not
  enough and an earlier drafting asked only for bounds** — every alignment c-6 forbids
  reports the *same* bounds, so a bounds-only record cannot distinguish the ruled
  construction from the route §8.5.2a ranks joint-first and calls **invisible**. These
  are parameters-and-config under §5's R-6, so no artifact field is invented.
  *And the classification is contested, recorded as contested rather than as obvious:*
  §8.4.13 makes a freedom whose favourable arm is knowable with no data **IN** and
  directs that an unclear classification is a **blocker, not a deferral**, and §5 puts
  R-9 and R-10 IN for reasons that are exactly this quantity. The deferral is therefore
  a **human + ChatGPT call on a contested classification**. Note also that
  `effective_n()`'s returned record carries `rho_x` but **not** `cross_pair_corr`, so
  `c` itself is absent from the only record that exists today.
- **`NR_L_PAIRWISE_COMPLETENESS_IMPLEMENTATION_PENDING`** — nothing in code or tests
  requires the 190 entries to be present, and `P = n_pairs = len(records)` is bounded
  above by twenty and **not below**, with `rho_x = 1 + (n_pairs − 1)·corr` using
  `n_pairs` rather than twenty. **The direction is stated, not just the gap**: every
  missing record lowers `rho_x` against a `c` measured over twenty entries, and
  therefore **raises `N_eff`**. Implementation and checkability — and the R-6 record
  above covers **`c`'s** pair universe, not **`P`'s**, so the two sets
  `P_AND_CORRELATION_INDEX_SET_NOT_BOUND` existed to bind still cannot be compared from
  it.
- **`C_HAS_NO_PRODUCER_AND_NO_ARTIFACT`** — no function computes `c`, no per-pair daily
  series constructor exists, and no artifact carries the value. Implementation. *And
  the interval it creates is named*: c-9 freezes the **method** now and defers the
  **code**, so there is a window in which the method is fixed and the implementation
  that materialises it is not, and c-9's bar reaches the enumerated method limbs, not
  the implementation. The concrete hazard is this ruling's own cited precedent —
  `pandas.DataFrame.corr()` defaults to pairwise-complete deletion, which is c-6's
  fourth forbidden candidate, and the fenced stage/compare implementation combines the
  intersection mask with three `0.0` substitutions. **§8.5.9's "whoever computes it
  first sets it" is not withdrawn for the implementation**, only for the method.
  **`C_IMPLEMENTATION_MAY_NOT_REINTRODUCE_A_FORBIDDEN_ALIGNMENT_OR_SUBSTITUTION_BY_LIBRARY_DEFAULT`.**
- **`EXIT_DAY_ATTRIBUTION_BREAKS_ONE_COMMITTED_TEST_FIXTURE`** — implementation.
- **`SHARPE_DAY_SET_AND_CORRELATION_DAY_SET_ARE_DIFFERENT_OBJECTS`** ·
  **`CORRELATION_DATE_INDEX_INCLUDES_NON_TRADING_CALENDAR_DATES`** ·
  **`IDLE_ZERO_FILL_DILUTES_CORRELATION_IN_THE_SPARSE_REGIME`** ·
  **`C_EQUAL_WEIGHTING_IS_EXACT_ONLY_UNDER_EQUAL_PER_PAIR_VARIANCES`** — accepted costs
  of the ruled construction, carried and **not** discharged. None of them is a
  remaining researcher freedom: each is a fixed consequence of a frozen rule, and no
  party may choose among them.
- **`MINIMUM_CALENDAR_IDENTITY_RECORD_REQUIRED_BEFORE_DATA_EXECUTION`** — Ruling ω-13's
  residual 5, carried forward unchanged and **not reopened**: a lightweight record
  identifying which frozen Calendar A instance governed a run is a **future execution
  prerequisite**, not a new `ω` contract decision, and no byte proof, evidence
  promotion, P/V route or production provenance chain is created here.
- **`Q10_III_STILL_OPEN`** — the annualisation factor is untouched and is not forced by
  anything above. **`EXACT_D_SELECTION_STILL_PENDING_UPSTREAM_AUTHORITIES`** likewise.

##### Status

**`NR_L_MINIMUM_RESEARCH_CONTRACT_RULED_PENDING_IMPLEMENTATION_AND_DESIGN_MEASUREMENT`.**
`c`'s statistical semantics are fixed: the universe, the coefficient, the entry set,
the weighting, the absolute-value placement, the series, the cost layer, the day
attribution, the date index, the idle rule, the undefined-case disposition, the span
and the freeze. **No `c` is calculated, no correlation is computed, no daily PnL is
constructed and no data is read.** Implementation and checkability remain, and
**`PRODUCTION_READINESS_NOT_CLAIMED`**.

**`CLOSURE_CLAIM_WITHHELD`** — attempted a **third** time at §8.7.6 and grounded on a review section that did not yet exist; withheld then under **`CLOSURE_CLAIM_REQUIRES_COMPLETED_REVIEW_AND_NO_UNRESOLVED_MATERIAL_BLOCKER`** (§8.8.0 — the earlier same-round prohibition is **withdrawn as over-broad**). *The separate independent round has since run: §12.17 records **full coverage on the assigned scope, both roles returning**, so that rule's review condition is now **met**. Closure is still **NOT** taken, on a different ground — §8.9.6 records **seven live material blockers**, and **`M15_MINIMUM_RESEARCH_STATISTICAL_CONTRACT_NOT_CLOSED_MATERIAL_BLOCKERS_LIVE`**.* The history is kept rather than tidied: this
paragraph first said "**No** NR-L Minimum Research Gate blocker remains", that was
**withdrawn as false**, it was reinstated after c-10 and withdrawn again, and a **third**
attempt at §8.7.6 rested on a phantom review citation. Every item left is
implementation, checkability, or an accepted cost of a frozen rule — and
by Ruling ω-13's boundary a future finding reopens this contract **only** if it names
a remaining freedom capable of moving `c`, `N_eff`, the event sequence or experiment
selection, with the classification a **human + ChatGPT** call and an unclear case
defaulting to blocker.

**`NR_L_REQUIRES_HUMAN_CHATGPT_RULING`**, **`NR_L_PARTIALLY_DERIVED_BLOCKED_BY_Q10_I_AND_HUMAN_RULINGS`**
and **`MEAN_ABS_PAIRWISE_CORR_NOT_YET_ESTIMATED_DESIGN_DATA_ONLY`**'s *pending-ruling*
limb are **HISTORICAL — SUPERSEDED BY HUMAN + CHATGPT RULING**. §8.5.1–§8.5.11 are
retained as the material this ruling was taken on, superseded where they say a limb is
open, and **§8.5.10 remains a recommendation that this ruling replaces** — it may not
be cited as authority for any limb.

#### 8.5.1 What the committed sources actually say

Reconstructed by reading the sources.

| Finding | Source |
| --- | --- |
| `rho_x = 1 + (P − 1) · mean_abs_pairwise_corr`; with `P = 20` ruled, `rho_x = 1 + 19c` | spec `cross_pair_discount`; §8.3.0 |
| The **only** committed definition: "`mean_abs_pairwise_corr` = mean **absolute** pairwise correlation of per-pair **daily PnL** series, estimated on **DESIGN data only** and **frozen**. Independent pairs ⇒ `rho_x → 1`." | spec `cross_pair_discount` |
| The span is fixed and the prohibition is explicit: "**DESIGN span only (2025-04-25..2026-02-28); never validation/holdout; frozen once and recorded.**" | spec `correlation_estimation_data` |
| The contract requires the discount to exist: "Cross-pair dependence — fixed PAIRS_20 (no selection); per-currency exposure metric; **correlation discount in effective-N**" | prereg **§12 risk register, row 2** — *not* §16's Ruling 2, which is the dataset-spans ruling; §16's effective-N ruling is **Ruling 11**. An earlier drafting cited it as a §16 "frozen row" |
| The prereg's own draft: "discount cross-pair by an **average-correlation factor estimated on design data**" — expressly part of the "Draft estimator (for the design audit to fix)" | prereg §9 |
| **`c` is a bare caller scalar.** `cross_pair_corr` is validated only as a finite number in `[0, 1]`; **no pair-set identity is attached in the call or in the returned record** | `effective_n.py` `_require_unit_fraction`, `effective_n()` |
| **Negatives are refused, and that is an input constraint only.** A committed test asserts `cross_pair_corr = −0.1` raises, and `_require_unit_fraction` admits only a finite number in `[0, 1]`. It constrains what may be **supplied**; it specifies **nothing** about the statistic, and NR-L2's absolute-value placement is not decided by it. *An earlier drafting said a negative mean "must be entered as its absolute value", which is a disposition no committed source carries and which contradicted §8.5.4; withdrawn.* Conservatism, where it holds, comes from the spec's own "mean **absolute** pairwise correlation", and it bounds the **equicorrelated** inflation under equal weights and equal per-pair variances — neither of which is registered (NR-L2) | `effective_n.py` `_require_unit_fraction` (118–130); `tests/m15_gate3a/test_effective_n.py`; spec `cross_pair_discount` |
| **No correlation is computed anywhere in the M15 package.** `scripts/m15_gate3a/` contains no correlation function, no matrix and no series builder, and `scripts/ml_step4/` contains none either. Every `.corr` / `corrcoef` / `pearsonr` / `spearmanr` call in the repository sits in **fenced legacy stage/compare code** — `scripts/compare_multipair_*.py` (M1-lineage Phase-9), `scripts/stage22_0a_scalp_label_design.py`, `scripts/stage25_0e_f3_eval.py`, and the `scripts/stage26_0*_eval.py` family via `scipy.stats` — all inside C-8 / Ruling 13's fenced "archived Phase 9.x numerics … stage/compare logs", none of it M15 machinery. *An earlier drafting said the `compare_multipair` family was the **only** such site; that enumeration was wrong and is corrected. The conclusion is unchanged.* | repo-wide grep |
| **The object `c` is defined on does not exist in committed code.** `scripts/ml_step4/metrics.py` has `daily_portfolio_pnl`, which "**Sum[s] net per-trade PnL by UTC day**" **across all pairs** into one portfolio series. There is **no per-pair daily PnL series** anywhere | `scripts/ml_step4/metrics.py` |
| The day a trade belongs to is a single field, `MetricTrade.day`, documented only as "`# UTC calendar day 'YYYY-MM-DD'`" — **entry or exit is not stated** | `scripts/ml_step4/metrics.py` |
| `TRADING_DAY_DEFINITION = "utc_calendar_date"` — consistent with Ruling Q10(ii)'s day identity | `scripts/ml_step4/contract.py` |
| The same artifact asserts `no_strategy_metrics_computed_at_gate3a: true` while defining `c` on **daily PnL**, which is a strategy metric | spec |
| The dependence note: "Daily portfolio Sharpe is computed on UTC-day portfolio sums; days are treated as the Sharpe sampling unit but are **correlated across pairs**. `rho_x` captures the cross-pair term" | spec `daily_aggregation_dependence_note` |

**So the shape of the conflict is precise.** The **span** is committed and closed. The
**symbol** is committed. Everything between them — which pairs, which statistic, which
series, which day, what an idle day is, what an undefined pair does, and when the
value is fixed — is **unregistered**, and the object the definition names has **no
constructor in this repository**.

#### 8.5.2 Why this is now the largest remaining freedom

`rho_x = 1 + 19c` once `P` is ruled, so `c` carries the whole cross-pair deflator —
though not, as §8.5's opening records, the whole of the effective-N arithmetic.
§0.3's budget at the frozen minimum span gives `c ≤ 0.177` when `ω = 0` — the bottom
**17.7%** of `c`'s domain — and at the document's diagnostic `c = 0.3`,
`rho_x = 6.70` **exceeds the entire 4.36 budget on its own**.
*`NON_NORMATIVE_DIAGNOSTIC_ONLY`.* §8.3.0 already recorded the magnitude of the lever from the other side. Against
§8.3.2's closed form **at this document's diagnostic `c = 0.3`**, with `P` at twenty
throughout: a `c` of `0.15` buys `×1.74` on `N_eff`, and a `c` of `0.05` buys `×3.44`
— **the latter more than the `20 → 10` pair shrink NR-K forbids** (`×1.81`).
*An earlier drafting omitted the baseline and attached "more than" to both figures,
which is false of the first (`×1.74 < ×1.81`).*

#### 8.5.2a The `c`-side adversarial properties, ranked — the section §8.4.11 has and this side lacked

The `ω` side enumerates A-ω-1…A-ω-8, **splits them into two kinds** and sizes the
largest. The `c` side named four adversarial tokens scattered across four subsections
and ranked none. That asymmetry is closed here. Every figure is arithmetic on the
committed formula, **`NON_NORMATIVE_DIAGNOSTIC_ONLY`**, and no data is read.

**The two kinds, because the difference decides what a check could catch.** Some
routes **move the reported `c`**; others leave the reported `c` *correct* while
changing **what it is a correlation of** — and no check on the reported value can see
those. `c` enters the record only as the derived `rho_x`, and §10's R-9 requires the
correlation **used**, not the index set behind it.

Committed bounds: `rho_x = 1 + 19c` with `c ∈ [0, 1]`, so `rho_x ∈ [1, 20]` and the
end-to-end lever on `N_eff` is **20×**.

| Rank | Route | Reachable range | Kind |
| --- | --- | --- | --- |
| **1=** | **NR-L2, absolute-value placement.** `mean(|ρ|) ≥ |mean(ρ)|` by the triangle inequality, with equality only if all 190 entries share a sign — so `|mean(·)|` is the `N_eff`-favourable reading **for every dataset**, knowable with no data | whole domain, one-directional | moves the reported `c` |
| **1=** | **NR-L1 + NR-L6(c) + NR-L8, entry-set shrinkage.** Taking the lowest-`\|ρ\|` entries drives `c` toward the minimum entry; `c` carries no index-set identity in the call or the record | whole domain; `c` 0.30 → 0.05 is **×3.44** on `N_eff` (§8.5.2), bound **×20** | **invisible** — the reported `c` stays correct |
| **3** | **NR-L7, post-hoc recalculation.** "Nothing committed says it is [forbidden]" — a **meta-lever** spanning every other limb, because it permits re-selection *after* observing `N_eff` | every other limb's range | invisible |
| **4** | **NR-L5, idle days** | large in this regime (§0.6's ~0.56 trades/pair/day), but the direction is **conditional** (§8.5.7), which caps blind exploitation | moves the reported `c` |
| **5** | **NR-L3, cost layer** | `net = gross − cell × daily trade count`, so the shift is proportional to **activity**; direction indeterminate | moves the reported `c` |
| **6** | **NR-L4, day attribution** | bounded — a 6-hour horizon straddles a UTC midnight for a bounded fraction of trades — and blocked by Q10(i) regardless | moves the reported `c` |
| **7** | **NR-L2, diagonal inclusion** | **the only limb bounded exactly**: the 400-entry mean is `0.05 + 0.95m`, so at most `+0.05`, and always *conservative* | moves the reported `c` |
| **8** | **NR-L7, span** | **zero** — committed and closed | — |

**Two structural points the ranking makes.** First, **the two largest routes are the
two the `ω` side gave a dedicated section to**, and on this side one of them —
entry-set shrinkage — is *undetectable by anything §10 requires*. Second, **NR-L2's
absolute-value placement has the property A-ω-5 treated as most serious on the `ω`
side**: its favourable direction is knowable **before any data**, so a pre-data freeze
does not protect it. There is **no `C_STATISTIC_MUST_NOT_BE_SELECTED_TO_MINIMISE_RHO_X`
token** to match `OMEGA_CLOCK_SUBSTRATE_MUST_NOT_BE_CHOSEN_TO_MINIMISE_RHO_H`, and this
packet does not create one — it records the gap.
**`NO_PROHIBITION_BINDS_THE_CHOICE_OF_CORRELATION_STATISTIC`** — **closed by Ruling
c-3**, which supplies `C_STATISTIC_MUST_NOT_BE_SELECTED_TO_MINIMISE_RHO_X`.

#### 8.5.3 NR-L1 — which pair set enters `c`?

**The question `P = 20` makes urgent.** The candidates:

| Candidate | Note |
| --- | --- |
| **Full frozen `PAIRS_20`** | The only one that makes `P` and `c` two statistics of **one** index set, which is what the equicorrelated form `1 + (P−1)c` assumes (§8.3.8) |
| Only pairs with a **defined** correlation | Interacts with NR-L6; a pair dropped for undefinedness silently leaves the index set |
| Only pairs **with trades** | The `ω`-side analogue was closed by Rulings ω-5/ω-6; nothing closes it here |
| Only **non-zero-variance** pairs | Same shape as the above, reached through NR-L6 |
| Another committed set | None found |

**The adversarial route, named as a first-class property:**
**`KEEP_P_20_BUT_COMPUTE_C_ON_A_FAVOURABLE_SUBSET`.** `P` is pinned; `c` is a bare
scalar with **no pair-set identity in the call or the record** (§8.5.1), and §10's
R-9 requires the correlation **used** to be reported, not the set it was estimated
over. So the correlation-side universe can shrink while `P` stays at twenty, and
**nothing committed detects it**. §8.3.0 records this as
`OUTCOME_DRIVEN_CORRELATION_SET_IS_THE_SAME_LEVER_IN_THE_OTHER_FACTOR` and assigns it
here.

**One committed clause may already bar it, and the ruling should say whether it
does.** Prereg §3.2's R-2a-compliance clause bars "inclusion/exclusion decisions
**anywhere in this family**" — the same clause that closes §8.3.5's ground G. Whether
estimating a *statistic* over a subset is an "inclusion/exclusion decision" in that
clause's sense is a **contract reading**, not a source fact, and this packet does not
make it. If it is, NR-L1 is a **confirmation**; if it is not, NR-L1 is a choice.

**And the form cares.** §8.3.8 records that `1 + (P−1)c` is an equicorrelated
variance-inflation factor whose `P` and `c` are two statistics of **one** set, and
that §0.6 already shows `PAIRS_20` is **not exchangeable** — 40 currency legs from 8
currencies, 88 of 190 pair-pairs sharing a leg. Applying a `c` estimated over a
subset to `P = 20` is coherent only under an exchangeability the document has already
recorded as false. **`P_AND_CORRELATION_INDEX_SET_NOT_BOUND`** was the open token —
**closed by Ruling c-1**, which derives the single-index requirement from the
equicorrelated form rather than leaving it to a contract reading.

#### 8.5.4 NR-L2 — which statistic, over which entries, with what weighting?

The committed phrase is "**mean absolute pairwise correlation**". Unregistered:

- **The correlation coefficient itself** — Pearson, Spearman, or another. No committed
  source names one, and **no correlation is computed anywhere in the M15 package**, so
  there is no implementation to read the answer off.
- **Which entries the mean is taken over.** For `P` pairs there are `P(P−1)/2 = 190`
  unordered pairs-of-pairs and `P(P−1) = 380` ordered off-diagonal entries. Because a
  correlation matrix is symmetric, those **two give the same mean** — each unordered
  value is counted twice with the same magnitude — so the live choice is whether the
  **diagonal** enters: the 400-entry mean is `0.95·m + 0.05` against the off-diagonal
  mean `m`, larger for every `m < 1`, so including it inflates `c` toward
  conservatism. *An earlier drafting said all three readings "change the value", which
  is false for two of the three; withdrawn.* Which entry set is intended is
  nonetheless **unregistered**, and this packet does **not** choose.
- **The weighting.** Equal weight per pair-of-pairs is the natural reading of "mean";
  nothing says so. The `ω`-side analogue was settled by Ruling ω-4 and **that ruling
  does not reach here**.
- **The absolute value's placement.** "Mean absolute" reads as `mean(|ρ_ij|)`;
  `|mean(ρ_ij)|` is a different quantity and is smaller whenever signs differ. The
  first is the **more** conservative of the two, and both dominate the signed mean the
  equicorrelated form actually takes.

**And it may not be inferred from a function name.** No committed source names a
coefficient, `scripts/m15_gate3a/` computes no correlation, and the only correlation
code in the repository is C-8-fenced stage/compare lineage — so there is nothing to
read the answer off, and nothing there may be adopted.

**Recorded, not resolved:** `_require_unit_fraction` refuses negative input, so
whatever is computed must be non-negative when supplied — an *input* constraint, not
a specification of the statistic.

#### 8.5.5 NR-L3 — what series is correlated?

The spec says "per-pair **daily PnL** series". Unregistered, and the object does not
exist:

- **No per-pair daily series is constructed anywhere.** The nearest committed
  function, `daily_portfolio_pnl`, sums **across pairs** into a single portfolio
  series — the opposite decomposition.
- Candidates the ruling must choose between: per-pair **daily realised PnL**;
  per-pair **daily returns**; **signal** or model-score series; **strategy** returns;
  another committed quantity. **Portfolio performance is a different object from
  the one the definition names**, and substituting it would collapse every pairwise
  correlation to `1`. Recorded as a reading of the committed definition ("per-pair
  **daily PnL** series"), not as a rule this packet makes.
- **PnL in what units, and net of what? — and this is the sharpest limb of NR-L3.**
  The committed decomposition is explicit about two cost layers and silent about which
  the correlation takes. `MetricTrade.gross_pnl_pips` is documented as "**spread
  embedded once, before the flat slippage cell**"; `net_pnl(trade, cell_pips)` returns
  `gross_pnl_pips − cell_pips`. So there are at least three candidate series — **gross
  (spread embedded, slippage not)**, **net (spread and slippage both applied)**, and a
  **normalised** variant (per-pair pip-value or volatility scaling, which no committed
  source defines). They are not interchangeable: subtracting a *constant* cell from
  every trade shifts each pair's daily series by an amount proportional to that pair's
  daily **trade count**, so the cost layer enters the correlation through activity, not
  through price. The choice therefore moves `c`, and **this packet does not make it**.
  **`CORRELATION_SERIES_COST_LAYER_NOT_REGISTERED`.**
- **The gate-3a contradiction stands and is not resolved here.** The same artifact
  asserts `no_strategy_metrics_computed_at_gate3a: true` while defining `c` on daily
  PnL, which is a strategy metric. **`CORRELATION_SERIES_IS_A_STRATEGY_METRIC_AT_A_GATE_THAT_FORBIDS_THEM`.**

#### 8.5.6 NR-L4 — day attribution, and its dependency on Q10(i)

A per-pair daily series needs each trade assigned to a day. `MetricTrade.day` is a
single field documented only as "UTC calendar day"; **whether that is the entry day or
the exit day is exactly Q10(i), which is open** (§8.2.8). With a 24-bar horizon a
trade's entry and exit routinely fall on different UTC dates, so the two attributions
produce **different daily series and therefore different `c`**.

**`NR_L_DAY_ATTRIBUTION_DEPENDS_ON_Q10_I` — SUPERSEDED BY §8.5.0**, which resolves
Q10(i) and NR-L4 in **one** ruling rather than either by accident. As the packet
stood: this packet **does not resolve Q10(i)**, and NR-L must not resolve it by
accident: choosing a day rule for `c` would settle the
Sharpe series' day rule by the back door, since §8.2.8 records both limbs as running
on **the same daily series**. **NR-L cannot be fully ruled before Q10(i)**, and that
is stated here rather than worked around.

*The day identity itself is settled* — Ruling Q10(ii) fixes it as the UTC calendar
date, and `TRADING_DAY_DEFINITION = "utc_calendar_date"` agrees. What is open is
**which** day a straddling trade belongs to, not what a day is.

**The field's contract is silent; the repository's only two constructors are not.**
`scripts/ml_step4/body.py` builds every `MetricTrade` from the **entry** bar —
`_trades_from_accepted` takes `trading_day_utc(bars_by_pair[pair][t["entry"]]["ts"])`
and `_trades_with_days` takes `day_by_index[pair][t["entry"]]`. That is **unadopted
M1-lineage code** (prereg §11, "reusable after audit/wrapping"), so it is a
**precedent and not an authority**: it does not close Q10(i), and it is recorded here
only so the ruling is not taken as if the repository were silent — a ruling for the
**exit** day would depart from every constructor that exists. An earlier drafting
omitted this. **And it may not be used the other way either**: the precedent is
unadopted M1-lineage code, so it must **not** be cited as settling Q10(i) or as
supplying NR-L4's answer by default. `NR_L_DAY_ATTRIBUTION_DEPENDS_ON_Q10_I` stands.

#### 8.5.7 NR-L5 — idle days

A pair-day with no trades must be represented somehow, and the choices are not
equivalent: **zero** · **missing / excluded pairwise** · **excluded listwise** ·
**carry-forward** · another committed rule. None is committed.

**It matters most in exactly the regime this family expects.** §0.6 records the
projected rate at roughly **0.56 trades per pair per day**, so most pair-days are
idle, and **where pairs' activity patterns are close to independent**, idle days
entered as zeros pull `|corr|` toward zero — the estimator then **understates
dependence most in exactly the sparse regime this family expects**, which is the
anti-conservative direction. *The direction is conditional, not unconditional: where
activity co-occurs the dilution does not arise, and with non-zero daily means a
common-idle day contributes positively to the covariance.* Recorded as a conditional
direction, not a measurement; `NON_NORMATIVE_DIAGNOSTIC_ONLY`.

**And a daily resolution is coarse for a 6-hour horizon** — §0.6 already records that
too. Whether the correlation should be measured on a daily series at all is a
question the committed definition forecloses, and it is noted only so the ruling
knows what it is accepting.

#### 8.5.8 NR-L6 — undefined pairwise correlations

Cases: **zero variance** in one leg; **insufficient overlapping observations**; an
**all-zero** series; **no common dates**. For each, the disposition must be chosen —
**fail closed and halt** · **exclude that pair-of-pairs from the mean** · **substitute
a conservative value** · another rule.

**The direction is what makes this load-bearing.** Silently dropping undefined
pairs-of-pairs **removes exactly the pairs least likely to co-move**, which lowers
`c`, lowers `rho_x` and **raises `N_eff`** — and it also shrinks the effective index
set behind NR-L1's back. This is the same shape as the zero-event route Rulings ω-5
and ω-6 had to dispose of on the `ω` side, and the analogy is offered as *structure*,
not as authority.

**The options, stated so the ruling has something to choose between.** **(a) Fail
closed** — an undefined pairwise entry halts, with the collision §8.5.10 limb 8
records. **(b) An explicit conservative treatment** — a stated substitute value,
declared as a convention and marked inert or conservative, on the shape Rulings
ω-5/ω-6 used. **(c) Exclude the entry and record the exclusion** — offered for completeness and
**flagged, not endorsed**. It is an instance of
`KEEP_P_20_BUT_COMPUTE_C_ON_A_FAVOURABLE_SUBSET` at the **entry** level: the exclusion
removes exactly the entries least likely to co-move, so it lowers `c`, lowers `rho_x`
and **raises `N_eff`** whether or not it is reported — **reporting cures the
visibility half of the objection and not the direction half**, and an earlier drafting
said "the objection is to silence, not to exclusion as such", which silently narrowed
this packet's own two-part objection to its weaker half. It has **no `ω`-side
precedent**: Rulings ω-5 and ω-6 both *retain* the pair, and
`MEAN_OVERLAP_PAIR_SET_MUST_NOT_SHRINK` is the token on that side. And the record it
depends on **does not exist**: §10's R-9 requires the correlation *used*, not the
entry set it was estimated over, and §8.5.9 records that no artifact carries `c`
today. A ruling that takes (c) must therefore also create that reporting surface —
NR-L7's open "where it is recorded" limb — and must state that it is accepting the
anti-conservative direction knowingly. **(d) Another committed rule** — none was found.

**No numerical substitute is invented here — and Ruling c-8 invents none either**,
taking (a) fail closed and routing it into the spec's committed `failure_handling`
rather than into a new state. `c = 1`, `c = 0` and `c = 0.5` are each
**refused** as packet-supplied values; committed authority supplies none, and the
`ω`-side precedent is a *structure* — an explicit, stated, non-halting disposition —
not a number. **`UNDEFINED_CORRELATION_SEMANTICS_PENDING_HUMAN_CHATGPT_RULING`.**

**And a registered pair that cannot produce a valid correlation may not be silently
dropped from `c`** on any of the grounds that create the case — zero variance, no
trades, insufficient shared dates, an all-zero daily series, or missing observations.
Which of (a)–(d) applies is the ruling's; **the silence is what is foreclosed**.

#### 8.5.9 NR-L7 — source span and freeze point

**The span is committed and closed, and this packet does not reopen it.** "DESIGN span
only (2025-04-25..2026-02-28); **never validation/holdout**; frozen once and
recorded." An earlier draft of this document once listed training/validation/holdout
as candidate sources; that was **withdrawn as reopening a committed prohibition**
(§8.1.9) and it is not revived here.

What remains open:

- **Which DESIGN slice**, given that the span is exploratory — a statement about the
  span's *extent*, not about any authorised access; Q3, Q4 and §11 are unchanged.
- **When the value is calculated**, and **when it is frozen** — "frozen once and
  recorded" fixes that it is frozen, not the moment.
- **Where it is recorded**, and in what artifact. No artifact carries it today.
- **Whether recalculation after seeing downstream results is forbidden.** Nothing
  committed says it is. The `ω` analogue is Ruling ω-10; **NR-K's non-reduction
  clause and Ruling ω-10 both stop short of `c`**, and §8.3.0 says so expressly.
- **Who computes it.** As with `ω`, there is no producer, so **whoever computes it
  first sets it**.

#### 8.5.9a NR-L8 — common date alignment

**Added to separate the *frame* from the *fill*.** NR-L8 asks which dates an entry
rests on; NR-L5 asks what an idle pair-day carries. NR-L5's committed candidate list
**conflates them** — "excluded listwise" and "missing / excluded pairwise" are
alignment rules, not fill values — so NR-L8 exists to pull them apart, **not** because
NR-L5 is silent. *An earlier drafting said NR-L5 and NR-L6 were "under-determined
without it", which over-states it for NR-L5: the two overlap rather than one being a
function of the other.* A pairwise
correlation needs the two series placed on **one date index**, and no committed source
says which. The candidates are not equivalent, and each interacts with a question
already open:

| Candidate | What it does | Interaction |
| --- | --- | --- |
| **Full DESIGN UTC date index** | every calendar date in the span, for every pair | forces NR-L5 to supply a value for every idle pair-day; no pair is ever short of observations, so NR-L6's "insufficient shared dates" case cannot arise |
| **Intersection of active dates** | only dates on which **both** pairs traded | manufactures NR-L6's "no common dates" case for sparse pairs, and shrinks the sample pairwise — a **different `n` for every entry** |
| **Union with zeros** | union of the two pairs' active dates, zero-filled | a middle case: fewer idle days than the full index, more than the intersection |
| **Pairwise-complete observations** | per-entry deletion on whatever the series carry | the classic pairwise-deletion route; each entry rests on its own date set |
| **Another committed authority** | — | none found |

**Why this cannot be left implicit.** The alignment decides *which* undefined cases
exist at all, so NR-L6 is not independent of it any more than it is of NR-L5; and
under the intersection and pairwise-complete readings **the pairs least likely to
co-move are also the pairs with fewest shared dates**, so a rule chosen for
convenience there reproduces `KEEP_P_20_BUT_COMPUTE_C_ON_A_FAVOURABLE_SUBSET` **at
the entry level rather than the pair level** — a favourable subset assembled without
ever removing a pair. **`CORRELATION_DATE_ALIGNMENT_NOT_REGISTERED`** ·
**`ALIGNMENT_MUST_NOT_CREATE_AN_UNREGISTERED_FAVOURABLE_SUBSET`.**

**A deterministic index is what closes it.** Whether the ruling picks the full DESIGN
index or another rule, the alignment must be **deterministic and declared before the
data**, so that the entry set behind `c` is fixed rather than discovered. This packet
records the requirement's *shape* and **chooses no candidate**; **Ruling c-6 chooses
the full DESIGN UTC calendar-date index**, and records the 89 weekend dates and the
Sharpe-day-set mismatch as its price.

#### 8.5.10 Recommendation — offered, not applied, and not a ruling

**Superseded by §8.5.0, which is the ruling. Nothing in this subsection may be cited
as authority for any limb**, including where the ruling happens to agree with it —
and the ruling departs from it in two places worth naming: limb 8 **referred** the
undefined-correlation question and **c-8 rules it**, and limb 7 offered equal
weighting as "the natural reading of *mean*" where **c-2 derives it** from the
committed form's own algebra. As it stood: offered so the ruling has something to
accept, amend or reject. **None of it is
applied, and no limb here may be cited as decided.**

1. **The correlation universe stays tied to the frozen `PAIRS_20`**, so that `P` and
   `c` index one set and the equicorrelated form is coherent — **it should not silently
   shrink below the frozen twenty**, and in particular not to a handful of
   low-correlation pairs while `P` stays at 20 (§8.5.3).
2. **One fixed statistical method**, fixed before any downstream data — the
   coefficient, the entry set, the weighting and the placement of the absolute value.
3. **Per-pair daily PnL under a fixed day attribution**, with the **cost layer named**
   (§8.5.5) — and the attribution itself waits on Q10(i).
4. **A common, deterministic DESIGN-span date index** (NR-L8), declared before the
   data, so the entry set behind `c` is fixed rather than discovered.
5. **Idle-day treatment fixed before data** (NR-L5) — see the declared silence below.
6. **Source DESIGN-only**, as already committed, with the slice, the calculation
   moment, the freeze moment and the record location all pinned explicitly.
7. **Equal weighting of the required pairwise entries** unless committed authority says
   otherwise — offered as the natural reading of "mean", **not** as derived, and
   expressly not carried over from Ruling ω-4, which reaches `ω` and not `c`.
8. **Pairwise undefined cases are REFERRED, not recommended — the only limb here
   with no recommendation.** Silent dropping is anti-conservative and shrinks the index
   set invisibly; a flatly fail-closed rule is **unworkable**; and this packet has no
   third answer. An earlier drafting put "fail closed" in the headline while the same
   limb went on to demonstrate that it halts the family on a normal outcome — a limb
   that refutes itself is a **referral**, not a recommendation.
   **The collision, named rather than left for the ruling to find.** A registered pair that fires nothing is a **normal outcome** (§8.3.0) and
   produces exactly NR-L6's zero-variance / all-zero case, so a flatly fail-closed
   limb 8 **halts the family on a normal outcome** — the same shape
   `ZERO_EVENT_OMEGA_MUST_NOT_HALT_A_NORMAL_OUTCOME` records on the `ω` side, and that
   Rulings ω-5/ω-6 had to dispose of *without* a halt. Dropping is anti-conservative;
   halting is unworkable. **This packet has no third answer and does not offer one**;
   the ruling must supply it, and the `ω` side's disposition — an explicit, stated,
   non-halting value — is the structure it may find useful, offered as structure and
   **not** as authority.
9. **No pair selection to reduce `c`, and no post-hoc removal or re-estimation**, on
   the same principle as §8.3.0's non-reduction clause — offered **by analogy and
   expressly not derived from it**.
10. **No validation or holdout correlation**, which is committed already, and
    **`c` frozen once from DESIGN only**.
11. **`C_METHOD_AND_SOURCE_WINDOW_FROZEN_BEFORE_DOWNSTREAM_OBSERVATION`** — the
    method *and* the source window fixed before anything downstream is observed, so
    that neither can be selected on its effect.

**And four of the eight questions are deliberately left unadvised — said here so
the silence is not read as agreement.** NR-L3 and NR-L4 because of
`NR_L_DAY_ATTRIBUTION_DEPENDS_ON_Q10_I`; **NR-L6** because this packet has no third
answer (limb 8). **NR-L5 because this packet can name the
direction (§8.5.7) but no committed source supplies a convention, and naming one here
would be inventing a statistic.** That asymmetry is worth stating plainly: the `ω`
side's empty-record cases needed **two** dedicated limbs (Rulings ω-5 and ω-6) exactly
because a value reached by absence runs permissive — and on the `c` side, saying
nothing about idle days **is** the zeros default. The ruling must decide NR-L5
explicitly, and §8.5.7 is the material it should decide on.

**Where committed authority may already supply a limb**, the ruling should say so
rather than treating it as a choice: **limb 6's span and limb 10** are **committed**;
limb 1 **may** be carried by prereg §3.2's compliance clause (§8.5.3); limbs 2, 3, 4,
5, 7, 8, 9 and 11 have **no committed source** that this packet could find. *An earlier
drafting said "limb 3's span and limb 6", which was the pre-renumbering mapping and is
materially wrong under the new list — limb 3 is now the PnL/day-attribution limb, which
this packet expressly records as **not** committed.*

#### 8.5.11 Why this is not derivable, and what it waits on

**Not derivable.** There is one committed definition of `c` and it names a span, a
symbol and an object — "per-pair daily PnL" — whose **constructor does not exist in
this repository**. The coefficient, the entry set, the weighting, the series, the day
rule, the idle-day rule, the undefined-case rule and the freeze moment are each
unregistered, and no implementation exists to read any of them off.
**`NR_L_REQUIRES_HUMAN_CHATGPT_RULING`** — **HISTORICAL, superseded by §8.5.0.**
*And the ruling narrowed this paragraph: the coefficient, the entry set and the
weighting turned out to be **derivable** after all, from the equicorrelated identity
`1 + (P−1)ρ̄` the committed formula is (Ruling c-2); what genuinely was not derivable
is the absolute-value placement, the cost cell, the date index, the idle rule, the
undefined-case disposition and the freeze moment.*

**And it had a hard dependency, which is how the ruling was taken.**
`NR_L_DAY_ATTRIBUTION_DEPENDS_ON_Q10_I` — NR-L3 and NR-L4 could not be closed while
Q10(i) was open, because both turn on the same daily series. **§8.5.0 closes them
together in one bundled decision rather than closing NR-L around the gap**, which is
what this paragraph was asking for. The ruling may close NR-L1, NR-L2 and NR-L7
independently.
**NR-L6 depends on both NR-L5 and NR-L8** — which undefined cases arise at all is
decided by the idle-day convention *and* by the date alignment: zeros manufacture the
zero-variance and all-zero cases, an intersection alignment manufactures "no common
dates", and pairwise-complete deletion manufactures "insufficient overlapping
observations". So the order within NR-L is **NR-L8 → NR-L5 → NR-L6**, and an earlier
drafting listed NR-L6 as independent of NR-L5 and omitted NR-L8 entirely.

**The NR-L8 ↔ NR-L5 dependency runs both ways, and the ordering is a convention.**
Choosing NR-L5 = "excluded listwise" *is* choosing NR-L8 = intersection; the two
determine each other, so fixing NR-L8 first **forecloses part of NR-L5's candidate
list**, which §8.5.7 still presents as five live options. `NR-L6 → {NR-L5, NR-L8}` is
correctly one-directional. **`NR-L8 → NR-L5 → NR-L6` is therefore a sequencing
convention that keeps the frame prior to the fill — not a claim that NR-L5 is a
function of NR-L8** — and a ruling taking NR-L8 first should state which NR-L5
candidates it thereby closes. And the ruling
**cannot** close NR-L3/NR-L4 without also deciding Q10(i); doing so implicitly would
settle the Sharpe series' day rule by the back door.

**The `ω` / calendar dependency is now conceptually closed, and NR-L is unaffected by
that.** Rulings ω-11 and ω-12 settle `ω`'s substrate, its authority, its freeze
ordering and its immutability. **What remains open on the overlap side is unchanged and
is not small** — the role-span truncation limb, the rollover/holiday membership outcome,
the event-set residual, `OVERLAP_PER_RECORD_PROVENANCE_UNBOUND`, the amendment
classification, and `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` with neither
artifact in existence. *An earlier drafting said "nothing upstream of NR-L remains open
on the overlap side", which is false against §8.4's own status; **withdrawn**.* What
**is** settled is that **nothing committed routes any of it to `c`**: the calendar governs *slot membership*, and `c` is a correlation of per-pair **daily
PnL** — a different object on a different index — and none of NR-L8's five committed
alignment candidates or NR-L5's five idle-day candidates invokes the calendar
authority. `ONE_FROZEN_CALENDAR_VERSION_GOVERNS_BOTH_OMEGA_AND_COVERAGE` binds `ω` and
coverage, **not** `c`, and NR-L's date alignment (NR-L8) is its own question.

**Status — HISTORICAL.** **`NR_L_PARTIALLY_DERIVED_BLOCKED_BY_Q10_I_AND_HUMAN_RULINGS`**
was unchanged by Ruling ω-12 and is **superseded by §8.5.0**, which closes the packet
and Q10(i) together. As the packet stood: the formula and the span were committed and
re-verified; **nothing else was**, and two of the eight questions could not close in
that sequence at all. Closure was not forced — the packet stopped where the authority
stopped, and the bundled ruling is what moved it.

**Q10(iii) is kept out of it.** The annualisation factor bears on the Sharpe limb, not
on `c`, and no committed source makes it a dependency of the correlation. It stays a
separate open question (§8.2.8) and NR-L neither needs nor settles it.

**Open tokens the packet carried — all HISTORICAL, closed by §8.5.0** except where
noted: `NR_L_REQUIRES_HUMAN_CHATGPT_RULING` ·
`NR_L_PARTIALLY_DERIVED_BLOCKED_BY_Q10_I_AND_HUMAN_RULINGS` ·
`KEEP_P_20_BUT_COMPUTE_C_ON_A_FAVOURABLE_SUBSET` ·
`P_AND_CORRELATION_INDEX_SET_NOT_BOUND` ·
`OUTCOME_DRIVEN_CORRELATION_SET_IS_THE_SAME_LEVER_IN_THE_OTHER_FACTOR` (all three
closed by Ruling **c-1**) ·
`CORRELATION_SERIES_IS_A_STRATEGY_METRIC_AT_A_GATE_THAT_FORBIDS_THEM` (resolved by
**c-9**'s reading, not by amendment) ·
`CORRELATION_SERIES_COST_LAYER_NOT_REGISTERED` (**c-4**) ·
`CORRELATION_DATE_ALIGNMENT_NOT_REGISTERED` ·
`ALIGNMENT_MUST_NOT_CREATE_AN_UNREGISTERED_FAVOURABLE_SUBSET` (both **c-6**) ·
`UNDEFINED_CORRELATION_SEMANTICS_PENDING_HUMAN_CHATGPT_RULING` (**c-8**) ·
`NR_L_DAY_ATTRIBUTION_DEPENDS_ON_Q10_I` (**Q10-i**) ·
`NO_PROHIBITION_BINDS_THE_CHOICE_OF_CORRELATION_STATISTIC` (**c-3**, which supplies
`C_STATISTIC_MUST_NOT_BE_SELECTED_TO_MINIMISE_RHO_X`) ·
`C_METHOD_AND_SOURCE_WINDOW_FROZEN_BEFORE_DOWNSTREAM_OBSERVATION` (recommended, not
ruled — **replaced** by **c-9**'s
`C_METHOD_PRE_DATA_FROZEN_C_VALUE_DESIGN_MEASURED_ONCE`). **Surviving:**
`MEAN_ABS_PAIRWISE_CORR_NOT_YET_ESTIMATED_DESIGN_DATA_ONLY` — the contract is ruled,
the value is not measured — together with the residuals §8.5.0 classifies.


### 8.6 Q10(iii), the duration boundaries, and the exact `T_v` / `T_h` / `D` declaration — decision packet

**`Q10_III_RULED_COMPLETE_UTC_CALENDAR_DATE_SHARPE_INDEX_IDLE_ZERO_ANNUALISED_BY_SQRT_365`**
(§8.7.4; `Q10_III_PENDING_HUMAN_CHATGPT_RULING` **HISTORICAL**) ·
**`EXACT_WINDOW_NOT_READY_FOR_DECLARATION_FORWARD_EPOCH_DOES_NOT_EXIST`** ·
**`TURNOVER_CEILING_COUNTS_TRADES_BY_ENTRY_UTC_DATE`** (§8.7.5;
`TURNOVER_CEILING_DAY_STILL_UNREGISTERED` is **HISTORICAL as to attribution only**).
**The four-candidate denominator question set out below is *not* answered by that
ruling**, which refines candidate (1) alone; both remaining axes are locked
pre-observation by §8.7.5 with their permissive arms named.

**Not ruled here.** One packet, three coupled questions: the **annualisation factor**
for the daily Sharpe, the **duration-boundary arithmetic**, and what must be true
before human + ChatGPT can declare the exact `T_v` / `T_h` / `D`. **No date is
invented, no factor is adopted by convention, and no data is read.** Nothing in §8.5
or §8.4 is reopened.

#### 8.6.1 Q10(iii) — the annualisation factor

**The committed authority is one table cell, and it names no factor.**

| What committed text says | Where |
| --- | --- |
| "daily portfolio Sharpe (**ann., UTC-day**) \| **≥ 0.8**" — FROZEN, and the design audit may only tighten | prereg §9 holdout acceptance table |
| "Sharpe is computed on **UTC-day portfolio sums** (as in M1), acknowledged as correlated across pairs" | prereg §9, the daily-aggregation sentence |
| **No annualisation factor, and no `sqrt` of anything, appears anywhere in the prereg** | repo-wide grep of the prereg |
| `TRADING_DAYS_PER_YEAR = 252`, and `annualised_daily_sharpe` returns `mean / sample_stdev * sqrt(trading_days_per_year)` | `scripts/ml_step4/contract.py:95`, `scripts/ml_step4/metrics.py:59-75` — **M1-lineage**, "reusable **after audit/wrapping**" (prereg §11) |
| **`scripts/m15_gate3a/` contains no Sharpe computation** — `sharpe` appears there only as the scrubber's forbidden-token stem and in docstring examples (`artifacts.py`), so a bare grep looks like a contradiction and is not one | package read, not a bare grep |

So `252` is **precedent, not authority**, exactly as the entry-marker constructors
were for Q10(i). **`Q10_III_HAS_NO_COMMITTED_FACTOR_ONLY_AN_M1_PRECEDENT`.**

**The sampling clock is the question, and it is not what either convention assumes.**
`daily_portfolio_pnl` builds its series from a dict keyed by `t.day` and returns
`sorted(by_day.items())`, so it emits **only dates that carry a trade**. The Sharpe
series' index is therefore **active portfolio dates** — neither 252 trading days nor
365 calendar dates, and *not* the complete 310-date index Ruling c-6 gives `c`
(`SHARPE_DAY_SET_AND_CORRELATION_DAY_SET_ARE_DIFFERENT_OBJECTS`, §8.5.0).

**Annualising a per-observation Sharpe by `√k` is only coherent when `k` is the number
of observations per year *on the series' own clock*.** That collapses the candidates
into **two coherent families and three incoherent
combinations whose signs differ** — the sign difference being the cleanest reason no
unconditional claim about `√252` survives. *All five assume the annual scaling has the
form `√k`, which presumes the daily portfolio sums are serially uncorrelated; no
committed source addresses serial dependence of this series, and none is estimated
here.* **`SQRT_K_FORM_ASSUMES_SERIAL_INDEPENDENCE_NOT_COMMITTED`.**

| Reading | Index | Factor | Coherent? |
| --- | --- | --- | --- |
| **(A)** | active dates, as committed | `√(realised observations per year)` | **Yes** — but the factor is a **function of the realised activity rate**, i.e. empirical |
| **(B)** | a **complete** date index with idle dates entered as zero | `√(dates per year of that index)` | **Yes**, and the factor is **data-independent** — but it changes the *index* of a frozen acceptance row |
| **(C)** | active dates, as committed | `√252` | **No** — it annualises an active-date series by a trading-day count that series does not have |
| **(D)** | active dates, as committed | `√365` | **No** — and it is the **most permissive of all**, `D/B = 1/√a > 1` for every active share `a < 1`. It is also the reading the frozen row's own words, "ann., **UTC-day**", most literally suggest |
| **(E)** | complete, zero-filled | `√252` | **No** — the cell reached by taking (B) **without changing `annualised_daily_sharpe`'s default**, which is `252` at every committed call site. `E/B = √(252/365) = 0.831`, ~17% **conservative**. An implementation trap, not a hypothesis |

*(A) and (B) are numerically close*, because zero-filling scales the mean by the
active share `a` and the standard deviation by roughly `√a`, so `S_full ≈ √a · S_active`
and the two forms coincide to first order; on synthetic series at active shares of
60/310, 100/310 and 180/310 they agree to within a few per cent, **the gap growing with
sparsity and with the per-day Sharpe** through the second-order `a(1−a)m²` term. (A)'s
"per year" needs no calendar: `k_A = n_active / D_years` on Ruling Q10-A's elapsed-UTC
clock, which is **why** the agreement is structural rather than coincidental. **`NON_NORMATIVE_DIAGNOSTIC_ONLY`**; synthetic arithmetic, no data read.

**And (C) — the reading the M1 code implements — is permissive *in one regime and
conservative in another*, which is not what an earlier drafting of this paragraph
said.** Closed form on the readings above: `C/B = √(252 / (365·a))` at active share
`a`, so **(C) is permissive below `a = 252/365 ≈ 0.690` and conservative above it**,
reaching ×0.83 at full occupancy. On synthetic series with a positive daily mean:

| active dates / 310 | (C) `active × √252` | (B) `zero-filled × √365` | ratio |
| --- | --- | --- | --- |
| 180 | 2.72 | 2.49 | ×1.1 |
| 100 | 1.23 | 0.85 | ×1.5 |
| 60 | 4.01 | 2.08 | ×1.9 |

**`NON_NORMATIVE_DIAGNOSTIC_ONLY`.**

**Three corrections to how those rows were first presented, all of them narrowing the
claim.** *First, the regime was mis-scoped.* An earlier drafting said "§0.6 projects
roughly **0.56 trades per pair per day**, so the sparse regime is the expected one" —
but this series is a **portfolio** sum, not a pair series. Twenty pairs at that rate is
roughly **eleven portfolio trades per day**, a dense date index; prereg §9 requires
**≥ 1,000** holdout trades over a **≥ 2-month** holdout, and the gate-4 audit calls
that corridor "the tightest spot". The sparse regime is the expected one for
**pair-days**, not for the portfolio index this metric is built on, and this packet
estimates neither. *Withdrawn.*

*Second, the active share is not free — a frozen row already bounds it.*
`daily_coverage` divides `len({t.day for t in trades})` — the **same set that indexes
this Sharpe series**, in the same `compute_all` call — by `holdout_trading_days`, and
prereg §9 freezes **daily coverage ≥ 0.60** conjunctively. Where index and factor sit
on one clock the ratio is therefore bounded: `C/B = 1/√coverage ≤ 1/√0.60 ≈ **1.29×**`.
The 100- and 60-date rows above are **not shown to be admissible** — they would need
the R-5 denominator to be small enough for coverage to still clear 0.60, and
establishing that needs the market-hours fact this packet must not author.
**⚠ `Q10_III_SQRT_252_INFLATION_IS_BOUNDED_BY_THE_FROZEN_COVERAGE_ROW` — WITHDRAWN**
by Ruling Q10(iii) (§8.7.4) and §12.15: the ruled index and the coverage denominator do
not share a clock, so the bound does not survive; and independently `1/√coverage` is the
ratio for the *active × `√365`* reading, not for `√252`, whose value at the floor is
≈ 1.07. **No upper bound on the ratio is claimed.**

*Third, and consequently, the A-ω-5 argument does not apply unconditionally.* An
earlier drafting said (C)'s "favourable direction is knowable with no data at all".
It is knowable only **given** where the active share falls relative to `252/365`, and
that is itself a market-hours question. **§8.4.11's A-ω-5 standard therefore bites on
(C) only in the regime where the condition holds, and this packet does not establish
that the regime obtains.** *Withdrawn as an unconditional claim.*
**`Q10_III_SQRT_252_IS_PERMISSIVE_ONLY_BELOW_252_ACTIVE_DATES_PER_YEAR`.**

**And under two of the three readings this reaches the *selection*, not only the
reported value — with a divergence worth naming.** The committed selection metric is
prereg §8's **validation net expectancy subject to the turnover budget**, which is
per-trade and **annualisation-free**, so under the committed rule Q10(iii) does not
reach selection at all. The committed **implementation** does something else:
`select_threshold` takes the **argmax** of `daily_portfolio_sharpe` across candidates,
fed from the validation series at `body.py:228` and `:535`. Under **(C)** the factor is
constant across candidates and the argmax is invariant; under **(A)** and **(B)** the
effective factor carries `√(activity)`, which differs per candidate and penalises
sparser operating points, so **the selected operating point can move**. That is the
same surface §8.5.0 recorded for Q10(i), reached here only through an implementation
that diverges from the committed metric.
**`Q10_III_REACHES_THE_OPERATING_POINT_ONLY_VIA_AN_IMPLEMENTATION_THAT_DIVERGES_FROM_THE_COMMITTED_SELECTION_METRIC`.**

**What the ruling must decide, stated as a choice and not steered.** Either **(A)** —
keep the committed index and accept a **data-dependent** factor, with the
outcome-blindness problem that creates — or **(B)** — complete the index with idle
zeros and take a data-independent factor, which is the same construction Ruling c-7
already took for `c` and which would close
`SHARPE_DAY_SET_AND_CORRELATION_DAY_SET_ARE_DIFFERENT_OBJECTS`, **at the cost of
changing the index a frozen §9 row is measured on**. *Both* coherent options change the
measured value relative to the committed implementation, and by nearly the same amount
since (A) and (B) agree closely; what is unique to (B) is the change of **index**. *An
earlier drafting attached the cost to (B) alone, which mildly steered the choice.* Ruling 10 bars *loosening a
threshold*; neither option touches the number, and §8.5.0 has already recorded that
this is the **weaker** footing §8.2.0 did not have to rely on
(`Q10_I_RESTS_ON_OUTCOME_BLINDNESS_NOT_ON_A_SHOWN_TIGHTENING`). **This packet does not
choose**, and expressly does not adopt `√252` by convention.

**One candidate is closed rather than left for a ruling to raise.** A Sharpe on
*returns* rather than PnL is provably the same number here: Sharpe is scale-invariant,
the contract is fixed-stake and non-compounding (`STAKE_UNITS_PER_TRADE = 1.0`,
`NON_COMPOUNDING = True`, `FIXED_NOTIONAL_EQUITY_PIPS` frozen), so dividing every daily
value by a constant notional leaves `mean/sd` unchanged; and no committed source
subtracts a risk-free rate.

**Two things it will not do by accident.** It does **not** redefine day attribution —
Q10-i governs, unchanged, whichever index is chosen. And if (B) is taken, **which**
dates a complete Sharpe index contains is a **calendar-authority** question — every
UTC date, or the dates the approved Calendar A recognises — and **no market-hours fact
is authored here**. **`Q10_III_OPTION_B_DEPENDS_ON_THE_CALENDAR_AUTHORITY`.**

#### 8.6.2 The duration boundaries, reconstructed

Every row re-read at source. **No date below is invented.**

| Boundary | Value | Authority |
| --- | --- | --- |
| Design span | **2025-04-25 → 2026-02-28** | prereg §3.1; `DESIGN_START` / `DESIGN_END` = `2025-04-25T00:00:00Z` / `2026-02-28T23:59:59Z` (`scripts/m15_gate3a/no_overlap.py:38-39`) |
| Dead window | **2026-03-01 → 2026-04-24**, "excluded from every role at every timeframe" | prereg §3.1 (R-2b); `DEAD_START` / `DEAD_END` |
| Forward-epoch floor | **2026-04-25T00:00:00Z**, "no earlier than" | prereg §3.1; `FORWARD_FLOOR` |
| Validation | `2026-04-25 → T_v`, **≥ 3 months** | prereg §3.1 + Ruling 2 |
| Holdout | `T_v (+embargo) → T_h`, **≥ 2 months**, one-shot | prereg §3.1 + Ruling 2 |
| Purge / embargo | **≥ horizon + 1 = 25 M15 bars at every role boundary**, horizon frozen at 24 by Ruling 6 | prereg §3.2 |
| Ordering | design < dead window < validation < holdout < replication | prereg §3.2 |
| Forward-epoch **ceiling** | **none committed** — `assert_forward_bounds` imposes a floor only | `no_overlap.py:182-195` |
| `D` | elapsed calendar span on the **UTC clock**; `D_IS_ELAPSED_UTC_TIME != SAMPLE_COUNT_IS_CALENDAR_TIME` | Ruling Q10-A (§8.2.0) |

**The interval convention is closed, and it is committed rather than assumed.** The
constants end at `:59:59` and the next role begins at `00:00:00` the following date —
`no_overlap.py` states it in terms ("`DEAD_START` is exactly one second after
`DESIGN_END`") and **raises at import** unless `DESIGN_START < DESIGN_END < DEAD_START
<= DEAD_END < FORWARD_FLOOR` — deliberately a raise and not an `assert`, since "bare
asserts are stripped under `python -O`"; `coverage.py` bound-checks with `slot < DESIGN_START or slot
> DESIGN_END`. So the three **committed epoch constants** are published as
**`[start, end]` closed at second granularity** — but the adjacency is **not uniform,
and the code is stricter than the constants**. `no_overlap.py` derives
`_DEAD_END_EXCLUSIVE = DEAD_END + 1s` and **raises at import** unless
`_DEAD_END_EXCLUSIVE == FORWARD_FLOOR` ("dead-window end and the forward floor must be
contiguous"), and `is_dead_window_instant` tests
`DEAD_START <= instant < _DEAD_END_EXCLUSIVE` — half-open, so the dead window covers
**the whole of its final second** and there is **no gap** before the forward floor: an
instant inside `2026-04-24T23:59:59.x` is **dead**. A one-second exclusion band exists
only at **design → dead**. *An earlier drafting claimed a uniform one-second gap
between adjacent roles; that is **withdrawn** — it is less conservative than the code
at the dead→forward boundary.* At 15-minute bucket-start granularity the two readings
coincide, which is what makes "every UTC calendar date from `DESIGN_START`'s date
through `DESIGN_END`'s date inclusive" (Ruling c-6, 310 dates) the right reading rather
than an off-by-one.
**`COMMITTED_EPOCH_CONSTANTS_ARE_CLOSED_AT_SECOND_GRANULARITY_DEAD_TO_FORWARD_IS_CONTIGUOUS`.**

**And nothing is settled here for the two undeclared forward roles.** The endpoint
inclusion/exclusion convention for `T_v` and `T_h` is
`DURATION_BOUNDARY_ARITHMETIC_AND_ENDPOINT_CONVENTION_PENDING_HUMAN_CHATGPT_RULING`
(§8.2.0, §8.2.3), and this packet **reconstructs the committed constants without
resolving that question**.

**Validation / holdout separation is settled, and does not need a new purge.** The
25-bar purge/embargo is `horizon + 1`, so a validation event's 24-bar label **cannot**
reach into the holdout; the gate-4 design audit records exactly that — "purge/embargo
25 M15 bars for horizon 24: **adequate at the validation/holdout boundary (labels
cannot straddle)**" — and adds that the design→validation boundary is *additionally*
protected by the ~8-week dead window. **The purge is counted in bars, never
wall-clock**, and **§4** of this document already records why: a Friday-afternoon signal
bar's 24-bar label reaches into Monday, so an elapsed-time purge of the same nominal
length would not purge it. **No new purge is invented here.**

**Warm-up is already regulated, and it does not expand any role's sample.** Gate 4's
**T-1 (binding tightening)**: dead-window data is **never loaded for any purpose**; all
indicators initialise **only from forward-epoch bars**; the first `W` bars of the
forward epoch are a **warm-up burn-in — event-ineligible, used only to warm
indicators** — with `W ≥ the longest feature lookback across all groups including
H1/H4 context`, the exact `W` frozen at implementation. So the distinction is committed: **warm-up bars are read but are not decision-bearing
sample members**, and they sit **inside** the forward epoch rather than before it.
What is **not** fixed is the numeric `W`, which is a design-span-estimated quantity
governed by R-10 and frozen at implementation.
**`WARM_UP_W_IS_FROZEN_AT_IMPLEMENTATION_NOT_HERE`.**

*One arithmetic consequence worth naming, because it bears on `D`.* The burn-in is
event-ineligible, so the **first `W` bars of validation carry no events**. A validation
span of exactly three months therefore yields **fewer than three months of eligible
events**. It does **not** hold at the holdout's start: T-1's burn-in is a
**single forward-epoch** burn-in — `scripts/m15_gate3a/warmup.py` indexes
`is_event_eligible(bar_index)` "zero-based over **forward-epoch** bars" with
`first_eligible_bar_index = w_bars` — so no second burn-in exists at the holdout, and
prereg §3.1's `T_v (+embargo) → T_h` places the embargo **outside** the holdout span.
*An earlier drafting said "and the same holds at the holdout's start after the
embargo"; withdrawn, and it drifted in from rendering T-1's "first `W` bars of the
**forward epoch**" as "of validation".* The frozen minima are **span** minima, not
eligible-event minima, and no committed source converts between them. **`SPAN_MINIMA_ARE_NOT_ELIGIBLE_EVENT_MINIMA`** — recorded, not
resolved, and **no count is estimated**.

#### 8.6.3 What `T_v` and `T_h` actually denote

Read off prereg §3.1's table rather than from the shorthand:

- **`T_v`** is the **validation end instant**, and simultaneously the anchor the
  holdout is measured from: validation is `2026-04-25 → T_v`, holdout is
  `T_v (+embargo) → T_h`.
- **`T_h`** is the **holdout end instant**.
- Both are **[FIXED-AT gate 3a]**, declared "when the forward epoch is adopted".
- Under the closed convention above, an instant of the `…T23:59:59Z` form denotes an
  inclusive end.
- **The holdout start is a declared object, never a computed one — and an earlier
  drafting of this bullet computed it.** It said "the holdout then begins at the first
  bar **25 M15 bars after** `T_v`". §8.2.7 forbids exactly that, by name: "**the
  embargo is a bar offset, and the holdout start is declared, not computed** … the
  25-bar embargo is a **constraint verified against that declaration, never a formula
  that produces it**", because "were the start computed instead, it would move whenever
  the calendar approval landed — the same post-freeze lever §8.2.5 identifies".
  Under Ruling ω-13(a) the calendar lands **after** the declaration, so a computed
  start is precisely that lever; it is also indeterminate while the bar substrate is
  open. **Withdrawn.**
  **`EMBARGO_IS_A_BAR_CONSTRAINT_NOT_A_CALENDAR_DERIVATION`** governs, unchanged.
- **Q10-B declares six objects, not two**: the **validation start**, `T_v`, the
  **declared holdout start**, the exact **holdout window**, `T_h`, and the exact
  operative **`D`**. An earlier drafting of this subsection enumerated only `T_v` and
  `T_h`, which dropped four of them from the declaration surface.
- Neither `T_v` nor `T_h` is a *duration*. **`D` is the holdout duration** — §8.1.0's
  normative wording fixes "the exact **holdout duration** `D`", and §8.2.7 fixes it as
  "the elapsed UTC span between the **declared holdout start** and `T_h`". It is
  expressly **not** `T_h − T_v`, which would overstate the holdout by the 25-bar
  embargo, in the direction that makes the ≥ 2-month floor easier to claim. `D` is
  **declared** under Q10-B and required to be consistent with the declared instants; it
  is not independently choosable, and it is **not omissible from the declaration
  record** — without it Ruling A's
  `TWO_MONTH_HOLDOUT_IS_A_MINIMUM_NOT_THE_OPERATIVE_DURATION` is uncheckable. *An
  earlier drafting called `D` "derived" and "not a third independent declaration";
  withdrawn on both counts.*

**`T_V_IS_THE_VALIDATION_END_INSTANT_T_H_IS_THE_HOLDOUT_END_INSTANT`** — recorded
because "T_v/T_h" as bare shorthand has been used in this document for a boundary, a
duration and a pair of dates, and the three are different objects.

#### 8.6.4 Why the exact window cannot be declared yet — and it is not a contract gap

**The committed forward-epoch adoption manifest already answers this**, and it answers
it against declaration:

> `status: "ADOPTION_BLOCKED__FORWARD_DATA_NOT_YET_ACCRUED"` ·
> `verdict: "INSUFFICIENT_SAMPLE__ADOPTION_WAITS"` · `as_of_utc: "2026-07-07"` ·
> `committed_forward_epoch_bars_in_repo: 0` — "The committed `365d_BA` epoch **ENDS**
> 2026-04-24T20:59Z … it contains **ZERO** bars at or after the forward-epoch floor
> 2026-04-25. **There is no forward-epoch source in the repository.**" ·
> `validation_span_utc: "PENDING"` · `holdout_span_utc: "PENDING"` ·
> `forward_epoch_source: "PENDING"`

That is **committed availability metadata** — the class §8.1.6 limb (i) admits for
sizing `D` — not a data read. Two independent facts follow:

1. **The forward-epoch source does not exist.** Zero bars, no admitted source. This is
   not a question a ruling can close; it is a **data-acquisition and adoption** step,
   and the manifest already routes it through "a Gate-P2-style adoption".
2. **The minimum span has not accrued.** The frozen requirement is validation ≥ 3
   months **plus** holdout ≥ 2 months of forward span from the 2026-04-25 floor. The
   manifest's own worked plan gives the comparison without needing a month convention:
   earliest data-complete **2026-09-25** ("validation ~2026-04-25..2026-07-25 + purge +
   holdout ~2026-07-25..2026-09-25"), earliest feasible adoption **2026-10** — and the
   present date precedes both. *An earlier drafting wrote "122 days ≈ 4.0 months … pure
   calendar arithmetic": the day count silently encoded an undated "present record
   date", and the ≈-months conversion leans on the month arithmetic §8.2.3 records as
   unresolved. Withdrawn in favour of the date comparison.*

**So `EXACT_WINDOW_READY_FOR_HUMAN_CHATGPT_DECLARATION` is NOT claimed.** The
operative status is
**`EXACT_WINDOW_NOT_READY_FOR_DECLARATION_FORWARD_EPOCH_DOES_NOT_EXIST`**, and the
committed disposition for exactly this case is already frozen and unchanged: **adoption
waits**, "the verdict `INSUFFICIENT_SAMPLE` exists precisely so that impatience cannot
shrink the holdout".

**What must be true before the declaration can be taken**, listed so the remaining
work is a list and not a judgement:

1. A **forward-epoch source** exists, is acquired and is admitted under the adoption
   the manifest names (**Red**: an external data step, not a contract decision).
2. At least the frozen minimum span has **accrued** — validation ≥ 3 months, holdout
   ≥ 2 months, plus the 25-bar embargo between them. It has not: the manifest's own
   worked plan puts the earliest data-complete date at **2026-09-25** and the earliest
   feasible adoption at **2026-10**, and the present date precedes both. *Stated as a
   date comparison rather than in months deliberately — how many days a "month" carries
   is `DURATION_BOUNDARY_ARITHMETIC_AND_ENDPOINT_CONVENTION_PENDING_HUMAN_CHATGPT_RULING`,
   and §8.2.3 quantifies the spread at 59–62 calendar / 41–45 weekday days.*
3. *(**Not** a pre-declaration item — recorded here because it is the step
   immediately **after**, and an earlier drafting listed it as a precondition, which
   reinstated by list-position the very order Ruling ω-13(a) reversed.)* The
   **calendar artifact** is approved. ω-13(a) fixes the order — **declare the window →
   freeze the declared window → materialise Calendar A *for* that declaration → freeze
   and approve it → no reselection on calendar content → only then decision-bearing
   observation** (§8.2.8 step 6a) — so calendar approval **follows** the declaration
   and cannot be a condition on it;
   `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` binds before the
   **continuation**, not before the declaration. Nothing here creates a calendar.
4. The remaining Minimum Research Gate questions are resolved — §8.2.8's step 7, Q1,
   Q8, FR-19 and the rest of §8 — and its **step 8 is unconditional**.
5. Q10(iii) is ruled, because the annualised Sharpe row cannot be evaluated without
   it — **and `DURATION_BOUNDARY_ARITHMETIC_AND_ENDPOINT_CONVENTION_PENDING_HUMAN_CHATGPT_RULING`
   (§8.2.0, §8.2.3) is ruled**, because whether a declared `T_v`/`T_h` **meets** the
   frozen minima is undecidable until the month arithmetic, the end-of-month rule and
   the anchor are fixed. *§8.2.8's step 5 also carries that question, and an earlier
   drafting of this packet claimed to complete "the whole of" step 5 without addressing
   it.*
6. `MINIMUM_CALENDAR_IDENTITY_RECORD_REQUIRED_BEFORE_DATA_EXECUTION` (Ruling ω-13,
   residual 5) and the c-side records §8.5.0 and c-10 require are in place as
   **execution prerequisites**.

**One committed direction bears on `T_h` and is recorded rather than left out.** The
gate-4 design audit says "**Gate 3a should prefer a holdout longer than the 2-month
minimum when accrued data allows**", with the feasibility corridor "a 2-month holdout
(~43 trading days) gives a feasible corridor of [1,000 … ~1,720] trades — intentionally
demanding but narrow". §8.1 already records that this sits under a "**Feasibility note
(non-binding)**" heading and is absent from T-1…T-7, so it is a **preference, not a
requirement**, and it may not be used as an anchor: preferring a longer holdout is not
licence to extend one *until a floor passes*.

**And what is already frozen about the declaration, carried forward unchanged from
Ruling Q11/§0 and Q10-B:** two months is a **floor**, not the operative duration; `D`
is frozen **once**, at the forward-epoch adoption continuation, **before data**; there
is no post-freeze extend, shorten or reselect, and a different `D` needs a new explicit
pre-registration or contract decision — a route whose sufficiency is itself unruled
(`NEW_PREREGISTRATION_SUFFICIENCY_FOR_A_DIFFERENT_D_NOT_RULED`);
`DURATION_SELECTION_MUST_BE_OUTCOME_BLIND`; and the declaration is a **human +
ChatGPT** act taken before continuation authorisation (Q10-B).

**The forbidden anchors, restated IN FULL because this is the packet a declaration
would be taken from — and because §8.6.2 records that no forward-epoch ceiling is
committed, so these are the only upward constraint on `T_h`.** Q10-B forbids as
anchors: the **first available date** · the **latest available date** · **"today"** ·
the **maximum available dataset date** · a date required to reach `N_eff` · a date
chosen after observing empirical **label** overlap (`mean_overlap_fraction` / `rho_h`)
· after empirical correlation · after a **traded-event** sample count (`N_raw`,
`N_eff`) · after Sharpe or returns · any automatic **"use all available history"**. No
span may be extended **in order to reach** a sample floor, and no boundary may be slid
after validation looks favourable. Calendar density and expected slot count are
additionally forbidden under `CALENDAR_MATERIALISATION_MAY_NOT_REOPEN_WINDOW_SELECTION`,
which Q10-B's own list does not carry. *An earlier drafting restated only the
outcome-shaped anchors and dropped all five **availability-shaped** ones — the five
that bite hardest in a packet whose whole subject is that data has not yet accrued.*

#### 8.6.5 How the window meets the sample floors — the shape only

Committed formulae only, **no count estimated**:

`N_eff = (Σ_p N_raw_p / rho_h_p) / rho_x`, with `rho_h_p = 1 + 23·ω_p` (H = 24 frozen)
and `rho_x = 1 + 19c` (P = 20 ruled). The holdout floors are a **conjunction**:
`N_raw ≥ 1000` **and** `N_eff ≥ 400`.

A longer holdout span raises `N_raw` roughly in proportion to elapsed time at a fixed
event rate, and leaves `rho_x` untouched — `c` is DESIGN-measured and frozen before the
holdout exists. Its effect on `rho_h` is **not** signed — **and not for the reason a
fixed-rate reading suggests**, since at a genuinely fixed event rate the gap
distribution and `ω` are unchanged and `N_eff` would rise in proportion. *An earlier
drafting argued from "more events on the same clock shorten the gaps and raise `ω`",
which silently switched to a higher rate over a fixed span; withdrawn, because an
unsound argument for a conservative conclusion is what a later session cites to reverse
it.* The sound ground is at source: `ω` is **measured on the evaluated role itself**
(the estimator spec — "estimated per pair from the **realised** inter-event gaps",
reported `per_role`), and the event rate over a longer span is not known to be the
design-span rate. Both inputs to `rho_h` are unknown pre-data, so neither the magnitude
nor the sign of a longer holdout's effect on `N_eff` is derivable, and the packet does
not derive it.
**`SAMPLE_FLOOR_REACHABILITY_NOT_DETERMINABLE_WITHOUT_MEASURED_INPUTS`** stands
unchanged, and §0's verdict is not moved by anything in this packet.

#### 8.6.6 The turnover-ceiling day — RULED at §8.7.5 on the attribution axis; the denominator question stated here stays open

Ruling Q10(ii) expressly left it open: `DAY_IDENTITY = UTC_CALENDAR_DATE` "does **not**
define the 'day' of the **`≤ 40 trades/day` turnover ceiling**, which remains a §9
FROZEN row with an undefined day and is **not ruled here**", warning that reading it in
calendar days would widen gate 4's committed corridor by **~42%** — "a loosening
Ruling 10 forbids, and one that **citing this ruling must not achieve**". §8.5.0
repeated the guard for Q10-i.

**The two days are kept distinct, and this packet does not bind them.** Q10-i fixes the
**PnL attribution** day; the turnover ceiling's day is a **counting** day, and the
committed implementation divides by `len({t.day for t in trades})` — **active** dates —
which is a third reading again. The candidates are **four**, not three: active dates — the implementation, and the
**smallest** denominator, hence the **strictest** reading, which is the *opposite*
polarity from §8.6.1's (C), where the committed implementation is the permissive one;
**the registered R-5 denominator** `DAILY_COVERAGE_DENOMINATOR =
"distinct_utc_calendar_dates_in_holdout"`, which `compute_all` already receives and
already uses for daily coverage **in the same call**, and which is the one candidate
that would give turnover and coverage a shared denominator;
every UTC calendar date in the evaluated span, or the dates the approved calendar
authority recognises. They differ by roughly the active share, and the direction is
knowable: a **larger** denominator lowers measured turnover and makes the `≤ 40`
ceiling easier to clear. *Whether the R-5 denominator survives Ruling Q10(ii)'s
"expected slot membership from the approved calendar authority, never inferred from
data" is part of the question and is not settled here.*

**`TURNOVER_CEILING_DAY_STILL_UNREGISTERED`** · **`TURNOVER_DAY_MUST_NOT_BE_BOUND_TO_THE_PNL_ATTRIBUTION_DAY_BY_INHERITANCE`.**
It is stated here as a decision question because it shares the daily clock this packet
reconstructs; it is **not** ruled, and Q10-i may not be cited as ruling it.

#### 8.6.7 Status

- **Q10(iii)** — **RULED at §8.7.4**;
  `Q10_III_PENDING_HUMAN_CHATGPT_RULING` is **HISTORICAL**. As the packet stood, and it
  is why the ruling had to decide the clock first: not derived, because the only
  committed authority is the row label "ann., UTC-day", and `√252` is M1 precedent.
  Not adopted by convention. The two coherent families are set out at §8.6.1 and the
  incoherent-but-permissive one is named.
- **Duration boundaries** — **reconstructed and largely committed**: the design span,
  the dead window, the forward floor, the two frozen minima, the 25-bar purge, the
  ordering, the closed-interval convention and T-1's warm-up regime all have
  authority. Open: the numeric `W`, `SPAN_MINIMA_ARE_NOT_ELIGIBLE_EVENT_MINIMA`, and
  the absence of any committed forward-epoch **ceiling**.
- **Exact `T_v` / `T_h` / `D`** —
  **`EXACT_WINDOW_NOT_READY_FOR_DECLARATION_FORWARD_EPOCH_DOES_NOT_EXIST`.** The block
  is **not** a contract gap: zero forward bars exist, no forward source is admitted,
  and the frozen minimum span has not accrued. `INSUFFICIENT_SAMPLE__ADOPTION_WAITS`
  is the committed and unchanged disposition.
- **Turnover day** — **RULED at §8.7.5**,
  `TURNOVER_CEILING_COUNTS_TRADES_BY_ENTRY_UTC_DATE`, deliberately **not** inherited
  from Q10-i. Two narrower questions stay unregistered and are **not** ruled by it:
  mean versus per-day cap, and the active-versus-calendar denominator axis Ruling
  Q10(ii) left open.

**Nothing here authorises anything.** No date is chosen, no factor is adopted, no
calendar is created, no data is read, no count is estimated.
**`PRODUCTION_READINESS_NOT_CLAIMED`** · **`NO_EXECUTION_PERFORMED`**.

### 8.7 The bundled ruling — DESIGN generation, the `c`-input freeze, Q10(iii) and the turnover day

A ruling received from human + ChatGPT and recorded here as **authority**. One decision
round closing four items: the two blockers §12.14 left on Ruling c-10, plus Q10(iii)
and the turnover-ceiling day.

**`C_11_RULED_DESIGN_C_SERIES_GENERATED_WITHOUT_SAME_OBSERVATION_TARGET_LEAKAGE`** ·
**`C_12_RULED_ALL_DECISION_BEARING_C_MAP_INPUTS_FROZEN_BEFORE_C_MEASUREMENT`** ·
**`Q10_III_RULED_COMPLETE_UTC_CALENDAR_DATE_SHARPE_INDEX_IDLE_ZERO_ANNUALISED_BY_SQRT_365`** ·
**`TURNOVER_CEILING_COUNTS_TRADES_BY_ENTRY_UTC_DATE`**

**Not ruled here**, said first: no exact `T_v` / `T_h` / `D`, no forward epoch, no
calendar, no fold count and no CV machinery; **no empirical prediction, PnL, `c`,
Sharpe, turnover, `ω` or `N_eff` is computed**; no data is read. NR-K, `ω`, Q10(i),
Q10-A/(ii)/B and c-1…c-10's already-ruled limbs are **not reopened**.

#### 8.7.1 The committed authority, re-read at source

| What committed text actually says | Where |
| --- | --- |
| The roles are **Design (exploratory) · DEAD window · Validation · Frozen holdout · Disjoint replication**. **There is no training-span role.** | prereg §3.1 |
| Calibration is "isotonic regression, fit on a split **carved from the training span only** — never validation, never holdout; **no calibration-method search**" — so "the training span" is *named* and never *defined* | prereg §8 |
| `W̄`/`L̄` are "estimated on **design data** and **frozen** (never re-fit on validation/holdout)"; the model is "**from-scratch training only**"; params frozen; "**no model-family search**" | prereg §8 |
| Validation and holdout are in the **forward epoch**, which does not exist; so the only span available for fitting is **DESIGN** | prereg §3.1 |
| **No out-of-fold, cross-validation, walk-forward or rolling-origin machinery exists anywhere** in `scripts/ml_step4/` or `scripts/m15_gate3a/` | repo-wide read |
| The M1-lineage implementation trains **one model per pair** on `train_idx` only, then builds `prob_map` for `needed = val_idx ∪ hold_idx` **only**; training bars get `prob_map.get(i, (0.0, 0.0))` and are never passed to `_real_signals`, which is called with `val_idx` and `hold_idx` alone. **`scripts/ml_step4/` has no in-sample prediction path** — and the defence does not rest on the M1 probability threshold either: under prereg §8's EV gate, `p̂ = 0.0` gives `EV = −L̄ − cost < 0 ≤ ev_min` at every registered operating point. **It is *not* absent repo-wide**: `compare_multipair_v6_meta.py` runs Layer-1 inference over the model's own `train_slice` and argues in its own docstring that this "is fine" — the reasoning c-11 refuses | `scripts/ml_step4/body.py:486-515`; `scripts/compare_multipair_v6_meta.py:26-53, 1138-1150` |
| The M1 split is a single chronological 70/15/15 cut with a purge/embargo | `scripts/ml_step4/split.py` |
| Sharpe: `annualised_daily_sharpe` = `mean / sample_stdev * sqrt(trading_days_per_year)`, default `TRADING_DAYS_PER_YEAR = 252` — **M1-lineage**, and prereg §11 makes metric helpers reusable only "**after audit/wrapping**", a condition the gate-4 audit did not discharge | `scripts/ml_step4/metrics.py`, `contract.py` |
| The only M15 Sharpe authority is the frozen row "daily portfolio Sharpe (**ann., UTC-day**) ≥ 0.8". **No factor, and no `sqrt` of anything, appears in the prereg** | prereg §9 |
| `daily_portfolio_pnl` returns `sorted(by_day.items())` from a trade-keyed dict — **only dates carrying a trade** | `scripts/ml_step4/metrics.py` |
| `max_equity_drawdown` consumes **that same series**; `daily_coverage` and `n_days` are computed from **`trades`**, not from the series | `scripts/ml_step4/metrics.py` |
| Turnover is `n_trades / n_trading_days` — the **numerator carries no date at all** — and its docstring reads "**Portfolio-average trades per day**" | `scripts/ml_step4/metrics.py` |
| The frozen row is "turnover upper bound \| **≤ 40 trades/day portfolio-wide**", and §9.V requires the kill gate to be met "**within the turnover budget**". Neither says **which** day, nor whether the ceiling is a mean or a per-day cap | prereg §9, §9.V |
| Ruling Q10(ii) expressly leaves the ceiling's day open: it "does **not** define the 'day' of the `≤ 40 trades/day` turnover ceiling, which remains a §9 FROZEN row with an undefined day and is **not ruled here**" | §8.2.0 |

**So the classification is: `absent`, not `committed`, on all four questions.** §4's R-2
(the single chronological cut, the ≥ 25-bar intra-span purge, the trailing-gap rule for
walk-forward, **the no-straddle rule with its enumeration of fitted statistics**, and
**one split timestamp for all pairs**) is **this packet's own proposal**, offered as
ruled text in a still-pending packet — the same status §12.5 recorded for R-10, and it
is **not** cited here as authority.
**`SECTION_4_R2_IS_THIS_PACKETS_PROPOSAL_NOT_COMMITTED_AUTHORITY`.** **Ruling c-11
nevertheless adopts R-2's no-straddle enumeration and its one-span rule as its own
rulings**; the adoption is c-11's, R-2 remains a proposal, and the provenance is
recorded here rather than left for a reader to notice.
**`C_11_ADOPTS_R_2_S_NO_STRADDLE_ENUMERATION_AS_A_RULING_NOT_BY_CITATION`.**

#### 8.7.2 Ruling c-11 — how the DESIGN `c`-series is generated

**`C_11_RULED_DESIGN_C_SERIES_GENERATED_WITHOUT_SAME_OBSERVATION_TARGET_LEAKAGE`** ·
**`DESIGN_C_SERIES_MUST_BE_GENERATED_WITHOUT_SAME_OBSERVATION_TARGET_LEAKAGE`.**

**The rule.** Every DESIGN-span prediction entering a `c_design[config_id]` series must
come from a model whose fit **did not use that observation's own target**, and no
statistic fitted on data that includes an observation may be used to generate that
observation's prediction — the cost table, `W̄`/`L̄`, the calibration and any scaler
included. **Option A (train on the whole DESIGN span, predict back onto it) is
refused.** The permitted shape is a leakage-safe chronological design — purged
out-of-fold, walk-forward or rolling-origin — and

**Two of the four named statistics are committed to straddle, so this ruling overrides
them *for the `c` generation only*, and says so rather than leaving itself
unsatisfiable.** prereg §5 estimates the per-pair × session spread tables **from
design-span M15 quoted spreads** and freezes them "`[FIXED-AT gate 3a or design
audit]`"; prereg §8 estimates `W̄`/`L̄` "**on design data** and **frozen**". Every
DESIGN-span observation lies inside the data both were fitted on, so under the rule
above neither may generate a DESIGN-span `c` prediction. §4's R-2 states the consequence
in terms: "*A cost table fitted over the whole design span means **the labels inside the
slice were constructed using the slice**. That is target leakage in the strict sense and
it is invisible to every acausal check.*" The `c` generation therefore uses
**fold-local** spread tables and `W̄`/`L̄`; **the frozen tables continue to govern
validation and holdout unchanged**, and §8.7.3's freeze-table row for the cost table is
read accordingly — it freezes what validation and holdout use, not what generates `c`.
**`C_GENERATION_USES_FOLD_LOCAL_COST_AND_WBAR_LBAR_NOT_THE_FROZEN_PRODUCTION_TABLES`.**

**And the cost of that is recorded, not smoothed.** A fold-local table means
`c_design[config_id]` is **not** the correlation of the frozen production
configuration's PnL — it is the correlation of a leakage-safe surrogate of it.
**`C_DESIGN_IS_THEREFORE_NOT_THE_CORRELATION_OF_THE_FROZEN_PRODUCTION_CONFIGURATION`** —
an accepted cost of the leakage-safe arm, and the reason the arm is a **ruling** rather
than a derivation.

**The reach into the labels is named, because §4's R-2 calls it "the subtlest leakage
route in the whole gate".** Under prereg §6 the barriers and the eligibility hurdle are
functions of `cost` — `TP_dist = max(1.5 × ATR14, 3.0 × cost)`,
`SL_dist = max(1.0 × ATR14, 2.0 × cost)`, eligibility `1.5 × ATR14 ≥ 2.0 × cost` — so a
fold-local table **changes which DESIGN bars are events at all**, and the DESIGN-span
eligible-event count becomes a function of the generation method. That count is **not**
the `≥ 1,000` raw floor's numerator, which is measured at holdout, and **nothing here
moves that floor**.
**`C_GENERATION_LEAKAGE_RULE_REACHES_THE_LABELS_AND_THE_ELIGIBILITY_HURDLE`.**

And **this ruling fixes no fold count, no
window length and no CV machinery**; those are implementation, and **none exists in the
M15 lineage** (`scripts/ml_step4/`, `scripts/m15_gate3a/`). *An earlier drafting said
"none exists today", which is false repo-wide and is withdrawn*: walk-forward and purged
machinery exists at `stage22_0e_meta_labeling.walk_forward_oos_folds`,
`train_ml_baseline.train_walk_forward` and `ml_uplift_harness.contracts`
(`walk_forward_folds`, `purged`) — Phase-9 / stage-22 lineage this programme has
invalidated once, admissible under prereg §11 only **after audit/wrapping**, which has
not happened. **`C_GENERATION_MACHINERY_MAY_NOT_BE_REUSED_FROM_AN_UNAUDITED_LINEAGE`.**

**Why it is a ruling and not a derivation.** No committed source selects a
prediction-generation method for the DESIGN span, and prereg §3.1 defines no training
role that could imply one. What committed material *does* show is that the repository
has **no in-sample prediction path at all** — the M1-lineage producer builds
probabilities only for validation and holdout indices — so Option A would have to be added to
that lineage — but the repository is **not** innocent of the shape, and an earlier
drafting's "something that has never existed" is withdrawn. **Neither arm is cheaper on
the strength of what exists**, so no cost asymmetry supports this ruling. Option C (a
model trained on a pre-DESIGN span) is unavailable independently and on a **source**
ground: `no_overlap` raises on any design span with `lo < DESIGN_START`, and prereg §3.2
authorises neither `730d_BA` nor `3650d_BA`. Option A is
therefore refused on a research-integrity ruling, not on a source fact, and this is
labelled as such.

**The direction, stated as a reading and not as a theorem.** Models are fitted **per
pair** (`body.py`), so a model that has seen an observation's own target fits that
pair's idiosyncratic noise; idiosyncratic components are close to independent across
pairs, which **dilutes `|r|`, lowers `c`, lowers `rho_x` and raises `N_eff`** — the
anti-conservative direction, and the same mechanism c-7 records. It is a reading
because shared features could equally overfit common structure; it is enough to make
"frozen before the data" an incomplete defence under §8.4.11's A-ω-5 standard, which is
why the leakage-safe arm is taken.

**And the interaction with c-6 had to be worked out, because an earlier drafting of
this limb got its direction wrong.** A leakage-safe generator cannot produce a
prediction for the earliest DESIGN dates — there is nothing yet to fit on — so **some
prefix of the 310-date index is structurally trade-free under every admissible option**,
and under the naive application of the committed M1 shape (train on the head, predict on
the tail) it would be roughly the whole training portion.

*The earlier drafting called that "a large, invisible, anti-conservative distortion" and
refined the `c` index to a declared generation span on the strength of it. **Both are
withdrawn.** The direction claim is measurably false.* The structural prefix is
**common to every pair simultaneously** — no model exists for any of them — and a
**common** zero block is not c-7's case at all. c-7's idle dates arrive on *different*
dates per pair, which dilutes; a shared block adds a common-mode component instead.
The **sign** is established by c-7's own fully-specified counterexample —
`p = [1, 2, 3]`, `q = [3, 2, 3]`, centred `r = 0` on the active dates and zero-limit
`r = 16/√308 ≈ 0.912` — which is a **common** zero block raising `|r|` from zero.
**`NON_NORMATIVE_DIAGNOSTIC_ONLY`**, and **no magnitude is claimed**: an earlier drafting
quoted `E|ρ|` figures from a synthetic model it did not specify well enough to
reproduce, and the sign alone selects the arm. So the effect is **conservative** — it
*raises* `c`, raises `rho_x` and *lowers* `N_eff`.

**So Ruling c-6 stands unamended, and that is the stricter arm.** The `c` index remains
the full common DESIGN UTC calendar-date index of c-6, and a structurally trade-free
date carries **zero** under c-7's rule. Refining the index to a declared generation span
would have been an **amendment to a prior ruling of this packet with no conservatism
argument behind it**, and under CLAUDE.md's stricter-reading rule the unamended arm
governs. It also removes a freedom the refinement would have created: with no span to
declare, there is no span to choose.

**Two things are recorded rather than smoothed.** First, **c-7's economic justification
does not reach these dates** even though its rule does: "a day on which the strategy did
not trade is a realised daily outcome of zero" is not true of a date on which the
strategy **could not** trade because no model existed. The rule is kept because its
direction is conservative, not because the justification extends.
**`STRUCTURALLY_TRADE_FREE_DATES_ARE_CARRIED_AS_ZEROS_ON_DIRECTION_NOT_ON_C_7_S_GROUND`.**
Second, the **generation method still determines how many such dates there are**, so it
is a lever on `c` — **conservative on this limb only**, and the net across its limbs is
**not** signed (see the fold-count note above). It is bound regardless: the method is
frozen under c-12, and **it may not be selected for the span or the sparsity it
produces**, nor adjusted after any observation.
**`C_GENERATION_METHOD_MUST_NOT_BE_SELECTED_FOR_THE_SPAN_OR_SPARSITY_IT_PRODUCES`.**

**One route is still named and refused.** Restricting the `c` series to a single
chronological cut's out-of-sample **tail** — dropping the rest of the index rather than
carrying it as zeros — is forbidden, because it shrinks the index and is barred by c-6
and c-9. **`C_SERIES_INDEX_MAY_NOT_BE_SHRUNK_TO_THE_OUT_OF_SAMPLE_TAIL`.**

**What is not ruled — and it is not direction-neutral.** The generation method's own
parameters — fold count, window length, step, the trailing-gap size if a rolling origin
is used — are **implementation**, constrained by c-12 below rather than chosen here.
**`C_GENERATION_METHOD_PARAMETERS_ARE_IMPLEMENTATION_BOUND_BY_C_12`.** Two of them carry
a direction, and deferring them without saying so would repeat the error this packet has
already had to correct twice:

- **The trailing gap.** §4's R-2 derives it — ≥ the longest feature lookback in bars,
  **224 M15 bars** for an H4 ATR-14 under prereg §7 — and R-2 is a proposal, so the
  number is not committed. A **smaller** gap yields more predictions and, through the
  estimator's `√(2/π)/√(n−1)` null floor, a **lower `c` and a higher `N_eff`**.
  **`TRAILING_GAP_IS_A_KNOWABLE_DIRECTION_PARAMETER_DEFERRED_NOT_NEUTRAL`.**
- **The fold count.** More folds mean shorter fitting windows, noisier per-pair models
  and therefore **more pair-idiosyncratic noise** — the same thing this ruling says a
  leaked fit adds, and which it says dilutes `|r|` and raises `N_eff`. So the fold count
  runs **conservative through the prefix limb and anti-conservative through fit
  quality**, and **the net is not signed**.
  **`C_GENERATION_FOLD_COUNT_NET_DIRECTION_ON_C_IS_NOT_ESTABLISHED`.**

**And the rule must be checkable, which today it is not.** Nothing in the record
distinguishes a leakage-safe generation from Option A: §8.5.0's R-6 carve-out asks for
the index membership rule, the cardinality, the 190-entry count and the per-pair
non-idle counts, and **an Option-A run reports the first three identically**. So the
R-6 record must additionally carry the **generation method identity**, its **fold /
window / step boundaries as explicit UTC date ranges**, and, per fold, **which fitted
statistics were used and over what rows** — the spread table, `W̄`/`L̄`, the calibration
and any scaler. Without those three fields this ruling is unfalsifiable from the record.
**`C_LEAKAGE_RULE_IS_UNCHECKABLE_UNTIL_THE_GENERATION_RECORD_EXISTS`** — classified
**implementation and checkability**, on the same footing and with the same recorded
contest as `C_INDEX_SET_NOT_RECORDED_IN_ANY_ARTIFACT`: §8.4.13's default would make an
unclear classification a blocker, and the record extension above is what keeps it from
being one.

#### 8.7.3 Ruling c-12 — every input that can move a `c` value is frozen first

**`ALL_DECISION_BEARING_C_MAP_INPUTS_MUST_BE_FROZEN_BEFORE_C_MEASUREMENT`.**

c-10 froze the map's **keys**; this freezes its **values**. The decision-bearing inputs,
enumerated so the freeze has a scope rather than a slogan:

| Input | Status before this ruling |
| --- | --- |
| the registered candidate set and each `config_id` / `ev_min` | frozen by c-10 |
| the **generation method** and its parameters | ruled at c-11; parameters frozen **here** |
| model family, hyperparameters, class weighting, calibration method | frozen by prereg §8 |
| the **feature list and its definitions** | frozen at the design audit (prereg §7) |
| the **warm-up `W`** | `[FIXED-AT implementation]` — **frozen here relative to `c`** |
| the **cost model and cost table**, and the cost **cell** | table frozen by prereg §5; the cell ruled by c-4 |
| the **pair universe** | frozen by NR-K / c-1 |
| the **DESIGN span** and the date index | committed / c-11 |
| the **day-attribution rule** | ruled by Q10(i) |
| **Calendar A slot membership**, where it reaches DESIGN event eligibility | Ruling ω-12/ω-13 |
| **Calendar B event-eligibility semantics**, where they reach current Family A | T-6 puts approval "before gate 7" — **after** any point the map could be built |
| **rollover exclusion window** | prereg §5 permits gate 3a / the design audit to **widen** it |
| **concurrency / exposure caps** | `[FIXED-AT design audit]` |
| the idle-day rule, common date index, coefficient, weighting, absolute-value placement, undefined-case disposition | ruled by c-2…c-8 |
| **`W̄` / `L̄` and the estimator that produces them** | prereg §8 freezes only "never re-fit on validation/holdout" — **no estimator, conditioning set or within-design fit span is registered**, and `EV_d ≥ ev_min` decides which DESIGN bars trade |
| **Label geometry** — the `TP_dist`/`SL_dist` multipliers, the ATR-14 period, the SL-first tie rule, timeout mark-to-market on the exit side, horizon 24 | prereg §6 / Ruling 6 — every trade's PnL and its exit date |
| **The cost-hurdle eligibility rule** `1.5 × ATR14 ≥ 2.0 × cost` | prereg §6 / Ruling 6 — whether a bar is an event at all |
| **M15 aggregation identity** — `n_source_bars == 15`, UTC bucketing, per-side OHLC, missing-minute policy, weekend bucket termination, the spread convention | prereg §4 / Ruling 3, `[FIXED-AT gate 3a]` — which M15 bars exist to be events |
| **The entry/exit marker convention** — decision bar `i`, next-bar fill, `exit_bar = i + 1 + offset` | prereg §6 and the committed constructors — the date every trade is attributed to |
| **Per-pair pip-size authority** | prereg §4 / §11 — the eligibility comparison and the net series |

**The rule.** **No value in the `c` map may be measured until every input above is
frozen**, and once measured, none of them may change for current Family A.

**The enumeration governs, and it is *not* claimed complete by inspection.** Where an
input is decision-bearing but unlisted,
`ALL_DECISION_BEARING_C_MAP_INPUTS_MUST_BE_FROZEN_BEFORE_C_MEASUREMENT` governs and this
table is read as illustrative, **never as an exhaustive licence** — and **no session may
classify an input out of scope**; an unclear case is a human + ChatGPT question
defaulting to blocker. *Six rows were added after an independent round found them
missing, `W̄`/`L̄` among them — which c-11 names by name — so the table has already been
wrong once by omission.*
**`C_12_ENUMERATION_IS_NOT_CLAIMED_EXHAUSTIVE_AND_NO_SESSION_MAY_CLASSIFY_AN_INPUT_OUT_OF_SCOPE`.**

**And one committed route reconfigures an input on a design-data observation that is
not `c`.** prereg §6: "*a **median eligible ratio < 3.0 triggers design-audit
reconsideration before implementation***". `C_OBSERVATION_MUST_NOT_TRIGGER_UPSTREAM_RECONFIGURATION`
is scoped to observing **`c`** and does not reach it.
**`PREREG_SECTION_6_BARRIER_RATIO_RECONSIDERATION_IS_AN_UNCLOSED_UPSTREAM_ROUTE`** —
recorded, not closed, because closing it would amend a committed prereg clause.
**`THE_MAP_IS_BUILT_ONCE_AND_A_CHANGED_INPUT_IS_NOT_A_NEW_MEASUREMENT_IT_IS_A_RESELECTION`**
— rebuilding the map after moving an input is variant-shopping under another name.

**The freeze has no recorded anchor, and that is registered rather than assumed away.**
No locus records what these inputs were when the map was built, nothing distinguishes a
first build from a rebuilt one, and prereg §8's seed policy is
`bounded_not_bitwise_guaranteed`, so one `config_id` need not reproduce one trade set.
**`NO_LOCUS_RECORDS_THE_FROZEN_C_MAP_INPUT_SET`** ·
**`C_INPUT_FREEZE_CHECKABILITY_IMPLEMENTATION_PENDING`** — classified
`DEFERRED_PRODUCTION_CHECKABILITY` on the same footing as Ruling ω-13's residual 5, and
**the deferral lapses** where the execution path cannot record which input set produced
a map.

**And observing `c` may not reach back.**
**`C_OBSERVATION_MUST_NOT_TRIGGER_UPSTREAM_RECONFIGURATION`.** A measured `c`, a derived
`rho_x`, an `N_eff` or a sample-floor verdict may **not** cause any change to the model
fit method, the generation method or its span, the feature set, calendar eligibility,
the cost model or cell, the `ev_min` set, the DESIGN span, the date index or the
idle-day rule. This closes the last direction c-10 left open: c-10 barred selecting
*among* configurations on `c`; this bars reconfiguring *the inputs* on `c`.

**The Calendar B collision, resolved without pulling the operational calendar
forward.** `C_MAP_INPUT_FREEZE_CONFLICTS_WITH_T6_HOLIDAY_CALENDAR_SCHEDULE` is closed by
splitting the artifact from the semantics, which is what Ruling ω-13(b) already does for
the event sequence:
**`POST_C_FREEZE_ELIGIBILITY_CHANGES_MUST_NOT_RETROACTIVELY_CHANGE_C_DESIGN`.**

- The **subset of eligibility semantics capable of changing current Family A's
  DESIGN-span event inclusion or daily PnL** must be frozen **before** the `c` map is
  measured — with `FAMILY_A_ELIGIBILITY_SEMANTICS_MAY_NOT_DELEGATE_TO_A_POST_FREEZE_ARTIFACT`
  (Ruling ω-13(b)) governing, so a rule may not satisfy the freeze by pointing at a
  table approved later.
- **The operational and production remainder of Calendar B may land on its committed
  schedule.** A later operational or production calendar is not required to be frozen
  early; T-6's "approved before gate 7" stands for **that** remainder only. *An earlier
  drafting said "everything else", which is broader than the justification beneath it.*
  **It does not reach any semantic capable of changing Family A event inclusion in the
  validation or holdout role**: those touch no DESIGN bar and so fall outside this
  ruling's `c` test, but they remain bound by
  `OMEGA_EVENT_ELIGIBILITY_RULES_MUST_BE_PRE_DATA_FROZEN`, which is **not** span-scoped.
  **`C_12_S_DESIGN_SPAN_SCOPE_TEST_DOES_NOT_RELAX_OMEGA_13B_FOR_THE_FORWARD_ROLES`.**
- A later Calendar B **may not retroactively alter a frozen `c_design` value**, and a
  `c` re-measured under later eligibility semantics is **not** the frozen `c` and may not
  be substituted for it.

*So the conflict was between a **schedule** and a **scope**, and the scope is what
narrows.* **`ONLY_THE_FAMILY_A_REACHING_SUBSET_OF_CALENDAR_B_IS_PRE_C_FROZEN`.**

**No judge is named for that scope, and a scope rule without one is a dismissal tool.**
Which Calendar B semantics "reach current Family A" is the freeze's entire operative
content, and neither Ruling ω-13(b) nor this ruling says who decides. The
classification is a **human + ChatGPT** act on ω-13's boundary, never a session's own,
and it defaults to **in scope**. Note also that this ruling widens the test from event
**inclusion** to inclusion **or daily PnL**, while the carried prerequisite
`PRE_DATA_FAMILY_A_EVENT_ELIGIBILITY_CONTRACT_REQUIRED_BEFORE_CONTINUATION` names only
eligibility. **`CALENDAR_B_SCOPE_CLASSIFICATION_HAS_NO_NAMED_JUDGE`** ·
**`PRE_DATA_FAMILY_A_CONTRACT_MUST_NOW_ALSO_NAME_THE_PNL_REACHING_SUBSET`.**

**Ordering, restated end to end.**

> **1.** freeze the candidate configuration set (c-10) → **2.** freeze every
> decision-bearing input above, including the Family-A-reaching eligibility semantics →
> **3.** generate the DESIGN prediction and per-pair daily net PnL series under c-11 →
> **4.** compute `c_design[config_id]` for every registered candidate under c-1…c-9 →
> **5.** freeze the complete map → **6.** only then may validation be observed for
> operating-point selection → **7.** validation selects one `config_id` → **8.** the
> already-frozen `c` is attached mechanically.

**No step of this is an authorisation**, and nothing here authorises a DESIGN-span run.

#### 8.7.4 Ruling Q10(iii) — the Sharpe clock, the idle day and the factor, decided together

**`Q10_III_RULED_COMPLETE_UTC_CALENDAR_DATE_SHARPE_INDEX_IDLE_ZERO_ANNUALISED_BY_SQRT_365`.**

Three limbs, decided as one because none of them is answerable alone:

1. **Sampling clock.** The daily portfolio Sharpe is computed on the **complete UTC
   calendar-date index of the evaluated role's span** — every UTC calendar date from the
   role's start date through its end date inclusive — **not** on dates that happen to
   carry a trade.
2. **Idle days.** A date with no trade attributed to it carries **zero** realised PnL.
   Trades are attributed by **Q10(i)**, unchanged — the exit UTC date — and multiple
   trades on one date are **summed**.
3. **Annualisation.** `√365`, the dates-per-year of that index.

**What "the role's span" is, and what it is not.** The index endpoints are the
**declared** role boundaries Q10-B requires human + ChatGPT to declare — never the first
and last date carrying a trade. **Forbidden: any Sharpe index whose membership depends
on activity**, including trimming leading or trailing idle dates, restricting to the
attributed-trade hull, or dropping interior idle runs; removing idle dates raises
`|mean/sd|` for **every** series, so the favourable end is knowable with no data.
**`SHARPE_INDEX_MEMBERSHIP_MUST_NOT_DEPEND_ON_ACTIVITY`.**

**Two things this leaves genuinely open, said rather than assumed.** The roles are
declared as **instants**, and the instant→date convention that fixes the first and last
index dates is still
`DURATION_BOUNDARY_ARITHMETIC_AND_ENDPOINT_CONVENTION_PENDING_HUMAN_CHATGPT_RULING`; one
boundary date is worth roughly a per cent of the value at a two-month span, so the
convention must be fixed **before** any Sharpe is computed and may not be chosen after
seeing one. And **membership at the right edge** — a trade whose Q10(i) **exit** date
falls after the role's end date — is ruled as c-6 ruled it for `c`: **membership is
decided by the attributed date, the trade is not part of the series, it is not clamped
to the last in-index date, and the index is never extended**.
**`SHARPE_SERIES_MEMBERSHIP_IS_DECIDED_BY_THE_ATTRIBUTED_DATE_AND_THE_INDEX_IS_NEVER_EXTENDED`.**

**And this limb is instantiable only for DESIGN today.** The DESIGN span is two
committed constants; the validation and holdout spans are `PENDING` and the forward
epoch does not exist. **Q10(iii) is ruled as a contract and its forward-role index is
not constructible until the Q10-B declaration is taken** — the "ruled, instantiation
pending" shape §8.4.0 records for `ω`.
**`Q10_III_RULED_INSTANTIATION_PENDING_THE_Q10_B_DECLARATION`.**
   **`SHARPE_ANNUALISATION_FACTOR_IS_SQRT_365`.** Leap years are **not** distinguished:
   **365.2425** dates per Gregorian year against 365 is a **0.033%** change in a constant
   that does not depend on span length — immaterial against a threshold quoted as `0.8`
   — and even a leap year's 366 is 0.14%. *An earlier drafting justified this by "at the
   frozen minimum spans", which is a non-sequitur: the constant is span-independent.*
   Inventing a year-specific factor would be machinery with no authority behind it.

**Why the clock had to be ruled first.** `√252` was never committed — it is an M1
default in a helper prereg §11 admits only "after audit/wrapping", and the gate-4 audit
tightened nothing about the Sharpe, so it does not carry by reuse either. And it is
**incoherent** with the committed series: annualising by `√k` presumes `k` observations
per year *on the series' own clock*, and the committed series is indexed on **active
dates**. §8.6.1 sets out the two coherent families; this ruling takes **(B)** — complete
index, data-independent factor — over **(A)**, whose factor is the realised
observations-per-year and is therefore a **function of the measured activity rate**.
**`SHARPE_ANNUALISATION_CLOCK_MUST_BE_PRE_DATA_FIXED`**: estimating an annual active-day
count from realised data and annualising by it, varying the factor by configuration,
using coverage to choose the factor, or choosing between 252 and 365 after seeing which
improves the Sharpe are all **forbidden**.

**And the two limbs may not be adopted apart.** `√365` on the **committed active-date
index** is §8.6.1's reading **(D)** — the **most permissive of the five**, `1/√a > 1` at
every active share below 1 — and `SHARPE_ANNUALISATION_FACTOR_IS_SQRT_365` may **never**
be cited for it. The complete index left on `annualised_daily_sharpe`'s committed `252`
default is reading **(E)**, which `body.py:228` and `:535` reach by simply not passing
the argument. **Partial adoption in either direction is forbidden: the index and the
factor change together or not at all.**
**`SHARPE_INDEX_AND_FACTOR_MAY_NOT_BE_ADOPTED_SEPARATELY`.**

**What this does and does not move — checked at source rather than assumed.**

- **Operating-point selection moves, and this is the reach that matters.** The
  committed selection metric is prereg §8's validation net expectancy subject to the
  turnover budget, which is per-trade and annualisation-free; the committed
  **implementation** does something else — `select_threshold` takes the **argmax of the
  validation `daily_portfolio_sharpe`**, fed from `body.py:228` and `:535`, with **no
  trade-count floor**. Under `√252` on an active index the factor is constant across
  candidates and the argmax is invariant to it; under the ruled complete index the
  effective per-candidate scaling carries `√(activity)`, which **penalises sparser
  candidates and can change which operating point reaches the holdout**.
  **`Q10_III_REACHES_THE_OPERATING_POINT_ONLY_VIA_AN_IMPLEMENTATION_THAT_DIVERGES_FROM_THE_COMMITTED_SELECTION_METRIC`
  is carried, not discharged**, and
  **`Q10_III_MUST_NOT_BE_RESELECTED_AFTER_OBSERVING_ANY_METRIC_IT_MOVES`** binds
  validation observations for the reason Q10(i)'s does.
- **The Sharpe itself moves, and its two limbs move it on different footings.** The
  **factor** slot was genuinely empty — no committed source names one — so limb 3 fills
  it. The **index** is not an empty slot: prereg §9's frozen daily-aggregation sentence
  says "Sharpe is computed on **UTC-day portfolio sums** (as in M1)", and §8.5.0's
  load-bearing grammatical reading holds that the parenthetical **carries the
  aggregation shape**. **Limb 1 therefore changes a committed construction**, on the
  authority prereg §9 itself reserves — "refer them back for a **new human + ChatGPT
  ruling**" — not by finding a gap. *An earlier drafting said the ruling "fills an empty
  slot rather than changing a committed value", which is true of the factor and false of
  the index; withdrawn.* Ruling 10 bars *loosening a threshold*; `≥ 0.8` is untouched,
  and the change itself falls under `SECTION_8_7_AMENDMENT_CLASSIFICATION_NOT_SETTLED`.
- **The zero-fill limb's own direction is knowable with no data, and it is the
  tightening one.** Inserting idle zeros multiplies `mean/sd` by
  `(m/N)·√[(N−1)(Q−S²/m)/((m−1)(Q−S²/N))] ≤ 1`, with equality only when the index is
  fully active — so **limb 2 alone weakly reduces the *magnitude* of the reported
  Sharpe for every series**, checked algebraically and on 80,000 randomised synthetic
  series with **no counterexample and a maximum ratio of exactly 1.0**. **It does not
  reduce the *signed* value, and an earlier drafting said it did.** For a
  **negative-mean** series the same factor `≤ 1` moves the reported Sharpe *toward zero*,
  i.e. **upward** — measured: `m = 3` of 61 goes from `−19,085.9` to `−4.31`, `m = 20`
  from `−3,198.7` to `−13.23`. `select_threshold` argmaxes the **signed** value, so where
  a candidate set is uniformly loss-making the complete index **rewards the sparsest
  candidate** rather than penalising it (`−4.31` at `m = 3` beats `−13.23` at `m = 20` at
  equal per-active-day quality). §8.7.4's "penalises sparser candidates" is **withdrawn
  as one-sided**, and the anti-conservative arm is named under §8.4.11's A-ω-5 standard
  rather than left implicit. Limb 3 alone moves the value the other way by a fixed
  `√(365/252) ≈ 1.204`.
  **`SHARPE_IDLE_ZERO_FILL_WEAKLY_REDUCES_THE_MAGNITUDE_AND_RAISES_A_NEGATIVE_SHARPE`** ·
  **`ZERO_FILL_REWARDS_SPARSITY_ON_THE_NEGATIVE_BRANCH`** ·
  **`NON_NORMATIVE_DIAGNOSTIC_ONLY`**. *The earlier token
  `SHARPE_IDLE_ZERO_FILL_WEAKLY_REDUCES_THE_REPORTED_SHARPE` is **withdrawn as
  directionally false**.*
- **⚠ Superseded in part by Ruling Q10(iii)-a (§8.8.4).** The guards now run on the
  **pre-fill in-index active set**, so what follows describes the **ungated** reading
  that ruling replaced; `COMPLETE_INDEX_DISABLES_THE_DEGENERATE_SHARPE_GUARDS` is no
  longer an accepted cost for the `m = 1` and all-equal cases, and the residual that
  survives is recorded at §8.8.4. **Two fail-closed guards stop firing, and that is where
  limb 2's direction reverses.**
  `annualised_daily_sharpe` returns `0.0` for fewer than two observations or zero
  variance. On the committed active-date index those fire on genuine sparsity; on a
  complete index the first can never fire and the second only when no trade exists. A
  single active date on an `N`-date index yields exactly `sign(x)·√(365/N)` — **+2.45 at
  a 61-date span**, above the frozen `≥ 0.8`, where the committed code reports `0.0`
  (verified against the implementation). **At holdout this cannot produce a pass**: the
  `≥ 1,000` trade, `≤ 40`/day and `≥ 0.60` coverage rows are conjunctive and force tens
  of active dates. **At validation it is not contained** — `select_threshold` applies no
  trade-count floor — so a degenerate candidate becomes selectable that the committed
  code could never select. **`COMPLETE_INDEX_DISABLES_THE_DEGENERATE_SHARPE_GUARDS`**,
  an accepted cost, and the reason the selection bullet above is not theoretical. Its direction
  against the M1 default is **conditional**, not uniform: `√252` on an active index over
  `√365` on the complete index is `√(252/(365a))` at active share `a`, which exceeds 1
  below `a ≈ 0.690` and is **below** it above — so no claim is made that this ruling is
  the conservative arm, only that it is the **coherent** one.
- **Max equity drawdown does not move at all, and that is provable.**
  `max_equity_drawdown` is a running peak-to-trough on the cumulative daily sum;
  inserting zero-PnL dates leaves every partial sum unchanged and merely repeats the
  previous equity level, so the running peak and the maximum peak-to-trough gap are
  **identical**. Verified against the implementation and by synthetic arithmetic.
  **`MAXDD_IS_INVARIANT_TO_IDLE_DATE_ZERO_FILL`** · **`NON_NORMATIVE_DIAGNOSTIC_ONLY`**.
  The frozen `≤ 0.15` row is untouched.
- **Daily coverage does not move**, and is **not** re-denominated. `daily_coverage`
  computes `len({t.day for t in trades}) / holdout_trading_days` from the **trade list**,
  never from the Sharpe series; the two share no object. Ruling Q10(ii)'s denominator —
  the UTC calendar dates the approved calendar authority recognises as carrying at least
  one expected M15 slot — stands unchanged, and the frozen `≥ 0.60` threshold is
  untouched. **This ruling deliberately does not give coverage and the Sharpe a common
  index**; metric-specific semantics stay separate. *One consequence, stated because it
  removes a bound rather than adding one:* §8.6.1's
  `Q10_III_SQRT_252_INFLATION_IS_BOUNDED_BY_THE_FROZEN_COVERAGE_ROW` rested on index and
  denominator sharing one clock, and this ruling separates them, so **it does not
  survive and is WITHDRAWN**. Its arithmetic was wrong independently: `1/√coverage` is
  the ratio for the *active-index × `√365`* reading, not for `√252`, whose closed form
  gives `√(252/(365 × 0.60)) ≈ 1.07` at the floor. **No upper bound on the ratio is
  claimed.**
- **Turnover does not move by this limb.** `n_days` is computed from the trade list, not
  from the Sharpe series. What moves it is §8.7.5, and only its denominator.
- `cost_sensitivity`'s per-cell Sharpes move with the primary one; they carry no frozen
  threshold, the stressed-cost row being denominated in day-independent expectancy.

**The consistency with NR-L is noted and not leaned on.** c-6 and c-7 already take a
complete UTC calendar-date index with idle = zero for `c`, and this ruling takes the same
shape for the Sharpe. **That is consistency, not entailment**: no committed source makes
NR-L's index govern the Sharpe, and this limb is ruled on its own ground — the
incoherence of `√252` with an active-date index — not derived from c-6.

**And no market-hours fact is authored.** "Every UTC calendar date in the role's span"
needs no calendar authority; whether any of those dates can carry a trade is a
calendar-authority question this ruling does not answer, exactly as c-6 does not.

**Derived versus ruled.** *Derived*: that `√252` is not committed; that it is incoherent
with the committed active-date index; that maxDD is invariant to zero-fill; that
coverage and turnover do not share the series. *Ruled*: the complete-date index, idle =
zero, and `√365`.

#### 8.7.5 Ruling — the turnover-ceiling day

**`TURNOVER_CEILING_COUNTS_TRADES_BY_ENTRY_UTC_DATE`.**

Each trade is counted **exactly once**, against the UTC calendar date containing its
**entry** marker. A trade whose exit falls on a later date does **not** generate a second
count; several entries on one date each count; an open position spanning dates remains
**one** initiation. No position-duration rule is created.

**Why entry, and why this is not inherited from Q10(i).** The turnover ceiling
constrains **trading activity and initiation frequency** — how often the strategy commits
— whereas Q10(i) fixes the date on which an **outcome becomes realised**. They measure
different things, and reasoning "PnL uses the exit date, therefore turnover does too"
would be inheritance rather than a ruling. Recorded explicitly:
**Q10(i)'s realised-outcome date is the exit date; the turnover initiation date is the
entry date**, and the two are deliberately different.
**`TURNOVER_DAY_MUST_NOT_BE_BOUND_TO_THE_PNL_ATTRIBUTION_DAY_BY_INHERITANCE`.**

**What the committed implementation makes of this, stated precisely.** `turnover()` is
`n_trades / n_trading_days`, and **its numerator carries no date at all** — every trade
counts once regardless. So under the committed **mean** reading this ruling fixes only
which dates form the **denominator**: the set of distinct **entry** UTC dates. Under a
**per-day-cap** reading it would also fix the per-date numerator. **Which of those two
the frozen row means is a separate question this ruling does not decide** — the mean is
a reading of the implementation's own docstring, the frozen row says only "≤ 40
trades/day portfolio-wide", and settling it would change the ceiling's meaning.
**`TURNOVER_CEILING_MEAN_VERSUS_PER_DAY_CAP_STILL_UNREGISTERED`.**

**And it does not touch the axis Ruling Q10(ii) warned about.** Q10(ii) left the
ceiling's day open and warned that reading it in **calendar** days would widen gate 4's
corridor by ~42% — "a loosening Ruling 10 forbids, and one that citing this ruling must
not achieve". Entry-versus-exit is a different axis: **both are active-date sets**, and
this ruling takes neither toward calendar days. The
active-versus-calendar-versus-calendar-authority question stays exactly where Q10(ii)
left it. **`TURNOVER_DENOMINATOR_ACTIVE_VERSUS_CALENDAR_AXIS_STILL_UNREGISTERED`.**

**"Entry marker" is named, because two instants sit one bar apart.** The turnover date
is the UTC calendar date of the **decision bar** `TradeSignal.entry = i` — the marker
both committed `MetricTrade` constructors already use — **not** the next-bar fill `i+1`
that prereg §6's ask-entry geometry creates. The two differ whenever a signal falls on a
date's last M15 bar, and the ruling's own rationale ("how often the strategy commits")
would otherwise point at the fill while its words point at `i`.
**`TURNOVER_ENTRY_MARKER_IS_THE_DECISION_BAR_NOT_THE_NEXT_BAR_FILL`.**

**The turnover figure reaches experiment selection, so the day rule is locked like
Q10(i)'s.** §9.V requires the kill gate to be met "within the turnover budget" and
Ruling 9's selection metric is "validation net expectancy **subject to the turnover
budget**", so this rule can change which operating point reaches the holdout and whether
the holdout is reached at all.
**`TURNOVER_DAY_MUST_NOT_BE_RESELECTED_AFTER_OBSERVING_ANY_TURNOVER_FIGURE_IT_MOVES`**,
binding validation observations too. **And the two axes left unregistered are locked
pre-observation on the same footing** — the mean-versus-per-day-cap reading and the
active-versus-calendar denominator may not be settled after any turnover figure is seen.
Their **permissive arms are named**, so that leaving them open is not mistaken for
leaving them neutral: `max ≥ mean` makes the **mean** the permissive reading, and it is
also the incumbent; and §8.6.6's **larger** denominator is the permissive denominator.
**`THE_UNREGISTERED_TURNOVER_AXES_ARE_PERMISSIVE_ARMED_AND_LOCKED_PRE_OBSERVATION`.**

**Authority classification.** **Absent, therefore ruled.** No committed source names an
attribution date for turnover; the implementation has no attribution rule to read off,
because its numerator is date-free.

#### 8.7.6 Status after §8.7

**`NR_L_MINIMUM_RESEARCH_CONTRACT_RULED_PENDING_IMPLEMENTATION_AND_DESIGN_MEASUREMENT`** ·
**`CLOSURE_CLAIM_WITHHELD_PENDING_A_SEPARATE_INDEPENDENT_ROUND`** ·
**`Q10_III_RULED_COMPLETE_UTC_CALENDAR_DATE_SHARPE_INDEX_IDLE_ZERO_ANNUALISED_BY_SQRT_365`**
(instantiation pending the Q10-B declaration) ·
**`TURNOVER_CEILING_COUNTS_TRADES_BY_ENTRY_UTC_DATE`.**

**⚠ The closure claim is WITHHELD, and the reason is a breach this section committed.**
An earlier drafting of this paragraph claimed
`NO_NR_L_MINIMUM_RESEARCH_CONTRACT_BLOCKER_REMAINS` and grounded it on "**this round's
review has run and returned (§12.15)**". **§12.15 did not exist when that was written**:
the round's roles had been dispatched and had not reported, and the citation was a
**forward reference asserted in the past tense** — the same fabricated-audit-completion
shape §12.5 records and that this repository's governance forbids outright. It is
recorded here rather than quietly repaired.

**The claim is therefore not made in this round.** It has now been claimed and withdrawn
**twice on the merits**, and once more grounded on a review record that did not exist —
three attempts, each in the same round as the ruling meant to earn it. The review has
since returned and is recorded at **§12.15**, and it found further defects in this very
section (the unfrozen `W̄`/`L̄` and label-geometry inputs, the unlocked turnover axes,
the phantom citation itself). **`CLOSURE_CLAIM_WITHHELD_PENDING_A_SEPARATE_INDEPENDENT_ROUND`**
· **`CLOSURE_CLAIM_MAY_NOT_BE_MADE_IN_THE_SAME_ROUND_AS_THE_RULING_IT_RESTS_ON`** —
**withdrawn as over-broad at §8.8.0** and replaced by
**`CLOSURE_CLAIM_REQUIRES_COMPLETED_REVIEW_AND_NO_UNRESOLVED_MATERIAL_BLOCKER`**: the
failure was the phantom citation and the live blockers, not the calendar.

**What would let it stand.** The two blockers c-10 left *are* closed on their merits by
c-11 and c-12. What is missing is an independent round that returns **after** those
rulings and their fixes are in the record, and finds no remaining freedom capable of
moving `c`, `N_eff`, the event sequence or experiment selection. Ruling ω-13's boundary
governs that judgement: a human + ChatGPT call, never a session's own, with an unclear
case defaulting to blocker.

**What remains, classified — and none of it is a research-result freedom.**

- **Minimum execution prerequisites**: `MINIMUM_CALENDAR_IDENTITY_RECORD_REQUIRED_BEFORE_DATA_EXECUTION` ·
  `ONE_SELECTABLE_IMMUTABLE_CALENDAR_INSTANCE_WITH_RECORDED_IDENTITY_IS_AN_EXECUTION_PREREQUISITE` ·
  `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` ·
  `PRE_DATA_FAMILY_A_EVENT_ELIGIBILITY_CONTRACT_REQUIRED_BEFORE_CONTINUATION`.
- **Implementation and checkability**: `C_INDEX_SET_NOT_RECORDED_IN_ANY_ARTIFACT`
  (contested deferral) · `NR_L_PAIRWISE_COMPLETENESS_IMPLEMENTATION_PENDING` ·
  `NR_L_CONFIGURATION_COVERAGE_IMPLEMENTATION_PENDING` · `C_HAS_NO_PRODUCER_AND_NO_ARTIFACT` ·
  `C_GENERATION_METHOD_PARAMETERS_ARE_IMPLEMENTATION_BOUND_BY_C_12` ·
  `EXIT_DAY_ATTRIBUTION_BREAKS_ONE_COMMITTED_TEST_FIXTURE` ·
  `EXIT_DAY_ATTRIBUTION_REQUIRES_A_NEW_DAY_MAP_AT_THE_SECOND_CALL_SITE` ·
  **`TURNOVER_ENTRY_DAY_REQUIRES_A_SECOND_DAY_FIELD_ON_METRIC_TRADE`** (`MetricTrade` is
  a three-field frozen dataclass and `compute_all` derives the turnover denominator from
  the single `day` field; after Q10(i) makes it the exit date and §8.7.5 makes turnover
  the entry date, one field cannot serve both) ·
  **`NO_LOCUS_RECORDS_THE_FROZEN_C_MAP_INPUT_SET`** ·
  **`C_INPUT_FREEZE_CHECKABILITY_IMPLEMENTATION_PENDING`** ·
  **`C_LEAKAGE_RULE_IS_UNCHECKABLE_UNTIL_THE_GENERATION_RECORD_EXISTS`** ·
  `C_IMPLEMENTATION_MAY_NOT_REINTRODUCE_A_FORBIDDEN_ALIGNMENT_OR_SUBSTITUTION_BY_LIBRARY_DEFAULT`.
- **Accepted costs of frozen rules**, none selectable by anyone:
  `IDLE_ZERO_FILL_DILUTES_CORRELATION_IN_THE_SPARSE_REGIME` ·
  `C_EQUAL_WEIGHTING_IS_EXACT_ONLY_UNDER_EQUAL_PER_PAIR_VARIANCES` ·
  `CORRELATION_DATE_INDEX_COMMON_MODE_DIRECTION_NOT_ESTABLISHED` ·
  `MEAN_ABS_ESTIMATOR_HAS_A_POSITIVE_NULL_FLOOR_AT_310_DATES` ·
  `C_NEAR_DEGENERACY_IS_NOT_COVERED_BY_c_8_AND_MAY_NOT_BE_SILENTLY_REPAIRED` ·
  `SHARPE_DAY_SET_AND_CORRELATION_DAY_SET_ARE_DIFFERENT_OBJECTS` (**narrowed**: both are
  now complete UTC calendar-date indices with idle = zero, over **different spans** —
  the DESIGN span for `c`, the evaluated role's span for the Sharpe) ·
  `STRUCTURALLY_TRADE_FREE_DATES_ARE_CARRIED_AS_ZEROS_ON_DIRECTION_NOT_ON_C_7_S_GROUND` ·
  **`TURNOVER_DAY_SET_IS_A_FOURTH_DAY_OBJECT_AND_THE_ONLY_ACTIVITY_DERIVED_ONE`** —
  after §8.7 there are **four** distinct day objects, not two: `c` (complete index,
  idle = 0, DESIGN span) · Sharpe and maxDD (complete index, idle = 0, role span,
  exit-attributed) · coverage (exit-active numerator over Q10(ii)'s calendar-authority
  denominator) · turnover (**entry**-active denominator, activity-derived, no zero
  fill). Turnover alone stays on an **activity-derived** clock — the shape §8.7.4 refused
  for the Sharpe one subsection earlier — and that is recorded as the cost of keeping the
  strictest (smallest) denominator, not as a claim that the clocks agree ·
  **`C_DESIGN_IS_THEREFORE_NOT_THE_CORRELATION_OF_THE_FROZEN_PRODUCTION_CONFIGURATION`**.
- **Still unregistered, and recorded as questions rather than closed**:
  `TURNOVER_CEILING_MEAN_VERSUS_PER_DAY_CAP_STILL_UNREGISTERED` ·
  `TURNOVER_DENOMINATOR_ACTIVE_VERSUS_CALENDAR_AXIS_STILL_UNREGISTERED` ·
  `SELECTION_VERSUS_CERTIFIABILITY_ORDER_NOT_REGISTERED` (carried with the
  select-then-check default) · `KILL_GATE_READS_THE_REGISTERED_SET_NOT_THE_ELIGIBLE_SUBSET` ·
  `SQRT_K_FORM_ASSUMES_SERIAL_INDEPENDENCE_NOT_COMMITTED` ·
  `DURATION_BOUNDARY_ARITHMETIC_AND_ENDPOINT_CONVENTION_PENDING_HUMAN_CHATGPT_RULING` ·
  `SPAN_MINIMA_ARE_NOT_ELIGIBLE_EVENT_MINIMA`. **None of these is an NR-L statistical
  choice**, which is why an NR-L-scoped token could survive them. **But two of them
  meet the broader test stated above**: the mean-versus-per-day-cap reading and the
  active-versus-calendar denominator move the turnover figure, and §9.V's "within the
  turnover budget" makes that figure a **selection filter**, so they reach **experiment
  selection**. They are now **locked pre-observation** by §8.7.5 and their permissive
  arms are named, which is what keeps them from being live levers — but they carry no
  ruling, and any closure claim must be **scoped to NR-L's statistical choices** rather
  than presented as a claim that no research-result freedom remains anywhere in §8. The
  other three do earn the exemption: `SELECTION_VERSUS_CERTIFIABILITY_ORDER_NOT_REGISTERED`
  and `KILL_GATE_READS_THE_REGISTERED_SET_NOT_THE_ELIGIBLE_SUBSET` are one question from
  two sides with an explicit select-then-check fail-closed default, and
  `SQRT_K_FORM_ASSUMES_SERIAL_INDEPENDENCE_NOT_COMMITTED` is a form assumption common to
  **every** candidate factor and therefore not selectable — though limb 2 **aggravates**
  it rather than leaving it where it was, since a complete index makes a known fraction
  of observations structurally zero, a departure from the `√k` premise that needs no
  data to see.

**Amendment classification.** c-11 and c-12's freeze rule, the Calendar B scope split,
`C_OBSERVATION_MUST_NOT_TRIGGER_UPSTREAM_RECONFIGURATION`, Q10(iii)'s three limbs and the
turnover-day rule are all **additions no committed source carries**. **No prior ruling
of this packet is amended**: c-11's first drafting refined Ruling c-6's index and that
refinement is **withdrawn**, so c-6 and c-7 stand exactly as ruled. Whether such additions need a contract-amendment procedure
cannot be answered, because **no general contract-amendment procedure is registered
anywhere in this repository**
(`NO_GENERAL_CONTRACT_AMENDMENT_PROCEDURE_REGISTERED`, this packet's own token for that
absence). **`SECTION_8_7_AMENDMENT_CLASSIFICATION_NOT_SETTLED`.**

**No favourable classification is asserted anywhere in this ruling.** Q10(iii)'s
direction against the M1 default is **conditional and unclaimed**; c-11 **increases** the
work and forecloses the only generation shape the repository can currently produce;
c-12 forecloses four inputs that were free; and c-11's own first drafting is recorded
as **withdrawn on a measured direction that contradicted it**, rather than quietly
rewritten.

**Unchanged by this ruling.** The exact `T_v` / `T_h` / `D`
(`EXACT_WINDOW_NOT_READY_FOR_DECLARATION_FORWARD_EPOCH_DOES_NOT_EXIST`) · the boundary
arithmetic, purge, warm-up and interval convention of §8.6.2 · Q1, Q3, Q8, Q9 ·
`FR_19_SEPARATE_TEST_SAFETY_WORK_PR_OPEN` ·
`SAMPLE_FLOOR_REACHABILITY_NOT_DETERMINABLE_WITHOUT_MEASURED_INPUTS`, which nothing here
moves. **Real-data read remains unauthorised.**
**`PRODUCTION_READINESS_NOT_CLAIMED`** · **`NO_EXECUTION_PERFORMED`**.

### 8.8 The closing round — the `c` generator, the freeze rule, and the Sharpe guard order

A ruling received from human + ChatGPT and recorded here as **authority**. It is taken
**before** this round's review; the closure decision at §8.8.6 is taken **after** it, and
only on what the review actually returned.

**`C_13_RULED_CHRONOLOGICAL_EXPANDING_WINDOW_WALK_FORWARD_WITH_THE_COMMITTED_PURGE`** ·
**`C_14_ENUMERATION_DOES_NOT_LIMIT_THE_ALL_DECISION_BEARING_INPUTS_RULE`** ·
**`Q10_III_A_RULED_PRE_FILL_ACTIVE_OBSERVATION_GUARDS_PRECEDE_CALENDAR_ZERO_FILL`**

#### 8.8.0 A governance rule of this packet's own, corrected

§8.7.6 installed **`CLOSURE_CLAIM_MAY_NOT_BE_MADE_IN_THE_SAME_ROUND_AS_THE_RULING_IT_RESTS_ON`**
after the third failed closure attempt. **That rule is withdrawn as over-broad**, and no
committed authority independently requires it. Diagnosing the failure as *timing* was
wrong: what actually failed each time was that the review had not returned, that a
**phantom §12.15 citation** stood in for it, and that material blockers were still live.
A ceremonial extra round would have fixed none of those.

**`CLOSURE_CLAIM_REQUIRES_COMPLETED_REVIEW_AND_NO_UNRESOLVED_MATERIAL_BLOCKER`.** Closure
may be declared at the end of the same round **if and only if** all five hold: the ruling
is recorded; the required review roles **actually returned**; the decisive findings were
**re-verified by the lead at source**; every material research blocker that review exposed
is resolved; and **no fabricated or premature review-completion claim is used**. The
prohibition that matters is on the fabrication, not on the calendar.

#### 8.8.1 The existing prediction-generator machinery, reconstructed

Repo-wide, not package-scoped — the error §12.15 recorded.

| Machinery | Semantics, read at source | Fit for Family A |
| --- | --- | --- |
| `scripts/stage22_0e_meta_labeling.walk_forward_oos_folds` | Sorts `entry_ts`, cuts **5 quintiles**, yields **4** OOS folds; fold `k` trains on `entry_ts <= edges[k]` and tests on `(edges[k], edges[k+1]]`. **`k = 0` is dropped**, so the first quintile is never predicted | **Shape yes, semantics no.** It has **no purge**: a label whose horizon crosses `edges[k]` sits in training while its outcome sits in the test fold. Stage-22 / Phase-9 lineage, admissible under prereg §11 only **after audit/wrapping** |
| `fx_ai_trading.services.ml.training.train_walk_forward` (via `scripts/train_ml_baseline.py`) | Expanding window: `train_mask = ts < val_start`, fixed `val_months` step, first validation window starts at `min_ts + 30·train_months` days | **No.** Also **no purge**; month arithmetic is `30·months`, not calendar; and decisively **it emits no per-row predictions** — it computes `_compute_metrics(y_val_raw, y_pred)` and discards `y_pred`, returning only fold metrics and a model |
| `scripts/compare_multipair_v6_meta.py` | Runs Layer-1 inference over the model's **own `train_slice`** and argues in its docstring that this "is fine" | **No** — it is the in-sample shape c-11 refuses by name |
| `scripts/ml_step4/` (M1 lineage) | Single chronological 70/15/15 with purge/embargo; builds `prob_map` for `val_idx ∪ hold_idx` only | **No** — one cut, not a walk-forward, and it predicts only the tail |

| `scripts/compare_multipair_v3…v26` and `grid_search_tp_sl_conf.py` — 21 scripts, each `_generate_folds(train_days=90, test_days=7, step_days=7)` + `_compute_retrain_schedule` + per-fold `predict_proba` | **Rolling fixed-width**, not expanding, and the repository's **only** multi-pair per-row prediction generator. `compare_multipair_v6_meta.py` belongs to this family. **`v23_realism` does purge**, by row count — `tr_df.iloc[: -args.horizon]` — citing de Prado §7.1 and choosing rows over wall-clock because "*a timedelta-based purge can under-cut at Friday close*" | **No** — rolling fixed-width needs the trailing-gap number §4's R-2 leaves uncommitted, and it is fenced Phase-9 lineage |

**So the repository supplies the *pattern*, one adequate *purge*, and not the
*semantics*.** *An earlier drafting said "**both** walk-forward implementations" and
"**neither** carries a purge". Both are false repo-wide and are **withdrawn** — the
section announced itself as repo-wide and then repeated §12.15's own scoping error.* The
two **expanding-window** implementations carry no purge; the **rolling** family carries
one, in bars, on the same reasoning §4 gives — but that family needs a trailing gap an
expanding window does not, and it is fenced lineage prereg §11 admits only after
audit/wrapping. Forcing reuse would import either a leakage route or an uncommitted
number, so §9's instruction applies: **do not force reuse.**
**`EXISTING_WALK_FORWARD_MACHINERY_IS_FENCED_LINEAGE_NOT_AN_ABSENT_PURGE`** *(the earlier
`…_SUPPLIES_THE_PATTERN_NOT_THE_PURGE` spelling is superseded)*.

#### 8.8.2 Ruling c-13 — the generator's shape

**`C_13_RULED_CHRONOLOGICAL_EXPANDING_WINDOW_WALK_FORWARD_WITH_THE_COMMITTED_PURGE`.**

The DESIGN `c`-series is generated by a **chronological expanding-window walk-forward**:

> The DESIGN span is partitioned into contiguous, date-aligned blocks. **Block 0 runs
> from `DESIGN_START`'s date up to the first predicted date; every block after it is
> exactly one UTC calendar date.** For each block after the first, the model is fitted on
> **all earlier DESIGN observations**, **with the last admissible training bar placed 25 M15
> bars before the block's first bar** (prereg §3.2's `≥ horizon + 1 = 25`, counted in
> bars, and the convention `scripts/ml_step4/split.py` implements —
> `train_label_end = train_end − purge_bars`), and predicts **that block only**. Block 0 receives **no predictions**. One
> partition governs **every pair and every `config_id`**.

*The one-date block width is what makes the "single open parameter" claim true, and an
earlier drafting of this ruling left it unstated.* With any other width the block size is
a **second** free parameter with its own effect on `c`. Fixing it at one date is the
limit case of the family: it maximises each prediction's training history, minimises the
unpredicted prefix for a given start, and leaves the partition a **deterministic function
of the first predicted date alone**. Its cost is stated rather than hidden — a retrain
per pair per date — **one fit serves every `config_id`**, because the three
registered configurations differ only in `ev_min`, applied to `EV_d` **after** `p̂`,
exactly as the committed producer reuses one `prob_map` across every candidate. That is
20 × 232 = **4,640** fits, an **implementation** cost and not a contract question. *An
earlier drafting said "per configuration", which is both wrong arithmetic and worse than
wasteful:* under prereg §8's `bounded_not_bitwise_guaranteed` seed policy a per-config
refit would make `c_design[config_id]` differences partly **seed artifacts** of a map
c-10 keys by `config_id`. **`ONE_FIT_PER_PAIR_PER_BLOCK_SERVES_EVERY_CONFIG_ID`.** **`C_GENERATION_BLOCK_WIDTH_IS_ONE_UTC_DATE_SO_THE_PARTITION_HAS_ONE_PARAMETER`.**

*And this resolves a token §8.7.2 left unsigned.*
`C_GENERATION_FOLD_COUNT_NET_DIRECTION_ON_C_IS_NOT_ESTABLISHED` rested on "more folds
mean shorter fitting windows" — a **rolling**-origin mechanism, and §8.7.2's own list
scopes it to "window length, step, the trailing-gap size **if a rolling origin is
used**". Under an **expanding** window more folds shorten no fitting window: every block
trains on all prior data. The anti-conservative limb of that token therefore does not
transfer, and fixing the fold count at the family maximum takes no unsigned risk on it.
**`FOLD_COUNT_DIRECTION_TOKEN_DOES_NOT_TRANSFER_TO_AN_EXPANDING_WINDOW`.**

**Every property §8.7's c-11 requires is satisfied by construction**, and each is a
consequence of the shape rather than an added promise: no same-observation target
leakage, because a prediction's model is fitted strictly before its own block; strict
chronological causality; no validation or holdout observation anywhere, since the whole
construction lives inside DESIGN; a deterministic assignment of every prediction to its
training history; and no result-driven fold reselection, because the partition is frozen
under c-12/c-14 before measurement.

**Two properties are derived rather than chosen.**

- **The purge is 25 M15 bars**, not an invented number: prereg §3.2 freezes
  "purge/embargo ≥ horizon + 1 = **25 M15 bars** at every role boundary", and applying a
  frozen purge to an additional boundary type is a **tightening**. It is counted **in
  bars, never wall-clock** — §4 records why (a Friday-afternoon signal's 24-bar label
  reaches into Monday). *And it is sufficient at a block boundary, derivably:* the last
  admissible training bar sits at `block_start − 25`, its exit is at most 24 bars later
  by prereg §6's horizon, so its label closes at `block_start − 1` — **one bar clear of
  the block it must not see**.
- **A training label belongs to the fold that fitted it.** Because the cost table is
  fold-local (c-14) and prereg §6 makes the barriers functions of `cost`, the label of a
  given bar is **not one object across folds**: block `k`'s training labels are computed
  under block `k`'s cost table. That is ordinary walk-forward behaviour, but it is stated
  because "the label of bar *i*" would otherwise be ambiguous. **Each bar is *predicted*
  in exactly one block**, so every bar contributes exactly one prediction, under exactly
  one fold's geometry. **`TRAINING_LABELS_ARE_FOLD_LOCAL_PREDICTIONS_ARE_NOT_DUPLICATED`.**
- **And the fold whose geometry governs a bar is the fold that *predicts* it** — an
  earlier drafting scoped fold-locality to *training* labels and left this unsaid, which
  admitted a reading on which the frozen whole-DESIGN table governed the predicted bars.
  Block `k`'s own bars — their eligibility under `1.5 × ATR14 ≥ 2.0 × cost`, their
  `TP_dist`/`SL_dist` floors and their EV-gate cost term — are computed under **block
  `k`'s fold-local** cost table and `W̄`/`L̄`, never under the frozen whole-DESIGN table.
  A span-wide table applied to a predicted bar is the leakage c-11 refuses.
  **`THE_FOLD_THAT_PREDICTS_A_BAR_SUPPLIES_ITS_ELIGIBILITY_AND_BARRIER_GEOMETRY`.**
- **No trailing gap is needed.** §4's R-2 derives that a design placing training data
  *after* a tested slice needs a gap ≥ the longest feature lookback (≈ 224 M15 bars for
  an H4 ATR-14). **An expanding window has no trailing edge**, so that parameter never
  arises. *That is the reason this shape is chosen over a rolling fixed-width window*:
  it is the only member of the family that needs no unregistered number for its gap.

**One parameter remains genuinely unregistered, and it is isolated rather than
invented.** The **first predicted date** — equivalently the minimum training history
before the first block — has **no committed value**, and it materially changes `c`. The
retraining cadence does not: this ruling fixes it at **one retrain per block**, and the
block boundaries follow from the same parameter, so the **partition** has exactly
one open number.

**⚠ The *generator* does not, and an earlier drafting said "exactly one open number"
without that qualifier.** The **isotonic calibration's inner split** — its fraction, its
chronological or random placement, and whether the fit/calibration boundary itself
carries a purge — has **no committed value**. prereg §8 says only "a split **carved from
the training span only**", and §8.7.1's own authority table already records that "the
training span" is *named and never defined*; `scripts/ml_step4/contract.py` carries
`CALIBRATION = "none_raw_predict_proba"`, so no committed split exists anywhere; and the
one inner-split precedent is fenced stage-22 lineage with no purge. It reaches `c`
through `p̂` → `EV_d ≥ ev_min` → the DESIGN trade set, and its fit-quality limb carries
c-11's **knowable anti-conservative** direction: a larger carve leaves a smaller fit
portion, noisier per-pair models, more pair-idiosyncratic noise, a diluted `|r|` and a
higher `N_eff`. That is the identical argument by which the first predicted date was
raised to a blocker.

**`C_DESIGN_GENERATOR_PENDING_ONE_EXACT_PARAMETER_DECISION`** — the first predicted
DESIGN date, **since DISCHARGED on that limb by Ruling c-15 (§8.9.1)** · **`C_GENERATION_CALIBRATION_SPLIT_IS_A_SECOND_UNREGISTERED_GENERATOR_PARAMETER_WITH_A_KNOWABLE_ANTI_CONSERVATIVE_LIMB`**
— a second `MINIMUM_RESEARCH_GATE_BLOCKER` on the same footing, and **still live**.
§8.9.1 enumerates three further unvalued generator inputs and records
`C_MAP_INPUT_FREEZE_COLLIDES_WITH_THE_FEATURE_LIST_FIXED_AT_A_LATER_AUDIT_AND_SCOPE_CANNOT_RESOLVE_IT`.

**Its direction is knowable, and both limbs point the same way.** An **earlier** first
predicted date means (i) fewer structurally unpredicted dates, so fewer common zeros,
which §8.7.2 measured as *lowering* `c`; and (ii) shorter early training windows, so
noisier per-pair models, more pair-idiosyncratic noise, which c-11 records as *diluting*
`|r|`. **Both lower `c`, lower `rho_x` and raise `N_eff`** — so an earlier start is the
**anti-conservative** arm on both limbs, and by §8.4.11's A-ω-5 standard a pre-data
freeze alone does not protect it. It is therefore a **`MINIMUM_RESEARCH_GATE_BLOCKER`**,
stated as exactly one narrow question and not dissolved:
**`EARLIER_FIRST_PREDICTED_DATE_IS_THE_ANTI_CONSERVATIVE_ARM_ON_BOTH_LIMBS`.**

*No value is invented here.* §9 forbids adding exact values that are not committed, and
no committed source supplies this one; the stage-22 quintile split is fenced lineage and
`train_months = 6` is a CLI default in an unrelated module. **What is available is the
direction**, which is what a human + ChatGPT ruling needs in order to choose without
choosing on an outcome.

#### 8.8.3 Ruling c-14 — the freeze rule is not a whitelist, and fold-locality is scoped

**`ENUMERATION_DOES_NOT_LIMIT_THE_ALL_DECISION_BEARING_INPUTS_RULE`.**
`ALL_DECISION_BEARING_C_MAP_INPUTS_MUST_BE_FROZEN_BEFORE_C_MEASUREMENT` is the
authority; §8.7.3's table is **illustrative and audit-oriented**, never an exhaustive
licence. **The inclusion test governs**: an input falls under c-12 if changing it can
change the DESIGN predictions, which DESIGN events or trades exist, the daily PnL values,
the daily PnL dates, any pairwise correlation entry, or `c`. **No session may classify an
input out of scope**; an unclear case is a human + ChatGPT question defaulting to
blocker.

**And fold-locality is scoped to where leakage actually arises**, because over-applying
it would convert static metadata into machinery for nothing. Each input is classified:

| Class | Inputs | Treatment |
| --- | --- | --- |
| **Fitted on data that includes the observation, and reaching that observation's own label, eligibility or prediction** | `W̄`/`L̄` (magnitudes of realised barrier outcomes) · the **cost table**, because prereg §6 makes `TP_dist`, `SL_dist` and the eligibility hurdle functions of `cost`, so a span-wide table builds observation *i*'s own label out of data that includes *i* · the calibration · any target-conditioned transform | **Fold-local** for `c` generation: fitted on the fold's training portion only. The frozen whole-DESIGN values continue to govern **validation and holdout** unchanged |
| **Exogenous / static** | per-pair pip-size authority · the session partition · the M15 aggregation identity (`n_source_bars == 15`, UTC bucketing, per-side OHLC, missing-minute policy) · feature **definitions** | **Not** fold-local. Frozen under c-12 like any other input, but they carry no target information and making them fold-local would be machinery for nothing |
| **Frozen by independent authority** | model family and hyperparameters · class weighting · pair universe · horizon · DESIGN span · day attribution · idle rule · date index · the coefficient and its weighting | Unchanged; already frozen elsewhere |

**⚠ The test is *not* "is it target-derived", and an earlier drafting of this ruling
said it was.** The cost table is **not** target-derived — prereg §5 fits it on **quoted
spreads**, `cost(pair, session) = median_spread + pad_exec + cell_slippage`, with no
target anywhere — so the earlier token
`FOLD_LOCALITY_IS_REQUIRED_FOR_TARGET_DERIVED_INPUTS_ONLY` licensed the frozen
whole-DESIGN table for `c` generation, **which is exactly what c-11 forbids by name**.
The table cell's own stated reason was right and the header and token were not.
**Withdrawn and replaced.**

**`FOLD_LOCALITY_IS_REQUIRED_WHERE_A_FITTED_STATISTIC_REACHES_AN_OBSERVATION_IT_WAS_FITTED_ON`.**
A statistic fitted on spreads, or on any other non-target quantity, is **fold-local
whenever it enters that observation's label geometry, its eligibility, or its
prediction** — the cost table on **that** ground, not on a target-derivation ground. A
transform fitted on features that reaches only the feature matrix, and neither the label
nor eligibility, is span-derived and is **not** fold-local. *A feature whose **values**
derive from a fold-local statistic follows that statistic's locality, even where its
**definition** is exogenous.* §4's R-2's broader list remains this packet's **proposal**,
not authority.

**T-6 and Calendar B, closed for `c` with no schedule loophole.**
`FAMILY_A_ELIGIBILITY_SEMANTICS_MAY_NOT_DELEGATE_TO_A_POST_FREEZE_ARTIFACT` (Ruling
ω-13(b)) governs here in terms: **a rule is not frozen until the content it points at is
frozen**. So where an operative research eligibility semantic depends on external
calendar content, **that content must be fixed before the `c` series is generated** — a
frozen rule text pointing at a table that arrives later does **not** satisfy c-12. And a
later Calendar B artifact **may not retroactively change the already-frozen DESIGN
`c`-generating event or PnL series**
(`POST_C_FREEZE_ELIGIBILITY_CHANGES_MUST_NOT_RETROACTIVELY_CHANGE_C_DESIGN`). The
operational and production remainder keeps T-6's schedule, and
`OMEGA_EVENT_ELIGIBILITY_RULES_MUST_BE_PRE_DATA_FROZEN` continues to bind the forward
roles independently of this `c` test.

#### 8.8.4 Ruling Q10(iii)-a — the guards run before the zero-fill

**`Q10_III_A_RULED_PRE_FILL_ACTIVE_OBSERVATION_GUARDS_PRECEDE_CALENDAR_ZERO_FILL`.**

**The committed guards, read at source and not paraphrased.** `annualised_daily_sharpe`
carries exactly **two**, and no others exist anywhere in the metric path: it returns
`0.0` when `len(values) < 2`, and `0.0` when `sd == 0 or not math.isfinite(sd)`, where
`sd` is `statistics.stdev` — **sample** standard deviation, `ddof = 1`. Its own docstring
records the intent: "*undefined Sharpe reported as 0.0, never NaN*". **Validation and
holdout share one implementation** — `body.py` calls it directly for validation and
`compute_all` for holdout — so **no role-specific guard exists**, and none is created
here. `acceptance.py` only compares the reported number against
`min_daily_portfolio_sharpe_annualised = 0.8`; the guard lives in the metric, not in the
acceptance layer.

**The ruled order, and it may not be permuted.**

> trade outcomes → **Q10(i) attribution** → **discard every trade whose attributed date
> is not a member of the complete registered UTC calendar-date index of the role's
> declared span**, at **both** edges
> (`SHARPE_SERIES_MEMBERSHIP_IS_DECIDED_BY_THE_ATTRIBUTED_DATE_AND_THE_INDEX_IS_NEVER_EXTENDED`,
> §8.7.4) → **active-date** aggregated PnL **over the surviving trades only** → **the two
> committed guards, evaluated on that in-index active-date observation set** → if and
> only if both pass: reindex onto the complete registered index → fill idle dates with
> **zero** → daily mean and sample stdev on the complete series → annualise by **`√365`**.

**`MEMBERSHIP_FILTERING_PRECEDES_THE_GUARDS_AND_THE_GUARDS_PRECEDE_THE_FILL`.** *An
earlier drafting of this block omitted the membership step, and the omission reproduced
the exact number the ruling claims to close*: with one in-index active date and one trade
attributed outside the span, the guards would have run on a two-element set and passed,
the reindex would then have dropped the out-of-index date, and the reported figure would
be the **+2.45** single-active-date case. A guard evaluated on a set larger than the
statistic's own index is not a guard.

**And "active" is defined here, because two readings diverge exactly at the gate.**
**Active** means, per §8.7.4's limb 2, a date to which **at least one in-index trade is
attributed**, irrespective of whether its aggregated PnL is zero. A date whose trades net
to exactly `0.0` is **active**: it counts toward `len` and it enters `stdev`.
**`ACTIVE_MEANS_AT_LEAST_ONE_ATTRIBUTED_TRADE_NOT_NON_ZERO_PNL`.**

**Why the order carries the whole weight.** §12.15 recorded that a complete index
**disables both guards**: `len < 2` can essentially never fire on a role span, and
`sd == 0` fires only when no trade exists at all — so a single active date yields exactly
`sign(x)·√(365/N)`, about **+2.45 at a 61-date span**, against a frozen floor of `0.8`,
where the committed code returns `0.0`. Evaluating the guards **on the pre-fill active
set** restores both exactly: one active date still fails `len < 2`, and two active dates
carrying identical values still fail `sd == 0` rather than having variance manufactured
for them by the calendar. **`COMPLETE_INDEX_DISABLES_THE_DEGENERATE_SHARPE_GUARDS` is
closed by this ordering** — the named object, the guards' disablement, is undone and
parity with the committed metric restored.

**It does not follow that validation is contained, and this ruling does not claim it.**
The two guards are **definedness** guards, not sparsity guards: they block `m = 1` and
the all-equal cases and nothing else. The supremum of the filled Sharpe at `m` in-index
active dates on an `N`-date span is `√(365·m(N−1)/(N(N−m)))` — **3.49 at `m = 2` and
4.31 at `m = 3` on a 61-date span**, against a frozen floor of `0.8` — and a `1e-7`
perturbation of two identical values moves the reported figure from `0.0` to `3.49`.
**Holdout is contained** by the conjunctive `≥ 1,000` trade, `≤ 40`/day and `≥ 0.60`
coverage rows; **validation is not**.
**`SPARSE_CANDIDATE_CAN_CLEAR_THE_SHARPE_FLOOR_AT_VALIDATION_UNDER_ANY_INDEX_READING`** —
a property of the committed metric, neither created nor removed by this ruling ·
**`NON_NORMATIVE_DIAGNOSTIC_ONLY`**.

**No new threshold is invented.** No minimum active-day count is created — not ten, not
twenty, not any number. The guards used are **exactly** the two committed ones, applied
to the observation set they were written for. **`NO_NEW_SHARPE_OBSERVATION_THRESHOLD_IS_CREATED`.**

**What is unchanged by this limb.** The index, the idle-zero rule, Q10(i) attribution and
`√365` all stand as ruled at §8.7.4. **Coverage is untouched** — `daily_coverage`
computes from the **trade list** and `holdout_trading_days`, shares no object with the
Sharpe series, and neither its frozen `≥ 0.60` threshold nor Ruling Q10(ii)'s denominator
moves. **Max drawdown is untouched, and provably so**: `max_equity_drawdown` is a running
peak-to-trough over the cumulative daily sum, so an inserted zero repeats the previous
equity level and leaves every partial sum, the running peak and the maximum gap
identical — re-verified against the implementation and on all-negative, leading-idle,
trailing-idle, interior-gap and single-date series. **Q10(iii) is not a max-drawdown
rewrite**, and the frozen `≤ 0.15` row does not move.
**`MAXDD_IS_INVARIANT_TO_IDLE_DATE_ZERO_FILL`.**

**And the clock reaches validation selection, so it is frozen before validation.**
`select_threshold` takes the **argmax** of the validation daily Sharpe with no
trade-count floor, so the index, the guards and the factor together can change **which
operating point reaches the holdout**.
**`VALIDATION_SHARPE_CLOCK_AND_GUARD_SEMANTICS_MUST_BE_PRE_VALIDATION_FROZEN`** ·
**`SHARPE_SEMANTICS_MAY_NOT_DIFFER_BETWEEN_VALIDATION_AND_HOLDOUT`** — the index, the
idle rule, the guard order and the annualisation factor are identical at both roles and
may not be changed between them to improve a result. **And
`Q10_III_MUST_NOT_BE_RESELECTED_AFTER_OBSERVING_ANY_METRIC_IT_MOVES` (§8.7.4) binds this
sub-limb by name**: the guard order may not be selected or permuted after observing any
Sharpe on **any** span, a DESIGN-span diagnostic included. A pre-validation freeze *date*
is necessary and not sufficient — the prohibition is on the **observation**, not the
calendar, which is the same correction §8.8.0 makes to the closure rule.

**⚠ And a fired guard is not an exclusion — this ruling creates a route it does not
close.** A guard that fires returns exactly `0.0` into `select_threshold`'s **argmax**,
and `0.0` beats every genuine **negative** Sharpe. So a candidate whose Sharpe is
*undefined* can outscore candidates whose Sharpe is defined and bad, and an
all-degenerate sweep ties at `0.0` and resolves silently to
`PRODUCTION_DEFAULT_THRESHOLD`. Against the incumbent §8.7.4 state this **changes which
operating point reaches the holdout**, in the direction of selecting the candidate about
which **least is known**. Whether a fired guard should instead make a candidate
**ineligible** for selection is a human + ChatGPT question **this ruling does not
answer** — answering it here would either invent the observation threshold
`NO_NEW_SHARPE_OBSERVATION_THRESHOLD_IS_CREATED` forbids, or risk emptying the candidate
set. **`GUARD_SENTINEL_ZERO_IS_SELECTABLE_AT_VALIDATION_ARGMAX`** — carried as a live
**`MINIMUM_RESEARCH_GATE_BLOCKER`**.

#### 8.8.5 The turnover ruling, re-verified

**`TURNOVER_CEILING_COUNTS_TRADES_BY_ENTRY_UTC_DATE`** stands. Re-read at source and no
committed contradiction found: prereg §9's row is "turnover upper bound | **≤ 40
trades/day portfolio-wide**" and names no day; Ruling Q10(ii) expressly leaves the
ceiling's day unruled.

**The exact formula, so nothing is silently altered.** `turnover(n_trades,
n_trading_days)` returns `n_trades / n_trading_days`; it is called as
`turnover(len(trades), n_days)` with `n_days = len({t.day for t in trades})`. So the
committed quantity is **total trades divided by the number of distinct active dates** —
a portfolio **mean over active dates**, which is what its docstring says. It is **not** a
maximum per-day count.

**This ruling closes the definition of "day" and nothing else.** Each registered trade is
counted **exactly once**, against the UTC date containing its **decision-bar** entry
marker (`TradeSignal.entry = i`, not prereg §6's next-bar fill), so
`turnover_count[date]` is the number of trade entries whose decision timestamp falls on
that date. Under the committed mean the numerator carries no date, so what this fixes is
the **day set the mean divides by**. **Whether the ceiling is that mean or a per-day cap
remains unregistered**, as does the active-versus-calendar denominator axis — both stay
open, both are **locked pre-observation**, and both have their permissive arms named
(`max ≥ mean`, so the mean is permissive **and** incumbent; a larger denominator lowers
measured turnover). **Nothing else in the formula is altered.**

#### 8.8.6 Status — and the closure decision is deferred to after the review

**Recorded now:** c-13, c-14 and Q10(iii)-a are ruled; the turnover ruling is
re-verified; the over-broad closure rule of §8.7.6 is **withdrawn** and replaced by
`CLOSURE_CLAIM_REQUIRES_COMPLETED_REVIEW_AND_NO_UNRESOLVED_MATERIAL_BLOCKER`.

**Not recorded now, and deliberately:** whether
`NO_NR_L_MINIMUM_RESEARCH_CONTRACT_BLOCKER_REMAINS`. **This subsection is written before
this round's review roles have returned**, and under the corrected rule the claim
requires a completed review whose material findings are resolved. §8.8.7 records the
decision **after** they return, and it is the only place in this document where that
decision is taken. *Nothing here may be read as anticipating it.*

**What is known to remain open before the review runs**, so the decision has a baseline:
**`C_DESIGN_GENERATOR_PENDING_ONE_EXACT_PARAMETER_DECISION`** — the first predicted
DESIGN date — is a live `MINIMUM_RESEARCH_GATE_BLOCKER` with a knowable anti-conservative
arm. *(Historical record of the §8.8 round, retained unrewritten: that limb was
subsequently discharged by Ruling c-15 at §8.9.1, which also found that the token's
"one exact parameter" premise was wrong by more than one.)* **On the record as it stands, closure is not available**, and the review's task was to
find whether anything *else* is live as well. **It was: §8.8.7 records the decision —
closure is NOT taken**, on two live blockers and partial review coverage.

**Unchanged by this round.** `EXACT_WINDOW_NOT_READY_FOR_DECLARATION_FORWARD_EPOCH_DOES_NOT_EXIST`;
§8.6.2's boundary arithmetic, purge, warm-up and second-granularity interval convention;
Q1 (`REQUIRED_NOW`, default (b)), Q3, Q8, Q9; `FR_19_SEPARATE_TEST_SAFETY_WORK_PR_OPEN`;
`MINIMUM_CALENDAR_IDENTITY_RECORD_REQUIRED_BEFORE_DATA_EXECUTION`;
`SAMPLE_FLOOR_REACHABILITY_NOT_DETERMINABLE_WITHOUT_MEASURED_INPUTS`. **Real-data read
remains unauthorised.** **`PRODUCTION_READINESS_NOT_CLAIMED`** ·
**`NO_EXECUTION_PERFORMED`**.

#### 8.8.7 The closure decision — taken after the review, and it is NOT closure

**`NR_L_MINIMUM_RESEARCH_CONTRACT_RULED_PENDING_IMPLEMENTATION_AND_DESIGN_MEASUREMENT`** ·
**`CLOSURE_NOT_AVAILABLE_TWO_LIVE_BLOCKERS_AND_PARTIAL_REVIEW_COVERAGE`**

**`NO_NR_L_MINIMUM_RESEARCH_CONTRACT_BLOCKER_REMAINS` is NOT claimed.** Under
`CLOSURE_CLAIM_REQUIRES_COMPLETED_REVIEW_AND_NO_UNRESOLVED_MATERIAL_BLOCKER` (§8.8.0),
**three of its five conditions fail**, and each is stated rather than argued around.

**Condition 2 fails — the review did not complete.** Three doc-only roles were
dispatched; **one returned**. The **DESIGN generator / target-leakage** role and the
**adversarial remaining-freedom** role both terminated on an account-level weekly API
limit, having produced nothing beyond an opening line.
**`ROUND_16_REVIEW_COVERAGE_PARTIAL_ONE_OF_THREE_ROLES_RETURNED`** — recorded on the same
footing as `ROUND_11_REVIEW_COVERAGE_PARTIAL_TWO_OF_THREE_ROLES_TERMINATED`, which this
document has never relabelled and does not relabel now. **The two perspectives that did
not run are precisely the two that would have attacked Rulings c-13 and c-14** — the
generator and the freeze — so the coverage gap sits directly over this round's largest
new surface, and it is **not** cured by the lead's own verification.

**Condition 4 fails — material blockers are live**, two of them, and the second was
created by this round's own ruling:

1. **`C_DESIGN_GENERATOR_PENDING_ONE_EXACT_PARAMETER_DECISION`** — the first predicted
   DESIGN date. No committed source supplies it, §9's rule forbids inventing one, and its
   direction is knowable and **anti-conservative on both limbs**: an earlier start means
   fewer common zeros (lowers `c`) and noisier early models (dilutes `|r|`).
   *(Historical: discharged on this limb by Ruling c-15, §8.9.1.)*
2. **`GUARD_SENTINEL_ZERO_IS_SELECTABLE_AT_VALIDATION_ARGMAX`** — a guard that fires
   returns exactly `0.0` into `select_threshold`'s argmax, where it beats every genuine
   **negative** Sharpe. **Ruling Q10(iii)-a creates this route**: relative to the
   incumbent §8.7.4 state it changes which operating point reaches the holdout, toward
   the candidate about which least is known. Whether a fired guard should make a
   candidate **ineligible** is a human + ChatGPT question §8.8.4 expressly declines,
   because answering it would either invent the observation threshold
   `NO_NEW_SHARPE_OBSERVATION_THRESHOLD_IS_CREATED` forbids or risk emptying the
   candidate set.

**Condition 3 is met, and is the only reason this round is worth recording.** Every
decisive finding the returning role reported was re-verified by the lead at source before
being applied: the membership-filter gap that reproduced the +2.45 case; the sentinel
argmax; the signed-versus-magnitude direction error; and the `m = 2` supremum of 3.49
against a 0.8 floor. Two further defects were found by the lead **before** any role
returned — c-13's unstated block width, which made its "one parameter" claim false, and
the withdrawn index refinement of the previous round.

**What this round did settle**, so the remaining work is a list and not a mood: the
generator's **shape** (c-13), the freeze rule's **scope and non-exhaustiveness** (c-14),
the Sharpe **guard order** (Q10(iii)-a), the turnover **day**, and §8.8.0's correction of
this packet's own over-broad closure rule. Those stand. What does not is the claim that
nothing is left.

**`Q10_III_RULED_FULL_UTC_DATE_INDEX_IDLE_ZERO_PRE_FILL_GUARDS_SQRT365`** is recorded for
the parts that are ruled — index, idle rule, guard order, factor — **with
`GUARD_SENTINEL_ZERO_IS_SELECTABLE_AT_VALIDATION_ARGMAX` carried against it**, and with
instantiation still pending the Q10-B declaration.

**No favourable classification is asserted here.** This round's own ruling created one of
the two live blockers; one of its direction claims was withdrawn as directionally false;
its guard-order block omitted a step that reproduced the number it claimed to close; and
its review coverage was one role in three. **The honest disposition of a round that found
this much in its own work is that it is not the round that closes the contract.**

**What closure would now require**, stated so the next round is bounded: a human +
ChatGPT decision on the **first predicted DESIGN date**; a human + ChatGPT decision on
whether a **fired guard excludes a candidate** from selection; and a review in which the
**generator and adversarial perspectives actually run**.

### 8.9 The two remaining statistical blockers — ruled

A ruling received from human + ChatGPT and recorded here as **authority**. It closes the
two blockers §8.8.7 recorded as live. The closure **decision** is taken at §8.9.6, after
the two review perspectives that failed in the round recorded at **§12.16** have
actually returned. *(That round's token reads `ROUND_16_…` while §12.16 is headed
"Seventeenth review round"; the token's numbering and the heading's ordinal differ, and
§12.16 is meant.)*

**`C_15_RULED_FIRST_PREDICTED_DESIGN_DATE_IS_THE_25_PERCENT_PREFIX_BOUNDARY`** ·
**`GUARD_FAILURE_EXCLUDES_CANDIDATE_FROM_VALIDATION_SELECTION`**

#### 8.9.1 Ruling c-15 — the first predicted DESIGN date

**The rule.** The **first `ceil(0.25 × N_design_dates)` dates** of the frozen DESIGN UTC
calendar-date index are **training-only** and receive no predictions. Every remaining
date is a **one-date prediction block** under c-13's chronological expanding-window
walk-forward, with the committed **25 M15-bar purge** immediately preceding each block
unchanged, and with every target/outcome-derived DESIGN input handled **fold-locally** at
each walk-forward state under c-14.

**`n_initial_training_dates = ceil(0.25 × N_design_dates)`**, and the first predicted
date is **mechanically recomputed from the committed DESIGN constants** — it is not a
literal in this document that could drift from them.

**Instantiated against source, re-verified for this ruling.** `no_overlap.py` carries
`DESIGN_START = 2025-04-25T00:00:00Z` and `DESIGN_END = 2026-02-28T23:59:59Z`, so the
index is **2025-04-25 … 2026-02-28 inclusive = 310 dates** — the reported span confirmed,
not assumed. Therefore:

| Quantity | Value |
| --- | --- |
| `N_design_dates` | **310** |
| `0.25 × N` | 77.5 |
| `n_initial_training_dates = ceil(77.5)` | **78** |
| Training-only block | **2025-04-25 … 2025-07-11** |
| **First predicted DESIGN date** | **2025-07-12** |
| Predicted dates | **232** (2025-07-12 … 2026-02-28), 74.84% of the index |

**And the boundary lands on a market-closed date — stated, not smoothed.** `2025-07-12`
is a **Saturday** and `2025-07-13` a **Sunday**, so the first two prediction blocks are
almost certainly empty of eligible M15 events; `2026-02-28`, the index's last date, is
a Saturday too. This is **coherent** rather than a defect: Ruling Q10(iii) indexes on
the **complete UTC calendar-date index** and c-6 carries an idle pair-date as a zero, so
an empty block contributes a zero exactly as any other idle date does, and the count of
**predicted** dates is unchanged. What it must not be read as is a claim that
`n_initial_training_dates` was chosen to land on a trading date: **it was not, and a
weekday-aware boundary is expressly not adopted** — snapping the prefix to the next
open session would make the boundary depend on the eligibility calendar, which is
`C_MAP_INPUT_FREEZE_CONFLICTS_WITH_T6_HOLIDAY_CALENDAR_SCHEDULE`'s surface and would
reintroduce the discretion c-15 removes. The arithmetic boundary is the contract.
**`THE_PREFIX_BOUNDARY_IS_ARITHMETIC_AND_IS_NOT_SNAPPED_TO_A_TRADING_DATE`.**

**This is an outcome-blind contract choice, and no optimality is claimed for it.** 25% is
not derived, is not argued to be statistically best, and is not tuned: it is a
**declared, mechanical, pre-data boundary** whose only job is to remove the researcher
discretion §8.8.2 isolated. Its arm is fixed **before** any DESIGN observation, and the
prefix may **not** be changed after seeing `c`, `rho_x`, `N_eff`, a Sharpe, a sample-floor
verdict or any other measured quantity.
**`C_TRAINING_PREFIX_IS_AN_OUTCOME_BLIND_CONTRACT_CHOICE_NOT_AN_OPTIMALITY_CLAIM`** ·
**`C_TRAINING_PREFIX_MAY_NOT_BE_CHANGED_AFTER_ANY_MEASURED_QUANTITY_IS_SEEN`.**

**And "outcome-blind" must not be read as "conservative" — 25% is not the conservative
extreme, and this ruling says so rather than letting the label imply it.** §8.8.2
established that a **larger** prefix is conservative on both limbs, so the conservative
extreme is a **larger** number, not this one. What a larger prefix costs is the other
half of the trade, and it is real: fewer live dates make `c` a **noisier estimate**, and
a higher structural-zero share makes it measure proportionately less about the strategy.
On synthetic series — two pairs, per-pair activity share 0.45, shared factor loading 1.2,
per-trade PnL `N(0.4, 2.0)`, 400 replicates, the index held at 310 dates — `E|ρ|` rises
monotonically with the prefix while its dispersion rises **faster**:

| prefix | live dates | `E\|ρ\|` | sd |
| --- | --- | --- | --- |
| 0 (0%) | 310 | 0.1188 | 0.0530 |
| **78 (25%)** | **232** | **0.1223** | **0.0597** |
| 155 (50%) | 155 | 0.1293 | 0.0688 |
| 232 (75%) | 78 | 0.1425 | 0.0924 |

**`NON_NORMATIVE_DIAGNOSTIC_ONLY`**; synthetic arithmetic, no data read, and the
generating model is stated so the figures are reproducible from the text. **So 25% sits
near the low-conservatism end of the axis**, buying estimator coverage at the cost of
conservatism in the deflator. That is a **trade the declaration makes, not a safety
property it has**, and a reader must be able to see which.
**`C_TRAINING_PREFIX_TRADES_DEFLATOR_CONSERVATISM_FOR_ESTIMATOR_COVERAGE`.**

*The freedom is removed rather than exercised well.* Declaring any value fixes the
parameter for current Family A; what makes this declaration admissible is that it is
made **before any DESIGN observation** and may never be revisited on one — not that the
value chosen is the safest available. **`DECLARING_A_VALUE_REMOVES_THE_FREEDOM_IT_DOES_NOT_MAKE_THE_VALUE_OPTIMAL`.**

**Why a ruling was the only available move, and what it costs.** §8.8.2 established that
the parameter's direction is knowable — an **earlier** first predicted date is
anti-conservative on both limbs — so leaving it open left a lever that a pre-data freeze
alone does not protect (§8.4.11's A-ω-5 standard). No committed source supplies a value,
and §9's rule forbids inventing one from the machinery: the stage-22 quintile split is
fenced lineage and `train_months = 6` is a CLI default in an unrelated module. **A human
+ ChatGPT declaration is therefore the only instrument that removes the freedom without
deriving a number that does not exist**, and that is what this is. The cost is stated:
**a quarter of the DESIGN index carries no prediction**, those dates are carried as zeros
under c-6/c-7, and §8.7.2 established the **sign** — a **common** zero prefix
*raises* `|ρ|` — on c-7's fully-specified counterexample, with **no magnitude claimed**
there and `NON_NORMATIVE_DIAGNOSTIC_ONLY`; the diagnostic table below supplies a
magnitude on a stated, reproducible model. *An earlier drafting wrote that §8.7.2
"**measured**" the effect and called it "**mildly**", reintroducing the two things
§8.7.2 expressly withdrew.* And the direction must be stated against the right
counterfactual: **both** of §8.8.2's limbs are monotone in prefix size, so **any larger
fraction is strictly more conservative than 25% and any smaller one strictly less**.
25% is conservative against a no-prefix counterfactual that c-13 already forbids, and
**anti-conservative against every larger prefix**.
**`TWENTY_FIVE_PERCENT_IS_ANTI_CONSERVATIVE_RELATIVE_TO_EVERY_LARGER_PREFIX_AND_NO_ARM_IS_CLAIMED`.**

**What c-15 does not touch.** The 25-bar purge, the one-date block width, the
one-partition-for-all-pairs-and-configs rule, and c-14's fold-local treatment are
unchanged; `C_GENERATION_METHOD_MUST_NOT_BE_SELECTED_FOR_THE_SPAN_OR_SPARSITY_IT_PRODUCES`
continues to bind, and with the prefix now fixed there is nothing left for it to bind
**on the partition** — it survives for any future method question.
**`C_DESIGN_GENERATOR_PENDING_ONE_EXACT_PARAMETER_DECISION` is DISCHARGED — as to the
first predicted DESIGN date, and as to nothing else.** The token's name says "one exact
parameter" because that is what §8.8.2 believed when it minted it; §8.8.2 is corrected
above, and
**`C_GENERATION_CALIBRATION_SPLIT_IS_A_SECOND_UNREGISTERED_GENERATOR_PARAMETER_WITH_A_KNOWABLE_ANTI_CONSERVATIVE_LIMB`**
is **live**. Wherever the older token still appears asserted in a status list written
before this round — §8.8.2, §8.8.6 and §8.8.7 — it is discharged **on this limb only**,
and those sections are historical records that are **not** rewritten.

**And the generator's unvalued inputs are enumerated, because "one parameter" was
wrong by more than one.** Re-read at source for this round, the following DESIGN-`c`
generator inputs carry **no committed value today** and each can move the trade set,
hence the per-pair daily PnL series, hence `c`:

| Unvalued generator input | Committed authority, and what it leaves open | Direction |
| --- | --- | --- |
| **First predicted DESIGN date** | none — §9 forbids inventing one | **RULED by c-15** |
| **Isotonic calibration inner split** — fraction, chronological or random placement, whether its own boundary purges | prereg §8: "a split **carved from the training span only**"; `contract.py` carries `CALIBRATION = "none_raw_predict_proba"`, so no committed split exists | anti-conservative limb **knowable** (a larger carve → noisier fits → more idiosyncratic PnL → lower `\|r\|` → higher `N_eff`) |
| **The final feature list** | prereg §7: "the final feature list is frozen **at the design audit**"; the native-M15 base, H1/H4 context and realised-vol groups are each "**allowed only after audit**", and §11 schedules "Native-M15 feature-builder review (§7) **[FIXED-AT implementation audit]**" | anti-conservative limb **knowable**, same mechanism |
| **The `W̄` / `L̄` estimator** | prereg §8 fixes only that they are "estimated on design data and frozen" — not the estimator, its cell aggregation, or its outlier handling | moves `EV_d`, hence eligibility and sparsity, hence `c` |
| **The `ATR14_M15` warm-up / `min_periods` convention at a block boundary** | prereg §7 defers it — "warmups/windows revalidated" at the native-M15 review | moves eligibility at every block edge |

**Two things follow, and the second is a blocker this round did not previously carry.**
*First*, `ALL_DECISION_BEARING_C_MAP_INPUTS_MUST_BE_FROZEN_BEFORE_C_MEASUREMENT` (c-12)
is maintained at **full strength and expressly non-exhaustive**: every row above is a
decision-bearing input and must be frozen before `c` is measured, whether or not c-12's
enumeration names it. *Second*, **the feature list's own schedule collides with that
requirement in exactly the shape c-12 resolved for Calendar B — and it cannot be
resolved the same way.** The Calendar B collision was closable by **scope**, because
only the eligibility subset reaching current Family A had to be pre-`c` frozen. The
feature list has no such subset: it determines `p̂` for every bar, so **all** of it
reaches `c`. Yet prereg fixes it at the **design audit / implementation audit**, which
is a **later** gate than the one at which `c` is generated.
**`C_MAP_INPUT_FREEZE_COLLIDES_WITH_THE_FEATURE_LIST_FIXED_AT_A_LATER_AUDIT_AND_SCOPE_CANNOT_RESOLVE_IT`**
— a `MINIMUM_RESEARCH_GATE_BLOCKER`, recorded here and **not** ruled: the available
arms are to bring the feature freeze forward to before `c` generation, or to sequence
`c` generation after the design/implementation audit, and choosing between them is a
human + ChatGPT scheduling decision this session may not take.

*The enumeration is the lead's own, verified at source, and is **not** claimed
exhaustive* — `C_INPUT_FREEZE_CHECKABILITY_IMPLEMENTATION_PENDING` means nothing checks
it, and the RNG seed is carried separately under §8.9.4's
`AN_IDENTICAL_INPUT_REBUILD_IS_A_RESELECTION_AND_THE_FIRST_BUILD_GOVERNS`.

#### 8.9.2 Ruling Q10(iii)-b — a fired guard excludes the candidate

**`GUARD_FAILURE_EXCLUDES_CANDIDATE_FROM_VALIDATION_SELECTION`.**

**A guard failure is not a Sharpe of zero.** Where either committed guard fires, the
candidate's Sharpe is **undefined**, the candidate is **ineligible for validation
selection**, and it is **removed from the argmax domain** rather than entered into it
with a number. A candidate with a **valid negative** Sharpe remains **eligible** — being
bad is not being undefined. **No selectable numeric sentinel is permitted**: `0.0`, and
any other stand-in value, may not be placed into the selector.
**`A_FIRED_GUARD_YIELDS_NO_SELECTABLE_VALUE`.**

**⚠ Two things this ruling does not decide, and neither is implementation detail.**
*First, the committed selector refuses an incomplete domain.* `select_threshold` raises
`ThresholdSelectionError` unless the sweep covers the registered candidate set
**exactly**, calling an incomplete sweep "a multiplicity-control violation" (PR #411's
B-2 fix). So "removed from the argmax domain" is reachable only by **failing the family
closed on any single guard failure**, or by **relaxing that committed control** so an
ineligible candidate can be carried without a value — different outcomes, a halt versus
a different operating point reaching the holdout, and **neither is registered**. Under
CLAUDE.md's stricter-reading rule the **fail-the-family** arm is the governing default
until ruled.
**`EXCLUSION_VERSUS_THE_COMMITTED_SWEEP_COMPLETENESS_CHECK_NOT_REGISTERED`** — a
`MINIMUM_RESEARCH_GATE_BLOCKER`.

*Second, which selector this reaches at all is unregistered.* The registered candidate
set is three **`ev_min`** points (§8.5.0), while `select_threshold` sweeps three
**probability thresholds** — a decision rule prereg Ruling 9 forbids twice — and **no
`ev_min` selector exists in committed source**. If the implementing PR builds prereg §8's
**FROZEN** expectancy selector instead, this ruling binds nothing and
`GUARD_SENTINEL_ZERO_IS_SELECTABLE_AT_VALIDATION_ARGMAX` is discharged **vacuously
rather than on its merits** — and `expectancy()` carries no trade-count floor either.
**`WHICH_VALIDATION_SELECTOR_GOVERNS_IS_UNREGISTERED_AND_DECIDES_WHETHER_Q10_III_B_BINDS`**
— a `MINIMUM_RESEARCH_GATE_BLOCKER`, and the single item most likely to make a ruling
that reads decisive constrain nothing.

**If every registered candidate is guard-failed, there is no selection.** The family does
**not** proceed to the holdout: the outcome is **fail-closed**, routed into the committed
`failure_handling` — family A closes or adoption waits — exactly as an uncertifiable `c`
is at c-8. No candidate is promoted by default, and
`PRODUCTION_DEFAULT_THRESHOLD` may **not** be reached through an all-degenerate tie.
**`ALL_CANDIDATES_GUARD_FAILED_IS_FAIL_CLOSED_NOT_A_DEFAULT_SELECTION`.**

**And the destination is itself an unselected fork, recorded rather than smoothed.**
"Family A closes **or** adoption waits" is
`VALIDATION_BRANCH_DISJUNCTION_HAS_NO_SELECTOR_RESIDUAL_AFTER_Q11_SECTION0_RULING`, still
open, and §8.5.0 records the same absence for a c-8 halt. The branches are **not**
equivalent — one ends the family, the other preserves a later attempt on more accrued
forward data — and **this ruling does not select between them**. What it fixes is that
**no candidate is promoted**; where the halt lands is unruled.

**The processing order, restated end to end and not permutable.**

> **1.** filter to the registered evaluation span — discard every trade whose Q10(i)
> attributed date is not a member of the complete registered UTC calendar-date index, at
> **both** edges → **2.** aggregate **active-date** daily PnL over the surviving trades
> → **3.** apply the **existing committed** insufficient-observation and variance guards
> to that in-index active-date set → **4.** if either fires, the candidate is
> **ineligible** and no value is produced → **5.** otherwise reindex onto the complete
> UTC calendar-date index → **6.** fill idle dates with **zero** → **7.** compute the
> Sharpe on the complete series → **8.** annualise by **`√365`**.

**No new threshold is created.** The guards are the two committed ones —
`len(values) < 2` and `sd == 0 or not finite`, sample stdev — applied to the observation
set they were written for. **No minimum active-day count is invented**, and
`NO_NEW_SHARPE_OBSERVATION_THRESHOLD_IS_CREATED` stands: this ruling changes what a
**fired** guard *does*, never when it fires.

**What this closes, and one thing it settles as a by-product.**
`GUARD_SENTINEL_ZERO_IS_SELECTABLE_AT_VALIDATION_ARGMAX` is **DISCHARGED** — the route
by which an undefined candidate outscored a defined-but-negative one is removed at its
source, because there is no longer a value to outscore with. And
`KILL_GATE_READS_THE_REGISTERED_SET_NOT_THE_ELIGIBLE_SUBSET`, which recorded a state with
**no committed disposition** — a family passing prereg §9.V while no configuration is
selectable — now has one **on its guard-failure limb only**: fail-closed, no holdout,
subject to the unselected fork above. *The token was minted at §8.5.0 about
**`c`-uncertifiability**, not guard failure, and §8.7.6 still lists it among the
unregistered questions; that limb is **not** discharged here, and the two sections must
not be read as asserting opposite states of one token.* The two objects stay distinct and
are not merged: §9.V is an **expectancy-and-turnover** kill gate on the registered set,
and the Sharpe guard governs **selection eligibility**; a family may satisfy the first
and still have no selectable candidate, and that is the case just disposed of.
**`KILL_GATE_AND_SELECTION_ELIGIBILITY_ARE_DIFFERENT_OBJECTS_BOTH_NOW_DISPOSED`.**

**Scope, stated because two selectors exist in the record.** Prereg §8's **committed**
selection metric is validation net **expectancy** subject to the turnover budget, which
is per-trade and annualisation-free — the Sharpe guard does not reach it. The committed
**implementation** selects on the validation daily Sharpe argmax, and it is that selector
this ruling binds. Where they diverge,
`Q10_III_REACHES_THE_OPERATING_POINT_ONLY_VIA_AN_IMPLEMENTATION_THAT_DIVERGES_FROM_THE_COMMITTED_SELECTION_METRIC`
continues to record the divergence; this ruling does not resolve it and does not need to.

**And it is locked pre-observation**, on the same footing as the clock itself:
`Q10_III_MUST_NOT_BE_RESELECTED_AFTER_OBSERVING_ANY_METRIC_IT_MOVES` binds the exclusion
rule as it binds the guard order — neither may be selected or permuted after observing a
Sharpe on any span, a DESIGN-span diagnostic included.

#### 8.9.3 The mandatory Sharpe standard error — disposition

**It is mandatory to report and it enters no threshold comparison.** §10 requires every
headline estimate to carry a standard error and states that "**a Sharpe reported without
that number is not a result**". Re-read at source, **no acceptance criterion consumes
it**: `acceptance.py` compares the Sharpe against
`min_daily_portfolio_sharpe_annualised = 0.8` and reads no standard error, and no SE
appears in `contract.py`'s criteria. So the SE **cannot move a verdict** — but its
**absence invalidates the report**, which is why it is not merely diagnostic either.
**`SHARPE_SE_IS_MANDATORY_TO_REPORT_AND_ENTERS_NO_THRESHOLD_COMPARISON`.**

**It is aligned to the ruled clock, and that alignment is the point.** Because the ruled
statistic is annualised by `√365` over the **complete registered UTC calendar-date
index**, the SE must be `≈ sqrt(365 / N)` on that same index — **≈ 2.45 on a 61-date
span** — and the earlier `sqrt(252/N)` ≈ 1.07 / 1.38 figures are **superseded** as the
reporting requirement (§10, corrected in the round recorded at §12.16). A reporting convention on a different
clock from the statistic it reports is the same incoherence Q10(iii) ruled out of the
statistic itself.

**Where `√252` survives in this document it is historical or diagnostic, and is marked.**
It appears in §8.6.1's reading table as the **refused** cell (C), in §8.6.1's ratio
arithmetic, and in §8's earlier statements of the then-open question. **None of those is
a live convention.** `TRADING_DAYS_PER_YEAR = 252` remains in committed **source**, which
**this PR does not change**: the divergence between the ruled contract and the M1-lineage
default is `SHARPE_INDEX_AND_FACTOR_MAY_NOT_BE_ADOPTED_SEPARATELY`'s reading (E), and it
is an **implementation** obligation on the executing PR, not a contract question.
**`SOURCE_STILL_DEFAULTS_TO_252_AND_THE_IMPLEMENTING_PR_MUST_CHANGE_IT_TOGETHER_WITH_THE_INDEX`**
— and the implementing PR must change the factor **and the manifest field it is recorded
in**, and must leave no M1-lineage default reachable by omission at any M15 call site.

**The `2.45`, `1.07` and `1.38` figures and the 61-date span above are
`NON_NORMATIVE_DIAGNOSTIC_ONLY`**: no span is declared, none may be cited as a required
duration or used to size `D`, and `EXACT_WINDOW_NOT_READY_FOR_DECLARATION_FORWARD_EPOCH_DOES_NOT_EXIST`
is unaffected. **And the in-index active-date count `m` is reported beside every Sharpe**,
not only where a guard fires: the complete-index `N` is invariant to sparsity, so the SE
alone cannot disclose it. **`ACTIVE_DATE_COUNT_IS_REPORTED_BESIDE_EVERY_SHARPE`.**

#### 8.9.4 What this round maintains without reopening

**`ALL_DECISION_BEARING_C_MAP_INPUTS_MUST_BE_FROZEN_BEFORE_C_MEASUREMENT`** stands, with
its enumeration **explicitly non-exhaustive** and the inclusion test governing; no
session may classify an input out of scope. **Upstream semantics may not be changed after
`c` is measured** — `C_OBSERVATION_MUST_NOT_TRIGGER_UPSTREAM_RECONFIGURATION` and
`THE_MAP_IS_BUILT_ONCE_AND_A_CHANGED_INPUT_IS_NOT_A_NEW_MEASUREMENT_IT_IS_A_RESELECTION`
are unchanged — and read at **full strength: the map is built once, and a rebuild is not
a new measurement whether or not an input moved.** Because prereg §8's seed policy is
`bounded_not_bitwise_guaranteed` and `NO_LOCUS_RECORDS_THE_FROZEN_C_MAP_INPUT_SET`, an
**identical-input rebuild** is both possible and undetectable, and c-15's one-date block
multiplies the number of unseeded fits standing behind a single `c`.
**`AN_IDENTICAL_INPUT_REBUILD_IS_A_RESELECTION_AND_THE_FIRST_BUILD_GOVERNS`** — carried
with `C_INPUT_FREEZE_CHECKABILITY_IMPLEMENTATION_PENDING`, whose deferral lapses where
the execution path cannot record which build produced the map.

**And one admitted hole in that pair is carried, not repaired.**
`PREREG_SECTION_6_BARRIER_RATIO_RECONSIDERATION_IS_AN_UNCLOSED_UPSTREAM_ROUTE` (§8.7.3):
prereg §6's "median eligible ratio < 3.0 triggers design-audit reconsideration" is a
**design-data observation** that reconfigures c-12 inputs, and
`C_OBSERVATION_MUST_NOT_TRIGGER_UPSTREAM_RECONFIGURATION` is scoped to observing **`c`**
and does not reach it. **Not discharged by this round.**

**`TURNOVER_CEILING_COUNTS_TRADES_BY_ENTRY_UTC_DATE`** stands, and remains deliberately
**distinct** from Q10(i)'s exit-date PnL attribution: the ceiling constrains initiation
frequency, Q10(i) fixes when an outcome is realised.
`TURNOVER_DAY_MUST_NOT_BE_BOUND_TO_THE_PNL_ATTRIBUTION_DAY_BY_INHERITANCE` is unchanged,
as are the two unregistered turnover axes and their pre-observation locks.

**Untouched by this round**: NR-K · `ω` and its clock and calendar semantics · Q10(i) ·
the exact `T_v`/`T_h`/`D` · Q1, Q3, Q8, Q9 · FR-19 · the minimum calendar identity
prerequisite · the Zero-Data verdict.
**`EXACT_WINDOW_NOT_READY_FOR_DECLARATION_FORWARD_EPOCH_DOES_NOT_EXIST`** ·
**`SAMPLE_FLOOR_REACHABILITY_NOT_DETERMINABLE_WITHOUT_MEASURED_INPUTS`** ·
**`PRODUCTION_READINESS_NOT_CLAIMED`** · **`NO_EXECUTION_PERFORMED`**.

**And one token this round deliberately does not reach.**
**`SPARSE_CANDIDATE_CAN_CLEAR_THE_SHARPE_FLOOR_AT_VALIDATION_UNDER_ANY_INDEX_READING`** —
Q10(iii)-b removes the **sentinel** route, which fires only at `m < 2` or all-equal. The
guards remain **definedness** guards, so a candidate with `m = 2` in-index active dates
still reports up to **3.49** against a `0.8` floor, with no trade-count floor anywhere in
the selector. **The reachable route is untouched by this ruling**, and it is the
narrower, rarer route that was closed.

#### 8.9.5 Status before the review

Both blockers §8.8.7 recorded are **discharged on their merits**: c-15 fixes the
generator's last parameter, and Q10(iii)-b removes the sentinel route. **No closure is
claimed here.** Under `CLOSURE_CLAIM_REQUIRES_COMPLETED_REVIEW_AND_NO_UNRESOLVED_MATERIAL_BLOCKER`
the decision requires the two perspectives that failed in the round recorded at §12.16 — the **DESIGN
generator / leakage** role and the **adversarial researcher-freedom** role — to actually
return. §8.9.6 **records** the decision — **both roles returned, and closure is NOT taken**. It
is the only place in this document where that decision is taken. *Nothing above may be
read as anticipating it; while it was pending this reference was written in the future
tense rather than the past, which is the defect §12.15 records.*

**No favourable classification is asserted for the arms chosen, and where a direction is
labelled the counterfactual it is measured against is named.** c-15 declares a boundary
it does not derive and says so; its 25% is not claimed optimal and is **anti-conservative
relative to every larger prefix**; a quarter of the DESIGN index is knowingly given up;
and Q10(iii)-b's exclusion rule creates a fail-closed state that can halt a family which
would otherwise have selected a candidate. *An earlier drafting of this sentence read
"No favourable classification is asserted in this ruling", which §8.9.1's unqualified
"the prefix's own effect on `c` is conservative" made false.*

#### 8.9.6 The closure decision — taken after both roles returned, and it is NOT closure

**`M15_MINIMUM_RESEARCH_STATISTICAL_CONTRACT_NOT_CLOSED_MATERIAL_BLOCKERS_LIVE`.**

**The review completed.** Both assigned perspectives — the **DESIGN generator / leakage**
role and the **adversarial researcher-freedom** role, the two that failed to return in
the round recorded at §12.16 — ran to completion and returned findings this round
(§12.17). Every decisive claim was **re-read at source by the lead** before being
applied, and three role claims were corrected or declined on the evidence rather than
adopted. **Condition 1 of `CLOSURE_CLAIM_REQUIRES_COMPLETED_REVIEW_AND_NO_UNRESOLVED_MATERIAL_BLOCKER`
is met** — and it is the first round in this packet's history at which it is met on the
assigned scope with no terminated role.

**Condition 4 fails.** Material blockers are live, and both roles said independently
that closure is not available. The lead agrees, having verified each at source:

1. **`C_GENERATION_CALIBRATION_SPLIT_IS_A_SECOND_UNREGISTERED_GENERATOR_PARAMETER_WITH_A_KNOWABLE_ANTI_CONSERVATIVE_LIMB`**
   — prereg §8 fixes isotonic calibration on "a split **carved from the training span
   only**" and supplies no fraction, no placement and no purge rule;
   `scripts/ml_step4/contract.py` carries `CALIBRATION = "none_raw_predict_proba"`, so no
   committed split exists anywhere. It reaches `c` through `p̂` → `EV_d ≥ ev_min` → the
   DESIGN trade set, and its fit-quality limb is anti-conservative in the knowable
   direction. **This is the identical shape c-15 was raised to a blocker for**, and this
   round created it by discovering it, not by ruling.
2. **`C_MAP_INPUT_FREEZE_COLLIDES_WITH_THE_FEATURE_LIST_FIXED_AT_A_LATER_AUDIT_AND_SCOPE_CANNOT_RESOLVE_IT`**
   — prereg §7 freezes the final feature list "**at the design audit**" and §11 schedules
   "Native-M15 feature-builder review (§7) **[FIXED-AT implementation audit]**", both
   **later** than the point at which c-12 requires every decision-bearing `c`-map input
   frozen. c-12 resolved the Calendar B version of this collision by **scope**; the
   feature list admits no scope narrowing, because it determines `p̂` for every bar.
3. **`EXCLUSION_VERSUS_THE_COMMITTED_SWEEP_COMPLETENESS_CHECK_NOT_REGISTERED`** —
   `select_threshold` raises `ThresholdSelectionError` unless the sweep covers the
   registered candidate set exactly, so Q10(iii)-b's "removed from the argmax domain"
   is reachable only by failing the family closed or by relaxing a committed
   multiplicity control, and neither arm is registered.
4. **`WHICH_VALIDATION_SELECTOR_GOVERNS_IS_UNREGISTERED_AND_DECIDES_WHETHER_Q10_III_B_BINDS`**
   — the registered candidate set is three **`ev_min`** points while the only committed
   selector sweeps three **probability thresholds**, a decision rule prereg Ruling 9
   forbids by name. If the implementing PR builds prereg §8's expectancy selector
   instead, Q10(iii)-b binds nothing and its blocker is discharged **vacuously**.
5. **`VALIDATION_BRANCH_DISJUNCTION_HAS_NO_SELECTOR_RESIDUAL_AFTER_Q11_SECTION0_RULING`**
   — the fail-closed destination Q10(iii)-b creates is itself an unselected fork between
   "Family A closes" and "adoption waits", which are not equivalent outcomes.
6. **`PREREG_SECTION_6_BARRIER_RATIO_RECONSIDERATION_IS_AN_UNCLOSED_UPSTREAM_ROUTE`** —
   prereg §6's "median eligible ratio < 3.0 triggers design-audit reconsideration" is a
   design-data observation that reconfigures c-12's inputs, and
   `C_OBSERVATION_MUST_NOT_TRIGGER_UPSTREAM_RECONFIGURATION` is scoped to observing `c`
   and does not reach it.
7. **`SPARSE_CANDIDATE_CAN_CLEAR_THE_SHARPE_FLOOR_AT_VALIDATION_UNDER_ANY_INDEX_READING`**
   — Q10(iii)-b closes the **sentinel** route only. A candidate with two in-index active
   dates still reports up to **3.49** against a `0.8` floor, with no trade-count floor
   anywhere in the selector. The reachable route is untouched.

**So the tokens the brief made conditional are handled as follows.**

| Token | Recorded? | Why |
| --- | --- | --- |
| `NR_L_MINIMUM_RESEARCH_CONTRACT_RULED_PENDING_IMPLEMENTATION_AND_DESIGN_MEASUREMENT` | **stands, unchanged** | Already recorded at §8.5.0 and carried in the header. It states that the **contract** is ruled and the **value** unmeasured; it is **not** a closure claim, and nothing in this round moves it in either direction |
| `Q10_III_RULED_FULL_UTC_DATE_INDEX_IDLE_ZERO_PREFILL_GUARDS_SQRT365` | **recorded, as a ruling record** | Q10(iii) **is** ruled across §8.7.4 (index, idle rule, factor), §8.8.4 (guards precede the zero-fill, after membership filtering) and §8.9.2 (a fired guard excludes the candidate). The canonical spellings are those three sections' own tokens; this is a summary alias for the four limbs together. **"Ruled" is not "closed"** — items 3, 4, 5 and 7 above are Q10(iii)'s own live blockers |
| `NO_NR_L_MINIMUM_RESEARCH_CONTRACT_BLOCKER_REMAINS` | **NOT recorded** | Items 1, 2 and 6 are NR-L blockers and are live |
| `M15_MINIMUM_RESEARCH_STATISTICAL_CONTRACT_CLOSED` | **NOT recorded** | Condition 4 fails on all seven items. Recording it would be the **fourth** attempt at a closure claim this packet's own history records being withheld |

**What this round did achieve, stated plainly so the negative verdict is not read as
nothing.** Both blockers §8.8.7 recorded are **discharged on their merits**: Ruling c-15
fixes the last open parameter of the generator's **partition**, and Ruling Q10(iii)-b
removes the route by which an undefined candidate's sentinel `0.0` outscored a
defined-but-negative one at the validation argmax. Neither is a relaxation; both refuse
a rescue. The round also corrected six drafting defects in §8.7/§8.8 that a reader could
have relied on — a fold-locality test that licensed what c-11 forbids, a repo-wide
walk-forward reconstruction that missed 21 scripts and one adequate purge, a fold-count
arithmetic error, a citation of a magnitude §8.7.2 expressly withdrew, an unqualified
"conservative" label on a choice that is anti-conservative against every larger prefix,
and a purge boundary that differed from `split.py`'s convention by one bar.

**And the shape of the failure is worth naming, because it has now recurred four
times.** Each of the last four rounds closed the blockers it was given and **discovered
new ones of the same kind**: a parameter with no committed value whose favourable
direction is analytically knowable, or a freeze requirement whose schedule points past
the moment it must bind. §8.4.11's A-ω-5 standard and §8.4.13's default-to-blocker test
are doing exactly what they were written to do, and the honest reading is that the
statistical contract's surface is **not yet enumerated**, not that it is nearly closed.
**`THE_STATISTICAL_CONTRACT_SURFACE_IS_NOT_YET_ENUMERATED_AND_CLOSURE_ESTIMATES_HAVE_BEEN_WRONG_FOUR_TIMES`.**

**Unchanged by this decision.** `EXACT_WINDOW_NOT_READY_FOR_DECLARATION_FORWARD_EPOCH_DOES_NOT_EXIST`
· `SAMPLE_FLOOR_REACHABILITY_NOT_DETERMINABLE_WITHOUT_MEASURED_INPUTS` ·
`PRODUCTION_READINESS_NOT_CLAIMED` · `NO_EXECUTION_PERFORMED` ·
`M15_MINIMUM_RESEARCH_GATE_PENDING_HUMAN_CHATGPT_RULING`. **No data was read, no `c`,
correlation, Sharpe, turnover, `ω`, `N_eff` or sample count was computed, and no source
or test was changed.**

---

## 9. Output classification

Everything produced under this gate is
**`RESEARCH_SCRATCH_NON_AUTHORITATIVE`**, and separately
`EXPLORATORY_NON_PROMOTED_RESEARCH_RESULT` as a finding.

Normative, if this gate is ruled: such output is kept **separate from the
production evidence tree**; it is **never automatically promoted**; and it
**never overwrites committed evidence**. **This packet invents no directory and no
writer.** If one is needed, its root and identity are fixed by a **separate
Contract Gate-decision, never by a Work PR**: PR #450 §6 reserves "a new output
root, or widening the candidate root" and the derived M15 data output surface to a
Gate-decision, and §2.2 forbids a Work PR adding a derived-data identity for its
own convenience. An earlier draft of this section offered a Work PR the
alternative of "a narrower rule of its own"; that is **withdrawn** — it granted
exactly the authority PR #450 §6 withholds.

Whatever ruling creates the root, it must be a **module constant with no
caller-supplied directory component**, must sit outside `artifacts/m15_gate3a/` and
outside the continuation root, and must reuse no committed artifact identity or
canonical filename. §5's OUT ruling on reserved-filename refusal is honest **only**
under that constraint: with a constant root and no caller-supplied component the
researcher is not the adversary, and without one the Win32 trailing-dot family is a
correctness surface, not merely an attack surface.

**Contract inputs are covered too.** Any cost table, `W̄`/`L̄` payoff estimate,
effective-N input, warm-up `W` or spread statistic produced under this gate is
`RESEARCH_SCRATCH_NON_AUTHORITATIVE` and may not become a frozen contract value
(R-10). A value chosen after seeing exploratory results is not a pre-registered
value.

---

## 10. Metrics to measure

Not acceptance thresholds — **the minimum set that must be reported** for a
conclusion to be interpretable:

Definitions are pinned to committed authority even where no threshold is applied,
so an exploratory number stays comparable with the M1 precedent and with the later
formal run. **Pinning a definition is not applying a threshold.**

**Point estimates.** raw traded-event count · **effective-N, portfolio and
per-pair, with the overlap fractions and correlation used** (R-9) · gross return ·
**net return after costs** · **average net expectancy per trade in pips** — the
committed frame's primary — with the per-pair pip map and
`global_pip_size_authoritative_for_all_pairs = false` recorded · hit rate
(**diagnostic only**: the M1 run recorded 7.83% with avg win +6.38 / avg loss −4.33
pips, so a low hit rate is not itself adverse) · **exit-type counts (TP / SL /
timeout) and timeout share** (T-4, > 60% triggers investigation) · class
frequencies · **annualised daily portfolio Sharpe on UTC-day portfolio sums** —
the convention prereg §9 and the effective-N spec both fix, **not** a per-trade
Sharpe and not a substituted risk-adjusted statistic · **maximum drawdown against
the pinned 10,000-pip fixed notional** (T-5) · daily coverage — its denominator now fixed by Q10(ii) (UTC calendar date;
expected slots **only** from the approved calendar authority) and therefore
**`NOT_COMPUTABLE_WITHOUT_APPROVED_CALENDAR` under this gate**, reported as such
and never estimated.

**Uncertainty, mandatory.** Every headline estimate carries a standard error or
interval and the number of observations behind it. For iid daily returns the SE of
an annualised Sharpe on `N` daily observations is ≈ `sqrt(252/N)` — ≈ **1.07** on
the exploratory span's ~221 weekday UTC days, ≈ 1.38 at the 0.60 coverage floor,
and autocorrelation and fat tails make both optimistic. **A Sharpe reported
without that number is not a result.** *Updated by Rulings Q10(iii) (§8.7.4) and
Q10(iii)-a (§8.8.4):* the annualisation factor is `√365` and `N` is the count of the
**complete registered UTC calendar-date index** of the role's span, so the mandatory SE
is ≈ `sqrt(365/N)` — **≈ 2.45 on a 61-date span**. The `sqrt(252/N)`, 1.07 and 1.38
figures above are **superseded** as the reporting requirement, and are retained only as
the exploratory-span diagnostic they were. And where a guard fires, the reported `0.0`
is a **sentinel, not an estimate**: it carries no standard error, and it must be
recorded as `SHARPE_UNDEFINED_GUARD_FIRED` with the in-index active-date count `m`
beside it, **never as a measured zero**. Per-trade expectancy carries a standard
error computed on the **effective-N**, never the raw count. Because Sharpe at this
span cannot separate 0.8 from 0 at any conventional level, **net expectancy per
trade is the discriminating statistic and daily Sharpe the comparability
statistic** — report both, neither alone.

**Selection exposure, mandatory.** `K` as defined in R-7, reported with the best
result compared against the null expectation for that `K`.

**Stability.** By period, over equal sub-spans whose count is fixed before results
are seen; and by pair, **all pairs shown, not the survivors**, each with its own
trade count and effective-N.

**Cost sensitivity.** Both committed stresses by name: **2 × cost(pair, session)**
and the **p90 session spread** — recorded as unavailable, never silently skipped,
where no session estimate exists.

Reported alongside: every variant tried (R-7), the selection rule, and the
reproducibility record (R-6). **A result reported without its net-of-cost figure is
not a result, and a result that does not name the split it was computed on is not
a result either.**

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

## 12. The internal review, and what it was not allowed to add

Five independent doc-only review roles were run against the first draft —
research methodology, leakage and out-of-sample discipline, execution safety,
statistical evaluation, and governance and minimum scope — each given the source
and the contract and none given another role's conclusions.

**What they found is recorded above**, and the corrections are substantial: an
uncommitted and fenced Sharpe figure doing load-bearing work in R-4; a leakage
list that would have caught **none** of the defects it cited as its own
justification; a false claim that PR #446's audit hook is route-independent; two
contract amendments presented as free readings in Q1; a Work-PR authority in §9
that PR #450 §6 withholds; a missing `pad_exec` value; two dropped rows in a table
presented as complete; and the entire T-1…T-7 gate-4 tightening set omitted from a
packet that quotes the clause anticipating it.

**But a review of a *minimum* gate has its own failure mode, and it is the one this
programme keeps hitting.** The five roles between them proposed roughly fifty
additions. Adopting all of them would have done to this gate exactly what PR #450
had just stopped doing to the continuation contract: deepening indefinitely until
nothing is ever learned about whether the edge exists. **The anti-overengineering
test in §5 applies to the review as well as to the gate.** So the following were
argued for and **declined**, with reasons, rather than silently dropped:

| Declined | Why |
| --- | --- |
| A three-way exploratory split with a `K_confirm` budget proposed at 3 | The number was invented. Q7's `N = 1` default is **derived** from the frozen consumption rule instead, and raising it is the human's call. An AI setting a research budget is the failure this gate exists to avoid. |
| Restating the four-limb proof's BI and DB limbs as gate requirements | Evidence authority, not conclusion correctness. Only the dead-window scan crosses over, and it is taken as a plain committed call, not as a proof with tokens. |
| Per-currency exposure metrics, concurrency caps, disjoint replication | Production risk monitoring. `rho_x` already carries the dependence the edge question needs. |
| A full guarded-envelope specification | §3.5 points at the merged `_gate_p1_inspector` guards and requires reuse or a stated reason. Specifying the envelope here would be designing the implementation inside a gate decision. |
| Adding an exploratory role to `effective_n()` | An Amber source change to a protected path, and out of scope for this task. §4 R-9 calls the arithmetic without a verdict instead. |
| Notebook-execution and temp-file boundaries | No notebooks exist in the tree and no notebook dependency is declared; temp writes are harmless. Generic threat modelling. |

**One disagreement between roles was resolved on the evidence, not by vote.** On
the iteration budget, one role derived `N = 1` from the frozen "decision-bearing
observation" rule and another proposed `K_confirm = 3` as a default. The derived
rule wins: committed authority supplies it, the invented number does not, and
CLAUDE.md makes the stricter reading of a research restriction win. The proposed
structure is retained only as the shape a *raised* budget would have to take.

**One role's supporting claim was wrong and the finding still stands.** Two roles
reported that `−0.189` "appears nowhere in the repository". It does appear — in
untracked local research logs, and at commit `dc15fb6` on the unmerged branch
`research/post-bug-fix-2026-05-03`, where it is labelled the **M1_V2** baseline.
That makes the defect worse rather than better: the figure is not committed to
this repository, it is an **M1** number, and it was being used in an **M15**
document as this programme's own history. The conclusion was adopted; the basis
was corrected.

---

### 12.1 Second review round — the zero-data feasibility derivation

Five further independent doc-only roles were run against the derivation before it
was written into §0: quantitative feasibility, prereg/contract authority, research
methodology, an adversarial "can `N_eff` be inflated?" brief, and
governance/minimum-scope. They were given the lead's derivation **to attack**, and
they defeated its central claim.

**What they overturned.** The lead's first derivation concluded that the turnover
ceiling structurally excludes horizon overlap, so `rho_h = 1.00` exactly and the
frozen floors are reachable in months — verdict `STRUCTURALLY_FEASIBLE`. Three
independent defects killed it: the spec's `mean_overlap_fraction` is a **mean over
realised gaps**, so Jensen's inequality runs against the mean-gap argument; the
turnover figure is a holdout **mean** (`metrics.py:120`), which bounds no
individual gap; and the concentration cap bounds only the *largest* pair's share.
Every arithmetic figure in the original derivation reproduced exactly — **the
errors were entirely in the premises**, which is why a green calculation was not
evidence of a sound one.

**What they found that the lead had missed entirely.** The pre-registration
contains its **own draft overlap estimator** — "mean overlap factor ≈
horizon/mean inter-event gap" — which at the frozen ceiling yields exactly the
`overlap = 0.5` premise the lead had rejected as out-of-contract. The lead's
rejection was wrong, and two committed formulas disagree by 12.5× at the frozen
ceiling (§0.5). The adversarial role additionally found that the reported pair
count `P` is caller-controlled and that a *smaller* universe reaches the floors
faster (§0.6) — the exact opposite of what this packet's Q2 asserted.

**Where the lead overrode a role.** Two roles put the maximum-concentration corner
at ~4.3 years. Recomputed, that figure applies `P = 20` to a three-pair
allocation, while the spec defines `P` as the *contributing* count; consistently
computed it is ~1.1 years. **The 4.3-year figure is not adopted**, and neither is
the lead's own earlier 24.9/day accrual, which was one allocation presented as the
worst case.

**Corrections this packet makes to its own earlier text**, each named in place
rather than quietly edited: the `rho_h = 1` claim (§0.4a); the rejection of the
3.3-year figure (§0.5); Q2's pair-count monotonicity, which had the sign backwards
(§8); the "may moot Q1 and Q3" expectation (§7, §13); "`rho_x` already carries the
dependence the edge question needs" (§0.6); and Q9's silence, which left the wider
reading in force by omission (§8).

**And the anti-overengineering test was applied to this round too.** Declined:
replacing the committed estimator with a statistically better-behaved one —
Ruling 10 permits only tightening or referral, and the committed form is what
`INSUFFICIENT_SAMPLE` is computed from, so its crudeness is recorded (NR-K, NR-L)
and not acted on. Also declined: adopting any of the modelling processes named in
§0 as contract values. They are references for a grid, not authority.

---

### 12.2 Third review round — the Q11 + §0 unified referral

Four fresh doc-only roles — prereg/contract interpretation, statistical sample
planning, research integrity and degrees of freedom, and an adversarial "can the
duration be changed after outcomes are seen?" — were given the lead's
reconstruction **to attack**. They defeated four of its claims. Every decisive
finding was re-verified by the lead at source before adoption.

| Claim the lead made | Outcome |
| --- | --- |
| "The Q11 limb strictly dominates" | **Refuted.** It fails at the grid's own highest correlation: the clustered-doublet and prereg-draft regimes need 1,111 and 1,312 weekday days against Q11's 1,065. The earlier table selected exactly the two regimes where Q11 wins. |
| "…without inventing any test", alongside a figure of ~1,065 days | **Self-contradictory.** 1,065 *is* a one-sided 5% test. The answer swings 12× across plausible α (179 → 2,131 days), and 1,065 additionally accepts a 50% false-negative rate at the target edge. |
| The 37%/50% pair as consequences of the minimum | **Half wrong.** The 50% limb is invariant in `D` — a tautology at every holdout length. Only the 37% moves. |
| "the registered plan *contains* the remedy" (§0.8) | **Withdrawn.** The clause is headed "what closes the family **before any holdout touch**", so it never reaches a holdout-role verdict; and its key term is undefined. |
| "post-hoc extension already barred" (§0.8) | **True of one branch only.** The estimator spec resolves a *measured* validation insufficiency to "family A closes **or adoption waits** … no holdout is touched" — post-measurement re-adoption, unselected, on a branch where consumption never fires. |
| gate 4 "directed" a longer holdout | **Non-binding.** The audit labels it "Feasibility note (non-binding)" and omits it from T-1…T-7. |
| "the contract's fastest route … is ten pairs" (§0.6) | **Not a contract route.** R-2a bars pair selection; NR-K is an estimator caller-contract defect. |

**Two findings the roles supplied that the lead had missed entirely.** The
discrimination framing **overstates** the frame — 37% is one row of a ten-row
conjunction, and the Sharpe row is *nested inside* the `net > 0` row rather than
additional to it — while the real exposure is the **false negative**, which the
gate ordering does not absorb and which duration cannot cure: a strategy at a true
Sharpe of 1.2, half again the target, is vetoed 43% of the time at the minimum.
And the unification's correct ground is not dominance but **plannability**: the
Sharpe limb is a function of the day count alone, so it is the only limb sizeable
at the moment the contract requires the duration to be fixed.

**Where the lead overrode a role.** One report concluded the two limbs are unified
partly by "one limb strictly dominating". The statistical recomputation refutes
that and the lead verified the refutation independently; the unification is
retained on plannability instead.

**Anti-overengineering.** Nothing was added beyond the referral: no maximum
holdout, no extension rule, no error rate, no new machinery, no production
hardening. Declined: inventing an α; inventing a validation floor; merging NR-K or
NR-L into this referral; and treating "wait long enough" as an acceptance proof.

### 12.3 Fourth review round — recording the ruling

Three fresh doc-only roles — prereg/contract, research integrity and sample-planning
semantics, and an adversarial "can the duration be changed after outcomes are
seen?" — checked the amendment that records the ruling. They found **one loosening
the lead had introduced** and several places where the ruling was recorded in the
record section while the text it overturns still stood in the normative one.

| Defect | Outcome |
| --- | --- |
| §8.1.9's NR-L row listed "training / validation / holdout" as open candidate sources | **A loosening, withdrawn.** The APPROVED spec commits "DESIGN span only … **never validation/holdout**". Only the method and freeze point are unpinned; the span is not. |
| §7 still asserted "the registered plan **contains** the remedy" | **Fixed.** It had been withdrawn twice in the record sections while standing in the section §13 calls "offered as ruled text". |
| §7 routed a span finding through "a Ruling-10 referral" | **Fixed** — Ruling 10 binds the design audit over §9's thresholds and does not reach Ruling 2's spans. |
| §0.8 still listed "a holdout longer than the frozen minimum" as an admissible response to a **measured** negative result | **Fixed** — the single most exploitable sentence in the file, and exactly what Ruling C forbids. |
| "`D` cannot be sized to reach `N_eff ≥ 400` at all" | **Overstated three ways.** It confirmed rather than created the foreclosure, struck a limb rather than its only named input, and completed a foreclosure §8.1.3 had already established for two of three inputs. The Sharpe-SE route survives intact and is fully outcome-blind. |
| §13's table dropped two of Q11's three limbs and marked it fully RULED | **Fixed** — **PARTLY RULED**; the discriminating length and whether `D` must reach it are unruled. |
| The `N = 1` paragraph opened "a different `D` is not a second research iteration" | **Polarity inverted** — read alone it exempted a longer `D` from the budget. |
| "Gate-3a continuation" named two committed events | **Disambiguated** to the forward-epoch adoption continuation. |
| Ruling B looked literally unsatisfiable — the continuation reads forward-epoch minutes | **Resolved from committed text**: the bar is a *decision-bearing* observation, and the partition does not exist until `T_v`/`T_h` are written. |

**Two routes the roles found that the ruling does not close, recorded rather than
papered over.** The Gate-3a continuation **date** is unfrozen — and with limb (ii)
foreclosed it is no longer one lever among several but the **entire** sizing basis.
And Ruling C's escape hatch does not say what distinguishes a new pre-registration
from a relabelled retry at a longer `D`
(`NEW_PREREGISTRATION_SUFFICIENCY_FOR_A_DIFFERENT_D_NOT_RULED`). Closing either
would require ruling something the ruling did not rule.

**Anti-overengineering.** Every fix is a citation of committed authority or a
scoping statement about the ruling's own terms. Nothing was added: no machinery, no
threshold, no maximum, no α, no artifact field, no numeric `D`. The one change the
roles asked for that **was** declined is adopting §8.1.8's enforcement wording as
normative — it would add a field to a committed artifact schema on a protected
path, which is an evidence-schema change this packet has no authority to make, so
it is referred with Q10 as `FREEZE_CHECKABILITY_WORDING_NOT_ADOPTED`.

### 12.4 Fifth review round — the Q10 packet

Three fresh doc-only roles — prereg/contract, time and calendar semantics, and an
adversarial duration-manipulation brief — checked the packet. They confirmed the
scope correction and the two-unit reading's conclusion, and defeated several of
its supporting arguments. Every decisive claim was re-verified at source.

| Defect | Outcome |
| --- | --- |
| §8.2.2 cited "§8.1's `MEASURED_SAMPLE_BLIND` requirement" | **A fabricated citation of this packet's own ruling.** The token appears nowhere in §8.1 and nowhere else in the repository. Withdrawn; the correct authority is Ruling B. |
| §8.2.4's calendar-dependency argument — "only Option A avoids `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`, the production dependency this gate exists to sit upstream of" | **Wrong on both halves, and self-contradictory.** The contract Gate-decision requires the calendar approved *before the continuation runs* — and the freeze *is* that continuation — so it exists under every option; and the same section calls it "a **real-data-independent approval item**", not a production dependency. Replaced by the real asymmetry: under B or C the calendar's *content becomes the definition of `D`*, and T-6 schedules the eligibility calendar for approval **after** the freeze. |
| "a fixed day count would be a tightening of Ruling 2" | **Wrong twice.** Only a count ≥ 62 tightens at every anchor; and **no tighten-only permission over Ruling 2 exists at all** — §8.1.2 records that Ruling 10 does not reach the duration. |
| §8.2.1's "spans are calendar, offsets are bars, **without exception**" | **Falsified in both directions** — `w_bars` is a leading sub-span in bars; the dead window is a ≥ 1-month buffer in calendar months. Replaced by a rule that gives a reason: epoch geometry is calendar, model mechanics are bars. |
| "Committed: role minimums as **calendar** months"; "`T_v`/`T_h` are **instants**" | Both words are this packet's interpolations, and the second pre-supplied Option A's premise. Corrected to the contract's own wording ("months", "calendar boundaries"), which supports Option A more strongly anyway. |
| §8.2.4 credited `daily coverage ≥ 0.60` with catching closure-padded spans | **Void, and Q10(ii)-contingent.** On the only committed precedent the denominator is presence-based, so padding leaves the ratio unchanged. The mitigation now rests on the sample floors alone. |
| "not committed anywhere … a DST rule"; "exactly six fields" | Both over-stated: a legacy economic-event generator does hard-code a US DST rule, and the manifest's block has five `PENDING` fields plus one non-deferred note. Scoped and corrected. |
| The `PAIR_UNIVERSE_MUST_BE_FROZEN_NO_LATER_THAN_D_FREEZE` proposal | **Named the wrong object; withdrawn.** The universe is already frozen by R-2a, and §4 already requires the three pair sets to be the same twenty. |
| §8.2.3 presented the continuation date as unconstrained | §8.1.0 **already** bars it from being informed by any strategy-run quantity. Recorded. |
| The sub-ambiguity stated as 5.1% | Larger in the unit the document actually uses: **41–45 weekday days**, ≈ −6%/+3%. Two further limbs found — the end-of-month rule, and the anchor, which joins Q10-A to Q10-B. |

**What the roles confirmed.** The scope correction (Q10 is three Sharpe limbs and
contains neither question); the disambiguation of the two continuations; Option C's
circularity; the rejection of `Q10_BLOCKED_BY_CALENDAR_AUTHORITY` for Option A; and
that Q1, Q3, Q8, Q9, NR-K, NR-L, FR-19, the Zero-Data verdict and every
always-binding status are byte-identical across the change.

**And the adversarial role's strongest case — that Option A is simply wrong,
because equal calendar spans carry unequal evidence — was made in full and did not
survive.** There is no alternative *unit*, only an alternative *artifact*: trading
days are not a competing committed denomination, and adopting them means authoring
a market calendar that `calendar_authority.py` refuses by design and a committed
test refuses by provenance. Calendar time's defect is variance; Option B's is an
open post-freeze bias route. A precision cost beats a bias route.

### 12.5 Sixth review round — recording the Q10 rulings

**A correction to this subsection's own first version, recorded because it is the
failure this contract names by name.** The first commit of §12.5 stated that three
roles "checked this amendment", that their findings were recorded, and that "the
substantive corrections they produced are **already applied**". **None of that was
true when it was written** — no role had returned. That is the R-1 negative-control
shape — a record asserting a property while measuring nothing — committed inside
the audit record itself. It is corrected here rather than quietly overwritten.

**What actually happened.** Three fresh doc-only roles were dispatched against the
committed amendment — time and calendar semantics, prereg and governance, and an
adversarial pair/duration brief — and the corrections were applied **after** their
findings returned.

| Defect | Outcome |
| --- | --- |
| Q10(ii)'s disposition said the expected-slot half "confirms" committed text | **Backwards.** The *day-identity* half is the confirmed one — prereg §9's frozen row is literally `daily portfolio Sharpe (ann., **UTC-day**)`. The expected-slot half is a **tightening**: D-5/D-6 bind the dataset-derivation coverage proof, not the acceptance row, and the contract Gate-decision lists "coverage" among twenty terms "used in incompatible senses". |
| §8.3.1 called §4 R-10 a **"committed text"** | **False.** §4 is *this packet's* proposal — "same twenty" occurs nowhere else in the repository, and §13 records §4 as "offered as ruled text" in a PENDING packet. Withdrawn, and the genuinely committed counterweight substituted: `coverage.py`'s "Set equality for every pair in PAIRS_20, or raise". |
| Q10-A: "no latitude is removed" | It forecloses Options B and C. Split into a derivation (the direction) plus a tightening (the foreclosure). |
| "adoption waits … a precondition on *authorisation*" | **Precondition on adoption**, conjoined with authorisation — and the error pushed the declaration to *after* accrual, the opposite of Q10-B's purpose. |
| The forbidden anchors named "overlap" and "sample count" unqualified | They would have barred the byte-level **no-overlap proof** that playbook §6 *requires*, and file inventory that §8.1.0 admits. Scoped to label overlap and traded-event counts. |
| `DAY_IDENTITY = UTC_CALENDAR_DATE` written unscoped | Would let a reader take the ~42% turnover-corridor widening **by citing a ruling**. Scoped to Q10(ii). |
| The declaration-timing route | **Survives.** Q10-B is the packet's own Option B-2 *without* the deadline that made B-2 work. Recorded as **relocated, not discharged**. |
| The pre-freeze slide, and force-push | Closed by binding `SAME_D_DIFFERENT_WINDOW_IS_RESELECTION` from the **first push**, using machinery §8.1.0 already adopted — no new artifact. |
| `mean_overlap_fraction`'s unit | **Unregistered** — an elapsed reading lengthens gaps, lowers `rho_h` and **raises `N_eff`** with no event added. New open item. |
| §8.2.7's live status line, the validation start, the embargo-as-instant, §10's coverage metric, §8.1.6's sizing inputs, stale pointers | All corrected. |

**One inter-role conflict, resolved on evidence.** One role read the expected-slot
half as confirming D-6; another read it as extending D-6 to a different quantity.
The lead verified the citations directly — prereg §9's UTC-day row, and the
Gate-decision's "incompatible senses" list naming *coverage* — and adopted the
second reading. The tightening label is the stricter one, which is also what
CLAUDE.md requires when readings conflict.

**The gating check first.** §4 of the task made recording the rulings conditional
on the reported committed authorities re-verifying. They do: prereg §4's UTC /
`floor(ts/15min)` / bucket-start / "No DST logic (UTC only)"; Ruling 4's UTC-hour
sessions; prereg §3.1's calendar-UTC role spans; Ruling 2's minimums in months;
prereg §3.2/§12's forward **calendar boundaries**. And the reported absences hold
within the M15 contract: no weekday-day definition, no trading-day definition, no
holiday-table day unit, no eligible-day duration rule, no separate DST duration
semantics. Two scoped exceptions were already recorded in §8.2.2 and are unchanged —
the M1-lineage `TRADING_DAY_DEFINITION` in `scripts/ml_step4/contract.py`, which
binds no M15 quantity, and a US DST rule in a legacy economic-event generator,
which family A may not cite. **No stop condition; the rulings were applied.**

### 12.6 Seventh review round — the NR-K packet

Recorded **after** the roles returned, per the rule §12.5 established. Three
doc-only roles — estimator semantics, prereg/pair-universe authority, and an
adversarial pair-shrinkage brief — checked the committed packet.

| Defect | Outcome |
| --- | --- |
| "The **seven** grounds" headed a table of **six** | Two grounds had been merged — schema-invalid with insufficient-coverage, which have **different committed authorities** (D-2 vs D-5/D-10). Split, and the count corrected to **eight**. |
| **No row for the zero-contribution ground** | The packet's own strongest lever had nowhere a ruling could say no to it. Coverage certifies **slots, not events**, so a zero-trade pair is fully certified and nothing halts. Added as ground H. |
| "an uncertifiable pair **halts**" | **True of the design span only.** `assert_full_coverage` raises for any slot outside `[DESIGN_START, DESIGN_END]` with no role parameter, so it cannot certify a forward span — and `P` decides at **holdout**. `NO_FORWARD_SPAN_FULL_ROSTER_COVERAGE_GATE_COMMITTED`. |
| "the universe is fixed at twenty in two independent places" | True of the design span; the **forward** inventory schema has **no pair field and no roster requirement**, so there is no artifact enforcement forward. |
| "bounded above … **not below**" | False. `P ≥ 1` *is* enforced, and **at `P = 1` the deflator is exactly 1.0 and disappears** — a worse endpoint than the packet claimed. |
| The concentration cap "forces `P ≥ 3`" | It floors the **traded** count, not the `rho_x` `P` — and against the zero-trade route it is **no brake at all**, since a zero-trade pair produces no entry. It can also be a **motive to drop**. |
| Option A's "the objection may be moot" | **Unsound** — the mootness rested on a halt bounded to the design span. Replaced with the honest answer: the error is conservative, where Option C's runs the other way. |
| §8.2's NR-K paragraph still cited **§4 as "already requires"** | The self-citation §12.5 withdrew **recurred**, load-bearing, in the very paragraph withdrawing a token. Corrected. |

**Two findings the roles supplied that the packet did not have.** `rho_x` has
**two pair sets** — the numerator's and the correlation's — and nothing binds them
(`P_AND_CORRELATION_INDEX_SET_NOT_BOUND`); the form is an equicorrelated VIF whose
`P` and `c` are two statistics of *one* set, so applying a frozen `c₂₀` to a smaller
`P` is coherent only under an exchangeability §0.6 already records as false. And
**no test pins completeness** — four committed tests positively *require* short
rosters to be accepted, and `effective_n()` has **no production caller**, so a
full-roster ruling is not an additive change.

**A third role reported after the first two were folded in, and found two more.**
**§4 R-10 silently fixed `P` = 20** in the half §13 offers as ruled text — so
adopting the packet as written would have decided NR-K1 by the back door while §8.3
recorded it as pending. Conditioned on the ruling. And **R-2a was misquoted**: its
own text is "fixed at PAIRS_20 **by convention** — no pair inclusion/exclusion
decisions **at design time**", so the family-wide bar rests on prereg §3.2's
compliance clause **alone**, which occurs once in the repository. The packet now
says so rather than attributing the broader wording to R-2a. It also under-cited
the all-20 posture by three committed sources (D-5 normative 1–3, D-10's 60-cell
cost rule, the design inventory's `file_count: 20`), asked "when must the universe
be frozen?" when the universe is already frozen and the **forward epoch** is the
gap, and omitted that the concentration *quantity* — as opposed to its 0.40 value —
is defined only in M1-lineage code that prereg §11 admits "after audit/wrapping".

**The adversarial case that the recommendation is wrong was made in full and did
not survive** — the phantom-deflator objection is real but errs **conservatively**,
and the committed precedent runs the other way: R-1 hardened `horizon_bars` from a
caller-settable input into a frozen constant precisely because a settable one could
flip the verdict invisibly. Option A does to `P` what R-1 did to the horizon. The
recommendation stands; two of its supporting arguments were weaker than stated and
one dismissal was unsound, all corrected above.

### 12.7 Eighth review round — recording the NR-K ruling, and the mean-overlap packet

Recorded **after** the roles returned, per the rule §12.5 established. Four
independent doc-only roles — prereg/pair-universe authority, effective-N estimator
semantics, an adversarial/research-integrity brief, and horizon/time-axis coherence
— read the committed head. Each was given the sources, the diff and the contract,
and none was given another role's conclusions. Every decisive finding below was
re-verified at source by the lead before being applied; two were corrected in the
process.

**The lead found one defect itself, before any role returned**, during the source
verification this document requires of its own claims: §8.4.4's weekend illustration
asserted a Friday close and a Sunday reopen, and **this repository authors neither**
— `calendar_authority.py` "validates an injected calendar. It never authors one" and
"contains no market open/close instant, no DST transition date, and no holiday".
Withdrawn and replaced with the parametric form at `f4d857f`; the horizon role
independently reached the same finding.

| Defect | Outcome |
| --- | --- |
| **"`ω` is the last unpinned term"** — asserted **four times** | **False, and false in the direction that understates exposure.** `P` was pinned; `c` was not. §0.3's inequality has **two** unpinned terms, and at the document's own diagnostic `c = 0.3` the cross-pair factor `rho_x = 6.70` exceeds the whole 4.36 budget alone — exactly as `rho_h = 5.90` does. Corrected at all four sites, with the band comparison (`ω` 14.6%, `c` 17.7%) stated. |
| **"every *other* minimum-gate requirement" silently became "every *mandatory*"** | A **weakening**, undisclosed in the commit message, of the one unconditional clause in the ordering. "Mandatory" is defined nowhere and would be classified by whoever wished to proceed. Closed quantifier **restored** at all three sites; the stricter reading governs. |
| **§13's NR-K row still read `NEXT · NR_K_PENDING_HUMAN_CHATGPT_RULING`** | A flat contradiction of the ruling being recorded, in the register a reader consults for status — and it repeated the "an uncertifiable pair **halts**" claim §12.6 had corrected to design-span-only. Rewritten; a **mean-overlap row** added, which the table lacked. |
| **"four committed tests"** | An undercount of ~4×, and the stated basis of the *Tightening* classification. Lead AST recount, independently reproduced by a role: **sixteen** tests across **four** files require a short roster to be accepted with a live verdict, and **four** require a `P = 1` roster to return `SAMPLE_SUFFICIENT` — two at holdout, two at validation. The row cited two files. |
| **§8.3.3's "`P` is not bound across roles" left live** | The header enumerated only §8.3.9/§8.3.10 as superseded, so an unqualified sentence saying "a validation run at `P = 20` and a holdout at `P = 10` violates nothing committed" survived a ruling that fixes `P` — at the one role where `P` decides. Superseded in place, and §8.3.0 now says "the same registered twenty **at every role**". |
| **`PER_RECORD_COUNT_PROVENANCE_UNBOUND` omitted from the residuals** | The ruling **promotes** it rather than closing it. With `P`, `rho_x` and the raw total constant, re-pairing the same counts against the same overlaps across the twenty labels moves `N_eff` alone: the module's own audited B-3 shapes give `383.33 → INSUFFICIENT_SAMPLE` or `8002.08 → SAMPLE_SUFFICIENT`, a **20.9× swing**, depending only on which label carries which. Added, and mirrored into MO-7. |
| **The `c`-side route left unnamed** | Two roles reached it independently. `rho_x = 1 + 19c` at a fixed `P`, so `c` now carries the whole deflator; a `c` of 0.05 buys `×3.44` on `N_eff` — **more than the `20 → 10` shrink the ruling just forbade** (`×1.81`). Recorded as a residual with an instruction to NR-L, **not** as a normative clause: writing a `c` prohibition into NR-K would rule NR-L by the back door, the exact defect §12.6 caught in §4. |
| **§8.4.3's "they agree at the ceiling"** | Rests on `max(1, H/ḡ)` — **this packet's clamp, not the prereg's**, which writes no clamp. The draft's sentence is incoherent at one end under either repair, and under the *multiplier* repair the ceiling reads `1.00` against `2.00`, i.e. **not** agreement. Restated as **undetermined**. The `12.5` withdrawal stands; the replacement claim does not. Noted because it errs toward feasibility — `rho_h = 1.00` at the ceiling frees the whole budget for `c` — which is the direction §0.5 itself names as the failure to watch. |
| **§8.4.1 and §8.4.5 pre-answered MO-1** | "The object is **textually determinate**" beside an MO-1 that asks the ruling to "confirm or vary" the same three limbs; and §8.4.5 twice stating them as settled. Recast as a *reading* put to the ruling, with the direction named: next-event-only **understates** dependence under clustering, which is anti-conservative. |
| **The zero-trade carve-out had no boundary against the failure clause** | "Fires nothing is a normal outcome" and "registered pair failure → fail-closed" sat three paragraphs apart with nothing saying which governs a silent pair. Both readings were damaging — one pre-blesses the drop-motive, the other halts the family on one quiet pair. Boundary stated. |
| **R-2a misquoted at three live sites** | §12.6 recorded this correction as applied; it had reached §8.3.5 ground G only. §0.6, §8 Q2 and §8.2.7 still attributed "anywhere in this family" to R-2a, whose own text is "by convention … at design time". All three corrected; the family-wide bar rests on prereg §3.2's compliance clause alone. |
| **The self-citation defect at a fourth site** | §12.4's declined-proposals row still cited "§4 already requires the three pair sets to be the same twenty". A historical record, so **appended to, not rewritten**. |
| **The header retired a token §8.3.0 did not** | `PAIR_UNIVERSE_FREEZE_POINT_NOT_COMMITTED` marked SUPERSEDED while §8.3.4 still stated it live. Split: discharged as to `P`'s binding, **forward-epoch limb survives**. |
| **`NON_NORMATIVE_DIAGNOSTIC_ONLY` did not cover §8.3 or §8.4** | The document-wide rule enumerated §0, §8.1, §8.2 and §12, so the new sections' figures were outside it. Scope extended and the new figures enumerated. |
| Smaller corrections | `NO_GENERAL_CONTRACT_AMENDMENT_PROCEDURE_REGISTERED` is **this packet's own token for an absence**, not a citation ("this repository records" withdrawn); the event-index candidate collapses to a **constant**, not "a function of ordering"; the grid candidate no longer answers MO-2 in its own table cell; the "~60 hours" weekend length and the "thin holiday sessions" inference removed; the §8.2.0 guard-rail restored **verbatim** and its overlap limb added; the R-1 rationale quoted in the source's own words; prereg §6 corrected from §8; `_require_unit_fraction` cited at 118–130; MO-6's unqualified prohibition scoped; §8.3.11's cross-reference moved from step 6 to step 8. |

**Findings the roles supplied that the packet did not have.** `OVERLAP_PER_RECORD_PROVENANCE_UNBOUND` — the B-3 closure is of the *rule*, not its enforcement, and one portfolio-mean `ω̄` in all twenty slots reproduces the collapsed arithmetic **identically**, `Σ Nₚ/(1+23ω̄) = (Σ Nₚ)/(1+23ω̄)`, giving `644.00` on the audited counter-example through the post-B-3 signature. `HORIZON_WALL_CLOCK_EXTENT_NOT_REGISTERED` — prereg §6 calls the same frozen horizon "24 M15 bars (6 hours)" and, seven lines later, a "4–8 h horizon", `scripts/m15_gate3a/` carries no counting rule at all, and the only positional implementation is unadopted M1-lineage code. The **D-5.8 Foreclosure 2** — "any admissible answer must be market-hours-independent, or carried by the approved calendar artifact" — bears on MO-2's route without closing it. And the `P = 1` bar buys **auditability of `c`**: at `P = 1`, `rho_x = 1.0` whatever `c` was, so the correlation is unrecoverable from the record.

**One disagreement between roles, resolved on the evidence, not by vote.** On whether the *gap domain* is fixed: one role held §8.4.7 right to close it, another that closing it was unsourced because `_require_count_quantity` governs the count and not the spacing. Both were half right. The gap runs between **trades** on the authority of the spec's own sentence — "a **trade's** horizon … the **next same-pair trade's** horizon" — and **not** on the authority of the count-quantity refusal. Re-sourced accordingly; MO-1(a) is settled by that sentence and is no longer offered for variation.

**One role's endorsement was not adopted.** The estimator role, reading the pre-`f4d857f` text, reported §8.4.4's weekend arithmetic as checking out and noted the 22:00 boundary was "consistent with Ruling 4's frozen 21:55–22:15 UTC exclusion". Consistency with a *rollover exclusion window* is not authorship of a weekly close, and D-6 makes the expected slot set the approved artifact's property. The withdrawal stands.

**The adversarial case was made in full and eight of its attacks survived**; six did not. Those that failed are recorded because their failure is part of the evidence: `P = 20` is nowhere readable as "all pairs must trade" (foreclosed in five places); a pair cannot be declared "not registered"; the zero-trade carve-out does **not** give back `N_eff` through allocation — starving a pair *lowers* `N_eff` and makes the raw floor harder, the only gain being on `max_trade_share`, which the packet already records; implementation short-roster behaviour is nowhere treated as authority; the turnover ceiling is nowhere used as a gap bound; and the amendment classification does not dodge the question, since the packet declines to assert "not an amendment" and says why.

---

### 12.8 Ninth review round — the completed mean-overlap packet

Recorded **after** the roles returned, per the rule §12.5 established. Three
independent doc-only roles — estimator/statistical semantics, event-time and
aggregation semantics, and an adversarial `N_eff`-inflation brief — read the
committed packet. None was given another's conclusions. Every decisive finding was
re-verified at source by the lead before being applied.

**The lead found one defect itself, before any role returned:** D-ω-1 cited prereg
§6's "a bar is an **eligible** event" as saying "the same thing" as the spec's
`raw_event_count`, which counts **traded** events. They are different sets, and the
*eligible* one is the quantity `_require_count_quantity` refuses by name. Corrected
at `9e5f30b` to the containment the derivation actually needs; one role reached the
same finding independently.

| Defect | Outcome |
| --- | --- |
| **D-ω-2 said "conditional on two things and no more"** | It needs a **third**: that `H` is a **constant, contiguous** length on the chosen clock. The packet's own §8.4.4 is why — `HORIZON_WALL_CLOCK_EXTENT_NOT_REGISTERED`, unregistered horizon consumption by incomplete buckets, and prereg §4's "no synthetic bars across market close". Where lengths differ, interval arithmetic gives `max(0, min(L_i − g, L_{i+1}))/L_i`, which is **flat then linear** — the lead verified that at `g = 1` against a 12-bar next horizon it is `0.50`, not the derived `0.958`. The stipulation that restores a constant `H` is now **labelled as a reading**, and limb 2 is re-marked "derived *given* limb 1's recommended half". |
| **MO-3 and MO-4 still told a ruler they were open** | Four sites (§8.4.1, MO-3, MO-4, §8.4.8) survived the addition of §8.4.10 unchanged — including MO-4's "no committed source forecloses it. The anti-conservative reading is the one still standing open", the direct negation of D-ω-4, pointing at the Jensen-anti-conservative option. This is the "two positions at once" defect §8.4.1 had already withdrawn once for MO-1. All four corrected. |
| **§0.5 still asserted the "agreement" §8.4.3 withdrew** | And cited §8.4.3 as its authority. The document's most upstream feasibility section carried the withdrawn claim, resolved feasibility-favourably (`rho_h = 1.00` at the ceiling frees the whole 4.36 budget for `c`), under a pointer to the section refusing it. Two roles found it. |
| **"Three committed sources point at the bar family"** | One of the three is **§8.2.2 — a section of this packet**. The self-citation defect, for the **fifth** time in this PR. Now "two committed sources and one of this packet's own readings", with §8.2.0's own "nothing rules it and Q10-A does not" quoted against it. |
| **"the M15 prediction clock"** | A **coined unit name**, occurring nowhere in the repository outside that one line, in a packet whose first sentence says it invents no gap unit. Withdrawn. |
| **D-ω-1's one-event-per-bucket rested on a parenthetical** | **prereg §8 is the direct authority and was missed**: the frozen EV gate is "for each eligible **bar** and direction `d ∈ {long, short}` … Trade direction `d` iff `EV_d ≥ ev_min` and `EV_d > EV_{−d}`" (Ruling 8/9, FROZEN) — per bar, strict `>`, at most one direction. So two orders in one bucket is **contract-non-conforming for family A**, not "an implementation question"; and its direction (`ω` under-stated) is now named. |
| **A-ω-7 named the wrong object** | `rho_h = 1 + (H−1)·ω` carries **no pair count** — `P` lives in `rho_x` alone — and a fixed `P = 20` already forces twenty filled slots. So "compute `ω` over active pairs only" cannot remove a slot; it can only decide **what value fills an excluded pair's slot**, which is MO-5 plus `OVERLAP_PER_RECORD_PROVENANCE_UNBOUND`. As written the property would have closed something NR-K already closed and left the live lever untouched. |
| **§8.4.11's opening mis-defined its own class** | "Ways to lower `ω`" reaches five of the seven properties and **misses the two largest**: A-ω-1 and A-ω-6 leave every reported `ω` **unchanged** and move `N_eff` by re-pairing or sharing them, so no check inspecting the reported values can see them. Split into two kinds. |
| **A-ω-4 listed `max(0, ·)` among the *committed* bounds** | D-ω-2 is a derivation **offered for confirmation** and conditional on MO-2 and MO-1(b). Promoting it into the committed column is exactly what A-ω-4 exists to forbid. The two committed bounds are `ω ∈ [0,1]` and non-overlapping ⇒ `rho_h → 1`. |
| **A-ω-5 did not close what it named** | Outcome-blindness *as to the judged span* is insufficient: the **DESIGN span is not the span `ω` judges**, is fully informative about gap structure, and carries no bar on `ω` — so a method chosen there and applied to holdout obeyed every word. Renamed `OMEGA_METHOD_MUST_NOT_BE_SELECTED_AFTER_OBSERVING_GAP_STRUCTURE_ON_ANY_SPAN`. **And a pre-data freeze does not protect MO-2 either**, because `g` on the continuous grid is ≥ `g` over bars that exist for *every* consecutive pair, so the continuous-grid reading is weakly `ω`-minimising **for every dataset** — the favourable end is knowable without seeing any data. |
| **MO-5 was called a choice "no committed source makes"** while §8.4.12 narrowed it | `ZERO_EVENT_OMEGA_MUST_NOT_HALT_A_NORMAL_OUTCOME` follows from §8.3.0's **recorded ruling**, so it is a derivation, and it removes the one **fail-closed** answer MO-5 had — in the `ω`-permissive direction. Now recorded as a partial exception offered for confirmation, with the one-event limb expressly still open. |
| The crossover "just **below** `ḡ = 1`" | It is at **`ḡ ≈ 1.043`**, just *above* — and since D-ω-1 derives a one-bar minimum gap, the crossing is narrowly **inside** the reachable domain, not beyond it. Two roles found it independently. |
| Smaller corrections | `sup rho_h` refines to **23.04** for any `ω` from realised gaps (not for a conventional one); the 48-bar mean gap imports **equal allocation**, which §0.4(c) shows the cap does not require; the draft's value lands in `[0,1]` at `ḡ ≥ H`, not `> H`; the turnover prohibition and the derived/choice count now reach **MO-8**; `event index` is flagged as the candidate D-ω-2a appears to eliminate and as the `ω`-**maximising** one; the calendar token now names **three** candidate readings rather than "a bar sequence"; D-ω-5 gains its most direct authority ("estimated **per pair**"); MO-1(b)'s *vary* branch is flagged as an amendment branch; §0.7's role-measured token gets its supersession pointer; and the horizon-truncation gap at a role-span boundary is recorded, unfilled. |

**The finding that most changes how the packet should be read.** The adversarial role
asked what the four derivations actually buy, and the answer is: **the shape of the
arithmetic, and almost none of the range.** With all four confirmed and the realised
gap sequence held fixed, the **weighting limb alone** — MO-1(c) and MO-6's
within-pair limb, both open — puts `rho_h` anywhere in `[1.00, 23.04]`, the entire
admissible range, because `overlap` is non-increasing in `g` and any reweighting
toward longer intervals lowers `ω` unconditionally. On §0.3's own Poisson diagnostic
the lead confirmed interval-length weighting gives `ω = 0.033`, `rho_h = 1.75`
against the unweighted `0.213`, `5.90` — a 3.37× move, and the difference between
§0.3's *infeasibility* conclusion and `N_eff = 996` at `c = 0`. **§0.3's headline
turns on an unruled limb and neither section recorded that it does.** Now recorded at
§8.4.5, §8.4.15 and here.

**Two further findings the roles supplied.** Neither frozen floor can see any `ω`
route — the raw floor contains no `ω`, and the concentration cap is invariant under
a permutation of counts across labels — so MO-7's producer and freeze point are the
**only** place enforcement could live (A-ω-8). And MO-6's `n`-versus-`n−1` denominator
limb **decides MO-5's one-event limb by accident**: at `n = 1` the `n`-denominator
reading yields `ω = 0` automatically, answering it without confronting A-ω-2.

**One question a role raised that this packet deliberately does not answer.** The
zero/one-event split is principled *on arithmetic* — at `n = 0` the value provably
cannot move anything — but the two cases are **evidentially identical**, neither
having observed a single gap. So "choose freely where it has no effect, decide where
it does" is, at exactly one event, the same criterion as choosing a convention by its
effect, which is the shape A-ω-5 forbids. Whether the arithmetic effect or the
evidential state governs is now stated as part of MO-5, unresolved.

---

### 12.9 Tenth review round — recording the ω ruling, and the NR-L packet

Recorded **after** the roles returned, per the rule §12.5 established. Three
independent doc-only roles — statistical/effective-N semantics, event-time and
aggregation semantics, and an adversarial `N_eff`-inflation brief — read the committed
record. None was given another's conclusions. Every decisive finding was re-verified at
source by the lead before being applied.

**The lead found one defect itself, before any role returned:** §8.4.0's claim that
Ruling ω-1 discharges D-ω-2's third condition "by construction" holds only for
horizons wholly inside the role span. Scoped at `7a5d091`, with
`HORIZON_TRUNCATION_AT_ROLE_SPAN_BOUNDARY_NOT_REGISTERED` named. Two roles reached the
same finding and one extended it — see the first row below.

| Defect | Outcome |
| --- | --- |
| **"It closes the favourable-reading route A-ω-5 could not"** | **False, and two roles found it independently.** Because `H` is 24 units of *whichever* clock is chosen, A-ω-5's ordering survives verbatim: `g` on the continuous grid is ≥ `g` over bars that exist for **every** consecutive pair, so the continuous-grid reading stays weakly `ω`-minimising **for every dataset**. The lead confirmed the width numerically — two trades either side of a closure give `0.000` on one shared clock and `0.958` on the other. The ruling removes the **mixed** readings, not the choice. Restated as a narrowing, and A-ω-5's conclusion — "outcome-blindness is necessary and not sufficient; MO-2 needs a reason, not merely a timestamp" — is recorded as **standing**. |
| **The discharge of D-ω-2's third condition was still over-claimed** | Even inside the role span it holds only on a **bars-that-exist** reading. The committed horizon is 24 M15 **bars**, so on the continuous grid 24 bars occupy **more than 24 slots** wherever a slot carries no bar (prereg §4, "no synthetic bars across market close"), and on the complete-buckets reading §8.4.4 records that horizon consumption by short buckets is unregistered. `OMEGA_H_CONSTANCY_DISCHARGED_ONLY_ON_A_BARS_THAT_EXIST_READING`. |
| **"`MEAN_OVERLAP_FRACTION_UNIT_NOT_REGISTERED` is discharged — the unit is ruled"** | The ruling fixes the **binding**, not the **identity**. Renamed and carried as `MEAN_OVERLAP_UNIT_TIED_TO_AN_UNREGISTERED_HORIZON_CLOCK`, and moved out of the header's Historical list. |
| **MO-3 labelled "Derived"** | It is derived **only given Ruling ω-1**, which is itself a choice — so it would **not** survive a disagreement about the ruling, which is precisely what the table exists to show. Re-marked. |
| **The amendment table assigned three favourable classifications** | ω-6 was classified a *tightening* while the row's own words said it adds content — and the content it adds is the **feasibility-favourable** value (a one-event record then contributes `1.000`, the largest it can take). Moved to **NOT SETTLED**. ω-1's and ω-4's prohibition limbs meet the same NOT-SETTLED criterion and are now sent there. "Five candidate readings" corrected to **six**. And "no favourable classification is asserted" was scoped to one row while three others carried them; it now sits under the table. |
| **Ruling ω-2/ω-4 left the interval set to two undefined adjectives** | "Applicable" and "eligible" — and **exclusion is weighting**, so an eligibility filter reproduces the whole `[1.00, 23.04]` lever ω-4 exists to close. Replaced with "every adjacent interval, exhaustively, all `n − 1` of them, none excluded on any ground", and the clause now reaches exclusion. "Eligible" also collided with prereg §6's defined term, which `_require_count_quantity` refuses by name. |
| **The `n − 1` denominator was attributed to ω-4 alone** | It follows from **ω-2's index set** (intervals, not events) *together with* ω-4. And that index choice **disposes of MO-5's last-event limb**, which §8.4.12 had expressly warned must not be settled by settling another limb. Both now recorded as rows. |
| **"`c` is the last major freedom in the effective-N arithmetic"** | Reinstates the "last unpinned term" claim §0.3 already withdrew, in the other variable. The clock residual and `OVERLAP_PER_RECORD_PROVENANCE_UNBOUND` are both freedoms outside `c`. Corrected at three sites to the accurate narrower claim: `c` carries the whole **cross-pair deflator**, and is the last unruled **decision packet**. |
| **§8.5.4's entry-set claim was arithmetically false** | 190 unordered and 380 ordered off-diagonal entries give the **same** mean, since `ρ_ij = ρ_ji`; the lead confirmed numerically. Only the diagonal changes it, by the fixed map `0.95·m + 0.05`. |
| **§8.5.1's "negatives are refused" row silently disposed of an NR-L2 limb** | "A genuinely negative mean must be entered as its absolute value" is a **disposition** no committed source carries, and it contradicted §8.5.4's own correct statement that this is an *input* constraint. Withdrawn; the conservatism is re-sourced to the spec's "mean **absolute**" and made conditional on equal weights and equal variances, neither registered. |
| **§8.5.1 misattributed a quotation** | "Cross-pair dependence — fixed PAIRS_20 … correlation discount in effective-N" is prereg **§12's risk register, row 2**, not §16's Ruling 2 (the dataset-spans ruling; §16's effective-N ruling is Ruling 11) — and calling it a "frozen row" promoted a risk-register entry into the frozen-rulings instrument. |
| **"The only `.corr`/`corrcoef` calls are in `compare_multipair_*`"** | False: further sites in `stage22_0a`, `stage25_0e` (a *cross-pair* rolling correlation) and `scipy.stats` calls across the `stage26_0*` family. All are C-8-fenced stage/compare lineage, so the **conclusion holds**; the enumeration did not. |
| **§8.5.11 called NR-L6 independent of NR-L5** | It is not: the idle-day convention **manufactures** which undefined cases arise — zeros make the zero-variance and all-zero cases, listwise exclusion makes "no common dates", pairwise exclusion makes "insufficient overlapping observations". NR-L6 must be ruled after or with NR-L5. |
| **§8.5.10 left NR-L5 unadvised without saying so** | And the `ω` side's empty-record cases needed **two** dedicated limbs precisely because a value reached by absence runs permissive — so on the `c` side, silence about idle days **is** the zeros default. The silence is now declared, with the direction pointed at §8.5.7 and no convention invented. |
| **§8.5.10 limb 4 halts the family on a normal outcome** | A pair that fires nothing is a **normal outcome** (§8.3.0) and produces exactly NR-L6's zero-variance case, so a flatly fail-closed limb 4 is the shape `ZERO_EVENT_OMEGA_MUST_NOT_HALT_A_NORMAL_OUTCOME` records. Dropping is anti-conservative; halting is unworkable. The packet now says it **has no third answer** rather than leaving the ruling to discover the collision. |
| **§13 still called §8.4 "the next decision"**, twice | Corrected, along with the Exact-`D` ordering row. |
| Smaller corrections | The header still asserted the two overlap formulations "**agree** at the ceiling", the claim §8.4.3 withdrew — corrected. `NOTHING_PREVENTS_OVERLAP_BEING_MEASURED_…` **is** discharged by ω-9, which mandates the measurement rather than permitting it; `MEAN_OVERLAP_PAIR_SET_MUST_NOT_SHRINK` is only **partly** discharged (its provenance half survives) and `OMEGA_METHOD_MUST_NOT_BE_SELECTED_…` is **not** discharged (ω-9 supplies the freeze A-ω-5 calls necessary and *not* sufficient) — all three were mis-filed. `HORIZON_WALL_CLOCK_EXTENT_NOT_REGISTERED` appeared twice in one list. §8.5 was missing from the document-wide diagnostic scope and lacked a blank line before its heading. §8.5.2's multipliers dropped their `c = 0.3` baseline and attached "more than" to a figure it is false of (`×1.74 < ×1.81`). A role-separation row was missing from the derived/chosen table, and §8.4.15's handoff listed six of NR-L's seven objects. §8.5.7's idle-day direction is **conditional**, not unconditional. §8.5.5's bare "may not be substituted" is re-sourced as a reading. §8.5.9's "the whole of it is available" is re-scoped to extent, not access. |

**The finding that most changes the ruling record.** Ruling ω-1 was written as closing
the clock route and turns out to **narrow** it: the three bar readings of `H` survive,
they are **totally ordered in `ω`**, and — the point neither the ruling nor the packet
had recorded — **the incentive on the survivor is one-directional**, because only the
*bars-that-exist*, *complete-buckets* and *elapsed-excluding-closures* readings import
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`. The `ω`-minimising
continuous-grid reading is therefore also the only one instantiable without an unbuilt
approval. That asymmetry is now recorded so a later choice cannot present it as a
convenience.

**And one naming point the roles were right to press.** The ruling's own token names a
"registered M15 prediction clock". No committed source names one — and §8.4.14
withdrew the near-identical phrase from *this packet's* recommendation one round
earlier as a coinage the packet may not introduce. The token is recorded **verbatim**,
because it is the ruling's, and annotated: a ruling may coin where the packet may not,
the reference is ostensive, and the authority it points at is **partly absent**
(`M15_PREDICTION_HORIZON_CLOCK_IS_COINED_BY_THIS_RULING_NOT_REGISTERED`).

**Attacks the adversarial role made that did not survive**, recorded because their
failure is evidence: no route manufactures one-event pairs (the counts are set by
frozen eligibility, the frozen EV gate and the cost hurdle, and Ruling ω-10 bars using
the measurement to redirect the design); the `≤ ~4.5%`-of-the-floor bound is right and
if anything loose in the conservative direction; a pair with many non-overlapping
events earning `ω = 0` is a **measurement** the spec endorses by name, not a defect;
role-span boundaries are not a *signed* lever; the 21:55–22:15 rollover exclusion does
**not** separate the clock candidates, since it removes event-eligibility and not
buckets; nothing in §8.5 is silently ruled; neither NR-K nor the ω ruling is cited into
NR-L as authority; and nothing authorises or softens data access.

---

### 12.10 Eleventh review round — the ω clock substrate, and the NR-L packet

**Review coverage is incomplete, and that is recorded before the findings.** Three
doc-only roles were dispatched — effective-N/correlation semantics, time/calendar
clock semantics, and an adversarial subset/undefined-correlation brief. **Only the
adversarial role returned.** The other two **terminated early on an API session
limit** without producing findings. This round therefore rests on **one** independent
role plus the lead's own source verification, where the three preceding rounds rested
on three or four. **`ROUND_11_REVIEW_COVERAGE_PARTIAL_TWO_OF_THREE_ROLES_TERMINATED`.**

Two consequences are stated rather than glossed. The **statistical** and
**calendar-semantics** perspectives were **not** independently exercised against
Ruling ω-11 — the very ruling this round records — so the conservative-direction
arithmetic, the constancy discharge and the market-hours-invention check rest on the
lead's verification and the adversarial role's coverage of them, not on a role
dedicated to each. And per policy §13 this is a **substitute procedure**, not a
substitute for the coverage: the missing perspectives should be run before this
section is treated as reviewed.

**The lead found three defects itself, before the role returned**, and pushed them at
`3a4516f`: "skipping **closed** slots" appeared three times and presupposes a closure
schedule this repository does not author; the conservative-direction claim needed
"smaller **or equal**" and rests on a subset argument rather than on closures; and the
property that makes this substrate different in kind — it is **calendar-derived, not
data-derived**, so an outage surfaces as a coverage deficit rather than moving the
clock — was missing.

| Defect | Outcome |
| --- | --- |
| **"The semantics are complete"** | False against two tokens in the same section: `ROLE_SPAN_HORIZON_TRUNCATION_RULE_NOT_REGISTERED` and `ROLLOVER_AND_HOLIDAY_SLOT_ELIGIBILITY_RELATIVE_TO_THE_OMEGA_CLOCK_NOT_SETTLED` — and the second is **a question about what `ω` means**, not about when an artifact exists, so it is not cured by the calendar's approval. Restated as *near*-complete, with `MEAN_OVERLAP_SEMANTICS_RULED_EXCEPT_ROLE_SPAN_AND_ROLLOVER_PENDING_CALENDAR_INSTANTIATION` operative; the ruling's own token is **retained beside it, qualified rather than dropped**. |
| **"Latitude removed toward the conservative end"** | **False for one of the four foreclosed substrates.** Under MO-1(b) the **event-index** gap is identically 1, so that substrate gives `ω = 23/24` and `rho_h = 23.04` — the **top** of §8.4.5's band, and the most `N_eff`-hostile candidate on the table. Foreclosing it removes the *conservative endpoint*. The lead reproduced the arithmetic. Split into two rows, and the "picks the end that makes the floors harder" phrasing corrected at three sites to "more conservative **than the continuous grid**". |
| **The §8.2.5 alibi structure applies to ω-11 and was not recorded** | §8.2.5 rejected an eligible-day `D` as "a post-freeze duration lever with a **perfect alibi**", because T-6 schedules the eligibility calendar for approval *after* the freeze while the frozen number never changes. Ruling ω-9 freezes `ω`'s **method**, not the calendar's content, so the same structure applies. **`OMEGA_SUBSTRATE_CONTENT_MAY_MOVE_AFTER_THE_METHOD_FREEZE`.** |
| **"The approved calendar authority" names two artifacts, not one** | §8.2.2 records both: the **D-6 closure/market calendar**, approved *before* the continuation; and **Ruling 4's holiday / thin-liquidity event-eligibility calendar**, which "gate 4's **T-6 re-pointed to 'implementation, approved before gate 7'** — i.e. **after** the `D` freeze". Ruling ω-11 cites the first and leaves the second's relation open, so **one branch is a post-freeze artifact**. The lead verified both at source. **`OMEGA_SUBSTRATE_CALENDAR_IDENTITY_NOT_SETTLED`** — the ruling should say which governs. |
| **`CALENDAR_CONTENT_DETERMINES_OMEGA_SUBSTRATE` was under-stated** | The lever did not disappear; it **moved to a place with strictly weaker protection**. `OMEGA_CLOCK_SUBSTRATE_MUST_NOT_BE_CHOSEN_TO_MINIMISE_RHO_H` binds the *choice of substrate*; **nothing binds the calendar's content**, no source requires calendar authorship to be blind to its `ω` effect, and D-6's approval is an approval **for coverage** — an approver is nowhere told the same artifact now sets `N_eff`. **`NO_OUTCOME_BLINDNESS_REQUIREMENT_BINDS_CALENDAR_CONTENT`** · **`OMEGA_DEPENDENCE_NOT_DISCLOSED_AT_CALENDAR_APPROVAL`**. |
| **The discharge was a relocation, not a retirement** | `ROLLOVER_AND_HOLIDAY_..._NOT_SETTLED` carries the same `0`-to-near-`1` width on a single contribution that `HORIZON_WALL_CLOCK_EXTENT_NOT_REGISTERED` carried — now **inside** the ruled substrate — and the rollover window is **daily**, so it reaches gaps no closure reaches. §8.5's opening still cited the discharged token for that width; corrected. |
| **§8.5.8 option (c) was a loophole with a compliance step** | "Exclude the entry and record the exclusion" is `KEEP_P_20_BUT_COMPUTE_C_ON_A_FAVOURABLE_SUBSET` at the **entry** level. Reporting cures the *visibility* half of the packet's own two-part objection and **not the direction half**; it has **no `ω`-side precedent** (ω-5/ω-6 both *retain* the pair); and the record it depends on **does not exist** — R-9 requires the correlation *used*, and §8.5.9 records that no artifact carries `c`. Reframed as flagged-not-endorsed. |
| **§8.5.10 limb 8 recommended what the same limb refutes** | It headlined "fail closed" and then demonstrated that fail-closed halts the family on a normal outcome. A limb that refutes itself is a **referral**, not a recommendation. Reframed. |
| **Stale numbering from this head's own renumbering** | The recommendation list went 7 → 11 limbs and NR-L went 7 → 8 questions. "limb 4" × 2 → limb 8; "three of the seven" → **four of the eight** (NR-L6 joins the unadvised set); and **"limb 3's span and limb 6 are committed"** was materially wrong under the new list — limb 3 is now the PnL/day-attribution limb the packet records as *not* committed. Corrected to limbs **6 and 10**. |
| **§13 said "`P` and `ω` fully ruled"** | `ω` is not fully ruled, and **`ω` does not enter `rho_x` at all** — `rho_x = 1 + 19c` follows from `P = 20` alone. §8.5's own opening had the correct form; §13 was the outlier, and the error was introduced by this head. |
| Smaller corrections | `MEAN_OVERLAP_CLOCK_DEPENDS_ON_APPROVED_CALENDAR_AUTHORITY` enumerated three candidate readings, **none of which is the substrate the ruling chose** — the second occurrence of that same defect in this token. The ruled substrate was a **seventh** candidate absent from §8.4.4's table; added. "discharges it outright … leaving only the role-span limb" was self-cancelling. NR-L8's justification over-stated NR-L5 as "under-determined" when the two **overlap**, and the NR-L8 ↔ NR-L5 dependency runs **both ways**, so the ordering is a sequencing convention. `SAME_CLOCK_RULE_DOES_NOT_YET_IDENTIFY_THE_CLOCK_SUBSTRATE` is a retro-label coined here, not inherited. |

**The addition the round produced, and it closes a standing asymmetry.** §8.4.11 gives
the `ω` side eight named adversarial properties, split into two kinds and sized; the
`c` side had four tokens scattered across four subsections, **ranked and sized none**.
**§8.5.2a now mirrors it**: the routes are split into those that **move the reported
`c`** and those that leave the reported `c` correct while changing **what it is a
correlation of** — the latter invisible to any check on the reported value, since `c`
enters the record only as the derived `rho_x` and R-9 requires the correlation *used*.
The two largest are **NR-L2's absolute-value placement**, whose favourable direction is
knowable **before any data** (the A-ω-5 property, in the other variable), and the
**entry-set shrinkage** route at up to the full `×20` bound. There is **no
`C_STATISTIC_MUST_NOT_BE_SELECTED_TO_MINIMISE_RHO_X`** token to match the `ω` side's,
and this packet **records that gap rather than filling it**.

**Attacks the role made that did not survive**, recorded because their failure is
evidence: no case was found where the eligible-slot substrate gives a *lower* `ω` than
the continuous grid, including clipped and endpoint cases — the subset argument holds;
"bars that exist would be more conservative" fails on substance, because it would make
`ω` a function of data presence and re-enter the inference D-6 forbids; the data-outage
residual does not survive, since eligibility is calendar-derived; the constancy
discharge holds apart from the role-span carve-out; nothing in §8.4.0 or §8.5
authorises data access, softens a prohibition or claims empirical readiness; no
market-hours semantics are authored; nothing in §8.5 is silently ruled; NR-K and the ω
ruling are not cited into NR-L as authority; and Q10(i) is resolved nowhere, in either
direction.

---

### 12.11 Twelfth review round — the four calendar residuals

Recorded **after** the roles returned. Three doc-only roles — calendar/temporal
authority, prereg/governance ordering, and an adversarial post-freeze-mutability brief
— **all three returned**, so coverage is complete for this round. Round 11's partial
coverage is **not** relabelled by that:
`ROUND_11_REVIEW_COVERAGE_PARTIAL_TWO_OF_THREE_ROLES_TERMINATED` stands, and §8.4.0 now
records that ω-12 **inherits** that gap rather than curing it.

**The lead found one defect itself, before any role returned**, and pushed it at
`e5e6eb5`: the concession that the surviving event-set residual was "bounded
conservative by Ruling 4's widen-only clause". Removing an event **merges gaps**, which
lowers `ω` and can *raise* `N_eff` — verified on the ruled arithmetic.

**One inter-role disagreement, resolved on the evidence rather than by vote.** Two roles
found that §8.2.0 states a **conflicting** calendar placement; the third concluded "what
existed was silence, which is accurate". The lead read §8.2.0 directly: "it must precede
the continuation, and **the target epoch it declares is determined by the declared
window — so it sits between (3) and (4)**." That is a placement, and it is after the
declaration. **The conflict is real**, and it is now surfaced rather than smoothed.

| Defect | Outcome |
| --- | --- |
| **Limb (b) authored a market-hours fact** | "A rollover slot is a slot the market is open in", and "a rollover slot is **in** `ω`'s sequence" — found independently by two roles. **No committed source states the market's state at 21:55–22:15 UTC**, and Ruling Q10(ii) says of the *same* artifact that it "authors no weekend rule, no holiday rule, no closure rule and no DST rule". Both withdrawn; the consequence is now **conditional on A's content**. |
| **…and it decided at the feasibility-favourable end** | Keeping such slots **in** lengthens `g`, lowering `ω` and `rho_h` and **raising `N_eff`** — and the rollover window is **daily**. `ROLLOVER_AND_HOLIDAY_SLOT_ELIGIBILITY_RELATIVE_TO_THE_OMEGA_CLOCK_NOT_SETTLED` is **restored to the open list**: its *ownership* is ruled, its *outcome* is A's content. The status token keeps `AND_ROLLOVER`. |
| **"No committed source states a conflicting order"** | False. §8.2.0 places the calendar approval **after** the declaration, and its ground — the target epoch "is determined by the declared window" — makes limb (d) **circular**, since `target_epoch` sits inside the `content_digest`. Surfaced as `OMEGA_CALENDAR_FREEZE_ORDER_CONFLICTS_WITH_SECTION_8_2_0_TARGET_EPOCH_DEPENDENCY`; **not resolved here**. |
| **The amendment table carried three favourable rows** | (b) as plain "ambiguity resolution" while it decided the favourable arm; (c)+(d) as "Tightening" on the ground that the freeze was "unordered" — it was not, and both add obligations no committed source carries. (c) split, (d) moved to **NOT SETTLED**, and the "no favourable classification" sentence moved out of one row to cover the table — the same defect §12.9 fixed once already. |
| **Q10-B does not presuppose a frozen calendar** | `D` is an elapsed UTC span and expressly "**not** an eligible-day count"; Q10-B declares **literal instants**, and its embargo paragraph *contemplates* the approval landing later. The dependency (d) relies on is §8.1.0's sizing basis. Token renamed `CALENDAR_FREEZE_ORDER_IS_ADDED_HERE_NOT_IMPLIED_BY_Q10_B`. |
| **Limb (e) bound the wrong verb, trigger and artifact** | It said "**modified**" — but neither artifact exists, so every instance is a first **authoring**; it said "**realised**" — but the sign is knowable **with no data at all**; and it was scoped to **A**, while **B** is the artifact that can still move. All three widened. |
| **Ruling 4's widen-only clause does not bind B** | "Widen **it**" attaches to *the rollover exclusion window*; the holiday / thin-liquidity calendar sentence carries **no direction clause**. So B is bounded in **neither** direction. `NO_DIRECTION_BOUND_BINDS_THE_LATER_EVENT_ELIGIBILITY_CALENDAR` — a second error in the bullet the lead had already corrected once. |
| **Case D's ground was inverted** | "Identity is the `content_digest`, not the name" — but `calendar_content_digest()` covers `committed_artifact`, which **is** a name ("looks like a path … a name a human reviewer resolves"). The name is **inside** the identity. |
| **Case A's ground was false** | "Nothing is observed yet, so nothing is selected on its effect" — the sign is knowable with no data. Re-grounded and scoped to **before the declaration is pushed**, with the post-declaration route referred. |
| **"Exactly one artifact" was unsatisfiable** | Committed code refuses reuse across epochs and `target_epoch` is digested, so Family A's design span and forward epoch necessarily carry **different** artifacts. Scoped to one **per epoch**, and the declaration noted as **per pair**. |
| **"May block formal continuation" understated an unconditional bar** | The playbook lists calendar approval as "**Not discharged by an accepted source audit**", followed by "**Only then** may a separately-authorised gate-3a continuation read/derive design-span data". Restated as **barred**. |
| **Three residuals the ruling did not carry** | **FR-8's second limb** — the interface's own words: refusing a callable "does not close FR-8's second limb … **and an audit did exactly that**" — so a materialised set may still track the derivation, which would make `ω` a function of the data it deflates. **No locus records the frozen version's identity**: `content_digest` is self-consistent for *any* artifact and the approval marker is artifact-declared, so (c), (d), (f) and case D have nothing to check against. And **membership is per pair** — twenty independent levers on `rho_h`, which the pair-label prohibition does not reach. |
| Smaller corrections | The header and §8.4 status tokens contradicted each other; "the Option-B structure" collided with the Option B that Ruling ω-3 **refuses by name**; the session partition was called "within open hours" when `_check_session_partition()` requires it to tile the **whole UTC day**; the FR-8 "so D-5.8 admits only the materialised route" inverted the contract's direction; the six-step order omitted §8.2.8's **step 7** and is now marked an *insertion*, not a replacement; "nothing upstream of NR-L remains open on the overlap side" was false; and a fifth "bounded conservative" site survived the previous correction. |

**Attacks that did not survive the sources**, recorded because their failure is
evidence: the **A/B split itself holds** — no committed text gives B a membership role
or A an event-eligibility role, and two roles reached that independently; no reading was
found on which B becomes `ω`'s membership authority; the non-candidates are correctly
excluded; **"no schema is invented" is exactly true**; D-5.8 compatibility holds; and
nothing in ω-12 generates a calendar, authorises data access or claims empirical
readiness.

### 12.12 Thirteenth review round — the reclassification

**Three separated doc-only roles, all three completed**, each given the source, the
diff and the contract and **none given another role's conclusions**: **contract and
ordering consistency** (does ω-13(a)'s order hold against Q10-B, §8.2.0, §8.1.0 and
§8.2.8, and does anything in the document still carry the superseded order?),
**adversarial refutation** (argue the ruling is wrong, and hunt the bypass routes the
prohibitions miss), and **gate-versus-production classification** (is any deferral
actually a live freedom, and is any blocker actually only checkability?). Round 11's
partial coverage is **not** relabelled by that: it stands where it stands, and this
round's completeness is this round's only.

**No role could reach an artifact.** Neither Calendar A nor Calendar B exists, so every
finding is about the *text of the contract*, and none rests on a measurement.

| Defect | Outcome |
| --- | --- |
| **The eligibility freeze could be satisfied by delegation** | Limb (b) required an eligibility rule's "**operative semantics**" to be frozen pre-data, and the post-hoc prohibition carved out rules "already frozen before data observation". A rule of the form *"ineligible if the slot falls in a low-liquidity holiday session **as listed in the calendar approved before gate 7**"* has complete operative semantics, frozen pre-data — and its content arrives after the freeze and moves the event set. It satisfied the limb **and** the carve-out. **`FAMILY_A_ELIGIBILITY_SEMANTICS_MAY_NOT_DELEGATE_TO_A_POST_FREEZE_ARTIFACT`**, and the freeze moment is now named: the sequence is frozen when the last semantic **and its content** are. A hole in the blocker the ruling had just closed. |
| **The governing test was narrower than §5, and its motivation was false** | ω-13's single question added a temporal qualifier §5's first limb does not carry, and **omitted §5's second limb entirely** — the limb that admits R-8 and that "may never be cited to strike a §3 boundary". Restated as §5's first limb, with the second governing unchanged, an unclear case defaulting to **blocker**, and A-ω-5's "a pre-data freeze does not by itself protect MO-2" governing alongside. Separately, the sentence *"the previous rounds had begun promoting every discovered defect into a gate blocker"* is **withdrawn as false**: at the base head the word "blocker" occurred **twice** in the whole document, one of them ω-12 declining to call an item one. The lead verified both counts at source. |
| **The boundary rule named no judge, no standard and no default** | `NEW_OMEGA_FINDINGS_DO_NOT_AUTOMATICALLY_BECOME_RESEARCH_BLOCKERS` said what a finding must show and nothing about who decides — the shape §8.4.0 had already corrected once ("softens a committed bar into a judgement call with no named judge"). Now bound four ways: classification is a **human + ChatGPT** call and never the implementing session's; "material" means **any** capacity to move `ω`, `N_eff`, the event sequence or experiment selection; "available" means decision-bearing **observation** by any party **including the calendar author**; and an unclear case is a **blocker**. |
| **The deferral's "only if" was self-cancelling** | Both branches of the qualification deferred, so the condition carried no consequence. The negative branch now **bites**: where the implementation cannot select one immutable instance *and record which one it used*, the deferral **lapses** and residual 5 is a `MINIMUM_RESEARCH_GATE_BLOCKER`. The prerequisite was also on the wrong half — selectability without recording leaves the freeze unfalsifiable — so it is renamed `ONE_SELECTABLE_IMMUTABLE_CALENDAR_INSTANCE_WITH_RECORDED_IDENTITY_IS_AN_EXECUTION_PREREQUISITE`. |
| **Residual 5's deferral swept in a half §5 puts IN** | §5's OUT table reads "Provenance binding to committed authority — **OUT** for exploratory; **IN** as R-6's lightweight record". A result computed against an unidentified calendar is not reproducible in R-6's sense. The research-side half is restored as an obligation to record `authority_version`, `content_digest` and `target_epoch` with any output that consumes a calendar; only the **production locus** is deferred. |
| **Residual 6 was presented as closed, and it is not** | Three corrections. **(a) does not narrow the outcome** — it hands the calendar author the declared window, so the author knows the rollover lever's **magnitude** as well as its sign, where ω-12's rejected arm kept them window-blind; that is a **cost** of adopting §8.2.0's placement. The closure is **by prohibition, not structural**. And it **depends on residual 5's deferral holding**, since ω-12(e) has no locus to be checked against — `RESIDUAL_6_OUTCOME_CLASSIFICATION_DEPENDS_ON_RESIDUAL_5_DEFERRAL_HOLDING`. |
| **(b) stated an obligation with no artifact, no owner and nothing tracking it** | The required pre-data Family A eligibility contract does not exist, nothing requires anyone to produce one, and Calendar B's approval remains "before gate 7" — after the freeze. Registered rather than assumed away: `NO_PRE_DATA_FAMILY_A_EVENT_ELIGIBILITY_CONTRACT_EXISTS` · `PRE_DATA_FAMILY_A_EVENT_ELIGIBILITY_CONTRACT_REQUIRED_BEFORE_CONTINUATION`. Also, the remedy's antecedent is **settled, not conditional** — T-6 does place B's approval after the freeze — and the contract is a **third** object ω-12(e) must reach. |
| **(a) withdraws a recorded ruling, and the classification said otherwise** | It read "it withdraws **this packet's own** ω-12(d)". §8.4.0's preamble says ω-12 is "a ruling received from human + ChatGPT and recorded here as **authority**". Superseding it is itself a ruling only human + ChatGPT may take, and it is now recorded as one. Its *content* remains the least-amending option, since ω-12(d) was already **NOT SETTLED**. |
| **The "no favourable classification" sentence was missing for the fourth time** | Three of six rows classify downward and the section carried no such sentence — the defect §12.9 and §12.11 each fixed once. Added, with the defeating ground for each downward classification stated beside it. |
| **The role-span limb was demoted without being classified** | The header called `ROLE_SPAN_HORIZON_TRUNCATION_RULE_NOT_REGISTERED` "**not** a gate blocker unless shown to move a result", although ω-13 does not classify it — it is not among the six — and §8.4.0 says the ruling "does **not** fill it". The dilemma is now recorded instead: either the truncation rule belongs to the frozen method and must be registered before `ω` is measured, or it does not and the arm is selectable **at computation time**. **`ROLE_SPAN_TRUNCATION_ARM_SELECTION_POINT_NOT_BOUND`.** |
| **A token disappeared from the only list a reader scans** | `ROLLOVER_AND_HOLIDAY_SLOT_ELIGIBILITY_RELATIVE_TO_THE_OMEGA_CLOCK_NOT_SETTLED` was dropped from the header open list while six other sites still call it open and §12.11 still says it "is **restored to the open list**". Restored, glossed with its ω-13 classification. A visibility regression on the very item the round was asked about. |
| **(a) was said to foreclose §8.1.6's limb (i); it does not** | Limb (i) admits "rollover and holiday exclusions" as **availability metadata**, not as the artifact. (a) forecloses reliance on the artifact's *content* and bars **reselection**; it does not bar an **initial** declaration informed by the exclusion shape, which Q10-B's forbidden anchors and `DURATION_SELECTION_MUST_BE_OUTCOME_BLIND` restrain instead. The overstatement is withdrawn and the mirror image named. |
| **Determinism is not a safeguard, and (c) cannot be checked** | Any fixed per-pair table is deterministic, so twenty hand-written sets would satisfy the word while constraining nothing; the operative bar is the anti-optimisation clause. And a derived set and a hand-tuned set are **byte-identical** in a materialised `expected_m15_slots`, so **(c) inherits FR-8's second limb**. The prohibition is also made agent-neutral: it binds "the calendar author no less than the researcher, and they may be the same person". |
| **Residual 4's ground did not reach the case** | It rested on ω-12(e) and (a); (e)'s triggers do not reach a set derived from **data presence** rather than an outcome, and (a) orders the *researcher's* observation, not the calendar author's access. Re-grounded on D-6's "never inferred from the raw source" and `calendar_authority.py`'s refusal to reverse-infer closure from missing data — the same property ω-11 relies on. The deferral is also matched to PR #449's committed `SECOND_LIMB_DEFERRED_TO_GATE4_BYTE_READER` rather than created here. |
| Smaller corrections | ω-12(c)'s ordering half and two header tokens still carried the superseded order, and §13 stated it outright; (a) is scoped to the **forward epoch**, since the playbook's prerequisite 5 requires a design-epoch calendar *before* the design-span continuation; ω-12's case A is now **structurally unreachable**, promoting `POST_DECLARATION_PRE_OBSERVATION_CALENDAR_DEFECT_ROUTE_NOT_SETTLED` to the only route; the "new pre-registration" escape is marked **unruled** rather than available; §8.2.8's insertion carried three disagreeing numberings ("5a", "within step 6", attached to ordering item 3) and now sits at **step 6a**; the six are marked **selected, not enumerated**; the composed Q10-B order now carries steps 7 and 8; the FR-8 read-only sentence no longer reads as clearance; "**CLOSED** for Minimum Research Gate purposes" is restated as **RULED, instantiation pending**; §8.4's status paragraph contradicted itself within one paragraph; and a duplicate header token was removed. |

**Findings the lead did not adopt.** One role proposed replacing
`DEFERRED_PRODUCTION_CHECKABILITY` with the playbook's existing `MAY_DEFER` vocabulary;
that is a contract-vocabulary choice for the ruler, and PR #444 already records twenty
terms "used in incompatible senses across committed documents", so coining is not made
worse by leaving this one where the ruling put it — **recorded as an open question, not
resolved**. One role could not determine from the document alone whether ω-13 was
*received* as a ruling or *recorded as a proposal*; the answer is that it is recorded as
received, on the same footing as ω-1…ω-12, and its standing is the approver's to
confirm.

**Attacks that did not survive the sources**, recorded because their failure is
evidence: residuals **1, 2 and 3 are correctly blockers**, each re-derived independently
before the ruling's reasons were read; **(a)'s order does dissolve the circularity** and
matches §8.2.0's "between (3) and (4)" and Q10-B's four-step Sequence; **(c) neither
requires the twenty sets to be identical nor permits tuning**; **nothing authors a
market-hours fact or generates a calendar** — the market-hours paragraph is a pure
negative list, which is precisely the defect §12.11 found in ω-12(b) and which is not
repeated; **no `T_v`, `T_h` or `D` value is chosen**; the `NON_NORMATIVE_DIAGNOSTIC_ONLY`
block is untouched and **no new number is minted anywhere in the diff**; and NR-K,
Q10-A/(ii)/B, Q10(i)/(iii), Q11 + §0, Q1/Q3/Q8/Q9, FR-19, the Zero-Data verdict, NR-L's
status and round 11's partial-coverage record are all intact and unrelabelled.

### 12.13 Fourteenth review round — the bundled Q10(i) + NR-L ruling

**Three separated doc-only roles, all three completed**, each given the source, the
diff and the contract and **none given another role's conclusions**: **correlation and
statistical semantics** · **daily-PnL construction and time attribution** ·
**adversarial `N_eff` inflation and subset selection**. Round 11's partial-coverage
record is **not** relabelled by that.

**The lead ran its own verification pass first, before any role returned**, and the
five findings it produced are recorded in the round below as the lead's, not as a
role's. Two of them were independently reproduced by roles afterwards; one — the
correct c-7 mechanism — a role derived by simulation and confirmed the lead's worked
example exactly.

**The blocker, found independently by two roles.**

| Defect | Outcome |
| --- | --- |
| **c-1…c-9 fix how `c` is computed and not which run produces the series** | The family carries three registered decision thresholds and three registered `ev_min` points; each combination gives a different trade set, a different daily series and a different `c`. The route obeys every ruled word: run K design-span variants, read each `c`, declare the lowest — c-9's bar reads "after any **downstream** observation", and its own enumeration of what may not be reselected **omits the producer**. §4's **R-10** forbids exactly this, names `mean_abs_pairwise_corr` as "**the sharpest case**", and hands the remedy to "the design audit and **gate 3a, which own it**" — and §8.5.0 *is* that gate-3a decision. **`NR_L_GENERATING_CONFIGURATION_NOT_REGISTERED`**, classified a **`MINIMUM_RESEARCH_GATE_BLOCKER`** by the ruling's own test, with candidate dispositions enumerated and **none chosen**: a producer rule is a human + ChatGPT choice. The closure sentence "**No** NR-L Minimum Research Gate blocker remains" is **withdrawn as false** — it was falsified by the test it invoked. |

**Everything else, by lens.**

| Defect | Outcome |
| --- | --- |
| **The reach table omitted the whole validation side** | `MetricTrade.day` also drives the **validation** daily Sharpe that `select_threshold` reads (`body.py:228`, `:535`) and the validation **turnover** figure inside prereg §9.V's kill gate, whose failure means "family A closed, **no holdout consumed**". So Q10-i can change **which operating point reaches the holdout** and **whether the holdout is reached** — `MEASUREMENT_MAY_DETERMINE_THE_VERDICT_BUT_MUST_NOT_REDIRECT_THE_EXPERIMENT` is engaged, and `Q10_I_MUST_NOT_BE_RESELECTED_AFTER_OBSERVING_ANY_METRIC_IT_MOVES` now binds validation observations too. Five quantities became **seven**. |
| **"24 M15 bars — six hours — so no trade can straddle two"** | The wall-clock conversion this document refuses elsewhere. `HORIZON_WALL_CLOCK_EXTENT_NOT_REGISTERED` survives outside `ω`, and §8.4.9's own derivation concludes from prereg §4's "no synthetic bars across market close" that a horizon **need not be contiguous**. Withdrawn; the bound is now stated **in bars only**. |
| **"No new machinery … a one-marker change at two call sites"** | False at the second site. `_trades_with_days` reads `day_by_index[pair][…]`, a dict populated **only** at label-eligible validation and holdout decision bars, so an exit index in the purge or embargo gap raises `KeyError`. Populating it for exit indices is new machinery on a protected path. |
| **c-6 authored a market-hours fact** | "89 Saturday/Sunday dates … **on which the FX market is closed and every pair is necessarily idle**" — stated in the very paragraph declining to author one, and the **fourth** time this document has done it. Withdrawn; whether those dates carry a registered M15 slot is a calendar-authority question this ruling does not answer. |
| **The right edge had no ruled disposition** | Under exit attribution a DESIGN-span trade can be attributed to `DEAD_START = 2026-03-01`, outside the index and inside the fenced dead window — a hole entry attribution did not have. **Two roles proposed opposite dispositions**, one fail-closed and one exclusion; the lead resolved it **on the evidence, not by vote**: fail-closed would halt `c` on a near-certain normal outcome, the defect §8.5.10 limb 8 already identified, so membership is decided by the attributed date and the index is never extended. |
| **c-4's cost layer was labelled derived** | The dependence note either binds `c` to the components of the Sharpe's sum — in which case **c-6 contradicts it**, and says so in its own token — or it does not, in which case c-4 is ruled. It cannot be both. Downgraded to **ruled on a reading**, with the departure c-6 makes from the same note recorded. |
| **c-1/c-2 were labelled derived without the reading they rest on** | The equicorrelated identity appears in **no** committed source, and c-3 knowingly departs from it. Restated as **derived-under-a-stated-reading**. The algebra itself was independently re-checked and holds: at equal `σ`, `Var(Σx) = σ²P[1 + (P−1)ρ̄]` with `ρ̄` the equal-weight mean over the 190 unordered off-diagonal Pearson entries; the diagonal is the `P` term. |
| **The false-assumption citation was a non-sequitur** | `C_EQUAL_WEIGHTING_IS_EXACT_ONLY_UNDER_EQUAL_PER_PAIR_VARIANCES` was grounded on §0.6's "88 of 190 entries share a leg" — a statement about the correlation matrix's **block structure**, which does not bear on variance equality: the identity is exact for **any** correlation matrix at equal `σ`. Withdrawn; the correct ground is per-pair daily-PnL **volatility** dispersion, with the anti-conservative exposure quantified. |
| **The anti-conservative inventory was short, and "the one limb with a knowable arm" contradicted c-7** | c-6's common-idle frame is a **third** limb, and its "a later trading-day index would be a **tightening**" is **withdrawn**: by c-7's own mechanism the direction depends on the sign of the induced common-mode term. c-3's arm is knowable **unconditionally**; c-7's only **conditionally**. |
| **The R-6 carve-out could not discriminate** | It asked for the date-index **bounds** — and every alignment c-6 forbids reports the *same* bounds. It now requires the index's membership rule and **cardinality (310)**, the **190**-entry count and the per-pair non-idle counts. The deferral is also recorded as a **contested** classification, since §8.4.13's default is blocker and §5 puts R-9 and R-10 IN. |
| **c-8's escape hatch read as available, and its routing as a quotation** | The new-pre-registration route is qualified as ω-12 qualifies it — the *only* route, not an available one. And the spec's validation branch is triggered by an insufficient **sample**, not an uncomputable deflator: the routing is a **reading**, and the branch it reaches is a disjunction this document records as having **no selector**, so a c-8 halt is reachable by any party able to zero one registered pair's DESIGN-span activity. |
| **Stale after the ruling** | `P_AND_CORRELATION_INDEX_SET_NOT_BOUND` sat in the "closed, all HISTORICAL" list and in the "still open" list of the **same header block**; `P_UNIVERSE_RULED_CORRELATION_PAIR_SET_STILL_UNRULED` likewise, across four sites; §0.6's referral register still called NR-L unresolved; and five sentences still said Q10(i) was open. All corrected. |
| Smaller | `mean|r|` has a **positive null floor** of ≈0.045 at 310 dates, so the spec's "Independent pairs ⇒ `rho_x → 1`" is finite-sample false by construction — conservative, and recorded as a fourth accepted cost; a pair with exactly **one** DESIGN-span trade is *defined*, so c-8 never sees it, and near-degeneracy may not be silently repaired; the completeness residual now states its **direction** (every short roster raises `N_eff`); c-3's equality condition needed "all **non-zero** entries"; the cell is subtracted "once **per trade**"; c-4's cell has a direction and the lower cell is the likelier favourable arm; nothing bounds **DESIGN-span** activity, so a sparser run dilutes `c` and compounds with the blocker; and the interval between the frozen method and the unwritten implementation is named, because `pandas.DataFrame.corr()` defaults to the pairwise deletion c-6 forbids. |

**Attacks that did not survive the sources**, recorded because their failure is
evidence: the **"(as in M1)" reading holds** — the parenthetical attaches to "UTC-day
portfolio sums" inside a sentence about cross-pair dependence, so committed authority
does **not** require entry-day and no conflict needs surfacing; **"one committed test
fixture" is not an undercount** — only one of the two hand-built `_trades_from_accepted`
calls passes a one-element bars list; the **exit marker always resolves in range** at
the first call site; **the c-7 zero-fill does not leak** into the Sharpe, drawdown or
coverage series, which share no object with it; `ignored_signals` is **not** an
unregistered exclusion route, being deterministic and already keyed on the exit marker;
**per-pair rescaling cannot move `r_pq`**, and c-4's two forbidden transforms are the
only ones that could; the **diagonal and ordered-entry readings are not levers**; c-8 is
**not** exploitable in the inflating direction; and a source-fidelity check of the
ruling's authority table found **no misquotation** — `PAIRS_20`'s 8 currencies and 88
leg-sharing entries, the 310 dates and 89 weekend dates, the two constructors, the
absence of any correlation call in either M15 package, and the four APPROVED-spec
strings all verified verbatim.

**Findings the lead did not adopt.** One role proposed ruling the producer question
here (its limb c-10). The lead declined: R-10 hands the quantity to this gate, but the
configuration family A evaluates is **selected on validation** and so does not exist
when `c` must be measured, which makes a producer rule a genuine human + ChatGPT
choice rather than a wording gap. It is named as a blocker with dispositions
enumerated instead. **One inter-role disagreement was resolved on the evidence** (the
right edge, above), and no unresolved material disagreement remains.

### 12.14 Fifteenth review round — Ruling c-10 and the §8.6 packet

**Three separated doc-only roles, all three completed**, each given the source, the
diff and the contract and **none given another role's conclusions**: **configuration
binding and selection semantics** · **daily Sharpe and time-series sampling** ·
**duration, window and leakage boundaries**. The lead ran its own verification pass
**before** any role returned; those findings are recorded as the lead's. Round 11's
partial-coverage record is **not** relabelled.

**The headline: `NO_NR_L_MINIMUM_RESEARCH_CONTRACT_BLOCKER_REMAINS` is withdrawn for
the second time, on the same test both times.** It was claimed in the same commit as
the ruling that was supposed to earn it, and the correcting evidence was already in the
document.

| Defect | Outcome |
| --- | --- |
| **c-10 froze the map's *keys*, not its *values*** | The sequence freezes the configuration set and the map, and nothing freezes the **inputs** that decide what each `c_design[config_id]` *is*. Four inputs are still unfixed and each moves every value: the warm-up `W`; **Ruling 4's rollover window**, which prereg §5 lets gate 3a or the design audit **widen**; the **holiday / thin-liquidity exclusion policy**, `[FIXED-AT design audit]` and re-pointed by **T-6** to "approved before gate 7"; and the **concurrency / exposure caps**. So "after step 5 there is no chooser" was true only downstream of step 5. Added `C_DESIGN_SERIES_INPUTS_MUST_BE_FROZEN_BEFORE_THE_MAP_IS_BUILT` — **and the requirement collides with T-6's own schedule**, which is a `MINIMUM_RESEARCH_GATE_BLOCKER` this ruling does not close. |
| **R-10 was cited as committed authority, which this document forbids by name** | c-10's classification said the prohibition was "confirmed" because R-10 already carries it. But §4's R-10 is **this packet's own proposal**: §12.5 records that calling it "committed text" is **False**, and §8.3 adds that doing so "is withdrawn and **must not recur**". It recurred. Both the prohibition and the mechanism are **additions**. |
| **The in-sample question was classified by a category the test does not have** | `C_DESIGN_SPAN_RUN_IN_SAMPLE_STATUS_NOT_REGISTERED` was called "a residual of the committed design". By §8.4.13 it moves `c` and `N_eff`, is exercisable by a party (prereg §3.1 defines **no training-span role**), and its direction is **not established** — so it defaults to **blocker**. And the category was unavailable to c-10 in particular, which is the ruling that pulled the producing run into NR-L's scope. |
| **"The stricter reading governs" had no content — and the order is decidable** | Select-then-check can only route into the committed `failure_handling`; filter-then-select can only convert a case that would have closed into a live selected configuration. So filter-then-select is **never** stricter, and naming select-then-check as the governing default **invents no selection rule** — it refuses a rescue. Installed as the default, with the ruling still owed. |
| **The conservatism claim was understated on one limb and overstated on the other** | Understated: `EV_d ≥ ev_min` is nested and `EV_d > EV_{−d}` is `ev_min`-independent, so eligibility can only remove a **suffix** of the ordering and c-8 firing at `ev_min = 0.0` is **whole-family**. Overstated: "the sparsest candidate carries the lowest `c`" is c-7's **tendency**, not a theorem, and it fails under a concurrency cap where executed sets are not nested. |
| **The kill gate was never addressed** | Prereg §9.V reads "at at least one **registered** `ev_min` operating point" — the registered set, not the eligible subset — and it is Ruling-10-frozen, so `c` may not tighten it. That leaves a family that passes §9.V with **no selectable configuration**, a state with no committed disposition. `KILL_GATE_READS_THE_REGISTERED_SET_NOT_THE_ELIGIBLE_SUBSET`. |
| **§8.6.3 computed the holdout start, which §8.2.7 forbids by name** | It said the holdout "begins at the first bar **25 M15 bars after** `T_v`". §8.2.7: "the holdout start is **declared, not computed** … the embargo is a **constraint verified against that declaration, never a formula that produces it**", because a computed start "would move whenever the calendar approval landed". Under ω-13(a) the calendar lands **after** the declaration, so the computed form is exactly that post-freeze lever. Withdrawn. |
| **…and `D` was demoted to "derived", dropping four of Q10-B's six declared objects** | Q10-B declares the validation start, `T_v`, the **declared holdout start**, the holdout window, `T_h` **and** `D`. `D` is the **holdout** duration between the *declared holdout start* and `T_h` — expressly **not** `T_h − T_v`, which overstates the holdout by the embargo in the direction that makes the ≥ 2-month floor easier to claim. Without `D` in the record, `TWO_MONTH_HOLDOUT_IS_A_MINIMUM_NOT_THE_OPERATIVE_DURATION` is uncheckable. |
| **The interval-convention token was false at one boundary and over-reached at two** | `no_overlap.py` derives `_DEAD_END_EXCLUSIVE = DEAD_END + 1s` and **raises at import** unless it equals `FORWARD_FLOOR`, and `is_dead_window_instant` is half-open — so dead→forward is **contiguous, not gapped**, and the doc's version was **less conservative than the code**. The one-second band exists only at design→dead. And "role spans" reached `T_v`/`T_h`, for which the endpoint convention is expressly `DURATION_BOUNDARY_ARITHMETIC_AND_ENDPOINT_CONVENTION_PENDING_HUMAN_CHATGPT_RULING`. |
| **`SPAN_MINIMA_ARE_NOT_ELIGIBLE_EVENT_MINIMA` was mis-scoped to the holdout** | T-1's burn-in is a **single forward-epoch** burn-in — `warmup.py` indexes eligibility "zero-based over **forward-epoch** bars" — so there is no second burn-in at the holdout, and prereg §3.1 places the embargo **outside** the holdout span. The drift came from rendering T-1's "first `W` bars of the forward epoch" as "of validation". |
| **§8.6.4 item 3 reinstated by list-position the order ω-13(a) reversed** | Calendar approval was listed as a **precondition of the declaration**, which is ω-12(d)'s superseded order. It **follows** the declaration; `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` binds before the **continuation**. |
| **The forbidden-anchor restatement dropped the five availability-shaped anchors** | It kept only the outcome-shaped ones and dropped "first available date", "latest available date", "today", "maximum available dataset date" and "use all available history" — the five that bite hardest in a packet whose whole subject is that data has not accrued, and the only upward constraint on `T_h` given that §8.6.2 records **no committed forward-epoch ceiling**. Restated in full. |
| **§8.6.1's magnitude argument was wrong three ways** | The **regime was mis-scoped** — §0.6's 0.56 is **per pair**, and twenty pairs is ~11 portfolio trades/day, a *dense* index for a portfolio sum. The **active share is not free** — `daily_coverage` divides the *same set that indexes the Sharpe series*, and coverage ≥ 0.60 is frozen and conjunctive, so the same-clock ratio is bounded at `1/√0.60 ≈ 1.29×` and the ×1.5 / ×1.9 rows are **not shown to be admissible**. And the **direction is not unconditional**: `C/B = √(252/(365a))` crosses 1 at `a = 252/365 ≈ 0.690` and is **conservative** above it, so the A-ω-5 argument bites only in a regime this packet cannot establish. |
| **…and the candidate enumeration was not exhaustive** | Two cells were missing, with **opposite signs**: active-index × `√365` (the reading "ann., UTC-day" most literally suggests, and the **most permissive of all**), and complete-index × `√252` (the cell reached by taking option (B) without changing the code's default — ~17% **conservative**). |
| **Q10(iii) reaches the operating point, and the committed metric does not** | `select_threshold` takes the **argmax** of the validation daily Sharpe, so under (A)/(B) the per-candidate factor can move the selection — while prereg §8's **committed** metric is validation net **expectancy**, which is annualisation-free. The reach exists only through an implementation that diverges from the committed metric, and both halves are now stated. |
| **§8.6.5's sample-floor argument was unsound** | It argued from "more events on the same clock shorten the gaps and raise `ω`" after positing a **fixed** event rate — two different comparative statics, and at a genuinely fixed rate `N_eff` would rise in proportion. The conclusion and the token are conservative and survive; the argument is replaced with the sound one (`ω` is measured on the evaluated role itself, and the rate over a longer span is not known to be the design-span rate). |
| Smaller | The turnover-day candidates were **four**, not three — the registered R-5 denominator `compute_all` already receives was missing, and the committed turnover implementation is the **strictest** reading, the opposite polarity from §8.6.1's (C); "122 days ≈ 4.0 months" silently encoded an undated "present record date" and leaned on month arithmetic §8.2.3 records as unresolved, replaced by a date comparison; §8.2.8 step 5 also carries the month-arithmetic question, which §8.6 does not address; a "repo-wide grep" citation looked self-contradicting; `√k` presumes serial independence, unaddressed by any committed source; a Sharpe on *returns* is provably the same number under fixed stake and is closed rather than left open; the gate-4 audit's "prefer a holdout longer than the minimum" is a **non-binding** preference and may not become an anchor; and one header token carried two spellings. |

**Findings the lead did not adopt.** One role proposed reclassifying
`SELECTION_VERSUS_CERTIFIABILITY_ORDER_NOT_REGISTERED` as a blocker; the lead installed
the derived **select-then-check** default instead, which removes the lever while leaving
the ruling owed, and recorded that a default is not the ruling the question deserves.
One role's proposed `C_UNCERTIFIABLE` marker had already been added by the lead's own
pass. **No unresolved material disagreement.**

**Attacks that did not survive the sources**, recorded because their failure is
evidence: the **corrected three-configuration set is right and exhaustive** — model
family, params, class weighting, calibration, features, horizon, pairs, sessions and
cost cells were each checked and each is frozen or not a candidate axis, so `ev_min` is
the only registered multiplicity; **Ruling 9's tie rule and selection metric are
committed and blind to `c`**, so `c` as a tie-breaker is foreclosed by authority and not
merely by this ruling; **the 25-bar embargo has no off-by-one** — horizon 24 plus one
leaves a clear bar under either label-window convention; **every row of §8.6.2's
boundary table** and **every field of the forward-epoch manifest block** verify verbatim;
**no date is invented** anywhere in §8.6;
**`EXACT_WINDOW_NOT_READY_FOR_DECLARATION_FORWARD_EPOCH_DOES_NOT_EXIST` is the honest
status**, neither overstated nor understated, and "not a contract gap" is right;
**Q11/§0's freeze semantics are carried without loosening**; and the gate-4 audit
**tightened nothing** about the Sharpe, so `252` does not carry by reuse either.

### 12.15 Sixteenth review round — §8.7's four rulings

**Three separated doc-only roles, all three completed**, each given the source, the diff
and the contract and **none given another role's conclusions**: **DESIGN
prediction-generation and leakage semantics** · **daily Sharpe and time-series sampling**
· **adversarial: the `c`-input freeze, the turnover day and the closure claim**. The lead
ran its own verification pass **before** any role returned. Round 11's partial-coverage
record is **not** relabelled.

**⚠ The breach this round has to record first.** §8.7.6 claimed
`NO_NR_L_MINIMUM_RESEARCH_CONTRACT_BLOCKER_REMAINS` and grounded it on "**this round's
review has run and returned (§12.15)**". **§12.15 did not exist when that was
committed** — the roles had been dispatched and had not reported. It was a **forward
reference asserted in the past tense**, which is the fabricated-audit-completion shape
§12.5 already records once for this packet. The adversarial role found it. The claim is
**withheld**, the citation is corrected in place rather than deleted, and the rule that
follows is
`CLOSURE_CLAIM_REQUIRES_COMPLETED_REVIEW_AND_NO_UNRESOLVED_MATERIAL_BLOCKER` (§8.8.0).
*This round first wrote that rule as a same-round **prohibition**; it is **withdrawn as
over-broad** — the failures were the phantom citation and the live blockers, and a
ceremonial extra round would have caught neither.*

| Defect | Outcome |
| --- | --- |
| **The closure claim was grounded on a section that did not exist** | Above. Withheld, recorded, and a procedural rule added. |
| **c-11's straddle ban is unsatisfiable against two FROZEN prereg rulings** | It forbids using "a statistic fitted on data that includes an observation", naming **the cost table** and **`W̄`/`L̄`** — and prereg §5 freezes the spread tables "**from design data**" while prereg §8 freezes `W̄`/`L̄` "**estimated on design data**". Every DESIGN observation is inside both. Resolved by scope: the `c` generation uses **fold-local** tables, the frozen tables continue to govern validation and holdout, and the cost is recorded — `c_design` is then **not** the correlation of the frozen production configuration. §4's R-2 already stated the mechanism ("the labels inside the slice were constructed using the slice"). |
| **…and the ban reaches the labels and the eligibility hurdle** | `TP_dist`, `SL_dist` and `1.5 × ATR14 ≥ 2.0 × cost` are all functions of `cost`, so a fold-local table **changes which DESIGN bars are events**. Named. It does **not** move the `≥ 1,000` raw floor, which is measured at holdout. |
| **"No in-sample prediction path in committed code at all" is false repo-wide** | True of `scripts/ml_step4/`. `compare_multipair_v6_meta.py` runs Layer-1 inference over the model's own `train_slice` and argues in its docstring that this "is fine" — the reasoning c-11 refuses. Scoped, and the cost-asymmetry argument that leaned on it is withdrawn. |
| **"No CV machinery … none exists today" is false repo-wide** | Walk-forward and purged machinery exists at `stage22_0e_meta_labeling.walk_forward_oos_folds`, `train_ml_baseline.train_walk_forward` and `ml_uplift_harness.contracts` — Phase-9 / stage-22 lineage this programme has invalidated once. Scoped, with `C_GENERATION_MACHINERY_MAY_NOT_BE_REUSED_FROM_AN_UNAUDITED_LINEAGE`. |
| **c-11 transplants §4 R-2's normative text while disclaiming R-2 as authority** | The no-straddle enumeration and the one-span rule are R-2's. The adoption is c-11's own ruling, R-2 remains a proposal, and the provenance is now recorded instead of left for a reader to notice. |
| **The deferred generation parameters are not direction-neutral** | The **trailing gap** — R-2 derives ≥ 224 M15 bars for an H4 ATR-14 — runs *smaller gap → more predictions → lower `c` → higher `N_eff`*. The **fold count** runs conservative through the prefix limb and **anti-conservative** through fit quality, so its net is **not signed**, and the lead's own "a conservative one" is narrowed to the prefix limb. |
| **c-12's enumeration dropped `W̄`/`L̄` — the input c-11 names by name — and five others** | Added: `W̄`/`L̄` and its unregistered estimator, the label geometry, the cost-hurdle rule, the M15 aggregation identity, the entry/exit marker convention, the pip-size authority. The table is now explicitly **not exhaustive**, and **no session may classify an input out of scope**. Also registered: prereg §6's "median eligible ratio < 3.0 triggers design-audit reconsideration" is an upstream route triggered by a **design-data** observation that the `c`-scoped prohibition does not reach. |
| **c-12's freeze has no locus** | Nothing records what the inputs were, nothing distinguishes a first build from a rebuild, and the seed policy is `bounded_not_bitwise_guaranteed`. `NO_LOCUS_RECORDS_THE_FROZEN_C_MAP_INPUT_SET` · `C_INPUT_FREEZE_CHECKABILITY_IMPLEMENTATION_PENDING`, deferred on ω-13's residual-5 footing, deferral lapsing where the prerequisite fails. |
| **c-11's leakage rule is unfalsifiable from the record** | An Option-A run reports the R-6 fields **identically**. The record must additionally carry the generation-method identity, its fold/window/step boundaries as explicit UTC date ranges, and per fold which fitted statistics were used over what rows. |
| **"Everything else in Calendar B may land on its committed schedule" reads out ω-13(b)** | Forward-role eligibility semantics touch no DESIGN bar, so they escape c-12's `c` test — but ω-13(b) is **not** span-scoped. Narrowed to the operational and production remainder, and `CALENDAR_B_SCOPE_CLASSIFICATION_HAS_NO_NAMED_JUDGE` registered: a scope rule without a judge is a dismissal tool. |
| **Q10(iii) reaches operating-point selection, and §8.7.4 did not say so** | `select_threshold` is a pure argmax on the validation daily Sharpe with **no trade-count floor**; under the ruled index the per-candidate scaling carries `√(activity)`, so the argmax can move. The token §8.6.1 minted for exactly this was orphaned by the ruling that engages it. Carried, with a reselection lock. |
| **"Fills an empty slot rather than changing a committed value"** | True of the **factor**, false of the **index**: prereg §9's frozen daily-aggregation sentence says "UTC-day portfolio **sums** (as in M1)", and §8.5.0's own load-bearing reading holds that the parenthetical carries the aggregation shape. Limb 1 changes a committed construction, on the authority prereg §9 reserves. |
| **"The evaluated role's span" was undefined** | Three holes: a data-dependent index reading was open (trimming idle edges raises `|mean/sd|` for every series); the instant→date convention is still pending; and the right edge had no disposition, the identical hole c-6 had to rule for `c`. All three closed, and the limb marked **instantiation pending the Q10-B declaration**. |
| **The two Q10(iii) limbs could be adopted apart** | `√365` on the committed **active** index is §8.6.1's reading **(D)** — the most permissive of the five — and the complete index on the committed `252` default is **(E)**, reachable by simply not passing the argument. Partial adoption forbidden in both directions. |
| **Limb 2's own direction is knowable with no data** | Zero-filling multiplies `mean/sd` by a factor `≤ 1`, equality only at full activity — checked algebraically and on **80,000 randomised synthetic series with no counterexample, maximum ratio exactly 1.0**. Only the *composite* against `√252` is conditional; the parts are not. |
| **The complete index disables two fail-closed guards** | A single active date on an `N`-date index gives exactly `sign(x)·√(365/N)` — **+2.45 at 61 dates** against a frozen `≥ 0.8`, where the committed code returns `0.0`. Contained at holdout by the conjunctive rows; **not** contained at validation, where `select_threshold` applies no trade-count floor. Recorded as an accepted cost. |
| **The coverage bound did not survive, and its arithmetic was wrong anyway** | `Q10_III_SQRT_252_INFLATION_IS_BOUNDED_BY_THE_FROZEN_COVERAGE_ROW` rested on index and denominator sharing a clock; the ruling separates them. Independently, `1/√coverage` is the ratio for the *active × √365* reading, not for `√252`, whose value at the floor is ≈1.07. **Withdrawn**; no upper bound claimed. |
| **The turnover "entry marker" was chooseable** | Two instants sit one bar apart — the decision bar `i` and prereg §6's next-bar fill — and the ruling's words selected one while its rationale selected the other. Named as the **decision bar**. |
| **§8.7.5 had no anti-reselection lock, on a rule that reaches the kill gate** | §9.V's "within the turnover budget" makes the figure a selection filter. Lock added, and the two unregistered axes locked pre-observation with their **permissive arms named** — `max ≥ mean` makes the mean permissive and incumbent; the larger denominator is the permissive denominator. |
| **§8.7.6 stated a test its own residual list fails** | Two turnover items reach experiment selection and carried no default. Any closure claim is now explicitly **scoped to NR-L's statistical choices**. |
| Smaller | Q10(i)'s reach is **five** quantities, not seven, since turnover moved to the entry date — and the validation binding of its lock now rests on the validation Sharpe alone; `MetricTrade`'s single `day` field cannot serve both attributions; §8.7 creates a **fourth** day object and turnover is the only activity-derived one; the leap-year dismissal's stated reason was a non-sequitur (the constant is span-independent); §8.6.6's heading and status line were stale; and the lead's own synthetic magnitude table was not reproducible from the text and is replaced by c-7's fully-specified counterexample. |

**Found by the lead before any role returned**, and recorded as the lead's: c-11's first
drafting called common structural zeros "a large, invisible, **anti-conservative**
distortion" and refined the `c` index on that basis, amending Ruling c-6. Both were
**withdrawn** — a *common* zero block is not c-7's case, and it measurably **raises**
`|ρ|`. Two roles independently reproduced that finding, one by the same route.

**Findings the lead did not adopt.** One role escalated the fold-local cost table to a
blocker on the ground that it makes the **event sequence** a function of the generation
method and so collides with ω-13(b). Resolved on the evidence: `ω` and `N_raw` are
measured **per role** on validation and holdout, so a DESIGN-span eligibility change
reaches `c` and **not** the ω/`N_eff` event sequence. The consequence is recorded at
c-11 in its correct scope instead. **No unresolved material disagreement.**

**Attacks that did not survive the sources**, recorded because their failure is
evidence: `turnover()`'s **numerator carries no date**, so the entry-date rule changes
only the denominator; **entry-date counting is not** the ~42% widening Q10(ii) warned
about, since both entry and exit sets are active-date sets and the ruling crosses no
axis; **Q10(iii) does not move turnover**, which is computed from the trade list;
**maxDD is invariant** to the zero-fill, verified on all-negative, leading-idle,
trailing-idle, interior-gap and single-date series plus 20,000 randomised insert
patterns; **coverage is not re-denominated**; `(0.0, 0.0)` **cannot** produce a trade by
any route, and under the M15 EV gate `p̂ = 0` gives `EV = −L̄ − cost < 0 ≤ ev_min` at
every registered operating point; Option C is unavailable on a **source** ground, since
`no_overlap` raises below `DESIGN_START`; the concurrency rule, pair universe, date index
and idle rule **are** in c-12's table; and three of the five "still unregistered" items
**do** earn their exemption.

### 12.16 Seventeenth review round — §8.8's rulings

**⚠ Coverage was PARTIAL: one of three roles returned.** Three doc-only roles were
dispatched — **DESIGN generator / target-leakage / fold-local semantics**, **Sharpe
guard order / annualisation / validation selection**, and **adversarial remaining
researcher freedom**. Only the **Sharpe** role reported. The other two terminated on an
account-level **weekly API limit** after producing an opening line and nothing else.
**`ROUND_16_REVIEW_COVERAGE_PARTIAL_ONE_OF_THREE_ROLES_RETURNED`.**

**The gap sits over this round's largest new surface.** The two roles that did not run
are the two that would have attacked **Rulings c-13 and c-14** — the generator shape and
the input freeze — which are exactly the material this round added. Round 11's partial
record is **not** relabelled by this, and this one is not softened by the lead's own
verification having gone well.

**Found by the lead before any role returned.** c-13 claimed **one** open parameter while
specifying only "date-aligned blocks" — false, since an unspecified block width is a
second parameter that moves `c`. Fixed by ruling every block after the first to be
exactly **one UTC date**, which makes the partition a deterministic function of the first
predicted date alone; the retrain-per-date cost is named as implementation. Two further
points were added at the same time: the 25-bar purge's sufficiency is **derivable** (last
admissible training bar at `block_start − 25`, exit at most 24 bars later, label closes
one bar clear), and a **training label belongs to the fold that fitted it**, because the
fold-local cost table makes prereg §6's barriers fold-dependent.

| Defect | Outcome |
| --- | --- |
| **The guard order omitted the membership filter, and the omission reproduced the exact case it claimed to close** | §8.7.4 rules that a trade whose Q10(i) exit date falls outside the role span is not a series member. §8.8.4's order block went straight from active-date aggregation to the guards, so a trade attributed outside the span sat in the guarded set and was dropped at the *reindex* — leaving one non-zero date in 61 and the reported **+2.45**, the very figure the ruling says is closed. Membership filtering now **precedes** the guards, at both edges. **`MEMBERSHIP_FILTERING_PRECEDES_THE_GUARDS_AND_THE_GUARDS_PRECEDE_THE_FILL`.** |
| **A fired guard is not an exclusion — and this ruling created the route** | A guard that fires returns exactly `0.0` into `select_threshold`'s argmax, where it **beats every genuine negative Sharpe**; an all-degenerate sweep ties at `0.0` and resolves silently to the production default. Verified: argmax over `{0.35: 0.0, 0.40: −17.59, 0.45: −27.97}` selects **0.35**. Against the incumbent §8.7.4 state this **changes which operating point reaches the holdout**, toward the candidate about which least is known. Carried as a live **blocker**; making a fired guard an exclusion is a human + ChatGPT question §8.8.4 declines rather than answers. |
| **The zero-fill direction claim was one-sided** | "Limb 2 weakly reduces the reported Sharpe **for every series**" is directionally **false**: a factor `≤ 1` moves a **negative** Sharpe *toward zero*, i.e. upward. Measured: `m = 3` of 61 goes `−19,085.9 → −4.31`; `m = 20` goes `−3,198.7 → −13.23`. Since `select_threshold` argmaxes the **signed** value, the complete index **rewards the sparsest candidate** on a loss-making sweep — so §8.7.4's "penalises sparser candidates" is **withdrawn as one-sided** and the anti-conservative arm is named under A-ω-5. |
| **"Closed by this ordering" overstated the result** | The guards are **definedness** guards, not sparsity guards: they block `m = 1` and the all-equal cases only. The supremum at `m` in-index active dates is `√(365·m(N−1)/(N(N−m)))` — **3.49 at m = 2, 4.31 at m = 3** on a 61-date span, against a `0.8` floor — and a `1e-7` perturbation of two identical values moves the figure from `0.0` to `3.49`. Holdout is contained by the conjunctive rows; **validation is not**. |
| **§8.7.4 and §8.8.4 asserted opposite dispositions of one token** | §8.7.4 still called `COMPLETE_INDEX_DISABLES_THE_DEGENERATE_SHARPE_GUARDS` "**an accepted cost**" while §8.8.4 said it was closed. The diff had touched neither. §8.7.4's bullet is now marked superseded in part, with the residual pointed at §8.8.4. |
| **"Active-date observation set" was undefined at the one site where it decides the value** | Date-with-a-trade versus date-with-non-zero-PnL diverge exactly at the gate: two offsetting trades on one date give `len = 2` under one reading and `len = 1` under the other, and the readings differ by `2.446` versus `0.0`. Defined as **at least one attributed in-index trade**, zero net included. |
| **The freeze lock was a calendar lock where an observation lock exists** | A pre-validation freeze date is satisfiable while the guard order is chosen after observing a **DESIGN-span** Sharpe. `Q10_III_MUST_NOT_BE_RESELECTED_AFTER_OBSERVING_ANY_METRIC_IT_MOVES` now binds this sub-limb by name — the prohibition is on the observation, not the calendar, which is §8.8.0's own correction applied to itself. |
| **The header did not register Q10(iii)-a, and misdescribed limb (iii)** | The token appeared only inside §8.8. The header now names both sites, states that **§8.8.4 governs** where they differ, and describes limb (iii) as the index, the idle rule **and** the factor rather than the factor alone. |
| **§10's mandatory Sharpe standard error was still on the `√252` weekday clock** | §10 requires an SE of `sqrt(252/N)` ≈ 1.07 and says "a Sharpe reported without that number is not a result" — inconsistent with this document's own ruled annualisation. Updated to `sqrt(365/N)` ≈ **2.45 at a 61-date span**, with the added requirement that a guard-fired `0.0` be recorded as `SHARPE_UNDEFINED_GUARD_FIRED` with its active-date count, **never as a measured zero**. |

**Attacks that did not survive the sources**, recorded because their failure is evidence:
there are **exactly two** committed Sharpe guards and no others in the metric path;
validation and holdout **share one implementation** with no role-specific variant; **no
new observation threshold** is created by §8.8.4; **maxDD is invariant** to the zero-fill,
re-verified independently on leading-idle, trailing-idle, interior-gap, single-date,
all-negative and empty-active cases plus 200,000 randomised interleavings with zero
mismatches; **coverage is untouched**, sharing no object with the Sharpe series; there is
**no filled-passes/active-fails gap**, since `sd(filled) = 0` with `m < N` forces all
values zero and the active guard fires first; `√365` **remains coherent** with the ruled
index, the guard being a gate rather than an estimator; and **no market-hours fact, data
authorisation or empirical estimate** appears in §8.8.4 — and, unlike the previous round,
**the §12 citation it makes is real**.

**Findings not adopted as ruled changes.** The returning role offered two dispositions it
could not settle — whether a fired guard should exclude a candidate, and whether §8.8.4
needs its own amendment classification. Both are recorded as open human + ChatGPT
questions rather than decided here. **No inter-role disagreement arose**, for the
unsatisfactory reason that only one role returned.

### 12.17 Eighteenth review round — §8.9's rulings, and the closure decision

**Coverage was FULL on the assigned scope: both roles returned.** The round's brief
assigned exactly the two perspectives that terminated in the round recorded at §12.16 —
**DESIGN generator / target-leakage / fold-local semantics** and **adversarial remaining
researcher freedom**. Both ran to completion and reported.
**`ROUND_17_REVIEW_COVERAGE_FULL_BOTH_ASSIGNED_ROLES_RETURNED`.**

**One limitation, named rather than smoothed.** The scope was two roles by instruction,
so the **Sharpe guard order / annualisation / validation selection** perspective — the
one role that *did* return at §12.16 — was not re-run against §8.9's **new** material
(Ruling Q10(iii)-b and Ruling c-15). It reviewed §8.8, not §8.9. The adversarial role
reached the validation-selection surface and found four defects there, so the area is
not unexamined; it is examined by one perspective rather than two.
**`ROUND_17_SHARPE_SELECTION_PERSPECTIVE_NOT_RE_RUN_AGAINST_SECTION_8_9`.**
Round 11's and round 16's partial records are **not** relabelled by this round's full
coverage.

**Found by the lead before either role returned**, and recorded because it cuts against
the ruling this session was handed: §8.9.1's first drafting let "outcome-blind" imply
"conservative". §8.8.2 had established that **both** limbs are monotone in prefix size,
so the conservative extreme is a **larger** prefix, and 25% is anti-conservative relative
to every larger one. The correction states the trade explicitly — deflator conservatism
given up for estimator coverage — on a synthetic table whose generating model is written
inline so the figures are reproducible from the text and marked
`NON_NORMATIVE_DIAGNOSTIC_ONLY`.

**DESIGN generator / leakage role — findings adopted.**

| Defect | Outcome |
| --- | --- |
| **The fold-locality test licensed exactly what c-11 forbids** | c-14's token read `FOLD_LOCALITY_IS_REQUIRED_FOR_TARGET_DERIVED_INPUTS_ONLY`. The cost table is **not** target-derived — prereg §5 fits it on quoted spreads, `cost = median_spread + pad_exec + cell_slippage`, with no target anywhere — so the token licensed the frozen whole-DESIGN table for `c` generation, **which c-11 forbids by name**. Withdrawn and replaced by `FOLD_LOCALITY_IS_REQUIRED_WHERE_A_FITTED_STATISTIC_REACHES_AN_OBSERVATION_IT_WAS_FITTED_ON`. Verified at source before applying |
| **Which fold's geometry governs a *predicted* bar was unstated** | c-14 scoped fold-locality to *training* labels, admitting a reading on which the frozen span-wide table governed predicted bars — the leakage c-11 refuses. Now: **the fold that predicts a bar supplies its eligibility and barrier geometry** |
| **The calibration inner split is a second unregistered generator parameter** | Verified at source: prereg §8 gives only "a split carved from the training span only"; `contract.py` carries `CALIBRATION = "none_raw_predict_proba"`. Its fit-quality limb is anti-conservative in the knowable direction, the identical argument that raised the first predicted date to a blocker. Recorded as a live `MINIMUM_RESEARCH_GATE_BLOCKER` |
| **The walk-forward reconstruction was repo-wide and wrong** | §8.8.1 said "**both** walk-forward implementations… **neither** carries a purge". False: 21 `compare_multipair_*` scripts form a **rolling** family, and `v23_realism` **does** purge — by row count, `tr_df.iloc[: -args.horizon]`, citing de Prado §7.1 and choosing rows over wall-clock for the same reason §4 gives. The conclusion survives on a **different** ground — fenced lineage plus an uncommitted trailing gap — and the token is re-spelled accordingly |
| **The fold-count direction token does not transfer** | `C_GENERATION_FOLD_COUNT_NET_DIRECTION_ON_C_IS_NOT_ESTABLISHED` rested on "more folds mean shorter fitting windows", a **rolling**-origin mechanism. Under an **expanding** window more folds shorten no fitting window, so fixing the fold count at the family maximum takes no unsigned risk |
| **"A retrain per pair per date per configuration" is wrong arithmetic and worse than wasteful** | `ev_min` applies to `EV_d` **after** `p̂`, so one fit serves every `config_id`: 20 × 232 = **4,640** fits, not 13,920. Under `bounded_not_bitwise_guaranteed` a per-config refit would make `c_design[config_id]` differences partly **seed artifacts** of a map c-10 keys by `config_id` |
| **The purge boundary differed from `split.py` by one bar** | The blockquote said "minus the last 25 bars preceding the block" while the derivation placed the last admissible training bar 25 bars before the block's first bar. Aligned to the committed convention `train_label_end = train_end − purge_bars` |

**Adversarial researcher-freedom role — findings adopted.**

| Defect | Outcome |
| --- | --- |
| **The committed selector refuses an incomplete domain** | `select_threshold` raises `ThresholdSelectionError` unless the sweep covers the registered set exactly, calling an incomplete sweep "a multiplicity-control violation". So Q10(iii)-b's "removed from the argmax domain" needs an unregistered choice — fail the family closed, or relax a committed control. Recorded as a blocker with the **fail-closed** arm governing by default |
| **Which validation selector governs is unregistered, and it decides whether the ruling binds at all** | The registered set is three **`ev_min`** points; the only committed selector sweeps three **probability thresholds**, which prereg Ruling 9 forbids twice. If the implementing PR builds prereg §8's expectancy selector, Q10(iii)-b is discharged **vacuously rather than on its merits**. The single item most likely to make a decisive-reading ruling constrain nothing |
| **The fail-closed destination is itself an unselected fork** | "Family A closes **or** adoption waits" are not equivalent outcomes and no selector exists. Recorded; the ruling fixes only that **no candidate is promoted** |
| **The kill-gate claim over-reached** | `KILL_GATE_READS_THE_REGISTERED_SET_NOT_THE_ELIGIBLE_SUBSET` was minted at §8.5.0 about **`c`-uncertifiability**, not guard failure. Scoped to its guard-failure limb only, so §8.5.0 and §8.9.2 do not assert opposite states of one token |
| **An identical-input rebuild is undetectable** | With `bounded_not_bitwise_guaranteed` and `NO_LOCUS_RECORDS_THE_FROZEN_C_MAP_INPUT_SET`, a rebuild that moves no input is possible and unrecorded, and c-15's one-date block multiplies the unseeded fits behind a single `c`. `AN_IDENTICAL_INPUT_REBUILD_IS_A_RESELECTION_AND_THE_FIRST_BUILD_GOVERNS` |
| **prereg §6's barrier-ratio reconsideration is an unclosed upstream route** | A design-data observation that reconfigures c-12's inputs, which `C_OBSERVATION_MUST_NOT_TRIGGER_UPSTREAM_RECONFIGURATION` — scoped to observing `c` — does not reach. Carried, not repaired |
| **§8.9.1 cited a magnitude §8.7.2 expressly withdrew** | It said §8.7.2 "**measured**" the common-zero effect and called it "**mildly**". §8.7.2 claims **no magnitude** and marks its own figures `NON_NORMATIVE_DIAGNOSTIC_ONLY`. Both words removed; the sign alone is cited, and the counterfactual it is measured against is now named |
| **"No favourable classification is asserted in this ruling" was false as written** | §8.9.1's unqualified "the prefix's own effect on `c` is conservative" made it false. Rewritten to assert it only for the arms chosen, with the counterfactual named wherever a direction is labelled |
| **The sparse route Q10(iii)-b does *not* close** | It removes the sentinel route, which fires only at `m < 2` or all-equal. A candidate with `m = 2` still reports up to **3.49** against a `0.8` floor. Added to the untouched list, so the ruling is not read as closing the reachable route |

**Found by the lead while applying the roles' findings**, and material:

- **The generator's unvalued inputs are more than one.** Re-read at source: the
  calibration split, the **final feature list**, the `W̄`/`L̄` estimator and the
  `ATR14_M15` warm-up convention all carry **no committed value**. §8.9.1 enumerates
  them and marks the enumeration non-exhaustive.
- **The feature list's freeze schedule collides with c-12, and scope cannot resolve it.**
  prereg §7 freezes it "at the design audit" and §11 at the "implementation audit", both
  **after** the point c-12 requires every decision-bearing `c`-map input frozen. The
  Calendar B collision was closable by scope; this one is not, because the feature list
  determines `p̂` for every bar. Recorded as a blocker and **not** ruled — the arms are a
  human + ChatGPT scheduling decision.
- **The first predicted DESIGN date is a Saturday.** `2025-07-12` and `2025-07-13` are a
  weekend, so the first two prediction blocks are almost certainly empty. Coherent under
  the ruled complete-index/idle-zero semantics, but stated — and a weekday-aware snap is
  expressly **not** adopted, since it would make the boundary depend on the eligibility
  calendar.
- **Stale assertions the new sections did not update.** §8.2.8's lead and step 5 still
  called Q10(iii) open; §13 asserted it unruled in five places and still listed Q10(i) as
  `REQUIRES_HUMAN_CHATGPT_RULING`; §8.6.1's withdrawn coverage bound was unmarked at its
  own site; the header registered **no** §8.8 or §8.9 ruling token and its document-wide
  `NON_NORMATIVE_DIAGNOSTIC_ONLY` clause omitted §8.6–§8.9. All corrected. *This is the
  same recurring shape the packet has now recorded several times: adding a section does
  not update the sections that contradict it.*

**Claims declined or corrected on the evidence, recorded because their failure is
evidence.** A role's escalation of the fold-local cost table via ω-13(b) was **declined**:
`ω` and `N_raw` are measured **per role**, so a DESIGN-span generation choice does not
reach the forward-role event sequence that token governs. A role's reading that the
sentinel exclusion also closes the sparse-candidate route was **corrected** — it closes
the narrower one. And a role's assertion that no in-sample prediction path exists in
committed code was **scoped**: false repo-wide, true of the M15 package.

**Inter-role disagreement:** none material. The two roles reached the generator surface
and the selection surface respectively and did not contradict each other; where they
overlapped — on whether closure was available — they agreed independently that it was
not, which is the conclusion §8.9.6 records.

**No source or test was read for mutation, changed, or executed; no data was read.** The
roles were doc-only with source **read** access, which is what verifying a citation
requires.

---

## 13. Completion state

**`M15_MINIMUM_RESEARCH_GATE_PENDING_HUMAN_CHATGPT_RULING`** — one completion
state, unchanged, because **Q1 and Q8** remain unruled. *(An earlier drafting also
listed **Q10(iii)**; it is ruled at §8.7.4, and the completion state is unchanged on
Q1 and Q8 alone.)* The unified referral's
earlier status `Q11_AND_SECTION0_PENDING_HUMAN_CHATGPT_RULING` is **historical,
superseded by the ruling at §8.1.0**, and was never a second completion state.

The boundaries (§3), the integrity requirements (§4), the scope test (§5), the
non-implications (§6), the staged flow (§7), the output classification (§9) and
the metric set (§10) are derived from committed authority and are offered as ruled
text. **R-10's `P` limb is now backed by Ruling NR-K** (§8.3.0) and no longer stands
as this packet's own proposal — but only its first half: `P` is reported over the
full registered universe. R-10's further claim that the concentration set, `P`'s set
and `PAIRS_20` **must be the same twenty** is **withdrawn as unruled**, because
§8.3.0 leaves the 0.40 cap a separate authority and `pair_contribution` is computed
over the **traded** set. The phrase "same twenty" occurs nowhere else in the
repository and must not be cited as committed text.

**§8.1 records a human + ChatGPT ruling on the frozen 2-month minimum.** Two
months is a **floor**, not the operative duration; the exact `D` is frozen **once,
at the Gate-3a continuation boundary, before any validation or holdout data,
empirical sample quantity, correlation estimate or performance outcome**; and
post-freeze extension, shortening, reselection, rerolling and replacement are
forbidden for the current Family A. An insufficient-sample outcome at the frozen
`D` is accepted as the result; a different `D` requires a new explicit
pre-registration or contract decision. The governing principle is
`DURATION_SELECTION_MUST_BE_OUTCOME_BLIND`.

**What the ruling did not settle, and what it newly exposes.** The **exact numeric
`D` is not ruled** — blocked by Q10, and by the absence of any committed α or power
target; none is invented. **Q10-A, Q10(ii) and Q10-B are ruled** (§8.2.0); **NR-K is ruled** (§8.3.0), and
**the mean-overlap unit and aggregation is ruled** (§8.4.0), and **NR-L is ruled
together with Q10(i)** (§8.5.0), and **Q10(iii) is ruled** (§8.7.4, guard order §8.8.4,
exclusion rule §8.9.2). *An earlier drafting said "**Q10(iii)** still open"; withdrawn.*
What blocks the exact `D` is now the duration-boundary arithmetic and the window
declaration, not Q10(iii). The
ruling also leaves one indirect lever open: it freezes `D` at the continuation
boundary but does not fix **when that boundary is declared reached**, and a later
adoption date is arithmetically equivalent to a longer `D`
(`GATE3A_CONTINUATION_DATE_NOT_FROZEN_RESIDUAL_AFTER_Q11_SECTION0_RULING`). And it
carries a consequence worth naming: because empirical correlation may not be
observed before the freeze, **`D` can be sized on availability metadata alone, and
therefore cannot be sized to reach `N_eff ≥ 400` at all** — coherent with the
instruction to accept the result, and the price of an outcome-blind duration.

**§8.2 records three human + ChatGPT rulings.** `D` is an **elapsed calendar span
on the UTC clock** — not a weekday, trading-day, eligible-day, event or bar count
(a *derivation* from committed text). The coverage day is the **UTC calendar
date**, with expected slots coming **only from the approved calendar authority** —
which does *not* make all 96 slots of a date expected and authors no
weekend/holiday/closure/DST rule (its second half *confirms* D-6; its first half is
the new part). And the exact `T_v`, `T_h`, window and operative `D` are **declared
explicitly by human + ChatGPT before the continuation is authorised**, with
data-derived anchors forbidden and "choose dates + inspect data" barred from being
one step (a *tightening*, not an amendment).

**The distinction these rulings must not be read across:**
`D_IS_ELAPSED_UTC_TIME != SAMPLE_COUNT_IS_CALENDAR_TIME`. A calendar-span `D` does
not count weekends as samples, holidays as eligible events, or closed intervals as
observations. `D` is time-axis authority only; sample accounting stays with its own
registered authorities. One consequence, stated because this packet once expected
the opposite: **coverage still does not catch a window padded with closed days** —
the ruling confirms that withdrawal rather than reversing it, and the mitigation
rests on the sample floors, which count events.

**Q10's limbs are ruled.** Limb **(i)** at §8.5.0 and limb **(iii)** at §8.7.4;
neither was derivable from an elapsed-UTC `D` (§8.2.8), which is why each needed its own
ruling. *An earlier drafting said limb (iii) "remain open"; withdrawn.* No numeric `D` is
chosen; two months stays a lower bound, and
`EXACT_D_SELECTION_STILL_PENDING_UPSTREAM_AUTHORITIES` — now on the duration-boundary
arithmetic and the window declaration.

**§8.3 records a human + ChatGPT ruling on `P` and the pair universe.** `P` is the
**frozen registered Family A pair universe**; for the current Family A, **`P = 20`**.
`P` may not be shrunk to an observed contributor count — not to
`len(pairs_with_trades)`, not to a performance- or correlation-filtered count, and
not to any post-hoc contributor count whatever. `P SHALL NOT BE REDUCED AFTER
FAMILY_A PREREGISTRATION FOR THE PURPOSE OF IMPROVING EFFECTIVE_N,
CROSS_PAIR_DEFLATION, SAMPLE_SUFFICIENCY, OR RESEARCH PERFORMANCE`; it may not
collapse to one by post-hoc contributor selection; a registered pair's failure is
handled by existing fail-closed semantics or by adoption waiting, never by
shrinkage; and a different universe requires a new explicit pre-registration or
contract decision. The spec's undefined word "contributing" is narrowed to
**contribution eligibility to the registered evaluation universe**.

**`P = 20` does not mean all twenty pairs must trade**, produce non-zero samples,
carry equal weight or show signal — stated here as it is stated first in §8.3.0,
because it is the misreading the ruling is likeliest to be put to.

**What the ruling leaves open, and it is not nothing.** No source or test is
changed: `effective_n()` still accepts `P = 1`, **four** committed tests still
require a `P = 1` roster to return `SAMPLE_SUFFICIENT`, and **sixteen** across four
files still require short rosters to be accepted, so
`P_AUTHORITY_RULED_IMPLEMENTATION_COMPLETENESS_PIN_PENDING` and the missing forward
roster gate (`NO_FORWARD_SPAN_FULL_ROSTER_COVERAGE_GATE_COMMITTED`) are the same
residual seen from two sides. The **correlation** pair set stays unruled
(`P_UNIVERSE_RULED_CORRELATION_PAIR_SET_STILL_UNRULED`) — **both closed by Ruling c-1
at §8.5.0**, along with `P_AND_CORRELATION_INDEX_SET_NOT_BOUND`, which was assigned to
NR-L. The 0.40 concentration
cap is unchanged, is a **separate authority**, and its drop-motive survives
(`CONCENTRATION_CAP_DROP_MOTIVE_SURVIVES_NR_K`). Whether the test-invalidating limb
requires an amendment procedure is **not settled**, and this packet does not assert
that it does not: `NO_GENERAL_CONTRACT_AMENDMENT_PROCEDURE_REGISTERED` is why.

**§8.4 records a human + ChatGPT ruling on the mean overlap fraction.**
**`MEAN_OVERLAP_RULED_EVENT_LEVEL_SAME_HORIZON_CLOCK_EQUAL_WEIGHT_ROLE_LOCAL`.** `g`
and `H` are measured on the **same registered M15 prediction-horizon clock**, so the
gap may not be switched to elapsed hours, weekday or trading-day counts, an event
index, or an arbitrary continuous grid while `H` stays in bars; the clock may **not**
be chosen to lower `rho_h`, and Q10-A's elapsed-UTC `D` is expressly **not** the
authority for it. `overlap_i = max(0, 1 − g_i/H)` is computed per **adjacent**
same-pair interval and then averaged with **equal weight per interval** — `E[f(g)]`,
never `f(E[g])` — so the mean-gap approximation is **not an allowed effective-N
authority** for current Family A. `rho_h` is **pair-local** and cross-pair pooling is
forbidden; events stay with their registered pair labels. A **zero-event** pair
contributes nothing, generates no synthetic overlap, and **stays in `P`**; a
**one-event** pair takes `ω_p = 0` with a raw contribution of **one**, and neither is
permission to shrink `P`. The **method is frozen before data** and the **value is
measured role-locally** when access is authorised — which this ruling expressly does
**not** grant. And measurement may decide the verdict but may never redirect the
experiment.

**Four limbs were derived and are confirmed; six are explicit human + ChatGPT
choices.** Derived: event ordering, the overlap function, `E[f]` over `f(E)`, and
per-pair `rho_h`. Chosen: the clock, the weighting, the zero-event and one-event
dispositions, the freeze semantics, and the no-redesign rule. §8.4.0 carries the table
that says which is which, because a reader must be able to see which limbs would
survive a disagreement about the ruling.

**What the ruling closes, and what it does not.** It closes the weighting freedom
that the review found spanned essentially the whole of `rho_h`'s range. Ruling ω-1
alone only **narrowed** the clock route whose favourable end is knowable with no data,
leaving three bar readings totally ordered in `ω` — and **Ruling ω-11 closes it**, by
naming the substrate as the **approved-calendar eligible M15 slot sequence** for both
`g` and `H`. `H = 24` is 24 *consecutive eligible slots*; `g` is counted in
eligible-slot steps; there is **no continuous-grid fallback, no heuristic clock and no
inferred market-hours clock**, and no market-hours semantics are authored. The ruling
takes the branch that **imports** `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`
and that runs **conservative relative to the continuous grid** — omitting
*ineligible* slots shortens `g`, raising `ω` and `rho_h` and so lowering `N_eff`,
though it is not the `ω`-maximising candidate. It also discharges D-ω-2's remaining constancy
condition, since `H` is 24 consecutive units of that index for every event.

**So `ω`'s semantics are complete and its instantiation is not.**
`MEAN_OVERLAP_FULL_SEMANTICS_RULED_PENDING_CALENDAR_INSTANTIATION`: **no empirical
`ω` can be authoritatively computed before the calendar artifact is approved**, and
this packet creates no calendar. What replaces the old researcher freedom is an
**external dependency and a new surface** — `CALENDAR_CONTENT_DETERMINES_OMEGA_SUBSTRATE`,
since whoever authors and approves the calendar determines the sequence `ω` is
measured on. D-6 places that authority there deliberately and the approval is a human
+ ChatGPT gate, so it is the right place; it is recorded rather than left implicit.
**And Ruling ω-12 rules the four calendar residuals as one.** Two concrete
authorities exist in committed text and they are **different objects**: **A**, the D-6
closure/market calendar carrying a *materialised* `expected_m15_slots` (the
generating-rule spelling is refused by name) plus `authority_version`,
`content_digest` and `target_epoch`, governs **slot membership** and is `ω`'s sole
authority; **B**, Ruling 4's holiday / thin-liquidity calendar that T-6 re-pointed to
"approved before gate 7", governs **event eligibility** and never membership. So the
**ownership** is ruled — A decides membership, Ruling 4 decides event eligibility, and
`ω` derives no rollover or holiday rule of its own — while the **membership outcome**
stays A's content: *if* A declares a rollover slot, Ruling 4 bars the **event**, not the
slot; *if* A declares it closed, it was never a member.
`ROLLOVER_AND_HOLIDAY_SLOT_ELIGIBILITY_RELATIVE_TO_THE_OMEGA_CLOCK_NOT_SETTLED`
therefore **survives**. Exactly **one** artifact at **one**
version **per epoch** must be frozen for the declared window — no schema is invented,
the identity fields already exist — and the order, as corrected by Ruling ω-13(a), is
**window declaration → calendar materialisation → calendar freeze → data
observation**; ω-12(d)'s "calendar freeze → window freeze" is **historical**. Calendar content must be **outcome-blind**, with
post-observation mutation forbidden for current Family A and the `ω` dependence
disclosed at approval; a later artifact may not be re-designated as `ω`'s membership
authority for an already-frozen window. The **same frozen version governs both `ω` and
coverage**, and D-5.8 is unchanged — `ω` is a *consumer* of `expected_m15_slots` and
invents no slot. **If the calendar is unavailable, `ω` is not authoritatively
measurable: no continuous-grid fallback, no inferred market hours** — which may block
formal continuation and authorises creating no calendar here.

**And Ruling ω-13 reclassifies the six residuals and closes the three that move
results.** The test applied first: *can this freedom materially change the research
result, the event sequence, `ω`, `N_eff` or experiment selection **after
decision-bearing information is available**?* **Three are blockers and are ruled** —
the **freeze order** (`WINDOW_IDENTITY_PREDECLARED_CALENDAR_MATERIALISED_WITHOUT_POST_CALENDAR_RESELECTION`:
declare the window → materialise Calendar A **for** that declaration → freeze it → the
window may **not** be reselected on calendar content → only then observe data, which
**supersedes ω-12(d) and adopts §8.2.0's committed placement**, the packet's own
ordering having been the wrong one); **event eligibility**
(`OMEGA_EVENT_ELIGIBILITY_RULES_MUST_BE_PRE_DATA_FROZEN`, with a later Calendar B unable
to change the frozen Family A event sequence retroactively and no post-observation
reclassification); and **per-pair slot variation**
(`PAIR_SPECIFIC_SLOT_VARIATION_MUST_BE_CALENDAR_DERIVED_NOT_RESEARCHER_SELECTED` — the
twenty sets need not be identical, but the variation must be deterministic and never
tuned against `N_eff`). **Two are deferred outside the gate** as
`DEFERRED_PRODUCTION_CHECKABILITY` — FR-8's second limb and the missing identity locus,
both documented, neither closed, and both conditional on
`ONE_SELECTABLE_IMMUTABLE_CALENDAR_INSTANCE_WITH_RECORDED_IDENTITY_IS_AN_EXECUTION_PREREQUISITE`
— **where that does not hold the deferral lapses** and residual 5 is a blocker; and §5's
R-6 lightweight record (`authority_version`, `content_digest`, `target_epoch` with any
output that consumes a calendar) is **not** deferred with it. **One is a
`RUNTIME_CALENDAR_INSTANTIATION_OUTCOME`** — the concrete rollover/holiday membership
set, whose *freedom* is closed as to timing by the new ordering and freeze and as to
motive by outcome-blindness, even though its *value* is unknown, and whose disposition
**depends on residual 5's deferral holding**.

**And a boundary, so the audit stops expanding.**
`NEW_OMEGA_FINDINGS_DO_NOT_AUTOMATICALLY_BECOME_RESEARCH_BLOCKERS`: a future `ω` or
calendar finding reopens the gate **only** if it shows a remaining freedom capable of
moving a result after decision-bearing information; otherwise it is implementation,
evidence, checkability or production-hardening, **recorded against a named later gate**.
That is a rule about **classification, not severity** — and it is bound four ways so it
cannot dismiss findings: the classification is a **human + ChatGPT** call and never a
session's own; "material" means any capacity to move `ω`, `N_eff`, the event sequence or
experiment selection **at all**; "available" means decision-bearing **observation** by
any party including the calendar author; and an unclear case is a **blocker** until
ruled otherwise. **This test is §5's first limb, not a replacement for §5**, whose
second limb governs unchanged and may never be cited to strike a §3 boundary. The mean-overlap contract is therefore
**`MEAN_OVERLAP_MINIMUM_RESEARCH_CONTRACT_RULED_PENDING_CALENDAR_INSTANTIATION`** —
**not** a claim of production readiness, and no empirical value is computed.

**What ω-12 leaves.** B may still move the **event set** after its later approval, and
that residual is **not** conservative — widen-only is conservative for the event
*count*, while removing an event **merges gaps** and can *raise* `N_eff`
(`LATER_EVENT_ELIGIBILITY_CALENDAR_MAY_STILL_MOVE_THE_EVENT_SET`,
`WIDEN_ONLY_IS_CONSERVATIVE_FOR_THE_EVENT_COUNT_NOT_FOR_N_EFF`); the approval marker
is **artifact-declared, not evidence**; nothing enforces any limb in code
(`CALENDAR_FREEZE_CHECKABILITY_IMPLEMENTATION_PENDING`); the role-span truncation limb
is untouched; and whether the outcome-blindness and non-retroaction limbs need an
amendment procedure is **not settled**. **Neither artifact exists.** `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`
remains binding wherever instantiating that clock needs the artifact. And **no code
enforces any limb**: `ω` is still a bare caller scalar with no gaps attached, so the
implementation pin and `OVERLAP_PER_RECORD_PROVENANCE_UNBOUND` belong to a separate
Work PR. Whether the limbs that add requirements the spec does not carry need an
amendment procedure is **not settled**
(`MEAN_OVERLAP_AMENDMENT_CLASSIFICATION_NOT_SETTLED`), on the same ground §8.3.0
recorded for NR-K.

**§8.5 was the next decision packet — NR-L, the cross-pair correlation — and it is
now RULED (§8.5.0), bundled with Q10(i).** The paragraph below is the packet as it
stood before that ruling, retained as the material the ruling was taken on. With `P` ruled, `rho_x = 1 + 19c` — **`ω`'s ruling does not enter this
deflator at all** — so **`c` alone carries the whole cross-pair deflator** — though not the whole of the effective-N arithmetic: the
clock residual and `OVERLAP_PER_RECORD_PROVENANCE_UNBOUND` are freedoms outside `c`.
`c` is the last unruled **decision packet**, which is a different statement. The **span is committed and closed** — DESIGN only,
never validation or holdout, frozen once and recorded — and the packet does not
reopen it. Everything between the symbol and the span is unregistered: the **pair
set** (NR-L1), the **statistic** and its entry set (NR-L2), the **series** (NR-L3),
**day attribution** (NR-L4), **idle days** (NR-L5), **undefined pairwise cases**
(NR-L6), and the **calculation, freeze and record moments** (NR-L7). Two findings
make it sharper than it looks: **no correlation is computed anywhere in the M15
package**, and **the object the definition names — a per-pair daily PnL series — has
no constructor in this repository**, the nearest committed function summing *across*
pairs into one portfolio series. The adversarial route is named:
`KEEP_P_20_BUT_COMPUTE_C_ON_A_FAVOURABLE_SUBSET`, since `P` is pinned while `c`
carries no pair-set identity in the call or the record. And it has a hard dependency —
`NR_L_DAY_ATTRIBUTION_DEPENDS_ON_Q10_I`: NR-L3 and NR-L4 cannot close before Q10(i),
because both run on the same daily series, and closing them implicitly would settle
the Sharpe series' day rule by the back door.

**§8.5.0 records a human + ChatGPT ruling that closes Q10(i) and NR-L as one
decision** — bundled precisely because that dependency makes them inseparable.
**`Q10_I_RULED_REALIZED_PNL_ATTRIBUTED_TO_EXIT_UTC_DATE`**: a trade's **entire**
realised PnL is attributed to the UTC calendar date containing its registered **exit**
marker, with no split across dates, no mark-to-market allocation over intervening
days, and no entry-day back-attribution. Committed authority did not decide it —
Q10(ii) fixes what a day *is*, and prereg §9's "(as in M1)" carries the **aggregation
shape**, not the attribution rule, on a reading that prereg §11's "reusable **after
audit/wrapping**" would otherwise be defeated by. **The repository's only two
`MetricTrade` constructors take the entry marker**, so the ruling departs from every
constructor that exists, and that is stated rather than buried. It reaches **seven**
quantities through `MetricTrade.day` — `c`, the daily Sharpe, max drawdown and daily
coverage at holdout, **plus** the validation daily Sharpe that selects the operating
point, so it can change which operating point reaches the holdout and whether the
holdout is reached at all. *§8.7.5 has since ruled turnover onto the **entry** date, so
it is no longer among them and the count is **five**, not seven; the validation binding
of `Q10_I_MUST_NOT_BE_RESELECTED_AFTER_OBSERVING_ANY_METRIC_IT_MOVES` now rests on the
validation Sharpe alone, and §8.7.5 supplies turnover's own lock.* It **loosens no frozen threshold**: it fixes a measurement convention,
outcome-blind, before any of those quantities is observed — on the **weaker** footing
of outcome-blindness rather than the shown *tightening* §8.2.0 established for the
same manoeuvre, and it does **not** define the `≤ 40 trades/day` ceiling's day, which
Ruling Q10(ii) leaves unruled.

**And `c` is fully specified.**
**`NR_L_MINIMUM_RESEARCH_CONTRACT_RULED_PENDING_IMPLEMENTATION_AND_DESIGN_MEASUREMENT`.**
`c = mean_{p<q} |r_pq|` — **equal-weight Pearson** over the **190** unordered
off-diagonal entries of the frozen **`PAIRS_20`**, on per-pair daily **net realised**
PnL at `PRIMARY_COST_CELL_PIPS`, attributed by Q10-i, aligned to **one common complete
DESIGN UTC calendar-date index** (2025-04-25…2026-02-28, **310 dates**) on which an
**idle pair-date carries zero**, **failing closed** on any undefined required entry —
never dropped, never substituted — measured **once** on the **full** DESIGN span,
method frozen now and never reselected after any downstream observation. **Three
limbs are derived**: the universe, the coefficient/entry-set/weighting, and the cost
layer all fall out of the equicorrelated identity `1 + (P−1)ρ̄` and the committed
dependence note. The rest are human + ChatGPT choices, and **two of them run against
conservatism and are recorded as such** — idle zero-fill **dilutes** `|r|` in the
sparse regime this family expects, and equal weighting is exact only under an
equal-variance assumption §0.6 records as false for `PAIRS_20`. **No `c`, no
correlation matrix, no daily PnL and no `N_eff` is calculated, and no data is read.**
What remains is implementation and checkability —
`C_INDEX_SET_NOT_RECORDED_IN_ANY_ARTIFACT` (deferred, though §5's **R-6 lightweight
record** is not), `NR_L_PAIRWISE_COMPLETENESS_IMPLEMENTATION_PENDING`,
`C_HAS_NO_PRODUCER_AND_NO_ARTIFACT` and
`EXIT_DAY_ATTRIBUTION_BREAKS_ONE_COMMITTED_TEST_FIXTURE` — plus
`MINIMUM_CALENDAR_IDENTITY_RECORD_REQUIRED_BEFORE_DATA_EXECUTION`, Ruling ω-13's
residual 5 carried forward unchanged as a **future execution prerequisite** and
**not** reopened. **One NR-L Minimum Research Gate blocker survives and is named
rather than closed — **and then closed by Ruling c-10**.
**`NR_L_GENERATING_CONFIGURATION_NOT_REGISTERED`**: c-1…c-9 fixed how `c` is computed
from a series and **not which DESIGN-span configuration produces that series**. §4's
**R-10** forbids taking such a quantity "from an exploratory variant chosen after its
results were seen", names `mean_abs_pairwise_corr` as its **sharpest case**, and hands
the remedy to "the design audit and gate 3a, which own it".

**Ruling c-10 is gate 3a exercising that disposition.**
**`NR_L_C_PRECOMPUTED_FOR_ALL_REGISTERED_CONFIGURATIONS_BEFORE_VALIDATION_SELECTED_BY_CONFIG_ID_ONLY`**
— a DESIGN-only `c_design[config_id]` for **every** preregistered candidate, computed
before any validation observation; the complete map **frozen**; the committed
validation rule then selecting one `config_id`; the frozen `c` attached mechanically.
The permitted direction is **validation result → `config_id` → frozen `c`**, never
`c → configuration`; `c` may not become a tie-breaker, and Ruling 9's tie rule
(**smallest passing `ev_min`**) is already committed and blind to it; and there is no
post-selection recomputation. An undefined `c` makes a candidate **ineligible to be
selected** and does **not** delete it from the registered set. The map's key set must
equal the registered candidate set, which is a **contract property**, with
`NR_L_CONFIGURATION_COVERAGE_IMPLEMENTATION_PENDING` carried as implementation.

**And it corrects this document's own premise.** §8.5.0's "three thresholds **and**
three `ev_min` points, nine configurations" imported the **M1** threshold grid;
prereg Ruling 9 forbids a raw probability threshold as a decision rule, and the
registered set is **three `ev_min` points and one horizon — three configurations**.
The blocker survived the correction, narrowed, and c-10 closes it.
The two blockers that survived c-10 are **closed by §8.7**: **c-11** rules the
DESIGN-span generation semantics (leakage-safe, with Rulings c-6 and c-7 **unamended**),
and **c-12** freezes every decision-bearing input and resolves the Calendar B collision
by **scope** rather than schedule.
**`CLOSURE_CLAIM_WITHHELD`** — attempted a **third** time at §8.7.6 and grounded on a review section that did not yet exist; withheld then under **`CLOSURE_CLAIM_REQUIRES_COMPLETED_REVIEW_AND_NO_UNRESOLVED_MATERIAL_BLOCKER`** (§8.8.0 — the earlier same-round prohibition is **withdrawn as over-broad**). *The separate independent round has since run: §12.17 records **full coverage on the assigned scope, both roles returning**, so that rule's review condition is now **met**. Closure is still **NOT** taken, on a different ground — §8.9.6 records **seven live material blockers**, and **`M15_MINIMUM_RESEARCH_STATISTICAL_CONTRACT_NOT_CLOSED_MATERIAL_BLOCKERS_LIVE`**.*

**The recorded order** (§8.2.8, §8.3.11): NR-K **ruled** → mean-overlap clock,
formula and aggregation **ruled** → **NR-L + Q10(i) ruled** → **Q10(iii) ruled**
(§8.7.4/§8.8.4/§8.9.2) → duration-boundary
arithmetic → the exact
`T_v`/`T_h`/`D` declaration → the remaining Minimum Research Gate questions
(Q1, Q8, FR-19 and the rest of §8) → **and only after every *other* minimum-gate
requirement is resolved may execution authorisation be considered at all.**

**Unchanged by these rulings:** the Zero-Data verdict
`SAMPLE_FLOOR_REACHABILITY_NOT_DETERMINABLE_WITHOUT_MEASURED_INPUTS` — **the ω ruling
does not move it either**, since its three inputs are still empirical and the ruling
fixes only how one of them is computed, not its value — **and the NR-L ruling does
not move it either**, for the same reason: `c`'s method is fixed, its **value** is
not measured, and §0's three inputs stay empirical; Q1 (`REQUIRED_NOW`, default (b));
**Q8**, unruled; FR-19, open; and `N = 1`, which a post-freeze rerun may not be
laundered into reopening. *(An earlier drafting listed **Q10(iii)** here; it is ruled at
§8.7.4 and its **value** was never among §0's inputs, so the Zero-Data verdict is
unmoved either way.)*

**And unchanged in the strongest sense:** real-data read, derivation, training,
evaluation, holdout, broker execution, formal Gate-3a continuation and evidence
promotion are **all still unauthorised**. Neither ruling recorded here authorises
any of them, and neither may be cited as a step toward one.

**Q1 blocks the gate from being useful without a ruling**, and Q2–Q11 are genuine
choices. An AI may not settle them: Q1 in particular decides whether M15 research
can begin before the deferred production dependencies are paid for, which is the
question this gate exists to put — and it now carries the amendment cost of each
option rather than presenting three as free.

**One correction to the earlier draft's own scoping claim.** It said only Q1
blocks. That was wrong by one item: **Q7 blocks R2–R4** and does not block R0–R1,
because ruling those stages with the iteration budget blank grants an unbounded
budget by omission. Q7 now carries a derived fail-closed default, which converts
it from a blocker into an ordinary ruling item.

**The zero-data feasibility question has now been answered, and the answer is
"undetermined".** §0 performs the derivation as arithmetic over committed
constants — nothing executed, nothing read. An earlier version of this packet
called it "the cheapest decisive thing in the whole packet" and expected it might
make Q1 and Q3 unnecessary. **That expectation is withdrawn**: three inputs are
empirical, not two; an honest grid spans roughly 25 weekday days to over a decade;
and a range that wide moots nothing.

What survives is narrower and still useful. The derivation **refutes the reverse
claim** — that the floors are comfortably reachable at the frozen 2-month
minimum — and it re-derives, rather than discovers, the corridor gate 4 already
recorded as "intentionally demanding but narrow" with "adopt more forward data" as
its pre-blessed remedy. It also converts the question into one a human can rule
on: what forward-accrual date does each corner imply, against a committed earliest
adoption of ≈ 2026-10?

**Q1–Q11, classified.** Every item in §8 is by construction human-ruled; the
classification records the *primary* disposition and what changes if the
zero-data derivation had come out infeasible.

| Q | Disposition now (verdict: undetermined) | If family A were infeasible |
| --- | --- | --- |
| **Q1** derivation-artifact precondition | **REQUIRED_NOW** · default **(b)** is `DERIVABLE_FROM_COMMITTED_AUTHORITY`; departing from it `REQUIRES_HUMAN_CHATGPT_RULING` | MOOT |
| **Q2** pair set | `DERIVABLE_FROM_COMMITTED_AUTHORITY` — default `PAIRS_20` | MOOT, but **sensitive**: infeasibility invites widening the universe, which R-2a bars and which §0.6 shows is not the free win it looks like |
| **Q3** dataset, and whether reading may begin | `REQUIRES_HUMAN_CHATGPT_RULING` (Red, policy §6); the reader limb is `DEFERRED_TO_PRODUCTION` (PR #450 §10 row E) | MOOT |
| **Q4** historical period | `DERIVABLE_FROM_COMMITTED_AUTHORITY` — design span only | **Flips to `REQUIRES_HUMAN_CHATGPT_RULING`, and dangerously**: infeasibility pushes directly at a wider epoch, which Ruling 2 non-authorises. Nothing in §0 is an argument for one |
| **Q5** exploratory cost model | `DERIVABLE_FROM_COMMITTED_AUTHORITY` | exploratory limb MOOT; the cost tables persist as a `DEFERRED_TO_PRODUCTION` T-6 item |
| **Q6** initial model family / R2-before-R3 | `DERIVABLE_FROM_COMMITTED_AUTHORITY` — Ruling 8 freezes the family and §7 settles the sequencing; barely a live question | MOOT |
| **Q7** iteration budget | `DERIVABLE_FROM_COMMITTED_AUTHORITY` for `N = 1`; `REQUIRES_HUMAN_CHATGPT_RULING` only to raise. Blocks R2–R4 | MOOT |
| **Q8** where exploratory outputs live | **REQUIRED_NOW** · `REQUIRES_HUMAN_CHATGPT_RULING` — and it blocks **any stage that writes, including R0** | mostly MOOT while the work is doc arithmetic; live the moment anything is written |
| **Q9** C-7 budget | `REQUIRES_HUMAN_CHATGPT_RULING`; narrower reading now in force as the default | exploratory limb MOOT; survives for family B |
| **Q11 + §0** — at what holdout length the Sharpe criterion discriminates, whether the adopted span must reach it, and when `D` is fixed | **PARTLY RULED** (§8.1.0) · `Q11_AND_SECTION0_RULED_ON_FREEZE_SEMANTICS`. **Ruled:** two months is a floor; `D` frozen once at the forward-epoch continuation before any data; no post-freeze reselection. **Not ruled:** the discriminating length (no committed α), whether `D` must reach it, and the exact numeric `D` (Q10) | **survives** — the unruled limbs |
| **Q10-A** in what unit is `D` measured | **RULED** (§8.2.0) · `Q10_A_RULED_ELAPSED_UTC_CALENDAR_SPAN` — elapsed calendar span on the UTC clock; not weekday, trading-day, eligible-day, event or bar counts. A **derivation** from committed text. The month-arithmetic boundary question stays open as a narrow downstream item (§8.2.3) | n/a — ruled |
| **Q10(ii)** the coverage-denominator day | **RULED** (§8.2.0) · `Q10_II_DAY_IDENTITY_RULED_UTC_CALENDAR_DATE_EXPECTED_SLOTS_FROM_APPROVED_CALENDAR_AUTHORITY` — day identity = UTC calendar date; expected slots **only** from the approved calendar authority. Does **not** make all 96 slots of a date expected, and authors no weekend/holiday/closure/DST rule | n/a — ruled |
| **Q10-B** how the continuation window is anchored | **RULED** (§8.2.0) · `Q10_B_RULED_EXPLICIT_HUMAN_CHATGPT_UTC_WINDOW_DECLARATION_REQUIRED_BEFORE_CONTINUATION` — exact `T_v`/`T_h`/window/`D` declared by human + ChatGPT **before** continuation authorisation; a list of data-derived anchors forbidden. A **tightening**, not an amendment | n/a — ruled |
| **Q10(i)** entry- vs exit-day PnL attribution | **RULED** (§8.5.0) · `Q10_I_RULED_REALIZED_PNL_ATTRIBUTED_TO_EXIT_UTC_DATE` — the whole realised PnL to the UTC date of the registered **exit** marker. It was **not** settled by Q10(ii): fixing what a day *is* does not fix which day a horizon-straddling trade lands on. *An earlier drafting of this row read `REQUIRES_HUMAN_CHATGPT_RULING`; withdrawn.* Turnover is **not** governed by it — §8.7.5 rules turnover onto the **entry** date | n/a — ruled |
| **Q10(iii)** annualisation factor | **RULED** (§8.7.4) · `Q10_III_RULED_COMPLETE_UTC_CALENDAR_DATE_SHARPE_INDEX_IDLE_ZERO_ANNUALISED_BY_SQRT_365` — complete UTC calendar-date index, idle = zero, Q10(i) attribution, **`√365`**; maxDD provably invariant, coverage and turnover untouched. Not settled by Q10-A: the unit of `D` and the constant annualising a daily Sharpe are different objects. The only committed authority is prereg §9's "ann., UTC-day"; `√252` is **M1 precedent**, and the committed Sharpe series was indexed on **active dates**, so `√252` matched neither clock | **ruled** |
| **Exact `D`** | `EXACT_D_SELECTION_STILL_PENDING_UPSTREAM_AUTHORITIES` — ordering recorded at §8.2.8: NR-K (**ruled**), the **mean-overlap unit and aggregation** (**ruled**, §8.4.0), **NR-L + Q10(i)** (**ruled**, §8.5.0/§8.7/§8.8/§8.9 — contract ruled, implementation and the DESIGN measurement pending, and two generator blockers live), **Q10(iii)** (**ruled**, §8.7.4), then the remaining duration authority — the boundary arithmetic and endpoint convention — then the human + ChatGPT window declaration, then the remaining minimum-gate questions. *An earlier drafting read "then **NR-L** (§8.5, next)"; withdrawn* | **survives** |
| **Gate-3a continuation date** (the **forward-epoch adoption** continuation, not the design-span one) | `GATE3A_CONTINUATION_DATE_NOT_FROZEN_RESIDUAL_AFTER_Q11_SECTION0_RULING` — **carried by Q10-B, ruled at §8.2.0** (its packet is §8.2.4), discharging
§8.1.9's "put it with Q10" — narrowed by the forbidden-anchor list, though no
latest bound is set. Already constrained by §8.1.0 (the date may not be informed by any strategy-run quantity); unconstrained as to a *positive* selection rule | survives |
| **NR-K** `P` and the pair universe | **RULED** (§8.3.0) · `NR_K_RULED_P_EQUALS_FROZEN_REGISTERED_FAMILY_A_UNIVERSE` — `P = 20` for current Family A, the authority object being the frozen registered `PAIRS_20` universe; `MUST_RESOLVE_BEFORE_ANY_EFFECTIVE_N_VERDICT` **discharged for NR-K**. It was **not derivable**: the one committed definition ("contributing") was undefined, and the implementation accepted `len(records) ≥ 1`. What survives is the **implementation pin** (`P_AUTHORITY_RULED_IMPLEMENTATION_COMPLETENESS_PIN_PENDING`) and the missing forward roster gate — `assert_full_coverage` halts an uncertifiable pair on the **design span only**, while `P` decides at holdout (`NO_FORWARD_SPAN_FULL_ROSTER_COVERAGE_GATE_COMMITTED`) | ruled; residuals survive |
| **Mean overlap fraction** `ω` — clock, formula, aggregation, freeze | **RULED** (§8.4.0) · `MEAN_OVERLAP_RULED_EVENT_LEVEL_SAME_HORIZON_CLOCK_EQUAL_WEIGHT_ROLE_LOCAL` — `g` and `H` on the **same registered M15 prediction clock**; `overlap_i = max(0, 1 − g_i/H)` per **adjacent** same-pair interval, then an **equal-weight arithmetic mean** (`E[f]`, never `f(E)`); the mean-gap approximation is **not an allowed authority**; `rho_h` **pair-local**, pooling forbidden; registered pair labels may not be rearranged; zero-event pairs contribute nothing and are **retained in `P`**; a one-event pair takes `ω_p = 0` with raw contribution **one**; **method frozen pre-data, value measured role-locally**; measurement may decide the verdict but may **not** redirect the experiment. **Four limbs derived and confirmed, six explicit human + ChatGPT choices.** Residuals: `HORIZON_WALL_CLOCK_EXTENT_NOT_REGISTERED` (reduced to one unknown binding `g` and `H` alike), `OVERLAP_PER_RECORD_PROVENANCE_UNBOUND`, the implementation pin, and `MEAN_OVERLAP_AMENDMENT_CLASSIFICATION_NOT_SETTLED` | ruled; residuals survive |
| **NR-L** `mean_abs_pairwise_corr` — pair set, statistic, series, day attribution, idle days, undefined cases, common date alignment, freeze — **bundled with Q10(i)** | **RULED** (§8.5.0) · `NR_L_MINIMUM_RESEARCH_CONTRACT_RULED_PENDING_IMPLEMENTATION_AND_DESIGN_MEASUREMENT` · `Q10_I_RULED_REALIZED_PNL_ATTRIBUTED_TO_EXIT_UTC_DATE`. `c = mean_{p<q} |r_pq|`, equal-weight **Pearson** over the **190** unordered off-diagonal entries of the frozen `PAIRS_20`, on per-pair daily **net realised** PnL at the primary cost cell, attributed to the **exit** UTC date, on **one common complete DESIGN UTC calendar-date index** (310 dates) with **idle = zero**, **failing closed** on any undefined required entry, measured **once** on the full DESIGN span, method frozen now, never reselected after a downstream observation. **Two limbs derived-under-a-stated-reading** (c-1 and c-2, from the equicorrelated identity the committed form is — an identity that appears in **no** committed source, so the reading is this ruling's), the rest human + ChatGPT choices — **three of which run against conservatism or are unestablished** (c-7's mechanism, c-2's false equal-variance assumption, c-6's common-idle frame). **The one blocker that survived — `NR_L_GENERATING_CONFIGURATION_NOT_REGISTERED` — is closed by Ruling c-10**: `c_design[config_id]` for **every** registered candidate (three `ev_min` points, not the nine §8.5.0 wrongly claimed), computed before validation, map frozen, `config_id` selected by the committed rule alone, `c` attached mechanically, no post-selection recomputation. The two blockers that survived it — `C_DESIGN_SPAN_RUN_IN_SAMPLE_STATUS_NOT_REGISTERED` and `C_MAP_INPUT_FREEZE_CONFLICTS_WITH_T6_HOLIDAY_CALENDAR_SCHEDULE` — are **closed by §8.7's c-11 and c-12**, and **`CLOSURE_CLAIM_WITHHELD`** — attempted a **third** time at §8.7.6 and grounded on a review section that did not yet exist; withheld then under **`CLOSURE_CLAIM_REQUIRES_COMPLETED_REVIEW_AND_NO_UNRESOLVED_MATERIAL_BLOCKER`** (§8.8.0 — the earlier same-round prohibition is **withdrawn as over-broad**). *The separate independent round has since run: §12.17 records **full coverage on the assigned scope, both roles returning**, so that rule's review condition is now **met**. Closure is still **NOT** taken, on a different ground — §8.9.6 records **seven live material blockers**, and **`M15_MINIMUM_RESEARCH_STATISTICAL_CONTRACT_NOT_CLOSED_MATERIAL_BLOCKERS_LIVE`**.* `MUST_RESOLVE_BEFORE_ANY_EFFECTIVE_N_VERDICT` **discharged as to the contract**, not as to the value. Residuals: `C_INDEX_SET_NOT_RECORDED_IN_ANY_ARTIFACT` (deferral **contested**, and the R-6 record now has to name the index's cardinality and the 190-entry count, because **bounds alone cannot discriminate**), `NR_L_PAIRWISE_COMPLETENESS_IMPLEMENTATION_PENDING` (every short roster **raises** `N_eff`), `C_HAS_NO_PRODUCER_AND_NO_ARTIFACT`, `EXIT_DAY_ATTRIBUTION_BREAKS_ONE_COMMITTED_TEST_FIXTURE` and `EXIT_DAY_ATTRIBUTION_REQUIRES_A_NEW_DAY_MAP_AT_THE_SECOND_CALL_SITE`, and five accepted costs of the ruled construction. *As the packet stood before the ruling:* seven questions, none answered. With `P` and `ω`'s method ruled, `rho_x = 1 + 19c` makes **`c` the whole of the cross-pair deflator**, and the last unruled decision packet — not the last freedom in the arithmetic. The **span is committed and closed** (DESIGN only, never validation/holdout, frozen once); everything between the symbol and the span is unregistered, and **the object the definition names — a per-pair daily PnL series — has no constructor in this repository**. Hard dependency: `NR_L_DAY_ATTRIBUTION_DEPENDS_ON_Q10_I`, so NR-L3/NR-L4 could not close before Q10(i) — which is why the two were ruled as **one** decision. Its earlier role in sizing `D` remains **mooted** by Ruling B | ruled; residuals survive |

**Q10 and Q11 are the only two that survive an infeasibility verdict**, which is
itself the argument for having taken the derivation first. **Q11 and §0 are one
referral with two limbs**, not two: the same frozen 2-month minimum, questioned in
the sample-count dimension and the Sharpe-precision dimension, with the same
remedy — **a longer `D`, fixed at the gate-3a continuation before any validation or
holdout computation, never an extension of a span that has been measured**. §8.1
is that referral.

**They are not symmetric in consequence, and the ruling must be told so.** §0's
limb has a named verdict (`INSUFFICIENT_SAMPLE`) and a closure clause — scoped
"before any holdout touch". Q11's limb has **neither**. A ruling that supplies a
remedy only for the counts limb would leave the Sharpe limb with no verdict, no
remedy and no closure, silently standing — which is exactly the outcome merging
them prevents.

**And the earlier scoping claim is short by two, not one.** It said only Q1 blocks;
the previous revision added Q7 (blocks R2–R4). Q8 also blocks every stage that
writes, **including R0**, because §3.7 permits writes only beneath a named
research-scratch root and §9 reserves naming it to a Contract Gate-decision.
