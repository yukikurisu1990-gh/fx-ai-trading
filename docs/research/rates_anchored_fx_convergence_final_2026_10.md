# RATES_ANCHORED_FX_CONVERGENCE — 最終報告（2026-10-13）

`PRODUCTION_READINESS_NOT_CLAIMED`. 権限: `docs/governance/rates_anchored_fx_convergence_track_2026_10.md`。primary の凍結: `docs/research/rates_anchored_fx_prereg_2026_10.md`（`10a33f0`）。

**記録**: 【B】`artifacts/research/rates_anchored_fx/backtest.json`（sha256 `d1acb5a3…`、code の head `166e5a7`、2026-10-12T16:38:02Z〜2026-10-13T06:31:44Z）。【R】`artifacts/research/rates_anchored_fx/rates_acquisition.json`（金利の取得）。

## 1. Executive Summary

**最終の分類: RAC-F — `NO_RESIDUAL_CONVERGENCE_EDGE`**（事前登録 §13 の規則による）。**この mechanism は終了する**。indicator・ML・閾値の変更で救済しない。

| 問い | 答え |
| --- | --- |
| **Q1** 金利の差は 30 分の FX の return を説明するか | **EUR は部分的に yes**（β > 0 が全ての日、平均 0.44、R² 0.12）。**GBP は弱い**（β 0.13、R² 0.02）。符号は経済的に正しい（外国の金利の上昇 → 外貨高） |
| **Q2** 残差は平均回帰するか | **ほとんどしない**。120 分後の残差の中央値の比は 0.92〜1.06（|Z| の bin によらず 1 に近い）。30 分の残差の lag-1 の自己相関は −0.03 / −0.02 |
| **Q3** overshoot と underreaction のどちらが強いか | overshoot（A）の trade は 1,730 件で gross +0.19 bp / trade、cost に遠く及ばない。**underreaction（B）は凍結した閾値の下で実質的に検定されていない**（4.5 年で 1 件）: `NOT_EFFECTIVELY_TESTED_UNDER_FROZEN_THRESHOLD`。閾値は下げない |
| **Q4** cost gate の後も正の期待値が残るか | **いいえ**。portfolio の net −1.79 bp / trade（gross +0.18、cost 1.97）、net Sharpe −1.93、bootstrap の P(平均 ≤ 0) = 1.00 |
| **Q5** 2 pair の portfolio に意味のある Sharpe があるか | **いいえ**。両方の pair・全ての年・development と holdout・全ての sensitivity で net < 0 |
| 金利の情報は価格だけの平均回帰より良いか | **いいえ**。price-only・time-shift・符号の乱数化の control は、主の strategy より**わずかに良い**（net −1.47〜−1.64 bp 対 −1.79） |

**USD/JPY は落とした**: retail が取得できる intraday の JPY の金利の proxy（JGB）が OANDA に無い。OIS / STIR futures の intraday は有料の data だけで、買っていない。金利の proxy は 3 通貨で共通に使える **10 年の国債の CFD**（指示の優先順位の 4 番目）。

## 2. Hypothesis

短期の金利の再評価が示す FX の fair value（ΔFX = β·ΔRD）と、実際の 30 分の FX の動きとの乖離（残差）は、overshoot なら戻り、underreaction なら追随する。大きな乖離だけを取れば、retail の cost の後に収益化できる。

## 3. Rate data sources

| 通貨 | instrument | 行 | 範囲 | 備考 |
| --- | --- | --- | --- | --- |
| USD | OANDA `USB10Y_USD`（米国債 10 年の CFD） | 107,440 | 2021-04-26 00:00 … 2025-12-28 23:30 UTC | ほぼ 24 時間 |
| EUR | OANDA `DE10YB_EUR`（Bund 10 年） | 94,788 | 2021-04-26 00:15 … 2025-12-23 20:45 | |
| GBP | OANDA `UK10YB_GBP`（Gilt 10 年） | 46,966 | 2021-04-26 07:00 … 2025-12-24 12:00 | **London の日中だけ**。NY の午後は気配が無い |
| JPY | 無し | — | — | **落とした** |

- 取得: v20 の candle の endpoint（historical / read-only）、M15 bid / ask、request の境界を 2021-04-26T00:00Z / 2025-12-29T00:00Z（排他）に固定し、返った全ての candle の時刻を parse して確かめた（【R】、code の sha256 を記録）。
- 優先の OIS（SOFR / €STR / SONIA / TONA）・STIR futures・2 年債の intraday は、無料の retail の経路が無い。**短期金利ではなく 10 年**で、期間 premium を含む。これは仮説の検定としての限界である（§25）。
- **feasibility の段の price の endpoint の読み取り**（事前登録の commit の前、記録の code は無く、lead の session の inline の Python で実行）: v20 の InstrumentsCandles に `granularity = M15`、`price = BA`、`from = 2021-04-26T12:00:00Z`、`count = 1` を、`USB02Y_USD`・`USB10Y_USD`・`DE10YB_EUR`・`UK10YB_GBP`・`USB05Y_USD`・`USB30Y_USD` に送り、返った candle の時刻だけを表示した（価格は表示していない。時刻は全て 2021-04-26T12:00Z、seen の範囲の中）。`JP10YB_JPY`・`JGB10Y_JPY`・`DE02YB_EUR`・`DE05YB_EUR`・`UK02YB_GBP` は「Invalid value specified for 'instrument'」。この読み取りの request は repo の記録に残っておらず、ここに文面で記録する。その前に `feasibility.py` で account の instrument の metadata（68 件、全て CURRENCY）を読んだ。

## 4. FX data

承認済みの seen の route（`patsd_stage0.data.load_pair`）の **M15** bid / ask。EUR_USD・GBP_USD（USD の共通の factor の secondary に AUD_USD・NZD_USD・USD_CAD・USD_CHF・USD_JPY）。**M5 は使わなかった**: archive の M5 の file は保護期間の行を含み、seen だけを読む guard 付きの route が無い（事前登録 §3）。

## 5. Timestamp alignment

- OANDA の candle の時刻は bar の始まり。判定の時刻 t = bar の終わり、値はその bar の終値（FX と金利で同じ規則）。
- ΔFX と ΔRD は t と t − 30m の両方の bar がある場合だけ。金利の bar は volume > 0（気配がある）。日次の利回りの forward-fill は使っていない。
- 判定の時刻: London 08:00 以降かつ NY 15:00 以前（zoneinfo で夏時間を処理、合成の test で確認）。NY 16:45 に強制決済。
- exit の監視での金利の値は、その時刻の直前の bar（as-of、未来を使わない）。

## 6. Fair-value model

- ΔFX = α + β·ΔRD の Huber の robust 回帰（c = 1.345）。**毎営業日、その日より前の 90 営業日**で推定（合成の test で、その日の data を壊しても β・σ が変わらないことを確認）。
- FAIR = β·ΔRD、RESIDUAL = ΔFX − FAIR、σ = 推定の窓の残差の MAD × 1.4826、Z = RESIDUAL / σ。

## 7. Signal definition

- A（overshoot）: |Z| ≥ 2.5、方向 −sign(Z)。
- B（underreaction）: |FAIR| ≥ 2.5σ、ACTUAL が同じ符号かほぼ 0（≤ 0.1·|FAIR|）、|ACTUAL| ≤ 0.5·|FAIR|、方向 sign(FAIR)。
- gate: 0.6·D ≥ 4·C、D ≥ 0.35·ATR_1h。

## 8. Execution model

entry は判定の bar の終値の気配（買いは ask、売りは bid）。exit は以後の M15 の bar の終わりの気配。収束（|RES| ≤ 0.4·|RES_entry|）・金利の thesis の崩れ（50% の戻り、|FAIR| ≥ 1σ の trade だけ）・stop（1.5 倍）・120 分・NY 16:45。pair ごとに 1 position、同じ USD の方向の衝突は expected capture / C の大きい方。

## 9. Costs

- 想定 C（gate）: entry の pair・NY の時の、過去 90 営業日の M15 の終値の spread の中央値 + 0.5 bp。
- 実現の cost: entry と exit の実際の bid / ask + slippage 0.5 bp（往復）。平均 **1.97 bp / trade**（EUR 1.93、GBP 2.03）。
- これは OANDA の pricing の tier の実測の気配で、より安い broker の公表の値ではない（PR #509 の E1 / E2 は公表で 0.53〜0.76 bp）。

## 10. Primary specification

事前登録 §4〜§7 の値（z 2.5 / lookback 90 / 保有 120 / cost の倍数 4 / capture 0.6 / ATR 0.35 / 残差の exit 0.4 / thesis 0.5 / stop 1.5）。結果の後に変えていない。

## 11. Overshoot results（A）

| 指標 | 値 |
| --- | --- |
| trades | 1,730（年 393） |
| 勝率 | 46.9% |
| gross / cost / net（平均、bp） | +0.19 / 1.97 / −1.78 |
| net の中央値 | −1.83 bp |
| net Sharpe / gross Sharpe | −1.91 / 0.21 |
| exit の理由（全体） | stop 671・収束 566・時間 440・thesis 42・16:45 12 |

**期待した収束の大きさと実現の差**: gate は 0.6·D ≥ 4·C（C ≈ 2 bp なら D ≥ 約 13 bp）を要求したが、実現の gross は平均 0.19 bp。**期待の capture の 1〜2% しか実現していない**。

## 12. Underreaction results（B）

- 規則の下で **1 件**（−27.7 bp）。|FAIR| ≥ 2.5σ（金利の 30 分の動きが FX の残差の σ の 2.5 倍以上）の観測が少なく、その中で |ACTUAL| ≤ 0.5·|FAIR| と cost gate を同時に満たすものはほぼ無い。
- 診断（§18）では、EUR の |FAIR| / σ が 2.0〜3.0 の観測（n = 55）で 120 分後の追随が +4.6〜+8.3 bp だった。**標本が小さく、規則の外の観測であり、閾値を下げて trade を増やすことはしない**（指示 §40、§47）。
- **B は `NOT_EFFECTIVELY_TESTED_UNDER_FROZEN_THRESHOLD`**: MIN_FAIR_MOVE = 2.5σ は指示が値を定めなかったため lead が凍結した値で、10 年の proxy の R² 0.02〜0.12 の下では、B の脚をほぼ止める閾値だった。**この報告の「mechanism の終了」は、A（overshoot）と、凍結した仕様の全体について言うもので、underreaction の仮説が data で反証されたという意味ではない**。

## 13. Pair-level results

| pair | trades | gross | cost | net | net Sharpe | gross Sharpe | MaxDD（1 倍、%） |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EUR_USD | 978 | +0.23 | 1.93 | −1.71 | −1.43 | 0.19 | 17.7 |
| GBP_USD | 753 | +0.12 | 2.03 | −1.91 | −1.20 | 0.08 | 15.3 |

## 14. Portfolio results

| 指標 | 値 |
| --- | --- |
| trades / 年 | 1,731 / 393 |
| 勝率 | 46.9% |
| gross / cost / net（平均、bp） | +0.18 / 1.97 / −1.79 |
| net の中央値 | −1.83 bp |
| 累積 net | −3,106 bp |
| net Sharpe / Sortino | −1.93 / −2.39 |
| gross Sharpe | 0.20 |
| MaxDD（1 倍の名目） | 31.9% |
| profit factor | 0.79 |
| position の時間 | 年 459 時間 |
| bootstrap（block 10 日、2,000 回） | Sharpe の 90% 区間 [−2.71, −1.19]、P(平均 ≤ 0) = 1.00 |

## 15. Event / non-event

| 区分 | trades | gross | net | net Sharpe |
| --- | --- | --- | --- | --- |
| EVENT（US の 08:30〜10:30 の proxy・FOMC・ECB） | 710 | −0.06 | −2.02 | −1.30 |
| NON_EVENT | 1,021 | +0.34 | −1.64 | −1.51 |

event の時間帯で特に良いわけではない（金利の再評価が最も大きい時間帯で gross が負）。

## 16. Year stability

| 年 | trades | gross | net | net Sharpe |
| --- | --- | --- | --- | --- |
| 2021（9 月〜） | 156 | +1.40 | −0.37 | −0.55 |
| 2022 | 587 | +0.08 | −2.01 | −2.11 |
| 2023 | 273 | −0.10 | −2.02 | −1.75 |
| 2024 | 356 | +0.10 | −1.82 | −2.46 |
| 2025（final seen holdout） | 359 | +0.10 | −1.86 | −2.32 |

- development（〜2024）: net −1.78、Sharpe −1.86。holdout（2025）: net −1.86、Sharpe −2.32。
- どの 1 年を除いても net は −1.68〜−1.94 bp。

## 17. Residual decay

全ての判定の時刻の残差の比 RES(t + h) / RES(t) の中央値（β は t で固定）:

| |Z| | EUR 30m | EUR 120m | GBP 30m | GBP 120m |
| --- | --- | --- | --- | --- |
| 1.0–1.5 | 0.96 | 0.97 | 1.00 | 0.98 |
| 1.5–2.0 | 0.97 | 0.96 | 0.98 | 1.05 |
| 2.0–2.5 | 0.97 | 0.92 | 0.94 | 0.99 |
| 2.5–3.0 | 0.95 | 0.93 | 0.99 | 1.06 |
| 3.0+ | 0.94 | 0.97 | 0.97 | 0.96 |

**残差は 120 分でほとんど縮まない**（半分の収束どころか、最大でも約 8%）。30 分の残差の lag-1 の自己相関は EUR −0.035、GBP −0.020 で、半減期は定義できない（正の自己相関が無い）。

## 18. Monotonicity

120 分の収束の return（gross、bp、−sign(RES)·ΔRES）:

| |Z| | EUR（n） | GBP（n） |
| --- | --- | --- |
| 1.0–1.5 | +0.33（4,333） | +0.05（3,319） |
| 1.5–2.0 | +0.44（2,147） | −0.15（1,672） |
| 2.0–2.5 | +0.66（1,149） | +0.15（800） |
| 2.5–3.0 | +2.14（591） | −2.34（430） |
| 3.0+ | −0.06（816） | +1.09（551） |

- **pair をまたいで pool した**加重の平均で、2.5 以上の bin（+0.34 bp）は 2.5 未満（+0.24 bp）より大きく、事前登録の「単調性」は形式上成り立つ。pair ごとに見ると、EUR の 3.0+（−0.06）と GBP の 2.5–3.0（−2.34）が低い bin を下回り、成り立たない。**しかし大きさは cost（約 2 bp）の 1/6 で、pair の間で符号が揃わない**（EUR の 2.5–3.0 は +2.1、GBP は −2.3）。経済的な単調性の証拠ではない。
- underreaction（|FAIR| / σ の bin、sign(FAIR)·ΔFX の 120 分）: EUR は +0.62（600）、+1.93（153）、+4.59（33）、+8.30（22）、+1.20（23）。GBP は標本が 2〜38 で符号が不安定。

## 19. Price-only control

| control | trades | gross | net | net Sharpe |
| --- | --- | --- | --- | --- |
| **主（RATE_ANCHORED）** | 1,731 | +0.18 | −1.79 | −1.93 |
| PRICE_ONLY_STANDALONE（β = 0、同じ規則） | 1,698 | +0.35 | −1.62 | −1.69 |
| PRICE_ONLY_MATCHED（主の A と同じ時刻、方向 −sign(ΔFX)） | 1,730 | +0.11 | −1.87 | — |

- matched では、主の A の方向と price-only の方向が 99.8% 一致した。**主の A の trade は、実質的に 30 分の価格の平均回帰の trade**である（β·ΔRD は 30 分の FX の動きに比べて小さい）。
- **RATE_ANCHORED は PRICE_ONLY より良くない**。mechanism の主張（金利の fair value への収束）は支持されない。

## 20. Time-shift / random control

| control | trades | gross | net | net Sharpe |
| --- | --- | --- | --- | --- |
| TIME_SHIFTED（金利を 1 営業日ずらす） | 1,710 | +0.34 | −1.64 | −1.68 |
| RANDOM_SIGN（ΔRD の符号を乱数化） | 1,705 | +0.50 | −1.47 | −1.53 |

**金利の情報を壊した control が、主の strategy より少し良い**。金利の情報は増分の edge を持たない。

## 21. Cost stress

| 水準 | trades | gross | cost | net | net Sharpe |
| --- | --- | --- | --- | --- | --- |
| C0（基本） | 1,731 | +0.18 | 1.97 | −1.79 | −1.93 |
| C1（×1.25） | 1,503 | +0.07 | 2.48 | −2.41 | −2.26 |
| C2（×1.5） | 1,196 | +0.20 | 3.01 | −2.81 | −2.20 |
| C3（×2.0） | 646 | +1.07 | 4.14 | −3.07 | −1.54 |

（stress は gate の C にも掛けるので、trade の集合が変わる。）

## 22. Sensitivity（報告だけ、best を採用しない）

| sensitivity | trades | gross | net | net Sharpe |
| --- | --- | --- | --- | --- |
| z 2.0 | 2,727 | +0.49 | −1.48 | −2.11 |
| z 3.0 | 1,038 | +0.67 | −1.33 | −0.98 |
| lookback 60 / 120 | 1,700 / 1,765 | +0.05 / +0.39 | −1.91 / −1.60 | −1.99 / −1.76 |
| 保有 60 / 180 分 | 1,781 / 1,709 | +0.24 / +0.24 | −1.75 / −1.74 | −2.22 / −1.75 |
| cost の倍数 3 / 5 | 1,784 / 1,503 | +0.17 / +0.07 | −1.81 / −1.91 | −2.00 / −1.81 |
| capture 0.4 / 0.8 | 1,196 / 1,784 | +0.20 / +0.17 | −1.81 / −1.81 | −1.43 / −2.00 |
| slippage 0.25 / 1.0 | 1,782 / 1,482 | +0.18 / +0.13 | −1.55 / −2.36 | −1.72 / −2.18 |
| σ = 標準偏差 | 883 | +0.99 | −1.01 | −0.66 |

- **capture と cost の倍数は同じ 1 つの parameter**: gate は D ≥ (倍数 / capture)·C なので、capture 0.8 は cost の倍数 3 と同じ run（1,784 件、同じ結果）、capture 0.4 は cost の stress C2 と trade の集合が同じ。C1（×1.25）は cost の倍数 5 と同じ trade の集合。独立の sensitivity ではない。
| secondary（leave-one-out の USD の共通の factor） | 1,692 | +0.15 | −1.83 | −1.94 |

**全ての sensitivity で net < 0**。最も良い σ = 標準偏差でも net −1.01 bp。

## 23. Independent reviews

3 つの役割を別の context の agent で、互いの結論を渡さずに行った（対象 `4bbb37f`）。**BLOCKER は 0**。全員が RAC-F を支持した。指示 §51 に従い、BLOCKER 以外は延々と直さず、報告の文面の必須の修正だけを 1 回反映した。

| 役割 | 主な所見 | 対応 |
| --- | --- | --- |
| Quant | lookahead なし（β・σ・cost・ATR・exit の as-of を合成で確認）。符号・P&L・position の衝突の規則は正しい。1,731 件の trade から portfolio・pair・年・exit の理由・MaxDD を再計算し全て一致。non-blocking: 単調性は pair をまたいで pool、price-only の σ の尺度、cost の stress は gate にも掛かる、同じ bar の終値での約定、exposure の単位、stale な Gilt | §18・§25 に注記 |
| Rates / FX microstructure | 符号・時刻の整合は正しい（FX も金利も bar の終わり）。β 0.44 と R² 0.12 は妥当。**必須（文面）**: B は実質的に未検定、「FX は効率的」は言い過ぎ。non-blocking: 10 年の先物の duration の不一致、roll の跳び、Gilt の時間帯 | §1・§12・§25 を訂正 |
| Adversarial | 事前登録 → 取得 → engine → backtest の順序と、全ての code / prereg の hash の一致を確認。data の境界（parse した datetime・str の subclass の拒否・guard 付きの FX の route）は正しい。lead の追加の値（MIN_FAIR 2.5σ など）は全て取得の前に凍結済み。**必須（文面）**: B を `NOT_EFFECTIVELY_TESTED_UNDER_FROZEN_THRESHOLD` と書く、feasibility の candle の読み取りの request を記録する。non-blocking: capture と cost の倍数は同じ parameter、cost の stress で trade の集合が変わる | §1・§3・§12・§22 を訂正 |

（修正の後の再監査は 23a。）

## 24. Final classification

**RAC-F — `NO_RESIDUAL_CONVERGENCE_EDGE`**（事前登録 §13 の 2: net の期待値 ≤ 0 で、gross の Sharpe 0.196 < 0.3）。

- 根拠: (1) 残差は 120 分でほとんど収束しない（§17）、(2) 実現の gross は期待の capture の 1〜2%（§11）、(3) 金利の情報を壊した control の方が良い（§19〜§20、RAC-D の性質も併せ持つ）、(4) 全ての pair・年・sensitivity・cost の水準で net < 0。
- gross Sharpe が 0.3 を超えていれば RAC-E（cost で消える）になるが、0.196 で超えない。non-event の gross Sharpe は 0.32 だが、それは事前登録の判定の対象ではなく、price-only の control（0.37）と同程度。

## 25. Next step

- **この mechanism は終了する**（指示 §56）。indicator・ML・閾値・保有・cost の倍数の変更で救済しない。
- **限界**（この結論の範囲）:
  - 金利の proxy は 10 年の国債の CFD で、短期金利（OIS / STIR）ではない。仮説の中心の「短期金利の再評価」を直接は検定していない。OIS / STIR の intraday の data は有料で、買っていない。
  - **duration の不一致**: 事前登録 §4 は「同じ 10 年なので duration は共通の定数」としたが、CFD が追う先物の最割安銘柄の修正 duration は、米 10 年 note の先物が約 6、Bund・Long Gilt が約 8〜9 で違う。ΔRD は US の脚を約 25% 軽く重み付けしており、fit（R²）を弱める。残差の平均回帰の有無そのものは変えない（price-only の control と方向が 99.8% 一致）。
  - CFD の価格の四半期の先物の roll の跳び（年 4 回 × 3 instrument）は確かめていない。Huber の推定で吸収される程度の件数。
  - Gilt の気配が無い NY の午後は、GBP の exit の監視で直前の Gilt の値を使う（as-of の規則どおり。entry は t の金利の bar を要求する）。
  - entry は signal を計算した bar の終値の気配で、遅延が無い。平均回帰の signal には楽観的で、真の gross はさらに低い可能性がある。
  - GBP の金利の proxy（Gilt の CFD）は London の日中だけで、NY の時間帯の GBP の判定は金利の data の欠落で除外された。
  - FX は M15 で、30 分の窓は 2 本の bar。M5 は guard 付きの route が無く使っていない。
  - cost は OANDA の実測の気配。PR #509 の公表の最良の cost（0.5〜0.8 bp）でも、gross +0.18 bp では net は負のまま。
- 有料の OIS / STIR の data で短期金利の版を検定するかは、Human の判断（購入の承認が要る）。判断の材料: 30 分の残差がほぼ収束しない（§17）のは、FAIR が残差の σ に比べて小さいので、**実質的には 30 分の FX の価格が平均回帰しないこと**についての結果である。短期金利の proxy で FAIR が大きくなっても A の結論が変わるとは考えにくいが、**underreaction（B）は FAIR の大きさに依存し、この programme では検定されていない**。
