# PROFITABLE_AUTOMATED_TRADING_SYSTEM_DISCOVERY — 研究 programme 設計報告（2026-09-29）

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` · `PRODUCTION_READINESS_NOT_CLAIMED`.**

Human + ChatGPT の依頼（2026-09-29、programme の研究思想の再設計）への設計報告。

**この文書は設計だけである。** 次のどれもしていない。

- backtest・alpha 実行・学習・hyperparameter 探索
- data 取得
- fresh・OOS・dead・forward の読み取り
- broker 接続
- 有料 data の購入

**表記**

- 「§N」はこの文書の節、「裁定 §N」は依頼文の節を指す。
- Sharpe は特に断らない限り、年率・net で、SE ≈ 1/√年数 の近似で扱う。
- 「確認できる Sharpe」は、片側 5%・検出力 80% で計算する。#496 §11 の 1.27 は両側 5% の値である。

**根拠**（全て読み取りだけ）

- repo の既存文書・code・artifact を読む監査 2 本
  - 過去の programme が system 要素をどこまで試したか
  - 再利用できる資産の棚卸し
- signal を使わない算術（§13）
- 独立 review 2 役（契約・事実の監査、敵対的 review）
  - どちらも BLOCKER を指摘した。この版は、その全てを反映した**第 2 稿**である（§44）。

**旧 programme の結論は変えない。** `EXPECTED_RETURN_SOURCE_DISCOVERY` は `LONG_TERM_HOLD` / `NO_FURTHER_SEEN_DATA_ALPHA_SEARCH` のまま保持する。

- `FX_HAS_NO_EDGE` という意味ではない。
- 根拠の 1 つである #497（carry + momentum の合成）は、PR が open で、merge は未承認である。

---

## 1. Executive Summary

**旧 programme の何が狭かったか**

- post-R1（#464〜#497）は、ほぼ全てを「固定 rule の standalone な expected return」として測った。
  - exit は固定 horizon だけ。
  - stop・条件付き exit・非線形 model・multi-family の合成は、ほぼ無い（合成は #497 の 1 本だけ）。
- **ただし「system としては試していない」は大部分が事実ではない。**
  - Round 1（#464）は、1〜6 日保有の trend / breakout / multi-timeframe を試し、trend と breakout は **gross から負**だった。vol regime・session・ADX の gate、meta-label の gate も試している。
  - Round 2 と momentum の鏡像は、数日の reversal / momentum を 3 span で測った。
  - pre-R1 era（Phase 9〜29、ML Step 4）は、intraday で entry・exit（87 cell）・TP/SL・filter・meta-label・sizing を大量に試した。全て REJECT か INVALID だった（数値の扱いは §2）。
- **本当に未検定で残るのは、狭い帯域である**（§3）:
  - event を**回避する**条件付けの層
  - 学習した regime gating
  - H4 の swing（barrier exit 付き）
  - 日次・断面の非線形の条件付け
  - 確信度に応じた sizing
  - 事前固定の multi-family portfolio
  - tick / quote data を使う執行

**system-level search への転換は妥当か**（前提への 4 つの問いは §4）

- 考え方としては妥当である。弱い情報でも、参加・exit・portfolio で経済性は変わりうる。
- **しかし現在の data・cost・prior の下では、大きな探索を始めても成功する見込みがほとんど無い。**

**算術**（§13）:

- untouched な fresh pool（約 4.8〜4.9 年）で確認できるのは、真の net Sharpe が **約 1.1 以上**の system だけである。
- programme の prior（tier A の縮小推定、μ = 0.07、実効の τ = √(0.55² + 0.13²) ≈ 0.565）の下で:
  - 真の Sharpe ≥ 1.1 の事前確率は **3%**。
  - 真の Sharpe が 1.1 の system が、fresh を使う条件（縮小した期待 Sharpe ≥ 1.0）を通る確率は **約 8〜12%**（fold 外の評価期間 3.4〜4.3 年）。
- τ の点推定（0）を prior にすると、どの候補も縮小後 0.07 になり、**条件は構造的に満たせない**。
- **成功確率は約 1% 以下**（§13 で導出）。第 1 稿の「約 1 割」は導出が無く、撤回する。

**最大の新しい opportunity**: 上に挙げた未検定の狭い帯域と、制約そのものを変える選択肢（§34）。

- **D: data**（tick・broker の financing / 約定）
- **E: 市場の breadth**（OANDA の CFD）

**最大の overfit risk**

- seen data（intraday の全 window が既に何度も使われている）の上の自由探索。
- 雑音の上に meta-model が作る見かけの edge。
- 事後の filter / regime による救済。

**推奨 architecture**: **S0-G（Stage 0 で関門を置く設計）**。

- **すぐに大きな探索をしない。** まず signal を使わない安い **Stage 0** で、次の 4 つを事前の合格線と比べる。
  1. 実測の cost drag
  2. 選択 pipeline 全体の帰無での誤合格率
  3. 確認の到達可能性
  4. 保護 data の汚染台帳
- 合格したときだけ、絞った B′（balanced）へ進む。
- 不合格なら、D（data）・E（CFD の breadth）・hold のどれかを Human が選ぶ。

**first cycle の概要**（§36）

- **cycle 0 = Stage 0**（alpha なし）。
- **cycle 1 = 絞った B′**（Stage 0 合格が条件）:
  - 4 family + portfolio 層
  - 試行は §23 の単一の式で数えて最大 600
  - discovery は seen の intraday span 全体（2021-04-26 … 2025-12-28）の purged walk-forward
  - 内部 holdout は置かない（untouched な seen window が無いため）
- Red の承認は段階ごとに別にする（§24）。

## 2. What The Old Programme Actually Tested

**post-R1（EXPECTED_RETURN_SOURCE_DISCOVERY、#464〜#497）**

- evidence ledger は 278 行、32 mechanism。
- tier A の TC-net の縮小平均は μ̂ = +0.07（素朴平均は −0.175）。
- null を超えた経済的な正は 0 本。
- #497 の judged net（carry の受取込み）は label 置換の帰無を超えた。しかし中身は 2000–07 の短 JPY carry で、2008–16 の Sharpe は −0.07 だった。

**intraday の窓**: 2021-04-26 … 2025-12-28 の 3 window は、**どれも複数の cycle の決定 panel**として使われた。

- ledger の 278 行のうち 112 行が 2021-04 … 2023-04 と重なる（17 PR）。
- 2023-04-26 … 2025-12-28 と重なるのは 150 行（再監査の数え方）。

**pre-R1 era**: `m15_minimum_research_gate.md` の C-8（Ruling 13）により、fenced な legacy route の数値は design の根拠・prior・baseline に使えない。この文書では、それらを**定性的な文脈としてだけ**示す。

| 項目 | 出所 | 状態 |
| --- | --- | --- |
| Phase 24 の exit 87 cell 全 REJECT、spread / ATR（M1 約 128%、M5 約 50%、M15 約 32%） | `docs/design/trading_logic_profitability_research_audit_fable5.md` | 文脈のみ |
| B Rule（+180 pip/年、Sharpe +0.082） | `docs/design/phase22_0z_results_summary.md` | **Phase 22 の定義の Sharpe で、年率の値とは比べられない**。文脈のみ |
| ML Step 4 −3.49 pips/trade（20 pair 全て負） | ML Step 4 の audit 群 | bid / ask の約定後・slippage 前でも負。文脈のみ |
| Phase 9 の「clean baseline Sharpe −0.19」 | 未 merge の branch の M1_V2 の値 | **撤回済み。この文書では使わない** |

## 3. What It Did Not Test

監査の分類（主要部分）。**「signal として試した」と「system として試した」を分けて書く。**

| 要素 | 分類 |
| --- | --- |
| 条件付き参加（no-trade filter） | intraday と 1〜6 日（Round 1 の gate）は EXTENSIVE、日次は PARTIAL |
| regime switching | 決定論的な分割は PARTIAL。**学習した gating（mixture of experts・HMM）は UNTESTED** |
| entry timing | intraday と 1〜6 日は EXTENSIVE。**H4〜日次の system としては BARELY** |
| exit policy | intraday は EXTENSIVE（pre-R1）。post-R1 は固定 horizon だけ。**multi-day の barrier exit は BARELY** |
| 非対称 payoff / stop / TP / trailing | intraday は EXTENSIVE か PARTIAL。**multi-day では UNTESTED** |
| time stop・動的な保有期間 | PARTIAL / BARELY |
| vol / session / spread 条件 | intraday と 1〜6 日は EXTENSIVE |
| cross-pair state | 特徴量としては EXTENSIVE（負） |
| cross-asset context | signal としては PARTIAL。**条件付けの層としては BARELY** |
| event context | signal としては EXTENSIVE（支持されず）。**回避の層としては UNTESTED** |
| trade ranking / top-K | EXTENSIVE（負） |
| take / skip meta-labeling | PARTIAL（base が負の上でだけ） |
| 動的 sizing | PARTIAL（vol target だけ。確信度 sizing は UNTESTED） |
| 執行を意識した判断 / passive 執行 | PARTIAL（bar の simulation だけ。tick では UNTESTED） |
| portfolio 単位の選択・ensemble | BARELY（#497 の 1 本） |
| 非線形の条件付き model | intraday は EXTENSIVE。**日次・断面は UNTESTED** |
| resolution | M1 / M5 / M15 は EXTENSIVE、H1 は PARTIAL、**H4 は UNTESTED**（Round 1 の 1〜6 日保有は M15 の decision） |

**rename リスクが高いもの**（新しく見えて既に試したもの）:

- 活動量 / 機会の gate
- hurdle 確率の take / skip
- regime の特徴量
- cost を意識した target
- session の routing
- 通貨の強弱 ranking
- 賢い exit（intraday）
- top-K
- limit 注文による cost 削減
- multi-timeframe 確認
- **1〜6 日の trend / breakout**（Round 1）

## 4. Why Profitable Trading System Discovery Is Different — と、前提への 4 つの問い

**違い**

- 問いが「情報が return を予測するか」から、「情報 × 状態 × 参加 × entry × exit × sizing × 執行 × portfolio が retail の net で残るか」に変わる。
- ただし **policy は情報を作らない**。
  - filter・exit・sizing が利益を上げるのは、予測可能な条件付き構造を使うときだけである。
  - それ自体が一種の signal で、同じ検出力の制約を受ける。自由度が多い分、偶然も多い。

**前提への 4 つの問い**（裁定 §3）

1. **方向転換は合理的か**
   - 考え方としては合理的。
   - しかし「未探索の広い空間がある」という前提は、監査で**大部分が否定された**。残るのは狭い帯域である。
2. **名前だけ変えた再探索の危険はあるか**
   - **高い。** 1〜6 日の trend / breakout・gate・meta-label・session・vol 条件は Round 1 と pre-R1 で試した。
   - family ごとに rename 台帳（§25）を必須にする。
3. **自由度を増やすと overfit factory になるか**
   - **なる。**
   - 偶然の最良は、4.7 年の span でも実効 100 試行で Sharpe 1.15、1,000 試行で 1.5 になる。fold 外の評価期間はさらに短い（§13）。
   - 手元の seen data は全て複数回使われていて、内部の untouched な window は無い。
4. **危険を制御しながら、standalone では拾えない edge を探せるか**
   - 探索の自由度を小さく保ち、選択 pipeline 全体を帰無で較正し、確認を 1 回にすれば、統制はできる。
   - ただし**統制できることと、見つかることは別である**。現在の prior では、見つかって確認まで通る確率は 約 1% 以下である。
   - だから、先に安い Stage 0 で「探す価値があるか」を測る。

## 5. Trading System Design Space

裁定の 10 軸は妥当である。研究の単位として、次の 6 層に整理する。

| 層 | 中身 | 自由度の数え方 |
| --- | --- | --- |
| L1 candidate generator | 情報 + 方向 + entry の規則 | family ごとの事前宣言の template |
| L2 participation | 状態・regime・event・cost による take / skip | 規則か ML。**1 つの L2 も 1 試行として数える** |
| L3 exit | 固定 horizon / time stop / ATR 対称 barrier / 非対称 barrier / trailing | 事前固定の template。**全ての template に最大保有期間の上限を付ける** |
| L4 sizing | 等リスク / vol target / 上限付きの確信度 sizing | 3 択 |
| L5 execution | 成行（bid / ask）/ spread 条件の見送り | bar data で測れない passive は扱わない（裁定 §26） |
| L6 portfolio | 事前固定の合成 | 等リスクか事前ルール |

horizon は独立の軸にしない（exit と generator の結果として決まる）。horizon の探索を禁じるためである。

## 6. System Archetype Inventory

| family | edge の源 | horizon | data | retail の実行可能性 | cost 感応度 | turnover | 標本効率 | overfit | engineering | repo の prior |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A 条件付き trend / breakout | 情報の遅い拡散 | H4〜数週 | M15 BA → H4 / D | 高 | 中 | 中 | 中 | 中 | 小 | 1〜6 日は Round 1 で gross 負。月次 TSMOM は検出力不足。**rename リスク高** |
| B 条件付き短期 mean reversion | 流動性供給 | H1〜1 日 | M15 BA | 高 | **高** | 高 | 高 | 高 | 小 | 数日の reversal は null と区別できない。**rename リスク高** |
| C 断面 / relative value | 相対の割安・勢い | 日〜月 | D | 高 | 低〜中 | 低 | **低** | 中 | 小 | #497・T-V で測定済み。非線形の条件付けだけ未検定 |
| D cross-pair lead-lag | 情報伝播の遅れ | 分〜時間 | tick | 低 | 非常に高 | 非常に高 | 高 | 高 | 大 | tick が無い |
| E clock / flow の構造（fix・月末） | 機械的な hedging / rebalance | H1 | M15 BA | 高 | 中 | 低（月末は年 12 回） | **低** | 中 | 小 | session filter は測定済み。flow の signal は未検定 |
| F vol 状態 | vol premium・圧縮後の拡大 | H4〜日 | M15 BA | 高 | 中 | 中 | 中 | 中 | 小 | ATR gate は breadth だけ。状態の遷移は未検定 |
| G event 条件 | 吸収・回避 | H1〜日 | calendar（一部の通貨） | 高 | 中 | 低 | 低 | 中 | 中 | signal は支持されず。**回避の層は未検定** |
| H carry / trend / value の合成 | 古典的 premia | 月 | D | 高 | 低 | 低 | 低 | 低 | 小 | #497 で測定済み。**再開しない** |
| I meta-labeling | base の条件付き構造 | base に従う | base + 特徴量 | 高 | base に従う | 低下する | 中 | **非常に高** | 中 | base が負の上でだけ試した |
| J 直接の expected net PnL | 条件付き期待 PnL | template | 同上 | 高 | 同上 | 同上 | 中 | 高 | 中 | intraday の EV label は判別力なし |
| K regime 切替（学習） | 状態依存 | 日〜週 | D + macro | 高 | 低 | 低 | **低** | 高 | 中 | 学習 gating は未実行 |
| L 執行を意識 | spread・流動性の時間構造 | 分〜時間 | **tick / quote** | 中 | — | — | 高 | 中 | 大 | data が無い |
| M portfolio-of-strategies | 独立な弱い edge の分散 | 混在 | 各 system | 高 | 低 | 混在 | — | 中 | 小 | 事前固定の合成はほぼ未検定 |
| N 他（週末 gap・rollover の構造・中銀介入の後） | 構造的な歪み | 様々 | M15 BA | 中 | 高 | 低 | 低 | 中 | 小 | rollover hour は cost の地雷としてだけ既知 |

indicator × horizon × 閾値の直積は、別 family にしない。family は edge の源で分ける。

## 7. Signal vs Policy vs Execution

**本物の条件付き edge の条件**

- 条件の変数と規則が、結果の前に経済的な理由で決まっている。
- 条件付きの期待 PnL の差が、fold をまたいで安定している。
- 参加率が下がった分の breadth の損失を、trade あたりの edge の増加が上回る。

**事後 filtering の徴候**

- 結果から選んだ。
- 条件のかけ方の自由度が大きい。
- 残った trade が少なく、fold で符号が揺れる。

**区別の方法**

- filter も 1 試行として ledger に記録する。
- 評価は fold の外だけで行う。
- 同じ参加率のランダムな skip と比べる。
- 選択 pipeline 全体を帰無で較正する（§23）。
- 確認は 1 回だけ。

## 8. ML Roles

| 役割 | merit | 理由 |
| --- | --- | --- |
| A 方向予測 | 低 | 繰り返し失敗 |
| B expected net PnL | 中 | cost と exit を target が含む。ただし target の雑音が大きい |
| C ranking | 中 | B の副産物 |
| D take / skip | 中（条件付き） | base が正の gross を持ち、選択を含む帰無を超えるときだけ |
| E sizing | 低〜中 | tail を増やしやすい |
| F regime 分類 | 中 | 学習 gating は未検定。ただし regime の標本は少ない |
| G exit | 低〜中 | template から選ぶ方が安全 |
| H 執行 | 低（今は） | tick が無い |
| I 配分 | 低 | 最適化は過学習する |

**cycle 1 で許すのは D と B だけ**（base が正の family に限る）。

## 9. Target Design

- **使う target**:
  - 事前固定の exit template（全て最大保有期間の上限付き）で持ったときの、bid / ask 約定の realized net R
  - barrier の結果
  - P(net > 0)
- **使わない target**: 次の bar の方向、MFE / MAE の単独予測。
- target は family ごとに最大 2。**target の変更も試行として数える。**

## 10. Discovery Architecture

**裁定の 4 段階案への修正**

1. **Phase 0（Stage 0）を先頭に置く。** signal を使わない測定で「探す価値があるか」を先に決める。
2. **内部 holdout は置かない。**
   - 2021-04 … 2023-04 は、複数の cycle の**決定 panel**だった（ledger で 112 行）。
   - そのうえ 2022 年の USD の強い trend は一般常識として既知である。
   - それを選択の gate にしても、既知の結果を当て直すだけになる（第 1 稿の誤り）。
   - 代わりに、seen の intraday span 全体の purged walk-forward と、選択 pipeline 全体の帰無較正を使う。
3. **confirmability gate** を、fresh の前に置く（§13）。

| phase | data | 目的 | 統計の役割 |
| --- | --- | --- | --- |
| 0 Stage 0 | seen の cache（cost の統計だけ）と合成 data | cost drag・pipeline の誤合格率・到達可能性・汚染台帳 | 事前の合格線 |
| 1 Discovery | seen intraday 2021-04-26 … 2025-12-28（4.68 年） | 探索 | p ≤ 0.05 を要求しない。全試行を記録 |
| 2 Robustness / selection | 同じ span の purged WF の fold の外 | 近傍・fold・pair・cost・ablation・baseline | deflated Sharpe・較正した pipeline の閾値 |
| 3 Lock | — | 全てを凍結 | digest・INTENT・STARTED |
| 3b Confirmability | — | 縮小した期待 Sharpe と fresh の検出力 | G4 |
| 4 Confirmation | fresh pool（Red） | 1 つの portfolio を 1 回 | 片側の検定 |
| 5 Forward / paper | 未来 data（Red、broker 認証） | 運用・執行・financing の実測 | 補助。長期では事後分布の更新 |

**warm-up と境界**:

- discovery の最初の 100 営業日（2021-04-26 から）は、特徴量の warm-up だけに使い、評価しない。
- **2021-04-26 より前の行は、warm-up でも読まない**（fresh pool の保護）。
- **上端**: 全ての exit は最大 20 営業日保有するので、2025-12-28 の 20 営業日前より後には entry しない。持っている position は 2025-12-28 の最後の bar で強制決済する。
  - それより後の timestamp（historical OOS slice）を読もうとしたら、guard が拒否する。
  - R1 では window の 1 行先を decode して「読み取り」と裁定された。この guard は test で固定する。
- guard は parsed date で比較し、厳密な YYYY-MM-DD だけを受ける。

**fold 外の評価期間**: 4.68 年から warm-up（約 0.4 年）と、anchored walk-forward の最初の学習 block（約 1 年）を除くと、**約 3.4 年**になる。§13 の G4 の計算はこの長さを使う。

## 11. Robustness Architecture

- **temporal**: purged walk-forward（anchored、四半期の fold、最大保有期間で purge、embargo も最大保有期間）。
- **parameter**: 近傍の中央値で評価する（§23）。
- **breadth**: pair 別・通貨別。
- **regime**: 事前定義（§28）。
- **cost**: stress ×1.5 / ×2、rollover hour を除外。
- **ablation**: 各層の寄与を分ける。
- **baseline**: §36 の一覧（裁定 §47）。

## 12. Validation Architecture

- **CV は新しい data を作らない。**
  - purged walk-forward は、model 選択の risk を減らす道具である。
  - この span は programme 全体で何度も見ているので、fold の外の成績も「確認」ではない。
- **confirmation**: fresh（1 回）と、forward の蓄積だけ。

## 13. Protected Data Strategy

**算術**（signal を使わない）

**確認できる真の Sharpe**

| untouched の長さ | 確認できる真の Sharpe |
| --- | ---: |
| 1 年 | 2.49 |
| 2 年 | 1.76 |
| fresh 4.79〜4.9 年 | **1.12〜1.14** |
| fresh + 36 か月の forward（7.9 年） | 0.88 |

**偶然の最良 Sharpe**（実効の試行数 N、SE × E[max]）

| discovery の長さ | N=10 | N=30 | N=100 | N=300 | N=1,000 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3.4 年（fold 外） | 0.84 | 1.11 | 1.36 | 1.55 | 1.75 |
| 4.7 年 | 0.71 | 0.94 | 1.15 | 1.32 | 1.49 |

**fresh 4.9 年での検出力**

| 真の Sharpe | 0.5 | 0.8 | 1.0 | 1.3 | 1.5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 検出力 | 0.30 | 0.55 | 0.72 | 0.89 | 0.95 |

**G4 の到達可能性**

**事前に凍結する prior**:

- μ = 0.07。
- 実効の τ = √(0.55² + 0.13²) ≈ 0.565。#496 の tier A の τ の上限に、μ̂ の SE（0.13）を足したもので、最も楽観的な値である。
- **参照クラスの不一致を開示する**:
  - この prior は、6 本の standalone な tier A mechanism から作った。一方、それを当てるのは、選択された multi-system の portfolio である。
  - しかも、その mechanism の span は discovery の data と重なっている（同じ data の二重使用）。

**縮小の手順**:

1. 観測 Sharpe を、実効試行数で deflate する。
2. deflate した値を、fold 外の評価期間（約 3.4 年、§10）の SE で縮小する。

**縮小後 ≥ 1.0 に必要な観測 Sharpe**（deflate の後）:

| fold 外の期間 | 重み | 必要な観測 Sharpe |
| --- | ---: | ---: |
| 3.4 年 | 0.52 | **1.86** |
| 4.28 年 | 0.58 | 1.68 |

**G4 を通る確率**（3.4 年）:

| 真の Sharpe | 0.8 | 1.1 | 1.5 | 2.0 |
| --- | ---: | ---: | ---: | ---: |
| G4 通過の確率 | 0.03 | 0.08 | 0.26 | 0.60 |

**成功確率の導出**:

- G4 を通る周辺確率（prior と観測の雑音を合わせた N(0.07, √(0.565² + 0.542²)) が 1.86 を超える確率）は **0.011**（4.28 年なら 0.015）。
- これに fresh の検出力 0.72 を掛けると **約 0.8〜1.1%**。
- 選択の deflation を入れると、さらに下がる。
- よって **成功確率は約 1% 以下**である。
- prior の下で、真の Sharpe ≥ 1.1 の確率は 0.03、≥ 0.8 の確率は 0.09。

**注意**:

- **τ の点推定 0 を使うと、縮小後は常に 0.07 になり、G4 は構造的に到達できない。**
- **in-cycle の family 内分散を prior に使うことは禁止する**（選択 bias で τ が膨らむ）。
- **S0-3（真の Sharpe 1.5 の G4 通過確率 ≥ 0.3）は、3.4 年では 0.26 なので、構成上不合格になる見込みが高い。** そう予想したうえで、Stage 0 を置く（§35）。

**fresh pool の使い方**

fresh（2016-06-02 … 2021-04-25、archive に M1〜D の bid / ask、未読）は、programme で最も価値のある単一の資源である。

| 案 | 評価 |
| --- | --- |
| system 選択の gate | 却下 |
| 分割して選択と確認 | 却下（各 2.45 年では確認できる Sharpe が 1.6） |
| **凍結した 1 portfolio の確認（1 回）** | 推奨 |
| forward を確認の主役にする | 却下（12 か月で確認できる Sharpe は 2.5） |

- **G4 を満たさなければ fresh は使わない。**
- 真の Sharpe 0.8〜1.0 の system は、fresh だけでは確認できない。確認するには「fresh + 36 か月の forward」を合わせるしかない（確認できる Sharpe 0.88）。

**汚染台帳**（Stage 0 で作る）

- #472 は 2019-01 からの ALFRED の vintage と COT を読んだ。
- #471 は 2020-06 からの BIS 金利を使った。
- #494 は CPI の分母で 2020 年の水準が逆算可能になった。D-M3 もある。
- 一般常識として既知の出来事: Brexit 2016-06-23、COVID 2020-03。
- pre-R1 の `*_1825d_BA` の取得（Phase 9 の時期）が、fresh の末尾と重なる可能性がある（未確認）。
- **F4（event）の event list は、fresh の時期の event を見ずに凍結する。**
- historical OOS slice は pristine の主張が撤回済みなので、使わない。dead window も使わない。

## 14. Fresh / Forward Strategy

**forward**

- forward epoch（2026-04-25 以降）は未読で、`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS` である。
- archive の README によれば、OANDA practice の API access は 2026-05-31 に tier の格下げで失効する予定だった。**forward の蓄積には broker の再接続（Red）が要る。**

**新しい未来 holdout**（裁定 §16）

- 凍結日の翌営業日から、append-only の forward epoch を封印して始める。
- その期間の data は、確認の前には読まない。
- 蓄積は paper の運用で行い、日次の P&L・spread・約定・financing を hash chain の ledger に書く。
- 期間ごとの役割:

| 期間 | 役割 |
| --- | --- |
| 6 か月 | 運用・執行の整合性 |
| 12 か月 | Sharpe 2.5 以上でなければ統計的な情報はほぼ無い |
| 24 か月 | fresh と合わせて、事後 SD が約 16% 縮む |
| 36 か月 | 約 21% 縮む。確認できる Sharpe は 0.88 |

## 15. Data Resolution Strategy

| 解像度 | cost / ATR | 位置づけ |
| --- | --- | --- |
| M1 / M5 | 高い（文脈のみ、§2） | 中心にしない |
| M15 | 約 32%（文脈のみ） | **cost を測る基礎**（bid / ask） |
| H1 / H4 | **未測定**（第 1 稿の 10〜15% は √t の推定にすぎない） | Stage 0 で実測する |
| D | 小 | 日次 family・portfolio |

- 「H1 / H4 で決め、M15 の bid / ask で約定の cost を測る」を採る。
- M1 執行の multi-resolution は採らない。M1 の OHLC では執行の優位を測れず、pre-R1 でも失敗した。

## 16. Existing Infrastructure Reuse

| 資産 | 用途 |
| --- | --- |
| M15 bid / ask cache（20 pair、2021-04-26 … 2025-12-28、seen） | discovery と Stage 0 |
| OANDA 10 年 archive（2016-06-02 … 2026-05-29、120 file、hash manifest） | fresh の確認 |
| ECB 長 span | mid だけなので、日次の診断に限る |
| cost model（pair round trip 2.58 bp、rollover の実測）・Track 3 の約定 simulator | cost と執行 |
| portfolio の construction・null framework・effective sample と feasibility の算術 | 構成・帰無・検出力 |
| 保護暦日の guard（parsed date・request 側の除外・audit hook） | 保護 data |
| 凍結 digest・閉包・2 段階実行・hash chain の ledger（#497） | provenance |
| programme の evidence ledger（278 行） | prior |
| 独立 review の運用 | review |
| live / paper stack（src/ の broker adapter・exit gate・risk manager） | paper の段階 |

## 17. Missing Data

| data | 無料 / 有料 | 情報利得 | 標本利得 | 期待効果 |
| --- | --- | --- | --- | --- |
| tick / quote の履歴 | 無料源あり（Dukascopy・TrueFX。ToS の確認が要る） | 高 | 高 | 執行層と spread の時間構造 |
| 実際の broker financing・spread・約定 | 認証（OANDA） | **高** | — | full retail net |
| 板・signed flow | 有料 / 不可 | 中〜高 | 高 | 短期 family |
| news の timestamp | 有料 | 中 | 中 | event family |
| 非 USD の時刻付き calendar | 一部無料 | 中 | 中 | event family |
| FX options（implied vol・risk reversal） | 有料 | 中〜高 | 低 | regime・tail の条件付け |
| cross-asset の価格（日次は一部無料） | — | 中 | 中 | 条件付け層 |
| OANDA の CFD（指数・商品）の価格 | broker / 無料源あり | **breadth が 3〜4 倍** | 高 | E 案 |

## 18. Paid Data Opportunities

有料 data を禁忌にはしない。**順位**:

1. tick 品質の data（無料で足りなければ）
2. options
3. news の timestamp

**条件**（旧 P1〜P5 を継承）: 具体的な仮説・検出力・point-in-time・保護期間を request で除外できること・費用対効果・Human の承認。

## 19. Broker Data Opportunities

OANDA の認証付き access で得られるもの:

- **実際の financing**: #495・#497 で結論を左右した唯一の変数。
- spread・約定・slippage・口座履歴。

**discovery には不要で、paper の開始時に要る。** 判断は Human に上げる（§43）。

## 20. Cost / Financing Architecture

**gross / TC-net / judged / full retail net（UNKNOWN）を常に並べる。**

- **TC-net**: M15 の bid / ask 約定、rollover hour を除外、stress ×1.5 / ×2。
- **financing**: 近似で、markup **1% を保守側の既定**にする。#497 で 0.5% の仮定の脆さが分かったため。

## 21. Risk Architecture

risk 管理は、弱い alpha を救う装置ではない。

- vol target・exposure / 相関の上限・事前固定の risk budget は研究対象にしてよい。
- drawdown governor は ablation として示し、**governor で正になる system は不合格**にする。

## 22. Portfolio Architecture

| 区分 | 条件 |
| --- | --- |
| research candidate | 単体の縮小 net Sharpe > 0、fold の外で安定、既存 portfolio への限界寄与が正 |
| production candidate | portfolio 全体が business threshold を満たす（§41） |

**限界寄与**: 採用で portfolio の Sharpe が上がるのは S_i > ρ_{i,P} × S_P のとき。

- S_i は縮小値、ρ は fold の外の return で推定する。
- 雑音の system は S_i ≈ 0 なので、低相関でも通らない。
- 合成は事前固定の等リスクで行い、最適化しない。

## 23. Anti-Overfit Framework

1. **試行の数え方**（単一の式）: 1 試行 = 評価した 1 つの (generator の設定, exit, target, L2 filter, model の hyperparameter, top-k) の組。
   - 組み合わせは全て掛け算で数える。登録の単位では数えない。
   - LLM の提案、F4 を overlay として使うこと、exit の選択（5 種から事前に選ぶ）も、全て試行に含める。
2. **実効試行数**: fold の外の日次 return の相関を階層 clustering し、相関 0.8 以上を 1 つにまとめる（方法は事前固定）。
3. **deflated Sharpe**（実効試行数を使う）。
4. **選択 pipeline 全体の帰無較正**（Stage 0）:
   - 選択の全手続き（base の選択・meta-model・filter・近傍評価・hard filter）を、同じ vol と spread の合成 data（符号をランダムにしたものと circular shift）で走らせる。
   - **family-wise の誤合格率が 10% 以下**になるよう閾値を較正する。
   - #490 では、事前登録の gate が帰無で 42% 通った。
5. **近傍の中央値と、事後救済の禁止**（裁定 §23）:
   - parameter の格子は事前に宣言する。
   - 評価は近傍（中心と隣接点）の中央値で行う。
   - 近傍のうち 70% 以上で符号が同じであること（plateau の基準）。
   - **失敗の後に格子を変えて再探索することは禁止。** 変えるなら新しい試行として予算から引き、lineage に記録する。
6. **複雑度 penalty**（§27）。
7. **縮小推定**（§13 の凍結 prior）。
8. **meta-labeling の帰無**:
   - 同じ頻度・同じ exit の random base に、**base の選択も含めて**同じ手続きを適用する。
   - 本物の改善が、その 95 percentile を超えること。
9. **rename 台帳**（§25）。

**ML governance**（裁定 §32）

- temporal CV（random shuffle 禁止）
- 特徴量の timing と label の leakage の監査（合成入力の test で先に確認する）
- pipeline の leakage（scaler・分位も fold 内で fit する）
- hyperparameter の予算
- early stopping は fold 内の検証部分だけで行う
- 複雑度の上限
- baseline との比較
- ablation
- calibration
- fold の安定性
- 学習した model は、code SHA・data hash・hyperparameter と一緒に registry に記録する

## 24. Multiple-Search Governance

**`autonomous_development_policy.md`（§2a / §6 / §9）と CLAUDE.md が優先する。** 第 1 稿の「cycle 単位の包括承認」は、training・holdout の凍結・評価を 1 つの承認にまとめており、policy と矛盾していたので撤回する。

**Red の承認は段階ごとに別にする**（連鎖させない）:

| 承認 | 範囲 |
| --- | --- |
| R-A | Stage 0 の seen cache の読み取り。**3 つの window の cache と、その 3 つの route（`bars.py`・`supplemental.py`・`momentum.py`）を名指す**。spread と ATR の統計だけを使う。signal と return は突き合わせず、価格の経路で exit を simulate することもしない |
| R-B1 | discovery の読み取りと特徴量の導出（cycle 1）。route・span・pair・timeframe・head を名指す |
| R-B2 | training（R-B1 の後に別承認） |
| R-B3 | fold 外の評価と選択（R-B2 の後に別承認） |
| R-C | finalist と portfolio の凍結 |
| R-D | fresh の使用（1 回） |
| R-E | broker 認証・paper |
| R-F | 有料 data |
| R-G | 市場の変更 |
| R-H | production |

- **cycle 内の自律**: 各承認（R-B1 / R-B2 / R-B3）の範囲の中の実験の追加は、ledger への事前登録だけでよい。ただし予算の上限を超えない。
- **段階をまたいで自動で連鎖させない**: 読み取り → training → 評価は、それぞれ別の承認を要する。
- **予算の上限に達したら終わる**（延長は Human の判断）。

## 25. Experiment Ledger

append-only の JSONL で、hash chain にする（#497 の ledger を一般化）。**各実験は結果を見る前に登録する。**

| field | 中身 |
| --- | --- |
| experiment_id / parent | S001 → S001a の系譜 |
| lineage_reason | human hypothesis / template / result-informed / LLM-proposed |
| rationale | なぜこの実験をするか |
| family | 所属 family |
| **rename_check** | 過去の同型（§3 の表）との差。書けなければ登録しない |
| code_sha / data_hash / span | provenance |
| features / target / params / grid_points / exit_templates / l2_filters | 試行の中身 |
| model / hp_trials | model |
| trial_count | 格子点 × exit × target × filter |
| complexity | 複雑度（§27） |
| result_summary / decision | 結果と判定 |
| **informed_by** | 設計に影響した過去の結果の ID |

deflated Sharpe の試行数は、ledger の trial_count の合計（と実効試行数）から出す。

## 26. Search Lineage と Strategy Generation

**系譜**: S001 → S001a → S001b。

- 結果の後に派生したものは `informed_by` が空でない。「最初から思いついていた」ことにしない。
- 系譜の深さは複雑度に足す。

**候補の作り方の比較**（裁定 §37）

| 方法 | 評価 |
| --- | --- |
| A 人の経済仮説 | **主** |
| B template 探索 | 事前宣言の小さな格子に限って可 |
| C ML による signal 発見 | 使わない（方向予測は失敗） |
| D 記号 / 遺伝的探索 | 使わない（試行が爆発する） |
| E LLM 支援 | 次の governance の下で、**仮説の提案だけ** |

**LLM の governance**

- 結果を見せずに、batch で提案させる。
- 提案は全て ledger に登録する（`LLM-proposed`）。
- 試行として予算から引く。
- family と rename_check を必須にする。
- **結果を見て再生成させることは、1 世代ごとに新しい試行として数える。**
- 世代の上限は cycle で 2 回。

## 27. Complexity Penalty

実効自由度 k の数え方:

- data で選んだ parameter の数
- 特徴量の数
- 条件分岐の数
- 系譜の深さ
- log2（hyperparameter の試行数）
- tree model: log2（葉の数 × 木の数）

| tier | k | 要求 |
| --- | --- | --- |
| S | ≤ 5 | 標準 |
| M | 6〜15 | 縮小 Sharpe に +0.2 の上乗せ |
| L | > 15 | +0.4 の上乗せ |

## 28. Temporal Validation

**事前宣言の分割**（discovery span の中に限る）:

- 暦年（2021〜2025）
- 四半期の fold
- vol の regime: trailing 60 日の実現 vol を、point-in-time の expanding window の分位で三分位に分ける
- 固定の暦の区切り: **2022-03-16（Fed の利上げ開始）と 2024-09-18（利下げ開始）**。どちらも公表日で、結果の前に固定する。

**要求**: fold の 60% 以上で正、最悪の fold が −1 SE を下回らない。

## 29. Pair / Currency Validation

- 通貨全体の mechanism と主張するには、正の pair が 60% 以上であること。
- pair 固有の edge は、事前に宣言した場合に限り認める。容量・broker 依存性・標本の小ささで penalty を付ける。

## 30. Tail / Ruin Validation と EA の anti-pattern

**必須の診断**

- 最悪の日 / 週 / 月、CVaR 1%
- 含み損と position の大きさの相関（> 0 は martingale の疑い）
- ナンピンの add の有無
- leverage の経路
- gap shock（最大 position に 1 日 20%）・週末 gap・rollover hour
- block bootstrap による DD 30% の確率

**不合格**: grid / martingale / ナンピン / short-vol の tail 収穫の構造が検出されたら、Sharpe に関係なく不合格。

**EA の anti-pattern**（programme として禁止する。裁定 §46）:

- backtest 期間の選り好み
- broker の選り好み
- parameter mining（tester の過最適化）
- 隠れた martingale / ナンピン
- 非現実的な spread（固定 spread・demo の約定）
- 曲線当てはめ
- survivorship bias
- news straddle
- demo の約定を前提にした scalping
- broker 固有の癖への依存
- 結果の悪い期間を「異常期間」として除外すること

## 31. Candidate Selection

**目的関数**（backtest Sharpe の最大化は禁止）

> U = median_fold(縮小 net Sharpe) − 1.0 × fold 間の SD − 0.5 × cost ×1.5 での低下 − tier penalty（0 / 0.2 / 0.4）− 0.3 × 集中度

あわせて Pareto front（U・breadth・tail）を報告する。

**hard filter**（閾値は Stage 0 の pipeline 帰無で較正する）

- TC-net > 0（cost ×1.5 でも）
- 近傍の plateau
- deflated Sharpe
- tail の検査
- baseline に margin 付きで勝つ（§36）

finalist は最大 3。

**p-value の扱い**（裁定 §49）

- discovery では、p-value で candidate を殺さない。
- 効果量・安定性・net の経済性・portfolio への価値・複雑度・不確実性を総合する。
- 不確実性は、deflated Sharpe と縮小推定で数値として持つ。
- p-value で判定するのは、**fresh の確認（片側 5%）だけ**。

**Bayesian / 縮小**（裁定 §50・§51）

- prior は §13 の凍結値（μ = 0.07、τ = 0.55）。family 内で推定した分散は使わない。
- candidate の score は、縮小した期待値を中心に置く。
- 恣意的な掛け算の score（裁定 §51 の例）は使わず、U と hard filter に分けて持つ。

## 32. Candidate Promotion Gates / Champion–Challenger / Evaluation Hierarchy

**評価の階層**（裁定 §48 を修正）

| 段階 | 中身 |
| --- | --- |
| L0 | 機械的な正しさ（合成入力での exposure・timing の test） |
| L1 | gross の情報 |
| L2 | TC-net |
| L3 | judged（financing） |
| L4 | temporal / pair / parameter の頑健性と tail |
| L5 | portfolio への限界寄与 |
| L6 | pipeline の帰無を超えるか（deflated） |
| L7 | confirmability（G4） |
| L8 | fresh の確認 |
| L9 | paper（運用・執行） |
| L10 | production |

旧案の「L6 untouched confirmation」の前に、帰無の較正と到達可能性を置いた。

**gate**

| gate | 条件 |
| --- | --- |
| G1 challenger | hard filter と、U の上位 |
| G2 frozen challenger | 全層を凍結（R-C） |
| G3 portfolio | finalist の事前固定の合成 |
| G4 confirmability | portfolio の縮小期待 Sharpe ≥ 1.0（fresh の検出力 ≥ 0.72） |
| G5 fresh | 片側 5% で有意、かつ net > 0（R-D） |
| G6 paper | 6 か月以上（R-E） |
| G7 production | R-H |

**champion / challenger**

- **champion** = 現在 production（または paper）で動いている凍結 portfolio。**現在は無い。**
- **challenger** が champion を置き換えるのは、次の 3 つが揃ったときだけ。
  1. 同じ gate（G1〜G6）を通る。
  2. paper で champion との差の事後確率 ≥ 0.8。
  3. 置き換えの cost（運用の変更）を上回る。

## 33. Paper / Production Roadmap

**paper は統計的な確認ではない。** 次の検証である:

- integration
- live data の timing
- 実際の spread・約定・financing の実測
- 運用の安定性

**production の gate**:

- paper が 6 か月以上、trade が 100 以上
- DD が backtest の 95 percentile 以内
- 執行の乖離が cost の 25% 以内
- drift の監視
- kill switch（DD 10%）
- capital ramp（10% → 25% → 50% → 100%）

**今回は実装しない。**

## 34. Programme Alternatives

| 案 | 中身 |
| --- | --- |
| **H hold** | 新 programme も始めない。`LONG_TERM_HOLD` を続ける |
| **A conservative** | 人が設計した 4 family の規則だけ。ML なし。試行は最大 300 |
| **B′ balanced（絞った版）** | 4 family + 事前固定の exit + ML は take / skip と expected net PnL（線形と浅い GBM）+ 事前固定の portfolio。試行は最大 600 |
| **C aggressive** | 自動探索・LLM の大量生成・深い model・RL。数千〜数万 |
| **D data-first** | tick と broker data（financing・約定）を先に集め、cost と執行の構造を測る |
| **E breadth-first** | OANDA の CFD（指数・商品・債券）を加え、breadth を 3〜4 倍にする |
| **S0-G（推奨）** | Stage 0（signal を使わない測定）を先に行い、合格なら B′、不合格なら D / E / H を Human が選ぶ |

**比較**

| 観点 | H | A | B′ | C | D | E | S0-G |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 本物の edge を見つける確率 | 0 | 非常に低 | 非常に低（約 1%） | 見かけだけ高い | 単独では 0（前提を作る） | 未知（制約を直接変える） | B′ と同じだが、無駄打ちを避ける |
| overfit risk | なし | 低 | 中 | **非常に高** | 低 | 中 | 低〜中 |
| compute | なし | 小 | 中 | 大 | 小 | 中 | 小 → 中 |
| engineering | なし | 小 | 中 | 大 | 中 | **大**（保護 data・cost・financing の作り直し） | 小 → 中 |
| data の要件 | なし | 既存 | 既存 | 既存 | 新規（Red） | 新規（Red） | 既存 → 判断 |
| 結果までの時間 | — | 短 | 中 | 長 | 長 | 長 | 短 → 中 |
| 解釈性 | — | 高 | 中 | 低 | 高 | 中 | 高 |
| 頑健性 | — | 中 | 中 | 低 | — | — | 中 |
| 現在の repo との相性 | — | 高 | 高 | 低 | 中 | 低 | 高 |
| fresh の効率 | 保存 | 1 回 | 1 回 | 実質使えない | 保存 | 新しい市場には別の fresh が要る | 保存（G4 まで） |
| retail での実行可能性 | — | 高 | 高 | 低 | 高 | 高 | 高 |

- **C は §13 の算術で否定される。**
- RL は、sample 効率・simulator の誤差・reward hacking・cost 感応度のどれも不利なので、入れない（裁定 §34）。
- **model family**（裁定 §33）:
  - cycle 1 で許すのは logistic / ridge / elastic net と LightGBM（深さ ≤ 4、木 ≤ 200）だけ。
  - HMM は regime の診断に限る。
  - XGBoost は LightGBM と重複するので入れない。
  - 浅い NN・sequence・Transformer は入れない（標本に対して自由度が大きすぎる）。

## 35. Recommended Architecture

**S0-G。**

**理由**

1. §13 の算術で、B′ をすぐ始めても成功確率は約 1% 以下で、期待される結果は「Human へ戻る」である。
2. Stage 0 は安く、signal を使わず、fresh も消費しない。そのうえで、B′ が構造的に不可能かどうか（cost drag・pipeline の誤合格率・G4 の到達可能性）を決められる。
3. B′ が不可能と分かれば、制約そのものを変える D / E か、H を、証拠に基づいて選べる。
4. **正直な予想**: S0-3 は §13 の算術で不合格になる見込みが高い（0.26 < 0.3）。
   - したがって S0-G の最も起きやすい帰結は、「Stage 0 が B′ の不可能性を実測で確かめ、D / E / H の判断を Human に返す」である。
   - それでも Stage 0 を置くのは、S0-1 の実測の cost drag と、S0-2 の較正した誤合格率が、D / E の設計にもそのまま使える情報だからである。
   - それに、仮定ではなく実測で B′ を閉じられる。

**Stage 0 の中身と合格線**（結果の前に固定する）:

| 項目 | 中身 | 合格線 |
| --- | --- | --- |
| S0-1 cost drag の実測 | seen の M15 bid / ask から、pair × H1 / H4 / D ごとの spread と ATR の分布を測る。想定の turnover（template ごとに事前固定）の下で、round trip cost を ATR 単位と Sharpe 単位（vol 8%）で出す。**価格の経路で barrier / trailing の exit を simulate しない。signal と return は突き合わせない** | H4 の標準の想定で、net Sharpe 1.0 に要る gross Sharpe ≤ 1.5 |
| S0-2 pipeline の帰無較正 | 選択の全手続きを合成 data で 200 回以上走らせる。合成 data は符号ランダムと circular shift で作り、vol と spread の parameter は seen data から取る（その旨を開示する） | 閾値を調整したうえで family-wise の誤合格率 ≤ 10%。かつ、その閾値での G4 到達可能性が次の S0-3 を満たす |
| S0-3 G4 の到達可能性 | 凍結 prior と較正した閾値、fold 外の評価期間（約 3.4 年）の下で、真の Sharpe 1.5 の system が G4 を通る確率 | ≥ 0.3（**§13 の算術では 0.26 で、構成上不合格の見込みが高い**） |
| S0-4 汚染台帳 | fresh の汚染台帳を作り、pre-R1 の 1825d の取得の重なりを確認する | 重なりがあれば、その区間を確認から除外する設計にする |
| S0-5 rename 台帳 | 各 family の過去の同型との差 | 差を書けない family を除外する |

**meta-labeling と expected net PnL**（裁定 §35・§36）

- 利点: cost・exit・spread を target が含む。方向を当てる必要が無い。
- 欠点: target の雑音が大きい。exit template に依存する。小さな正の予測が並ぶと、cost の誤差で負に転じる。
- 対策:
  - base が正の family に限る。
  - 選択を含む random base の帰無を置く。
  - 上位 k%（事前固定の 3 点）だけを取る。
  - 予測の calibration を fold の外で確認する。
  - cost ×1.5 の stress をかける。

## 36. First Cycle Detailed Design（実行しない）

### cycle 0: `PATSD_STAGE_0_FEASIBILITY`（alpha なし）

- **data**: seen の M15 bid / ask cache（20 pair、2021-04-26 … 2025-12-28）から、spread と ATR の統計だけを使う（R-A）。S0-2 の pipeline の較正は合成 data だけで行う。
- **出力**:
  - S0-1〜S0-5 の結果
  - 合格 / 不合格
  - B′ の最終的な試行予算（S0-2 の較正結果に基づく）
- **停止**: 合格線のどれかに届かなければ cycle 1 に進まず、Human に D / E / H の判断を上げる。

### cycle 1: `PATSD_CYCLE_1_HORIZON_SHIFTED_SYSTEM_DISCOVERY`（Stage 0 合格と、R-B1 / R-B2 / R-B3 の個別承認が条件）

**data**

- seen の intraday span 全体: 2021-04-26 … 2025-12-28（4.68 年）。
- 最初の 100 営業日は warm-up だけ。2021-04-26 より前は読まない。
- 全 window が複数の cycle で使われたことを開示する。**2025 年だけで効く system は疑う。**

**family**（4 本 + 層 2 つ。B（mean reversion）は証拠が最も弱く rename リスクも高いので外す）

| family | 中身 | 注 |
| --- | --- | --- |
| F1 条件付き multi-day trend / breakout | H4 → 数日〜数週、barrier exit、vol 状態で条件付け | **rename リスク高**（Round 1 の 1〜6 日 trend は gross 負）。差は H4 の decision・barrier exit・状態条件。予算は小さくする |
| F3 clock / flow | WMR 16:00 fix・月末・Tokyo fix、H1 | 月末は warm-up の後で約 51 回しかないので、Stage 0 で検出力を計算してから予算を配る |
| F4 event の条件付け層 | 発表の前後の参加 / 回避・発表後の drift | event list は fresh の時期を見ずに凍結する。F1・F5 の上の回避層として使うときも、別の試行として数える |
| F5 vol 状態の policy | 圧縮後の拡大、H4〜日 | |
| L-meta（層） | base が正の family に、take / skip と expected net PnL の ranking | |
| L-port（層） | finalist の事前固定の等リスクの合成 | |

**exit template**（5 種、**全て最大保有 20 営業日の上限付き**）: 固定 horizon / time stop / 対称 ATR barrier / 非対称 barrier（2 : 1）/ trailing（ATR 2）。

**予算**（§23 の単一の式: 1 試行 = 評価した 1 つの (設定, exit, target, filter, hyperparameter, top-k) の組）

| 項目 | 式 | 試行 |
| --- | --- | ---: |
| 規則 | 4 family × 3 architecture × 9 格子点 × 2 exit | 216 |
| L2 filter（F4 の overlay を含む） | 4 family × 2 filter × 各 family の上位 3 設定 × 2 exit | 48 |
| ML（L-meta） | 最大 2 family × 2 model × 6 hyperparameter × 2 target × 3 top-k × base 1 設定 | 144 |
| 予約（事前登録した拡張・LLM の提案） | — | 192 |
| **合計** | | **最大 600** |

- **exit は、family ごとに 5 種から 2 種を、結果の前に選んで宣言する。**
- LLM の提案は予約の中から引く（§26）。
- 実効試行数は、§23 の clustering で事前に固定した方法で出す。
- S0-2 の結果で予算を下げることはあっても、上げない。

**CV**: purged walk-forward（anchored、四半期の fold、purge と embargo は最大保有期間 = 20 営業日）。random shuffle は禁止。分位は expanding window で過去だけから作る。

**target**: bid / ask 約定の realized net R、barrier の結果、P(net > 0)。

**model**: logistic / ridge、LightGBM（深さ ≤ 4、木 ≤ 200、hyperparameter ≤ 12）。

**baseline**（margin: candidate の fold 外の net Sharpe が、最良の baseline を 0.3 以上上回ること）

- 何もしない
- 同頻度・同 exit のランダムな entry
- 単純な trend（20 / 100 日）
- 単純な mean reversion
- 定数の position

**cost**: M15 の bid / ask 約定、rollover hour を除外、stress ×1.5 / ×2、financing は近似で markup 1% を既定。

**robustness**: §11・§28〜§30。

**選択**: §31 の U と、較正した hard filter。finalist は最大 3。

**凍結**: finalist と portfolio の全層を凍結する（R-C。digest・INTENT・STARTED の 2 段階）。

**confirmation の計画**:

1. G4 を満たせば、R-D（fresh の 1 回）を提案する。
2. 満たさなければ fresh は使わず、Human へ返す。
3. 真の Sharpe 0.8〜1.0 級の portfolio については、「fresh + 36 か月の forward」の確認計画を別に提案できる（R-D と R-E）。

## 37. Expected Failure Modes

1. Stage 0 で、H4 の cost drag が大きすぎると分かる。
2. pipeline の帰無の誤合格率を 10% に下げると、G4 がさらに遠くなる（最も起きやすい）。
3. 全 family が cost 後に負になる（Round 1 の再現）。
4. meta-model が雑音を拾う。
5. 1 通貨・1 pair に集中する。
6. G4 に届かない（候補はあるが確認できない）。

## 38. What Would Make Us Stop

- Stage 0 のどれかの合格線に届かない → cycle 1 に進まない。
- cycle 1 で hard filter を通る候補が 0、または G4 を満たす portfolio が作れない → **1 回で** `LONG_TERM_HOLD`（第 1 稿の「2 cycle 続けば」は撤回する）。
- tail の検査で残った候補が全て martingale 型。

## 39. What Would Make Us Escalate

- Stage 0 の結果、B′ が構造的に不可能と分かった → D / E / H の選択を Human に上げる。
- G4 を満たす portfolio ができた → R-D（fresh）。
- cost・financing・執行の不確実性が律速と分かった → D（R-E / R-F）。
- breadth が律速と分かった → E（R-G）。

## 40. FX-only について

G10 FX spot の breadth は小さい。8 通貨で、独立な方向は約 5〜7 しかなく、しかも強く相関する。#497 も JPY 1 つに依存した。

**研究の成功確率を最も制約しているのは、次の 3 つの組み合わせである。** B′ はこのどれも変えない。

- FX-only の breadth
- retail の cost
- seen span の短さ

**D と E は制約そのものを変える案で、S0-G が不合格のときの第 1 候補になる。**

## 41. Business Threshold の再評価

「年 5%・Sharpe 0.5・DD 20%」は整合しない。Sharpe 0.5 で年 5% なら vol は 10% になり、10 年 DD の中央値は −23% である（#496）。

**数値を 1 つに揃える**

| 項目 | 値 |
| --- | --- |
| production の目標 | portfolio の net Sharpe ≥ **1.0**、vol 5% で年 5%、MaxDD ≤ 15%（stress 込み） |
| 壊滅的な tail | なし |
| cost・financing | 実測に近い retail の値 |
| margin 利用 | ≤ 30% |

**Sharpe 0.8〜1.0 の system**:

- **昇格を決めるのは 1.0 の方である**（production の目標と G4）。0.8〜1.0 は production candidate にしない。
- この帯の system は、fresh だけでは確認できない（確認できる Sharpe は 1.12）。確認には fresh + 36 か月の forward（0.88）が要る。
- Human が §43 の 2 でその経路を認めた場合に限り、「延長確認の候補」として扱う。
- **「本物の 0.8 の system は、この設計では fresh だけでは確認できない」と明記する。**

年 5% は、Sharpe で稼ぐ目標としてならまだ合理的である。leverage で稼ぐ目標としては不合理である。通貨ごとの無 risk 金利との比較も並べる。

## 42. Final Questions

1. **これまでの programme は「儲かる FX 自動売買全般」を十分探索していたか？**
   → **大部分はしていた。**
   - intraday と 1〜6 日の system 要素（gate・exit・meta-label・session・vol）は、Round 1 と pre-R1 で広く試して失敗した。
   - 未探索は狭い帯域に限られる: event 回避の層・学習した regime gating・H4 の barrier exit・日次の非線形の条件付け・確信度 sizing・multi-family portfolio・tick の執行。
2. **standalone alpha source discovery から trading-system discovery へ移る合理性はあるか？**
   → **考え方としてはある。** ただし現在の data・cost・prior では、すぐに大きな探索を始めても成功確率は 約 1% 以下である。先に Stage 0 で「探す価値」を測るべきである。
3. **最も有望な未探索領域は何か？**
   → 次の 2 つ。
   - 探索の中なら、H4〜日次の vol 状態 / trend の barrier exit と、event 回避の層を、事前固定の portfolio で合成すること。
   - 制約を変える選択肢の中なら、**E（CFD の breadth）と D（broker の financing・執行 data）**。
4. **ML を再導入するなら、どの役割で使うべきか？**
   → take / skip と expected net PnL だけ。base が正の family に限り、選択を含む random base の帰無を置く。
5. **どの程度の探索自由度を許すべきか？**
   → cycle 1 で試行 600 以下（格子点 × exit × target × filter で数える）。Stage 0 の較正で下げることはあっても、上げない。
6. **過学習をどう抑えるか？**
   → 次の組み合わせで抑える。
   - 試行の正確な計数と、結果の前に登録する ledger
   - 選択 pipeline 全体の帰無較正（誤合格率 ≤ 10%）
   - deflated Sharpe
   - 近傍の plateau と、事後救済の禁止
   - 複雑度 penalty
   - 凍結した prior での縮小
   - rename 台帳
   - 確認は fresh の 1 回だけ
7. **fresh pool は今後どの段階で使うべきか？**
   → 凍結した 1 つの portfolio が G4（縮小期待 Sharpe ≥ 1.0）を満たしたときに、1 回だけ（R-D）。満たさなければ使わない。
8. **forward はどの段階で使うべきか？**
   → 凍結の翌営業日から封印して蓄積し、paper として運用・執行・financing を実測する。統計的には、fresh と合わせた 24〜36 か月で意味を持つ（0.8〜1.0 級の確認）。broker の再認証が要る。
9. **最初の cycle で何 family・何 candidate 程度を探索すべきか？**
   → cycle 0 は Stage 0（family の探索なし）。cycle 1（条件付き）は 4 family + 2 層、architecture は最大 12、試行は最大 600、finalist は最大 3。
10. **最初の cycle で実装・実行すべき具体的な research architecture は何か？**
    → **S0-G の cycle 0（Stage 0）**。合格すれば §36 の cycle 1。
11. **この programme で年 5% net を狙うことは、まだ合理的な business objective か？**
    → Sharpe ≥ 1.0・vol 5% の portfolio としてなら、目標として合理的である。ただし達成の事前確率は 約 1% 以下と低い。leverage で狙うのは不合理である。
12. **FX spot だけに固定したままでよいか？**
    → cycle 0 と 1 は FX spot のまま。**Stage 0 が不合格なら、E（CFD の breadth）を最初の option として Human に上げる。** FX-only の breadth は、成功確率を制約する主因の 1 つである。

## 43. Human + ChatGPT Decisions Needed（3 件）

1. **S0-G の採用と cycle 0（Stage 0）の承認（R-A）**: seen の M15 bid / ask cache から cost の統計だけを読む（signal と return は突き合わせない）。pipeline の較正は合成 data だけで行う。
2. **business objective の再定義**:
   - 「年 5%・Sharpe 0.5・DD 20%」を「portfolio net Sharpe ≥ 1.0・vol 5%・MaxDD ≤ 15%」に改める。
   - 成功の事前確率が 約 1% 以下であることを受け入れるか。
   - Sharpe 0.8〜1.0 の system の確認に「fresh + 36 か月の forward」を使う経路を認めるか。
3. **Stage 0 が不合格だった場合の方向**: D（tick・broker data）/ E（OANDA の CFD で breadth を広げる）/ H（hold）のどれを優先するか。どれも実行には別の Red の承認が要る。

## 44. 独立 review の記録

役割は 2 つ。どちらも別 session で、source と repo を読み直した。互いの結論は渡していない。

**契約・事実の監査**

- 必須の見出し 36・12 の問い・3 件の判断・STOP は揃っていた。§13 の算術は正しい。
- **BLOCKER 2 件**:
  - 内部 holdout の窓の説明が誤り（実際は複数 cycle の決定 panel）
  - pre-R1 の数値を、C-8 の fenced と開示せずに根拠にした
- **REQUIRED_FIX 9 件**:
  - forward の事後 SD の縮みの誤用（29% → 16〜21%）
  - 縮小の未定義と G4 の到達不能性
  - 閾値の不一致
  - discovery 外の暦の区切り
  - 予算の算術
  - Sharpe の単位の混在
  - archetype 表の欠けた列
  - 付随的にしか答えていない裁定項目（EA の anti-pattern・ML governance・model family・LLM・champion / challenger・plateau・評価の階層・p-value・prior・baseline の margin・前提への 4 問・新しい未来 holdout）
  - API の失効の根拠
- NON_BLOCKING 7 件。
- **全て反映した**（§2・§3・§6・§10・§13・§14・§23〜§32・§34・§41）。

**敵対的 review**

- **BLOCKER 4 件**:
  - 内部 holdout は軽く使われた window ではない（112 行・17 PR）
  - warm-up が保護の境界を越える
  - G4 はほぼ常に塞がり、「約 1 割」は導出されていない（実際は 1% 未満）
  - cycle の包括承認が policy と矛盾する
- **REQUIRED_FIX 8 件**:
  - H1〜H4 の新規性の誇張（Round 1）
  - 10〜15% は未測定
  - 試行の過少計数
  - pipeline 全体の帰無較正
  - meta-label の帰無に選択が入っていない・trailing の上限・分位の時点
  - fresh の汚染台帳
  - 閾値の不一致
  - 「stop」と「市場の変更」が選択肢に無い
- 推奨は「hold + Stage 0。合格なら絞った B′、不合格なら D / E を Human に」だった。
- **全て反映し、推奨も S0-G に変えた。**

**再監査**（第 2 稿を、別の新しい context で読み直した）

- 上の指摘の大半は RESOLVED だった。
- **新しい BLOCKER 1 件**: R-B が読み取りと training を 1 つの承認にまとめていた。
  - → R-B1（読み取り）・R-B2（training）・R-B3（評価）に分けた。policy の引用も §2a / §6 / §9 に直した。
- **新しい REQUIRED_FIX 5 件**:
  - 上端の保護境界 → entry の打ち切りと強制決済、guard の test（§10）
  - 試行の数え方の矛盾 → 単一の式と予算表（§23・§36）
  - G4 の期間を fold 外の約 3.4 年に直した（§10・§13）
  - 2.68 年の数値の残り → 更新（§1・§4・§36）
  - 「約 1%」の導出 → 周辺確率 0.011 × fresh の検出力 0.72（§13）
- **NON_BLOCKING 6 件**:
  - R-A で 3 つの route を名指す
  - S0-1 では価格の経路で exit を simulate しない
  - S0-2 の parameter の出所を開示する
  - 150 行
  - prior の参照クラスの不一致と、τ の実効値 0.565
  - 1.0 が昇格を決めること
- **全て反映した。**

**lead の判断**

- 3 回の review の BLOCKER と REQUIRED_FIX は全て、証拠を確かめたうえで受け入れた。
- §13 の数値は lead が独立に再計算して一致した（fold 外 3.4 年で観測 1.86 が必要、真の 1.1 で通過 0.08、周辺確率 0.011）。
- 未解決の意見の相違は無い。
- ただし S0-3 は構成上不合格の見込みが高く、推奨の最も起きやすい帰結は「D / E / H の判断を Human に返す」である（§35）。

---

**STOP（裁定 §64）。** 設計報告の完成で止まる。

- alpha を走らせない。
- ML を学習しない。
- fresh・forward を開かない。
- 有料 data を買わない。
- broker に接続しない。
- Stage 0 も、Human + ChatGPT の承認（R-A）の後に行う。
