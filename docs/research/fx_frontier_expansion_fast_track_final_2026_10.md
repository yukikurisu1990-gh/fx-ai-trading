# FXID_FRONTIER_EXPANSION_FAST_TRACK — 最終報告（2026-10-11）

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` · `PRODUCTION_READINESS_NOT_CLAIMED`.**

**記号**:

| 記号 | 意味 |
| --- | --- |
| 【記録】 | repo に commit 済みの記録 |
| 【B】 | `artifacts/research/fx_frontier/track_b_cost.json`（sha256 `7491242fcdea03af9374442cbefe0f841f039d3397d952afea15b45b76117bcb`） |
| 【A】 | `docs/research/fx_frontier_track_a_record_2026_10.md`（Role H の出力） |
| 【算術】 | この文書の計算 |

---

## 1. Executive Summary

**最終判定: FRONTIER-A — `NO_ORIGINAL_MECHANISM_SURVIVES`。** STOP の理由は「desk power infeasible / candidate 0」。state は **`FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE` に戻る**。

| track | 結果 |
| --- | --- |
| **Track A（original な mechanism）** | 価格の data を見ない Role H が、市場の配管の地図から 7 つの original な mechanism を作った。data を見る前の power-first の gate（F0 §5、最低限の有用な component の net Sharpe 0.58）を、**どれも通らなかった**。Base の予測は −2.48 〜 +0.07。data の取得・target の return の読み取り・実証は行っていない |
| **Track B（execution の cost の frontier）** | seen の 2021-04 … 2025-12 の M15 bid / ask の spread を測った。最も低いのは USD_JPY の London fix の時刻の中央値 1.13 bp で、all-in の往復は約 1.63 bp（slippage 0.5 bp の推定を含む）。**all-in ≤ 1.0 bp は、20 pair × 11 の時間帯の 220 の cell のうち 212 で一度も無く、8 で一瞬（bar の 0.05% 以下）だけ**。HOLD の再開の trigger A（all-in ≤ 1.0 bp の継続）も観測されない |

**構造的な所見**（Role H が見つけ、lead が確認した）:

- 日次の intraday の取引では cost / σ ≈ 0.06〜0.08 で、component の Sharpe 0.76 に届くには、cost の無い gross で pair あたり年率 Sharpe 約 3.8 が要る。
- これは、公表された最も強い intraday の FX の効果（KMW の fix の W 字、cost なし 1.24〜1.82）の 2 倍以上である。
- **直接の証拠が無い original な仮説は、50% の haircut と retail の cost の下で、data を見る前に構造的に gate を通れない**。

**意味**: FX のデイトレードが不可能という判定ではない。retail の cost の下では、事前に検出できる大きさの original な mechanism を、根拠を持って予測できなかった。

## 2. #507 merge record

| 項目 | 記録 |
| --- | --- |
| 確認 | OPEN、head `47be79d`（報告と一致）、変更 9 file（予期しない差分なし）、CI `contract-tests` / `test` success、独立レビュー + 再監査が完了、未解決の BLOCKER なし |
| merge | `f91e20d85aef…`（2026-10-11T11:14:29Z） |
| master | `f91e20d`。master の CI は success を確認してから次に進んだ |

## 3. Reopen authority

`docs/governance/fxid_frontier_expansion_reopen_2026_10.md`（`53d5d9f`）:

- literature-first から mechanism-first への転換
- Track A / B
- 到達してよい最終段は FRONTIER-E（fresh の直前）
- fresh・保護期間・取引の禁止
- 予算（3 family、6 variant、3 の取得の package）

## 4. Why literature-first discovery ended

- #503（文献の机上の検討）と #507（31 の mechanism、D1 で 1 family、D2 で 0）で、既存の文献に、retail の cost の後に検証できる edge は見つからなかった。
- 今回は、文献を候補の必須の条件にせず、mechanism・制度・sign・timing・外部の prior・重複の監査の材料として使った。

## 5. Market plumbing map

【A】§1。17:00 の rollover から、東京の仲値・日銀の国債買入の通知・人民銀行の基準値・CLS・London の開場・ECB の参照 rate・US の指標・option cut・WMR fix・国債の入札・FOMC・CME の清算・月末と四半期末・月初の NISA / 投信・日本の配当の季節まで、「誰の balance sheet がいつ、なぜ動くか」を整理した。

## 6. Original mechanism candidate generation

Role H が 7 つの候補を作った（【A】§2）。

| ID | 中身 |
| --- | --- |
| H-01 | CNY の基準値の surprise の Asia への伝達 |
| H-02 | 月初の投信の換算（東京の仲値） |
| H-03 | 日本の配当の季節の円売り |
| H-04 | 国債の入札の結果 → USD |
| H-05 | 日銀の買入の規模の surprise |
| H-06 | 公開の SDR の strike への pinning |
| H-07 | 週末の gap の流動性の反転 |

data を見る前に捨てた案（6 つ）は【A】§2 の末尾。

## 7. Duplicate audit

| 分類 | 候補 |
| --- | --- |
| NEW_MECHANISM | H-01・H-03・H-05 |
| NEW_INFORMATION_FOR_EXISTING_MECHANISM | H-02（F1 / F6）・H-04（F7）・H-06（F11） |
| HORIZON_VARIANT（進めない） | H-07（F9） |

## 8. Pre-data ranking

F0 §4 の 12 の基準（最大 156）: H-02 112、H-07 92、H-05 85、H-03 83、H-01 81、H-06 72、H-04 70。

## 9. Preregistered hypotheses

**該当しない**。power-first の gate を通る候補が 0 なので、仮説の事前登録（Role E の評価の前の freeze）は行っていない。

## 10. Power calculations

| 候補 | s_B（Base） | PF1（≥ 0.58） | 結果 |
| --- | --- | --- | --- |
| H-01 | −2.48 | × | 不合格 |
| H-02 | −0.21 | × | 不合格 |
| H-03 | −0.02 | × | 不合格 |
| H-04 | −1.79 | × | 不合格 |
| H-05 | +0.03 | × | 不合格 |
| H-06 | −1.25 | × | 不合格 |
| H-07 | +0.07 | × | 不合格（HORIZON_VARIANT でもある） |

**Track B の実測の cost で置き換えた場合**【算術】:

- H-02 の cost を Track B の USD_JPY の東京の時間帯の中央値 1.22 + 0.5 = 1.72 bp にしても、s_B = (1.5 − 1.72) / 16 × √24 ≈ −0.07 で、不合格のまま。
- 他の候補も、cost の差（0.2〜0.8 bp）では符号が変わらない。

**参考**: m = 0.58 の真の効果があっても、S（4.67 年）での検出力は約 0.35、E（6.4 年）では約 0.43。

**F0 §5 の erratum**（Role H の指摘）:

- PF2 の本文の z_{1−0.10/V} と、例（V = 6 で 1.11、V = 3 で 0.98）が合わない。例は z_{1−0.05/V}（両側の family-wise 10%）に相当する。
- 凍結した事前登録は変えない。全ての候補は PF1 で不合格なので、判定に影響しない。

## 11. Track B execution-cost frontier

【B】seen の 2021-04-26 … 2025-12-28、20 pair、M15 の bid / ask の終値の spread。実行は 1 回（head `5fc223f`、dirty 0）。

**最も低い中央値の spread**（pair × 時間帯）:

| pair | 時間帯 | 中央値（bp） |
| --- | --- | --- |
| USD_JPY | London fix（10:45〜11:15 ET） | 1.13 |
| USD_JPY | NY の午後 | 1.16 |
| USD_JPY | London の朝 | 1.18 |
| USD_JPY | NY 09 時台 / 10 時台 | 1.18 |

**主要な pair の中央値 / p90**（bp）:

| pair | London の朝 | NY 09 時台 | London fix | NY の午後 | rollover の後（17:00〜19:00） |
| --- | --- | --- | --- | --- | --- |
| EUR_USD | 1.38 / 1.54 | 1.37 / 1.54 | 1.33 / 1.49 | 1.37 / 1.53 | 1.97 / 4.82 |
| USD_JPY | 1.18 / 1.39 | 1.18 / 1.41 | 1.13 / 1.32 | 1.16 / 1.35 | 2.06 / 5.77 |
| GBP_USD | 1.41 / 1.68 | 1.39 / 1.68 | 1.34 / 1.57 | 1.39 / 1.65 | 3.00 / 7.55 |
| USD_CAD | 1.37 / 1.57 | 1.34 / 1.59 | 1.31 / 1.52 | 1.33 / 1.58 | 2.42 / 5.18 |
| EUR_JPY | 1.33 / 1.62 | 1.32 / 1.64 | 1.27 / 1.53 | 1.29 / 1.57 | 3.06 / 8.86 |
| AUD_USD | 1.93 / 2.17 | 1.93 / 2.21 | 1.87 / 2.13 | 1.94 / 2.21 | 2.98 / 7.73 |

**属性による差**:

- 夏時間と冬時間の差は小さい（EUR_USD 1.38 対 1.40、USD_JPY 1.19 対 1.21）。
- 曜日の差も小さい。
- 定時の発表の slot（08:30・10:00 の bar の終値）は、通常と同程度。M15 の終値は発表の瞬間の後の quote なので、発表の瞬間の拡大は捕まえていない。

**1.0 bp の区別**（all-in = spread + 0.5 bp ≤ 1.0 の bar の割合）:

| 区分 | cell の数 |
| --- | --- |
| NEVER | 212 |
| MOMENTARY（< 5%） | 8 |
| PARTIAL / CONTINUOUS | 0 |
| 最大の割合 | 0.05%（GBP_AUD の NY 10 時台） |

**cost の floor**: 主要な pair で all-in の往復 約 1.6〜1.9 bp。cost は、gross − 現実の all-in の cost で評価した（1.0 bp を絶対の条件にしない）。

**限界**:

- M15 の終値の snapshot だけで、bar の中の spread の最小は捕まえていない。
- 実約定・slippage・拒否の data は無く、slippage 0.5 bp は推定。
- order の種類（指値など）の効果は測っていない（#475 では passive の執行は cost を上げた【記録】）。

## 12. Data acquisition

**0 package**。候補が 0 なので、E の期間（2010〜2016-05）の取得も、Role D の確認も行っていない。

## 13. Data provenance

| 段階 | 記録 |
| --- | --- |
| F0 | `53d5d9f`（2026-10-11 20:24 JST）。仮説の生成と cost の測定の前 |
| Track B の code | commit の後に実行（head `5fc223f`、dirty 0、command `python -X utf8 -m scripts.research.fx_frontier.track_b_cost`、2026-10-11T11:25:41Z）。記録に入力の content hash（20 pair）・code の sha256・slippage の仮定を保存 |
| Track B の記録 | `66064b4`、sha256 `7491242f…` |
| Track A | Role H の出力を【A】として commit。Role H は別の context で、価格の data を読んでいない（指示の文面と出力は【A】） |

## 14〜23. Empirical component results 〜 H vs G

**該当しない**。候補が 0 で、次のどれも実行していない。

- 実証（§14）
- 多重性の補正（§15）
- 独立な推定（§16）
- 生き残った family（§17、0）
- 共分散（§18）
- Architecture H の統合（§19）
- system の実現性（§20）
- system の prior（§21。PR #506 の契約は維持）
- P2（§22）
- H vs G（§23）

## 24〜26. Formal system freeze / Fresh prereg draft / Execution validation plan

**該当しない**（FRONTIER-E に到達していない）。

## 27. Independent reviews

（下に記録する。）

## 28. Governance compliance

| 項目 | 状態 |
| --- | --- |
| fresh・OOS・dead・forward | 読んでいない（Track B は承認済みの guard 付きの route だけ） |
| 取引・account の変更・broker の接続 | 無し（OANDA の API も使っていない） |
| data の取得 | 0 |
| target の return の読み取り | 無し（Track A は data を見ず、Track B は spread だけ） |
| 予算 | 候補の生成 7（≤ 10）、実証 0。延長なし |
| indicator・ML・交互作用の探索 | 無し |
| 事前登録の順序 | F0 は仮説の生成と cost の測定の前。F0 の erratum は記録だけで、事前登録は変えていない |
| HOLD の裁定 | sha256 を test で固定（不変） |
| FX のみ | はい |

## 29. Final verdict

**FRONTIER-A — `NO_ORIGINAL_MECHANISM_SURVIVES`**（desk power infeasible / candidate 0 で STOP）。

- state は **`FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE` に戻る**。
- STOP の後に、予算を足して候補を増やすことはしない。

**Human の目的に対する示唆**（判定ではなく、次の判断の材料）:

1. **原因は data の長さではなく、効果の大きさと cost の比である**。cost / σ が 0.06〜0.08 の intraday では、事前に予測できる original な効果は、その数倍の大きさが要る。
2. **cost の側の改善**（all-in の往復が 1 bp 以下になる執行）は、Track B の実測では、現在の OANDA の retail では観測されない。
3. したがって、FX の intraday で G4 に届く system を作るには、次のどれかが要る。
   - (a) cost の構造の大きな変化（HOLD の trigger A・D）
   - (b) 公開の情報で事前に観測できる、新しい flow の情報源（trigger C）
   - (c) 新しい独立な文献の証拠（trigger B）

## 30. Human + ChatGPT decision request

1. **FRONTIER-A を受け入れ、HOLD に戻すことを確認するか**。
2. **governance の記録**（frontier の再開の範囲と、その終了）と、**Track B の cost の frontier**（再開の trigger A の監視の基準として）を、この PR とともに merge するか。
3. **今後の方針**: FX のデイトレードの研究は、HOLD の裁定 §9 の trigger が観測されるまで止めるか。それとも、目的の制約（当日決済・retail の cost・FX のみ）のどれかを見直すかを、Human が別に判断するか。

---

**STOP（指示 §48: candidate 0 / desk power infeasible）。** data の取得・実証・fresh・取引には進まない。Human + ChatGPT の承認なしに merge しない。
