# Phase 9.X-B Amendment — Re-ranking under causal multi-TF (post Phase 9.X-E)

**Status:** RECORD-ONLY. No implementation change recommended at this time.
**Date:** 2026-04-26.
**Trigger:** Phase 9.X-E/L-2 v19 causal-fix eval revealed that the original Phase 9.X-B winner (+mtf, claimed Sharpe 0.174) was inflated by a multi-TF lookahead bias of ~9%. This memo re-ranks the four Phase 9.X-B cells against the corrected anchor and records false-negative candidates for future reference.

---

## What changed

The Phase 9.X-B closure (`docs/design/phase9_x_b_closure_memo.md`) was authored against pre-fix v18 outputs. The +mtf cell appeared to dominate by a clear margin:

| Cell (v18, pre-fix) | K=3 Sharpe | K=3 PnL | DD%PnL |
| ---                 | ---        | ---     | ---    |
| +mtf alone          | **0.174**  | 15,118  | 1.8%   |
| +vol alone          | 0.160      | 10,385  | 3.3%   |
| +moments alone      | 0.157      | 9,650   | 2.7%   |
| +all (vol+moments+mtf) | 0.156   | 11,428  | 2.8%   |

After Phase 9.X-E/L-1 fixed the lookahead in `_add_multi_tf_extended_features` (only the mtf-using paths were affected), the v19 re-run produced:

| Cell (v19 causal where applicable) | K=3 Sharpe | K=3 PnL | DD%PnL | Bug-affected? |
| ---                                | ---        | ---     | ---    | ---           |
| **+mtf v19 causal**                | 0.158      | 11,414  | 2.1%   | now causal    |
| +vol alone                         | **0.160**  | 10,385  | 3.3%   | never affected |
| +moments alone                     | 0.157      | 9,650   | 2.7%   | never affected |
| +all (still has mtf bug at K=3)    | 0.156      | 11,428  | 2.8%   | still inflated |

(Cells without mtf in `enable_groups` were never bug-affected; their numbers are unchanged from the original Phase 9.X-B run.)

---

## Re-ranking under each judgment frame

### PnL-priority frame (Phase 9.15-established default)

The Phase 9.X-B closure used this frame. Re-running with v19:

| Rank | Cell | PnL | Δ vs Phase 9.16 baseline (~10,990 K=1) |
| ---  | ---  | --- | ---                                  |
| 1    | +mtf v19 causal | 11,414 | +3.9% |
| 2    | +all (still bug) | 11,428 | +4.0% (would drop after fix) |
| 3    | +vol | 10,385 | -5.5% |
| 4    | +moments | 9,650 | -12.2% |

**Verdict under PnL-priority: +mtf still wins.** Even after the inflation correction, +mtf retains the highest causal PnL among single-group cells. Production wiring (Phase 9.X-B/J-5, PR #223) remains the right ship.

### Sharpe-priority frame

| Rank | Cell | Sharpe |
| ---  | ---  | ---    |
| 1    | **+vol** | **0.160** |
| 2    | +mtf v19 causal | 0.158 |
| 3    | +moments | 0.157 |
| 4    | +all (still bug) | 0.156 |

**Verdict under Sharpe-priority: +vol becomes the winner**, by a thin margin (Δ = +0.002).

### DD-efficiency frame (PnL / DD)

| Rank | Cell | DD%PnL |
| ---  | ---  | ---    |
| 1    | +mtf v19 causal | 2.1% |
| 2    | +moments | 2.7% |
| 3    | +all | 2.8% |
| 4    | +vol | 3.3% |

**Verdict: +mtf has the cleanest drawdown profile.** +vol's slightly higher Sharpe comes with notably worse DD efficiency.

---

## False-negative candidate

**+vol** is the lone false-negative candidate from Phase 9.X-B. The original closure dismissed it as "worse than mtf"; under the corrected anchor it ties or marginally beats mtf on Sharpe alone.

Why we are NOT switching production to +vol now:

1. **PnL is lower** (-9.9% vs causal mtf, -5.5% vs Phase 9.16 baseline). PnL-priority remains our default frame per Phase 9.15.
2. **DD efficiency is materially worse** (3.3% vs 2.1%). Drawdown is a live-money concern, not just a backtest metric.
3. **The Sharpe gap is razor-thin** (Δ = +0.002, well within run-to-run noise). The signal does not warrant invalidating an in-flight production rollout.
4. **Trade count is lower** (-17%), which is unhelpful for OANDA volume requirements (Phase 9.X-F runs separately, but lower alpha trade count means more reliance on the volume runner).
5. **No theory** for why volatility-clustering features would be a structurally better signal than slow-cadence multi-TF features. The existing `+mtf` story (h4/d1/w1 regime context) has a clearer mechanism.

---

## When +vol becomes worth re-opening

- **Phase 9.11 robustness gate (Sharpe ≥ 0.20)**: if we shift the judgment frame to Sharpe to clear that gate, +vol moves to top-1 candidate. A combined `+mtf+vol` test (orthogonality check) would be the natural first move.
- **Multi-strategy weighting**: if the signal-mix scheme weights by Sharpe rather than PnL, +vol's higher Sharpe earns more allocation.
- **Live-paper divergence**: if Phase 9.X-B/J-5 production data shows live PnL falling below the causal v19 backtest (i.e. another inflation source), +vol becomes a fall-back default.

---

## Other phases — re-checked, all stand

| Phase | Verdict | Bug-affected? | Stands? |
| ---   | ---     | ---           | ---     |
| 9.4-9.13 (TA / cost / labels / kill switches) | various | NO | ✅ stand |
| 9.15 spread+RH | spread bundle GO | NO | ✅ stand |
| 9.16 20-pair | 20p v9 spread default | NO | ✅ stand |
| 9.17 ensemble (MR/BO) | NO ADOPT (trade-rate explosion) | NO | ✅ stand |
| 9.17b conf threshold | NO ADOPT (per-trade EV is binding) | NO | ✅ stand |
| 9.19 Top-K | PARTIAL GO at K=2 | NO | ✅ stand |
| 9.X-A regression labels | NO ADOPT (Sharpe 0.092) | NO | ✅ stand |
| 9.X-C/M-1 LSTM Mode A | NO ADOPT (Sharpe 0.061) | NO | ✅ stand |
| 9.X-D +dxy alone | NO ADOPT (Sharpe 0.154) | NO | ✅ stand |
| 9.X-D +dxy+mtf | NO ADOPT (Sharpe 0.168 → causal ~0.152) | YES (mtf path) | ✅ still NO ADOPT |
| 9.X-B +mtf | PARTIAL GO+ (now Sharpe 0.158) | YES | ✅ still PARTIAL GO (PnL-priority) |
| 9.X-B +vol | NO ADOPT | NO | ⚠️ FALSE NEGATIVE under Sharpe-priority |
| 9.X-B +moments | NO ADOPT | NO | ✅ still NO ADOPT (tied with mtf, lower PnL) |
| 9.X-B +all | NO ADOPT | YES | ✅ still NO ADOPT |

---

## Action items

- [x] Record +vol as a Phase 9.11 candidate in this memo.
- [x] Master tip post-amendment: 74303ef (PR #224 merged).
- [ ] When Phase 9.11 robustness work begins, run a `+vol` 20-pair eval as anchor and test `+mtf+vol` orthogonality. Estimated 2 hours of compute.

---

## Files

- Closure (original): `docs/design/phase9_x_b_closure_memo.md`
- Lookahead fix: `scripts/compare_multipair_v19_causal.py`
- v19 result log: `artifacts/phase9_x_e_mtf_causal.log`
- Original cell logs: `artifacts/phase9_x_b_{vol,moments,mtf,all}.log`
- Production wiring: `src/fx_ai_trading/services/feature_service.py` (FEATURE_VERSION v3)
