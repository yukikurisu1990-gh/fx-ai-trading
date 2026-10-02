# FX INTRADAY SYSTEM DISCOVERY — 研究方針の再設計（2026-10-02、design-only、第 2 稿）

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` · `PRODUCTION_READINESS_NOT_CLAIMED`.**

Human + ChatGPT の指示（FX のデイトレードを目標に保つ研究方針の再設計）への設計報告。独立 review 2 役の指摘を全て反映した第 2 稿である（§15）。

**この文書でしていないこと**: alpha・backtest・学習・data の取得・fresh / OOS / dead / forward の読み取り・broker・CFD。

**数字の出所**:

- Stage 0 の記録（`artifacts/research/patsd_stage0/stage0.json`）の pair 別の spread と vol を使った、signal を使わない算術
- 過去の研究の記録（§3）

**維持する結論**:

- 旧 programme: `LONG_TERM_HOLD` / `NO_FURTHER_SEEN_DATA_ALPHA_SEARCH`
- PATSD Stage 0: `STAGE0_RED_RETURN_TO_HUMAN`（変えない）

**例外の明示**: seen 2021–2025 を推定の block に使うことは、それ自体が `NO_FURTHER_SEEN_DATA_ALPHA_SEARCH` の例外である。Human の裁定を要する（§16 の 3）。

**位置づけ**: この再設計は PATSD の中の FX intraday の再設計（以下 FXID）である。Stage 0 の RED を解除するものではない。seen data の上の alpha 探索は、どの形でも Human の明示の裁定を要する。

**表記**:

- 「§N」はこの文書の節、「指示 §N」は依頼文の節を指す。
- 確認できる Sharpe は片側 5%・検出力 80% で計算する。
- 勝率への換算は ±σ の 2 値の損益を仮定する（正規分布なら約 1 pt 低い）。

**PR #499**: 2026-10-02T00:01:55Z に merge した（head `7139076`、CI success 2/2、merge `11ebcfc`）。

---

## 1. Executive Summary

**結論**: FX のデイトレード（H1 の状態 + M15 の entry、2〜8 時間保有、NY 17:00 の rollover の前に決済）に、研究の余地は**残っているが狭く、今ある seen data だけでは確認まで届かない**。

**事実**（§3）:

- **H1 の trend 方向に M15 で entry する system は、高回転の形で試した**（Round 1 の `F_mtf_agreement`、年約 2,186 往復）。gross −77.5 pip / pair（約 734 回の決済で、1 回 約 −0.1 pip、ほぼ 0）。**選択的な 2〜8 時間の設計を否定するものではない**が、正の gross も示さなかった（出所は gitignore された `artifacts/track_a_scratch/exploratory_round_1/round1_families_pooled.json` で、commit された文書には無い）。
- seen の M15 の return の特徴は、1〜192 bar の全ての horizon で IC が負だった。
- 分散比 VR < 1 は全ての horizon で成り立った（z −14.7、panel をまたいで再現）。**数時間の horizon では、継続ではなく反転の側に構造がある。**
- session / vol / spread / ADX の gate は、net を上げなかった。
- 4 時間で cost を超える IC は 8.7〜12.5%（Round A）。4 時間の IC がこれを超えた観測は無い。5 日の horizon では測られた |IC| が損益分岐（約 1.7%）を超えたが、**符号が持続しなかった**（Round A T1）。
- event の日は、動きが 1.13〜1.63 倍になる一方で spread は 1.01〜1.05 倍にしかならず、cost の超過の比は 1.00（H-018 / H-019）。**event の回避で cost の効率は上がらない。**

**算術**（§4・§8）:

- 4 時間保有の cost / 動き は 8%（中央値）〜12%（平均 + slippage）。
- portfolio の net Sharpe 1.0 に要る 1 trade の gross の期待値は、**動きの 12.5〜19%**（breadth と cost の基準による）。
- 選択・推定・fresh を通して最後まで通る確率:

  | 真の Sharpe | seen だけ | pre-2016 の intraday を使う場合 |
  | --- | --- | --- |
  | 1.0 | **約 2%** | 約 15% |
  | 1.5 | 16% | 64% |

**推奨: 案 A″（data の実現性を先に確かめ、それが立つ場合だけ最小の規則研究へ進む）。**

- **cycle 1 は alpha を計算しない**。中身は次の 2 つ。
  - (a) **pre-2016 の FX intraday の bid / ask 履歴の入手可能性の机上調査**（入手先・bid / ask の有無・解像度・ToS・保護期間の境界・時刻付きの指標 calendar）
  - (b) seen の M15 cache の signal を使わない統計（時刻ごとの vol・開場と発表の窓の spread・高値と安値の幅・event の時刻の breadth）。新しい承認の区分（R-A2）で行う。
- **cycle 2（規則研究）は、pre-2016 の data が得られることを前提条件にする。** seen だけで進めるなら、Sharpe ≳ 1.3〜1.5 の system しか検出できないことを Human が明示的に受け入れる必要がある。

**候補**（§7）:

- **S1（session の始まりの継続）は、測られた事実（VR < 1、IC 負）と逆向きの賭け**で、事前の見込みは負である。pre-R1 の Phase 9.17 で提案され、走らなかった「session opener momentum」の直系でもある。
- **S2（USD の定時発表の後）は、時刻付きの calendar が USD の慣例の時刻（08:30 ET）にしか無い。**
- どちらも弱い候補として、事前に符号を固定した 1 回の検定に限る。

**Q5**: portfolio の net Sharpe 1.0（vol 5% で年 5%）に要る 1 trade（4 時間保有、1 pair 年 100 回）の gross の期待値（bp）。

| 実効の breadth k ＼ cost の基準 | median 1.70 | 平均 2.06 | 平均 + slippage 2.56 |
| --- | --- | --- | --- |
| k = 5 | 2.65 | 3.01 | 3.51 |
| k = 3 | 2.92 | 3.28 | 3.78 |
| k = 2 | 3.20 | 3.56 | 4.06 |

## 2. Human の目標と研究上の制約

| 要素 | 目標 | 研究上の扱い |
| --- | --- | --- |
| 市場 | FX のみ、OANDA retail | 変えない。CFD は提案しない |
| 環境の判断 | H1 | M15 bid / ask から時計に揃えて集約する（`patsd_stage0/data.py` に実装がある）。entry の時点で閉じた H1 だけを使う |
| entry | M15 | M15 の終値で bid / ask の約定 |
| M5 | 必要性が示せる場合だけ | 根拠: 約定順序の曖昧さの上限（§4.1） |
| 保有 | 2〜8 時間 | 設計上の範囲。**探索の軸にしない**（cycle 2 では事前に 1〜2 点） |
| 決済 | 当日中、rollover の前 | 取引日は NY 17:00（OANDA の rollover、UTC では夏 21:00・冬 22:00）を区切りにする。NY 16:45 までに全て決済する。rollover の前後 30 分と週末の close の前は entry しない |
| 方向 | long / short | 各候補の符号は事前に固定する。結果を見て反転しない |
| 頻度 | 事前に決めない | 取引しない日を認める |

**基本構想の検討**:

- **利点**: 当日決済は financing（swap）を払わない。H4 の swing では markup 1% で約 0.12 の Sharpe の drag が付くが、それが無い。
- **欠点**: 保有が短いほど cost / 動き が大きい。測られた VR < 1 で、数時間の σ は √時間 の推定より小さい（EUR_USD の H4 で 19.4 bp 対 20.4 bp）。cost の比は表より少し悪い。
- **構想は合理的である。ただし、測られた構造（反転・IC 負）と、継続の仮説は衝突する。**

## 3. 過去研究の監査結果

**C-8 の扱い**: pre-R1 の数値（Phase 9 / 22〜29・ML Step 4・stage log）は C-8 により、design の根拠・prior・baseline に使わない。この文書では文脈として示すだけで、除外の根拠は post-R1 の結果に置く。

### 3.1 post-R1（seen、根拠として使える）

| 研究 | 中身 | 結果 |
| --- | --- | --- |
| Round 1（#464、2025-04 … 12） | 15 規則（EMA / ADX trend・breakout・mean reversion、**H1 trend と M15 entry の一致**、**HTF context breakout**、range breakout）、session / ATR / ADX / spread の gate、meta gate、ML 57 変種、walk-forward 52 | `F_mtf_agreement` gross −77.5 pip / pair（position の変化 28,444 回、決済した trade 14,685）。`F_htf_context_breakout` −104.7。`B_range_breakout_24_12` −140.7。**return の特徴の IC は 1〜192 bar の全てで負**。gate は全て net を下げた。「1 日のうちに判断し直すもので生き残ったものは無い」。edge は US session に偏っていた（前半だけ） |
| Round A（#468、3 panel） | 39 の条件 cell（ATR・vol の拡大・D1 trend・range の位置・極端な動き） | 0/39。cost を超える IC は 4 時間で 8.66〜12.50%、12 時間で 5.04〜7.23%。**5 日の horizon では測られた \|IC\| が損益分岐（約 1.7%）を超えたが、符号が持続しなかった**（4 時間の IC が 8.7% を超えた観測は無い） |
| Round B′（#469） | 価格経路の構造 | VR < 1（z −14.7）が実在する。最良の線形の 96 bar 予測は損益分岐の 6〜16% |
| Monetizability（#470） | 線形の取引選択 | 収穫できない |
| CPI（#472） | 発表後 1 時間 / 4 時間 | panel 間で符号が反転、NOT_SUPPORTED |
| #473（未 merge） | USD の survey の surprise、1 時間 | 検出力のある null |
| H-018 / H-019（rerank） | event の日の動きと spread | 動き 1.13〜1.63 倍、spread 1.01〜1.05 倍、cost の超過の比 1.00 |
| clock flow（#474） | WMR fix・Tokyo fix・London open・NY cut・月末の 1 時間の窓（**ランダムな方向で frontier だけ**） | 毎日の窓には損益分岐の IR 4.1〜58.7 が要る（58.7 は cost のために調べた rollover の cell）。検出力があって払える cell は **月末の London open の前の窓**の 1 つだけ |
| Track 3（#475） | 指値で待ってから成行 | cost が上がる（C′/C 1.28） |
| Stage 0（#499） | cost の実測 | M15 の spread の中央値 1.70 bp（1.20〜2.75）、pair の平均の中央値 2.06 bp、H1 / M15 の vol 比 1.96 |

### 3.2 pre-R1（C-8、文脈だけ）

- ≤ 1 時間の保有で、LightGBM の方向・EV label・triple barrier・meta-label・session filter・Donchian・87 の exit を試し、全て REJECT か INVALID。
- 9.X-H は event の近さの特徴量（`cal_in_pre_event`）を試し、NO ADOPT。9.X-L は時刻の除外を試した。
- **Phase 9.17 は「session opener momentum（London 7〜9 UTC）」を提案して先送りし、走らなかった**（S1 の直系）。
- Family A（`docs/design/m15_first_cost_hurdle_aware_preregistration_design.md`）は M15 の trend / 継続の family で、継続の仮説は Round 1 で検定された。**走っていないのは、その cost の下限付きの barrier label だけ**である。

### 3.3 確認できた事実と、新しい仮説

| 種類 | 中身 |
| --- | --- |
| 事実 | 一般的な指標の trend / breakout / MTF の一致は、M15 の intraday で gross から負。数時間の horizon の構造は反転側（VR < 1、IC 負）。条件付けは net を上げなかった。event の日の cost の効率は変わらない。cost は rollover を除いて時刻でほぼ平坦 |
| 仮説（未検定） | (a) 時計（session の始まり）に錨を下ろした継続（**事実と逆向きで、事前の見込みは負**）。(b) USD の定時発表の後の数時間の継続（文献では drift は数分〜1 時間程度。数時間の機構の説明が要る）。(c) 当日決済で financing が消える分の経済性の改善（edge ではない） |

## 4. M15 デイトレードの経済性

（signal を使わない算術。Stage 0 の pair 別の値の中央値。σ_h = M15 の bar の vol 5.30 bp × √(4h)。VR < 1 なので実際の σ_h はこれより少し小さい。）

| 保有 | σ_h | cost / σ_h（median 1.70） | 同（平均 + slippage 2.56） | drag（1 pair、年 50 回） | 年 100 回 | 年 250 回 |
| --- | --- | --- | --- | --- | --- | --- |
| 2 時間 | 15.0 bp | 0.113 | 0.171 | 0.80 | 1.13 | 1.79 |
| **4 時間** | **21.2 bp** | **0.080** | **0.121** | **0.57** | **0.80** | **1.27** |
| 6 時間 | 26.0 bp | 0.065 | 0.098 | 0.46 | 0.65 | 1.03 |
| 8 時間 | 30.0 bp | 0.057 | 0.085 | 0.40 | 0.57 | 0.90 |

（drag = cost / σ_h × √年間 trade 数、median の cost。trade 単位で vol をそろえた場合の、1 pair の年率 Sharpe の低下。）

**指示 §3 の 3 区分**:

1. **M15 の高頻度売買**（Stage 0 の想定: 約 5 時間保有で常時建玉、年約 1,250 回）: drag 2.69。**構造的に負ける。**
2. **H1 の状態 + M15 entry、2〜8 時間、条件を満たす日だけ**（1 pair 年 50〜100 回）: drag 0.40〜1.13。**参加を絞れば cost は越えうる水準。ただし予測力が要る。**
3. **数日保有の swing**（H4、Stage 0 の想定: 5 日保有で年約 62 往復）: drag 0.13 + financing 約 0.12。参照だけ。

**pair の差**（cost / 4 時間の σ）:

- 最良: USD_JPY 0.047、EUR_JPY 0.056、GBP_USD 0.063
- 最悪: AUD_NZD 0.172、EUR_CHF 0.107、EUR_GBP 0.106

**cost の基準の注意**:

- 候補が取引する時間（session の始まり・発表の後）は、spread と slippage が広い時間である。median は楽観側になる。
- cycle 1 で、開場と発表の前後 ±15 分の spread を測る。

### 4.1 デイトレード固有の採算性の計画

| 項目 | 計画 |
| --- | --- |
| 取引機会 | 参加率と trade あたりの gross の関係は、cycle 2 で事前に決めた 2 点（全機会 / 上位の条件）だけで比べる。同じ参加率のランダムな skip を対照にする。**参加率の点も試行に数える** |
| 必要な期待値 | Q5（cost 3 基準 × breadth 3 段）。採用には cost × 1.5 でも net 正を要求する |
| session | 東京 / London / NY の 3 区分だけ。DST に正しい時計で定義する。`clock_flow/clock.py` は london_open を持つが、**Tokyo と NY の開場は定義が要る** |
| 決済 | 固定時間（事前の 1〜2 点）・対称の ATR barrier 1 種・NY 16:45 の強制決済。rollover の前後 30 分と週末の close の前は entry しない |
| risk | 定時の発表をまたぐか否か（S2 以外）。gap と急変は、最悪の M15 bar の分布で stress する。**MaxDD ≤ 15% は portfolio の段階で確かめる** |
| 約定の不確実性 | TP と SL が同じ M15 bar の中にあるときは、**SL が先**と置く（保守側）。曖昧さの**上限**は、高値 − 安値 ≥ barrier の幅の 2 倍の M15 bar の割合（pair × 時刻）で、経路を使わずに測る。上限が 5% を超える設計だけ、M1 の承認の対象にする |
| 使える情報 | entry の時点で確定した bar だけを使う |
| edge の単位 | cost の効率の層（S3）が Sharpe を上げるのは、**edge が σ に比例する場合だけ**。edge が bp で一定なら、高 vol の時間に寄せても Sharpe は上がらない。この仮定を明記する |

## 5. H1 + M15 構成の合理性

- **H1 が経済的に意味を持つ条件**: H1 の状態によって、M15 の entry の後 2〜8 時間の条件付きの期待損益が変わること（trade が減るだけでは足りない）。
- **区別の方法**: 同じ参加率のランダムな skip と比べる。条件の内と外の gross の差を推定する。cost の総額の減少と、trade あたりの edge の増加を分ける。
- **H1 を方向の判断に使う構成は、既に負**（Round 1）。
- H1 を状態（予定された情報の到来・vol の水準）の判断に使う構成だけが未検定。ただし event の日の cost の効率は変わらない（H-018 / H-019）ので、効果は edge の側から来る必要がある。

## 6. 未検定領域と既存研究の重複

| 構造（指示 §5） | 判定 | 残すか |
| --- | --- | --- |
| A. H1 の方向 + M15 entry | 重複大（Round 1 の MTF 一致・HTF breakout は gross 負） | 方向の判断としては除外 |
| B. 条件付きの intraday 取引 | session / vol / spread / ADX の gate は重複大。event の近さの特徴量は pre-R1 で NO ADOPT。event の回避は cost の効率を上げない（H-018 / H-019） | **回避の層は除外**。USD の発表の後の継続（S2）だけを、弱い候補として残す |
| C. entry / exit system | ≤ 1 日で判断し直す規則は重複大（Round 1）。**2〜8 時間の barrier・rollover 前の強制決済は system としては未検定** | 2〜8 時間の barrier と強制決済を、S1 / S2 の exit として残す |
| D. ML による取引選択 | 負の base の上では重複大 | 正の gross の base が出るまで保留 |

## 7. 候補戦略の比較

| 候補 | 利益の源と機構 | 事前に固定する符号 | 予想される符号 | 既存研究との違い | 棄却の条件 | data |
| --- | --- | --- | --- | --- | --- | --- |
| **S1 session の始まりの継続**（London / NY の開場後 1〜2 時間の方向に乗り、2〜6 時間保有、当日決済） | 情報と大口注文の到来の集中と、その分割執行による数時間の価格発見の遅れ | 継続（開場の値動きと同じ方向） | **負**（VR < 1、IC 負、session gate 付きの trend も負） | 開場の時計に錨を下ろす（clock flow はランダムな方向だけ）。Phase 9.17 の提案（走らず）の直系 | gross ≤ 0。**反転して使うことは禁止**（失敗した規則は反転した規則ではない） | 既存で足りる |
| **S2 USD の定時発表の後の継続**（08:30 ET の発表の 30 分後に、価格の反応の方向へ入り、2〜4 時間保有） | 解釈の分散と在庫の調整による吸収の遅れ | 継続 | 不明（文献では drift は 1 時間以内が多い） | CPI（#472）は surprise の符号を使った。こちらは価格の反応だが、**surprise の符号と強く相関する** | gross ≤ 0 | 発表の時刻は慣例（08:30 ET）。**非 USD の時刻付き calendar は無い**（Forex Factory の時刻は使えないと #477 で判明） |
| S3 cost の効率による参加の選択（層） | edge ではなく cost / 動き の改善（edge が σ に比例する場合だけ） | — | — | signal を使わない層 | — | 既存で足りる |

- **S1 の NY の開場と S2 の 08:30 ET は時間が重なり、独立な試行ではない。**
- 一般的な trend / breakout / mean reversion の再探索は除外する。ML は正の gross の base が出るまで使わない。

## 8. data と統計的検証可能性

**seen の intraday は 4.68 年**（2021-04-26 … 2025-12-28）。全ての window が旧 programme の決定 panel だった。fold 外は約 3.3 年（Stage 0 の実測 3.29 年。PATSD の設計の 3.4 年は事前の概算）。

**選択の検出力**（帰無で family-wise 10% に較正した閾値、独立な試行を仮定。試行が相関していれば閾値は下がる）。真の Sharpe ごとの、選ばれる確率:

| data | 実効の試行 | 閾値 | 真の 0.8 | 1.0 | 1.3 | 1.5 |
| --- | --- | --- | --- | --- | --- | --- |
| seen、fold 外 3.29 年 | 10 | 1.27 | 0.20 | 0.31 | 0.52 | 0.66 |
| seen、fold 外 3.29 年 | 30 | 1.49 | 0.11 | 0.19 | 0.37 | 0.51 |
| pre-2016、10 年 | 10 | 0.73 | 0.59 | **0.80** | — | 0.99 |
| pre-2016、10 年 | 20 | — | 0.49 | **0.73** | — | 0.99 |
| pre-2016、10 年 | 30 | — | 0.43 | 0.68 | — | 0.98 |

**最後まで通る確率**（選択 × 推定の block での G4 の条件 2 × fresh の検出力。推定の block は seen 4.68 年、prior は μ = 0.07・τ = 0.565 に凍結）:

| 経路 | 真の 0.8 | 真の 1.0 | 真の 1.5 |
| --- | --- | --- | --- |
| **pre-2016 で選択（試行 10〜30）→ seen で推定 → fresh** | 0.03〜0.05 | **0.13〜0.15** | 0.63〜0.64 |
| seen を 2 つに分割（2.34 年 / 2.34 年、試行 10） | 0.005 | **0.018** | 0.16 |

（fresh は 2016-06-02 … 2021-04-25 の 4.90 年。片側 5% の検出力を使った。）

**prior の τ に対する感度**（推定の block の条件 2 の通過確率、真の 1.0。全体の確率もほぼ比例して動く）:

| τ | 必要な観測 Sharpe | 推定の block の通過（真の 1.0） | 全体（pre-2016、試行 10） |
| --- | --- | --- | --- |
| 0.4 | 1.78 | 0.047 | 約 0.03 |
| **0.565（凍結値）** | **1.29** | **0.266** | **約 0.15** |
| 0.8 | 1.04 | 0.46 | 約 0.26 |

**全体の確率は τ によって約 10 倍動く。** prior の値は cycle 2 の前に凍結し、この表と合わせて Human が判断する。

**読み方**:

- **律速は選択の試行数ではなく、推定の block と prior である。** pre-2016 があれば、試行 10 → 30 でも全体はほぼ変わらない。
- seen だけの経路は、真の 1.0 の system を約 2% しか通さない。**実質的に閉じている。**
- **試行の上限**:
  - pre-2016 を使うなら **実効 20**（真の 1.0 の選択の検出力 ≥ 0.7）。
  - seen だけなら、**どの試行数でも真の 1.0 の選択の検出力は 0.7 に届かない**（試行 10 で 0.31、1 でも 0.70）。上限 10 は**導出ではなく選択**で、試行 1〜5 の方が良い。その経路は Human の明示の受け入れを要する。
- **実効の試行の定義**: max-T で較正した独立相当の数（帰無の最大値の分布から逆算）。名目の設定数ではない。
- **数えるもの**: 候補・parameter・保有・決済・条件付け・参加率の点・session の選択・pair の選択の規則・特徴量と target・model・途中で足した候補の全て。

**breadth**:

- 20 pair は独立ではない。S1 / S2 は同じ時刻に全 pair で同時に立つので、**その時刻の損益の相関は無条件の相関より高い**。
- 実効の breadth は 2〜3 まで下がりうる（Q5 の表に反映した）。cycle 1 で、開場と発表の時刻の窓で測る。

**FX の範囲の追加 data**（どれも今回は取得しない）:

| data | 効果の種類 | 説明 |
| --- | --- | --- |
| **pre-2016 の FX intraday の bid / ask 履歴**（2006-01 … 2016-05-31） | 標本の追加 | 約 10 年で、seen の fold 外の**約 3 倍**。下の表のとおり |
| M1（seen の archive、既存） | 約定順序の解像度 | R-B1 型の読み取りの承認が要る |
| tick / quote | cost の改善と執行の精度 | **予測情報ではない。tick で利益が出るとは仮定しない** |
| 実際の約定・spread（broker） | cost の実測 | paper の段階 |
| 時刻付きの非 USD の指標 calendar | 予測情報（S2 の範囲） | 無料で公式のものは無い |

**pre-2016 FX intraday の取得の詳細**:

- **境界**:
  - 終わりは **2016-05-31**。NY 17:00 の取引日では、2016-06-01 の 21:00 UTC 以降は 2016-06-02 の取引日に属するので、2016-06-01T21:00Z を上限とする案もある。
  - 年や月の単位で配布する源の 2016 年の file には、fresh の行が含まれる。**その file は取らない**か、request の段階で除外する。
  - 専用の guard を作る: 境界を日付として parse し、範囲外の timestamp を含む応答を拒否し、bulk だけの源を拒否する。
- **汚染として開示するもの**:
  - ECB の日次（1999–2016）と BIS の CPI（1994–2016）は seen。日次の解像度の知識があるが、intraday の方向への影響は小さい。
  - #497・#496 の知識。
  - 広く知られた出来事: 2008 年、2013 年の WMR fix の不正、2015 年の fix の改革（**fix の flow を変えた。S1 / S2 の非定常性**）、2015-01 の CHF の固定の解除。
- **cost**:
  - 無料の M1 の源には bid だけのものがある。
  - そこで、**pre-2016 の block では gross で選択し、net は OANDA の時代の block だけで判定する**。
- **入手経路**:
  - 無料の配布元（tick / M1。bid / ask の有無と ToS を確かめる）。
  - OANDA の API の過去の履歴は**認証が要るので Red**。broker の禁止に近い。

## 9. 新しい Selection / G4 設計

### 9.1 A: selection error の制御

- **方法**: 候補の生成から最終選択までの pipeline 全体を帰無 data で走らせ、各 replication で全候補の選択統計量の**最大値**を記録する。
- **閾値 = 帰無の最大値の分布の 90 percentile**（max-T 型）。名目の DSR の階段は使わない。
- **Monte Carlo**:
  - 閾値の推定に 1,537 回（誤合格率 10% を ±1.5 pt で）。独立の検証にも 1,537 回。
  - 1,000 回では ±1.86 pt になることを開示する。
- **帰無 data**:
  - 主: seen の M15 の return に、時点ごとに全 pair 共通の ±1 を掛ける。**seen の return を読むので、承認の範囲に入れる。**
  - 感度: 日を単位にした再標本化、または時刻を動かした event の calendar（第 2 の帰無の誤指定を確かめる）。
- **10% の妥当性**: discovery の段階の誤合格は、後の独立な推定と fresh で捕まえられる。fresh は片側 5% のまま。
- **Stage 0 の事後の感度（p* ≈ 0.8 など）は流用しない。**

### 9.2 B: 真の効果量の推定

- **二重処理**: 同じ data で選択と推定をするなら、選択の補正と縮小を重ねるのは二重である。
- **新しい設計**: 選択と推定に別の block を使う。

| block | 用途 |
| --- | --- |
| 選択 | pre-2016（gross で） |
| 推定 | seen 2021–2025（net で。選択に使っていないので、選択の補正は要らない。外部の prior による縮小だけを掛ける） |
| confirmation | fresh |

- **開示**: S1 / S2 の仮説は、seen 2021–2025 の結果（Round 1 の session の表・clock flow の cell・CPI の panel）を知って作った。**推定の block は、仮説の生成からは独立でない。**
- **prior**（cycle 2 の前に値を凍結する）:
  - μ = 0.07、τ = 0.565（programme の値。standalone の日次 mechanism から作ったので、参照クラスが違う）。
  - 条件 2 は τ に敏感で、τ = 0.4 / 0.565 / 0.8 の通過確率を §8 に示した。

### 9.3 G4（fresh を使う条件）

**fresh を提案してよいのは、全てを満たすとき**:

1. 9.1 の較正した選択を通っている。
2. 推定の block で、縮小した後の **P(真の net Sharpe ≥ 0.8) ≥ 0.5**（= 事後平均 ≥ 0.8。seen 4.68 年なら観測 ≥ 1.29）。**これは PATSD の G4（portfolio の縮小期待 Sharpe ≥ 1.0）を 1.0 から 0.8 へ下げる提案である**。また Stage 0 の裁定 §5 では、0.8〜1.0 は `PROMISING_BUT_BELOW_PRODUCTION_TARGET` として Human に返す帯である。下げる理由は、選択と推定の block を分けたので推定に選択の bias が乗らないこと。**採るかは Human の判断**（§16 の 3）。
3. **意思決定が変わる**: 合格なら paper へ、不合格なら FX intraday の track を止める、と事前に書いてある。
4. **fresh は programme の名前に依らない、全体で 1 回だけの予算**（ledger に記録する。新しい programme を名乗っても、予算は戻らない）。

- 旧案の条件 3（fresh の検出力 ≥ 0.6）は、条件 2 とほぼ重なる（事後平均 ≥ 0.86 と同値）ので、条件 2 に統合した。
- forward は paper の運用と執行の実測で、統計的には補助。
- fresh の汚染台帳（Stage 0 の S0-4）を維持する。S2 に関係する露出（一般常識の出来事・#472 の CPI の vintage）は個別に開示し、**S2 の event list は fresh の時期を見ずに凍結**する。

**採用の基準を揃える**:

| 段階 | 基準 |
| --- | --- |
| research candidate | 較正した選択を通り、推定の block で net > 0 が cost × 1.5 でも保たれる |
| fresh の提案 | 上の G4 |
| production | net Sharpe ≥ 1.0 の portfolio |

## 10. 研究 programme の代替案

| 案 | 研究価値 | data | 課題 | 過学習 | 検証可能性 | 負荷 |
| --- | --- | --- | --- | --- | --- | --- |
| A 最小の規則研究（seen だけ） | 低〜中 | 既存 | 時計・DST・当日決済 | 低 | **真の 1.0 で最後まで通る確率 約 2%** | 小〜中 |
| B 規則 + 条件付きの選択 / ML | 低（正の base が無い） | 同上 + 特徴量 | ML の governance | 高 | さらに低い | 中〜大 |
| C 少数のデイトレード戦略の portfolio | 中（独立な戦略が 2 本以上あれば） | 同上 | 相関の推定 | 中 | 個々の戦略が正でなければ意味が無い | 中 |
| **A″ data の実現性を先に確かめる A（推奨）** | **高（情報の価値）** | cycle 1 は机上調査と signal を使わない統計。cycle 2 は pre-2016 を前提 | 入手経路・ToS・境界・cost の転用 | 最小 | pre-2016 があれば、真の 1.0 で約 15%、1.5 で約 64% | 小 → 中 |

成功確率は付けない（指示どおり）。上の通過確率は、仮定した真の Sharpe の下での検出力である。

## 11. 推奨する研究方針

**A″。**

**理由**:

1. 一般的な intraday の規則は既に負で、数時間の構造は反転側にある。残る仮説は少数で、しかも事前の見込みは弱い。
2. seen だけの経路は、真の Sharpe 1.0 の system を約 2% しか確認まで通さない（§8）。
3. **律速は data の長さで、それは FX の範囲（pre-2016 の intraday）で緩められる可能性がある。**
4. それが得られるかどうかは、alpha を計算せずに調べられる。

## 12. 最初の研究 cycle の詳細設計

### cycle 1: `FXID_CYCLE_1_DATA_FEASIBILITY_AND_SIGNAL_FREE_MAP`（alpha なし）

| # | 項目 | 決定 |
| --- | --- | --- |
| 1 | 中心の問い | FX のデイトレードの system を、確認まで届く形で検定できる data（長さ・bid / ask・時刻）と、cost の時刻構造は揃うか |
| 2 | 通貨 pair | 既存の 20 pair |
| 3 | 時間足 | M15 bid / ask（seen）→ 時計に揃えた H1 |
| 4 | 保有 | 2・4・6・8 時間は経済性の表の行（探索ではない） |
| 5 | 戦略候補と試行数 | **0** |
| 6 | 作業 | (a) **pre-2016 の FX intraday の机上調査**（download しない）: 入手先・bid / ask の有無・解像度（≤ M15）・期間・ToS・request の境界の付け方・時刻付きの指標 calendar の有無・spread の model の作り方。(b) **signal を使わない統計**（R-A2）: 時刻ごとの実現 vol（return の SD）と spread（DST に正しい時計）、開場と発表の時刻の ±15 分の spread、高値 − 安値 ≥ 2w の M15 bar の割合（曖昧さの上限）、開場と発表の時刻の窓での pair 間の return の相関の主成分の数（breadth）。**方向や side 別の統計は出さない**。(c) 選択 pipeline の帰無の道具（合成 data。seen の return に共通の ±1 を掛けるので R-A2 の範囲）。**帰無の candidate は、signal を持たない置き換えの規則（ランダムな時刻・ランダムな side・固定の保有）だけに限る**。S1 / S2 の規則は実装しない（B′ の準備に当たるため。Stage 0 の裁定 §6 と同じ） |
| 7 | 比較対象 | — |
| 8 | cost | 終値の bid / ask の spread（pair × 時刻、開場と発表の窓）、+0.5 bp の stress |
| 9 | walk-forward | — |
| 10 | 帰無と効果量 | §9 の道具を組み、試行 1・10・20 の合成の検出力と、帰無の FWER（1,537 回）を確かめる |
| 11 | 出力 | cycle 2 の事前登録案（S1 / S2、符号は固定、保有 1〜2 点、試行の数え方、閾値、推定の block、G4、prior の値）と、`DATA_EXPANSION_PROPOSAL`（pre-2016 の intraday） |
| 12 | fresh | 使わない |
| 13 | **失敗しうる終了条件**（どれかに当たれば cycle 2 に進まず、Human に返す） | (i) bid / ask（または信頼できる spread の model）付きで、M15 以下の解像度、許容できる ToS の pre-2016 の源が無い。(ii) 開場と発表の窓の平均 spread + slippage で、必要な gross が**その窓から始まる 4 時間の実測の σ** の 15% を超える（k = 3 で）。無条件の σ では、平均 + slippage・k = 3 で既に 17.8% なので、窓の σ が無条件より約 20% 以上大きくなければこの条件に当たる。(iii) 開場と発表の時刻の breadth が 3 未満。(iv) S1 について、VR < 1 と IC 負に対して継続の符号を支える機構を書けない → S1 を外す |

### cycle 2: `FXID_CYCLE_2_MINIMAL_RULES`（cycle 1 の後。Red の承認を段階ごとに分ける）

| # | 項目 | 決定（予定） |
| --- | --- | --- |
| 1 | 中心仮説 | S1（符号固定・継続）と S2（USD 08:30 ET の後の継続）のどちらかで、当日決済の 2〜8 時間の system の gross が正で、推定の block の net が cost × 1.5 でも正 |
| 2〜4 | 対象・時間足・保有 | cost の効率の上位の pair（cycle 1 で事前に固定）、H1 + M15、保有 1〜2 点 |
| 5 | 試行 | 実効 ≤ 20（pre-2016 を使う場合）。全ての自由度を数える |
| 6 | 特徴量 | session の時刻・前の session の range・H1 の vol・発表の予定（entry の時点で確定したもの） |
| 7 | 比較対象 | 何もしない・同頻度のランダムな entry・単純な trend / mean reversion |
| 8 | cost | pair × 時刻の spread の実測、stress × 1.5 |
| 9 | data の分割 | pre-2016 で選択（gross）、seen 2021–2025 で推定（net）、fresh で確認 |
| 10 | 帰無と効果量 | §9 |
| 11 | 採用 / 棄却 | §9.3 の表 |
| 12 | fresh | §9.3 |
| 13 | 終了 | S1・S2 とも棄却なら、FX intraday の track を `LONG_TERM_HOLD` へ |

**Red の承認**（段階ごと、連鎖させない）:

1. pre-2016 の data の取得
2. 選択の block の読み取りと特徴量の導出（R-B1）
3. 選択（R-B3）
4. 推定の block の 1 回の読み取り
5. fresh（R-D）

## 13. 必要な追加情報と承認

1. **cycle 1 の承認**: 机上調査（download しない）と、R-A2（seen の M15 cache の signal を使わない統計と合成の帰無の道具。§12 の (b) と (c) に限る。方向・side 別の統計・損益は出さない）。
2. pre-2016 の取得は、cycle 1 の提案を見てから別に判断する（Red）。
3. seen だけで cycle 2 を行う場合は、「真の Sharpe ≳ 1.3〜1.5 しか検出できない」ことを受け入れる明示の裁定。

## 14. 想定される失敗原因

1. S1 の gross が負（測られた反転の構造どおり）。
2. S2 の drift が 1 時間以内で、2〜4 時間の保有では cost に負ける。
3. pre-2016 の源に bid / ask が無い、ToS が使えない、または fresh の境界で切れない。
4. 2015 年の fix の改革などで、pre-2016 と 2021 年以降で機構が変わる（非定常性）。
5. 開場と発表の時刻の breadth が小さく、portfolio の Sharpe が伸びない。
6. 推定の block の G4 の条件 2（観測 ≥ 1.29）が、真の 1.0 でも 27% しか通らない。

## 15. 独立レビュー結果

役割は 2 つ。どちらも別 session で、repo を読み直した。互いの結論は渡していない。

**Role 1（経済性・統計・研究設計）— BLOCKER 0、REQUIRED_FIX 8**

| 指摘 | 反映先 |
| --- | --- |
| R1: cost の基準が楽観側 | §1・§4 の 3 基準・cycle 1 の開場と発表の窓 |
| R2: vol の季節性は両方向に効く・edge が σ に比例する仮定 | §4.1 |
| R3: breadth を event の時刻で測る | §8・Q5 |
| R4: 試行の数え方の不整合と、上限を実際の data の場合から導く | §8 |
| R5: 最後まで通る確率が低いことの開示・prior の値の凍結 | §8・§9.2 |
| R6: fresh の予算を programme の名前に依らず 1 回に・推定の block は仮説の生成から独立でない | §9.2・§9.3 |
| R7: S1 の rename と、予想される符号・S2 の機構と data | §7 |
| R8: 失敗しうる終了条件 | §12 |

NON_BLOCKING（全て反映した）:

- pre-2016 は約 3 倍
- 非定常性
- gross で選択
- 第 2 の帰無
- 1,000 回の誤差
- Stage 0 の M15 の想定
- 勝率の仮定
- 情報 cycle の縮小
- 採用の基準の不一致

**Role 2（過去研究・実装・data・governance）— BLOCKER 1、REQUIRED_FIX 9**

| 指摘 | 反映先 |
| --- | --- |
| B-1: 約定の曖昧さの測り方が実際の価格の経路の上の first passage で、R-A の禁止に当たる | 経路を使わない上限（高値 − 安値 ≥ 2w の割合）に置き換え、主成分とともに新しい区分 R-A2 として名指しした（§4.1・§12・§13） |
| R-1: S1 は事実（VR < 1、IC 負）と逆向き | §1・§7 |
| R-2: rename 台帳の漏れ（Phase 9.17 の session opener、clock flow の月末の cell、H-018 / H-019、9.X-H、#473） | §3・§7 |
| R-3: S2 の data（非 USD の時刻付き calendar は無い）・S1 と S2 は重なる | §7 |
| R-4: cycle 2 で Red の承認が連鎖している | §12 |
| R-5: 推定の block の独立性 | §9.2 |
| R-6: 「合成 data だけ」の表現・programme の位置づけ | 冒頭・§9.1 |
| R-7: 事実の訂正（約 3 倍、IC の主張を 4 時間と符号の持続に限定、B′ の 6〜16% の範囲、Family A の正確な記述） | §1・§3・§8 |
| R-8: C-8（87 cell を除外の根拠にしない） | §3・§6 |
| R-9: pre-2016 の境界（2016-05-31、年や月の file、NY 17:00）・専用の guard・汚染（BIS CPI・2013 / 2015 の fix）・OANDA の API は Red | §8 |

NON_BLOCKING（全て反映した）:

- 28,444 は position の変化
- 勝率
- EUR_USD の pip 換算の例を削除（§2 の H4 の vol の例は残した）
- √時間 の過大評価
- H1 の塊の drift
- `clock.py` に NY と Tokyo の開場が無い
- 58.7 は rollover の cell

**再監査**（第 2 稿を、別の新しい context で読み直した）

- 上の指摘は全て RESOLVED（BLOCKER B-1 を含む）。一部は PARTIAL で、下で解消した。
- **新しい REQUIRED_FIX 6 件**（全て反映した）:

| 指摘 | 反映先 |
| --- | --- |
| N1: 新しい G4 は PATSD の G4（1.0）を 0.8 へ下げることになり、それを開示していない | §9.3・§16 の 3 |
| N2: 帰無の道具の candidate を、signal を持たない置き換えの規則に限る | §12 |
| N3: τ の感度の表を示す。全体の確率が約 10 倍動く | §8 |
| N4: IC の horizon の混同（損益分岐を超えたのは 5 日の IC） | §1・§3.1 |
| N5: `F_mtf_agreement` は高回転の形の、ほぼ 0 の gross で、選択的な設計を否定しない（出所は gitignore された artifact） | §1 |
| N6: seen だけの上限 10 は導出ではなく選択 | §8 |

- NON_BLOCKING（全て反映した）:
  - 真の 0.8 の確率を 0.03〜0.05 に
  - fresh の長さ 4.90 年
  - 終了条件 (ii) の σ の定義
  - swing の想定を Stage 0 に合わせた
  - EUR_USD の記録の整合
  - fold 外の長さの説明
  - seen を推定に使うことは例外であること
  - Family A の出所

**lead の判断**

- 全ての指摘を証拠で確かめて受け入れた。
- §8 の最後まで通る確率は、lead が独立に再計算して一致した（pre-2016 で真の 1.0 は 0.15、seen だけで 0.018）。
- 両役とも、seen だけの alpha の cycle は確認まで届かず、次の判断は pre-2016 の data の実現性だと結論しており、lead も同意した。
- 未解決の意見の相違は無い。

## 16. Human + ChatGPT への判断依頼

1. **A″ の採用と cycle 1 の承認**: pre-2016 の FX intraday の机上調査（download しない）と、R-A2（seen の M15 cache の signal を使わない統計と合成の帰無の道具。方向・side 別の統計・損益は出さない）。
2. **cycle 2 の前提**: pre-2016 の data を cycle 2 の前提条件にすること。それが得られない場合に seen だけで進めるなら、「真の Sharpe ≳ 1.3〜1.5 しか検出できず、真の 1.0 は約 2% しか確認まで届かない」ことを受け入れるか。
3. **統計の規則の凍結**: 次を cycle 2 の開始前の規則として認めるか。
   - max-T の帰無較正（FWER 10%、1,537 回 × 2）
   - 選択と推定の block の分離。**seen 2021–2025 を推定に使うのは `NO_FURTHER_SEEN_DATA_ALPHA_SEARCH` の例外**
   - prior の値（μ 0.07、τ 0.565。§8 の感度）
   - 新しい G4。**PATSD の G4 を 1.0 から 0.8 へ下げる**。fresh は全体で 1 回

## Q1〜Q6 への回答

- **Q1. M15 を使った通常の FX デイトレードに、研究する合理的な余地はあるか。**
  → **ある。ただし狭く、事前の見込みは弱い。**
  - 一般的な規則と H1 の方向の一致は、cost の前から負。数時間の構造は反転側にある。
  - 残る余地は、時計に錨を下ろした機構（S1、ただし事実と逆向き）・USD の定時発表の後（S2）・当日決済による financing の消滅（edge ではない）。
  - 検定して確認まで届くには、data の長さが要る。
- **Q2. H1 で相場環境を判断することは、既存研究に対して本質的に新しい可能性を提供するか。**
  → **方向の判断としては提供しない**（Round 1 で負）。予定された情報の到来の状態として使う形は未検定。ただし event の日の cost の効率は変わらないので、効果は edge から来る必要がある。
- **Q3. 現在の data で研究できることと、追加 data がなければ検証できないことは何か。**
  - 現在の data でできること: signal を使わない経済性の地図と、Sharpe ≳ 1.3〜1.5 の非常に強い system の発見。
  - 追加 data が要ること:
    - 0.8〜1.0 級の system の発見と確認（pre-2016 の intraday で、標本が約 3 倍）
    - 非 USD の発表の時刻
    - 約定順序（M1）
    - 実際の約定と spread（broker）
- **Q4. 過去の研究を繰り返さず、最も少ない試行数で情報を得るには、どの戦略構造を検討すべきか。**
  → S1（符号を固定した継続）と S2（USD 08:30 ET の後）を、当日決済・保有 1〜2 点・実効 ≤ 20 で、**pre-2016 の選択 block の上で**検定する。その前に cycle 1 で data の実現性を確かめる。ML は正の base が出るまで使わない。
- **Q5. 年率 net 5% を狙うために、どの程度の取引単位の期待利益が必要か。**
  - portfolio の net Sharpe 1.0（vol 5%）に要る 1 trade の gross の期待値（4 時間保有、1 pair 年 100 回）は、**2.65〜4.06 bp**（典型的な動き 21 bp の 12.5〜19%）。
  - 幅は cost の基準（median 1.70 / 平均 2.06 / 平均 + slippage 2.56）と実効の breadth（5 / 3 / 2）による（§1 の表）。
  - 勝率に直すと（±σ の 2 値を仮定）約 56〜60%。
  - あわせて、portfolio の stress MaxDD ≤ 15% を満たす必要がある。
- **Q6. 次に Human が承認すべき、最小限の実行範囲は何か。**
  → **cycle 1 だけ**。pre-2016 の FX intraday の机上調査（download しない）と、R-A2（seen の M15 cache の signal を使わない統計と合成の帰無の道具）。alpha・backtest・学習・data の取得・broker・CFD は含まない。

---

**STOP（指示 §18）。** 設計報告と独立レビューの完了で止まる。cycle 1 も承認の後に行う。
