# FXID_FRONTIER_EXPANSION — Track A（ORIGINAL_MECHANISM_DISCOVERY）の記録（2026-10-11）

**Role H（Hypothesis Architect）** の出力の記録。

- 別の context の agent で行った。
- **価格・return の data を読んでいない**: repo の既存の報告と、3 回の web 検索だけ。
- 使った cost と σ は、repo が既に報告した集計（Cycle 1 §11–§12、R-A2b §7–§11）だけ。
- 時刻: F0 の事前登録の commit（`53d5d9f`、2026-10-11T20:24:03+09:00）の後、2026-10-11T11:24:40Z（20:24:40 JST）に起動した。
- 指示の文面は §6 に逐語で残す。§1〜§5 は Role H の出力のまま。lead の訂正と開示は §7 にまとめる（本文は書き換えない）。

## 1. 市場の配管の地図（ET、夏時間 / 冬時間）

| ET | 出来事 | 動く balance sheet | 理由 | 既存の inventory |
| --- | --- | --- | --- | --- |
| 17:00 | rollover / value date の roll | retail と PB の financing、LP | T+2 の roll、LP の quote の引き上げ（約 9.2 bp） | cost のみ |
| 日曜 17:00〜19:00 | 週の開始（Wellington / Sydney） | 週末の gap の risk を負う LP | 2 日分の news、薄い板 | 未登録（H-07） |
| 19:00 / 20:00 | 東京の開場 | 日本の銀行・輸出企業・投信の信託銀行 | 仲値に向けた顧客の注文 | F1 / F2 |
| 19:55 / 20:55 | 東京の仲値（9:55 JST） | 日本の企業・投信 / NISA・輸入企業（gotobi） | 契約と NAV が TTM で決まる | F1、F6 |
| 20:10 / 21:10 | 日銀の国債買入の通知（10:10 JST） | 日銀・国債のディーラー | 政策の実施 | 未登録（H-05） |
| 20:15 / 21:15 | 人民銀行の CNY の基準値（9:15 北京） | 本土の銀行・CNH のディーラー・Asia の代理（AUD / NZD） | 本土の取引の幅が基準値で決まる | 未登録（H-01） |
| 01:00〜03:00 | CLS の決済 | 決済銀行 | pay-in の期限 | #507 で不合格 |
| 03:00 | London の開場 | Asia の book・欧州の企業 | book の引き継ぎ | F2 / F10 / C03 |
| 02:00〜08:15 | 欧州の指標・ECB の参照 rate | EUR の企業・会計 | ECB の rate での請求と会計 | F1 の EUR の窓 |
| 08:00 / 08:30 / 10:00 | NY の開場・US の指標 | 全て | news | F7、#473（検出力のある帰無） |
| 10:00 | NY の option cut | option のディーラーの delta hedge | 満期の gamma | F11、M-PIN・M-GAMMA は不合格 |
| 11:00 | WMR の 4 pm fix | benchmark の運用者・index の hedge | 義務的な benchmark の執行 | F1、F4、F5 |
| 13:00 | US 国債の入札の結果 | primary dealer・海外の実需 | 金利の再評価 | 未登録（H-04） |
| 14:00（年 8 回） | FOMC | 全て | 政策 | CB premium は K8 で kill（#507） |
| 15:00 | CME の FX 先物の清算 | 先物の証拠金 | 変動証拠金 | M-FUT は不合格 |
| 月末・四半期末 | fix の rebalance・G-SIB / CIP の funding | hedge 付きの投資家・銀行 | hedge の再設定・window dressing | F4、C04 / C05 |
| 月初（2024 年以降） | NISA / 投信の積立の決済、翌日の TTM での換算 | 信託銀行経由の家計 | 目論見書が TTM での換算を求める | 未登録（H-02） |
| 6 月下旬・12 月上旬 | 日本の配当の海外の保有者への支払い | 海外の custodian | 本国通貨の mandate | 未登録（H-03） |

## 2. original な候補と Base の予測（data を使わない）

式: s = √(n·k) · (h·g − c) / σ。

| 記号 | 意味 |
| --- | --- |
| n | 年の機会 |
| k | 実効の breadth |
| g | haircut の前の gross（bp） |
| h | 直接の証拠が無いための haircut。Base 0.5、Optimistic 1（Optimistic は g も上の prior に変えている。§7 の 1） |
| c | retail の all-in の往復 |
| σ | 保有の窓の σ |

| ID | mechanism | 分類 | n × k | g | c | σ | **s_B** | Optimistic |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H-01 | CNY の基準値の surprise の Asia への伝達 | NEW_MECHANISM | 250 × 1.3 | 0.32 | 2.5 | 17 | **−2.48** | −1.96 |
| H-02 | 月初の投信の換算（東京の仲値） | NEW_INFORMATION_FOR_EXISTING_MECHANISM（F1 / F6） | 24 × 1 | 3 | 2.2 | 16 | **−0.21** | +1.16 |
| H-03 | 日本の配当の季節の円売り | NEW_MECHANISM | 10 × 1 | 4 | 2.2 | 30 | **−0.02** | +0.40 |
| H-04 | 国債の入札の結果 → USD | NEW_INFORMATION（F7）、方向が曖昧 | 100 × 1.5 | 0.4 | 1.9 | 11.6 | **−1.79** | −1.16 |
| H-05 | 日銀の買入の規模の surprise | NEW_MECHANISM | 6 × 1 | 7 | 3.0 | 40 | **+0.03** | +0.46 |
| H-06 | 公開の SDR の strike への pinning | NEW_INFORMATION（F11） | 100 × 2 | 0.8 | 2.35 | 22 | **−1.25** | −0.48 |
| H-07 | 週末の gap の流動性の反転 | **HORIZON_VARIANT（F9）**、進めない | 15 × 2.5 | 6 | 2.7 | 26 | **+0.07** | +1.48 |

- 共通の prior: price impact は約 3 bp / $1B（Evans–Lyons 2002 の 1996 年の値を、現在の厚みで約 10 分の 1 にしたもの）。分単位で価格の発見が終わる場合、M15 の entry で得られるのは 15〜25%。
- data を見ずに捨てたもの（行なし）: 週末の前のディーラーの持ち高の調整（F9 の DUPLICATE）、国債の利払いの換算（日次の取引量の約 0.03%）、CLS の pay-in（既に不合格）、IMM / MSCI の見直しの日（年 4 回以下）、くりっく 365 の建玉（M-RETAIL、既に不合格）、17:00 の rollover の歪み（約 9 bp の cost）。

## 3. ranking（F0 §4、最大 156）

| ID | 点 |
| --- | --- |
| H-02 | 112 |
| H-07 | 92 |
| H-05 | 85 |
| H-03 | 83 |
| H-01 | 81 |
| H-06 | 72 |
| H-04 | 70 |

## 4. power-first の gate（F0 §5）

| 候補 | s_B | PF1（≥ 0.58） | PF2 | PF3 | PF4 | 結果 |
| --- | --- | --- | --- | --- | --- | --- |
| 全 7 候補 | −2.48 〜 +0.07 | **×** | × | × | 一部 ○ | **全て不合格** |

**参考**: m = 0.58 での検出力は、S で約 0.35、E で約 0.43。

**F0 §5 の式の不整合**（Role H の指摘）:

- 本文の z_{1−0.10/V} と、例（V = 6 で 1.11、V = 3 で 0.98）が合わない。例は z_{1−0.05/V} に相当する。
- どちらの読み方でも、全ての候補は PF1 の段階で不合格なので、判定に影響しない。
- F0 は凍結した事前登録なので変えず、最終報告で erratum として記録する。

## 5. Role H の構造的な所見

| 種類 | 必要なもの |
| --- | --- |
| **日次の intraday の候補** | c/σ ≈ 0.06〜0.08 の下で s_B ≥ 0.76（PF2 の厳しい読み方）に届くには、0.5·g/σ ≥ 0.07 + 0.76/√250、すなわち g/σ ≥ 0.24（pair・日あたり）。cost が無い場合の gross の年率の Sharpe で、pair あたり約 3.8 |
| **比較** | 公表された最も強い intraday の FX の効果（KMW の fix の W 字）は、cost なしで 1.24〜1.82、CME の firm な気配で 0.52〜0.99 |
| **年 12〜24 回の event の候補** | 1 回あたり 10〜17 bp の残る gross が要る（σ ≈ 30 bp） |

**結論**: 直接の証拠が無い効果への 50% の haircut と retail の cost が重なると、本当に original な intraday の mechanism は、構造的に gate を通れない。通りうるのは直接の post-cost の証拠がある効果だけで、それらは既に inventory にある（主に F1）。

**Role H の推奨**: どの family も事前登録しない。

## 6. Role H への指示の文面（逐語）

lead が 2026-10-11T11:24:40Z に、別の context の agent（description「Role H: hypothesis architect (no data)」）に渡した。

```text
You are Role H — Hypothesis Architect — in a pre-registered FX research programme (repo C:\Users\yukik\fx-ai-trading, branch research/fxid-frontier-expansion). STRICT FIREWALL: you must NOT read, load, or compute anything from FX price/return data (no data/*.jsonl, no parquet, no caches, no running research scripts, no artifacts containing return statistics beyond what prior reports already state in prose). You MAY read repo docs (docs/**) and the web (literature, central-bank/institutional docs) for institutional detail, sign/timing priors and external effect-size priors. Do not modify repo files. Return your full output as your final message.

Read first:
- docs/research/fx_frontier_f0_prereg_2026_10.md (roles, period architecture, duplicate classes, 12-criterion ranking rubric with weights 12..1, power-first gate PF1–PF4 with m=0.58, component gate)
- docs/governance/fxid_frontier_expansion_reopen_2026_10.md
- Inventory to dedup against: scripts/research/fx_system_reopen_feasibility/prereg.py (FAMILIES F1–F15), docs/research/fx_component_discovery_fast_track_final_2026_10.md §7 (31 mechanisms examined, incl. CB announcement-day premium, option volume, quarter-end funding, etc.), docs/research/fxid_final_mechanism_feasibility_review_2026_10.md §6–§16 (KMW fixing W, Breedon-Ranaldo, Melvin-Prins month-end, Ito-Yamada, etc.), docs/research/m15_next_edge_source_reframing.md and m15_candidate_rerank_2026_09.md (S01..S23, C01..C13, H-001..), Round 1/A/B′ results (docs/research/m15_track_a_exploratory_round_1.md, m15_round_a_results.md, m15_round_b_prime_results.md: VR<1 at all horizons, IC negative).
- Retail cost context (aggregate, already reported): docs/research/fxid_cycle1_data_feasibility_final_report_2026_10.md §11–§12 and docs/research/fxid_ny_intraday_economics_followup_2026_10.md §7–§11 (round-trip ~1.7–2.6 bp majors depending on hour; rollover hour ~9 bp; 08:30 window ×1.44).

Tasks:
1. MARKET PLUMBING MAP (instruction §10): for the FX day (in ET), map whose balance sheet moves when and why: Tokyo open/Tokyo fixing (9:55 JST), Asia close, London open, European data, ECB reference (14:15 CET), London 4pm WMR fix, US data (08:30/10:00 ET), NY open, NY 10:00 option cut, FOMC/CB events, CLS settlement windows, 17:00 ET rollover/value-date roll, corporate payment cycles (gotobi, month-end, quarter-end), benchmark execution, dealer inventory management, liquidity-provider risk limits, futures/spot information transfer (CME, IMM dates), rates/FX transfer, options hedging (delta/gamma around expiries), international asset hedging. Keep it compact (table).
2. ORIGINAL CANDIDATES: generate 5–10 original mechanism hypotheses derived from the map (not indicator ideas; no RSI/EMA/etc.; no data mining). For each: MECHANISM_ID; Who; Why (necessity); When (exact ET timing); Information set observable ex-ante by a retail trader (public, available at decision time — specify source & latency); Direction (or relative value) and why; Decay (when the edge ends); Counterparty (who pays the premium); Cost (why it can exceed retail all-in round trip; pair & time of execution); duplicate classification vs inventory (NEW_MECHANISM / NEW_INFORMATION_FOR_EXISTING_MECHANISM / DUPLICATE / PREVIOUSLY_REJECTED / EXECUTION_VARIANT / HORIZON_VARIANT) with reasoning; opportunity frequency per year and cross-sectional breadth; needed data and whether available free (for S = 2021-04-26..2025-12-28 and E = 2010-01-01..2016-05-31).
3. BASE PREDICTED EFFECT s_B (annual retail net Sharpe) per candidate, derived WITHOUT looking at FX data: state assumptions explicitly (flow size, price-impact elasticity from literature, fraction captured, horizon σ, retail cost, 50% haircut for lack of direct evidence). Be honest and conservative; if you cannot justify ≥0.58, say so. Also give Optimistic and a range.
4. Apply the F0 ranking rubric (12 criteria, 0/1/2, weights 12..1) and the power-first gate PF1–PF4 (T_S=4.67y; T_E≈6.4y; V = total registered variants you'd propose, ≤6; z = Φ⁻¹(1−0.10/V)) to each candidate. Show the arithmetic.
5. Recommend ≤3 families for preregistration (each: 1 primary hypothesis fully specified — exact direction, timing, information set, target currencies, pair expression, horizon, entry, exit, primary statistic, null, minimum effect; optional ≤1 secondary variant). If none pass PF1–PF4, say so plainly — that is an acceptable outcome; do NOT inflate s_B to pass.

Output under 3500 words, structured with tables.
```

- Role H が行った 3 回の web 検索の **検索語は記録していない**（agent の出力に残っていない）。外部の prior（Evans–Lyons 2002、KMW など）は、§2 と §5 に出典の名前だけが残る。
- 指示の文面は z = Φ⁻¹(1 − 0.10 / V) を明示している（F0 §5 の本文と同じ。例の値とは合わない。§4）。

## 7. lead の訂正と開示（独立の review の後）

### 7.1 Optimistic の列の定義

§2 の Optimistic は **h = 1 だけではない**。Role H は Optimistic で g も上の prior に変えている（例: H-02 は g = 6、H-07 は g = 9、H-05 は g = 10 と c = 2.5）。H-02 = (6 − 2.2) / 16 × √24 = 1.16、H-07 = (9 − 2.7) / 26 × √37.5 = 1.48 で再現する。倍率は候補ごとに違い、根拠の記録は無い。

**h = 1 だけを変えた場合**【算術、§2 の n・k・g・c・σ のまま】:

| ID | s_B（h = 0.5） | h = 1 だけ |
| --- | --- | --- |
| H-01 | −2.48 | −2.31 |
| H-02 | −0.21 | +0.25 |
| H-03 | −0.02 | +0.19 |
| H-04 | −1.79 | −1.58 |
| H-05 | +0.03 | +0.25 |
| H-06 | −1.25 | −1.00 |
| H-07 | +0.07 | **+0.78** |

- **判定は、事前登録した 50% の haircut に依存する**。h = 1 なら H-07 は 0.78 > 0.58 で PF1 を通る。
- H-07 は `HORIZON_VARIANT`（F9）と分類され、F0 §3 で実証に進めない。ただし FX の microstructure の review は、週末の再開の流動性の供給は F9 と別の mechanism と読めると指摘した。その場合も Base（h = 0.5）は +0.07 で PF1 を通らない。
- **h = 1・V = 1 なら、H-07 は PF1〜PF4 を全て通る**【算術】: s = 0.777 ≥ 0.761（PF2 の厳しい読み方 z₀.₉₅/√4.67）、≥ 0.593（F0 §5 の文面 z₀.₉₀/√4.67）、PF3 は 0.777·√6.4 = 1.97 ≥ 1.645、PF4 は n = 15 > 12 で該当しない。H-07 を除外しているのは、h = 0.5 と `HORIZON_VARIANT` の分類だけである。他の 6 候補は h = 1 でも PF1 を通らない。

### 7.2 cost の入力

- Role H の c は、Cycle 1 §11–§12 と R-A2b §7–§11 の既報の集計である。**F0 §5 は Track B の値を使うと定めており、これは事前登録からの逸脱**（Track B は Role H と並行して走り、Role H の起動の時点で無かった）。
- Track B の値で置き換えても判定は変わらない: H-02 は c = 1.72 で −0.07、H-07 は c = 2.2 で約 +0.19、H-05 は c を 1.28 下げて 1.72 にしても約 +0.11（c = 1.28 にしても約 +0.14）。**どれも 0.58 に届かない**。
- H-07 の c = 2.7 は測定に裏付けられていない。Track B は日曜の再開の bar を測っていない（§7.4）。

### 7.3 「構造的」の所見の範囲

- §5 の結論は、**事前登録した 50% の haircut と、Role H の g の prior の下で**の所見である。市場の構造についての事実ではない。
- §5 の g/σ ≥ 0.24（年率 約 3.8）は、PF2 の厳しい読み方の 0.76 と k = 1 を使っている。breadth と保有を変えると、必要な gross の年率 Sharpe（pair あたり）は約 2.2〜3.7（k = 5 で 2.89、k = 20 で 2.55、cost の floor の約 2.2）。**haircut が無ければ約 1.9** で、KMW の 1.24〜1.82 に近い。
- Role H は gate を知った上で予測した。予測が保守的に偏る（偽陰性の）risk がある。rubric の基準 11（検証の実現性）は gate そのものを採点に入れており、循環している。
- h = 1 なら H-07 は PF1〜PF4 を全て通る（§7.1）。§5 の「構造的に通れない」は h = 0.5 の下でだけ成り立つ。
- **FRONTIER-A は「desk の段で、実証していない」判定である**。どの候補も data で反証されていない。

### 7.4 F0 §5 の gate の性質

- m = 0.58 の真の効果でも、片側 5% の単一の検定の検出力は S で約 0.35、E で約 0.43。V = 6 の多重性の下では、S で約 0.13〜0.19、E で約 0.18〜0.25（z の二つの読み方）。**PF2・PF3 を m ちょうどの効果で満たすことは、S = 4.67 年・E = 6.4 年では不可能**で、この読み方では、FRONTIER-A は設計でほぼ決まっていた。
- 一方で m = 1/√3 は緩い。system の posterior（#506 の prior の縮小）で G4 の 1.0 に届くには、component の真の Sharpe は約 1.1 が要る。
