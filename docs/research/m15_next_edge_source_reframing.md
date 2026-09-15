# 次の expected-return source の再設計と候補 ranking

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

作業 status: `FX_SPOT_ACTIVE_ALPHA_RESEARCH_CONTINUES_REFRAMING_NEXT_EDGE_SOURCE`（一時的な workflow status。永久 token ではない）

Human + ChatGPT 裁定（2026-09-15）に基づく research reframing。**市場データは読んでいない**。backtest・model 学習・
fresh read・broker access はしていない。数値はすべて signal-free な算術か、commit 済みの Track 1 記録から来る。
機械可読な写しは `scripts/research/edge_sources/`、記録は `artifacts/research/edge_sources/reframing.json`、
表は `tests/research/test_edge_sources.py` が package から再描画して一致を確認する。

---

## A. 直前の pause 指示の訂正

- 2026-09-14 に一度出た「FX spot active-alpha research の programme-level pause」は **撤回された**。本 PR はそれを
  採用しない。pause token、全面研究停止、CLAUDE.md / playbook の pause override、reopen trigger まで研究禁止という
  policy、「追加探索の期待情報利得が低いので停止」という programme-level 結論は、どれも記録しない。
- その pause を記録していた PR #483 は **merge せずに閉じた**（2026-09-15）。有効な研究結果（Track 1 の Case C、H-023、
  5/20/60 日に限定した H-024、tail diagnostic と similar-rule kill の方法論上の所見、保護データの状態）は本 PR に移し、
  pause governance は持ち込んでいない。
- PR #473（expectation benchmark）は本 task では merge も close もしない。**現状は open・未 merge**（研究再設計とは独立）。
- 研究は続く。Track 1 は失敗した。研究は終わっていない。

## B. Track 1 の最終 evidence

正式 status: `CONTINUOUS_CURRENCY_PORTFOLIO_ARCHITECTURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`（#481 `e13dba2`、#482 `a98fbc6`、ledger H-023）。

| 指標 | 値 |
| --- | --- |
| gross Sharpe | −0.4688 |
| net Sharpe | −0.8425 |
| net 年率 / 実現 vol | −8.42% / 9.99%（10% vol target） |
| cost | 3.74%/年（損失の 44%） |
| turnover | 25.6 RT/年/単位 gross |
| 正の fold | 1 / 6 |
| max DD | −32% |

再実行しない。結果後の feature 追加・符号反転・band 変更・leverage 変更・通貨除外・非線形救済もしない。

## C. Track 1 が実際に反証したもの

- **事前登録した線形の continuous currency expected-return architecture**（price 由来 7 特徴 → pooled ridge → 5 日先
  通貨 excess return → factor-neutral・capped・band・vol target の book）は、seen development data 上で経済的に支持されなかった。
- **continuous 化・部分 rebalance・no-trade band・turnover 低減では、負の base expected return は正にならない。**
  gross の時点で負だった。
- 学習された係数（20・60 日 reversal + 5 日 momentum）と、それに似た unfitted rule に対する劣後。

## D. Track 1 が反証しなかったもの

- `FX_HAS_NO_EDGE` ではない。FX 市場に alpha が無いことも、将来も無いことも示していない。
- **非 price 情報**（市場利回り、cross-asset、valuation、positioning、option）には一切触れていない。
- ML 一般、cross-sectional 一般、multi-timeframe 一般、event 方向一般を反証していない。
- **continuous portfolio architecture 自体**は、執行層として機能した: 予測頻度と turnover を分離し（band で
  42.8 → 25.6 RT/年/単位 gross）、差分課金の会計は正しく働いた（`TURNOVER_REDUCTION_MECHANISM_SUPPORTED`、`ALPHA_SUPPORTED` ではない）。
- H-024 の post-hoc 通貨 reversal（5/20/60 日の +0.52・+0.31）は `POST_HOC_EXPLORATORY_NON_DECISION_BEARING` で、
  5/20/60 日に限定し、他 horizon へ一般化せず、次の本命研究として復活させない。

### 方法論上の所見（今後の研究に適用、過去の判定は変えない）

- **tail concentration** は hard kill ではなく adversarial diagnostic として扱う方向。今後見るもの: top 1 / 5 / 10 day
  contribution、largest losses、top days 除外後、temporal concentration、event concentration、downside-tail concentration。
  Track 1 で使った「上位 10 日 ≤ net の半分」は実現 Sharpe ≈ 1.0 を暗に要求し、「上位 5 日除外」は厚い裾で基準を上げた。
- **similar-rule relation** は hard kill ではなく diagnostic・complexity penalty・novelty check として扱う方向。
  独立な edge を 2 つ持つ本物の分散 book でも、片方を知る rule と相関 0.6 前後になり約 2 割で誤 kill しうる。
  高相関だけで候補を自動 kill しない。
- いずれも **Track 1 の Case C は変更しない**。

## E. 現在の information set

| 区分 | 内容 | 状態 |
| --- | --- | --- |
| 保有（seen） | 20 pair の M1 bid/ask → M15（`2021-04-26 … 2025-12-28`、`EXPLORATORY_SEEN_DATA`） | 研究利用可（seen） |
| 保有 | BIS 政策金利（EUR は deposit facility 補正）、中銀会合カレンダー（Fed・ECB・BoJ・RBA の 4 行のみ、2021〜2026）、ALFRED vintage、Cleveland Fed nowcast、CFTC COT、tick volume | 研究利用可 |
| 取得不可（記録済み） | BoE・BoC・SNB・RBNZ の会合カレンダー（#472 で自動取得をすべて拒否、手作業の再構成はしない）、非 USD 機関の時刻付き発表カレンダー（C02） | 取得不可 |
| 保有（未 merge） | survey consensus（#473 の branch） | #473 未 merge |
| 無料・未取得（metadata 確認） | FRED の US 2 年金利 日次 `1976-06-01〜`、VIX `1990-01-02〜`、Nikkei 225 `1949-05-16〜`、Brent `1987-05-20〜`、SOFR `2018-04-03〜`。S&P 500・HY OAS・WTI・US 10 年は page は到達したが range を parse できず**履歴長は未確認**（S&P 500 と ICE 系列は license で短縮されている可能性）。probe した非 US 10 年は OECD の月次系列で、FRED 上の非 US 日次系列は probe していない | 取得は承認後 |
| 無料・未取得（到達性のみ確認） | 非 US の日次 2 年金利: BoE・BoC Valet・日本 MOF は到達、ECB・Bundesbank・SNB は本環境で証明書エラー、RBA・RBNZ は script に 403（**いずれも未確認で、8 通貨揃うかは分からない**） | 取得は承認後 |
| 無料・長期 FX 履歴（**確認していない**） | Fed H.10・ECB 参照レート等の公開日次 FX。FX 系列のページは保護 span・forward epoch の値を含むため、metadata 確認も含め一切取得していない | read には保護 span を除外した Red 承認が要る（W 節 D-1） |
| 有料 | FX option（risk reversal）、intraday 株価指数先物、CME FX 先物 intraday、OIS / 金利先物の履歴 | 未取得 |
| 認証要（未承認） | OANDA positionBook、IG client sentiment | 禁止 |

metadata 確認の記録: `artifacts/research/edge_sources/public_data_availability.json`（非 FX のみ、値は分析していない）。
それを出力した probe は `scripts/research/public_data_probe/availability_check.py` として commit した（再実行は承認後）。

## F. 既存の engineering asset（再利用）

- **Track 1 の執行層**: 通貨レベル表現、factor neutralization、target weight、pair routing、部分 rebalance、no-trade band、
  turnover 会計、vol scaling。新しい source の評価共通基盤として再利用する。**Track 1 の alpha model は再利用しない。**
- cost framework（pair 往復 2.58 bp、課金 3.406 bp/turnover unit、faithful cost）、unit-safe 換算、Feasibility Gate v2、
  signal-blind な capacity / search budget、walk-forward・purge・embargo、leakage guard、事前登録の凍結・実行束縛、
  変異テスト、hypothesis ledger、event calendar、public macro data。

## G. Expected-return source map（既存研究の分類）

分類は各記録の status 語と内容から付けた。ledger 上の status が `CLOSED - …` でも token が NOT_SUPPORTED のもの（H-016・H-020・H-021・H-023）は
NOT_SUPPORTED に置き、決定により停止中の inventory 候補（C04・C05）は SUSPENDED に置いた。SUSPENDED・NOT_DECISION_GRADE を
CLOSED 扱いしない。**検出力不足の null として記録されたもの**（H-005・H-007・H-012、H-020・H-021 の注記）は内容欄に明記した。

<!-- table:evidence_map -->
| ref | 内容 | 分類 | 記録上の status |
| --- | --- | --- | --- |
| H-001 | M15 indicator zoo の絶対方向 | CLOSED | `CLOSED` |
| H-002 | session / ATR / ADX / spread gate | CLOSED | `CLOSED` |
| H-003 | pair relative strength（通貨 exposure が 96%） | CLOSED | `CLOSED` |
| H-004 | raw / simple price-feature の方向 ML | CLOSED | `CLOSED` |
| H-005 | multi-day reversal の 39 config（検出力 0.29 の検出力不足の null。family は後に dropped） | CLOSED | `MULTI_DAY_REVERSAL_UNRESOLVED_INSUFFICIENT_DETECTION_POWER` |
| H-006 | 4〜6 日 reversal family | CLOSED | `MULTI_DAY_REVERSAL_FAILED_SUPPLEMENTAL_HISTORY_REPLICATION` |
| H-008 | Round A の条件付け family | CLOSED | `CLOSED — Round A` |
| H-009 | 単純な HTF / D1 trend 条件付け | CLOSED | `CLOSED — Round A` |
| H-010 | price-path structure（VR<1、収益化不能） | CLOSED | `CLOSED - real but unharvestable microstructure` |
| H-013 | retrace geometry（clean retest） | CLOSED | `RETRACE_GEOMETRY_FAMILY_DROPPED_AFTER_CLEAN_RETEST` |
| H-014 | path linear monetization（固定 horizon、線形 selector） | CLOSED | `PATH_STRUCTURE_STATISTICALLY_REAL_BUT_ECONOMICALLY_TOO_SMALL` |
| H-017 | tick volume の方向 / timing | CLOSED | `CLOSED - volume is a volatility variable, not a timing one` |
| H-024 | post-hoc 通貨 reversal（5/20/60 日のみ） | CLOSED | `POST_HOC_EXPLORATORY_NON_DECISION_BEARING` |
| C08 | currency rank persistence | CLOSED | `PRIOR_FAMILY_CLOSED` |
| C21 | futures positioning（COT 由来） | CLOSED | `PRIOR_FAMILY_CLOSED` |
| C22 | carry level | CLOSED | `PRIOR_FAMILY_CLOSED` |
| H-012 | monthly TSMOM（ledger 自身が「検出力不足の null、反証ではない」と記録） | NOT_SUPPORTED | `MONTHLY_TSMOM_NOT_SUPPORTED_IN_EXISTING_PRICE_HISTORY` |
| H-016 | 政策金利 proxy の carry（level / change） | NOT_SUPPORTED | `CARRY_EDGE_NOT_SUPPORTED` |
| H-020 | USD CPI の nowcast surprise 方向（ledger: 無料データで有用な breadth では検定不能） | NOT_SUPPORTED | `MACRO_SURPRISE_DIRECTIONAL_EDGE_NOT_SUPPORTED` |
| H-021 | COT の tested cells（同じ長さの再現では検出力が同じで何も決まらない、と ledger が記録） | NOT_SUPPORTED | `COT_EDGE_NOT_SUPPORTED` |
| H-023 | linear continuous currency expected-return architecture | NOT_SUPPORTED | `CONTINUOUS_CURRENCY_PORTFOLIO_ARCHITECTURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` |
| #471 | event-day の cost 優位 | NOT_SUPPORTED | `EVENT_DAY_COST_ADVANTAGE_NOT_ESTABLISHED` |
| #475 | near-touch passive 執行 | NOT_SUPPORTED | `passive 執行は、この 2 パネルで意味のあるコスト削減を与えられない。` |
| H-007 | mirror momentum（反証ではなく検出力不足の null。ledger の status は CLOSED だが、drop されたのは reversal family で momentum は UNRESOLVED） | NOT_DECISION_GRADE | `MULTI_DAY_MOMENTUM_UNRESOLVED_IN_FRESH_EXPLORATORY_HISTORY` |
| H-022 | model learning（3 track、当時の gate。run は gate 無効化で evidence ではなく record） | NOT_DECISION_GRADE | `MODEL_LEARNING_NOT_DECISION_GRADE_UNDER_CURRENT_DEVELOPMENT_GATE` |
| #478 | seen data 上の長 horizon 構造（検出力不足） | NOT_DECISION_GRADE | `CURRENT_SEEN_DATA_FX_RESEARCH_SPACE_EXHAUSTED` |
| C09 | yield differential change（未実行。horizon・economic_net_under_stress・dispersion window で不合格、追加履歴でも pass region は開かない） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C10 | equity risk regime conditioning（未実行。horizon・economic_net_under_stress・dispersion window で不合格、追加履歴でも pass region は開かない） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C11 | commodity link response（未実行。horizon・economic_net_under_stress・dispersion window で不合格、追加履歴でも pass region は開かない） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C01 | central bank decision response（未実行。horizon と dispersion window で不合格、economic は通過。取得可能な中銀は 4、年 34.4 回） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C03 | session handover relative（未実行。horizon・economic_net_under_stress・dispersion window で不合格） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C06 | factor-neutral residual value（未実行。horizon・economic_net_under_stress・dispersion window で不合格） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C07 | cross-sectional dispersion state（未実行。horizon・economic_net_under_stress・dispersion window で不合格） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C13 | timeframe disagreement state（未実行。horizon・economic_net_under_stress・dispersion window で不合格） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C12 | volatility regime transition（未実行。horizon・economic_net_under_stress・dispersion window で不合格） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C14 | latent regime state（未実行。horizon・economic_net_under_stress・dispersion window で不合格） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C16 | horizon selection（未実行。horizon・economic_net_under_stress・dispersion window で不合格） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C18 | ML currency ranking（未実行。horizon・economic_net_under_stress・dispersion window で不合格） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C19 | ML take / skip gate（未実行。horizon・economic_net_under_stress・dispersion window で不合格） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| #475 | clock / London fix の構造 | SUSPENDED | `CLOCK_STRUCTURE_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER` |
| #477 | non-USD surprise relative | SUSPENDED | `NON_USD_SURPRISE_DATA_NOT_DECISION_GRADE_SKIP` |
| C04 | benchmark fix flow（決定により停止、提案不可。horizon・economic_net_under_stress でも不合格） | SUSPENDED | `NO_DECISION_GRADE_PASS_REGION` |
| C05 | month-end rebalancing flow（決定により停止、提案不可） | SUSPENDED | `NO_DECISION_GRADE_PASS_REGION` |
| C02 | macro surprise intraday | SUSPENDED | `DATA_INTEGRITY_BLOCKED` |
| C20 | broker order flow | SUSPENDED | `DATA_INTEGRITY_BLOCKED` |
| H-011 | retrace geometry（B′-2） | OPEN | `OPEN` |
| H-015 | tick volume → 将来の活動・volatility | OPEN | `TICK_VOLUME_INFORMATION_INCREMENTALLY_DISTINCT` |
| H-018 | 政策金利変更日の movement structure（cost 優位は不成立） | OPEN | `CALENDAR_EVENT_MOVEMENT_STRUCTURE_SUPPORTED` |
| H-019 | forward-known event の movement（方向なし） | OPEN | `FORWARD_KNOWN_EVENT_OPPORTUNITY_STRUCTURE_SUPPORTED` |
| #482 | efficiency bundle（band・部分 rebalance）の turnover 低減。裁定 token TURNOVER_REDUCTION_MECHANISM_SUPPORTED は H-023 に記録 | ENGINEERING_RESULT | `bundle は本来の目的（turnover 削減）は果たした` |
| #476 | unit-consistent feasibility gate | ENGINEERING_RESULT | `FEASIBILITY_GATE_V2_PROSPECTIVE_ONLY` |
| C15 | movement magnitude forecast（gate の対象外） | UNTESTED | `OUT_OF_GATE_SCOPE` |
| C17 | intraday execution timing（gate の対象外） | UNTESTED | `OUT_OF_GATE_SCOPE` |
| — | 市場利回り（2 年・曲線）による repricing | UNTESTED | `未取得・未検定` |
| — | 実質為替レート / valuation | UNTESTED | `未取得・未検定` |
| — | event 日の市場 repricing を方向ソースにする構造 | UNTESTED | `未検定` |
<!-- /table -->

## H. Rates / yield-curve の評価（候補 S01・S02・S23・S25・S27・S28）

- **S01（front-end 金利差 repricing）が最有力だが、prior は中程度で出典のない判断**。過去に閉じたのは政策金利（階段関数）の
  level / change（H-016、`CARRY_EDGE_NOT_SUPPORTED`）で、**市場利回り**は一度も取得していない。
- **C09（yield differential change）は反証ではないが、horizon だけで落ちたのでもない**。inventory では horizon・dispersion window に
  加えて `economic_net_under_stress` でも不合格（margin −0.63）で、追加履歴でも pass region は開かないと記録されている。economic
  不合格は inventory の未実行候補 15 のうち 13 に共通で、事象ごとに 1 往復のコストを仮定した設計規約に依存し、#480 の band law（20 日半減期で 18 RT/年）では前提が変わる、
  というのが本節の主張であり、**それ自体は未検証**。
- mechanism: 市場が織り込む政策パス（2 年金利）の相対変化に FX が遅れて追随する。同時相関は強いと予想されるが、
  **先行性**（数日〜数週の under-reaction）が問い。
- **偽装 momentum の危険**: 2 年金利差と FX は同日に強く共動するので、lag 付きの利回り変化は lag 付きの FX return（閉じた・
  検出力不足の momentum family: H-005/H-007/H-012、Track 1 の 5 日 momentum leg）を大きく含む。**同じ lookback の FX momentum を
  control にし、それを超える部分だけを S01 の情報と認める**。under-reaction に最も忠実な形は「利回りが動いたのに FX がまだ
  追随していない」乖離である。
- capacity（R 節）: 半減期 20 日で net 0.5 に日次 IC 2.9%（breadth 2 なら 4.1%）、AR(1) の 20 日 IC で 9.5%。
- 最大の技術的罠は **非同期終値**: 各国の利回り終値は現地時刻で、FX の日次終値（例 21:00 UTC）と揃わない。
  利回りを 1 日遅らせるか、FX 側を利回り終値の後の時刻に揃えないと先読みになる。
- **データが律速**: US は FRED 日次で長期に揃うが、非 US の日次 2 年金利は各中銀から個別に取得する必要があり、本環境で到達を
  確認できたのは 7 中 3（E 節）。8 通貨揃わなければ breadth が下がる。
- S02（曲線形状）は S01 と同点の 3 位だが、同じ金利データを使う第 2 の金利仮説で prior が弱い（W 節で別 track にしない理由）。
  S23（実質金利差 level）はここでの定義（政策金利 + CPI）では H-016 の組み替えなので除外。市場の実質利回りで作る版は
  S28（breakeven）・S13 の隣接として扱う。S25（balance sheet）と S26（資本 flow）は観測数が少なく低 capacity。
  S27（中銀 communication の tone）は新しい情報源だが、テキストの時刻付き archive が未確認でテキスト処理の負担が重い。

## I. Cross-asset lead-lag の評価（S05・S06・S07・S24）

- FX は 24 時間連続取引なので、株式・商品の情報は **同時に** 織り込まれる prior が強い。先行性を主張するには
  時刻を揃えた検定（株式終値と同時刻の FX）が必須で、日次終値のずれは見かけの lead-lag を作る。時刻を揃えられるのは
  seen span の M1 archive だけ。
- S05（risk shock → funding vs 資源国通貨）は VIX・Nikkei が無料で長期に揃う（S&P 500 の履歴長は未確認）が、実効 breadth が
  2 程度で、必要 IC が約 1.4 倍に上がる。
- S06（商品 → 資源国通貨）は breadth 1〜2 で単独の年 5% は困難。S07（信用 stress）は stress 期に偏り tail 集中が大きく、
  HY OAS の履歴長も未確認。
- S24（vol で timing した carry）は NOT_SUPPORTED の carry を vol filter で救済する形なので **除外**。
- 結論: cross-asset は top 3 に入れない。S05 は S01 の検定後に、同じ執行層で安価に追加できる次点。

## J. Currency network / triangular structure の評価（S09・S10・S11）

- S09（三角 residual）は、改名ではなく **構造的に不成立** のため除外: bid/ask を整合させると乖離は spread の内側に収まる
  無裁定構造で、H-010（収益化不能な microstructure）と同じ層。
- S10（bloc 間 lead-lag 伝播）は aggregate VR（H-010）とは別の未検定仮説だが、FX の伝播は秒単位で裁定される prior が強く、
  intraday の turnover で cost を超えるには日次 IC 7% 以上（breadth 2 なら 10%）が要る。低順位。
- S11（動的共通 factor residual の reversal）は H-024 の post-hoc 通貨 reversal と同形で、**名前を変えた復活になるため除外**。
- H-003（pair relative strength、通貨 exposure が 96%）との違い: Track 1 は通貨単位・factor 除去済みで H-003 の欠陥を
  構成で避けたが、price 由来の期待リターンそのものが負だった。network 構造は情報源ではなく **執行層**（pair routing、
  netting）として既に使っている。

## K. Relative-value / residual の評価（S12・S13）

- S12（相関 breakdown / dispersion の relative value）は price 由来の収束で H-024 と隣接、#480 の A12 でも年 2% 未満と
  **判断**された（試算ではなく宣言した判断）。低順位。
- **S13（実質為替レート valuation）が第 2 位。** valuation は一度も検定していない（H-016 は carry、H-012 は momentum）。
  学術的な currency value premium は長期で存在し、低 turnover（約 5 RT/年）で cost の影響が小さい。
- ただし **seen の 4.7 年では検定不能**（半減期が年単位）。数十年の公開 FX 履歴が要り、それは保護 span
  （`2016-06-02 … 2021-04-25` の fresh pool、historical OOS、dead window、forward epoch）を**除外した** Red 承認の read を要する。
- leakage: CPI は公表日（lag と改定あり）で揃え、AUD・NZD の CPI は四半期。PPP anchor は ex-ante（拡張窓または固定基準）に
  限り、全期間平均を使わない。2021 年以降の日付で数年の lookback を取ると fresh pool の FX 水準が要るので、warm-up は
  seen または pre-2016 の範囲に閉じる。
- capacity: 120 日半減期で net 0.5 に日次 IC 2.1%、AR(1) の 120 日 IC で 16.8%。学術 prior は G10 value 単独で net 0.2〜0.4
  程度で、**単独で年 5% は楽観的**、他 source との分散源として価値がある。

## L. Multi-horizon interaction の評価（S14・S15）

- S14（fast/medium/slow の price state 不一致）は、Track 1 が 5/20/60 日の強さと trend age を線形に使って gross 負だった
  直後で、price 由来の多 horizon 情報に正の prior が無い。単純 sign conditioning（H-009）とは違う形にしても、
  情報源が同じ price なら indicator zoo に戻る危険が大きい。低順位。
- S15（状態遷移・latent regime）は条件付けであって return source ではない。H-022 の regime-gain は一定 gross の book では
  日ごとのスカラーが消えるため **測定されておらず**（反証ではない）、その run も gate の無効化で evidence ではなく record。
  base が負なら条件付けは救済にならないので低順位。

## M. State-dependent nonlinear の評価（S16・S08）

- 非線形を研究仮説にしない。**S16（金利 repricing × volatility の閾値効果）** だけが機構から説明できる候補
  （risk 環境が荒れると金利差の感応度が落ちる）で、**S01 の線形 baseline が正になった場合の増分検定**としてのみ残す。
- S08（金利 vol 状態）は単独の return source ではなく、S16 に統合。
- 「LightGBM なら拾うかも」は採らない。順序は economic mechanism → feature family → simple baseline → nonlinear 増分。

## N. Event-conditioned の評価（S03・S04・S17・S27）

- 過去の証拠は **event → movement / volatility が強く、方向が無い**（H-018・H-019 は OPEN の movement structure、
  H-020 の USD nowcast surprise は NOT_SUPPORTED で ledger は「無料データで有用な breadth では検定不能」と記録、
  #471 の event-day cost 優位は不成立）。
- 新しい構造は **event × 別の方向ソース**: event 日の**市場 repricing**（2 年金利の当日変化）を surprise の測度にし、
  その後数日の FX drift を狙う。consensus も発表時刻も要らない（C02 の時刻問題、#477 の検出力問題を回避）。
- **S03（中銀会合）** は mechanism が最も明確だが、**会合カレンダーを取得できるのは Fed・ECB・BoJ・RBA の 4 中銀だけ**
  （年 34.4 回、C01 の実測）。BoE・BoC・SNB・RBNZ は #472 で自動取得をすべて拒否し、手作業の再構成はしない規則。
  事象数が検出力の律速で、年 5% には届きにくい。
- **S04（主要指標発表）** は事象数を 150〜300 に増やしうるが、非 USD 機関の無料の公式発表カレンダーは時刻付きでは存在せず
  （C02）、日付だけのカレンダーの可否は未確認。未 merge の #473 が survey consensus の USD 1h で検出力のある null を返しており、
  announcement 効果が 1h に集中するなら多日 drift も弱い、という警告付き。
- **price continuation の偽装**: event 日の repricing の符号は event 日の FX return と大きく重なる。event 日の FX return
  自体を control にし、それを超える部分だけを repricing の情報と認める。
- capacity（R 節）: S03（n=34.4・3 日保有）で net 0.5 に事象あたり 12.0 bp（課金）/ 7.7 bp（pair）、集中 position の vol 7% なら
  14.6 bp。S04 込み（n=150〜300）で 8.3〜9.3 bp（集中なら 9.1〜10.5 bp）。
- S17（event × cross-asset 共動）と S27（communication tone）は S03・S04 の後の増分・別情報源としてのみ。
- **event filter で負の base を救済するものではない**: 方向は event ではなく repricing が決める。T-R の結果を見た後に
  event 日へ絞ることは救済になるので、T-E の事象母集団と規則は T-R の結果を読む前に凍結する（W 節）。

## O. Positioning / flow の評価（S18・S19・S20・S26）

- S18（retail positioning）は OANDA positionBook（認証要・禁止）、IG（口座要）、Myfxbook（web、過去履歴なし）で、
  **無料の過去履歴が揃わない**。forward に蓄積するしかなく、データ不可。
- S19（COT 変化 × price）は H-021（tested cells NOT_SUPPORTED）・C21（PRIOR_FAMILY_CLOSED）に重なり除外。
- S20（FX option の risk reversal）は prior が比較的強いが **有料データ**。取得は Human + ChatGPT の判断事項（勝手に取得しない）。
- S26（US TIC・国際収支の資本 flow）は COT（先物の投機 positioning）とは別の現物証券 flow で未検定だが、月次・公表 lag 約 6 週で
  観測数が少なく、seen では検定不能。

## P. Intraday information transmission の評価（S21・S22）

- S22（session 間の cross-market 情報伝達）は price のみにすると C03・H-002（CLOSED）と同じで、非 FX の intraday 情報
  （株価指数先物）は有料。データ不可。
- S21（月末の株式相対リターンに条件付けた hedge rebalance flow）は、inventory で **C04（benchmark fix）・C05（month-end
  rebalancing）が決定により停止・提案不可**なので除外（改名ではなく、停止中 family に属するため）。加えて年 12 事象で、
  年 5% には構造的に届かない。
- 単なる時刻平均リターンへの回帰はしない。

## Q. Candidate universe（28 候補）

28 候補のうち、閉鎖 family の改名・救済として除外したのが 4（S11・S19・S23・S24）、他の候補の増分に過ぎないのが 3
（S08・S16 は S01 の、S17 は S03・S04 の増分）。**独立な方向として数えられるのは 21**（データ不可 3、構造的不成立 1、
停止中 family 1 を含む）。

### Q.1 定義

<!-- table:candidate_definitions -->
| ID | 方向 | 候補 | mechanism | information | target / horizon | architecture |
| --- | --- | --- | --- | --- | --- | --- |
| S01 | A | front-end 金利差 repricing → 通貨相対リターン | 市場が織り込む政策パス（2 年金利）の相対変化に、FX が数日〜数週遅れて追随する | 各国 2 年国債利回りの日次変化（通貨ごとに対 G10 平均） | 通貨の 5〜20 日先 excess return／5〜20 日 | continuous currency book（Track 1 の執行層を再利用） |
| S02 | A | 曲線 slope / curvature 差の変化 | 成長・インフレ期待の相対変化が通貨需要を動かす | 各国 2s10s・曲率の日次変化 | 通貨の 20〜60 日先 excess return／20〜60 日 | continuous currency book |
| S03 | G | 中銀会合日の市場 repricing → 会合後 drift | 会合日に市場が織り込んだ政策パスの変化（2 年金利の当日変化）に、FX が会合後数日かけて追随する（under-reaction） | G10 中銀会合カレンダー + 会合日の 2 年金利変化 | 会合通貨の 1〜5 日先 excess return（repricing の方向）／1〜5 日 | event book（idle 時は保有なし、Track 1 の執行層で差分売買） |
| S04 | G | 主要指標発表日の市場 repricing → 発表後 drift | surprise を consensus ではなく当日の市場 repricing（2 年金利の変化）で測り、発表後数日の FX drift を狙う | G10 主要指標の発表日 + 当日の 2 年金利変化 | 発表通貨の 1〜5 日先 excess return／1〜5 日 | event book |
| S05 | B | 株式・volatility shock → funding 通貨 vs 資源国通貨（時刻整合した lag） | risk appetite の変化が funding / carry 通貨へ遅れて波及する | VIX（FRED 日次 1990〜）、Nikkei（FRED 日次 1949〜）、S&P 500（FRED、range は probe で取れず、license で直近約 10 年に限られる可能性） | JPY・CHF 対 AUD・NZD・CAD の 1〜5 日先 excess return／1〜5 日 | continuous currency book |
| S06 | B | 商品価格 → 資源国通貨（terms of trade lead） | 原油・金属の価格変化が交易条件経由で CAD・AUD・NZD に遅れて反映される | WTI・Brent（FRED 日次）。金属の日次は無料では限定的（銅は月次） | CAD・AUD・NZD の 5〜20 日先 excess return／5〜20 日 | continuous currency book（3 通貨に集中） |
| S07 | B | 信用 spread・funding stress → USD・JPY・CHF | funding 市場の緊張が安全通貨需要に先行する | US HY OAS（FRED 日次）、SOFR（2018〜） | USD・JPY・CHF の 5〜20 日先 excess return／5〜20 日 | continuous currency book |
| S08 | B | 金利 volatility 状態 × FX | 金利 volatility の高低で FX の金利感応度が変わる | 利回り変化から推定する rates vol（MOVE は有料） | S01 の条件付け／5〜20 日 | S01 への条件付け |
| S09 | C | 三角 residual（cross と合成 cross の乖離） | pair 間の一時的な不整合の解消 | 20 pair の bid/ask | residual の縮小／秒〜分 | 高頻度 |
| S10 | C | 通貨 complex 間の lead-lag 伝播（例: EUR→CHF、AUD→NZD） | bloc の先行通貨の動きが追随通貨へ遅れて伝わる | 通貨 excess return の intraday 系列 | 追随通貨の数時間先 return／数十分〜数時間 | intraday currency book |
| S11 | C | 動的共通 factor residual の reversal | 共通 factor から外れた通貨が戻る | 通貨 excess return の rolling PCA residual | residual の 5〜20 日先縮小／5〜20 日 | continuous currency book |
| S12 | D | 相関 breakdown / dispersion 状態の relative value | 通常の共動から外れた pair が収束する | rolling 相関と dispersion | pair spread の 5〜20 日先／5〜20 日 | pair relative-value book |
| S13 | D | 実質為替レート valuation（PPP・実質金利 anchor） | 実質為替レートの長期均衡からの乖離が数か月〜数年で戻る（学術的な currency value premium） | 各国 CPI（月次、AUD・NZD は四半期）と長期の FX 水準 | 通貨の 3〜12 か月先 excess return／3〜12 か月 | continuous currency book（低 turnover） |
| S14 | E | fast / medium / slow の price state 不一致 | horizon 間で状態が食い違うときの期待リターン | 複数 horizon の price state | 通貨の 5〜20 日先／5〜20 日 | continuous currency book |
| S15 | E | volatility / trend の状態遷移（latent regime） | 状態の切り替わり直後に期待リターンが変わる | price 由来の regime 推定 | 通貨の 5〜20 日先／5〜20 日 | continuous currency book |
| S16 | F | 金利 repricing × volatility の閾値効果 | 金利差の変化が効くのは risk 環境が落ち着いているときに限る、という相互作用 | S01 + risk 状態（VIX 等） | S01 と同じ／5〜20 日 | S01 の非線形増分 |
| S17 | G | event 日の cross-asset 共動を方向ソースにする | event 日に株式・金利がどちらへ動いたかが、その後の FX の方向を決める | event カレンダー + 当日の株式・金利変化 | event 通貨の 1〜5 日先／1〜5 日 | event book |
| S18 | H | retail positioning の逆張り | retail の片寄りが逆方向の将来リターンに対応する | OANDA positionBook（認証要・禁止）、IG client sentiment（口座要）、Myfxbook（web、履歴なし） | pair の 1〜5 日先／1〜5 日 | pair book |
| S19 | H | COT の変化 × price の相互作用 | 投機ポジションの変化と price の食い違い | CFTC COT（取得済み） | 1〜4 週／1〜4 週 | currency book |
| S20 | H | FX option の risk reversal / implied vol skew | option 市場の片寄りが spot の将来方向を示す | 25 delta risk reversal | pair の 5〜20 日先／5〜20 日 | currency book |
| S21 | I | 月末の株式相対リターンに条件付けた hedge rebalance flow | 月中に外国株が米国株に負ければ、海外投資家の hedge 調整で月末に USD の売買が起きる | 月次の株式指数リターン | 月末 fix 前後の USD／数時間〜1 日 | event book |
| S22 | I | session 間の cross-market 情報伝達（Asia→London、London→NY） | 前 session の非 FX 市場（株価指数先物等）の情報が次 session の FX に遅れて伝わる | intraday の株価指数先物（有料）。price のみにすると C03 と同じ | 次 session 開始後数時間の通貨 return／数時間 | intraday currency book |
| S23 | A | ex-ante 実質金利差の level | インフレ調整後の金利差が高い通貨が上がる | 政策金利・利回り − インフレ期待 | 月次／1〜3 か月 | currency book |
| S24 | B | volatility で timing した carry（crash risk 回避） | 高 vol 期に carry を減らす | carry + VIX | 月次／1 か月 | currency book |
| S25 | A | 中銀 balance sheet・準備資産 flow | QT / QE の相対ペースと準備資産の再配分が通貨需要を動かす | 中銀 balance sheet（FRED 等、週次〜月次） | 3〜12 か月／3〜12 か月 | currency book（低 turnover） |
| S26 | H | 国際資本 flow（US TIC・国際収支）の相対変化 | 海外投資家の証券売買 flow の変化が、ヘッジ・決済需要として通貨需要に遅れて表れる | US Treasury TIC（月次、約 6 週の公表 lag）、各国の国際収支（月次〜四半期） | 通貨の 1〜3 か月先 excess return／1〜3 か月 | continuous currency book（低 turnover） |
| S27 | A | 中銀 communication の tone 変化（声明・議事要旨・講演） | 声明文の hawkish / dovish への変化が、市場の政策パス織り込みより先に通貨需要を動かす | 中銀の公開テキスト（声明・議事要旨・講演）の tone score | 会合通貨の 1〜20 日先 excess return／1〜20 日 | event book または continuous currency book |
| S28 | A | 市場のインフレ期待（breakeven）の repricing | 名目金利ではなく実質金利側の変化（breakeven の変化）が通貨の実質リターン期待を動かす | US 5 年・10 年 breakeven（FRED 日次）、非 US の breakeven は限られる | 通貨の 5〜20 日先 excess return／5〜20 日 | continuous currency book |
<!-- /table -->

### Q.2 実現可能性・重なり・capacity

<!-- table:candidate_feasibility -->
| ID | turnover | utilisation | breadth | data | access | 既存研究との重なり | なぜ未反証か | capacity | ML の役割 | 扱い |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | 18〜43 RT/年/単位 gross | 常時 | 8 通貨（実効 4） | US 2y は FRED 日次 1976〜。非 US 2y は各中銀で、到達を確認できたのは BoE・BoC・MOF の 3 つだけ（ECB・Bundesbank・SNB は本環境で証明書エラー、RBA・RBNZ は 403、いずれも未確認）。8 通貨揃うかは未確認 | 公開・認証不要のはず（取得可能性は 7 中 3 のみ確認、取得は承認後） | H-016、C09、H-023 | H-016 は政策金利（階段関数）の level / change で、市場利回りは未取得。C09 は未実行だが horizon・dispersion window に加え economic_net_under_stress でも不合格（margin −0.63）で、この不合格は日次 1 往復を仮定したコストに依存する（#480 の band law では 20 日半減期で 18 RT/年）。追加履歴でも pass region は開かないと inventory が記録 | net 0.5 に日次 IC 2.9%（breadth 2 なら 4.1%）、20 日 IC 9.5%。prior は出典なしの判断で net 0.1〜0.4 | 不要（線形 baseline）。閾値相互作用は S16 で増分のみ | 対象 |
| S02 | 8〜18 RT/年/単位 gross | 常時 | 8 通貨（実効 4） | 非 US 10y の日次は中銀ソース。probe した FRED の非 US 10 年は OECD 月次系列（series id 末尾 M156N）で、FRED 上の非 US 日次系列は probe していない | 無料・認証不要（取得は承認後） | C09 | 曲線形状は一度も取得していない | net 0.5 に日次 IC 2.3%、60 日 IC 13.0%。prior は net 0.1〜0.3 | 不要 | 対象 |
| S03 | 事象あたり 1 往復、年 34.4 事象（取得可能な 4 中銀の実測） | 保有のある日 約 34%（通貨 slot の 5%） | 4 中銀（Fed・ECB・BoJ・RBA） | 会合カレンダーは Fed・ECB・BoJ・RBA を取得済み。BoE・BoC・SNB・RBNZ は #472 であらゆる自動取得を拒否し、手作業の再構成はしない規則。2 年金利は S01 と同じ（ECB・RBA は到達未確認） | 4 中銀のみ取得可能 | C01、H-019、H-018、H-016 | H-018/H-019 は event の movement のみで方向ソースを持たず、H-016 は決定そのもので市場 repricing ではない。C01 は未実行（horizon と dispersion window で不合格、economic は通過） | n=34.4・3 日保有で net 0.5 に事象あたり 12.0 bp（課金）/ 7.7 bp（pair）、集中 position の vol 7% なら 14.6 bp。事象数が少なく検出力が律速 | 不要 | 対象 |
| S04 | 事象あたり 1 往復、150〜300 事象/年 | 保有のある日 83〜100%（通貨 slot の 22〜74%） | 8 通貨（非 US の発表日カレンダーは未確認） | US 発表日は ALFRED を取得済み。非 USD 機関の無料・公式な時刻付き発表カレンダーは存在しない（C02）、日付だけのカレンダーの可否は未確認。2 年金利は S01 と同じ | US のみ取得済み、非 US は未確認 | H-020、C02、#477、H-019 | H-020 は US CPI の nowcast surprise で 1h〜1d・breadth 不足、C02 は時刻データの問題で blocked、#477 は検出力で skip。市場 repricing を surprise とする多日 drift は未検定。未 merge の #473 は survey consensus の USD 1h で検出力ある null | n=150〜300・2〜5 日保有で net 0.5 に事象あたり 8.3〜9.3 bp（課金）/ 4.1〜5.1 bp（pair）、集中 position の vol 7% なら 9.1〜10.5 bp | 不要 | 対象 |
| S05 | 43〜100 RT/年/単位 gross | 常時 | 実効 2（risk 軸 1 本） | VIX・Nikkei は FRED で無料、S&P 500 の履歴長は未確認。FX 側は株式終値と同時刻に揃える必要（seen span の M1 archive でのみ可能） | 無料・認証不要 | C10、H-016 | C10 は未実行。carry（H-016）は level で risk shock の lag ではない | breadth 2 のため必要 IC が約 1.4 倍に上がる。FX は 24h 連続取引で同時に織り込む prior が強い | 不要 | 対象 |
| S06 | 18〜43 RT/年/単位 gross | 常時 | 実効 1〜2 | 原油は無料、金属・乳製品の日次は有料寄り | 一部無料 | C11 | C11 は未実行 | breadth が狭く、net 0.5 に必要な IC が高い。単独での年 5% は困難 | 不要 | 対象 |
| S07 | 18〜43 RT/年/単位 gross | 常時（効くのは stress 期のみの可能性） | 実効 1〜2 | HY OAS は FRED にあるが range は probe で取れず、ICE の license で履歴が短縮されている可能性（未確認）。SOFR は 2018〜 | 公開・認証不要（履歴長は未確認） | C10 | 未実行 | stress 期に偏るため tail 集中が大きく、年間を通じた収益は小さい prior | 不要 | 対象 |
| S08 | S01 と同程度 | 常時 | S01 と同じ | S01 と同じ | 無料（MOVE は有料） | C12、H-002 | 単独の return source ではなく条件付けで、S01 の base が正でなければ意味を持たない | S01 の増分のみ | S16 と統合 | 対象 |
| S09 | 極めて高い | 断続 | 多い | M1 archive はあるが分解能が足りない | — | H-010 | bid/ask を整合させると乖離は spread の内側に収まる（無裁定条件） | spread 内の構造で、構造的に cost を超えない | — | 除外（構造的に cost を超えない） |
| S10 | 100 RT/年/単位 gross 超 | 常時 | bloc 数（3〜4） | M1 archive（seen span のみ） | 保有 | H-010、H-003、H-002 | aggregate の VR（H-010）は検定済みだが、bloc 間の cross lead-lag は未検定 | 半減期 1 日で net 0.5 に日次 IC 7%、intraday はさらに高い。FX の伝播は秒単位で裁定される prior | 不要 | 対象 |
| S11 | 18〜43 | 常時 | 実効 4 | 保有 | 保有 | H-024、C06、H-023 | —（通貨 reversal の事後観察 H-024 と同形で、名前を変えた復活になる） | — | — | 除外（閉鎖 family の改名・救済） |
| S12 | 18〜43 | 断続 | 低い | 保有 | 保有 | C07、H-003、H-024 | C07 は未実行だが、price 由来の収束は H-024 と隣接 | #480 の A12 は構造的に年 2% 未満と試算 | 不要 | 対象 |
| S13 | 約 5 RT/年/単位 gross | 常時 | 8 通貨（実効 4） | CPI は無料（公表 lag と改定がある）。検定には数十年の FX 履歴が要り、seen の 4.7 年では不能 | FX 長期履歴は保護 span を除外した範囲に限り、Red 承認の後に read（D-1） | H-016、H-012 | valuation は一度も検定していない。H-016 は carry、H-012 は momentum | net 0.5 に日次 IC 2.1%、120 日 IC 16.8%。学術 prior は G10 value 単独で net 0.2〜0.4、低 turnover の分散源 | 不要 | 対象 |
| S14 | 18〜43 | 常時 | 実効 4 | 保有 | 保有 | C13、H-009、H-023 | C13 は未実行だが、Track 1（5/20/60 日 + trend age の線形結合）が gross 負 | price 由来の多 horizon 情報は H-023 で線形に使って負 | 非線形の相互作用を仮説にしない限り不要 | 対象 |
| S15 | 18〜43 | 常時 | 実効 4 | 保有 | 保有 | C12、C14、H-002、H-022 | C12・C14 は未実行。H-022 の regime-gain は一定 gross の book では日ごとのスカラーが消えるため測定されておらず（反証ではない）、その run も gate 無効化で evidence ではない | 状態は return source ではなく条件付け。base が負なら救済にならない | HMM 等は未承認の複雑化になりやすい | 対象 |
| S16 | S01 よりやや高い | 常時 | S01 と同じ | S01 + FRED | 無料 | S01、C10 | S01 の線形 baseline が正でない限り検定しない（順序規律） | S01 の増分のみ | 閾値の非線形は S01 の後に増分検定として | 対象 |
| S17 | 事象あたり 1 往復 | 断続 | 8 通貨 | S03・S04・S05 の合成 | 無料 | S03、S04、C10 | S03・S04 の repricing 方向が効くかを先に見るべきで、cross-asset の追加はその増分 | S03・S04 の増分のみ | 不要 | 対象 |
| S18 | 高い | 常時 | 20 pair（実効は少ない） | 過去履歴が無料で揃わず、forward に蓄積するしかない | 認証または web scraping（未承認） | C20 | データが無い | —（データなし） | 不要 | データ不可 |
| S19 | 低い | 常時 | 7 通貨 | 保有 | 保有 | H-021、C21 | —（H-021 で tested cells が NOT_SUPPORTED、C21 は PRIOR_FAMILY_CLOSED） | — | — | 除外（閉鎖 family の改名・救済） |
| S20 | 中 | 常時 | 主要 pair | 無料の履歴なし（Bloomberg・CME 等の有料） | 有料 | なし | データが無い | —（データなし） | 不要 | データ不可 |
| S21 | 年 12 回 × 数 pair | 極めて低い | 低い | S&P・Nikkei は無料、他は限定的 | 一部無料 | C05、C04、#475 | —（C04・C05 は inventory で決定により停止・提案不可、#475 の London fix は検出力で SUSPENDED） | 事象が年 12 回しかなく、年 5% には構造的に届かない | 不要 | 除外（決定により停止中の family） |
| S22 | 高い | 1 日 1〜2 回 | 実効 2〜4 | intraday 先物は有料 | 有料 | C03、H-002、#475 | price のみの session 効果は H-002 で CLOSED、clock は #475 で SUSPENDED（C04 と同じく決定により停止中の clock family に隣接）。非 FX の intraday 情報は未取得 | 日 1〜2 回の決定で、半減期は数時間。cost 負けの prior が強い | 不要 | データ不可 |
| S23 | 低い | 常時 | 実効 4 | 取得済みの政策金利 + CPI | 保有・無料 | H-016、C22 | —（ここでの定義は取得済みの政策金利 + CPI で、H-016 の carry premium が short-yen に集中した NOT_SUPPORTED の組み替え。市場の実質利回りで作る版は S01・S13 の隣接として別に扱う） | — | — | 除外（閉鎖 family の改名・救済） |
| S24 | 低い | 常時 | 実効 4 | 保有 | 保有 | H-016、C22 | —（NOT_SUPPORTED の carry を vol filter で救済する形） | — | — | 除外（閉鎖 family の改名・救済） |
| S25 | 低い | 常時 | 主要 4〜5 中銀 | 無料だが月次で観測数が少ない | 無料 | なし | 未検定 | 観測数が少なく、seen の期間では検定不能。単独で年 5% の prior は低い | 不要 | 対象 |
| S26 | 約 5〜8 RT/年/単位 gross | 常時 | 実効 2〜3（US 視点の flow が中心） | TIC は公開・無料（本 task では probe していない）。公表 lag が長く、seen の期間では月次観測が約 56 | 公開・認証不要のはず（未確認） | H-021、C21 | COT（H-021・C21）は先物の投機 positioning で、現物証券の国際 flow は未取得・未検定 | 観測が月次で少なく、seen では検定不能。単独で年 5% の prior は低い | 不要 | 対象 |
| S27 | 事象あたり 1 往復〜 18 RT/年/単位 gross | 断続〜常時 | 取得できる中銀数に依存（テキストの時刻付き archive は未確認） | 公開テキストは各中銀 web にあるが、時刻付き・過去分の機械取得は未確認 | 公開（scraping の可否は未確認、承認前は取得しない） | C01、H-019 | 会合日の movement（H-019）と決定そのもの（C01）は扱ったが、テキストの tone は未取得・未検定 | 事象数は S03 と同程度で検出力が律速。S03 の repricing が tone を既に織り込むなら増分は小さい | tone の scoring に NLP が要る（方向予測を ML に任せるのではない）。辞書による単純 score を先に置く | 対象 |
| S28 | 18〜43 RT/年/単位 gross | 常時 | 実効 1〜2（非 US の breakeven が揃わない） | US は FRED（本 task では probe していない）、非 US は物価連動債市場が薄い | US は公開・無料のはず（未確認） | S01、H-016 | 政策金利の carry（H-016）とも名目 2 年（S01）とも別の成分だが、S01 と強く相関する | breadth が狭く、単独での年 5% は困難。S01 と情報が強く相関するので、独立な source として成立するかが最大の不確実性 | 不要 | 対象 |
<!-- /table -->

## R. Profit-capacity table

**測定**: 単位 gross あたり vol 2.329%（Track 1 primary book の実測 9.9943% ÷ 平均通貨 gross 4.2917）、cost 3.406 bp/turnover
unit（課金規約。この drag は Track 1 の gross − net 0.374 を再現する）、transfer coefficient 0.90（Track 1 の raw→neutralised 相関）。
**計算**: band 0.10・cap 0.25 の signal-free band law。**仮定**: 実効 breadth 4/日（測定ではない。inventory の断面 share 0.30 は
約 2/日に相当するので breadth 2 も併記）、event position の vol は分散 book から借用（集中 position の 7%/年も併記）、drawdown は
Gaussian i.i.d.（厚い裾を過小評価）。**source がこの品質を持つとは言っていない。必要な品質を示す。**

horizon IC は、半減期 h の AR(1) 予測が h 日先 return に対して示す相関（`日次 IC × Σρ^k / √h`）。一定 alpha を仮定した
`日次 IC × √h` は減衰する予測に過大な要求をする。

### R.1 continuous currency book

<!-- table:continuous_capacity -->
| 予測の半減期 | turnover / 年 / 単位 gross | alpha capture | cost による IR 低下 | net 0.3 / 0.5 / 0.8 に必要な gross IR | net 0.3 / 0.5 / 0.8 に必要な horizon IC（AR(1)、breadth 4） | net 0.5 に必要な日次 IC（breadth 4 / 2） |
| --- | --- | --- | --- | --- | --- | --- |
| 1d | 100.78 | 0.9513 | 1.474 | 1.774 / 1.974 / 2.274 | 6.5% / 7.3% / 8.4% | 7.3% / 10.3% |
| 5d | 43.36 | 0.9323 | 0.634 | 0.934 / 1.134 / 1.434 | 6.1% / 7.3% / 9.3% | 4.3% / 6.0% |
| 20d | 18.28 | 0.9264 | 0.267 | 0.567 / 0.767 / 1.067 | 7.0% / 9.5% / 13.2% | 2.9% / 4.1% |
| 60d | 8.39 | 0.9395 | 0.123 | 0.423 / 0.623 / 0.923 | 8.8% / 13.0% / 19.3% | 2.3% / 3.3% |
| 120d | 5.07 | 0.9498 | 0.074 | 0.374 / 0.574 / 0.874 | 10.9% / 16.8% / 25.5% | 2.1% / 3.0% |
<!-- /table -->

### R.2 年率・leverage・drawdown

再利用する執行層の leverage 上限は 5 倍。表の leverage は vol target ÷ 単位 gross vol の計算値で、10% vol で 4.29 倍（Track 1 の実測平均は 4.41 倍）、12% vol では 5.15 倍で上限を超える。Track 1 は 10% vol で
**46% の日に上限に張り付き**、上限なしの p95 は 8.0 倍だった。

<!-- table:return_capacity -->
| vol target | 必要 gross leverage（vol target ÷ 単位 gross vol。上限 5 との比較、日々は上限に張り付きうる） | net 0.3 / 0.5 / 0.8 の年率 | 10 年の最大 DD 中央値（net 0.3 / 0.5 / 0.8） | 10 年の最大 DD 95%点（net 0.3 / 0.5 / 0.8） | 年 5% に必要な net Sharpe | 年 10% に必要な net Sharpe |
| --- | --- | --- | --- | --- | --- | --- |
| 8% | 3.44（以内） | 2.4% / 4.0% / 6.4% | 21% / 18% / 15% | 42% / 34% / 26% | 0.625 | 1.25 |
| 10% | 4.29（以内） | 3.0% / 5.0% / 8.0% | 26% / 23% / 19% | 52% / 42% / 33% | 0.5 | 1.0 |
| 12% | 5.15（超過） | 3.6% / 6.0% / 9.6% | 32% / 27% / 23% | 63% / 51% / 39% | 0.417 | 0.833 |
<!-- /table -->

### R.3 検出に要る年数

<!-- table:detection_capacity -->
| net Sharpe | 片側 5% 検定の必要年数（検出力 50%） | 同（検出力 80%） | 最初の 5 年が負になる確率（Gaussian） |
| --- | --- | --- | --- |
| 0.3 | 30.07 | 68.7 | 25% |
| 0.5 | 10.82 | 24.73 | 13% |
| 0.8 | 4.23 | 9.66 | 4% |
<!-- /table -->

### R.4 event book（事象は独立と仮定、これは楽観側）

<!-- table:event_capacity -->
| 事象 / 年 | 保有日数 | net Sharpe | 事象あたり sd（bp） | 必要 edge（課金 cost、bp） | 必要 edge（pair cost、bp） | 必要 edge（集中 position vol 7%、課金、bp） | 平均同時保有 | 保有のある日 | 10% vol の片側 notional レバレッジ（基準 / 集中） |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 34.4 | 3 | 0.3 | 60.49 | 9.91 | 5.67 | 11.46 | 0.41 | 34% | 1.15 / 0.77 |
| 34.4 | 3 | 0.5 | 60.49 | 11.97 | 7.74 | 14.56 | 0.41 | 34% | 1.15 / 0.77 |
| 34.4 | 3 | 0.8 | 60.49 | 15.06 | 10.83 | 19.21 | 0.41 | 34% | 1.15 / 0.77 |
| 150 | 3 | 0.3 | 60.49 | 8.29 | 4.06 | 9.04 | 1.79 | 83% | 2.41 / 1.6 |
| 150 | 3 | 0.5 | 60.49 | 9.28 | 5.05 | 10.52 | 1.79 | 83% | 2.41 / 1.6 |
| 150 | 3 | 0.8 | 60.49 | 10.76 | 6.53 | 12.75 | 1.79 | 83% | 2.41 / 1.6 |
| 300 | 2 | 0.3 | 52.89 | 7.73 | 3.5 | 8.19 | 2.38 | 91% | 2.6 / 1.73 |
| 300 | 2 | 0.5 | 52.89 | 8.34 | 4.11 | 9.11 | 2.38 | 91% | 2.6 / 1.73 |
| 300 | 2 | 0.8 | 52.89 | 9.26 | 5.02 | 10.48 | 2.38 | 91% | 2.6 / 1.73 |
| 300 | 5 | 0.3 | 73.35 | 8.08 | 3.85 | 8.72 | 5.95 | 100% | 4.69 / 3.12 |
| 300 | 5 | 0.5 | 73.35 | 8.93 | 4.7 | 9.99 | 5.95 | 100% | 4.69 / 3.12 |
| 300 | 5 | 0.8 | 73.35 | 10.2 | 5.97 | 11.9 | 5.95 | 100% | 4.69 / 3.12 |
<!-- /table -->

### R.5 読み方

- **edge per unit turnover × turnover × exposure**: 速い予測（半減期 1〜5 日）は turnover が 43〜101 RT/年/単位 gross で、
  cost だけで IR が 0.6〜1.5 削られる。遅い予測（60〜120 日）は cost が軽い（0.07〜0.12）。**turnover を減らせば解決、でも、
  高頻度は不可能、でもない。** net 0.5 に必要な日次 IC は半減期 20〜120 日で 2.1〜2.9%（breadth 2 なら 3.0〜4.1%）。
- **年 5〜10% の capacity**: 10% vol で年 5% に net 0.5、年 10% に net 1.0。12% vol なら net 0.42 / 0.83（ただし leverage 5.15 倍で
  上限 5 倍を超える）。net 0.5・10% vol でも 10 年の最大 DD 中央値は 23%、95%点は 42%。
- **検出の限界**: net 0.5 を片側 5% で検出力 80% で見るには約 24.7 年（検出力 50% でも 10.8 年）、net 0.8 でも 9.7 年の
  out-of-sample が要る。seen の 4.7 年（walk-forward の out-of-fold は約 2.9 年）では net 0.5 の source を決められない。
  **新しい独立履歴が研究可能性そのものを左右する。**

## S. Prior-overlap / falsification map

<!-- table:overlap_map -->
| ID | 重なる既存研究（分類） | 扱い |
| --- | --- | --- |
| S01 | H-016（NOT_SUPPORTED）、C09（NOT_DECISION_GRADE）、H-023（NOT_SUPPORTED） | 対象 |
| S02 | C09（NOT_DECISION_GRADE） | 対象 |
| S03 | C01（NOT_DECISION_GRADE）、H-019（OPEN）、H-018（OPEN）、H-016（NOT_SUPPORTED） | 対象 |
| S04 | H-020（NOT_SUPPORTED）、C02（SUSPENDED）、#477（SUSPENDED）、H-019（OPEN） | 対象 |
| S05 | C10（NOT_DECISION_GRADE）、H-016（NOT_SUPPORTED） | 対象 |
| S06 | C11（NOT_DECISION_GRADE） | 対象 |
| S07 | C10（NOT_DECISION_GRADE） | 対象 |
| S08 | C12（NOT_DECISION_GRADE）、H-002（CLOSED） | 対象 |
| S09 | H-010（CLOSED） | 除外（構造的に cost を超えない） |
| S10 | H-010（CLOSED）、H-003（CLOSED）、H-002（CLOSED） | 対象 |
| S11 | H-024（CLOSED）、C06（NOT_DECISION_GRADE）、H-023（NOT_SUPPORTED） | 除外（閉鎖 family の改名・救済） |
| S12 | C07（NOT_DECISION_GRADE）、H-003（CLOSED）、H-024（CLOSED） | 対象 |
| S13 | H-016（NOT_SUPPORTED）、H-012（NOT_SUPPORTED） | 対象 |
| S14 | C13（NOT_DECISION_GRADE）、H-009（CLOSED）、H-023（NOT_SUPPORTED） | 対象 |
| S15 | C12（NOT_DECISION_GRADE）、C14（NOT_DECISION_GRADE）、H-002（CLOSED）、H-022（NOT_DECISION_GRADE） | 対象 |
| S16 | S01（候補）、C10（NOT_DECISION_GRADE） | 対象 |
| S17 | S03（候補）、S04（候補）、C10（NOT_DECISION_GRADE） | 対象 |
| S18 | C20（SUSPENDED） | データ不可 |
| S19 | H-021（NOT_SUPPORTED）、C21（CLOSED） | 除外（閉鎖 family の改名・救済） |
| S20 | なし（UNTESTED） | データ不可 |
| S21 | C05（SUSPENDED）、C04（SUSPENDED）、#475（NOT_SUPPORTED・SUSPENDED） | 除外（決定により停止中の family） |
| S22 | C03（NOT_DECISION_GRADE）、H-002（CLOSED）、#475（NOT_SUPPORTED・SUSPENDED） | データ不可 |
| S23 | H-016（NOT_SUPPORTED）、C22（CLOSED） | 除外（閉鎖 family の改名・救済） |
| S24 | H-016（NOT_SUPPORTED）、C22（CLOSED） | 除外（閉鎖 family の改名・救済） |
| S25 | なし（UNTESTED） | 対象 |
| S26 | H-021（NOT_SUPPORTED）、C21（CLOSED） | 対象 |
| S27 | C01（NOT_DECISION_GRADE）、H-019（OPEN） | 対象 |
| S28 | S01（候補）、H-016（NOT_SUPPORTED） | 対象 |
<!-- /table -->

## T. Candidate ranking

重み（採点前に宣言）: 利得は P(real edge)×2・経済規模・資本稼働・breadth・頑健性・情報利得×2、負担は turnover cost・
複雑さ・過学習リスク・データ負担・実装負担を各 1 で差し引く。**判断であって測定ではない**（backtest は一切していない）。
除外・データ不可・停止中 family の候補は順位を付けずに下に並べる。同点は ID 順（S02 と S03 は 11 点で同点）。

<!-- table:ranking -->
| 順位 | ID | 候補 | score | P(real) | 規模 | 稼働 | breadth | 頑健 | 情報利得 | turnover | 複雑 | 過学習 | data | 実装 | 扱い |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | S01 | front-end 金利差 repricing → 通貨相対リターン | 19 | 3 | 3 | 5 | 4 | 3 | 5 | 2 | 2 | 2 | 4 | 2 | 対象 |
| 2 | S13 | 実質為替レート valuation（PPP・実質金利 anchor） | 18 | 3 | 2 | 5 | 4 | 3 | 4 | 1 | 1 | 2 | 4 | 2 | 対象 |
| 3 | S02 | 曲線 slope / curvature 差の変化 | 11 | 2 | 2 | 5 | 4 | 2 | 3 | 1 | 2 | 3 | 4 | 2 | 対象 |
| 4 | S03 | 中銀会合日の市場 repricing → 会合後 drift | 11 | 3 | 1 | 2 | 2 | 3 | 4 | 2 | 2 | 2 | 3 | 2 | 対象 |
| 5 | S05 | 株式・volatility shock → funding 通貨 vs 資源国通貨（時刻整合した lag） | 9 | 2 | 2 | 5 | 2 | 2 | 3 | 3 | 2 | 3 | 2 | 2 | 対象 |
| 6 | S04 | 主要指標発表日の市場 repricing → 発表後 drift | 8 | 2 | 3 | 3 | 4 | 2 | 4 | 3 | 3 | 3 | 4 | 3 | 対象 |
| 7 | S25 | 中銀 balance sheet・準備資産 flow | 7 | 2 | 1 | 5 | 2 | 2 | 2 | 1 | 2 | 3 | 3 | 2 | 対象 |
| 8 | S26 | 国際資本 flow（US TIC・国際収支）の相対変化 | 7 | 2 | 1 | 5 | 2 | 2 | 2 | 1 | 2 | 3 | 3 | 2 | 対象 |
| 9 | S16 | 金利 repricing × volatility の閾値効果 | 5 | 2 | 2 | 5 | 4 | 2 | 2 | 2 | 4 | 4 | 3 | 3 | 対象 |
| 10 | S06 | 商品価格 → 資源国通貨（terms of trade lead） | 4 | 2 | 1 | 4 | 1 | 2 | 2 | 2 | 2 | 3 | 3 | 2 | 対象 |
| 11 | S14 | fast / medium / slow の price state 不一致 | 4 | 1 | 2 | 5 | 4 | 1 | 1 | 2 | 3 | 5 | 1 | 1 | 対象 |
| 12 | S28 | 市場のインフレ期待（breakeven）の repricing | 4 | 2 | 1 | 5 | 1 | 2 | 2 | 2 | 2 | 3 | 4 | 2 | 対象 |
| 13 | S07 | 信用 spread・funding stress → USD・JPY・CHF | 3 | 2 | 1 | 2 | 1 | 2 | 2 | 2 | 2 | 3 | 2 | 2 | 対象 |
| 14 | S27 | 中銀 communication の tone 変化（声明・議事要旨・講演） | 2 | 2 | 2 | 3 | 3 | 2 | 3 | 2 | 4 | 4 | 4 | 4 | 対象 |
| 15 | S17 | event 日の cross-asset 共動を方向ソースにする | 0 | 2 | 2 | 2 | 3 | 2 | 2 | 3 | 4 | 4 | 3 | 3 | 対象 |
| 16 | S10 | 通貨 complex 間の lead-lag 伝播（例: EUR→CHF、AUD→NZD） | -1 | 1 | 2 | 4 | 2 | 1 | 2 | 5 | 3 | 4 | 1 | 3 | 対象 |
| 17 | S15 | volatility / trend の状態遷移（latent regime） | -1 | 1 | 1 | 4 | 3 | 1 | 1 | 2 | 4 | 5 | 1 | 2 | 対象 |
| 18 | S08 | 金利 volatility 状態 × FX | -2 | 1 | 1 | 3 | 3 | 1 | 1 | 2 | 3 | 4 | 3 | 2 | 対象 |
| 19 | S12 | 相関 breakdown / dispersion 状態の relative value | -3 | 1 | 1 | 2 | 2 | 1 | 1 | 3 | 3 | 4 | 1 | 2 | 対象 |
| — | S20 | FX option の risk reversal / implied vol skew | 8 | 3 | 2 | 4 | 3 | 2 | 3 | 2 | 2 | 3 | 5 | 3 | データ不可 |
| — | S23 | ex-ante 実質金利差の level | 7 | 1 | 2 | 5 | 4 | 1 | 1 | 1 | 2 | 3 | 2 | 1 | 除外（閉鎖 family の改名・救済） |
| — | S24 | volatility で timing した carry（crash risk 回避） | 6 | 1 | 2 | 4 | 4 | 1 | 1 | 1 | 2 | 4 | 1 | 1 | 除外（閉鎖 family の改名・救済） |
| — | S11 | 動的共通 factor residual の reversal | 5 | 1 | 2 | 5 | 4 | 1 | 1 | 2 | 2 | 5 | 1 | 1 | 除外（閉鎖 family の改名・救済） |
| — | S19 | COT の変化 × price の相互作用 | 4 | 1 | 1 | 4 | 3 | 1 | 1 | 1 | 2 | 4 | 1 | 1 | 除外（閉鎖 family の改名・救済） |
| — | S18 | retail positioning の逆張り | 3 | 2 | 2 | 4 | 3 | 2 | 3 | 4 | 2 | 3 | 5 | 4 | データ不可 |
| — | S21 | 月末の株式相対リターンに条件付けた hedge rebalance flow | 2 | 3 | 1 | 1 | 1 | 2 | 2 | 2 | 2 | 3 | 3 | 3 | 除外（決定により停止中の family） |
| — | S22 | session 間の cross-market 情報伝達（Asia→London、London→NY） | -7 | 1 | 2 | 2 | 2 | 1 | 2 | 4 | 3 | 4 | 5 | 4 | データ不可 |
| — | S09 | 三角 residual（cross と合成 cross の乖離） | -8 | 1 | 1 | 2 | 3 | 1 | 1 | 5 | 3 | 3 | 4 | 4 | 除外（構造的に cost を超えない） |
<!-- /table -->

## U. Blind-spot review

- **「price 由来だから全部無理」と一般化していないか**: していない。閉じたのは検定した price family（H-001・H-003・H-004・
  H-006・H-009・H-023 等）で、未検定の price 構造（S10 の bloc 間 lead-lag）は低順位だが残している。順位が低いのは
  price 由来だからではなく、裁定速度と turnover の算術のため。逆に、**非 price と称する S01・S03 が price momentum /
  continuation を偽装しうる**点は control で扱う（H・N 節）。
- **「ML が全部無理」**: していない。S16 を非線形の増分候補、S27 をテキスト scoring が要る候補として残した。ML を仮説に
  しないだけで、排除していない。
- **「cross-sectional が全部無理」**: していない。S01・S13 は cross-sectional な通貨 book。H-003 と Track 1 の失敗は
  情報源（price）の問題として扱った。
- **「multi-timeframe が全部無理」**: 単純 sign conditioning（H-009）と Track 1 の線形多 horizon は負。非 price 情報の
  horizon 構造（S01 の 5〜20 日、S13 の月単位）は別物として評価した。
- **「event 方向が全部無理」**: していない。H-020 は US CPI の nowcast surprise 1 種、#473 は survey consensus の USD 1h で、
  市場 repricing を方向ソースにする多日 drift（S03・S04）は未検定。
- **過去の検出力不足を反証と読んでいないか**: C01・C09・C10・C11 は未実行で反証ではない。ただし **horizon だけで落ちたのは
  C01 だけ**で、C09・C10・C11 は economic_net_under_stress と dispersion window でも不合格、追加履歴でも pass region は開かないと
  inventory が記録している（H 節で S01 について扱った）。H-005・H-007・H-012 は検出力不足の null として記録されている。
- **停止中の family を候補にしていないか**: C04・C05 は決定により停止・提案不可で、それに属する S21 は除外した。
- **見落とし候補**: 有料データ（S20 の option、OIS 履歴、intraday 先物）は prior が比較的強いが、データ購入は Human 判断。

## V. Adversarial review（上位候補）

### S01（front-end 金利差 repricing）

- **焼き直しではないか**: H-016 の carry change と同じでは？ → H-016 は中銀の**決定**（月に一度変わる階段関数）で、
  S01 は毎日動く**市場の期待**。ただし両者の情報は相関する。carry level の premium が short-yen に集中した H-016 の教訓から、
  S01 も **JPY 依存と breadth** を最初に確認する必要がある。
- **price momentum の偽装ではないか**: 利回り差と FX の同日共動が強いほど、lag 付き利回り変化は lag 付き FX return に近づく。
  同じ lookback の FX momentum を control にし、それを超えなければ S01 ではなく閉じた momentum family を再発見しただけになる。
- **本当に expected-return source か**: 同時相関は強くても、先行性は効率的市場なら小さい。先行性が無ければ
  S01 は「同時に動く」だけで収益にならない。これが最大の反証リスク。
- **architecture で負の edge を隠していないか**: Track 1 と同じ執行層を使うので、gross が負なら band・vol target では救えない
  （C 節）。判定は gross と benchmark で行う。
- **capacity は十分か**: 成立すれば常時稼働で年 5% の射程だが、net 0.5 に日次 IC 2.9%（breadth 2 なら 4.1%）が要る。
  prior（net 0.1〜0.4）は出典のない判断で、その中央では年 5% に届かない。
- **データで研究可能か**: 非 US の日次 2 年金利は 7 中 3 しか到達を確認できていない。seen 4.7 年では net 0.5 を決められない。
- **inventory との整合**: C09 は economic でも不合格で、追加履歴でも pass region は開かない。本 PR の「コスト仮定の違い」という
  反論は未検証で、Gate v2 は T-R にも horizon で確実に RED を出す（W 節で扱い）。

### S13（実質為替レート valuation）

- **焼き直しではないか**: carry・momentum とは別の style で、ledger に重なりは無い。
- **本当に source か**: 学術的には長期で観測されるが、G10 value の Sharpe は低く、数年単位で負け続ける期間がある。
- **capacity**: 単独で年 5% は楽観的。分散源としての価値が中心。
- **データで研究可能か**: seen では不能。保護 span を除外した長期公開 FX 履歴の read 承認が前提で、承認されなければ研究できない。
  CPI の公表 lag・四半期の通貨・ex-ante anchor・warm-up の範囲が leakage の要点（K 節）。

### S03 / S04（event × 市場 repricing）

- **焼き直しではないか**: H-019 の event movement に方向を足しただけでは？ → 方向ソース（市場 repricing）が新しく、
  それが無い限り H-019 は方向を持たない。ただし **event filter 救済** にならないよう、baseline は「全日の repricing」
  （S01 の日次版）と比べて event 日に上乗せがあるかで判定し、事象母集団は T-R の結果を読む前に凍結する。
- **price continuation の偽装ではないか**: repricing の符号は event 日の FX return と重なる。event 日の FX return を control にする。
- **本当に source か**: FX の repricing への反応が当日中に完了するなら drift は無い。#473 の USD 1h の null はその方向の警告。
- **capacity**: S03 は取得可能な 4 中銀で年 34.4 事象、net 0.5 に事象あたり 12.0 bp（集中 position なら 14.6 bp）が要り、
  検出力が律速。S04 を足すと事象数は増えるが、非 US のカレンダーが未確認で、個々の edge は薄くなる可能性。
- **データで研究可能か**: 残り 4 中銀のカレンダーは取得不可と記録済み。非 US の指標発表日カレンダーは未確認。

## W. 次に研究する価値が最も高い track（最大 3）

共通の前提（track ではなく **Human + ChatGPT の判断事項**）:

- **D-1. 新しい独立履歴**: 保護 span（fresh pool `2016-06-02 … 2021-04-25`、historical OOS、dead window、forward epoch）を
  **除外した**、`2016-06-02` より前の公開日次 FX 履歴の read。seen 4.7 年では net 0.5 を決められない（R.5）。T-V はこれが
  無ければ実行不能、T-R・T-E も検出力が大きく変わる。Red（実データ read）なので、操作・span・系列・承認 head を名指しした承認が要る。
  **除外の強制方法も承認対象**: hashing も read なので「全体を download してから filter」は保護 span の byte を読むことになり不可。
  取得要求そのものを終端 `< 2016-06-02` に制限する（server 側の期間指定）、それができない系列は使わない、取得前後に日付範囲を
  検査する guard を置く、を条件とする。保有カレンダーは 2021〜2026 のみなので、pre-2016 の event 研究には新たな取得が要る。
- **D-2. 非 FX の公開データ取得**: 日次 2 年金利（到達確認は BoE・BoC・MOF の 3、他の 5 は本環境で未確認）、指標発表日カレンダー
  （非 US は未確認）、CPI。無料・認証不要のはずだが、取得可能性の確認自体が最初の作業になる。BoE・BoC・SNB・RBNZ の会合
  カレンダーは取得不可と記録済みで、D-2 に含めない。

全 track に共通の規則:

- **2 段の判定（対称）**: seen data だけの結果は **development screen** であり、どちらの方向にも decision-grade にならない
  （seen の out-of-fold 約 2.9 年では net 0.5 を 0 と区別できない、R.3）。screen は同じ点推定規則で **advance**（独立履歴の検定へ
  進む価値がある）か **stop**（この track を止め、`…_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` として Track 1 と同じ形で記録する）の
  どちらかを必ず返し、success も family 閉鎖も主張しない。**T-R・T-E を seen data だけで実行した場合、出せる結論はこの screen まで**。
- **decision-grade の判定（独立履歴）**: 片側 5% で net の下側信頼限界 > 0 なら source として支持。**family を閉じるのは、net の
  上側信頼限界が年 5% 目標の net 0.5 を下回るとき**（真の値が 0 なら約 10.8 年で到達可能で、D-1 の数十年なら届く）。
  必要年数は結果を見る前に計算し、手元の履歴で閉鎖に届かないならそれを事前に記録する。
- **Feasibility Gate v2**: seen だけでは horizon 条件で確実に RED（C09 と同じ）。ruling どおり development では hard gate にしないが、
  RED のまま得た結果は decision-grade にならず、decision-grade には D-1 等の独立履歴が要る。
- **regime 集中**: seen の 2021〜2025 は世界的な利上げ局面で金利が FX を支配した期間、pre-2016 は JPY・CHF・EUR が
  ゼロ金利に近い期間。片方の regime だけで成立・不成立する結果は一般化しない。

### T-R — 市場利回り repricing → 通貨相対リターン（S01）

| 項目 | 内容 |
| --- | --- |
| economic mechanism | 市場が織り込む政策パス（2 年金利差）の相対変化に FX が数日〜数週遅れて追随する |
| なぜ本当に新しいか | 市場利回りは未取得・未検定。H-016 は政策金利（決定）。C09 は未実行だが economic でも不合格と記録されており、その扱いを最初に示す |
| exact target | 通貨の 5 日先・20 日先 excess return（2 本を事前に固定、sweep しない） |
| data | 日次 2 年金利（D-2、揃う通貨数は未確認）、FX は seen corpus（+ D-1 が承認されれば pre-2016 履歴） |
| horizon | 5〜20 日 |
| portfolio architecture | Track 1 の執行層（factor-neutral・cap・band 0.10・vol target）を再利用。alpha model は新規 |
| expected turnover | 18〜43 RT/年/単位 gross |
| plausible return capacity | prior は出典のない判断で net 0.1〜0.4、10% vol で年 1〜4%。年 5% は prior の上端を超える |
| baseline / control | **主検定は unfitted な 2 年金利差変化 rule（符号固定、1 本）**。control: 同じ lookback の FX momentum（閉じた family）、B0 cash、Track 1 の price model（負の比較対象） |
| minimum experiment | (1) データ取得と時刻整合の監査（非同期終値を 1 日 lag で処理、揃う通貨数の確定）(2) 検出力と Gate v2・capacity を結果前に計算 (3) unfitted rule、次に線形 1 model（特徴 3 以下）・walk-forward・purge/embargo |
| development screen（seen、対称） | **advance**: unfitted rule の gross > 0 かつ net Sharpe ≥ 0.3、FX momentum control を超える増分が正、JPY 除外でも符号維持、正の fold が過半。**stop**: gross ≤ 0、または control を超える増分が 0 以下、または JPY 除外で符号反転。どちらも点推定で判定し、decision-grade ではない |
| decision-grade 判定（独立履歴、D-1） | 支持: FX momentum control を超える増分の net 下側信頼限界 > 0。不支持: 上側信頼限界 < net 0.5。**fitted model が unfitted rule に劣後するのは model の kill であって source の kill ではない** |
| broad family を閉じる結果 | 独立履歴（約 10.8 年以上）で 5〜20 日の先行性の net 上側信頼限界が 0.5 を下回れば「front-end 金利 repricing が G10 FX を先行する」family を閉じる |
| ML は必要か | 不要。S16 の閾値相互作用は gross 正の後の増分検定としてのみ |

### T-E — event 日の市場 repricing → 事後 drift（S03 主、S04 は発表日カレンダーが揃う場合のみ）

| 項目 | 内容 |
| --- | --- |
| economic mechanism | 中銀会合・主要指標の当日に市場が repricing した方向へ、FX が数日かけて追随する（under-reaction） |
| なぜ本当に新しいか | 過去の event 研究は movement のみ（H-018/H-019）か、consensus / nowcast の surprise（H-020、#473）。市場 repricing を方向ソースにする多日 drift は未検定 |
| exact target | 会合・発表通貨の 1 日先・3 日先 excess return（2 本を事前固定） |
| data | 会合カレンダー（取得可能な Fed・ECB・BoJ・RBA の 4 中銀、年 34.4 回）、指標発表日（US は ALFRED、非 US は未確認）、当日の 2 年金利変化（D-2） |
| horizon | 1〜3 日 |
| portfolio architecture | event book（idle 時は保有なし）を Track 1 の差分課金執行層で |
| expected turnover | 事象あたり 1 往復、S03 で年 34.4、S04 込みで 150〜300（カレンダー次第） |
| plausible return capacity | S03 単独は事象あたり 12.0 bp（課金、集中 position なら 14.6 bp）が要り年 5% に届きにくい。S04 込みで 8.3〜10.5 bp |
| baseline / control | 全日の repricing rule（S01 の日次版）、event 日の無条件 book、**event 日の FX return そのもの（price continuation の control）**、B0 |
| leakage 規則（結果前に凍結） | 取引開始は event の終了と利回り終値の遅い方より後。保有カレンダーは日付単位なので時刻は保守側（翌営業日）に置く。臨時会合は母集団から除く規則だが、保有データに臨時会合の flag は無く（#472 §3.1、BIS の政策金利変更との包含 check が代替で、必要条件であって十分条件ではない）、除外は不完全と事前に記録する。S04 の「主要指標」は機械的規則で選び、実現した市場インパクトで選ばない |
| minimum experiment | (1) 事象母集団と規則を **T-R の結果を読む前に凍結**（会合は取得可能な 4 中銀、指標は機械的規則）(2) 検出力計算（事象数×必要 edge）を結果前に (3) repricing 符号の単一 rule |
| development screen（seen、対称） | **advance**: event 日の repricing rule が全日の repricing rule と event 日 FX return control を上回り、net Sharpe ≥ 0.3、leave-one-bank-out で符号維持。**stop**: event 日の上乗せが 0 以下、または control を超える増分が 0 以下、または leave-one-bank-out で符号が崩れる。中銀ごとの符号不一致は 1 中銀あたり年約 8 事象ではノイズで起きるので stop にしない |
| decision-grade 判定（独立履歴） | 支持: event 日の上乗せの net 下側信頼限界 > 0。不支持: 上側信頼限界 < net 0.5。pre-2016 の会合カレンダーは新たな取得が要る |
| broad family を閉じる結果 | 独立履歴で drift の net 上側信頼限界が 0.5 を下回れば「G10 FX は event 時の市場 repricing に当日中に反応を完了する」として event-direction family を閉じる |
| ML は必要か | 不要 |

### T-V — 実質為替レート valuation（S13）— **D-1 が承認された場合のみ**

| 項目 | 内容 |
| --- | --- |
| economic mechanism | 実質為替レートの長期均衡からの乖離が数か月〜数年で戻る（currency value premium） |
| なぜ本当に新しいか | valuation は未検定。carry（H-016）・momentum（H-012）とは別 style |
| exact target | 通貨の 3 か月先 excess return（1 本） |
| data | CPI（無料、AUD・NZD は四半期）、保護 span を除外した長期公開 FX 履歴（D-1） |
| horizon | 3〜12 か月 |
| portfolio architecture | Track 1 の執行層、月次 rebalance |
| expected turnover | 約 5 RT/年/単位 gross |
| plausible return capacity | 単独 net 0.2〜0.4 の学術 prior、10% vol で年 2〜4%。分散源 |
| baseline | 等加重 cash、PPP 乖離の単純 rank rule（1 本） |
| leakage 規則（結果前に凍結） | CPI は公表日で揃える（初値を使い改定を使わない）。PPP anchor は拡張窓または固定基準で、全期間平均を使わない。warm-up は seen または pre-2016 に閉じ、fresh pool の FX 水準を使わない |
| minimum experiment | (1) D-1 の履歴の品質監査（fix 時刻、bid/ask の欠如、cost の上乗せ）(2) 長期 walk-forward の検出力計算 (3) 単一 rule |
| decision-grade 判定（独立履歴のみ） | 支持: 複数 decade で net の下側信頼限界 > 0、decade 間で符号が安定 |
| 不支持 | net の上側信頼限界 < 0.5、または 1 通貨・1 decade 依存 |
| broad family を閉じる結果 | 数十年で net の上側信頼限界が 0.5 を下回れば G10 valuation family を閉じる |
| ML は必要か | 不要 |

**3 つを無理に選んだのではない**: T-R は最上位。T-V は第 2 位だが D-1 の承認に完全に依存する。T-E は S03 が 11 点で S02 と
同点の 3〜4 位、S04 が 6 位で、event の強い movement 構造に初めて方向ソースを与える唯一の候補だが、取得可能な中銀が 4 に
限られ検出力は弱い。S02 を別 track にしないのは、T-R と同じ金利データを使う第 2 の金利仮説で prior が弱く、T-R の data 取得後に
安価に追加できるから（Human が T-E と入れ替える判断はありうる）。D-1 が否決されれば T-V は外れ、提案は 2 track になる。

## X. 最小実験（実行はしない）

| track | 最初の実験 | 結果を見る前に固定するもの | 読むデータ | 承認 |
| --- | --- | --- | --- | --- |
| T-R | データ取得・時刻整合監査 → 検出力・signal-blind gate → unfitted rule → 線形 1 model | target 2 本、特徴 3 以下、lag 規則、FX momentum control、benchmark、screen 規則、判定に要る年数 | 非 FX 公開データ（D-2）、seen FX | D-2 の取得、実行は Red |
| T-E | 事象母集団と規則の凍結（T-R の結果前）→ 検出力計算 → 単一 rule | 事象規則、取引開始時刻の規則、臨時会合の除外、target 2 本、baseline・control、screen 規則、判定に要る年数 | 同上 | 同上 |
| T-V | D-1 履歴の品質監査 → 長期検出力 → 単一 rule | 系列、span（保護 span 除外と強制方法）、CPI 公表日、anchor の作り方、warm-up 範囲、target、判定規則 | D-1 | D-1（Red） |

いずれも探索自由度（特徴数、target 本数、model 数、horizon）を事前に宣言し、feature zoo・hyperparameter zoo・timeframe zoo・
seed mining・通貨 subset mining はしない。development では α=0.05 の証明を hard gate にせず、限定 search budget・時間方向の
walk-forward・benchmark 比較・経済 stress・安定性・複雑さ penalty・leakage control で判断する。seen だけの結果は advance / stop の
development screen に留め、支持・family 閉鎖は独立履歴の信頼限界で行う（W 節）。

## Y. 最終推奨

**問い 1: Track 1 が gross 負だった事実を受け入れた上で、次にどの expected-return source を研究するのが最も合理的か。**

→ **市場利回りの repricing（T-R）**。price 以外で常時稼働し、未検定で、Track 1 の執行層をそのまま使える。ただし prior は
中程度で、lag 付き利回りが price momentum を偽装する危険（control 必須）、非 US 利回りの取得可能性（7 中 3 しか確認できていない）、
inventory が C09 を economic でも不合格と記録している点を抱えている。次点は **実質為替レート valuation（T-V）** で、D-1 次第。
**event × 市場 repricing（T-E）** は方向ソースとして新しいが、取得可能な中銀が 4 で検出力が弱い。

**問い 2: 成立した場合、年 5〜10% の net return に届く経済 capacity はあるか。**

→ **算術上の capacity はあるが、どの source にもそこに届く証拠は無い。** 10% vol で年 5% に net 0.5、年 10% に net 1.0 が要る
（12% vol なら 0.42 / 0.83 だが、必要 leverage 5.15 倍は再利用する執行層の上限 5 倍を超え、Track 1 は 10% vol ですでに 46% の日に上限に張り付いた）。
T-R の prior（出典のない判断で net 0.1〜0.4）の中央（約 0.25）では単独で 10% vol の年 2.5% 程度で、年 5% は上端を超える。
T-R を 0.1〜0.4、T-V を学術 prior の 0.2〜0.4、T-E を 0.1〜0.4 と置き、3 つが独立に成立すれば合成 net は √ΣS² で 0.24〜0.69
（10% vol で年 2.4〜6.9%）。**年 10%（10% vol で net 1.0）には、
独立 source が 3 つならそれぞれ net 約 0.58、net 0.4 の source なら約 6 つの成立が要る**。net 0.5・10% vol でも 10 年の最大 DD 中央値は約 23%、95%点は約 42%
（Gaussian、厚い裾は含まない）。

**問い 3: 次に何を実験すべきか（最大 3）。**

1. **T-R の最小実験**（データ取得・時刻整合監査 → 検出力と signal-blind gate → unfitted rule → 線形 1 model）
2. **T-V の最小実験**（D-1 が承認された場合のみ）
3. **T-E の最小実験**（事象母集団の凍結を T-R の結果前に行う → 検出力計算 → 単一 rule）

**Human + ChatGPT の判断事項**: どの track を選ぶか（S02 と T-E の入れ替えを含む）、D-1（保護 span を除外した pre-2016 公開 FX
履歴の read と、その除外の強制方法）、D-2（非 FX 公開データの取得）、有料データ（option・OIS・intraday 先物）を検討するか、#473 の扱い。

**研究を止める提案ではない。** top 候補の prior は中程度で、年 10% の単独 source は見当たらず、seen data だけでは net 0.5 を決め
られないが、未検定の情報源は残っている。continuation / stop は Human 判断。

保護データ: fresh pool `2016-06-02 … 2021-04-25`、historical OOS、dead window、forward Formal Confirmation epoch は、本 task の
candidate 生成・schema 確認を含め一切読んでいない。
