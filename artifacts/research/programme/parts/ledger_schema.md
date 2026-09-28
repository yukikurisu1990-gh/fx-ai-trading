# Programme evidence ledger — extraction schema

Output: a JSON file (UTF-8) containing a list of row objects. One row per **measured result** (a track × span × variant that has a recorded result). Use `null` for any value not present in the source. **Never infer, estimate, recompute from returns, or guess a number.** Every numeric value must come from a recorded artifact or a results document, and `source` must say exactly where (file path + JSON key path or document section/table).

Fields (all required keys; values may be null):

- `track_id`: short unique id, e.g. "TOP5_T1_long", "R1_F3_S2", "NF_U2_long".
- `cycle`: programme cycle name, e.g. "Exploratory Round 1", "Top-Five", "next-five", "mechanism redesign".
- `pr`: PR number(s) as string, e.g. "#490".
- `family`: economic family (e.g. "carry", "momentum", "reversal", "rates repricing", "valuation", "flow", "risk-off", "macro momentum", "clock/fix", "liquidity", "ML model", ...).
- `hypothesis`: one-line exact hypothesis as frozen/recorded.
- `mechanism`: one line.
- `information_source`: e.g. "FX prices only", "BIS policy rates", "US TIC", "ALFRED CPI/unemployment".
- `price_only`: true if the signal uses only FX prices, false if external data.
- `book_type`: "CROSS_SECTIONAL" | "USD_FACTOR" | "PAIR_LEVEL" | "OTHER".
- `span_label`: e.g. "long", "recent", "development", "supplemental 2023-04-26..2025-04-24".
- `span_dates`: "YYYY-MM-DD..YYYY-MM-DD" if recorded.
- `calendar_years`: number if recorded (or derivable directly as recorded days/252 only if the source states days and says daily — else null).
- `effective_n`: recorded effective independent observations / regimes (null if not recorded).
- `event_count`: for event studies (null otherwise).
- `gross_annual_return`, `gross_sharpe`.
- `tc_adjusted_annual_return`, `tc_adjusted_sharpe`: the recorded "net" after transaction costs. If the recorded net ALSO includes an approximate carry/markup, put it here and set `financing_included` accordingly.
- `financing_included`: "NONE" | "APPROXIMATE_CARRY_AND_MARKUP" | "RESEARCH_CARRY_POLICY_RATES" | "OTHER".
- `financing_type`: free text.
- `turnover`: recorded turnover (state unit in notes).
- `annual_cost`.
- `ic`, `incremental_ic`.
- `null_percentile`, `p_value`: from a recorded null/permutation test for this row (null if none).
- `stability`: e.g. positive blocks "40/70" or fold results (string).
- `loo_worst`: worst leave-one-currency-out net Sharpe if recorded.
- `concentration_top10`: top-10-day contribution if recorded.
- `max_dd`.
- `result_status`: the verdict/status token exactly as recorded (e.g. "U1_S29_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT", "FAILED", "UNRESOLVED").
- `is_primary`: true if this row is the pre-registered primary test of its hypothesis; false for secondary spans, sensitivities, diagnostics.
- `preregistered`: true if the hypothesis/parameters were frozen before the result was seen.
- `post_result_correction`: true if this row comes from a run re-done/corrected after results were seen.
- `invalid`: true if the record was later declared INVALID/superseded (e.g. next-five run2, mechanism redesign M15/M16).
- `variant_type`: "DISTINCT_MECHANISM" | "SIGN_VARIANT" | "HORIZON_VARIANT" | "MODEL_VARIANT" | "UNIVERSE_VARIANT" | "SENSITIVITY" | "SECONDARY_SPAN" | "POST_HOC_DIAGNOSTIC" | "REPLICATION" | "BENCHMARK".
- `variant_of`: track_id of the base hypothesis if this is a variant (else null).
- `protected_data_caveat`: text or null (e.g. OOS row decode incident, D-5, D-M3).
- `closure_scope`: what the result closes, as recorded (text or null).
- `source`: exact file path(s) and key path(s)/section.
- `notes`: anything needed to interpret (units, caveats). Keep short.

Rules:
- Read-only. Do not run any backtest, driver, acquisition, or network. Do not compute P&L/Sharpe/IC from returns. You may run small Python snippets only to read JSON files and print values.
- If a cycle reports many strategies only as a summary (e.g. "8 families / 26 strategies all net negative") without per-strategy numbers available anywhere in the repo, emit one row per strategy only if per-strategy numbers are recorded; otherwise emit a single SUMMARY row with the recorded counts in notes and numeric fields null.
- Include INVALID / superseded runs as rows with `invalid: true`.
- Report in your final message: the path of the JSON you wrote, the row count, and any sources you could not find.
