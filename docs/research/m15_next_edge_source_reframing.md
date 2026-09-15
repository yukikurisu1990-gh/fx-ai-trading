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
- その pause を記録していた PR #483 は **merge しない**。有効な研究結果（Track 1 の Case C、H-023、5/20/60 日に限定した
  H-024、tail diagnostic と similar-rule kill の方法論上の所見、保護データの状態）は本 PR に移し、#483 は pause
  governance とともに閉じる。
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
| 保有 | BIS 政策金利（EUR は deposit facility 補正）、中銀会合カレンダー（Fed・ECB・BoJ・RBA）、ALFRED vintage、Cleveland Fed nowcast、CFTC COT、tick volume | 研究利用可 |
| 保有（未 merge） | survey consensus（#473 の branch） | #473 未 merge |
| 無料・未取得（metadata 確認） | US 2 年金利 FRED 日次 `1976-06-01〜`、VIX `1990-01-02〜`、Nikkei 225 `1949-05-16〜`、Brent `1987-05-20〜`、SOFR `2018-04-03〜`。非 US 10 年は FRED では月次（OECD）のみ | 取得は承認後 |
| 無料・未取得（到達性のみ確認） | 非 US の日次 2 年金利: BoE・BoC Valet・日本 MOF は到達、ECB・Bundesbank・SNB は本環境で証明書エラー（未確認）、RBA・RBNZ は script に 403（未確認） | 取得は承認後 |
| 無料・長期 FX 履歴（**確認していない**） | Fed H.10・ECB 参照レート等の公開日次 FX。FX 系列のページは保護 span・forward epoch の値を含むため、metadata 確認も含め一切取得していない | read には保護 span を除外した Red 承認が要る |
| 有料 | FX option（risk reversal）、intraday 株価指数先物、CME FX 先物 intraday、OIS / 金利先物の履歴 | 未取得 |
| 認証要（未承認） | OANDA positionBook、IG client sentiment | 禁止 |

metadata 確認の記録: `artifacts/research/edge_sources/public_data_availability.json`（非 FX のみ、値は分析していない）。

## F. 既存の engineering asset（再利用）

- **Track 1 の執行層**: 通貨レベル表現、factor neutralization、target weight、pair routing、部分 rebalance、no-trade band、
  turnover 会計、vol scaling。新しい source の評価共通基盤として再利用する。**Track 1 の alpha model は再利用しない。**
- cost framework（pair 往復 2.58 bp、課金 3.406 bp/turnover unit、faithful cost）、unit-safe 換算、Feasibility Gate v2、
  signal-blind な capacity / search budget、walk-forward・purge・embargo、leakage guard、事前登録の凍結・実行束縛、
  変異テスト、hypothesis ledger、event calendar、public macro data。

## G. Expected-return source map（既存研究の分類）

分類は ledger・inventory・merge 済み phase 記録の status のとおり。SUSPENDED を CLOSED 扱いしない。

<!-- table:evidence_map -->
| ref | 内容 | 分類 | 記録上の status |
| --- | --- | --- | --- |
| H-001 | M15 indicator zoo の絶対方向 | CLOSED | `CLOSED` |
| H-002 | session / ATR / ADX / spread gate | CLOSED | `CLOSED` |
| H-003 | pair relative strength（通貨 exposure が 96%） | CLOSED | `CLOSED` |
| H-004 | raw / simple price-feature の方向 ML | CLOSED | `CLOSED` |
| H-006 | 4〜6 日 reversal family | CLOSED | `MULTI_DAY_REVERSAL_FAILED_SUPPLEMENTAL_HISTORY_REPLICATION` |
| H-007 | mirror momentum（反証ではなく検出力不足） | CLOSED | `MULTI_DAY_MOMENTUM_UNRESOLVED_IN_FRESH_EXPLORATORY_HISTORY` |
| H-009 | 単純な HTF / D1 trend 条件付け | CLOSED | `CLOSED — Round A` |
| H-010 | price-path structure（VR<1、収益化不能） | CLOSED | `CLOSED - real but unharvestable microstructure` |
| H-013 | retrace geometry（clean retest） | CLOSED | `RETRACE_GEOMETRY_FAMILY_DROPPED_AFTER_CLEAN_RETEST` |
| H-014 | path linear monetization（固定 horizon、線形 selector） | CLOSED | `PATH_STRUCTURE_STATISTICALLY_REAL_BUT_ECONOMICALLY_TOO_SMALL` |
| H-017 | tick volume の方向 / timing | CLOSED | `CLOSED - volume is a volatility variable, not a timing one` |
| H-024 | post-hoc 通貨 reversal（5/20/60 日のみ） | CLOSED | `POST_HOC_EXPLORATORY_NON_DECISION_BEARING` |
| C21 | futures positioning（COT 由来） | CLOSED | `PRIOR_FAMILY_CLOSED` |
| C22 | carry level | CLOSED | `PRIOR_FAMILY_CLOSED` |
| H-012 | monthly TSMOM | NOT_SUPPORTED | `MONTHLY_TSMOM_NOT_SUPPORTED_IN_EXISTING_PRICE_HISTORY` |
| H-016 | 政策金利 proxy の carry（level / change） | NOT_SUPPORTED | `CARRY_EDGE_NOT_SUPPORTED` |
| H-020 | USD CPI の nowcast surprise 方向 | NOT_SUPPORTED | `MACRO_SURPRISE_DIRECTIONAL_EDGE_NOT_SUPPORTED` |
| H-021 | COT の tested cells | NOT_SUPPORTED | `COT_EDGE_NOT_SUPPORTED` |
| H-023 | linear continuous currency expected-return architecture | NOT_SUPPORTED | `CONTINUOUS_CURRENCY_PORTFOLIO_ARCHITECTURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` |
| #471 | event-day の cost 優位 | NOT_SUPPORTED | `EVENT_DAY_COST_ADVANTAGE_NOT_ESTABLISHED` |
| #475 | near-touch passive 執行 | NOT_SUPPORTED | `passive 執行は、この 2 パネルで意味のあるコスト削減を与えられない。` |
| H-022 | model learning（3 track、当時の gate） | NOT_DECISION_GRADE | `MODEL_LEARNING_NOT_DECISION_GRADE_UNDER_CURRENT_DEVELOPMENT_GATE` |
| #478 | seen data 上の長 horizon 構造（検出力不足） | NOT_DECISION_GRADE | `CURRENT_SEEN_DATA_FX_RESEARCH_SPACE_EXHAUSTED` |
| C09 | yield differential change（未実行） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C10 | equity risk regime conditioning（未実行） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C11 | commodity link response（未実行） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C01 | central bank decision response（未実行） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C03 | session handover relative（未実行） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C04 | benchmark fix flow（未実行） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C05 | month-end rebalancing flow（未実行、事象数が下限未満） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C06 | factor-neutral residual value（未実行） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C07 | cross-sectional dispersion state（未実行） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C13 | timeframe disagreement state（未実行） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C12 | volatility regime transition（未実行） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| C14 | latent regime state（未実行） | NOT_DECISION_GRADE | `NO_DECISION_GRADE_PASS_REGION` |
| #475 | clock / London fix の構造 | SUSPENDED | `CLOCK_STRUCTURE_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER` |
| #477 | non-USD surprise relative | SUSPENDED | `NON_USD_SURPRISE_DATA_NOT_DECISION_GRADE_SKIP` |
| C02 | macro surprise intraday | SUSPENDED | `DATA_INTEGRITY_BLOCKED` |
| C20 | broker order flow | SUSPENDED | `DATA_INTEGRITY_BLOCKED` |
| H-011 | retrace geometry（B′-2） | OPEN | `OPEN` |
| H-015 | tick volume → 将来の活動・volatility | OPEN | `TICK_VOLUME_INFORMATION_INCREMENTALLY_DISTINCT` |
| H-018 | 政策金利変更日の movement structure（cost 優位は不成立） | OPEN | `CALENDAR_EVENT_MOVEMENT_STRUCTURE_SUPPORTED` |
| H-019 | forward-known event の movement（方向なし） | OPEN | `FORWARD_KNOWN_EVENT_OPPORTUNITY_STRUCTURE_SUPPORTED` |
| #482 | efficiency bundle（band・部分 rebalance）の turnover 低減。裁定 token TURNOVER_REDUCTION_MECHANISM_SUPPORTED は H-023 に記録 | ENGINEERING_RESULT | `bundle は本来の目的（turnover 削減）は果たした` |
| #476 | unit-consistent feasibility gate | ENGINEERING_RESULT | `FEASIBILITY_GATE_V2_PROSPECTIVE_ONLY` |
| — | 市場利回り（2 年・曲線）による repricing | UNTESTED | `未取得・未検定` |
| — | 実質為替レート / valuation | UNTESTED | `未取得・未検定` |
| — | event 日の市場 repricing を方向ソースにする構造 | UNTESTED | `未検定` |
<!-- /table -->

## H. Rates / yield-curve の評価（候補 S01・S02・S23・S25）

- **S01（front-end 金利差 repricing）が最有力。** 過去に閉じたのは政策金利（階段関数）の level / change（H-016、
  `CARRY_EDGE_NOT_SUPPORTED`）で、**市場利回り**は一度も取得していない。C09（yield differential change）は horizon gate で
  未実行（`NO_DECISION_GRADE_PASS_REGION`）であり反証ではない。
- mechanism: 市場が織り込む政策パス（2 年金利）の相対変化に FX が遅れて追随する。同時相関は強いと予想されるが、
  **先行性**（数日〜数週の under-reaction）が問いであり、prior は中程度。
- capacity（R 節）: 半減期 20 日なら net 0.5 に 20 日 IC 12.8%（日次換算 2.9%）。常時稼働・breadth 実効 4 で、
  成立すれば 10% vol で年 5% の射程に入る。
- 最大の技術的罠は **非同期終値**: 各国の利回り終値は現地時刻で、FX の日次終値（例 21:00 UTC）と揃わない。
  利回りを 1 日遅らせるか、FX 側を利回り終値の後の時刻に揃えないと先読みになる。
- **データが律速**: US は FRED 日次で長期に揃うが、非 US の日次 2 年金利は各中銀から個別に取得する必要がある
  （本環境での到達性は E 節）。FRED の非 US は月次のみ。
- S02（曲線形状）は S01 より prior が弱くデータ負担が重い。S23（実質金利差 level）は H-016 の carry と隣接するため除外。
  S25（balance sheet）は観測数が少なく低 capacity。

## I. Cross-asset lead-lag の評価（S05・S06・S07・S24）

- FX は 24 時間連続取引なので、株式・商品の情報は **同時に** 織り込まれる prior が強い。先行性を主張するには
  時刻を揃えた検定（株式終値と同時刻の FX）が必須で、日次終値のずれは見かけの lead-lag を作る。
- S05（risk shock → funding vs 資源国通貨）は無料データで検定可能だが、実効 breadth が 2 程度で、必要 IC が上がる。
- S06（商品 → 資源国通貨）は breadth 1〜2 で単独の年 5% は困難。S07（信用 stress）は stress 期に偏り tail 集中が大きい。
- S24（vol で timing した carry）は NOT_SUPPORTED の carry を vol filter で救済する形なので **除外**。
- 結論: cross-asset は top 3 に入れない。S05 は S01 の検定後に、同じ執行層で安価に追加できる次点。

## J. Currency network / triangular structure の評価（S09・S10・S11）

- S09（三角 residual）は bid/ask を整合させると spread の内側に収まる無裁定構造で、H-010（収益化不能な microstructure）と
  同じ層。**除外**。
- S10（bloc 間 lead-lag 伝播）は aggregate VR（H-010）とは別の未検定仮説だが、FX の伝播は秒単位で裁定される prior が強く、
  intraday の turnover で cost を超えるには日次換算 IC 7% 以上が要る。低順位。
- S11（動的共通 factor residual の reversal）は H-024 の post-hoc 通貨 reversal と同形で、**名前を変えた復活になるため除外**。
- H-003（pair relative strength、通貨 exposure が 96%）との違い: Track 1 は通貨単位・factor 除去済みで H-003 の欠陥を
  構成で避けたが、price 由来の期待リターンそのものが負だった。network 構造は情報源ではなく **執行層**（pair routing、
  netting）として既に使っている。

## K. Relative-value / residual の評価（S12・S13）

- S12（相関 breakdown / dispersion の relative value）は price 由来の収束で H-024 と隣接、#480 の試算でも年 2% 未満。低順位。
- **S13（実質為替レート valuation）が第 2 位。** valuation は一度も検定していない（H-016 は carry、H-012 は momentum）。
  学術的な currency value premium は長期で存在し、低 turnover（約 5 RT/年）で cost の影響が小さい。
- ただし **seen の 4.7 年では検定不能**（半減期が年単位）。数十年の公開 FX 履歴が要り、それは保護 span
  （`2016-06-02 … 2021-04-25` の fresh pool、historical OOS、dead window、forward epoch）を**除外した** Red 承認の read を要する。
- capacity: 120 日半減期で net 0.5 に horizon IC 23%。学術 prior は G10 value 単独で net 0.2〜0.4 程度で、
  **単独で年 5% は楽観的**、他 source との分散源として価値がある。

## L. Multi-horizon interaction の評価（S14・S15）

- S14（fast/medium/slow の price state 不一致）は、Track 1 が 5/20/60 日の強さと trend age を線形に使って gross 負だった
  直後で、price 由来の多 horizon 情報に正の prior が無い。単純 sign conditioning（H-009）とは違う形にしても、
  情報源が同じ price なら indicator zoo に戻る危険が大きい。低順位。
- S15（状態遷移・latent regime）は条件付けであって return source ではなく、H-022 の regime-gain は一定 gross の book で
  増分が厳密に 0 だった。低順位。

## M. State-dependent nonlinear の評価（S16・S08）

- 非線形を研究仮説にしない。**S16（金利 repricing × volatility の閾値効果）** だけが機構から説明できる候補
  （risk 環境が荒れると金利差の感応度が落ちる）で、**S01 の線形 baseline が正になった場合の増分検定**としてのみ残す。
- S08（金利 vol 状態）は単独の return source ではなく、S16 に統合。
- 「LightGBM なら拾うかも」は採らない。順序は economic mechanism → feature family → simple baseline → nonlinear 増分。

## N. Event-conditioned の評価（S03・S04・S17）

- 過去の証拠は **event → movement / volatility が強く、方向が無い**（H-018・H-019 は OPEN の movement structure、
  H-020 の USD nowcast surprise は NOT_SUPPORTED、#471 の event-day cost 優位は不成立）。
- 新しい構造は **event × 別の方向ソース**: event 日の**市場 repricing**（2 年金利の当日変化）を surprise の測度にし、
  その後数日の FX drift を狙う。consensus も発表時刻も要らない（C02 の時刻問題、#477 の検出力問題を回避）。
- **S03（中銀会合）** は mechanism が最も明確（政策パスの repricing）で prior 中程度、ただし年約 60 事象で検出力が律速。
- **S04（主要指標発表）** は事象数を 150〜300 に増やすが、未 merge の #473 が survey consensus の USD 1h で検出力のある
  null を返しており、announcement 効果が 1h に集中するなら多日 drift も弱い、という警告付き。
- capacity（R 節）: 事象あたり net 0.5 に 8.4〜10.9 bp（課金 cost）/ 4.2〜6.7 bp（pair cost）、事象 sd の 12〜17%。
- S17（event × cross-asset 共動）は S03・S04 の増分としてのみ。
- **event filter で負の base を救済するものではない**: 方向は event ではなく repricing が決める。

## O. Positioning / flow の評価（S18・S19・S20）

- S18（retail positioning）は OANDA positionBook（認証要・禁止）、IG（口座要）、Myfxbook（web、過去履歴なし）で、
  **無料の過去履歴が揃わない**。forward に蓄積するしかなく、データ不可。
- S19（COT 変化 × price）は H-021（tested cells NOT_SUPPORTED）・C21（PRIOR_FAMILY_CLOSED）に重なり除外。
- S20（FX option の risk reversal）は prior が比較的強いが **有料データ**。取得は Human + ChatGPT の判断事項（勝手に取得しない）。

## P. Intraday information transmission の評価（S21・S22）

- S22（session 間の cross-market 情報伝達）は price のみにすると C03・H-002（CLOSED）と同じで、非 FX の intraday 情報
  （株価指数先物）は有料。データ不可。
- S21（月末の株式相対リターンに条件付けた hedge rebalance flow）は mechanism は明確だが年 12 事象で、#475 の London fix が
  検出力で SUSPENDED になった理由がそのまま当てはまる。年 5% には構造的に届かない。
- 単なる時刻平均リターンへの回帰はしない。

## Q. Candidate universe（25 候補）

### Q.1 定義

<!-- table:candidate_definitions -->
| ID | 方向 | 候補 | mechanism | information | target / horizon | architecture |
| --- | --- | --- | --- | --- | --- | --- |
| S01 | A | front-end 金利差 repricing → 通貨相対リターン | 市場が織り込む政策パス（2 年金利）の相対変化に、FX が数日〜数週遅れて追随する | 各国 2 年国債利回りの日次変化（通貨ごとに対 G10 平均） | 通貨の 5〜20 日先 excess return／5〜20 日 | continuous currency book（Track 1 の執行層を再利用） |
| S02 | A | 曲線 slope / curvature 差の変化 | 成長・インフレ期待の相対変化が通貨需要を動かす | 各国 2s10s・曲率の日次変化 | 通貨の 20〜60 日先 excess return／20〜60 日 | continuous currency book |
| S03 | G | 中銀会合日の市場 repricing → 会合後 drift | 会合日に市場が織り込んだ政策パスの変化（2 年金利の当日変化）に、FX が会合後数日かけて追随する（under-reaction） | G10 中銀会合カレンダー + 会合日の 2 年金利変化 | 会合通貨の 1〜5 日先 excess return（repricing の方向）／1〜5 日 | event book（idle 時は保有なし、Track 1 の執行層で差分売買） |
| S04 | G | 主要指標発表日の市場 repricing → 発表後 drift | surprise を consensus ではなく当日の市場 repricing（2 年金利の変化）で測り、発表後数日の FX drift を狙う | G10 主要指標の発表日 + 当日の 2 年金利変化 | 発表通貨の 1〜5 日先 excess return／1〜5 日 | event book |
| S05 | B | 株式・volatility shock → funding 通貨 vs 資源国通貨（時刻整合した lag） | risk appetite の変化が funding / carry 通貨へ遅れて波及する | VIX（FRED 日次 1990〜）、S&P 500・Nikkei（FRED 日次） | JPY・CHF 対 AUD・NZD・CAD の 1〜5 日先 excess return／1〜5 日 | continuous currency book |
| S06 | B | 商品価格 → 資源国通貨（terms of trade lead） | 原油・金属の価格変化が交易条件経由で CAD・AUD・NZD に遅れて反映される | WTI・Brent（FRED 日次）。金属の日次は無料では限定的（銅は月次） | CAD・AUD・NZD の 5〜20 日先 excess return／5〜20 日 | continuous currency book（3 通貨に集中） |
| S07 | B | 信用 spread・funding stress → USD・JPY・CHF | funding 市場の緊張が安全通貨需要に先行する | US HY OAS（FRED 日次）、SOFR（2018〜） | USD・JPY・CHF の 5〜20 日先 excess return／5〜20 日 | continuous currency book |
| S08 | B | 金利 volatility 状態 × FX | 金利 volatility の高低で FX の金利感応度が変わる | 利回り変化から推定する rates vol（MOVE は有料） | S01 の条件付け／5〜20 日 | S01 への条件付け |
| S09 | C | 三角 residual（cross と合成 cross の乖離） | pair 間の一時的な不整合の解消 | 20 pair の bid/ask | residual の縮小／秒〜分 | 高頻度 |
| S10 | C | 通貨 complex 間の lead-lag 伝播（例: EUR→CHF、AUD→NZD） | bloc の先行通貨の動きが追随通貨へ遅れて伝わる | 通貨 excess return の intraday 系列 | 追随通貨の数時間先 return／数十分〜数時間 | intraday currency book |
| S11 | C | 動的共通 factor residual の reversal | 共通 factor から外れた通貨が戻る | 通貨 excess return の rolling PCA residual | residual の 5〜20 日先縮小／5〜20 日 | continuous currency book |
| S12 | D | 相関 breakdown / dispersion 状態の relative value | 通常の共動から外れた pair が収束する | rolling 相関と dispersion | pair spread の 5〜20 日先／5〜20 日 | pair relative-value book |
| S13 | D | 実質為替レート valuation（PPP・実質金利 anchor） | 実質為替レートの長期均衡からの乖離が数か月〜数年で戻る（学術的な currency value premium） | 各国 CPI（FRED 月次）と長期の FX 水準 | 通貨の 3〜12 か月先 excess return／3〜12 か月 | continuous currency book（低 turnover） |
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
<!-- /table -->

### Q.2 実現可能性・重なり・capacity

<!-- table:candidate_feasibility -->
| ID | turnover | utilisation | breadth | data | access | 既存研究との重なり | なぜ未反証か | capacity | ML の役割 | 扱い |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | 18〜43 RT/年/単位 gross | 常時 | 8 通貨（実効 4） | US 2y は FRED 日次 1976〜。非 US 2y は各中銀（BoE・BoC・MOF は到達、ECB・Bundesbank・SNB は本環境で証明書エラー、RBA・RBNZ は 403） | 無料・認証不要（取得は承認後） | H-016、C09、H-023 | H-016 は政策金利（階段関数）の level / change で、市場利回りは未取得。C09 は horizon gate で未実行 | net 0.5 に 20 日 IC 12.8%（日次換算 2.9%）。prior は net 0.2〜0.5 | 不要（線形 baseline）。閾値相互作用は S16 で増分のみ | 対象 |
| S02 | 8〜18 RT/年/単位 gross | 常時 | 8 通貨（実効 4） | 非 US 10y の日次は中銀ソース（FRED の OECD 系列は月次のみ） | 無料・認証不要（取得は承認後） | C09 | 曲線形状は一度も取得していない | net 0.5 に 60 日 IC 17.8%。prior は net 0.1〜0.3 | 不要 | 対象 |
| S03 | 事象あたり 1 往復、約 60 事象/年 | 約 9% の日 | 8 中銀 | 会合カレンダーは Fed・ECB・BoJ・RBA を取得済み、BoE・BoC・SNB・RBNZ は追加要。2 年金利は S01 と同じ | 無料・認証不要（取得は承認後） | C01、H-019、H-018、H-016 | H-018/H-019 は event の movement のみで方向ソースを持たず、H-016 は決定そのもので市場 repricing ではない。C01 は未実行 | n=60・3 日保有で net 0.5 に事象あたり 10.9 bp（課金）/ 6.7 bp（pair）。事象数が少なく検出力が律速 | 不要 | 対象 |
| S04 | 事象あたり 1 往復、150〜300 事象/年 | 22〜74% の日 | 8 通貨 | US 発表日は ALFRED を取得済み、非 US は発表日カレンダーが要る。2 年金利は S01 と同じ | 無料・認証不要（取得は承認後） | H-020、C02、#477、H-019 | H-020 は US CPI の nowcast surprise で 1h〜1d・breadth 不足、C02 は時刻データの問題で blocked、#477 は検出力で skip。市場 repricing を surprise とする多日 drift は未検定。未 merge の #473 は survey consensus の USD 1h で検出力ある null | n=150〜300・2〜5 日保有で net 0.5 に事象あたり 8.4〜9.4 bp（課金）/ 4.2〜5.2 bp（pair） | 不要 | 対象 |
| S05 | 43〜100 RT/年/単位 gross | 常時 | 実効 2（risk 軸 1 本） | FRED で無料。FX 側は株式終値と同時刻に揃える必要（M1 archive で可能） | 無料・認証不要 | C10、H-016 | C10 は未実行。carry（H-016）は level で risk shock の lag ではない | breadth 2 のため必要 IC が約 1.4 倍に上がる。FX は 24h 連続取引で同時に織り込む prior が強い | 不要 | 対象 |
| S06 | 18〜43 RT/年/単位 gross | 常時 | 実効 1〜2 | 原油は無料、金属・乳製品の日次は有料寄り | 一部無料 | C11 | C11 は未実行 | breadth が狭く、net 0.5 に必要な IC が高い。単独での年 5% は困難 | 不要 | 対象 |
| S07 | 18〜43 RT/年/単位 gross | 常時（効くのは stress 期のみの可能性） | 実効 1〜2 | FRED で無料 | 無料・認証不要 | C10 | 未実行 | stress 期に偏るため tail 集中が大きく、年間を通じた収益は小さい prior | 不要 | 対象 |
| S08 | S01 と同程度 | 常時 | S01 と同じ | S01 と同じ | 無料（MOVE は有料） | C12、H-002 | 単独の return source ではなく条件付けで、S01 の base が正でなければ意味を持たない | S01 の増分のみ | S16 と統合 | 対象 |
| S09 | 極めて高い | 断続 | 多い | M1 archive はあるが分解能が足りない | — | H-010 | bid/ask を整合させると乖離は spread の内側に収まる（無裁定条件） | spread 内の構造で、構造的に cost を超えない | — | 除外（閉鎖 family の改名・救済） |
| S10 | 100 RT/年/単位 gross 超 | 常時 | bloc 数（3〜4） | M1 archive（seen span のみ） | 保有 | H-010、H-003、H-002 | aggregate の VR（H-010）は検定済みだが、bloc 間の cross lead-lag は未検定 | 半減期 1 日で net 0.5 に日次 IC 7%、intraday はさらに高い。FX の伝播は秒単位で裁定される prior | 不要 | 対象 |
| S11 | 18〜43 | 常時 | 実効 4 | 保有 | 保有 | H-024、C06、H-023 | —（通貨 reversal の事後観察 H-024 と同形で、名前を変えた復活になる） | — | — | 除外（閉鎖 family の改名・救済） |
| S12 | 18〜43 | 断続 | 低い | 保有 | 保有 | C07、H-003、H-024 | C07 は未実行だが、price 由来の収束は H-024 と隣接 | #480 の A12 は構造的に年 2% 未満と試算 | 不要 | 対象 |
| S13 | 約 5 RT/年/単位 gross | 常時 | 8 通貨（実効 4） | CPI は無料。検定には数十年の FX 履歴が要り、seen の 4.7 年では不能 | 無料（FX 長期履歴の read は保護 span 外に限り承認が要る） | H-016、H-012 | valuation は一度も検定していない。H-016 は carry、H-012 は momentum | net 0.5 に 120 日 IC 23%。学術 prior は G10 value 単独で net 0.2〜0.4、低 turnover の分散源 | 不要 | 対象 |
| S14 | 18〜43 | 常時 | 実効 4 | 保有 | 保有 | C13、H-009、H-023 | C13 は未実行だが、Track 1（5/20/60 日 + trend age の線形結合）が gross 負 | price 由来の多 horizon 情報は H-023 で線形に使って負 | 非線形の相互作用を仮説にしない限り不要 | 対象 |
| S15 | 18〜43 | 常時 | 実効 4 | 保有 | 保有 | C12、C14、H-002、H-022 | C12・C14 は未実行。H-022 の regime-gain は一定 gross の book で増分が厳密に 0 | 状態は return source ではなく条件付け。base が負なら救済にならない | HMM 等は未承認の複雑化になりやすい | 対象 |
| S16 | S01 よりやや高い | 常時 | S01 と同じ | S01 + FRED | 無料 | S01、C10 | S01 の線形 baseline が正でない限り検定しない（順序規律） | S01 の増分のみ | 閾値の非線形は S01 の後に増分検定として | 対象 |
| S17 | 事象あたり 1 往復 | 断続 | 8 通貨 | S03・S04・S05 の合成 | 無料 | S03、S04、C10 | S03・S04 の repricing 方向が効くかを先に見るべきで、cross-asset の追加はその増分 | S03・S04 の増分のみ | 不要 | 対象 |
| S18 | 高い | 常時 | 20 pair（実効は少ない） | 過去履歴が無料で揃わず、forward に蓄積するしかない | 認証または web scraping（未承認） | C20 | データが無い | —（データなし） | 不要 | データ不可 |
| S19 | 低い | 常時 | 7 通貨 | 保有 | 保有 | H-021、C21 | —（H-021 で tested cells が NOT_SUPPORTED、C21 は PRIOR_FAMILY_CLOSED） | — | — | 除外（閉鎖 family の改名・救済） |
| S20 | 中 | 常時 | 主要 pair | 無料の履歴なし（Bloomberg・CME 等の有料） | 有料 | なし | データが無い | —（データなし） | 不要 | データ不可 |
| S21 | 年 12 回 × 数 pair | 極めて低い | 低い | S&P・Nikkei は無料、他は限定的 | 一部無料 | C05、C04、#475 | C05 は未実行、#475 の London fix は検出力で SUSPENDED | 事象が年 12 回しかなく、年 5% には構造的に届かない | 不要 | 対象 |
| S22 | 高い | 1 日 1〜2 回 | 実効 2〜4 | intraday 先物は有料 | 有料 | C03、H-002、#475 | price のみの session 効果は H-002 で CLOSED、clock は #475 で SUSPENDED。非 FX の intraday 情報は未取得 | 日 1〜2 回の決定で、半減期は数時間。cost 負けの prior が強い | 不要 | データ不可 |
| S23 | 低い | 常時 | 実効 4 | 取得済みの政策金利 + CPI | 保有・無料 | H-016、C22 | —（H-016 の carry premium は short-yen に集中して NOT_SUPPORTED、level の組み替えは隣接） | — | — | 除外（閉鎖 family の改名・救済） |
| S24 | 低い | 常時 | 実効 4 | 保有 | 保有 | H-016、C22 | —（NOT_SUPPORTED の carry を vol filter で救済する形） | — | — | 除外（閉鎖 family の改名・救済） |
| S25 | 低い | 常時 | 主要 4〜5 中銀 | 無料だが月次で観測数が少ない | 無料 | なし | 未検定 | 観測数が少なく、seen の期間では検定不能。単独で年 5% の prior は低い | 不要 | 対象 |
<!-- /table -->

## R. Profit-capacity table

calibration: 単位 gross あたり vol 2.426%（Track 1 の unlevered 診断 book の実測 2.3704% ÷ 平均 gross 0.9771）、
cost 3.406 bp/turnover unit（課金規約）、実効 breadth 4/日、transfer coefficient 0.90（Track 1 の raw→neutralised 相関）、
band 0.10・cap 0.25 の signal-free band law。**source がこの品質を持つとは言っていない。必要な品質を示す。**

### R.1 continuous currency book

<!-- table:continuous_capacity -->
| 予測の半減期 | turnover / 年 / 単位 gross | alpha capture | cost による IR 低下 | net 0.3 / 0.5 / 0.8 に必要な gross IR | net 0.3 / 0.5 / 0.8 に必要な horizon IC | net 0.5 の日次換算 IC |
| --- | --- | --- | --- | --- | --- | --- |
| 1d | 100.78 | 0.9513 | 1.415 | 1.715 / 1.915 / 2.215 | 6.3% / 7.0% / 8.2% | 7.0% |
| 5d | 43.36 | 0.9323 | 0.609 | 0.909 / 1.109 / 1.409 | 7.6% / 9.3% / 11.8% | 4.2% |
| 20d | 18.28 | 0.9264 | 0.257 | 0.557 / 0.757 / 1.057 | 9.4% / 12.8% / 17.8% | 2.9% |
| 60d | 8.39 | 0.9395 | 0.118 | 0.418 / 0.618 / 0.918 | 12.0% / 17.8% / 26.5% | 2.3% |
| 120d | 5.07 | 0.9498 | 0.071 | 0.371 / 0.571 / 0.871 | 15.0% / 23.1% / 35.2% | 2.1% |
<!-- /table -->

### R.2 年率と leverage

<!-- table:return_capacity -->
| vol target | gross leverage | net 0.3 の年率 | net 0.5 の年率 | net 0.8 の年率 | 年 5% に必要な net Sharpe | 年 10% に必要な net Sharpe |
| --- | --- | --- | --- | --- | --- | --- |
| 8% | 3.3 | 2.4% | 4.0% | 6.4% | 0.625 | 1.25 |
| 10% | 4.12 | 3.0% | 5.0% | 8.0% | 0.5 | 1.0 |
| 12% | 4.95 | 3.6% | 6.0% | 9.6% | 0.417 | 0.833 |
<!-- /table -->

### R.3 event book（事象は独立と仮定、これは楽観側）

<!-- table:event_capacity -->
| 事象 / 年 | 保有日数 | net Sharpe | 事象あたり sd（bp） | 必要 edge（課金 cost、bp） | 必要 edge（pair cost、bp） | 必要 edge（事象 sd 比、課金） | 平均同時保有 | 10% vol の片側 notional レバレッジ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 60 | 3 | 0.3 | 63.0 | 9.25 | 5.02 | 14.7% | 0.71 | 1.46 |
| 60 | 3 | 0.5 | 63.0 | 10.88 | 6.65 | 17.3% | 0.71 | 1.46 |
| 60 | 3 | 0.8 | 63.0 | 13.32 | 9.09 | 21.1% | 0.71 | 1.46 |
| 150 | 3 | 0.3 | 63.0 | 8.36 | 4.12 | 13.3% | 1.79 | 2.31 |
| 150 | 3 | 0.5 | 63.0 | 9.38 | 5.15 | 14.9% | 1.79 | 2.31 |
| 150 | 3 | 0.8 | 63.0 | 10.93 | 6.7 | 17.3% | 1.79 | 2.31 |
| 300 | 2 | 0.3 | 55.09 | 7.77 | 3.53 | 14.1% | 2.38 | 2.5 |
| 300 | 2 | 0.5 | 55.09 | 8.4 | 4.17 | 15.2% | 2.38 | 2.5 |
| 300 | 2 | 0.8 | 55.09 | 9.36 | 5.12 | 17.0% | 2.38 | 2.5 |
| 300 | 5 | 0.3 | 76.4 | 8.14 | 3.9 | 10.7% | 5.95 | 4.5 |
| 300 | 5 | 0.5 | 76.4 | 9.02 | 4.79 | 11.8% | 5.95 | 4.5 |
| 300 | 5 | 0.8 | 76.4 | 10.34 | 6.11 | 13.5% | 5.95 | 4.5 |
<!-- /table -->

### R.4 読み方

- **edge per unit turnover × turnover × exposure**: 速い予測（半減期 1〜5 日）は turnover が 43〜101 RT/年/単位 gross で、
  cost だけで IR が 0.6〜1.4 削られる。遅い予測（60〜120 日）は cost が軽い（0.07〜0.12）が、horizon IC を 18〜23% 要求する。
  **turnover を減らせば解決、でも、高頻度は不可能、でもない。** 日次換算の必要 IC は半減期 20〜120 日で 2.1〜2.9% に収まる。
- **年 5〜10% の capacity**: 10% vol で年 5% に net 0.5、年 10% に net 1.0。12% vol なら net 0.42 / 0.83。
  leverage は 10% vol で gross 約 4.1 倍（片側 notional ではその半分）。
- **検出の限界**: net 0.5 を片側 5% で 0 と区別するには約 10.8 年、net 0.8 で約 4.2 年の out-of-sample が要る。
  seen の 4.7 年では net 0.5 の source を決められない。**新しい独立履歴が研究可能性そのものを左右する。**

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
| S09 | H-010（CLOSED） | 除外（閉鎖 family の改名・救済） |
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
| S21 | C05（NOT_DECISION_GRADE）、C04（NOT_DECISION_GRADE）、#475（NOT_SUPPORTED・SUSPENDED） | 対象 |
| S22 | C03（NOT_DECISION_GRADE）、H-002（CLOSED）、#475（NOT_SUPPORTED・SUSPENDED） | データ不可 |
| S23 | H-016（NOT_SUPPORTED）、C22（CLOSED） | 除外（閉鎖 family の改名・救済） |
| S24 | H-016（NOT_SUPPORTED）、C22（CLOSED） | 除外（閉鎖 family の改名・救済） |
| S25 | なし（UNTESTED） | 対象 |
<!-- /table -->

## T. Candidate ranking

重み（採点前に宣言）: 利得は P(real edge)×2・経済規模・資本稼働・breadth・頑健性・情報利得×2、負担は turnover cost・
複雑さ・過学習リスク・データ負担・実装負担を各 1 で差し引く。**判断であって測定ではない**（backtest は一切していない）。
除外・データ不可の候補は順位を付けずに下に並べる。

<!-- table:ranking -->
| 順位 | ID | 候補 | score | P(real) | 規模 | 稼働 | breadth | 頑健 | 情報利得 | turnover | 複雑 | 過学習 | data | 実装 | 扱い |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | S01 | front-end 金利差 repricing → 通貨相対リターン | 20 | 3 | 3 | 5 | 4 | 3 | 5 | 2 | 2 | 2 | 3 | 2 | 対象 |
| 2 | S13 | 実質為替レート valuation（PPP・実質金利 anchor） | 18 | 3 | 2 | 5 | 4 | 3 | 4 | 1 | 1 | 2 | 4 | 2 | 対象 |
| 3 | S03 | 中銀会合日の市場 repricing → 会合後 drift | 12 | 3 | 2 | 1 | 3 | 3 | 4 | 2 | 2 | 2 | 3 | 2 | 対象 |
| 4 | S02 | 曲線 slope / curvature 差の変化 | 11 | 2 | 2 | 5 | 4 | 2 | 3 | 1 | 2 | 3 | 4 | 2 | 対象 |
| 5 | S05 | 株式・volatility shock → funding 通貨 vs 資源国通貨（時刻整合した lag） | 9 | 2 | 2 | 5 | 2 | 2 | 3 | 3 | 2 | 3 | 2 | 2 | 対象 |
| 6 | S04 | 主要指標発表日の市場 repricing → 発表後 drift | 8 | 2 | 3 | 3 | 4 | 2 | 4 | 3 | 3 | 3 | 4 | 3 | 対象 |
| 7 | S25 | 中銀 balance sheet・準備資産 flow | 7 | 2 | 1 | 5 | 2 | 2 | 2 | 1 | 2 | 3 | 3 | 2 | 対象 |
| 8 | S16 | 金利 repricing × volatility の閾値効果 | 5 | 2 | 2 | 5 | 4 | 2 | 2 | 2 | 4 | 4 | 3 | 3 | 対象 |
| 9 | S06 | 商品価格 → 資源国通貨（terms of trade lead） | 4 | 2 | 1 | 4 | 1 | 2 | 2 | 2 | 2 | 3 | 3 | 2 | 対象 |
| 10 | S14 | fast / medium / slow の price state 不一致 | 4 | 1 | 2 | 5 | 4 | 1 | 1 | 2 | 3 | 5 | 1 | 1 | 対象 |
| 11 | S07 | 信用 spread・funding stress → USD・JPY・CHF | 3 | 2 | 1 | 2 | 1 | 2 | 2 | 2 | 2 | 3 | 2 | 2 | 対象 |
| 12 | S21 | 月末の株式相対リターンに条件付けた hedge rebalance flow | 2 | 3 | 1 | 1 | 1 | 2 | 2 | 2 | 2 | 3 | 3 | 3 | 対象 |
| 13 | S17 | event 日の cross-asset 共動を方向ソースにする | 0 | 2 | 2 | 2 | 3 | 2 | 2 | 3 | 4 | 4 | 3 | 3 | 対象 |
| 14 | S10 | 通貨 complex 間の lead-lag 伝播（例: EUR→CHF、AUD→NZD） | -1 | 1 | 2 | 4 | 2 | 1 | 2 | 5 | 3 | 4 | 1 | 3 | 対象 |
| 15 | S15 | volatility / trend の状態遷移（latent regime） | -1 | 1 | 1 | 4 | 3 | 1 | 1 | 2 | 4 | 5 | 1 | 2 | 対象 |
| 16 | S08 | 金利 volatility 状態 × FX | -2 | 1 | 1 | 3 | 3 | 1 | 1 | 2 | 3 | 4 | 3 | 2 | 対象 |
| 17 | S12 | 相関 breakdown / dispersion 状態の relative value | -3 | 1 | 1 | 2 | 2 | 1 | 1 | 3 | 3 | 4 | 1 | 2 | 対象 |
| — | S20 | FX option の risk reversal / implied vol skew | 8 | 3 | 2 | 4 | 3 | 2 | 3 | 2 | 2 | 3 | 5 | 3 | データ不可 |
| — | S23 | ex-ante 実質金利差の level | 7 | 1 | 2 | 5 | 4 | 1 | 1 | 1 | 2 | 3 | 2 | 1 | 除外（閉鎖 family の改名・救済） |
| — | S24 | volatility で timing した carry（crash risk 回避） | 6 | 1 | 2 | 4 | 4 | 1 | 1 | 1 | 2 | 4 | 1 | 1 | 除外（閉鎖 family の改名・救済） |
| — | S11 | 動的共通 factor residual の reversal | 5 | 1 | 2 | 5 | 4 | 1 | 1 | 2 | 2 | 5 | 1 | 1 | 除外（閉鎖 family の改名・救済） |
| — | S19 | COT の変化 × price の相互作用 | 4 | 1 | 1 | 4 | 3 | 1 | 1 | 1 | 2 | 4 | 1 | 1 | 除外（閉鎖 family の改名・救済） |
| — | S18 | retail positioning の逆張り | 3 | 2 | 2 | 4 | 3 | 2 | 3 | 4 | 2 | 3 | 5 | 4 | データ不可 |
| — | S22 | session 間の cross-market 情報伝達（Asia→London、London→NY） | -7 | 1 | 2 | 2 | 2 | 1 | 2 | 4 | 3 | 4 | 5 | 4 | データ不可 |
| — | S09 | 三角 residual（cross と合成 cross の乖離） | -8 | 1 | 1 | 2 | 3 | 1 | 1 | 5 | 3 | 3 | 4 | 4 | 除外（閉鎖 family の改名・救済） |
<!-- /table -->

## U. Blind-spot review

- **「price 由来だから全部無理」と一般化していないか**: していない。閉じたのは検定した price family（H-001・H-003・H-004・
  H-006・H-009・H-023 等）で、未検定の price 構造（S10 の bloc 間 lead-lag）は低順位だが残している。順位が低いのは
  price 由来だからではなく、裁定速度と turnover の算術のため。
- **「ML が全部無理」**: していない。S16 を非線形の増分候補として残した。ML を仮説にしないだけで、排除していない。
- **「cross-sectional が全部無理」**: していない。S01・S13 は cross-sectional な通貨 book。H-003 と Track 1 の失敗は
  情報源（price）の問題として扱った。
- **「multi-timeframe が全部無理」**: 単純 sign conditioning（H-009）と Track 1 の線形多 horizon は負。非 price 情報の
  horizon 構造（S01 の 5〜20 日、S13 の月単位）は別物として評価した。
- **「event 方向が全部無理」**: していない。H-020 は US CPI の nowcast surprise 1 種、#473 は survey consensus の USD 1h で、
  市場 repricing を方向ソースにする多日 drift（S03・S04）は未検定。
- **過去の失敗に過学習して新しい mechanism を落としていないか**: 最大の危険は逆で、**過去の検出力不足（NOT_DECISION_GRADE）を
  反証と読むこと**。C01・C09・C10・C11 は gate の horizon 条件で未実行なだけで、候補の重なりとして扱い、除外理由にしていない。
- **見落とし候補**: 有料データ（S20 の option、OIS 履歴、intraday 先物）は prior が比較的強いが、データ購入は Human 判断。

## V. Adversarial review（上位候補）

### S01（front-end 金利差 repricing）

- **焼き直しではないか**: H-016 の carry change と同じでは？ → H-016 は中銀の**決定**（月に一度変わる階段関数）で、
  S01 は毎日動く**市場の期待**。ただし両者の情報は相関する。carry level の premium が short-yen に集中した H-016 の教訓から、
  S01 も **JPY 依存と breadth** を最初に確認する必要がある。
- **本当に expected-return source か**: 金利と FX の**同時**相関は強くても、先行性は効率的市場なら小さい。先行性が無ければ
  S01 は「同時に動く」だけで収益にならない。これが最大の反証リスク。
- **architecture で負の edge を隠していないか**: Track 1 と同じ執行層を使うので、gross が負なら band・vol target では救えない
  （C 節）。判定は gross と benchmark（unfitted な金利差 rule）で行う。
- **capacity は十分か**: 成立すれば常時稼働・breadth 4 で年 5% の射程。ただし必要 IC 12.8%（20 日）は高い。
- **データで研究可能か**: 非 US の日次 2 年金利の取得と、非同期終値の処理が前提。seen 4.7 年では net 0.5 を決められない。

### S13（実質為替レート valuation）

- **焼き直しではないか**: carry・momentum とは別の style で、ledger に重なりは無い。
- **本当に source か**: 学術的には長期で観測されるが、G10 value の Sharpe は低く、数年単位で負け続ける期間がある。
- **capacity**: 単独で年 5% は楽観的。分散源としての価値が中心。
- **データで研究可能か**: seen では不能。保護 span を除外した長期公開 FX 履歴の read 承認が前提で、承認されなければ研究できない。

### S03 / S04（event × 市場 repricing）

- **焼き直しではないか**: H-019 の event movement に方向を足しただけでは？ → 方向ソース（市場 repricing）が新しく、
  それが無い限り H-019 は方向を持たない。ただし **event filter 救済** にならないよう、baseline は「全日の repricing」
  （S01 の日次版）と比べて event 日に上乗せがあるかで判定する。
- **本当に source か**: FX の repricing への反応が当日中に完了するなら drift は無い。#473 の USD 1h の null はその方向の警告。
- **capacity**: S03 は年 60 事象で年 5% には leverage と事象ごとの edge 約 11 bp（課金）が要り、検出力が律速。
  S04 を足すと事象数は増えるが、個々の edge は薄くなる可能性。
- **データで研究可能か**: 会合カレンダーの残り 4 中銀と、非 US の指標発表日カレンダー、日次 2 年金利が要る。

## W. 次に研究する価値が最も高い track（3 つ）

共通の前提（track ではなく **Human + ChatGPT の判断事項**）:

- **D-1. 新しい独立履歴**: 保護 span（fresh pool `2016-06-02 … 2021-04-25`、historical OOS、dead window、forward epoch）を
  **除外した**、`2016-06-02` より前の公開日次 FX 履歴の read。seen 4.7 年では net 0.5 を決められない（R.4）。T-V はこれが
  無ければ実行不能、T-R・T-E も検出力が大きく変わる。Red（実データ read）なので、操作・span・系列・承認 head を名指しした承認が要る。
- **D-2. 非 FX の公開データ取得**: 日次 2 年金利（8 通貨）・中銀会合カレンダー（残り 4 中銀）・指標発表日カレンダー・
  CPI の取得。無料・認証不要。

### T-R — 市場利回り repricing → 通貨相対リターン（S01）

| 項目 | 内容 |
| --- | --- |
| economic mechanism | 市場が織り込む政策パス（2 年金利差）の相対変化に FX が数日〜数週遅れて追随する |
| なぜ本当に新しいか | 市場利回りは未取得・未検定。H-016 は政策金利（決定）、C09 は未実行 |
| exact target | 通貨の 5 日先・20 日先 excess return（2 本を事前に固定、sweep しない） |
| data | 8 通貨の日次 2 年金利（D-2）、FX は seen corpus（+ D-1 が承認されれば pre-2016 履歴） |
| horizon | 5〜20 日 |
| portfolio architecture | Track 1 の執行層（factor-neutral・cap・band 0.10・vol target）を再利用。alpha model は新規 |
| expected turnover | 18〜43 RT/年/単位 gross |
| plausible return capacity | 成立時 net 0.2〜0.5 の prior、10% vol で年 2〜5% |
| baseline | unfitted な 2 年金利差変化 rule（符号固定、1 本）、B0 cash、Track 1 の price model（負の比較対象） |
| minimum experiment | (1) データ取得と時刻整合の監査（非同期終値を 1 日 lag で処理）(2) signal-blind な Feasibility Gate v2 と capacity を結果前に計算 (3) 線形 1 model・特徴 3 以下・walk-forward・purge/embargo |
| success criterion | gross > 0 かつ net Sharpe ≥ 0.3（seen）、JPY 除外でも符号維持、正の fold が過半、D-1 承認時は独立履歴でも gross > 0 |
| kill criterion | gross ≤ 0、または unfitted rule に劣後、または JPY 依存（除外で符号反転） |
| broad family を閉じる結果 | 独立履歴を含めて 5〜20 日の先行性が gross 0 以下なら「front-end 金利 repricing が G10 FX を先行する」family を閉じる |
| ML は必要か | 不要。S16 の閾値相互作用は gross 正の後の増分検定としてのみ |

### T-E — event 日の市場 repricing → 事後 drift（S03 主、S04 副）

| 項目 | 内容 |
| --- | --- |
| economic mechanism | 中銀会合・主要指標の当日に市場が repricing した方向へ、FX が数日かけて追随する（under-reaction） |
| なぜ本当に新しいか | 過去の event 研究は movement のみ（H-018/H-019）か、consensus / nowcast の surprise（H-020、#473）。市場 repricing を方向ソースにする多日 drift は未検定 |
| exact target | 会合・発表通貨の 1 日先・3 日先 excess return（2 本を事前固定） |
| data | 8 中銀の会合カレンダー、指標発表日、当日の 2 年金利変化（D-2） |
| horizon | 1〜3 日 |
| portfolio architecture | event book（idle 時は保有なし）を Track 1 の差分課金執行層で |
| expected turnover | 事象あたり 1 往復、S03 で年約 60、S04 込みで 150〜300 |
| plausible return capacity | 事象あたり 8〜11 bp（課金）の edge が要る。S03 単独は年 5% に届きにくく、S04 込みで射程 |
| baseline | 全日の repricing rule（S01 の日次版）、event 日の無条件 book、B0 |
| minimum experiment | (1) 事象母集団を結果前に凍結（会合は全 8 中銀、指標は機械的規則）(2) 検出力計算（事象数×必要 edge）を結果前に (3) repricing 符号の単一 rule |
| success criterion | event 日の repricing rule が全日の repricing rule を上回り、net Sharpe ≥ 0.3、会合・中銀の breadth（1 中銀依存でない） |
| kill criterion | event 日の上乗せが無い（= S01 と同じ）、または drift の符号が中銀間で不一致、または検出力が事前に不足（その場合は NOT_DECISION_GRADE で止める） |
| broad family を閉じる結果 | 十分な検出力で drift が 0 なら「G10 FX は event 時の市場 repricing に当日中に反応を完了する」として event-direction family を閉じる |
| ML は必要か | 不要 |

### T-V — 実質為替レート valuation（S13）— **D-1 が承認された場合のみ**

| 項目 | 内容 |
| --- | --- |
| economic mechanism | 実質為替レートの長期均衡からの乖離が数か月〜数年で戻る（currency value premium） |
| なぜ本当に新しいか | valuation は未検定。carry（H-016）・momentum（H-012）とは別 style |
| exact target | 通貨の 3 か月先 excess return（1 本） |
| data | CPI（無料）、保護 span を除外した長期公開 FX 履歴（D-1） |
| horizon | 3〜12 か月 |
| portfolio architecture | Track 1 の執行層、月次 rebalance |
| expected turnover | 約 5 RT/年/単位 gross |
| plausible return capacity | 単独 net 0.2〜0.4 の prior、10% vol で年 2〜4%。分散源 |
| baseline | 等加重 cash、PPP 乖離の単純 rank rule（1 本） |
| minimum experiment | (1) D-1 の履歴の品質監査（fix 時刻、bid/ask の欠如、cost の上乗せ）(2) 長期 walk-forward の検出力計算 (3) 単一 rule |
| success criterion | 独立履歴の複数 decade で gross > 0 かつ net Sharpe ≥ 0.3、decade 間で符号が安定 |
| kill criterion | gross ≤ 0、または 1 通貨・1 decade 依存 |
| broad family を閉じる結果 | 数十年で net ≤ 0 なら G10 valuation family を閉じる |
| ML は必要か | 不要 |

**3 つを無理に選んだのではない**: T-R は最上位、T-E は event の強い movement 構造に初めて方向ソースを与える唯一の候補、
T-V は第 2 位だが D-1 の承認に完全に依存する。D-1 が否決されれば T-V は外れ、提案は 2 track になる。

## X. 最小実験（実行はしない）

| track | 最初の実験 | 結果を見る前に固定するもの | 読むデータ | 承認 |
| --- | --- | --- | --- | --- |
| T-R | データ取得・時刻整合監査 → signal-blind gate → 線形 1 model | target 2 本、特徴 3 以下、lag 規則、benchmark、kill | 非 FX 公開データ（D-2）、seen FX | D-2 の取得、実行は Red |
| T-E | 事象母集団の凍結 → 検出力計算 → 単一 rule | 事象規則、target 2 本、baseline、kill | 同上 | 同上 |
| T-V | D-1 履歴の品質監査 → 長期検出力 → 単一 rule | 系列、span（保護 span 除外）、target、kill | D-1 | D-1（Red） |

いずれも探索自由度（特徴数、target 本数、model 数、horizon）を事前に宣言し、feature zoo・hyperparameter zoo・timeframe zoo・
seed mining・通貨 subset mining はしない。development では α=0.05 の証明を hard gate にせず、限定 search budget・時間方向の
walk-forward・benchmark 比較・経済 stress・安定性・複雑さ penalty・leakage control で判断する。

## Y. 最終推奨

**問い 1: Track 1 が gross 負だった事実を受け入れた上で、次にどの expected-return source を研究するのが最も合理的か。**

→ **市場利回りの repricing（T-R）**。price 以外で、常時稼働・breadth 4・無料データ・未検定・Track 1 の執行層を
そのまま使える唯一の source。次点は **event × 市場 repricing（T-E）** で、過去研究で最も強かった event の movement 構造に
方向を与える。

**問い 2: 成立した場合、年 5〜10% の net return に届く経済 capacity はあるか。**

→ **年 5% は射程、年 10% は困難**。10% vol で年 5% に net 0.5、年 10% に net 1.0 が要る。T-R の prior（net 0.2〜0.5）の
上端で年 5%、T-R と T-V・T-E の組み合わせで分散が効けば 12% vol で年 5〜6% が現実的な上限の見立て。年 10% は
単一 source の prior を超え、複数の独立 source の成立が前提。

**問い 3: 次に何を実験すべきか（最大 3）。**

1. **T-R の最小実験**（データ取得・時刻整合監査 → signal-blind gate → 線形 1 model）
2. **T-E の最小実験**（事象母集団の凍結 → 検出力計算 → 単一 rule）
3. **T-V の最小実験**（D-1 が承認された場合のみ）

**Human + ChatGPT の判断事項**: どの track を選ぶか、D-1（保護 span を除外した pre-2016 公開 FX 履歴の read）、D-2（非 FX
公開データの取得）、有料データ（option・OIS・intraday 先物）を検討するか、#473 の扱い。

**研究を止める提案ではない。** top 候補の prior は中程度で、年 10% の単独 source は見当たらないが、未検定の情報源は残っている。
continuation / stop は Human 判断。

保護データ: fresh pool `2016-06-02 … 2021-04-25`、historical OOS、dead window、forward Formal Confirmation epoch は、本 task の
candidate 生成・schema 確認を含め一切読んでいない。
