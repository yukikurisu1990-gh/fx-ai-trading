# FX System Architecture — Decision Freeze + P1 / P2 Fast-Track 最終報告（2026-10-08）

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` · `PRODUCTION_READINESS_NOT_CLAIMED`.**

**authoritative な state は変わらない: `FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE`。**

**記号**:

| 記号 | 意味 |
| --- | --- |
| 【記録】 | repo に commit 済みの報告・記録 |
| 【P1】 | `artifacts/research/fx_system_reopen_feasibility/p1_result.json`（sha256 `8986337aa447c8dae7f0e1b022ac83bad699309607ac952479a4825849ce3005`） |
| 【算術】 | この文書の計算 |

---

## 1. Executive Summary

**最終判定: FAST-A — `NO_REOPEN_JUSTIFICATION_COMPONENT_SUPPLY_INSUFFICIENT`。**

P1 は STOP（`PORTFOLIO_ARCHITECTURE_FEASIBLE_BUT_COMPONENT_SUPPLY_INSUFFICIENT`）。P2 は実行していない。HOLD は継続する。

- **component の供給**:
  - 棚卸しした 15 の mechanism family のうち、過去の判定（RED・CLOSED・HOLD・DUPLICATE・NOT_IMPLEMENTABLE・ECONOMICALLY_UNATTRACTIVE など）を受けていないものは無い。
  - 上限の計算に入れられるのは、**dollar の日中の W 字の family（F1）の 1 つだけ**。HOLD の裁定 §6 が near-miss として保存したのは、そのうち EUR の欧州の朝と JPY の仲値の後の 2 つの窓で、EUR の ECB の後の窓は部分的な復活（§9）。
  - **distinct な family が 1 つしかないので、P1 の PASS 条件 (3)「2 つ以上の family」は、family の分類の段階で（上限を計算する前に）満たせないことが決まっていた**（独立レビュー Statistics の指摘。§13）。
  - さらに、Optimistic の窓は全て「古い」と事前に印を付けたので、`p1.py` の読み方では AMBER にも到達できなかった。**どの数値の結果でも STOP 以外は出なかった**。判定は、事前登録の分類と、事前登録の後・実行の前に書いた code の読み方で決まっており、上限の計算は判定に影響しない記述的な数値である（§14）。
- **system の上限**【P1】（long only、年率の retail の net の真の Sharpe）:

  | scenario | 上限 | 備考 |
  | --- | --- | --- |
  | **Base** | **0.28** | 正の窓は EUR の欧州の朝だけ |
  | Optimistic | 1.15 | 3 つの窓が全て古い推定で、それを除くと 0。窓の間の相関が約 0.27 以下の時だけ 1.0 を超える（0.3 で 0.99） |
  | Stress | 0 | cost 1.5 倍で全ての窓が負 |

  Base の上限は、検討した代替の仮定（haircut なし 0.40、CME の上端 0.52、閉じた family を戻しても 0.41）でも 1.0 から遠い【独立レビュー】。比べているのは真の Sharpe の上限で、G4（縮小後の事後の Sharpe）にとっては必要条件にすぎない。届かないことの結論は、より強くなる向きである。
- **結論**: 統合する正の component が足りない。ARCH-C の判定（主な制約は `COMPONENT_SUPPLY + COST + INDEPENDENT_DATA`）を、P1 が具体的な数で裏付けた。STOP の token の「ARCHITECTURE_FEASIBLE」は事前登録の token で、H の合成の構造が P2 で検証されたことを意味しない（P2 は未実行）。

## 2. PR #505 merge record

| 項目 | 記録 |
| --- | --- |
| 確認 | OPEN、head `a2d75e8`（報告と一致）、変更 6 file（予期しない差分なし）、CI `contract-tests` / `test` success、独立レビュー + 再監査が完了、未解決の BLOCKER なし |
| merge | `57723a27a117…`（2026-10-08T12:13:31Z） |
| master | `57723a2`（この branch の起点） |
| master の CI | `57723a2` の CI は success |

## 3. Adopted ARCH-C decision

**`ARCH-C — COMPOSITION_DOES_NOT_SOLVE_THE_FUNDAMENTAL_LIMITATION`** を、`docs/governance/fx_system_architecture_ruling_2026_10.md` に正式に記録した。

足し算・掛け算・ensemble・MoE・通貨の netting・最適化は、正の component を統合する方法ではあるが、正で・cost の後に残り・重複しない component そのものを作り出すことはできない。主な制約は `COMPONENT_SUPPLY + COST + INDEPENDENT_DATA` である。

## 4. Architecture H baseline

将来の再開の baseline として、上の governance の文書 §3 に記録した:

- mechanism-first・通貨の view
- 文献と commit 済みの証拠で事前に固定した期待 return
- Black–Litterman 型の精度の加重の合成
- 通貨の exposure
- まとめての最適化
- 多期間 / aim portfolio
- 硬い制約

具体的な値（文献の効果の最終値・haircut・Ω・λ・上限など）は凍結しない（同 §4）。

## 5. Architecture G conditional role

G は既定にしない。P2 で、同じ selection-error の予算の下で、事前登録の基準で H を上回る場合だけ候補にする（同 §5）。

- その基準の形は `gates.choose_architecture` に実装した。基準の要素（独立レビューの指摘で強化）: 同じ対立仮説の集合、G の FWER の CI の上端 ≤ 10% かつ H の CI の上端以下、どの対立仮説でも 0.10 以上の検出力を失わない、半数以上で 0.10 以上向上、増えた自由度あたりの中央値の向上。
- **`GCriterion` の閾値の値は placeholder で、P2 を行う場合は、その事前登録で出力の前に改めて固定する**（事前登録された基準ではない）。
- **今回は P2 を実行していないので、G は評価されていない**。

## 6. One-time P1/P2 HOLD exception

- Human + ChatGPT の指示（2026-10-08）は、**P1 と、P1 が PASS した場合の P2 だけ**を、HOLD の中で実行することを一度だけ許可した。
- これは、HOLD の裁定と PR #505 の「P1 / P2 は REOPEN の承認の後だけ」を、P1 / P2 に限って上書きするもの。
- P3 以降には及ばない。
- 記録: `docs/governance/fx_system_architecture_ruling_2026_10.md` §6。`gates.EXCEPTION_SCOPE = {P1, P2}` と test で固定した。

## 7. P1 preregistration

| 項目 | 記録 |
| --- | --- |
| 事前登録 | `docs/research/fx_system_p1_prereg_2026_10.md` と `scripts/research/fx_system_reopen_feasibility/prereg.py` |
| commit | `9ad8960`。上限を計算する code（`p1.py`）が存在する前に commit と push を行った |
| 計算の code | `96796d5` で commit |
| 実行 | 1 回（記録の head `96796d5`、dirty 0、記録の commit `f81f646`） |
| hash | 事前登録の 2 file の sha256（`prereg.py` `86a6f2e1…`）は、事前登録・実行・記録の 3 つの commit で同一（独立レビューが確認） |

**開示**:

- PASS の規則の条件 (2)（1 つの古い推定・極端な相関だけで成立していない）と条件 (4)（cost の stress の後の余地）の**操作的な定義は、事前登録の文書ではなく `p1.py` に書かれた**。実行の前（`96796d5`）だが、事前登録の後である。
  - (2): 1 つを除いた上限 ≥ 1.0、かつ古い窓を除いた上限 ≥ 1.0
  - (4): Base に cost 1.5 倍を掛けた後の上限 ≥ 1.0
- 条件 (1) が不成立なので、どちらも判定に影響しない。
- commit の間隔は約 2 分。commit の順序は、記録した実行の前に file が凍結されていたことを示すが、commit の前の下書きの計算が無かったことまでは示せない。

## 8. Mechanism-family inventory

15 の family。同じ economic source を strategy の名前で複数に数えない（`prereg.FAMILIES`）。

| family | P1 での扱い |
| --- | --- |
| F1 dollar の日中の W 字 / fixing の在庫 | ELIGIBLE（§6 が保存した 2 つの窓。ECB の後の窓は部分的な復活、§9） |
| F2 自国時間 / 顧客の flow | F1 に統合（EUR の窓では同じ pair・窓・符号で、損益の系列が同じ。JPY では B&R の自国時間の効果は東京の時間の JPY の short で F1 の窓と違うが、F2 は LOCKED で影響なし） |
| F3 機関の注文 flow | LOCKED |
| F4 月末の株式ヘッジ | LOCKED |
| F5 fix の後の反転 | LOCKED |
| F6 東京の仲値の spike / gotobi | LOCKED |
| F7 指標の発表の repricing | LOCKED |
| F8 日中の momentum | LOCKED |
| F9 短期の平均回帰 | LOCKED |
| F10 session の引き継ぎ | LOCKED |
| F11 option cut | LOCKED |
| F12 carry | LOCKED |
| F13 cross-sectional / 時系列の momentum | LOCKED |
| F14 classical premia の合成 | LOCKED |
| F15 その他の日次の研究（T-R / T-R2 / T-V / Top-Five / next-five / M16） | LOCKED |

**F1 の窓**:

| 窓 | 方向 | 時刻（ET） |
| --- | --- | --- |
| EUR の欧州の朝 | short EUR | 02:00 → 08:15 |
| JPY の東京の仲値の後 | long JPY | 冬 19:55 / 夏 20:55 → 02:00（同じ取引日の中） |
| EUR の ECB の後 | long EUR | 08:15 → 16:45 |

- 全て NY 17:00 の rollover をまたがない。
- 事前登録の文書は ECB の後の窓の終わりを 17:00 と書いたが、計算は #503 §14 と同じ 16:45（当日決済の制約。17:00 ちょうどは rollover の spread と financing の境）を使った。
- ECB の参照 rate は 14:15 CET で、英米と欧州の夏時間のずれの週は 09:15 ET になる（年に 3〜4 週）。

## 9. Existing statuses

| family | 過去の判定【記録】 |
| --- | --- |
| F1 | `ECONOMICALLY_UNATTRACTIVE`（#503 §15）、HOLD の裁定 §6 の near-miss。**fix の flow の以前の記録**（独立レビュー FX の指摘で追加）: C04 benchmark fix flow は RED（停止、#478 inventory）、#474 の fix の前後 1 時間の cell は方向が未検定 |
| F2 | C03 `NO_DECISION_GRADE_PASS_REGION`（#484）・RED（#478 inventory）、H-002 CLOSED（gate として）、#503 で programme の要求に不足 |
| F3 | `NOT_IMPLEMENTABLE_WITH_AVAILABLE_INFORMATION`（#503） |
| F4 | `DUPLICATE_OF_PREVIOUS_RESEARCH`（C05 / S21 停止）・`ECONOMICALLY_UNATTRACTIVE`（#503 §13d） |
| F5 | `NOT_IMPLEMENTABLE`（分単位） |
| F6 | `NOT_IMPLEMENTABLE` / `INSUFFICIENT_EVIDENCE` |
| F7 | #473 の検出力のある帰無、S2 保留 |
| F8 | S1 除外、VR < 1 |
| F9 | Round 1 で net 負、B′ は損益分岐の 6〜16%、multi-day の反転は dropped |
| F10 | C03 `NO_DECISION_GRADE_PASS_REGION` |
| F11 | #474 の option cut の cell の毎日の損益分岐 IR 4.10 / 4.93 |
| F12 | `CARRY_EDGE_NOT_SUPPORTED`（#471）、#497 `LONG_TERM_HOLD`。carry は 17:00 の rollover をまたいで初めて生じ、当日決済では 0 |
| F13 | #497 で hedge の役だけ、B′-4 の月次 TSMOM は負 |
| F14 | #497 `LONG_TERM_HOLD`（TC-net 0.127） |
| F15 | NOT_SUPPORTED。M16 は POSITIVE_EXPLORATORY だが #495 で「閉じる」。12 か月の USD の因子で、当日決済の範囲外 |

ML・tabular の系譜（Phase 9・27〜29・ML Step 4、C-8）・Round A（#468）は F8・F9・F15 に属し、全て負か無効【記録】。

**開示（独立レビュー FX の指摘）**:

- HOLD の裁定 §6 が near-miss として保存したのは、**EUR の欧州の朝と JPY の仲値の後の 2 つの窓だけ**で、**EUR の ECB の後の窓は保存されていない**（#503 §13c / §15 で `ECONOMICALLY_UNATTRACTIVE`、CME 0.08）。
- それを F1 の窓として Optimistic に 0.25 で入れたのは、**部分的な復活**に当たる。
- **事前登録の不整合**として記録する（事前登録 §2 の「過去の判定を受けたものは寄与 0」の規則に反する）。計算の前に登録したので結果に依存した拡大ではなく、Optimistic を上げる向き（STOP に不利な向き）だけに効く。
- 影響は無い: ECB の後を除いても、Optimistic は 1.127（1 つを除いた上限）で、判定は同じ。Base と Stress では、この窓は 0 か負。

## 10. Effect scenarios

計算の前に固定した（§7）。年率の retail の net Sharpe（真の値の想定）。

| 窓 | P1-O | P1-B | P1-S |
| --- | --- | --- | --- |
| EUR の欧州の朝 | 0.74（B&R 1997–2007 を retail に置き換え、#503 §13a） | 0.40 × 0.70 = **0.28** | 0.16 × 0.40 = 0.064 → cost 1.5 倍で −0.47 |
| JPY の仲値の後 | 0.85（KMW 1999–2018 の平均、#503 §13b。**最近の証拠と矛盾**） | 0 | 0 → −0.50 |
| EUR の ECB の後 | 0.25（KMW 1999–2018 の gross / σ 0.072 − retail の cost / σ 0.056 = 0.016、× √250、#503 §13c） | 0 | 0 → −0.44 |
| 窓の間の相関 | 0 | 0.3 | 0.5 |
| cost の倍率 | 1.0 | 1.0 | 1.5 |

**Base の根拠の訂正**（独立レビュー Statistics・FX の指摘。**どちらも Base を高く見せる向きで、判定に影響しない**）:

- 0.29〜0.52 は不確かさの区間ではなく、同じ CME の推定の slippage 0.5 bp を含む値と含まない値である。P1 の cost の基準（slippage を含む）に揃えると 0.29 で、0.29 × 0.7 = **0.20**。
- 事前登録は「CME の期間は KMW の公表より前なので、減衰の全量は掛けない」として 30%（低い端）を選んだが、この理由は逆向き。公表の後の減衰は、公表の前の推定に対して測るものなので、**公表の前の期間の推定にこそ全量を掛けるべき**。また、B&R は 2013 年に公表されており、CME の期間の一部は既に公表の後である。
- 正しく直せば、Base は 0.20 × (0.4〜0.7) ≈ 0.08〜0.14 で、更に低い。
- 窓の間の相関 0.3 の根拠（W 字の強さが日ごとに共通）は推測で、窓の USD の符号は逆なので、負の相関もありうる（#505 §1）。Base は正の窓が 1 つなので、どの相関でも上限は約 0.28（−0.2 で 0.295）。

## 11. System upper-bound method

【P1】`p1.py`:

- **long only**（重み ≥ 0）の最大の Sharpe は、部分集合を全て調べて求める。各部分集合で接点の重み R_S⁻¹ s_S が全て ≥ 0 のものの最大で、KKT の最適の support はその部分集合の 1 つなので、真の最大になる（独立レビュー Quant が確認。scipy の独立な最適化でも一致）。
- **cost の stress**: 窓の Sharpe から (倍率 − 1) × cost / σ × √250 を引く。
- **1 つを除いた上限・古い窓を除いた上限**を、条件 (2) に使う。
- **判定に使わない感度**: 窓の間の相関 −0.2、状態を解いた参考の行。

**記録の値の注記（独立レビューの指摘）**:

| 記録の field | 注記 |
| --- | --- |
| `unconstrained_any_sign` | **無効**（`INVALID_SIGN_FLIP_IGNORES_COST`）。cost の後の Sharpe が負や 0 の窓を「売る」ことで上限を上げているが、取引を逆にしても cost は再び払う（売りの Sharpe は −gross − cost で、+\|net\| ではない）。Stress の 0.58、Stress の相関 −0.2 の 1.05、Base の 0.30 はこの理由で実現できない。**1.0 への経路として引用しない** |
| `currency_exposure_constrained` | **上限の値としては無効**。窓は時間が重ならない（終わりと始まりが接するだけ）ので同時の複数通貨の exposure は無いが、**3 つの窓は全て USD の pair の bet**（USD の符号は、EUR の朝で long、JPY の仲値の後と ECB の後で short と交互）で、USD の risk の比率の上限は満たせない（制約は binding）。記録の値は long only の値の複写 |
| `same_day_constrained` | overnight の family は全て LOCKED なので、判定に影響しない |
| `distinct_families...`・`family_concentration...` | F1 だけが eligible なので、計算ではなく分類の結果として記録した値 |
| `TRADES_PER_YEAR` | 250（原典の値の一部は √252 で作られている。差は判定に影響しない） |

**cost の現実性の注記**（独立レビュー FX）: Base は、CME の firm な気配を OANDA の 2021–2025 の時刻の平均の M15 の spread + 0.5 bp に置き換えたもので、次を model していない。Base の EUR の朝は cost の倍率約 1.26 で 0 になるので、どれも STOP を強める向き。

- OANDA の market maker の気配（last look・requote）と firm な気配の違い
- 02:00・08:15 の境の時刻の spread
- ECB の会合の日の 08:15（年約 8 回）
- ECB の後の窓の中の US 08:30・10:00 の発表・option cut・11:00 の London fix・FOMC

**証拠の新しさ**: P1 の入力は、どれも 2018 年より新しくない。Base の入力（CME 2009–18）も、KMW 自身の 1999–2018 の sample の中にある。

## 12. P1 results

【P1】long only の上限:

| scenario | 窓の Sharpe（cost の stress の後） | 上限 | 1 つを除いた上限 | 古い窓を除いた上限 | 感度: 相関 −0.2 |
| --- | --- | --- | --- | --- | --- |
| **P1-B** | EUR 朝 0.28 / JPY 0 / ECB 後 0 | **0.28** | 0（EUR 朝を除く）/ 0.28 / 0.28 | 0.28 | 0.295 |
| P1-O | 0.74 / 0.85 / 0.25 | **1.154** | 0.886 / 0.781（JPY を除く）/ 1.127 | **0**（全て古い） | 1.432 |
| P1-S | −0.47 / −0.50 / −0.44 | **0** | 0 | 0 | 0 |

- **Optimistic の相関の感度**【算術】: 0.25 で 1.010、0.275 で 1.000、0.3 で 0.99、0.5 で 0.93。**1.0 を超えるのは相関が約 0.27 以下の時だけ**。
- **Base の cost の損益分岐**: EUR の朝の 0.28 は、cost の倍率約 1.26 で 0 になる【算術、独立レビュー Quant】。
- **状態を解いた参考の行**（判定に使わない）: Base 0.28 に、閉じた #497 の 0.127 と M16 の 0.276 を相関 0 で足しても 0.41。当日決済に反し、観測の Sharpe と真の上限の混在でもある。

**条件**【P1】:

| 条件 | 結果 |
| --- | --- |
| (1) Base の上限 ≥ 1.0 | **不成立**（0.28） |
| (2) 1 つの古い推定・極端な相関だけで成立していない | 不成立 |
| (3) distinct な family が 2 つ以上 | **不成立**（1 つ。分類の段階で決まっていた） |
| (4) cost の stress の後の余地 | 不成立（Base に cost 1.5 倍で 0） |

## 13. P1 independent review

3 つの独立な役（指示 §14）を、別の context で並行して走らせた。互いの結論は渡していない。**3 役とも BLOCKER なし、STOP を支持**。

| 役 | 主な確認と指摘 | 対応 |
| --- | --- | --- |
| **Quant** | 全ての数値を再現した（scipy の独立な最適化でも一致）。long only の部分集合の列挙の正しさを確認。事前登録 → code → 実行 → 記録の順を確認。REQUIRED: (1) 符号を反転した上限は cost を無視していて無効、(2) 通貨の exposure の制約は USD の集中で binding。NON-BLOCKING: Optimistic は相関 0 の時だけ 1.0 を超える、AMBER と STOP の解釈、cost の損益分岐 1.26、√252 と 250 | §11・§12・§14 に反映 |
| **Statistics** | provenance・scenario の値・drag の算術を確認。REQUIRED: (1) **PASS は分類の段階で不可能だった**（条件 (3)）ことを明記、(2) Base の根拠の 2 つの誤り（slippage の有無の取り違え、haircut の理由が逆）はどちらも寛大な向き。NON-BLOCKING: 相関 0.3 の根拠は推測、AMBER と STOP の解釈、条件 (2)・(4) は code でだけ操作的に定義、Base の頑健性（0.40 / 0.52 / 0.53 / 0.41、全て 1.0 から遠い）、符号の反転の無効、単位の混在 | §1・§7・§10・§11・§14 に反映 |
| **FX economics** | F2 を F1 に統合するのは経済的に正しい（顧客の dollar の需要を dealer の balance sheet が吸収する同じ現象の 2 つの説明）。窓の方向・時刻、carry = 0 を確認。REQUIRED: (1) **ECB の後の窓は保存された near-miss ではなく、部分的な復活**（影響なし）、(2) AMBER の字義の条件は成り立つことを明記、(3) F1 の以前の判定（C04 RED、#474 の cell）を引き継ぐ。NON-BLOCKING: 終わりの 16:45 と 17:00、ECB の夏時間のずれ、02:00 のドイツの指標・ECB の会合の日の 08:15・介入の jump は model していない（Base は 0 なので影響なし）、2015 の WMR の窓の変更は 3 つの窓に関係しない、KMW Table 8 の GBP と JPY の前の窓は記載が無い（結果を見た後の universe の拡大は禁止なので、記録だけ） | §8・§9・§14 に反映 |

**再実行はしない**: 全ての指摘は記録の注記と文言で、判定に影響しない。P1 は事前登録どおり 1 回だけ実行した。

## 14. P1 verdict

**`STOP` — `PORTFOLIO_ARCHITECTURE_FEASIBLE_BUT_COMPONENT_SUPPLY_INSUFFICIENT`**。

**AMBER と STOP の関係（3 役の指摘による開示）**:

- **規則の字義では AMBER の行も成り立つ**（Optimistic 1.154 ≥ 1.0 > Base 0.28）。
- STOP は、規則の STOP の第 1 の節「Base と Optimistic のどちらにも credible な 1.0 の経路が無い」による:
  - Optimistic の 3 つの窓は全て、最近の証拠より古い sample の推定で、古い窓を除くと上限は 0。
  - JPY の 0.85 は最近の証拠（CME 2009–18 で −0.2〜0.07、2013 年以降は横ばい）と矛盾する。
  - 1.0 を超えるのは窓の間の相関が約 0.27 以下の時だけ（§12）。
- 第 2 の節「1 つの古い推定だけに依存」の字義では、1.0 には**2 つ**の古い推定（EUR の朝と JPY）が要る（1 つを除くと 0.886 と 0.781）。code の「古い窓を除いた上限 < 1.0」は、事前登録の文言より厳しい読み方である。
- **どちらの読み方でも結果は同じ**: AMBER も STOP も P2 に進まず（指示 §13）、HOLD は継続する。指示 §32 は FAST-A を「P1 で STOP」と定義しているので、**AMBER を FAST-A に対応させるのは解釈**である（P2 が無いことは同じ）。
- **上限の計算は判定に影響しなかった**: PASS は分類の段階で不可能（条件 (3)）で、Optimistic の窓は全て事前に「古い」と印を付けたので、code の読み方では AMBER にも到達できなかった。

## 15. P2 preregistration if applicable

**該当しない**（P1 が PASS しなかったので、P2 は実行しない。`gates.p2_allowed("STOP") = False`）。

## 16. Null scenarios

該当しない（P2 は未実行）。

## 17. Alternative scenarios

該当しない（P2 は未実行）。

## 18. H results

該当しない（P2 は未実行）。

## 19. G results

該当しない（P2 は未実行）。

## 20. FWER

該当しない（P2 は未実行）。

## 21. Power

該当しない（P2 は未実行）。

## 22. System-prior calibration

P2 は未実行だが、**system の prior の契約は code と test で固定した**（`system_prior.py`）。

**最初の版の欠陥と修正**（独立レビュー Statistics・Quant の指摘）:

- 最初の版（`96796d5`）は、実効の数に k / (1 + (k − 1) ρ) を使っていた。これは等しい重み・同じ符号の合成の量である。
- 符号と重みを最適に選ぶ合成（S = √(sᵀ R⁻¹ s)）では、component の prior N(0, τ_c² I) の下で **E[S²] = τ_c² · tr(R⁻¹)** で、等相関では tr(R⁻¹) = 1 / (1 + (k − 1) ρ) + (k − 1) / (1 − ρ) ≥ k になる（正の相関は、hedge で達成しうる Sharpe を上げる）。
- 最初の版の「較正した」τ_c は、k = 10・ρ = 0.3 で system の RMS を 0.88 にし（G4 の 0.4 ではなく）、P(S > 1) は 23% だった。**抜け穴を閉じていなかった**。
- 最初の版の test は、ρ = 0 の simulation と、自分自身との循環の比較だけで、この欠陥を見逃していた。

**修正の後の契約**:

| 項目 | 内容 |
| --- | --- |
| 2 次の moment | τ_c = τ_sys / √tr(R⁻¹) で、含意する system の RMS を G4 の τ に一致させる |
| tail | 含意する P(S > 1) が、G4 の prior の P(system の Sharpe > 1) = 1 − Φ(1/τ_sys)（τ 0.4 で 0.0062）以下であることを、Monte Carlo（決定的）で確かめる。2 次の moment を合わせても、S は χ 型なので tail は別に検査する |
| test | ρ = 0・0.3 の simulation、tr(R⁻¹) の式、tail、k = 1 で符号を data で選ぶと tail が 2 倍になり拒否されること |

**計算の例**【算術】: τ_sys = 0.4、k = 10。

| ρ | 2 次の moment で較正した τ_c | tail で較正した τ_c | 拘束する条件 |
| --- | --- | --- | --- |
| 0 | 0.127 | 0.202 | 2 次の moment |
| 0.3 | 0.110 | 0.174 | 2 次の moment |

**P1 の記録への影響**: `system_prior.py` と `gates.py`（`choose_architecture` の強化）は P1 の実行の後に変えたので、記録の `code_sha256` のこの 2 file の値は現在の file と一致しない。

- `p1.py` は `system_prior` を import していない。
- `gates` からは `p2_allowed` と `final_classification` だけを使い、この 2 つは変えていない。
- したがって、P1 の計算と判定は影響を受けない。

## 23. H vs G decision

P2 を実行していないので、G は評価されていない。**既定の H のまま**（裁定 §5）。G を採る基準の形は `gates.choose_architecture` に実装し、test で形を固定したが、**閾値の値は placeholder で、将来の P2 の事前登録で改めて固定する**。

## 24. Final verdict

**FAST-A — `NO_REOPEN_JUSTIFICATION_COMPONENT_SUPPLY_INSUFFICIENT`。**

- P1 で STOP した。P2 は実行していない。
- 最終の state は **`FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE` のまま**。
- 指示 §26 に従い、次のことはしない:
  - 追加の strategy 案・indicator の追加
  - ML
  - 交互作用の探索
  - 保有期間の変更による救済
  - CFD への拡張
- Human が改めて指示するまで、研究を止める。

## 25. REOPEN proposal if applicable

**該当しない**（FAST-A）。`FXID_REOPEN_REVIEW_PROPOSAL` は作成しない。

## 26. P3/P4 drafts if applicable

**該当しない**（FAST-A）。P3 の計画と P4 の事前登録の草案は作成しない。

## 27. Independent reviews

**P1 の独立レビュー**（3 役）は §13。

**最終の成果物の独立レビュー**（4 役、指示 §30）: 別の context で並行して走らせ、互いの結論は渡していない。**4 役とも BLOCKER なし、FAST-A と P2 の未実行を支持**。

| 役 | 主な指摘 | 対応 |
| --- | --- | --- |
| **Quant Portfolio** | REQUIRED: (1) **system の prior の契約の実効の数が ρ > 0 で誤り**（tr(R⁻¹) が正しい。k = 10・ρ = 0.3 で尺度は 3.62 τ_c、code は 1.64 τ_c）、(2) Optimistic が 1.0 を超える相関は 0 ではなく約 0.275。NON-BLOCKING: `currency_exposure_constrained` は上限の値として無効、`choose_architecture` の甘さ（点と CI の比較、key の集合、損失の上限）、「H の構造は使える」は未検証 | §22 の契約を書き直し test を追加、§1・§12 の相関、§11、§5 の基準の強化 |
| **Statistician** | REQUIRED: (1) 同じ契約の欠陥（ρ = 0.3 で RMS 0.88、P(S > 1) 23%）、(2) simulation の test が ρ = 0 だけで、2 次の moment だけ、(3) **どの数値でも STOP 以外は出なかった**ことを §1・§14 に明記、(4) `GCriterion` は placeholder、(5) 「どの合理的な代替でも」は過大。NON-BLOCKING: AMBER → FAST-A は解釈、真の Sharpe の上限は G4 の必要条件 | §22・test・§1・§14・§5・§23 |
| **FX Economist** | REQUIRED: (1) governance の文書の §1 の参照が §5（正しくは §6）、(2) ECB の後の窓を「保存された near-miss」と書いた箇所（§1・§8）。NON-BLOCKING: F2 の統合は EUR の窓だけで成り立つ、C03 の RED の併記、時刻の確認、cost の現実性（market maker・境の時刻・ECB の会合の日・窓の中の event）、2018 年より新しい入力は無い | governance の §1、§1・§8・§9・§11 |
| **Adversarial Governance** | BLOCKER・REQUIRED なし（PR の作成だけが残る）。範囲・隠れた data の読み取り・事前登録の順序・例外の範囲・G4 の抜け穴・§29 を確認。NON-BLOCKING: ECB の後の窓は事前登録の不整合、AMBER は事前登録の定数の下で到達不能、test 11 は記録の削除で抜けられる、test 4〜6 の禁止の呼び出しが部分一致だけ、出力の sha の全桁の記録 | §9、§14、test 11 を記録の存在の必須と scenario の値の固定に、test 4〜6 に `open`・`np.load`・`fromfile`・`importlib`・`pickle` と、file の読み取り・subprocess を helper の中に限る検査を追加、全桁の sha |

**修正の後の再監査**（新しい context、`d127e27`）: BLOCKER 0。(a) 契約（tr(R⁻¹) 13.127、較正の値、拒否と受理、旧版の失敗 RMS 0.88・P(S > 1) 0.234 の再現）、(c)・(e)・(f)・(g)・(h)・(i)（P1 の結果に影響なし）を確認。**REQUIRED FIX 2 件**: `choose_architecture` が上側の中央値を使っていた（2 つの対立仮説では最大の利得になる）→ `statistics.median` に直し test を追加、§14 に「相関 ≤ 0」が残っていた → 直した。NON-BLOCKING: NaN の guard を追加、test の件数・3.62 の表記を直した。§13 の Quant の行の「相関 0 の時だけ」はそのレビューの記録として残す（正しい値は §12）。

## 28. Governance compliance

| 項目 | 状態 |
| --- | --- |
| 新しい価格の系列の読み取り・取得 | 無し（P1 は事前登録の定数と、commit 済みの記録の値だけ。package の import は test で検査） |
| broker・OANDA | 無し |
| fresh / OOS / dead / forward | 無し |
| strategy / alpha の backtest・ML | 無し |
| P3 / P4 の実行 | 無し |
| HOLD | 維持（test で固定） |
| 例外の範囲 | P1（実行）と P2（条件不成立で未実行）だけ |
| G4 | system 単位の 1.0（test） |
| component の prior の和による抜け穴 | 契約と test で禁止 |
| 結果に依存した候補の拡大 | 無し（15 family の universe を事前登録で固定、test で確認）。ECB の後の窓の部分的な復活は §9 で開示（影響なし） |
| 新しい文献の探索 | 無し |
| 指示 §29 の 12 項目の test | `tests/research/test_fx_system_reopen_feasibility.py`（parametrize を展開して 20 件以上） |

## 29. Human + ChatGPT decision requests

1. **最終判定 FAST-A**（`NO_REOPEN_JUSTIFICATION_COMPONENT_SUPPLY_INSUFFICIENT`、P1 STOP、HOLD 継続）を受け入れるか。AMBER の字義の読み方を採っても、P2 に進まず HOLD 継続で結果は同じ（§14）。
2. **governance の記録**（`docs/governance/fx_system_architecture_ruling_2026_10.md`: ARCH-C・Architecture H の baseline・G の条件・system 単位の G4・一度限りの例外）を、この PR とともに authoritative として merge するか。
3. **今後**: FX の自動売買の研究は、HOLD の裁定 §9 の再開の trigger（特に、all-in の往復の cost ≤ 1.0 bp の継続）が観測されるまで、何も行わないことを確認するか。

---

**STOP（指示 §34）。** 実価格 data・broker・fresh・backtest には進まない。Human + ChatGPT の承認なしに merge しない。
