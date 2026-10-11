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
| **Track B（execution の cost の frontier）** | seen の 2021-04 … 2025-12 の M15 bid / ask の spread を測った。最も低いのは USD_JPY の London fix の時刻の中央値 1.13 bp で、all-in の往復は約 1.63 bp（slippage 0.5 bp の推定を含む）。**all-in ≤ 1.0 bp は、20 pair × 11 の時間帯の 220 の cell のうち 212 で一度も無く、8 で一瞬（bar の 0.05% 以下）だけ**。HOLD の再開の trigger A（all-in ≤ 1.0 bp の継続）も、**この OANDA の pricing の tier では**観測されない（他の業者・口座は測っていない） |

**所見**（Role H が見つけ、review で範囲を絞った。【A】§7）:

- **事前登録した 50% の haircut と、Role H の g の prior の下で**、日次の intraday の候補が gate に届くには、cost の無い gross で pair あたり年率 Sharpe 約 2.2〜3.7 が要る（breadth と保有による）。haircut が無ければ約 1.9。
- 公表された最も強い intraday の FX の効果（KMW の fix の W 字）は、cost なしで 1.24〜1.82。
- **判定は haircut に依存する**。h = 1・V = 1 なら H-07 は 0.78 で **PF1〜PF4 を全て通る**。H-07 を除外しているのは、h = 0.5 と、F9 の horizon variant という分類（FX microstructure の review は別の mechanism と読めると指摘）だけである。
- **FRONTIER-A は desk の段の判定で、どの候補も data で反証されていない**。

**意味**: FX のデイトレードが不可能という判定ではない。この OANDA の pricing の cost と事前登録の haircut の下では、事前に検出できる大きさの original な mechanism を、根拠を持って予測できなかった。

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
- H-07 は c = 2.2 で約 +0.19、H-05 は c を 1.28 下げて 1.72 にしても約 +0.11（c = 1.28 にしても約 +0.14）。**どの候補も 0.58 に届かない**。
- **逸脱の開示**: Role H の c は Cycle 1 / R-A2b の既報の集計で、F0 §5 が定める Track B の値ではない（Track B は並行して走った）。上の置き換えで判定は変わらない。

**Optimistic の列と haircut**【A】§7.1:

- 【A】§2 の Optimistic は h = 1 に加えて g も上の prior に変えている（H-02 g = 6 など）。h = 1 だけでは H-01 −2.31、H-02 +0.25、H-03 +0.19、H-04 −1.58、H-05 +0.25、H-06 −1.00、**H-07 +0.78**。
- **判定は事前登録の 50% の haircut に依存する**。h = 1・V = 1 なら H-07 は PF1〜PF4 を全て通る（0.777 ≥ 0.761、PF3 は 1.97 ≥ 1.645、PF4 は n = 15 > 12 で該当しない）。他の 6 候補は h = 1 でも PF1 を通らない。

**gate の性質**【A】§7.4:

- m ちょうどの効果では、PF2・PF3 は S = 4.67 年・E = 6.4 年で満たせない（V = 6 の検出力は S で約 0.13〜0.19、E で約 0.18〜0.25）。この読み方では FRONTIER-A は設計でほぼ決まっていた。
- m = 1/√3 は緩い。#506 の prior の縮小の後で G4 に届くには、真の Sharpe 約 1.1 が要る。
- Role H は gate を知った上で予測した（偽陰性の risk）。rubric の基準 11 は gate を採点に入れており循環している。

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

**cost の floor**: EUR_USD・USD_JPY・GBP_USD・USD_CAD・EUR_JPY で all-in の往復 約 1.6〜1.9 bp、AUD_USD で約 2.4 bp。cost は、gross − 現実の all-in の cost で評価した（1.0 bp を絶対の条件にしない）。

**限界**:

- M15 の終値の snapshot だけで、bar の中の spread の最小は捕まえていない。
- 実約定・slippage・拒否の data は無く、slippage 0.5 bp は推定。
- order の種類（指値など）の効果は測っていない（#475 では passive の執行は cost を上げた【記録】）。
- **この OANDA の pricing の tier だけ**の測定である。日本の国内の retail の業者の原則固定の spread（USD/JPY 0.2 銭 ≈ 0.14 bp）や、手数料型の口座は測っていない。そこでの実約定の質（slippage・拒否・API の可否）も不明。
- **曜日の filter が日曜の夕方の bar を落としている**（`weekday < 5`）。週末の再開（H-07 の窓）は測っていない。
- `london_fix_1045_1115` は ET で固定している。US と UK の夏時間がずれる週（年に約 3 週）は、WMR の fix が 12:00 ET、ECB の参照 rate が 09:15 ET になり、この bucket から外れる。
- MOMENTARY の 8 cell（GBP_AUD、0.5 bp 未満の spread）は、quote の artefact の可能性が高い。
- `spread_open_bp` は計算したが、記録の統計には使っていない。
- Tokyo の bucket（19:00〜02:00 ET）は、仲値の slot（19:55 / 20:55 ET）の近似でしかない。

**F0 §8 からの erratum**: 実装した bucket は F0 §8 と違う。pre_london（02:00〜03:00）を足し、NY 10 時台を 10:00〜10:45、London fix を 10:45〜11:15、NY の午後を 11:15〜16:00 にした（F0 は「11:00 前後」「12:00〜16:00」）。境界は bar の終わりの時刻。測定の前に code を commit した（`5fc223f`）が、F0 の文面は変えていない。

## 12. Data acquisition

**0 package**。候補が 0 なので、E の期間（2010〜2016-05）の取得も、Role D の確認も行っていない。

## 13. Data provenance

| 段階 | 記録 |
| --- | --- |
| F0 | `53d5d9f`（2026-10-11 20:24 JST）。仮説の生成と cost の測定の前 |
| Track B の code | commit の後に実行（head `5fc223f`、dirty 0、command `python -X utf8 -m scripts.research.fx_frontier.track_b_cost`、2026-10-11T11:25:41Z）。記録に入力の content hash（20 pair）・code の sha256・slippage の仮定を保存 |
| Track B の記録 | `66064b4`、sha256 `7491242f…` |
| Track A | Role H の出力を【A】として commit。Role H は別の context で、価格の data を読んでいない。起動は 2026-10-11T11:24:40Z（F0 の commit の 37 秒後）。指示の文面は【A】§6 に逐語。**web 検索の検索語は記録していない** |
| 順序 | master の CI（#507 の merge）は 11:23:36Z 頃に完了し、F0 の commit は 11:24:03Z。F0 `53d5d9f` は Track B の code の commit `5fc223f` の祖先 |
| seed | 該当なし（Track B は決定的、乱数を使わない） |
| 環境 | repo の `.venv`（Python 3.12.10、pandas 3.0.2、numpy 2.4.4。この報告の作成時に確認、Track B の記録自体には保存していない）。Windows 11 |

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

4 つの役割を、別の context の agent で、互いの結論を渡さずに行った（対象 `b5bf0ff`）。**BLOCKER は全ての役割で 0**。

| 役割 | 主な所見 | 対応 |
| --- | --- | --- |
| Quant | 全ての s_B と §10 の −0.07 を再現。系統的に悲観に寄せた形跡は無い。Optimistic の列が定義（h = 1）と合わない | 【A】§7.1 で入力を開示し、h = 1 だけの値を追加 |
| Statistician | m ちょうどの効果では PF2・PF3 は満たせない（設計でほぼ決まる）。m = 1/√3 は posterior の縮小の下では緩い。判定は haircut に依存。rubric の基準 11 が循環。「0.2〜0.8 bp」の記述が不正確 | §10・【A】§7.3〜§7.4 に開示。記述を訂正 |
| FX microstructure | 配管の地図の時刻は正しい（夏時間のずれの週は除く）。H-01〜H-07 の棄却は公平。「構造的」は haircut の効果。cost の結論は OANDA の tier に限る。Track B は日曜を測らず、London fix の bucket は夏時間のずれの週に外れ、GBP_AUD の MOMENTARY は artefact の可能性 | §1・§11・§29 の範囲を絞り、限界を追加 |
| Adversarial governance | fresh・OOS・取引・HOLD の裁定は守られている。Role H の指示の文面が【A】に無いのに §13 が「ある」と書いていた。cost の入力が F0 §5（Track B）からの逸脱。Track B の bucket が F0 §8 と違う。web 検索の記録が無い | 指示の文面を【A】§6 に逐語で追加し、§13 を訂正。逸脱と erratum を §10・§11 に開示 |

- 全ての修正は記録と開示で、記録の JSON（上書きを拒否する）と F0 は変えていない。判定は変わらない。
- 修正の後の再監査は、別の新しい context で行った（下の 27a）。

### 27a. 修正の後の再監査

対象 `a43cd94`。別の新しい context で、source と数値を再計算した。**BLOCKER 0、REQUIRED FIX 2、NON-BLOCKING 5**。

| 区分 | 所見 | 対応 |
| --- | --- | --- |
| REQUIRED | 【A】§7.1 の「h = 1 でも PF2 を通る候補は無い」は誤り。H-07 は h = 1・V = 1 で PF1〜PF4 を全て通る | 【A】§7.1・§7.3、本報告 §1・§10 を訂正 |
| REQUIRED | H-05 の「c を 1.28 下げても約 +0.14」は誤り（1.72 にすると +0.11。+0.14 は c = 1.28） | 訂正 |
| NON-BLOCKING | 27a の参照先が無い | この節 |
| NON-BLOCKING | V = 6 の検出力 0.13〜0.19 は S だけ（E は 0.18〜0.25） | 両方を記載 |
| NON-BLOCKING | §1 の trigger A の記述が OANDA の tier に限定されていない | 限定した |
| NON-BLOCKING | cost の floor 1.6〜1.9 bp に AUD_USD（約 2.4）が入らない | pair を明記 |
| NON-BLOCKING | 【A】§5 の「構造的」は Role H の原文のまま | §7.3 に h = 1 での H-07 の通過を追記 |

- 再監査は、全ての s_B・h = 1 の値・Optimistic・検出力・PF2 の erratum・Track B の 30 の cell・class の数・記録の sha256・code の sha256・期間の guard・HOLD の裁定の hash・commit の順序を、独立に再現・確認した。
- 判定 FRONTIER-A（事前登録の h = 0.5 の下で）は変わらない。

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

**FRONTIER-A — `NO_ORIGINAL_MECHANISM_SURVIVES`**（desk power infeasible / candidate 0 で STOP。**desk の段の判定で、実証していない**）。

- state は **`FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE` に戻る**。
- STOP の後に、予算を足して候補を増やすことはしない。

**Human の目的に対する示唆**（判定ではなく、次の判断の材料）:

1. **原因は data の長さだけではなく、事前登録の haircut の下での効果の大きさと cost の比である**。cost / σ が 0.06〜0.08 の intraday では、事前に予測できる original な効果は、その数倍の大きさが要る。判定は desk の段のもので、候補は data で反証されていない。
2. **cost の側の改善**（all-in の往復が 1 bp 以下になる執行）は、Track B の実測では、**この OANDA の pricing の tier では**観測されない。他の業者・口座の種類は測っていない。
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
