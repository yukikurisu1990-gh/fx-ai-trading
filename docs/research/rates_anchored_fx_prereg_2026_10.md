# RATES_ANCHORED_FX_CONVERGENCE — primary specification の凍結（2026-10-13、金利の価格の取得の前）

**この文書は、金利の proxy の価格の取得・FX の data の読み取り・backtest のどれよりも前に commit する。** primary の値は指示 §47 のとおりで、結果を見て変えない。sensitivity は報告だけで、best を採用しない。

権限: `docs/governance/rates_anchored_fx_convergence_track_2026_10.md`。

## 1. data の feasibility（指示 §8、取得の前に確認済み）

| 通貨 | 優先の proxy（OIS / STIR / 2Y） | 実際に使える proxy | 判定 |
| --- | --- | --- | --- |
| USD | SOFR futures など | **OANDA の `USB10Y_USD`**（米国債 10 年の CFD、M15 bid / ask、2021-04-26 以降の candle の存在を確認）。`USB02Y_USD`・`USB05Y_USD`・`USB30Y_USD` もある | 使う |
| EUR | €STR / Euribor futures | **OANDA の `DE10YB_EUR`**（Bund 10 年の CFD）。2Y / 5Y は OANDA に無い | 使う |
| GBP | SONIA futures | **OANDA の `UK10YB_GBP`**（Gilt 10 年の CFD）。2Y は無い | 使う |
| JPY | TONA futures | **OANDA に JGB の instrument が無い**（`JP10YB_JPY`・`JGB10Y_JPY` は「Invalid instrument」） | **落とす**（指示 §8） |

- OIS・STIR futures の intraday の historical は、CME / ICE の有料の data（Databento・CME DataMine など）だけで、購入は Human の承認が要る。**この programme では買わない**。
- **2 pair が残る（EUR/USD・GBP/USD）ので研究を続ける**（指示 §8: 最低 2 pair）。
- **金利の proxy は短期金利ではなく 10 年**: 3 通貨の全てで使える唯一の tenor で、差を取るために tenor を揃える。10 年は期間 premium を含み、政策金利の期待の再評価より広い。**指示の優先順位 1〜3 を満たさず、4（その他の流動性のある金利の proxy）に当たる**。
- OANDA の bond CFD は先物の価格に連動する broker の気配で、取引時間は商品ごとに違う（Gilt は London の午後に閉じるなど）。気配の無い時刻は §5 の no-trade の filter で除く。
- 日次の利回りの forward-fill は使わない（指示 §7）。

## 2. 期間と split

| 項目 | 値 |
| --- | --- |
| 期間 | **2021-04-26 … 2025-12-28**（seen）。金利の取得もこの範囲に request の段で限る |
| 推定 | 毎営業日、**その日より前の 90 営業日**だけで推定（past-only、walk-forward） |
| 評価 | 最初の 90 営業日の後から最後まで |
| 時間順の区分（報告） | development: 評価の開始 … 2024-12-31。**final seen holdout: 2025-01-01 … 2025-12-28**。parameter は無いので、両方を out-of-sample として別に報告する |
| 読まない | fresh `2016-06-02 … 2021-04-25`、OOS `2025-12-29 … 2026-02-28`、dead、forward |

## 3. data

- FX: 承認済みの route `scripts.research.patsd_stage0.data.load_pair` の **M15** bid / ask（EUR_USD・GBP_USD）。**M5 は使わない**: archive の M5 の file は保護期間の行を含み、seen だけを読む guard 付きの route が無い（指示 §4: M15 しか decision-grade で使えない場合は M15）。
- 金利: OANDA v20 の M15 bid / ask（`USB10Y_USD`・`DE10YB_EUR`・`UK10YB_GBP`）。request の from / to を 2021-04-26T00:00Z / 2025-12-29T00:00Z（排他）に固定し、返った candle の最小・最大を確かめる。`complete = true` だけ。
- 時刻: OANDA の candle の時刻は bar の始まり。**判定の時刻 t = bar の終わり**（始まり + 15 分）。t の値はその bar の終値。
- mid = (bid_c + ask_c) / 2。

## 4. 量の定義（凍結）

| 量 | 定義 |
| --- | --- |
| P（FX） | 外貨の USD 建ての価値: EUR = EURUSD、GBP = GBPUSD（JPY は落とした） |
| ΔFX_t | log(P_t / P_{t−30m})（mid） |
| Δr（金利） | bond の価格 B の 30 分の log の変化の符号を反転: Δr_t = −log(B_t / B_{t−30m})。利回りの上昇 ≈ 価格の下落。duration は同じ 10 年なので共通の定数として β に吸収する |
| ΔRD_t | Δr_foreign,t − Δr_USD,t |
| 判定の時刻 | t の分が :00 か :30（30 分ごと） |
| 推定の観測 | 過去 90 営業日の、§5 の時間帯の 30 分ごとの (ΔFX, ΔRD)（同じ時刻の 4 つの価格が全てある観測だけ） |
| fair value の model | ΔFX = α + β·ΔRD + ε の **Huber の robust 回帰**（IRLS、c = 1.345、scale は MAD）。毎営業日 1 回、その日より前の 90 営業日で推定 |
| FAIR_MOVE_t | β_t · ΔRD_t（α は使わない、指示 §13） |
| RESIDUAL_t | ΔFX_t − FAIR_MOVE_t |
| σ_t | 推定の窓の残差（ΔFX − α − βΔRD）の MAD × 1.4826（past-only） |
| Z_t | RESIDUAL_t / σ_t |
| ATR_1h | M15 の mid から作る H1 の bar（時刻の境界は UTC の正時）の、直前の完成した 14 本の true range の平均（log、past-only） |
| 想定 cost C | entry の pair・NY の時（hour）の、**過去 90 営業日の M15 の終値の spread（bp）の中央値** + slippage 0.5 bp（往復） |

## 5. 時間帯と no-trade の filter

- entry の判定の時刻: **London 08:00（Europe/London）以降、かつ New York 15:00（America/New_York）以前**。夏時間は zoneinfo で扱う。
- 全ての position は **NY 16:45 まで**に決済（その時刻の bar の終値）。17:00 の rollover をまたがない。週末をまたがない。
- 許す filter だけ（指示 §30）: rollover に近い（上の時刻の規則）、spread が異常（entry の spread が想定 C の spread 部分の 3 倍超）、金利の data の欠落（t か t − 30m の bar が無い）、stale な気配（t の金利の bar の tick の数 `volume` が 0、または t − 30m … t の間に金利の bar が 1 本も無い）、data の質の問題（bid > ask など）、cost gate の不合格。

## 6. signal（凍結）

**Strategy A（overshoot の回帰）**: |Z_t| ≥ **2.5**。方向 = −sign(Z)（Z > 0 なら外貨の売り）。D = |RESIDUAL|。

**Strategy B（underreaction の追随）**:

- |FAIR_MOVE| ≥ **MIN_FAIR_MOVE = 2.5 · σ_t**（指示は値を定めていないので、A の閾値と同じ尺度で凍結）
- ACTUAL と FAIR が同じ符号、または |ACTUAL| ≤ 0.1 · |FAIR|（「ほぼ 0」の凍結）
- |ACTUAL| ≤ **0.50** · |FAIR|
- 方向 = sign(FAIR)。D = |FAIR − ACTUAL|

**共通の gate**:

- expected capture = **0.60** · D ≥ **4** · C
- D ≥ **0.35** · ATR_1h
- A と B が同時に成り立つ場合（同じ方向になる）、A に数え、重なりの印を付ける。

**position の衝突**（指示 §26）: pair ごとに同時の position は 1 つ。同じ判定の時刻に 2 pair が同じ USD の方向（両方で外貨の買い = USD の売り、など）の signal を出した場合、expected capture / C の大きい方だけ（同点は |Z|）。片方の pair に position がある間、もう片方の pair の同じ USD の方向の signal は取らない。

## 7. 執行と exit（凍結）

- entry: 判定の時刻 t の bar の終値の気配。買いは ask_c、売りは bid_c。
- exit の判定: 以後の各 M15 の bar の終わり。exit も その bar の終値の気配（買いの決済は bid_c、売りの決済は ask_c）。
- P&L（bp）= 方向 × (log(exit の気配) − log(entry の気配)) × 10⁴ − slippage 0.5 bp。spread は気配で実現する。
- **anchor**: 判定の窓の始まり t₀ − 30m。entry の β を固定し、RES(s) = [log P_s − log P_anchor] − β·[RD 累積(s) − RD 累積(anchor)]（RD 累積 = Δr_foreign − Δr_USD の累積）。
- **収束の exit**: |RES(s)| ≤ **0.40** · |RES_entry|
- **金利の thesis の崩れ**: entry の |FAIR_MOVE| ≥ 1.0 · σ の trade だけに適用（金利の動きが小さい A の trade で、ほぼ 0 の 50% で発火するのを避ける凍結）。RD の累積の変化（anchor から）が、entry の ΔRD の向きに、entry の大きさの **50%** 以下まで戻ったら exit
- **stop**: RES(s) が entry と同じ符号で、|RES(s)| ≥ **1.5** · |RES_entry|（現在の fair value で再計算）
- **時間**: **120 分**（8 本）。NY 16:45 の強制決済が先ならそちら
- 判定の順序（同じ bar で複数）: stop → thesis → 収束 → 時間

## 8. 報告する指標（指示 §37）

trades・trades / 年・勝率・平均の gross・平均の cost・平均の net・中央値の net・年率の net Sharpe（日次の P&L、取引の無い日は 0、√252）・Sortino・MaxDD（1 trade = 名目 1 倍、累積の bp を % で）・profit factor・exposure（position のある時間の割合）・turnover。pair 別・A / B 別・event / non-event 別・年別・development / holdout 別。

**event の定義**（凍結）:

- US の指標の時間帯の proxy: 平日の NY の 08:30〜10:30（CPI・NFP などの 08:30 と 10:00 の発表の時間帯。日ごとの発表の有無は見ない clock の proxy）
- FOMC: 発表日の NY 14:00〜16:00（`artifacts/track_a_scratch/exogenous/s1_calendar.json` の USD の日付、一次の記録から抽出済み）
- ECB: 決定日の Frankfurt 13:45〜16:00（同じ記録の EUR の日付）
- BoE: 日付が取得できていない（同じ記録の `unacquirable`）ので event に数えない（限界）

## 9. controls（指示 §43〜§45）

| control | 中身 |
| --- | --- |
| **PRICE_ONLY_STANDALONE** | β = 0（金利の情報なし）。Z = ΔFX / σ_FX（ΔFX の過去 90 営業日の MAD）。A と同じ規則（|Z| ≥ 2.5、−sign、cost gate、exit は β = 0 の RES） |
| **PRICE_ONLY_MATCHED** | 主の A の entry の時刻と同じ時刻で、方向 = −sign(ΔFX)、exit は β = 0 の RES |
| **TIME_SHIFTED** | 金利の series を 1 営業日（同じ時刻の前の営業日）ずらして、主の strategy の全体を回す |
| **RANDOM_SIGN** | ΔRD の符号を、30 分の観測ごとに乱数で反転（seed 20261013）して、主の strategy の全体を回す |

**金利の情報が増分の edge を持つ**とは: 主の strategy の net の平均が、TIME_SHIFTED・RANDOM_SIGN の net の平均より大きく、かつ主の net Sharpe が PRICE_ONLY_STANDALONE の net Sharpe より大きいこと（matched は報告）。

## 10. 診断（指示 §34〜§36、§42）

- 残差の減衰: 全ての判定の時刻で、|Z| の bin（1.0–1.5 / 1.5–2.0 / 2.0–2.5 / 2.5–3.0 / 3.0+）ごとに、RES(t + h) / RES(t) の平均（h = 30 / 60 / 90 / 120 分、β は t で固定、anchor の定義は §7）。**exit を再調整しない**。
- 単調性: 同じ bin で、120 分の収束の return −sign(RES)·(ΔFX_{t→t+120} − β·ΔRD_{t→t+120})（bp、gross）。B は |FAIR| / σ の同じ bin で sign(FAIR)·ΔFX_{t→t+120}。
- 回帰: β の符号・安定性（日次の β の分布）・R²・残差の lag-1 の自己相関・半減期・不均一分散（残差² と |ΔRD| の相関）。

## 11. 統計の sanity

- 日次の P&L の block bootstrap（block 10 営業日、2,000 回、seed 20261013）: 平均と Sharpe の 90% 区間、P(平均 ≤ 0)。
- cost の stress: C0 = 基本、C1 = ×1.25、C2 = ×1.5、C3 = ×2.0（spread と slippage の両方に掛ける）。
- 大きな多重検定の仕組みは作らない（primary は 1 本）。

## 12. sensitivity（報告だけ、指示 §48）

z: 2.0 / 2.5 / 3.0、β の lookback: 60 / 90 / 120、保有の上限: 60 / 120 / 180、cost の倍数: 3 / 4 / 5、capture: 0.4 / 0.8、slippage: 0.25 / 1.0、σ = 標準偏差（secondary）、secondary の model（leave-one-out の USD の共通の factor）。**primary の判定は 2.5 / 90 / 120 / 4**。

- USD の共通の factor（secondary）: target の pair を除いた seen の M15 の USD の pair（EUR_USD・GBP_USD・AUD_USD・NZD_USD・USD_CAD・USD_CHF・USD_JPY のうち target 以外）の、外貨の USD 建ての log の 30 分の変化の平均。

## 13. 判定（指示 §39・§52、凍結）

基本の cost（C0）での portfolio（EUR + GBP）で判定する。

1. 2 pair 未満しか金利の data が decision-grade でない → **RAC-G**（該当しない。§1）
2. net の期待値 ≤ 0:
   - gross の期待値 > 0 かつ gross の Sharpe ≥ 0.3 → **RAC-E**
   - それ以外 → **RAC-F**
3. net の期待値 > 0 で、金利の情報が増分の edge を持たない（§9） → **RAC-D**
4. net の期待値 > 0 で、金利の情報が増分の edge を持つ:
   - STRONG: net Sharpe ≥ 1.0、MaxDD ≤ 15%、2 pair 以上で net > 0、C2（×1.5）でも net > 0、どの 1 年を除いても net > 0、|Z| の bin の 120 分の収束が 2.5 以上の bin で正 → **RAC-A**
   - PROMISING: net Sharpe ≥ 0.5、2 pair 以上か A / B の 2 つ以上の subgroup で net > 0、単調性（2.5–3.0 と 3.0+ の bin の収束が 1.0–2.5 の bin の平均より大きい） → **RAC-B**
   - net Sharpe ≥ 0.3 で、bootstrap の 90% 区間が 0 を含み、単調性がある → **RAC-C**
   - それ以外（net Sharpe < 0.3、1 pair / 1 年だけで成立） → gross の Sharpe ≥ 0.3 なら **RAC-E**、そうでなければ **RAC-F**

## 14. 記録

入力の源と hash・期間・instrument・時刻の扱い・code の SHA・command・環境・出力の hash。記録は上書きを拒否する。
