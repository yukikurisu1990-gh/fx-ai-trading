# PROFITABLE_AUTOMATED_TRADING_SYSTEM_DISCOVERY — Stage 0（S0-G）最終報告（2026-09-30）

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` · `PRODUCTION_READINESS_NOT_CLAIMED`.**

Human + ChatGPT 向け。

**数字の出所**

- `artifacts/research/patsd_stage0/stage0.json`（1 回の実行記録、sha256 `0003e23c…`）
- `stage0_review_addendum.json`（独立 review の後の訂正と開示。記録は再生成していない）

**凍結の記録**: `docs/governance/patsd_stage0_ruling_2026_09_30.md`（Stage 0 の実行前に commit した）。

---

## 1. Executive Summary

| 項目 | 結果 |
| --- | --- |
| #497 | **MERGED**（head `6577acf` → merge `d38fa2c`、CI success） |
| #498 | **MERGED**（status だけを訂正 `1708378`、master の取り込み `00b7954`、merge `71f4282`） |
| Stage 0 の status | **`STAGE0_RED_RETURN_TO_HUMAN`** |
| cost（S0-1） | **GREEN**。H4 の Sharpe drag の中央値 **0.13**（20 pair 全て ≤ 0.5）。H1 は 0.67、M15 は 2.69 |
| null の誤合格（S0-2） | **GREEN**。ただし**較正は効いていない**（階段の全ての段で 0/200） |
| S0-3 | **RED**。真の Sharpe 1.5 の system の G4 通過確率 **0.025**（凍結した規則） |
| fresh の汚染（S0-4） | **GREEN**。価格の値の読み取りは無い。archive の byte の整合性の読み取りを開示 |
| rename（S0-5） | **AMBER**。本物の差は 4 family のうち 2（F4・F5） |
| 推奨 | **E（市場の breadth の拡張、R-G）を第一候補**として提案する。代替は **H**。B′ は今の形では進めない |
| R-B1 を進める価値 | **今の形では無い**（§21・§24） |

**一文で**: cost は H4 以上の horizon では障害ではない。しかし seen の fold 外 3.3 年の上で、試行を数百持つ選択 pipeline からは、真の Sharpe 1.5 の system ですら G4 に届かない。律速は、**標本（確認可能性）と多重性**である。

## 2. Identity

| | |
| --- | --- |
| #497 | final head `6577acf04776…`、merge `d38fa2c1a23b…`（2026-09-29T22:04:11Z）、CI success |
| #498 | 報告 head `25465d3` → status だけの訂正 `1708378` → master を機械的に取り込み `00b7954`（内容の変更なし）→ merge `71f4282643af…`。PR の CI success、master の CI は merge 時点で実行中 |
| Stage 0 の branch | `research/patsd-stage0` |
| code の commit | `ea5da89`（実行前に push） |
| 実行記録の commit | `952c49c` |
| 実行 | HEAD `ea5da89`、dirty 0、freeze digest `efbc86ee…`、2026-09-29T22:25:20Z → 22:27:28Z、workers 6 |
| artifact | `stage0.json` sha256 `0003e23c93ccd5755946c369778922eeaadcb999fe0f7e787e72f55eb4d11aae`（`.gitattributes` で `-text`） |
| input | 20 pair の content hash を記録に含む |

## 3. Scope

R-A だけ。

- seen の 3 window の M15 bid / ask cache を、`exploratory_m15.momentum` / `supplemental` / `bars` の `load(pair)` だけで読んだ（2021-04-26 … 2025-12-28、20 pair）。
- 使ったのは spread・range・vol の大きさの統計だけ。
- 合成 data の上の選択 pipeline の較正（S0-2 / S0-3）。
- 台帳（S0-4 / S0-5）。

## 4. Explicitly Not Executed

次のどれもしていない。

- alpha
- training
- signal と return の突き合わせ（実際の return の符号を position と対応させる経路は無い。Role 2 が全経路を追跡し、AST の test でも固定した）
- 実際の価格の経路の上の損益
- fresh / OOS / dead / forward の読み取り
- broker
- 有料 data
- 市場の拡張
- B′ の準備（特徴量・label・dataset・family の実装）

## 5. Stage 0 Data Access

| route | span | 行（EUR_USD の例） |
| --- | --- | --- |
| momentum | 2021-04-26 … 2023-04-25 | 49,972 |
| supplemental | 2023-04-26 … 2025-04-24 | 49,717 |
| bars | 2025-04-25 … 2025-12-28 | 16,796 |

`data.load_pair` は、route ごとの宣言 span・timestamp の重なり・全体の span・fresh の日付を、parsed date で確かめる。

## 6. Protected Boundary Audit

- 全ての行が 2021-04-26 … 2025-12-28 の中にある。fresh（〜2021-04-25）と OOS（2025-12-29〜）の行は無い（Role 2 が route の span を完全に再確認した）。
- 開示: route の module は freeze digest の閉包に入っていなかった（動的 import のため）。どれも Stage 0 の code commit より前から変わっておらず、hash を addendum に記録した。

## 7. Cost Measurement

**timeframe 別**（20 pair の中央値）

| TF | spread の中央値 | cost / ATR | Sharpe drag（標準の保有） | drag ≤ 0.5 の pair |
| --- | --- | --- | --- | --- |
| M15（保有 0.25 日） | 1.70 bp | 0.295 | **2.69**（1.49〜6.42） | 0 / 20 |
| H1（1 日） | 1.70 bp | 0.146 | **0.67**（0.37〜1.60） | 2 / 20 |
| H4（5 日） | 1.69 bp | 0.073 | **0.13**（0.07〜0.32） | **20 / 20** |
| D（20 日） | 1.95 bp | 0.032 | **0.04**（0.02〜0.08） | 20 / 20 |

**pair 別の分布**（H4）

| 区分 | drag |
| --- | --- |
| 最小 | USD_JPY 0.074 |
| 低い側 | EUR_JPY 0.091、GBP_USD 0.103 |
| 最大 | AUD_NZD 0.318、EUR_CHF 0.191、EUR_GBP 0.185 |

- vol の低い cross ほど不利である。
- **session**: EUR_USD の spread の中央値は asia 1.40 / europe 1.37 / us 1.41 bp で、ほぼ平坦。21 時台（UTC、夏時間の rollover）は 2.6〜7.1 bp に跳ねる。H4 の終値は 21:00 に来ないので、判定には影響しない。
- √t の推定（#498 の H4「10〜15%」）は、**実測で置き換えた**。H4 の cost / ATR は 7.3%（4.5〜14%）である。

## 8. Cost-to-Range Economics

- H4 以上では、cost は小さい（drag 0.07〜0.32）。
- H1 は境界付近（中央値 0.67）、M15 は明確に不利（2.7）。**cost は H4 以上の探索を妨げない。**
- **開示**（Role 2 RF-5）: D の bar は UTC 日で、日曜の短い bar を営業日に数えた（312 日 / 年、平日なら 261）。turnover は約 20% 大きく出ていて、**drag は保守側**である（EUR_USD: 0.112 → 平日基準で 0.093）。
- **F3（月末）の検出力**: warm-up の後の月末は 51 回。EUR_USD の 1 事象あたりの MDE は 3.96 bp（1 pair・1 時間）で、cost 1.39 bp の約 3 倍である。**pair を跨いでも相関で目減りし、検出力は小さい。**

## 9. Selection-Pipeline Null Calibration

**方法**（凍結した規則）

- 合成 data: seen の H4 mid の log return に、時点ごとに全 pair 共通の ±1 を掛ける。
- candidate: signal を持たない置き換えの規則（ランダムな entry・方向・保有）。
- 1 replication あたりの試行: 規則 216 + L2 48 + ML 0〜144 = **264〜408**。
- 手続き: #498 の選択手順をそのまま適用した（縮小・U・plateau・deflated Sharpe・fold・baseline margin・finalist 3・G4）。
- replication は 200。

## 10. False-Pass Rate

| DSR の閾値 p* | 0.10 | 0.05 | 0.025 | 0.01 | 0.005 | 0.001 |
| --- | --- | --- | --- | --- | --- | --- |
| family-wise の誤合格率 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

- 凍結した規則では S0-2 は **GREEN**（p* = 0.10 で ≤ 10%）。
- **ただし較正は効いていない**（Role 1 RF-1）。
  - 0/200 の 95% 上限は約 1.5%。
  - calibrated_p = 0.10 は階段の緩い端であって、10% への較正ではない。
  - pipeline は 10% の目標よりはるかに保守的である。
- **誤合格を防いでいるのは DSR だけ**（Role 1 NB-1）。合成で DSR を外すと、帰無の any-pass は 65〜77% になる。

## 11. Effective Trial Interpretation

- N_eff（fold 外の日次 P&L の相関 ≥ 0.8 を平均 linkage でまとめた数）の中央値は **314**（257〜378）。
- 置き換えの candidate は相関が低いので、N_eff が大きく出る。**実際の規則の格子なら低くなり、偏りは保守側である**（Role 1 NB-2）。
- **SR0 は、config ごとの決まった cost drag の違いで約 34% 膨らむ**（Role 1 RF-2。保守側）。

## 12. Confirmability Arithmetic

- fold 外の期間は **3.294 年**（warm-up 100 営業日と、最初の学習 1 年を除く）。
- SE 0.551、縮小の重み 0.513、縮小後 ≥ 1.0 に必要な観測 Sharpe は **1.88**（deflation の前）。

| 真の Sharpe | 1.0 | 1.1 | 1.5 | 2.0 |
| --- | --- | --- | --- | --- |
| 算術（deflation の前） | 0.054 | 0.077 | 0.243 | 0.583 |
| **simulation（凍結した規則、p* = 0.10）** | 0.000 | 0.005 | **0.025** | 0.060 |
| 設計どおりの「deflate してから縮小」（観測 ≥ 3.49） | ≈0 | ≈0 | **0.00015** | 0.0035 |

**結果の後の感度**（判定には使わない）:

- **N_eff の感度**（解析、DSR と G4 だけ、他の filter は無視した上限）

  | N_eff | 1〜30 | 100 | 314 |
  | --- | --- | --- | --- |
  | 真の 1.5 の通過確率 | 0.243 | 0.138 | 0.071 |

- **合成 panel で階段の外まで p* を緩めた場合**（Role 1）: p* ≈ 0.8 で帰無の FWER 7.5%、そのとき真の 1.5 の通過確率 0.39。

## 13. S0-3 Classification

**RED**（0.025 < 0.20、凍結した規則による）。

**読み方**（Role 1 RF-1・RF-3）:

- RED は、「凍結した DSR の階段（最大 0.10）」と「G4」を合わせた結果である。
- 設計どおりの G4（deflate してから縮小）では、さらに強く RED（0.00015）になる。
- 一方、「DSR を gate にし、p* を本当に 10% へ較正する」読み方を**今後**採るなら、合成では GREEN 相当（約 0.39）になりうる。
- この読み方の選択は**統計の問題ではなく、Human の判断**である。
- **Stage 0 の後に閾値を下げることは裁定 §41 で禁止されているので、Stage 0 の label は RED のまま**とする。

## 14. Success Probability Interpretation

**`MODEL_BASED_PRIOR_SUCCESS_ESTIMATE_VERY_LOW`**。凍結した参照クラスの仮定の下で、G4 の周辺確率は 0.0108、fresh の検出力 0.72 を掛けて **約 0.8%**（約 1% 以下）。

- **参照クラスの不一致**: prior は standalone な tier A mechanism（6 本）から作った。一方、探すのは選択された system の portfolio である。
- span も重なっている。
- したがって、この数字は頻度論的な実際の成功確率ではない。用途は計画・hurdle の設計・情報価値の比較に限る。

## 15. Business Objective

**production portfolio の目標**:

- `FULL_RETAIL_NET_SHARPE ≥ 1.0`
- vol 約 5%
- strategy net 約 5% 以上
- stress DD ≤ 15%

**区別**:

- 年 5% は取引 P&L で測り、financing・cash yield を分けて示す。
- **research candidate には Sharpe 1.0 を要求しない。**
- 0.8〜1.0 の candidate は `PROMISING_BUT_BELOW_PRODUCTION_TARGET` として Human に返す。

## 16. Fresh Contamination Ledger

| id | 種類 | scope | 価格の値の読み取り |
| --- | --- | --- | --- |
| X-472-ALFRED-COT | 外部情報 | US CPI の vintage・COT（2019-01 以降）。USD の macro / positioning の mechanism だけ | 無し |
| X-471-BIS | 外部情報 | 政策金利（2020-06 以降）。carry / 金利の mechanism だけ | 無し |
| X-494-CPI-DENOM | 外部情報 | 2020 年の物価水準が逆算可能。M01 / M11 / M16 だけ | 無し |
| X-D-M3 | 外部情報 | 2026 年の BoJ。forward の JPY 金利の確認だけ（fresh には及ばない） | 無し |
| X-GENERAL-EVENTS | 一般常識 | Brexit・COVID。F4 と tail の設計に効きうる | 無し |
| X-ARCHIVE | file は存在するが未読 | fresh の M1〜D の bid / ask。guard 付きの route は seen の span だけを読んだ | 無し |
| **X-BYTE-LEVEL-INTEGRITY**（review で追加） | byte の整合性の読み取り | Gate P1 PR-B と Foundation T2 が、archive の全行の hash・行数・整合性を記録した。#444 の裁定では byte の読み取りに当たる | **値の統計は無い** |

**pre-R1 の 1825d の取得**:

- 取得の code（end = now、start = end − 1,825 日）と、最も早い mtime（2026-05-02 21:18 UTC）から、最初の candle は **2021-05-03**。学習 log の最初の日付と一致する。
- fresh の終わり（2021-04-25）より 8 日後で、**重なりは無い**。
- ただし、この判定は local の mtime と、track されていない log に依る。clean clone では AMBER になりうる。

**分類: GREEN**（価格の値の情報の読み取りは無い。byte の読み取りを開示）。

## 17. Fresh Confirmation Capacity

fresh は読まずに、長さと既知の metadata だけから評価した。

- fresh は **4.89 年**。確認できる真の Sharpe は **1.12**（片側 5%・検出力 80%）。
- 汚染は特定の mechanism に限られる。**fresh は今後も、確認の資源として有用である。**
- ただし、確認できるのは Sharpe ≥ 1.1 級の portfolio だけである。

## 18. Stage 0 Gate Table

| 項目 | 分類 | 根拠 |
| --- | --- | --- |
| S0-1 cost economics | **GREEN** | H4 の drag の中央値 0.13 ≤ 0.5 |
| S0-2 pipeline の帰無 | **GREEN**（較正は効いていない） | 全ての段で FWER 0 |
| S0-3 confirmability | **RED** | 0.025 < 0.20 |
| S0-4 fresh の汚染 | **GREEN** | 値の読み取り無し・露出は限定・byte の読み取りを開示 |
| S0-5 rename | **AMBER** | 本物の差は 2 / 4（F3 を clock_flow の既存研究に訂正。凍結した境界で AMBER のまま） |
| **全体** | **`STAGE0_RED_RETURN_TO_HUMAN`** | |

## 19. Failure Cause Analysis

**主な原因は confirmability（標本と多重性）である。**

- seen の fold 外は 3.3 年しかない。試行が数百あると、DSR の hurdle は年率で約 2 近くになる（SR0 ≈ 1.96、cost の分散込み）。
- そのため、真の Sharpe 1.5〜2.0 の system でも、選択を通るのは 2.5〜6% にとどまる。
- **cost は原因ではない**（H4 以上は GREEN）。
- **誤合格の統制も原因ではない**（むしろ保守的すぎる）。
- **fresh の汚染も原因ではない。**
- rename（AMBER）は副次的で、F3 と F1 は既存研究と部分的に重なる。

## 20. D Assessment

- D（tick・quote・broker の data）は、**この failure を解かない**。cost は H4 以上で既に小さく、D は執行の精度を上げるだけで、標本と多重性の問題は変えない。
- 裁定 §26 のとおり、cost が主因ではないので D は優先しない。
- 実際の financing の実測は、将来の production の段階では必要である（`BROKER_DATA_PROPOSAL` は今は出さない）。

## 21. E Assessment（第一候補）

裁定 §28 のとおり、confirmability が主因なので **E を第一候補**とする。

**E が効く理由**

1. **breadth**: OANDA の CFD（株価指数・商品・金属など）は、FX と相関の低い独立な賭けを増やす。portfolio の Sharpe は breadth で上がるので、G4 に要る Sharpe を個々の system に求めずに済む。
2. **新しい、読んでいない履歴**: 新しい市場の data はまだ programme で見ていない。discovery / 確認の分割を最初から設計でき、確認の資源が増える。
3. **cost**: 指数・金の CFD の spread は、H4 以上なら FX と同程度の drag に収まる可能性がある。**実測は R-G の後。**

**E の代償**

- 保護 data・cost・financing・歴史の取得経路を、新しい市場ごとに作り直す必要がある（engineering 大）。
- CFD の financing は FX より大きいことが多い。
- **R-G が要る。** 今回は設計の比較だけで、取得はしていない（`MARKET_BREADTH_EXPANSION_PROPOSAL`）。

## 22. H Assessment

- H（`NO_CURRENTLY_JUSTIFIED_EXPANSION`）は、E の engineering の費用に見合う期待が無いと Human が判断した場合の、正当な選択肢である。
- 自動売買が不可能という意味ではない。

## 23. Recommended Next Path

1. **E を第一候補として提案する**（`MARKET_BREADTH_EXPANSION_PROPOSAL`）。
   - 次の段階は、data を取らずに、OANDA で取引できる CFD の一覧・cost / financing の公開情報・取得経路と保護期間の設計を作る設計 cycle。
   - 取得と実測は R-G の後。
2. **FX の B′ は今の形では進めない**（R-B1 は求めない）。
   - FX に留まるなら、試行を 30 以下の実効数に絞った「最小の B′」だけが、S0-3 を AMBER 帯（0.24）に近づける。
   - ただしそれは G4 の読み方の決定を先に要し、F1 / F3 の rename の重なりも残る。
3. E を採らないなら **H**。

## 24. Final Answers

1. **現在の M15 / H1 / H4 の実測 cost は、system discovery を始める余地を残すか？**
   → **H4 以上なら残す**（drag の中央値 0.13、D は 0.04）。H1 は境界（0.67）、M15 は不可（2.69）。
2. **selection pipeline は、null 上で false-positive を十分抑えられるか？**
   → **抑えられる。むしろ保守的すぎる**（全ての段で 0%）。ただし統制しているのは DSR だけで、他の filter はほぼ統制しない。
3. **S0-3 は GREEN / AMBER / RED のどれか？**
   → **RED**（0.025、凍結した規則）。設計どおりの G4 ではさらに RED。今後 p* を本当に較正する読み方を採るかは、Human の判断。
4. **現在の seen data から G4 へ進める候補を発見することは、統計的にどの程度現実的か？**
   → **非常に低い。** 真の Sharpe 1.5 でも 2.5%、2.0 でも 6%。model に基づく成功の推定は約 1% 以下（`MODEL_BASED_PRIOR_SUCCESS_ESTIMATE_VERY_LOW`）。
5. **fresh pool は、今後 confirmation resource としてまだ有用か？**
   → **有用**（値の読み取りは無く、露出は限定されている）。ただし確認できるのは Sharpe ≥ 1.1 級だけ。
6. **S0-G 全体は PASS か？**
   → **PASS ではない**（`STAGE0_RED_RETURN_TO_HUMAN`）。
7. **B′ discovery へ進む価値はあるか？**
   → **今の形では無い。**
8. **進まない場合、主な failure cause は何か？**
   → **confirmability**（seen の fold 外 3.3 年と、試行数百の多重性）。cost と汚染は原因ではない。
9. **そのfailure に対して、D / E / H のどれを次に検討すべきか？**
   → **E**（breadth と新しい未読の履歴）。代替は H。D はこの failure を解かない。
10. **次に Human + ChatGPT が承認すべき操作は何か？**
    → E の設計 cycle（data を取らない `MARKET_BREADTH_EXPANSION_PROPOSAL` の作成）を承認するか、H にするか。R-G（取得）は、その設計の後の別承認になる。

## 25. 独立 review の記録

役割は 2 つ。どちらも別 session で、source と記録を読み直した。記録は再生成していない。

**Role 1（統計・null の較正・確認可能性）— BLOCKER 0**

- **REQUIRED_FIX 3 件**（どれも解釈と報告で、label は変えない）:
  - RF-1: 較正が効いていない
  - RF-2: SR0 の cost の分散による膨張
  - RF-3: G4 の読み方の併記
- NON_BLOCKING 6 件:
  - DSR だけが FWER を統制している
  - N_eff は置き換えの artefact
  - 注入による SR0 の自己膨張は小さい
  - τ の不一致（0.55 / 0.565、影響なし）
  - exit 日の損益の会計
  - 0/200 の分解能
- ACCEPTED:
  - G4 の算術を再導出して一致した
  - 注入は意図どおりの真の Sharpe を作る（合成で平均 1.53）
  - 誤合格の定義
  - label の導出

**Role 2（data・cost・保護境界・engineering・alpha でないことの監査）— BLOCKER 0**

- **核心の問いへの回答**: 実際の return の符号を position と対応させる経路は無い。Stage 0 は alpha 評価に変質していない。
- **REQUIRED_FIX 5 件**:
  - 閉包に route が入っていない
  - `.gitattributes`
  - S0-5 の F3 の誤り
  - S0-4 の byte の読み取りの記載漏れ
  - 暦日と営業日の定義
- NON_BLOCKING:
  - cost の再計算が一致した（EUR_USD・USD_JPY・GBP_AUD）
  - DST の rollover
  - S0-2 GREEN が空であること
  - 重なりの推論の根拠
  - test の欠け
- ACCEPTED:
  - R-A の範囲だけに触れた
  - 決定的
  - 露出の scope は広げていない

**lead の判断**

- 全ての指摘を証拠で確かめて受け入れた。
- **実行した code と記録は変えず**、訂正は `stage0_review_addendum.json` とこの報告に書いた（code を変えると記録を再現できなくなるため）。
- 変更したのは `.gitattributes` と、test 2 本の追加（AST による「実 return は符号ランダム化と vol にだけ使う」の固定、pathlib の読み取りの guard）だけで、test は 17 本とも通る。
- **どの label も変わらない。**
- Role 2 の「DSR 以外の filter が全てを弾く」は、Role 1 の直接の測定（DSR を外すと帰無の any-pass 65〜77%）と食い違う。lead は測定のある Role 1 を採った。

## 26. Human + ChatGPT Decisions Needed（3 件）

1. **次の path**: E の設計 cycle（data を取らず、OANDA の CFD の breadth の拡張案 `MARKET_BREADTH_EXPANSION_PROPOSAL` を作る）を承認するか、H にするか。
2. **今後の cycle の G4 と較正の規則**（どの新しい cycle でも、data を見る前に決める。Stage 0 の label には遡って適用しない）:
   - 設計どおりの「deflate してから縮小」を保つか。
   - 「DSR を gate にし、p* を帰無で本当に 10% へ較正する（階段を 0.10 で止めない）」に改めるか。
   - SR0 の分散から cost の決まった分を除くか。
3. **この PR の merge**（Stage 0 の記録・addendum・報告。Amber）。

---

**STOP（裁定 §43）。** R-B1 以降は未承認で、B′ は始めない。E / D / H のどれも実行していない。
