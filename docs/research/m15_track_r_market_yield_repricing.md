# T-R — 市場利回り repricing の development 結果

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

判定: **`MARKET_YIELD_REPRICING_FAST_5D_MEASURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`**（裁定の Case B）

> **scope（2026-09-18 の裁定で明確化）**: この判定は **事前登録した fast 5 日 measure** についてのもの。
> market-yield repricing family 全体が閉じたことを意味しない。slow state 版は T-R2 として別に事前登録・実行した
> （`docs/research/m15_track_r2_slow_repricing.md`）。

Human + ChatGPT 裁定（2026-09-16）で D-2（非 FX の無料・公開データ取得）が承認され、T-R が最初の track に指定された。
事前登録は commit `a25d078` で **結果を 1 つも含まない状態** で凍結・push し、そのあとに 1 度だけ実行した。
保護 span（fresh pool `2016-06-02 … 2021-04-25`、historical OOS、dead window、forward epoch）は読んでいない。

---

## 1. 何を問うたか

> 市場が価格をつける 2 年国債利回りの **repricing** には、同じ時点で既に分かっている **FX の価格情報を超える**
> 予測内容が残っているか？

H-016 が閉じたのは政策金利（中銀が決める階段関数）の level / change。市場利回りは毎日動く別の量で、本 programme では
一度も取得していなかった。C09 は未実行（horizon・dispersion window・economic で不合格の記録）で、反証ではない。

## 2. データ — 出所と取得

すべて中銀・財務省の公開ページ。有料・認証・scraping なし。FX 系列は 1 本も要求していない。

| 通貨 | 出所 | 系列 | 取得 |
| --- | --- | --- | --- |
| USD | U.S. Department of the Treasury | Daily Treasury Par Yield Curve, 2 Yr | 済 |
| EUR | Deutsche Bundesbank（BBSIS 日次、残存 2.0 年） | 連邦債の term structure 利回り | 済 |
| EUR（照合用） | European Central Bank（YC dataset、AAA 2Y spot） | `YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y` | 済（primary ではない） |
| JPY | 財務省 | 国債金利情報 2Y | 済 |
| GBP | Bank of England | GLC nominal spot curve, 24 か月 | 済 |
| CAD | Bank of Canada（Valet） | `BD.CDN.2YR.DQ.YLD` | 済 |
| CHF | Swiss National Bank（cube `rendoblid`） | 連邦債利回り 2J | 済だが **2025-07-31 で終了** |
| NZD | Reserve Bank of New Zealand（B2 daily） | 2 year government bond closing yield | **不可**（現行ファイルは 403、旧ファイルは 2025-08-22 まで） |
| AUD | Reserve Bank of Australia（表 F2） | 2Y government bond yield | **不可**（自動取得を 403 で拒否） |

記録: `artifacts/research/market_yields/acquisition.json`（取得時刻、行数、各ファイルの sha256）。
取得スクリプトは `scripts/research/market_yields/acquire.py` で、**opt-in 環境変数が無ければ何も取得しない**。

## 3. 時刻・入手可能性の監査

**どの公開ページも「その日の値がいつ利用可能になるか」を書いていない。** 推測せず、裁定どおり保守的な一律規則にした。

- 日付 `d` の利回りは、**1 取引日後**（`d+1` の FX 終値）の建玉にしか使えない。その建玉は翌日のリターンを取る。
- 同日利用は一切しない。`leak_check` が通貨ごとに、使った値の最小 age（1 日以上）と同日・未来日付の件数（0 件）を測っている。
- 祝日は直近値を持ち越し、持ち越しの最大 age を測る（採用 5 通貨はいずれも 10 暦日以内）。
- **EUR の 2 出所の照合**: 水準の相関 0.9996、平均差 2.8bp。ただし **1 日変化の相関は 0.65**（終値時点の違いと Bundesbank の
  0.01pp 丸め）。**5 日変化なら 0.925**。1 日の repricing は出所依存で、事前登録が lookback を 5 日にした理由の 1 つ。

## 4. 通貨 coverage gate — 信号を見る前に確定

| 通貨 | 判定 | 理由 |
| --- | --- | --- |
| CAD・EUR・GBP・JPY・USD | **decision-grade** | 決定日の 99.9% で使用可能な値があり、gap・staleness・重複・範囲すべて合格 |
| CHF | 不可 | 決定 span の最後を覆えない（2025-07-31 まで）、持ち越し age が最大 148 日 |
| NZD | 不可 | 同上（2025-08-22 まで）、持ち越し age 最大 126 日、5 営業日超の gap |
| AUD | 不可 | 本環境から取得できない（403）。「利用不可」ではなく「ここでは未確認」 |

**universe = CAD・EUR・GBP・JPY・USD の 5 通貨**、決定 span `2021-04-27 … 2025-12-26`（FX 取引日 1213）。
G10 の断面を無理に作らず、reduced universe として実行した（裁定 §24）。記録: `artifacts/research/market_yields/integrity.json`。

## 5. 事前登録（`a25d078` で凍結）

- signal: 5 通貨断面での **2 年利回りの 5 日変化の z-score**。符号は +1（相対的に利回りが上がった通貨が上昇する）で凍結。
- target: 通貨の excess return、horizon は **5 日と 20 日**の 2 本。
- book: **A** 利回り repricing 単独 / **B** 同じ lookback の FX momentum（閉じた price family）/ **C** A を B に断面回帰した残差（主検定）。
- 執行層は Track 1 のものを再利用（cap 0.25・sum-zero・band 0.10・差分課金・vol target 10%）。**Track 1 の alpha model は再利用しない。**
  leverage 上限は設けず、必要 leverage・routed margin・gap stress を報告する。
- screen は **対称かつ網羅的**: advance の条件を 1 つでも満たさなければ stop。seen data はどちらの向きにも decision-grade にならない。
- **実行前の signal-blind 検出力**: breadth 2.5、4.81 年では 80% の検出力で見えるのは net Sharpe **約 1.13**。
  つまり 0.3〜0.5 の結果は、出ても出なくても decision-grade にならないと事前に記録した。
- **実行前の必要 IC**: 半減期 5 日なら net 0.3 に日次 IC **4.44%**、net 0.5 に 5.39%（breadth 2.5）。
  ただしこれは半減期 5 日＝turnover 43.4 を仮定した値で、実際の book の turnover はもっと高かった。§6 では
  **実測 turnover での必要 IC** と **日次換算した観測 IC** で比べ直す。

## 6. 結果（1 回のみ実行）

| book | gross Sharpe | net Sharpe | gross 年率 | net 年率 | 年間 cost | turnover（RT/年/単位 gross） | IC 5 日 | IC 20 日 | 最大 DD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A 利回り repricing | **+0.144** | **−0.921** | +1.56% | −9.98% | 11.54% | 82.4 | +1.43% | −0.99% | −56.4% |
| B FX momentum（control） | −0.023 | −0.947 | −0.24% | −9.81% | 9.57% | 69.6 | +0.73% | −4.55% | −51.4% |
| C 残差（主検定） | **+0.772** | **−0.512** | +8.32% | −5.54% | 13.87% | 98.1 | +2.36% | +0.13% | −32.4% |

- **gross は正、net は大きく負**。差は全部 cost で、A で IR −1.07、C で −1.28 に相当する。
  ただし **A は cost がゼロでも advance 条件（net ≥ 0.3）に届かない**（gross +0.144、t = 0.32）。「cost が理由」と言えるのは C だけ。
- **なぜ turnover が高いのか**: 事前登録した signal（5 日変化の z-score）の日次自己相関は A 0.661・C 0.551、つまり **半減期 1.7 日**。
  Track 1 の 25.6 RT/年に対して 82〜98 RT/年になる。**band 0.10 では、この速さの signal のコストを吸収できない。**
- **必要 IC との距離（同じ土俵で比較し直す）**: 事前の 4.44% は「半減期 5 日・turnover 43.4」を仮定した値で、観測 IC は 5 日
  horizon の Spearman 相関。実測の drag と signal 自身の減衰で揃えると:

| book | 実測 signal 半減期 | 実測 cost drag | net 0.3 に必要な日次 IC | 観測 IC の日次換算 | 不足倍率 |
| --- | --- | --- | --- | --- | --- |
| A | 1.68 日 | 1.065 | **6.42%** | 1.24% | **5.2 倍** |
| B | 2.18 日 | 0.923 | 5.76% | 0.56% | 10.3 倍 |
| C | 1.16 日 | 1.284 | **7.37%** | 2.50% | **3.0 倍** |

  （観測は Spearman、法則側は Pearson 系の IC なので厳密には同一量ではない。差は不足倍率を覆す大きさではない。）
  **事前の 4.44% との比較は不足を 3 倍程度に見せていたが、実測で揃えると 5.2 倍。**
- 安定性: A は 6 block 中 **1 つだけ正**。leave-one-currency-out は **5 通り全部が負**（−0.50 〜 −1.04）。
- 集中: A の上位 5 日は net の −25.6%（net が負なので損失を和らげている側）、C の最大 DD は −32.4%。
- **通貨集中**: A の gross は GBP +0.130・USD +0.077 に対し CAD −0.121・EUR −0.045（合計 +0.075）。正の gross は 2 通貨が作っている。
- **turnover の一部は測定ノイズ**: 5 日の重なり合う変化はランダムウォークでも lag-1 自己相関 0.8（半減期 3.1 日）になるはずで、
  実測 0.661（1.68 日）はそれより速い。EUR 2 出所の 1 日変化の相関 0.65 と整合し、**signal の一部は短命な測定差**で、
  その分の turnover を払って IC を下げている。

### 凍結した文言からの逸脱（1 件、開示）

事前登録は「執行層をそのまま再利用、factor 中立化あり」と書いた。しかし層の中立化は **8 通貨の factor** に対して行うため、
観測できない 3 通貨に意図的な weight を置いてしまう。そこで **中立化は 5 通貨 universe の中で行い、層側の flag は off** にした。
凍結後の実装判断であり、結果を変えうる。実行した `BookConfig` は `artifacts/research/market_yields/development.json` の
`executed_book_config` に記録し、`deviations_from_the_frozen_text` に理由を残した。

### 執行層の副作用（実測して開示、原因は 2 つ）

実測: 日数の **70.2%** で universe 外に建玉があり、通貨 gross の **1.67%**、累積 P&L は **−0.89%**
（AUD −0.45%、CHF −0.58%、NZD +0.15%）。原因は 2 つある。

1. `band_rebalance` は「breach した gap の符号が全部同じとき、反対向きの gap が最大の通貨を counter-leg にする」。
   universe 外の通貨は gap 0 なので、その比較に勝つことがある。
2. `capped_weights` は **8 通貨で demean** する。universe 側の long / short のどちらかが 1 通貨だけになり cap が binding する日には、
   埋められなかった分が **signal を持たない通貨に丸ごと流れる**（レビューの実測で全日数の 2.75%、1 通貨あたり最大 0.0833）。
   向きは中立化が残す 1e-17 級の丸め誤差で決まる。

どちらも signal ではなく層の性質。判定（net −0.92 対 閾値 +0.3）を動かす大きさではないが、**将来 universe を絞って走らせるなら、
0 和に頼らず明示的に除外する形に変える**のが正しい。

### universe-closed 層での再実行（#485 merge 後、判定は変えない）

上の副作用を取り除いた層（`scripts/research/market_yields/portfolio.py`: demean・中立化・band・routing をすべて
5 通貨 universe の中で閉じ、両脚が universe に入る 8 pair だけで routing）で、**同じ凍結 signal を再実行**した。

| book | gross（元 → 修正後） | net（元 → 修正後） | turnover |
| --- | --- | --- | --- |
| A 利回り repricing | +0.144 → **+0.125** | −0.921 → **−0.926** | 82.4 → 82.8 |
| B FX momentum | −0.023 → −0.021 | −0.947 → −0.915 | 69.6 → 70.7 |
| C 残差 | +0.772 → **+0.630** | −0.512 → **−0.651** | 98.1 → 98.4 |

**判定は動かない。** universe 外の建玉は fast の失敗の原因ではなく、むしろ gross をわずかに押し上げていた側だった。
記録は `artifacts/research/market_yields/fast_repaired.json`。T-R2 はこの修正後の層で実行する。

### leverage と margin（#484 の枠組み）

10% vol target なら平均 risk leverage C **4.29**、routed margin は equity の **13.8%**（平均）。gap stress では equity 比例の
sizing なら loss-cut に至らず、**固定 notional のままなら至る**。ただし **この book は net が負なので、leverage は何倍でも無意味**。
年 5% / 10% の話に入る前に、正の net が要る。

## 7. screen の適用（事前登録どおり）

| 条件 | 結果 |
| --- | --- |
| A の gross Sharpe > 0 | **満たす**（+0.144） |
| A の net Sharpe ≥ 0.3 | 満たさない（−0.921） |
| C が B に対して正の net 増分を保つ | **満たす**（−0.512 − (−0.947) = +0.435。凍結した条文は増分のみを要求しており、「C 自身が正」は条文に無い。C 自身は負） |
| 1 通貨を落としても符号が残る | 満たさない（5 通り全部負） |
| 6 block の過半が正 | 満たさない（1 / 6） |
| 10% vol が gap stress の内側 | 満たす |

→ **stop**。`MARKET_YIELD_REPRICING_FAST_5D_MEASURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`。

## 8. 何が決まって、何が決まっていないか

**決まったこと（この設計について）**

- **事前登録した設計は、この seen span では経済的に成立しない。** C については理由は cost で、それは推定ではなく実測
  （turnover × 課金規約）。**A は cost がゼロでも advance 条件に届かない**（gross +0.144、t = 0.32）。
- 速い repricing measure（半減期 1.2〜1.7 日）を band 0.10 の通貨 book で運ぶと、実測 turnover が要求する日次 IC 6.4〜7.4% に対し、
  観測の日次換算は 1.2〜2.5%（不足 3.0〜5.2 倍）。
- FX momentum 単独（B）の gross は **−0.023（t ≈ −0.05）で 0 と区別できない**。net が負なのは 9.57% の cost によるもので、
  **momentum family について何かを再確認したことにはならない**（検出力不足の null）。

**決まっていないこと**

- **「市場利回りの repricing が G10 FX を先行するか」は決まっていない。** C の gross +0.772 は、4.81 年・SE 約 0.46 で
  t ≈ 1.7 にすぎない。事前に記録したとおり、この span は net 1.13 未満を分離できない。
- 増分の向きは **示唆的**ではある（C の gross +0.77 > A +0.14 > B −0.02、IC も C が最大）。しかし **これは decision-grade ではなく、
  結果を見たあとで lookback や horizon を変えることは事前登録が禁じている**。
- さらに C = A − β·B は **momentum の逆向きの脚を内包する**。B の gross はほぼ 0 なのでその寄与は小さいと思われるが、
  本記録は C の P&L を「残差」と「−β·momentum」に分解していない。C の gross を「利回り情報の増分」と読むのは、この点で未確認。
- CHF・NZD・AUD を含む 8 通貨ならどうなるかは、**このデータでは分からない**（取得できていない）。

## 9. 次にやらないこと

- signal の符号反転、lookback の変更、horizon の追加、通貨の追加・削除、vol target の変更による救済。
- stop した track を、Human + ChatGPT の新しい決定なしに独立履歴（D-1）で検定し直すこと。
- fresh pool・historical OOS・dead window・forward epoch を読むこと。

## 10. Human + ChatGPT へ返す選択肢（実行しない）

1. **T-R をここで閉じる**（この設計は成立しない、という記録のまま）。
2. **遅い repricing measure の新しい事前登録**（例: 20〜60 日の利回り変化、月次 rebalance）。turnover を Track 1 水準まで落とせば
   必要 IC は 2.7% 付近に下がる。**新しい prereg が要る**（今回の結果を根拠に lookback を選ぶのは post-hoc になるため、
   選択は Human が行う）。
3. **AUD・NZD・CHF の取得手段を確保**してから breadth 8 でやり直す（別環境・別ソース）。
4. **T-V（実質為替レート valuation、D-1 承認が前提）や T-E に進む。**

いずれも本 task では実行しない。
