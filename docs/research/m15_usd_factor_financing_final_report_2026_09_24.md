# USD-factor 修正と financing 監査 — 最終統合報告（2026-09-24）

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` ·
`PRODUCTION_READINESS_NOT_CLAIMED` · `POST_RESULT_IMPLEMENTATION_CORRECTED_EXPLORATORY_ONLY`

2026-09-24 第 3 裁定（measurement integrity / economic accounting / USD-factor hypothesis の完了）への最終報告。

- 数値の出典: `artifacts/research/usd_factor_financing/development.json`（1 回、M15 と M16 の両方、HEAD `69a18a0`、dirty 0）
- 記録の読み方: `scripts/research/usd_factor_financing/post_run.py`

---

## Executive Summary

- **#494 は merge 済み。** head `7fb09d5`、merge commit `32984a3`、CI green。
  - M15 / M16 は `INVALID_IMPLEMENTATION_BOOK_MISMATCH` として確定した。
- **financing 監査の結論: これまでの net は financing を含んでいなかった。**
  - Top-Five・next-five・Track 1・T-R・T-V・exploratory の net は `NET_EX_TRANSACTION_COSTS_EXCLUDING_FINANCING` である。
  - 例外は 2 つだけで、どちらも実際の OANDA financing ではない。
    - mechanism redesign: carry の近似と仮定の markup を入れていた。
    - #471: 政策金利の research carry を入れていた。
  - **OANDA の過去の financing 履歴は、公開情報では見つからなかった。** 実際の履歴を得るには、認証付きで broker にアクセスする必要がある（`PUBLIC_FINANCING_HISTORY_NOT_AVAILABLE_WITHOUT_AUTHENTICATED_BROKER_ACCESS`）。
- **USD-factor book を修正した。**
  - rebalance の単位を basket 全体にした。
  - 7 本の USD pair で持つ USD numeraire の book にした。
  - 合成入力と実際の signal の両方で、7 通貨すべてが等しい exposure を持つことを確かめた。
- **M15（dollar carry）: `FINANCING_NOT_DECISION_GRADE`。**
  - spot はほぼ 0 で、正の値はほぼすべて carry から来ている。
  - markup が 2%/年（pair notional あたり）で負になる。
  - **financing が分かっても判定できる材料は無い**（有効標本 5、spot の不確かさ）。
- **M16（米国 vs 他国の macro momentum → ドル）: `POSITIVE_EXPLORATORY_NOT_DECISION_GRADE`。**
  - long の total economic は 8 セル全点で正（central の Sharpe 0.276）で、spot に由来する。
  - null の p は 0.16〜0.19、recent は −0.50。
  - long の値は**実行前に既知だった**。
- **strong / marginal の candidate は無い。年 5% に届く candidate も無い。** M16 で年 5% を出すには DD −70% が要る。
- **推奨**:
  - この 2 本は閉じる。同じ family を seen data の上で変種にするのは勧めない。
  - 次の判断は programme の側にある。利用できる履歴の長さでは、Sharpe 0.3 級の信号は 1 本ずつ判定できない。これを前提に、何を目的とするかを決める必要がある。
  - financing の実測（broker の自口座履歴）は Human の判断事項。

---

## Identity

| 項目 | 値 |
|---|---|
| #494 | final head `7fb09d5`、merge `32984a3`（merge commit）、CI（contract-tests / test）success |
| master（#494 の後） | `32984a3` |
| 本 cycle の branch | `research/m15-usd-factor-financing`（1 PR。Amber、Human + ChatGPT の merge 承認待ち） |
| 凍結の履歴 | `daacf18`（`6f0616ff…`）→ `bc0cab7`（`3ceb6ca5…`）→ `7a1dd07`（`bccb1cee…`）→ `69a18a0`（**最終 `d3dcfbba…`**）。すべて alpha の前 |
| 実行 | 1 回、2026-09-23T23:33:42Z、HEAD `69a18a0`、dirty 0、`--workers 14`。記録 commit `f1bd264` |

## #494 Finalization

- merge 前に次のものを authoritative に記録した（`mechanism_redesign/post_run.py`）。
  - M15 / M16 = `INVALID_IMPLEMENTATION_BOOK_MISMATCH`
  - M11 / M01 = `POSITIVE_EXPLORATORY_NOT_DECISION_GRADE`
  - M10 = `NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`
  - net の定義についての caveat
  - 修正版の実行方針
  - 保護情報の policy
- mutation test は 10 件すべて捕捉した。CI は green。

## Existing Track Status

| track | status |
|---|---|
| M11 | POSITIVE_EXPLORATORY_NOT_DECISION_GRADE（fresh へは進めない。再実行しない） |
| M01 | POSITIVE_EXPLORATORY_NOT_DECISION_GRADE（同上） |
| M10 | NOT_SUPPORTED_IN_SEEN_DEVELOPMENT |
| M15（旧） | INVALID_IMPLEMENTATION_BOOK_MISMATCH |
| M16（旧） | INVALID_IMPLEMENTATION_BOOK_MISMATCH |

---

## Financing Accounting Audit（`financing_audit.py`、`financing_audit_v3.json`）

- **既存の net の中身**
  - spread は Σ|Δexposure| × 1.703bp（片道）で、slippage は実測の spread に含まれる。commission は無し。
  - **rollover・financing・swap・金利調整・triple-day・long / short の非対称・pair ごとの financing は、どれも含まれていない。**
- **cycle ごとの net**

  | cycle | net の定義 |
  |---|---|
  | Top-Five・next-five・Track 1・T-R・T-V・exploratory_m15 | `NET_EX_TRANSACTION_COSTS_EXCLUDING_FINANCING` |
  | #471 | 政策金利の research carry（spot / carry / cost を分けている） |
  | mechanism redesign | `NET_INCLUDING_APPROXIMATE_INTEREST_DIFFERENTIAL_AND_ASSUMED_MARKUP` |

- **OANDA の公開情報**
  - #472 の anonymous probe は 6 件。financing-rates と historical rates の各ページは 404 で、v20 API の account endpoint は token が要る。
  - 404 は推測した URL が外れただけの可能性があり、存在しないことの証明ではない。**公開の過去履歴は見つからなかった**、という強さの結論である。
  - 現在の swap / financing ページは**今回は取得していない**。そこには 2026 年（forward epoch）の値が載り、保護情報に当たる。現在の値から過去を逆算することも禁じられている。
- **triple-day**: 研究用の carry は暦日で accrual するので、週末の分は総量として入る。OANDA の過去の運用は検証できていない。
- **pair の非対称**: markup を |exposure| に対称に掛けた近似。実際の bid / offer の非対称は再現していない。
- **近似の名前は `APPROXIMATE_RESEARCH_FINANCING`**。actual OANDA financing とは呼ばない。

## Financing Terminology Correction

- 過去の artifact の数値は書き換えない。定義だけを正確にする。
  - これまでの「net」は `NET_EX_TRANSACTION_COSTS_EXCLUDING_FINANCING`。
  - mechanism redesign の「net」は `NET_INCLUDING_APPROXIMATE_INTEREST_DIFFERENTIAL_AND_ASSUMED_MARKUP`。
- carry の基準も cycle ごとに違う。

  | cycle | carry の基準 |
  |---|---|
  | Track 1 | 当日の政策金利（診断のみ） |
  | #471 | 政策金利 |
  | mechanism redesign | lag 付き 3 か月金利 × pair 演算子 |
  | 今回 | 当時の政策金利（primary）、lag 付き 3 か月金利（感度） |

## Historical Financing Impact Audit（再実行なし）

- **方法**（signal-blind、記録済みの数字だけを使う）
  - carry は「向きが金利と無関係なときの典型値」c = 0.38 × gross × 金利の cross-section sd とする。
  - net > 0 の track は net < c + 1%·gross なら flag する。net ≤ 0 の track は |net| < c なら flag する。
  - 測った carry がある track（Track 1・M11・M01）は、それに markup 0〜1% を足し引きして符号を見る。
- **financing で経済的な符号が変わりうる track（10 件）**:
  - Top-Five T3-H2 recent、T5 long
  - next-five U1 long、U2 long、U2 recent、U4 recent
  - T-R2 B、T-V A
  - mechanism redesign M11 long、M01 long
- **読み方**（Role 1）
  - 負の結論が candidate に変わる現実的な経路は無い。向きが金利と無関係なら carry の期待値は 0 で、markup は常に費用だからである。
  - **正の net だった過去の結果は、ほぼ一様に過大評価の方向にある。** U2 recent・U4 recent・T-R2 B・T-V A・M11・M01 は、現実的な markup で負になりうる。T5 recent は残る。
  - 判定のラベルは変わらない。どれも decision-grade ではない。
- **実行は Human の判断に回す。**

---

## USD-Factor Book Defect

- **期待した設計**: USD 対 EUR / JPY / GBP / AUD / CAD / CHF / NZD の等ウェイト basket。
- **旧実装**
  - 通貨ごとの band（0.10）で、外国の脚（0.071）が売買されなかった。
  - 同符号の breach に対する counter-leg として、アルファベット順の先頭（AUD → CAD → CHF）が選ばれた。
  - 結果として USD 対 AUD / CAD / CHF の book になり、EUR / GBP / JPY / NZD は常に 0 だった。合成入力と実際の signal の両方で再現した。
- **修正**
  - `factor_rebalance`: basket を 1 単位として動かす。band 0.10 はそのまま。
  - **USD numeraire の routing**: 7 本の USD pair で持つ。equal-split の pair book だと、recent の 20 pair で外国脚が最大 2.08 倍ずれていた。
  - band 幅・頻度・leverage・signal・符号・horizon・basket の構成は変えていない。

## Corrected Factor Exposure Tests

- 次の性質を test と `exposure_check.json` で確かめた（return は合成、signal は実物）。
  - 7 通貨すべてに等しい exposure がある。
  - USD は通貨 gross の半分で、basket と釣り合う。
  - band が 0.05・0.10・0.20 のどれでも通貨が消えない。
  - USD の符号が signal と一致する。
  - pair への routing が P&L を保つ。
  - 既定の rebalance では `construction.run_book` と完全に一致する。
- 実行記録でも、4 本すべてで `foreign_legs_equal: True`、USD の share が 0.5、投資中に 0 になった通貨は無い。

## Corrected Prereg（最終 `d3dcfbba…`）

- signal は mechanism redesign のものをそのまま使う。
- **P&L**
  - spot・spread・carry・markup の 4 行に分ける。
  - carry は 2 つの基準で測る。primary は当時の政策金利（BIS の月末値を月末から使う）、感度は lag 付き 3 か月金利。
  - markup は pair notional 1 単位あたり {0, 0.5, 1, 2}%/年。
- **判定**
  - 符号は 8 セル（金利基準 2 × markup 4）の全点で見る。
  - STRONG / MARGINAL の core 条件は、不利な端点（markup 2% で金利基準 2 つの両方）でも満たすことを要求する。
  - null は circular shift を 1000 回（seed 20260925）。total と ex-financing の 2 つの統計量で行う。
  - 有効標本数 10 未満には上限を掛ける。
- **既に見ていた値**
  - 修正版の held weight は、旧 book の band 0.05 感度行と同じだった。
  - long の central の値（net Sharpe M16 0.279、M15 0.102）、recent の値（M15 0.213、M16 −0.150）、long の null percentile は、実行前に知っていた。
- **結果を見た後の設計変更**（M15 と M16 に同じく当てた。`post_run.POST_RESULT_DESIGN_CHANGES`）
  - rebalance の単位
  - routing
  - carry の金利基準
  - markup の単位と band
  - 8 セル規則
  - 最初の 2 つは裁定の §16 / §17 が要求する修正。残りの 3 つは §7 / §11 に合わせた financing の扱い。「同一の修正」の範囲に入るかは判断事項 1。

---

## M15 Result（dollar carry）

- **Mechanism**: 外国の平均金利が米金利を上回る間、ドル factor は carry premium を払う（Lustig–Roussanov–Verdelhan）。
- **Signal**: 外国 7 通貨の 3 か月金利の平均から米 3 か月金利を引いた値の符号。> 0 ならドル売り。long span の反転は 5 回、有効標本数は 5.0。
- **Spot gross**: +0.15%/年。net ex-financing の Sharpe は 0.007（null percentile 0.43、p 0.57）。
- **Transaction costs**: 0.08%/年。
- **Financing**: carry は +1.65%/年（政策金利。3 か月金利でも +1.61%）。markup は central で −0.71%/年。
- **Total economic**（年率）

  | markup（pair notional あたり） | 政策金利 | 3 か月金利 |
  |---|---|---|
  | 0% | +1.72% | +1.69% |
  | 0.5% | +1.01% | +0.97% |
  | 1% | +0.29% | +0.26% |
  | 2% | **−1.14%** | **−1.17%** |

  **符号が揃わない。** 損益分岐の markup は 1.2%/pair notional で、平均の |金利差| とほぼ同じ。
- **Sharpe の分解**: spot 0.015、total central 0.097。
- **Turnover**: 0.79 RT/年。
- **Persistence**: 符号の反転は 5 回、regime は 6 個。
- **Temporal stability**: 36/70 ブロック。
- **Breadth**: USD を除く LOO の最悪は +0.027（central）。
- **Tail / DD**: 最大 DD −85%。
- **Null**: total の percentile 0.60（p 0.40）。
- **Profit capacity**: 8 セル全点で正ではないので算出しない。
- **Recent span**: 常にドル買い。**constant_long_usd の benchmark と完全に同じ**なので、M15 の証拠にはならない。
- **Verdict**: `M15_CORRECTED_FINANCING_NOT_DECISION_GRADE`（POST_RESULT_IMPLEMENTATION_CORRECTED_EXPLORATORY_ONLY）。
  - これは「financing が分かれば判定できる」という意味ではない。markup 0 でも E6 / E8 は偽で、null の p は 0.40。
  - spot の不確かさ（SE 約 2.5%/年）は markup band の幅と同じ大きさで、broker のデータを得ても減らない。

## M16 Result（米国 vs 他国の macro momentum → ドル）

- **Mechanism**: 米国の macro（インフレ・失業率）が他国より速く改善すると、ドル全体が上がる。
- **Signal**: M11 の score の USD 成分の符号。long span の有効標本数は 23.1。
- **Spot gross**: +3.82%/年。net ex-financing は +3.64%/年（Sharpe 0.348、null percentile 0.839、p 0.162）。
- **Transaction costs**: 0.18%/年。
- **Financing**: carry は −0.04%/年（政策金利）で、ほぼ中立。markup は central で −0.72%/年。
- **Total economic**: 8 セル全点で正。
  - central（政策金利・markup 0.5%）: **+2.88%/年、Sharpe 0.276**（null percentile 0.809、p 0.192）
  - 不利な端点（markup 2%）: +0.73%（政策金利）、+0.65%（3 か月金利）
- **P&L の出どころ**: `SPOT_DRIVEN_FINANCING_NEGATIVE`。
- **Turnover**: 1.83 RT/年。
- **Temporal stability**: 40/70 ブロック。
- **Breadth**: USD を除く LOO の最悪は 0.218。
- **Concentration**: top10 は 0.536（E6 は偽）。
- **Tail / DD**: 最大 DD −40%。
- **Cost stress**（central）: ×1.5 で 0.233、×2 で 0.190。
- **Stage 2**: signal の t は 0.92（重複を補正していないので過大）。
- **Change window**（nuisance）: 6 か月 0.095、12 か月 0.276、24 か月 0.419。**この grid の形は実行前に既知**で、24 か月を選び直すのは post-hoc。
- **Recent span**: −0.50（2.1 年、有効標本数 3）。
- **Profit capacity**: 下の Leverage / Margin の節を参照。
- **Verdict**: `M16_CORRECTED_POSITIVE_EXPLORATORY_NOT_DECISION_GRADE`。
  - MARGINAL に届かない理由: central で E6 と E8（0.276 < 0.30）が偽。不利な端点では E7 が偽（cost ×2 で markup も ×2 = 4% になる）。
  - いずれも凍結した規則どおりで、救済の論拠にはしない。

## M15 vs M16 Comparison

| | M15 | M16 |
|---|---|---|
| spot（net ex-financing、Sharpe） | 0.007 | 0.348 |
| carry / 年 | +1.65% | −0.04% |
| total central（Sharpe） | 0.097 | 0.276 |
| 8 セルの符号 | 揃わない | 全点で正 |
| null の p（total） | 0.40 | 0.19 |
| 有効標本数 | 5.0 | 23.1 |
| recent | ドル買い benchmark と同一 | −0.50 |
| verdict | FINANCING_NOT_DECISION_GRADE | POSITIVE_EXPLORATORY |

- 日次 net の相関は long で −0.15、recent で +0.47。recent は 2 本ともドル beta に寄っている。

## Financing Contribution vs Signal Contribution

- **M15 は signal の alpha ではない。** 総合の正は carry を機械的に受け取った結果で、signal の符号が金利差の符号そのものなので、carry は構造的に正になる。
- **M16 は spot（signal の方向）が本体。** financing は小さな費用にとどまる。
- どちらについても、「financing で総合が良くなった」ことを signal alpha とは書かない。

## Leverage / Margin

- **broker の上限**（margin 20x / 25x）は制約にならない。M16 で年 5% に必要な pair notional は約 2.5 倍で、25 倍口座の証拠金の約 10%。
- **portfolio gross**: 記録の portfolio_gross 5.04 は**通貨 gross**で、pair notional の 2 倍にあたる。pair_specific_margin 0.252 も 2 倍過大（保守側）。
- **risk leverage**: held gross = 1 なので portfolio_gross と同じ値で、独立の情報ではない。
- **制約は risk**
  - **M16 で年 5% には vol 18.2%、DD −70%（線形拡大）** が要る。central での financing 負担は −1.3%/年で、markup 2% なら約 −5%/年。
  - 年 10% には vol 36%、DD −140% が要り、破綻する。
  - DD を 20% に抑えると、net は約 1.4%/年。
  - M15 の long で年 5% には vol 52% が要る。

---

## Protected Data / Information Status

- **FX の fresh pool・OOS・dead window・forward epoch**: 読んでいない。
  - panel は long が 1999-01-05 … 2016-06-01、recent が 2021-04-27 … 2025-12-26。
  - 使った金利の stamp は long が 2016-05 まで、recent が 2021-05 から 2025-11 まで。保護期間に掛かる stamp は 0 件。
- **外部の metadata**: この cycle で新しく取得したものは無い。OANDA の現在値ページも取得していない。
- **D-M3（BoJ の露出）**
  - lead は BIS の属性列で 2026 年の BoJ の政策決定を読んでいる。
  - 今回は JPY の政策金利が primary の carry の会計に入ったので、`JPY_RATE_RELATED_FORWARD_CONFIRMATION_CONTAMINATED_BY_EXTERNAL_INFORMATION_EXPOSURE` がこの track にも当てはまる。範囲は JPY の金利に関わる forward confirmation に限る。
- **前 cycle から引き継ぐ開示**: CPI 前年比の分母、HICP の 2025=100、季節調整の係数、GBP の lag の慣行。M16 は M11 と同じ入力なので、これらが当てはまる。

## Request-Level Exclusion Policy

- 期間を指定できる request では、保護期間を request の段階で外すことを必須とする（`data_access/request_policy.py`）。
- 保護情報には observation 値だけでなく、metadata・属性・公表文・政策決定文も含める（`mechanism_redesign/post_run.PROTECTED_INFORMATION_POLICY`）。
- bulk-only の source は、development では taint を明示すれば使ってよい。Formal Confirmation では原則禁止。

## Forward Epoch Policy

- この cycle では forward を開かない。M16 が POSITIVE_EXPLORATORY であっても、forward は消費しない。
- JPY の金利 mechanism を将来 confirmation するなら、JPY を除外する（A）か、D-M3 の後に始まる新しい forward epoch を使う（B、推奨）。今回は決定しない。

## Engineering Findings

1. **pre-alpha review は 4 回行い、そのたびに欠陥が見つかった。**
   - carry が signal の series と同じだった。
   - recent の routing で外国脚の exposure が等しくなかった（2.08 倍）。
   - 影響監査の式が符号の向きを見ていなかった。
   - 凍結の文言が実装と合っていなかった。
2. **修正版の book は、旧 book の band 0.05 感度行と同じ held weight になる。** factor book では band が構造的に効かない。
3. **開始記録は実行前に commit されていない**（前 cycle と同じ）。1 回だけの実行だという根拠は状況証拠による。次回は、開始記録を先に commit するか、tree の外の append-only の台帳に書くことを勧める。
4. spread cost は通貨の Σ|Δx| で数えているので、USD routing では pair notional の 2 倍に課金している（保守側、0.08〜0.18%/年）。

## Candidate Status

| 区分 | 該当 |
|---|---|
| strong exploratory | 無し |
| marginal exploratory | 無し |
| positive exploratory（非 decision-grade） | M16（修正版）、M11、M01 |
| financing not decision grade | M15（修正版） |
| not supported | M10 |

---

## Final Answers

1. **M15 の修正版 book に net の経済的な edge はあったか？**
   - **決められない**（FINANCING_NOT_DECISION_GRADE）。
   - 総合は markup 1% までは正で、2% では負。spot はほぼ 0（Sharpe 0.007）で、正の値は carry を機械的に受け取った結果。
   - 有効標本は 5、null の p は 0.40。financing が分かっても判定できる材料は無い。
2. **M16 の修正版 book に net の経済的な edge はあったか？**
   - **観測上は正だが、decision-grade ではない**。long の total は 8 セル全点で正（central Sharpe 0.276）で、spot に由来する。
   - 一方で、null の p は 0.16〜0.19、recent は −0.50。long の値は実行前に既知で、Stage 2 の t は 0.92。
3. **どちらかは null / 情報の無い振る舞いを超えたか？**
   - **超えていない**。最小の p は 0.162（M16、ex-financing）。
   - 数十本の事前登録を重ねてきたことを考えると、帰無の下で予想される値そのものである。
4. **financing は過去の経済的な判定を大きく変えるか？**
   - **判定のラベルは変えない**（どれも decision-grade ではない）。
   - ただし、正の net だった過去の結果（U2 recent・U4 recent・T-R2・T-V・M11・M01）は現実的な markup で負になりうる。**過大評価の方向**。
   - 負の結論が正に転じる現実的な経路は無い。
5. **年 5% の net は、現実的な risk・leverage・margin で射程か？**
   - **射程外**。M16 でも vol 18%・DD −70% が要る。
6. **年 10% はどうか？**
   - **射程外**。vol 36%・DD −140% になる。
7. **次にやるべきものは何か？**
   - **mechanism・signal の深掘り、新しい mechanism、paid data、forward confirmation、execution engineering のどれでもない。** 次の判断は programme の側にある。
     - 利用できる履歴の長さでは、Sharpe 0.3 級の日次 FX signal を 1 本ずつ判定できないことが、繰り返し示されている。
     - financing の会計を正すと、過去の正の結果は小さくなる方向に動く。
     - 「G10 FX spot で、retail の条件のもと年 5〜10%」という目的を、このままの研究方法で追い続けるかどうかを Human + ChatGPT が決める段階にある。
   - 技術的に次に意味があるのは **financing infrastructure**、つまり broker の自口座の financing 履歴。
     - ただし、それで決められるのは carry を含む track の符号だけで、spot の不確かさは残る。
     - 認証付きのアクセスが要るので、Human の判断事項。

---

## Human + ChatGPT Decisions Needed

1. **結果を見た後の設計変更を「同一の修正」として受け入れるか。**
   - M15 / M16 に同じく当てた変更は、rebalance の単位・USD routing・carry の金利基準・markup の単位と band・8 セル規則。
   - 最初の 2 つは裁定 §16–17 の要求、残りは §7 / §11 に合わせた financing の扱い。
   - 受け入れない場合、M15 / M16 の修正版の結果は `POST_RESULT_IMPLEMENTATION_CORRECTED_EXPLORATORY_ONLY` よりさらに弱い参考値になる。
2. **broker の financing 実績の取得（認証付き、自口座）を認めるか。**
   - carry を含む track の経済的な符号を決める唯一の手段。
   - ただし、M15 のように spot の不確かさが残る track では、得られる情報の価値は低い。
3. **programme の方向。**
   - 1 本ずつの signal では検出力の天井を超えられないことが繰り返し示されている。
   - その上で、目的（年 5〜10% の net）と研究方法（seen data 上の開発と forward confirmation）をどう扱うかを決める必要がある。
   - 本 PR の merge 可否（Amber）もあわせて判断してほしい。
