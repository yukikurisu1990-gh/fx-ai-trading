# ARCHITECTURE_NEUTRAL_FX_SYSTEM_REDESIGN — FX 自動売買 system の合成原理のゼロベース設計（2026-10-07）

**DESIGN ONLY · `NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` · `PRODUCTION_READINESS_NOT_CLAIMED`.**

**authoritative な state は変わらない: `FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE`**（`docs/governance/fxid_long_term_hold_ruling_2026_10.md`、PR #504 で merge 済み: head `afef899` → merge `bd69dd1`。この branch の起点）。この文書は HOLD を解除せず、`FXID_REOPEN_REVIEW_PROPOSAL` でもない。

**承認**: Human + ChatGPT の指示 `ARCHITECTURE_NEUTRAL_FX_SYSTEM_REDESIGN`（2026-10-07）。以下で「指示 §n」はこの指示の節を指す（HOLD の裁定の節は「裁定 §n」と書く）。指示 §36 は、既存の文書と集計の記録の確認、taxonomy、数学・統計の設計、**synthetic / analytic calculation**、独立レビュー、報告の作成を許可し、新しい価格 data の読み取りと取得、backtest、ML、fresh の読み取り、HOLD の解除を禁止している。

**記号**:

| 記号 | 意味 |
| --- | --- |
| 【記録】 | repo の既存の報告・記録 |
| 【合成】 | `artifacts/research/architecture_redesign/synthetic.json`（`scripts/research/architecture_redesign/synthetic.py`。価格 data を読まない合成と解析。指示 §36 の許可による） |
| 【算術】 | この文書の計算 |
| 【設計】 | 提案 |

---

## 1. Executive Summary

**最終判定（提案）: ARCH-C — `COMPOSITION_DOES_NOT_SOLVE_THE_FUNDAMENTAL_LIMITATION`。**

足し算・掛け算・ensemble・mixture・通貨の netting・最適化のどれを選んでも、**現在の edge・cost・data という根本の制約は解けない**。合成が効くのは、正で・機構を持ち・cost の後に残り・互いに重ならない component が複数ある場合だけで、それが無い。

**それとは別に**、合成の構造の問いには答えが出るので、将来の再開のための**設計の基準**として記録することを提案する（判断依頼 2。HOLD は変えない）:

- **既定は Architecture H**: 通貨単位・最適化を中心にした合成の構造で、期待 return は文献の prior で事前に固定し、data で推定しない。
- **Architecture G**（H に、mechanism ごとの条件付きの推定と family の縮小を加えたもの）は、合成の帰無の検証（§29 の P2）で H を上回る場合にだけ採る。

**根拠の要点**:

1. **最も近い 2 区間を合わせても届かない**【合成・記録】。比べる基準は、全て retail の net。

   | 組み合わせ | 合成の上限（真の Sharpe） |
   | --- | --- |
   | EUR の朝（retail の net 0.2〜0.75）＋ JPY の仲値の後（最近の retail の net ≈ 0） | 0.75（相関 0）〜0.87（相関 0.5 の hedge の効果） |
   | 同上、JPY を 1999–2018 の長期・half spread の 0.85 に置いた場合（古い sample の上端） | 1.13 |

   - この 2 区間は、同じ機構（dealer が fix での dollar の需要を在庫で受ける W 字）の、**時間が重ならず、USD の符号が逆**の 2 つの窓である（EUR の short は USD の long、JPY の long は USD の short）。同じ family の中の上限であり、独立な 2 つの component ではない。
   - これは真の Sharpe の上限で、G4（縮小後の事後 Sharpe 1.0）に要る観測（G4-A、τ 0.8〜0.4 で 1.31〜2.56、τ 0.4 では 2.24〜2.56【記録 Cycle 1 §16 と `cycle1_design_supplement.json`】）とは比べる量が違う。どちらで見ても届かない。
   - #496 の算術【記録】では、s ≈ 0.07 の source を無限に足しても上限は s/√ρ = 0.22（ρ = 0.1）。
2. **最大の危険は、architecture の名前で偽発見を増やすこと**【合成】。真の Sharpe が全て 0 の候補 100 本から、in-sample の上位 5 本を等 risk で組むと:
   - in-sample の portfolio の Sharpe は平均 **2.03**（帰無の 90 percentile は 2.36）
   - 独立な期間では **−0.003**
3. **交互作用は、現実の効果量では検証できない**【合成】。2×2 の 1 cell だけに効果がある交互作用の項 β12 を直接検定するには、効果が trade あたり 0.03（年率の Sharpe 0.47 相当）なら、検定 1 つでも約 11 万 trade（年 250 回で約 440 年）が要る。
4. **過去研究**【記録】:
   - 特徴量・gate・meta-label・Top-K の組み合わせは豊富（全て負か、検出力不足か、無効）。
   - **機構の違う component を同時に持って portfolio として評価したのは #497 の 1 本だけ**。
   - 通貨単位の architecture（Track 1、#481）は、signal が gross で負で、architecture の評価になっていない。
   - 交互作用の項を直接検定する事前登録は無い（条件付けの事前登録は #471 にある）。
5. **次の cycle**（§29 の P1・P2、実 data を読まない）は、**裁定 §9 の trigger が成立し、`FXID_REOPEN_REVIEW_PROPOSAL` が承認された後にだけ**行う。HOLD のままでは行わない。P1 の予想される結論は STOP（§29）。

## 2. What is an edge?

**定義【設計】**: edge とは、**情報集合 I_t の下で、ある通貨の組（numeraire に対する通貨、または通貨の basket）の horizon h の条件付きの期待 return が、その horizon と turnover に伴う取引の cost を超えて 0 と違うこと**: |E[r_{t→t+h} | I_t]| > c(Δx, t)。

- edge は**情報・horizon・cost（取引と時刻の関数）の 3 つ組**に付く性質で、「strategy」や「pair」には付かない。
- **経済的な edge**（誰が・なぜ・いつ支払うかの説明を持つ。risk premium・dealer の在庫の対価・需要の集中）と、**統計的な edge**（説明を持たない）を分ける。component にするのは前者だけ。

## 3. What is a signal?

**定義【設計】**: signal とは、**時刻 t に観測できる量を、edge の予測（期待 return の推定とその不確実性）に写す関数**の出力。

- 単位は「期待 return / σ」（予測の強さ）と、その予測の誤差の分散。BUY / SELL のような離散の命令ではない。
- 離散化（閾値）は、情報を捨て、閾値を自由度として加える。最終の position の段まで遅らせる。

## 4. What is a strategy?

**定義【設計】**: strategy とは、情報集合・予測・timing・entry・exit・sizing・執行を、1 つの取引の規則に**束ねた複合物**。

**結論**: **strategy は研究の原子として不適切**。理由は次の 4 つ。

- (a) 閾値・保有期間・gate を内蔵し、探索の数を隠す。
- (b) 同じ edge が別の strategy として重複して数えられる（§13 の 3 pair の例）。
- (c) 衝突と重複は、最終の position の前に解く必要がある。
- (d) cost と risk は portfolio で決まる。

**EUR の欧州の朝の short の分解**:

| 層 | この例での中身 |
| --- | --- |
| mechanism | dealer が fix での dollar の需要を在庫で受け、その対価を取る（KMW の W 字）。自国の取引時間の顧客の flow（B&R） |
| 予測 | 02:00〜08:15 ET の EUR の対 USD の期待 return < 0 |
| 執行の schedule | 02:00 に入り、08:15 に出る |
| strategy | 上の 3 つを EUR_USD で束ねたもの |

**JPY の仲値の後は、同じ機構の別の時刻の予測**で、独立な strategy ではない。

## 5. What is a portfolio component?

**定義【設計】**: portfolio component とは、**1 つの mechanism family が出す、通貨単位の期待 return の view（と、その予測の誤差の共分散）**。

- view は、numeraire（USD）に対する通貨、または通貨の差（例 e_EUR − e_CHF）で表す。合計 0 の制約で、自由度は 7。
- **component は取引しない**。取引するのは、全ての component を集めた後の最適化だけ。
- 同じ機構の時刻の違う予測（EUR の朝・JPY の仲値の後）は、**1 つの component の中の要素**として扱い、別の component として数えない。

## 6. What previous research actually combined

【記録】pre-R1 の結果は C-8 により文脈だけで、証拠に使わない。

| 類型 | 代表的な研究 | 状態 | 結果 |
| --- | --- | --- | --- |
| **A. 特徴量の組み合わせ** | Phase 9 の LightGBM（C-8、leakage で無効）、Phase 27–29（C-8）、ML Step 4（C-8）、Round 1 の family H（#464、57 variant）、Track 1 の ridge、B′ の線形 | 検定済み | 全て負か、検出力不足（Round 1 H は family-wise の p = 0.699）。B′ は損益分岐の IC の 6〜16% |
| **B. filter / gate** | Round 1 の session・ATR・ADX・spread の gate、Round A の 39 cell（周辺のみで、交差なし）、#471 の carry × tick 量（条件付けとして事前登録） | 検定済み | gate は全て net を下げた。Round A は 0/39（帰無の通過率 0.227）。#471 は 15/15 で悪化 |
| **C. meta-label** | Phase 22.0e（C-8）、Round 1、#479 M13 | 検定済み | 全て負の base の上。#479 は「負の base への filter は何も証明しない」の kill 規則が発火 |
| **D. strategy の選択・Top-K** | Phase 9.17 / 9.19（C-8、無効）、Phase 28 A4（C-8）、#479 M01 | 検定済み | 負か無効 |
| **E. strategy の ensemble** | Phase 9.17 の selector・Phase 28.0c AR3 の stacking（C-8）だけが走った。#480 A15 / A03 は設計だけ | ほぼ無い | 負か、設計のみ |
| **F. multi-family の portfolio** | **#497（carry + 12-1 momentum、等 risk、8 通貨、ECB 2000–2016）だけ**。#496 は算術だけ。#490 の 5 本は凍結したが**個別に評価** | 1 本 | TC-net 0.127（t ≈ 0.5）、judged 0.340。carry が 99%、2008 年以降は約 0。検出力不足 |
| **G. 通貨単位の portfolio** | Track 1（#481）。#478 以降は通貨の book が標準の harness（各 signal は単独）。#494 の M15 / M16 は book の欠陥で無効、#495 で修正 | 検定済み（signal は単独） | Track 1: net −0.84、**gross −0.47**（signal が負）。M16（修正後）は 0.276 の positive-exploratory |
| regime / MoE | Phase 28.0c AR1〜AR4（C-8、全て反証）、#479 M03（設計の欠陥で未検定）、M10 HMM（未実行） | 学習した gating は未検定 | — |
| 交互作用 | **交互作用の項 β12 を直接検定する事前登録は無い**。Round A は意図的に周辺のみ、B′ は「交互作用なし」を事前登録。#471 は条件付けを事前登録（§25 の分類では条件付きの strategy） | 項の検定は未実施 | — |
| exit | Phase 24 の 87 cell（C-8、文脈のみ。trailing 33・部分決済 27・regime 27）、Phase 9.18（C-8） | intraday のみ | 87 cell 全て REJECT（`still_overtrading`）。post-R1 は固定の horizon だけ。multi-day の barrier は未検定 |

## 7. Feature combination vs strategy combination

| 区別 | 中身 | 過去研究での量 |
| --- | --- | --- |
| 特徴量の組み合わせ（A） | 1 つの edge の推定を改善しようとするもの。分散化ではない | 豊富 |
| filter / gate（B）・meta-label（C） | 1 つの edge を条件付きで使うもの。分散化ではない | 豊富 |
| strategy の組み合わせ（D・E・F） | 別の edge を同時に持つもの。分散化はここだけ | ほぼ無い（#497 の 1 回） |

「indicator を複数使った」を「strategy の分散化を試した」と数えない。

## 8. Additive composition

**正しい合成は、予測の誤差の共分散を使った精度の加重**である【設計】:

- 線形・正規で予測が条件付きで独立なら、E[r | I₁, I₂] = E[r | I₁] + E[r | I₂]。**足し算はこの一次の近似**であり、仮定ではない。
- 予測の誤差が相関する（同じ機構の family、W 字の 2 区間）と、個別の精度だけの重みは**二重計上**になる。component の間の予測の誤差の共分散（§21 の構造の代理）を、合成に入れる。
- 合成した期待 return μ を、最終の最適化に渡す。position は Σ⁻¹μ に比例し（cost・制約で修正）、μ の足し算そのものではない。

**重みの決め方の候補**:

| 方式 | 自由度 | 評価 |
| --- | --- | --- |
| 等 risk（事前に固定） | 0 | 最も安全。#497 |
| risk parity（mechanism の間） | 0（共分散の推定だけ） | 安全 |
| prior の強さの比（文献の効果量で固定） | 0 | 安全（外部の prior） |
| Black–Litterman（文献の prior + view、Ω で不確実性） | 少 | **推奨の合成の形**（§13 の疎な view も扱える） |
| 推定した平均・分散 | 多 | 縮小が必須 |

## 9. Multiplicative composition

`adjusted_μ = μ_base · g(state)`

- 掛け算が正しいのは、**1 つの edge の強さが状態で変わる時**（例: dealer の在庫の対価は vol に比例）。別の edge どうしを掛けると、意味の無い積になる。
- 硬い掛け算（0 / 1 の gate）は標本を捨てる。soft な掛け算（連続の g）は自由度を加える。g の形は事前に固定するか、縮小を伴う推定にする。
- **cost と risk は μ の掛け算にしない**【設計】:
  - **cost は予測ではなく取引（Δx）の関数**。|Δx| の罰則は、現在の保有に依存する**no-trade の帯**を作る。μ に掛ける scalar では、この帯は作れない。
  - **risk の 1/σ² の縮小は、対角の Σ の特別な場合**。最適化の Σ⁻¹ は、交差の項（通貨の重なり）も扱う。

## 10. Interaction effects

**理論**: E[R | A] = E[R | B] = 0 でも E[R | A, B] > 0 はありうる（XOR 型）。「単独で弱いものの組み合わせに意味は無い」とは言えない。

**検出の代償**【合成】:

- 2×2 の均衡な設計で、効果 δ（trade あたり net の平均 / σ）が 1 cell だけにある時、SE(β12) = 4σ / √N。
- 必要な総 trade 数は N = (4 (z_{α/M} + z_β) / δ)²（片側 5%・検出力 80%、M は検定する交互作用の cell の数）。

| δ（trade あたり） | 年率の Sharpe 相当（年 250 回） | M = 1 | M = 45 | M = 180 |
| --- | --- | --- | --- | --- |
| 0.013 | 0.21 | 約 58.5 万 trade（2,341 年） | 5,761 年 | 6,983 年 |
| 0.03 | 0.47 | 約 11 万（440 年） | 1,082 年 | 1,311 年 |
| 0.05 | 0.79 | 約 4 万（158 年） | 390 年 | 472 年 |
| 0.1 | 1.58 | 約 1 万（40 年） | 97 年 | 118 年 |

- retail の net の推定（Sharpe 0.2〜0.75）は、trade あたり 0.013〜0.047 に当たる。
- **結論**: 1 日 1 回の頻度の intraday では、**2 次の交互作用を現実の効果量で検定することは、事実上できない**。最初の版の「cell の trade ≥ 600」は、効果 0.1 を仮定した循環で、cell の平均の SE を使っていたので、撤回する。

**本物の交互作用と事後の filter の区別【設計】**（将来、もし交互作用を扱うなら）:

1. 経済的な理由を事前に書く。
2. 交互作用の項 β12 を直接検定する（factorial の回帰）。
3. 次数 ≤ 2（§27）。
4. 交互作用の係数を、主効果より小さい prior の SD で 0 に縮小する。
5. **必要な標本は上の式で事前に計算し、満たさなければ検定しない**。
6. 検定した全ての cell を max-T の候補の数に数える。
7. H-002・Round 1 の gate・Round A の 39 cell・#471 と同じ変数・水準を、名前を変えて検定しない。

## 11. Mixture-of-experts

`forecast = Σ_k P(regime_k | I_t) · model_k`

- **利点**: 状態で予測の仕組み自体が変わる時に、1 つの model より適切。
- **危険**: model の数 × gating の自由度。学習した gating は暗黙の探索になる。
- **過去**: 決定論的な分割（Phase 28 AR4、C-8）は最悪。学習した gating は未検定。
- **評価【設計】**: 各 expert が単独で正の component として事前に成立している場合だけ候補にする（負の expert を gating で救うのは、meta-model による救済の禁止に当たる）。状態は 2 つまで、gating の変数は事前登録の 1 つ。

## 12. Hierarchical architecture

経済的な edge → 状態の条件付け → cost の条件付け → 確信度 → position の提案 → 通貨の netting → portfolio の risk の管理 → 執行。

- 層を分けると、監査と自由度の数え上げがしやすい。ただし**層ごとに閾値を置くと、自由度が掛け算で増える**。
- **原則【設計】**:
  - 推定する層は 2 つまで（mechanism の中の条件付きの μ と、mechanism 間の縮小）。
  - 残り（cost・risk・netting・執行）は、事前に固定した規則か、最適化の制約。
  - 確信度は、別の層ではなく、予測の誤差の分散（Black–Litterman の Ω）として扱う。

## 13. Currency-level architecture

**FX の return は、既に通貨の空間にある**【算術】:

- 三角の裁定が無ければ、pair の mid の log return は、通貨の 7 次元の空間（incidence 行列 A の列空間、rank 7）にある（bid / ask を除けば厳密に）。**pair 固有の「return の雑音」というものは無い**。
- 【合成】「射影で 65% が除かれる」のは、**全 20 pair に、独立・等分散の予測の誤差がある時の、予測の誤差**の話（rank 7 / 20 = 35% が残る）。FX の return の性質ではなく、signal の作り方の性質である。
- **疎な view を A⁺ で射影してはいけない**【合成】。EUR_CHF だけの予測 1 を、他の 19 pair の予測 0 として A⁺ で射影すると、AUD +0.03・CAD +0.06・EUR +0.14・CHF −0.22 などに散り、予測の二乗ノルムの 36% しか残らない（「view なし」を「予測 0」と扱うため）。

**設計【設計】**:

- **mechanism は、通貨の view を直接出す**（例: EUR の対 USD、または e_EUR − e_CHF）。pair の view しか持たない mechanism は、Black–Litterman の形（P = A の行、view の無い pair は Ω = ∞）で合成する。
- **portfolio の原子は通貨にする**。
- **pair に固有のものは、return ではなく、執行の cost と jump / regime の risk**（EUR/CHF の floor の解除など）。view 自体は、通貨の差の vector として表せる。

**重複の例**【合成】: EUR_USD long + USD_JPY short + EUR_JPY long の 3 つの「strategy」は、通貨の exposure（return の単位）では **EUR +2・USD −2** で、JPY は相殺し、**1 つの bet の 2 倍**にすぎない。

**netting の利得の条件**:

- netting で得をするのは、**複数の通貨の position を同時に持つ時**だけ。
- FXID の当日決済の範囲で知られている family（EUR の朝 02:00〜08:15 ET、JPY の仲値の後 20:00 前後〜02:00 ET）は、**時間が重ならない「1 通貨 対 USD」の窓**で、通貨の vector はほぼ同時に存在しない。**FXID の範囲では、netting の利得は小さい**。
- 通貨単位の architecture の価値は、主に日次以上の horizon で複数の mechanism が同時に position を持つ場合に現れる。

**注意**:

- Cycle 1 の breadth（participation ratio 約 5、第 1 固有値の割合 約 0.32）は、**20 pair の相関行列**の値で、通貨の空間の値ではない。第 1 成分が USD の因子であることも確かめていない【記録】。
- Track 1（#481）の負は、signal の gross の負で、通貨の architecture の反証ではない【記録】。
- Q8 の支持は、rank の議論による**事前の**ものである。

## 14. Signal conflicts and netting

例: 平均回帰 → EURUSD long、fix flow → EURUSD short、macro → USD long。

| 処理 | 評価 |
| --- | --- |
| 相殺 | 期待 return の空間で精度の加重で合成すれば自然に起こる。推奨 |
| 強い方が勝つ | 情報を捨て、閾値の自由度を足す。非推奨 |
| 確信度の加重和 | 確信度が予測の誤差の分散なら、ベイズの合成と同じ。推奨の形 |
| 優先順位 | 監査しやすいが恣意的。非推奨 |
| no-trade | 最適化で、合成した期待の net が cost を超えなければ自然に起こる |
| **通貨の exposure での netting** | 推奨（§13） |
| 最適化に渡す | 推奨（最終の段） |

**意見の不一致**: 予測の誤差の分散の増加として扱う。合成の μ が小さく、Ω が大きくなれば、最適化は自然に size を下げる。「不一致そのものを signal にする」は別の component の仮説で、事前登録が要る。

## 15. Regime architecture

| 方式 | 統計的な性質 | 評価 |
| --- | --- | --- |
| 硬い gate `α · I(regime)` | 標本を p 倍に減らす。閾値が自由度 | 経済的に明確な場合だけ（例: rollover の前後は取引しない＝cost の制約） |
| mixture `Σ P(k) α_k` | expert × gating の自由度 | §11 の条件付きで |
| **条件付きの期待 return を直接推定**（状態を共変量にした縮小の回帰） | 全標本を使い、状態の効果を部分 pooling で縮小 | **最も安全。推奨** |

状態変数は mechanism ごとに 1 つまで、事前登録する。

## 16. AI/ML placement

| 位置 | 多重性・過学習の危険 | 外部の検証 | 評価 |
| --- | --- | --- | --- |
| 価格の方向の直接の予測 | 最大 | 難しい | **使わない**（Round 1 H・Phase 9・ML Step 4 は負か無効【記録】） |
| 期待 return の推定（mechanism の中） | 中〜大 | 中 | 事前登録の 1 つの状態変数の縮小の回帰まで。GBDT は使わない |
| edge が働く確率・no-trade・meta-label | 大 | 難しい | base が正の時だけ。今は使わない |
| regime の推定 | 中 | 中 | vol の状態などの推定に限る |
| signal の合成・strategy の重み | 大 | 難しい | ML にしない。縮小と事前の重み |
| **cost・slippage の予測** | 小（方向ではない） | 執行の data で検証できる（**live の約定が要るので、production の段の Red の作業**） | 推奨（将来） |
| **vol・相関の予測** | 小 | 価格だけで検証できる | 推奨（risk の層） |
| portfolio の配分 | 中 | 中 | 最適化（解析）で十分 |
| 執行の timing | 小〜中 | 執行の data で | 将来の候補 |

**原則**: ML を alpha の源泉にする architecture と、複数の経済的な mechanism を ML が統合する architecture を分ける。前者は使わない。後者も、統合の重みは ML ではなく縮小で決める。ML は方向ではない量（cost・vol・相関・slippage）に置く。負の base を meta-model で救うことは禁止。

## 17. Exit architecture

| exit | 分類 | 扱い |
| --- | --- | --- |
| 時間 stop | **edge の一部**（mechanism の窓） | mechanism ごとに事前に固定 |
| barrier（TP / SL） | risk の管理 | portfolio の risk の制約。exit を edge の源泉にしない |
| regime の変化・alpha の減衰・反対の signal | 予測の更新 | 最適化の再計算 |
| portfolio の rebalance | 執行の方針 | turnover の罰則・帯 |
| **当日決済**（FXID） | **硬い制約** | NY 17:00 の前に flat、週末をまたがない |

- **時刻が固定の schedule の component（EUR の朝・JPY の仲値の後）は、entry と exit の時刻そのものが edge**である。turnover の罰則を持つ 1 期間の最適化は、入りと出が遅れる。**多期間の最適化**（Gârleanu–Pedersen 型の aim portfolio。予想される μ の時間の形を先読みする）で扱う【設計】。
- 「exit を工夫して負の alpha を正にする」ことはできない（Phase 24、C-8、文脈のみ）。「exit は全部終わった」とも言えない（multi-day の barrier は未検定【記録】）。

## 18. Risk architecture

risk は μ に掛ける scalar ではなく、**最適化の目的と制約**で扱う。

- **目的**: 分散（または ES）の罰則。
- **制約**:
  - 通貨ごとの exposure の上限、USD の因子の exposure の上限
  - 1 つの mechanism family の risk の予算の上限
  - turnover の上限
  - ES / tail の制約
  - margin（pair の gross notional と通貨の gross の比。Track 1 では 0.76【記録】。日本の個人の leverage の上限 25 倍）
  - vol target
  - **当日決済・週末・指標の発表の前後の blackout（または cost の拡大）**
- **Σ**: 標本の相関ではなく、構造化した推定（通貨の因子 + 時刻の重なり + 流動性の shock の共通の因子）。
- **stress**: 中央銀行の介入と jump（BoJ 2022・2024、SNB 2015）、risk-on / off（AUD・NZD 対 JPY・CHF）。JPY の窓は介入の tail の risk を持つ。

## 19. Execution architecture

**alpha の層と執行の層を分ける【設計】**:

| 層 | 決めること |
| --- | --- |
| alpha の層 | 通貨の期待 return と、通貨の目標の exposure |
| 執行の層 | どの pair を、いつ、どれだけの cost で |

**1 つの最適化に統合する**【設計】:

- 決定変数は **pair の保有 x**（20 pair 全て）。
- pair の期待 return は μ_pair = A μ_ccy、通貨の exposure は Aᵀx（常に合計 0。z は USD を含む）。
- cost は**取引に**掛ける: Σ_p c_p(t) |x_p − x_p,prev|。
  - c_p(t) は**時刻と event に依存する**（Cycle 1【記録】: rollover の 17 時台 9.2 bp、16 時台 2.5 bp、08:30 の発表の前後は ×1.44 以上、東京の朝は ×1.10）。
  - mechanism の窓の時刻の値を使う。NY 09:00 の値を 02:00 ET や東京の仲値の時刻に転用しない。
- 2 本の pair を合成して cross を作る場合は、**2 本の約定の時刻のずれの slippage**の項を加える（OANDA retail では 2 本は同時に約定しない）。
- この問題は凸のまま。

**最も安い表現は、USD の major とは限らない**:

- 8 通貨の任意の exposure は、USD を含む 7 つの major（EUR_USD・GBP_USD・AUD_USD・NZD_USD・USD_CAD・USD_CHF・USD_JPY）で張れる（全域木、rank 7）【合成】。
- しかし、R-A2b の 09:00 ET の往復の spread【記録】では:
  - USD の major: USD_JPY 1.17・EUR_USD 1.36・USD_CAD 1.36・GBP_USD 1.41・USD_CHF 1.73・AUD_USD 1.95・NZD_USD 2.54 bp
  - cross: EUR_JPY 1.33・EUR_CAD 1.37 bp など、USD の major より安いものもある
  - EUR 対 JPY を EUR_USD + USD_JPY で作ると 2.53 bp で、EUR_JPY 1.33 bp の約 2 倍
- **最適な表現は、20 pair 全てを入れた最適化で決める**。
- **pair ごとの financing（swap の markup）**も、表現の cost に入る（当日決済なら主に rollover をまたがないことで避ける）。
- **執行の現実**: OANDA retail は market maker の気配で、文献（KMW・B&R）の firm な気配（EBS・CME）とは違う（requote・slippage）。文献の net の Sharpe は firm な気配の上の値である。

**今回は設計だけ**で、実 data の取得・broker の接続はしない。

## 20. Component value vs standalone Sharpe

| 面 | 量 |
| --- | --- |
| standalone | E[R_i]、Sharpe_i（cost の後） |
| conditional | E[R_i \| state]（事前登録の状態だけ） |
| incremental | 既存の portfolio に足した時の ΔE[R]、ΔSharpe、ΔMaxDD、ΔES |
| information | 既存の component で説明できない return を説明する量（残差の IC） |
| capital | margin・turnover・執行の cost あたりの貢献 |

【算術】2 本の最適な合成の Sharpe = √((s1² + s2² − 2ρ s1 s2) / (1 − ρ²))。

- standalone 0.3 でも、ρ < 0 の相手には大きく貢献する。
- standalone 0.8 でも、既存と ρ ≈ 1 なら増分はほぼ 0。
- Sharpe 0 でも相関する component は hedge として貢献しうる（0.75 と 0、ρ = 0.5 で 0.87【合成】）。ただし相関の推定の誤差に弱い。

## 21. Marginal portfolio value

- component の採否は**限界的な portfolio の価値**で判断する。ただし限界の価値は standalone より推定の誤差が大きい（共分散の推定が加わる）。
- 共分散は、標本の相関ではなく、**構造の重なり**から作る:

  | 重なり | 中身 |
  | --- | --- |
  | return の相関 | 標本の値 |
  | tail の相関 | 下側の同時の発生 |
  | 通貨の因子の重なり | 同じ通貨の exposure |
  | 時刻の重なり | 同じ時間帯の position |
  | 流動性の重なり | rollover・週末・指標の発表 |
  | macro の exposure | risk-on / off、USD の資金の逼迫 |
  | vol の状態の exposure | 高 vol で同時に壊れる |
  | 機構の重なり | 同じ経済的な説明（EUR の朝と JPY の仲値の後） |
  | drawdown の重なり | DD の期間の一致 |

- 「低相関 = 独立」とは扱わない。
- 限界の価値の推定と、包含の決定を、選択の多重性に数える（§22）。

## 22. False-discovery risk

**中心の問題**【合成】: 真の Sharpe が全て 0 の候補から上位 k 本を選んで、等 risk で組んだ場合（約 5 年、400 回の反復）。

| 候補 N | 選ぶ k | 共通因子の相関 | 選んだ component の in-sample | **portfolio の in-sample**（平均 / 帰無の 90%） | 独立な期間 |
| --- | --- | --- | --- | --- | --- |
| 20 | 5 | 0 | 0.56 | **1.24** / 1.65 | 0.00 |
| 100 | 5 | 0 | 0.91 | **2.03** / 2.36 | 0.00 |
| 100 | 10 | 0 | 0.79 | **2.48** / 2.84 | −0.01 |
| 100 | 5 | 0.3 | 0.76 | **1.15** / 1.66 | 0.00 |

低相関の弱い component を data から選んで集めることは、偽発見の portfolio を作る強い経路である（相関 0 では、in-sample の portfolio の Sharpe は選んだ component の平均の √k 倍）。

**ベイズの経路の抜け穴**【設計・算術】:

- component ごとに独立な N(0, τ) の prior で縮小してから足すと、system の Sharpe の暗黙の prior は約 τ·√k になる（τ = 0.4、k = 10 で約 1.26）。
- G4 の system の prior（τ 0.4）より遥かに緩く、事後 0.35 の component を 10 本足すと system の事後 約 1.1 になる。§22 の偽発見のベイズ版である。
- **対策**: G4 の prior は **system の Sharpe に直接**課す。component の prior（family の τ、0 への spike の質量）は、それが含意する system の prior が G4 の prior と一致するよう較正する（§30）。

**手続きの指定【設計】**（どの paradigm で何を決めるか）:

| block | 手続き | 決めること |
| --- | --- | --- |
| **選択の block** | 候補の component・variant・包含の全てを候補とする **max-T（FWER 10%）** | 何を残すか |
| | nested walk-forward は、選択の block の**内側だけ**で使う（選択・重み・包含を内側で再実行） | |
| | 帰無の生成: 時刻が固定の component には、mechanism の窓で区切った block の符号の randomization（裁定 §8 の案 C、限定の候補。制約を守る）。それ以外は、その戦略に合わせて事前に設計する | |
| **独立な推定の block** | **system の事後の Sharpe**（G4 の prior を system に課す）で判定 | 残したものが G4 に届くか |
| **fresh** | system 全体を 1 回 | 確認 |

**比較**:

| 方法 | 評価 |
| --- | --- |
| 階層 Bayes・部分 pooling・family の prior | 推奨（system の prior との整合が条件） |
| FDR | component の段で補助。portfolio の段では不十分 |
| **選択の手続き全体の max-T・経験的な帰無** | 推奨（選択の block） |
| portfolio 単位の bootstrap | 依存を保つ block で補助 |
| nested walk-forward | 推奨（選択の block の内側） |
| deflated / selection-adjusted Sharpe | 報告に使う |
| 実効の strategy の数 | 試行の数の入力（§23） |
| 事後の system の Sharpe | system gate（§30） |
| BMA | 重みには有用、選択の多重性は解かない |

**最も強い防御は、data で component を探さないこと**: 機構と外部の prior（文献）で事前に決め、N を小さく保つ。

## 23. Search-complexity control

**実効の探索の複雑さ**は、全ての自由度の積を相関で割り引いたもの。

| 自由度 | 例 |
| --- | --- |
| 特徴量・signal の規則 | 窓の長さ・閾値 |
| 交互作用 | 状態変数 × 水準 |
| regime | 状態の数・gating |
| 保有期間・exit | horizon・時間 stop |
| pair・通貨の選択 | 対象の集合 |
| 重み | 推定の自由度 |
| 執行 | 注文の種類・timing |
| portfolio への包含 | 2^N の部分集合 |

**Architecture G に固有の自由度の台帳【設計】**（独立レビュー Role 4 の指摘）:

- mechanism ごとの状態変数・g(·) の形・family の τ・family の risk の予算
- Σ の構造（9 つの重なりの選び方と重み）
- λ₁〜λ₃
- 上限（通貨・USD の因子・family・turnover・ES・vol target）
- rebalance の帯・mechanism ごとの μ の減衰の形・cost の表

**これらのうち、seen data を見て決めた値は、全て等価試行数に数える**。文献か事前の規則だけで決めた値だけが、探索の外に置ける。

**管理の設計【設計】**:

1. **探索の台帳**: cycle の前に全ての自由度を列挙し、候補の総数を事前登録する。
2. **予算**: 選択の block の長さで決める。閾値は max-T の z_{α/M} で上がる（10 年で、試行 10 → 20 で z は 2.81 → 3.02、Sharpe の閾値は約 0.07 上がる）。
3. 保有期間・exit・cost・risk の規則・執行は、事前に固定する。
4. ML の暗黙の試行は、交差検証の実効の自由度で数えるか、使わない。
5. 「試したのは 20 本だけ」は安全の根拠にならない。

## 24. Fresh / confirmation architecture

| 方式 | 評価 |
| --- | --- |
| component ごとに順に fresh で試す | fresh を何度も使い、最後の system は無検証の合成になる。**不採用** |
| **全てを development で凍結し、最終の system 全体だけを fresh で 1 回確認** | **推奨** |

**fresh の前に固定するもの**: component・parameter・交互作用・重み・risk の規則・執行の規則・no-trade の規則・cost の model。

**検出力**【合成】: fresh は 4.895 年（fresh pool 2016-06-02 … 2021-04-25）、片側 5%。

| 真の system の Sharpe | 0.5 | 0.7 | 1.0 | 1.3 | 1.5 |
| --- | --- | --- | --- | --- | --- |
| 検出力（SE = 1/√T） | 0.30 | 0.46 | 0.72 | 0.89 | 0.95 |
| 検出力（Lo 2002 の SE） | 0.27 | 0.40 | 0.56 | 0.68 | 0.74 |

**真の system の Sharpe 1.0 でも、検出力は 0.72 以下**（fat tail と自己相関があれば更に下がる）。fresh は programme の名前に依らず全体で 1 回しか使えない（裁定 §7）。

## 25. Candidate system architectures

| 案 | 構造 |
| --- | --- |
| **A. 一枚岩の予測 model** | 全ての情報から直接 position を出す（GBDT / NN） |
| **B. 単一の edge + 掛け算の gate** | edge ごとに regime・cost・確信度を掛ける |
| **C. 足し算の multi-edge portfolio** | edge の予測（pair 単位）を足す |
| **D. mixture of experts** | regime で複数の model を切り替える |
| **E. 階層の hybrid** | edge の中は条件付きの model、edge の間は portfolio の統合 |
| **F. 通貨単位の潜在の alpha** | 通貨の exposure を先に決め、pair は執行の手段 |
| **G. mechanism-first・通貨単位・推定あり** | H に、mechanism ごとの条件付きの μ の推定（状態変数 1 つ、縮小）と family の縮小を加えたもの |
| **H. mechanism-first・通貨単位・推定なし**（**既定の案**） | mechanism が文献の prior で固定した通貨の view を出す → Black–Litterman の形で合成 → 多期間の cost を意識した最適化（pair の保有を決定変数、制約付き）→ 執行。**G から推定の層を除いたもの** |
| I. risk parity of mechanisms | mechanism の間を risk parity で配分（§8 の重みの一形態として H / G に含める） |
| J. 執行の alpha だけ | passive の約定などで cost を下げる。Track 3（#475）で passive の執行は cost を上げた（C′/C 1.28）【記録】ので、単独の案にしない |
| K. cash / no-trade | 比較の基準 |

**taxonomy**（指示 §25、混同しないための区別）:

| 構造 | 中身 | この文書での扱い |
| --- | --- | --- |
| 条件付きの strategy | Trend × Mean Reversion を「trend の状態でだけ平均回帰」と組む。1 つの新しい予測 | 交互作用（§10） |
| multi-strategy の portfolio | Trend の portfolio + 平均回帰の portfolio を同時に持つ | 足し算（§8） |
| mixture of experts | regime が trend なら Trend、range なら平均回帰 | §11 |

## 26. Architecture comparison

H = 良い、M = 中、L = 悪い（overfit・多重性・sample の必要量・実装の複雑さは「少ないほど良い」を H と書く）。

| 基準 | A | B | C | D | E | F | G | **H** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 経済的な解釈性 | L | H | M | M | H | H | H | **H** |
| 交互作用の捕捉 | H | M | L | H | M | L | M | **L** |
| 分散化 | M | L | M | M | H | H | H | **H** |
| 統計的な効率 | L | M | M | L | M | M | L-M | **H** |
| sample の必要量 | L | M | M | L | M | M | L-M | **H** |
| overfit の危険 | L | M | M | L | M | M | **L-M**（E + F + 最適化で、E / F 以下） | **H** |
| 多重性 | L | M | M | L | M | M | **L-M** | **H** |
| cost の意識 | M | M | L | M | M | M | H | **H**（同じ最適化の層） |
| FX 固有の適合 | L | L | L | L | M | H | H | **H** |
| regime への頑健性 | M | L | M | M | M | M | M | **L** |
| 実装の複雑さ | M | H | H | L | M | M | L | **M** |
| 監査性 | L | H | M | L | M | M | M | **H** |
| production の保守性 | L | H | M | L | M | M | M | **M** |
| 追加の data の要求 | L | M | M | L | M | M | M | **H** |
| 既存の repo との互換 | M | H | M | L | M | H | H | **H** |
| AI/ML を安全に使えるか | L | M | M | L | H | H | H | **H** |

- AI/ML を cost・vol・相関に限る方針は、A と D 以外の全ての案に適用できるので、B・C は M、E・F・G・H は H とした。
- **判定の規則**: 表の数え上げでは決めない。**G は、§29 の P2（合成の帰無の検証）で、同じ FWER の下で H より検出力が高い場合にだけ採る**。そうでなければ H。

## 27. Recommended architecture

**推奨: Architecture H を既定とし、G は P2 で H を上回る場合だけ採る。**

**層ごとの合成**（Q4 の答え）:

| 層 | 合成の演算 | 理由 |
| --- | --- | --- |
| mechanism の中 | 文献の prior で固定した条件付きの期待 return（H）。G では、事前登録の 1 つの状態変数で縮小を伴って推定 | edge の強さが状態で変わることを表す。硬い gate は標本を捨てる |
| mechanism の間 | **精度の加重の合成**（予測の誤差の共分散を入れた Black–Litterman の形。一次の近似として足し算） | 別の edge は加法的に貢献するが、相関する予測は二重計上しない |
| 通貨の重複 | 通貨の view と netting | 同じ通貨の bet を重複させない |
| 衝突 | 精度の加重（不一致は Ω の増加） | size を自然に下げる |
| cost・risk・turnover・集中 | **最適化**（cost は取引に、risk は Σ と制約に） | no-trade の帯と交差の項は、掛け算の scalar では作れない |
| 時刻が固定の窓 | **多期間の最適化**（aim portfolio） | entry と exit の時刻が edge |
| no-trade | **portfolio の段**（net の効用 ≤ 0）＋硬い制約（当日決済・週末・rollover・発表の blackout・data の欠損） | 個別に弱くても合わせて正、個別に正でも全部同じ USD なら縮小、を扱える |
| AND | 硬い制約だけ | — |
| 選択（勝者総取り） | 使わない | 情報を捨て、分散を増やす |
| 執行 | pair の保有を決定変数にした同じ最適化（20 pair、時刻と event の cost、2 本の約定のずれの slippage） | 最も安い表現 |

**system の目的【設計】**:

> maximize  Σ_t E[net return] − λ₁·Var − Σ_p c_p(t)|Δx_p| − λ₃·Turnover
> subject to 通貨の上限、USD の因子の上限、family の risk の上限、ES、margin、vol target、当日決済、週末・rollover・発表の制約

- model の不確実性は、目的の項ではなく、μ の縮小（事後の平均）と Ω（予測の誤差の分散）で入れる。
- 評価の量は、事後の system の net Sharpe（G4 の prior を system に課す）と MaxDD。

## 28. Proposed research programme

**前提**: 次の全ては、**裁定 §9 の trigger が成立し、`FXID_REOPEN_REVIEW_PROPOSAL` が Human + ChatGPT に承認された後にだけ**行う。HOLD のままでは行わない。

| Phase | 中身 | 実 data | gate |
| --- | --- | --- | --- |
| P0 | architecture の決定（この文書） | なし | Human + ChatGPT |
| P1 | component の供給の調査と system の上限の解析（§29） | なし | 上限 < 1.0 なら STOP |
| P2 | 合成の pipeline の帰無の検証（H と G、合成 data） | なし | FWER ≤ 10%、検出力の目標 |
| P3 | cost の較正と replication（文献の期間の内側。発見の証拠には使わない） | 別承認（Red） | cost の model の妥当性 |
| P4 | component の推定（独立な推定の block） | 別承認（Red） | component gate |
| P5 | system の合成と凍結 | — | system gate |
| P6 | fresh での system 全体の 1 回の確認 | 別承認（Red） | production gate |

**外部の文献の使い方**（指示 §32）:

| 用途 | 可否 |
| --- | --- |
| 発見の証拠 | 不可 |
| 外部の prior | 可（P1・P4 の縮小の prior。公表の後の減衰の haircut を掛ける） |
| replication | 可（P3） |
| cost の較正 | 可（P3） |
| 執行の検証 | 可（live の約定は production の段の Red） |
| 独立な確認 | 文献の sample の期間と重なる data では不可 |

## 29. Minimal next cycle

**提案（実行しない）**: REOPEN が承認された場合の最初の cycle は、**P1 + P2 だけで、どちらも実 data を読まない**。

**P1（component の供給と system の上限）**:

- 機構を持つ候補を mechanism family ごとに 1 行にまとめ、**既存の判定を引き継ぐ**:

  | family | 既存の判定【記録】 |
  | --- | --- |
  | dollar の日中の W 字（EUR の朝・JPY の仲値の後を 1 family） | `ECONOMICALLY_UNATTRACTIVE`（#503） |
  | 自国時間の顧客の flow | W 字と重なる |
  | 月末の株式ヘッジ | `DUPLICATE_OF_PREVIOUS_RESEARCH`（C05 / S21 停止） |
  | 指標の発表の後の drift | 査読の drift の実証なし、#473 の帰無、S2 保留 |
  | NY 10:00 の option cut・session の引き継ぎ | C03 `NO_DECISION_GRADE_PASS_REGION` |
  | fix の後の反転・東京の仲値の spike・gotobi | M15 では実装不能 |
  | carry・momentum | #497 で `LONG_TERM_HOLD`、日次で FXID の当日決済の範囲外 |

- **過去に RED / HOLD / 停止の判定を受けた mechanism は、その mechanism 自身の REOPEN なしに component として戻れない**（裁定 §12、緩い component gate による復活の禁止）。
- 各 family の文献の効果量（retail の net の推定）に、**公表の後の減衰の haircut**（30〜60%。McLean & Pontiff 2016、J. Finance【文献・この文書では原典を未照合】）を掛け、§21 の重なりで構造化した相関を置き、system の真の Sharpe の上限を解析的に計算する。
- **予想される結論**: 残る family は全て USD を中心にしたもの（S8）で、上限は 1.0 に届かない（§1）。**P1 で STOP になる見込みが高い**。

**P2（pipeline の帰無の検証）**: P1 が上限 ≥ 1.0 を示した場合だけ行う。H と G を合成 data の上で走らせ、選択を含めた portfolio 単位の FWER と検出力を確かめる。G が H を検出力で上回らなければ H を採る。

この 2 つで、**architecture の良し悪し（統計の安全）と、そもそも architecture を使う意味（component の供給）**の両方を、data を読まずに判断できる。

## 30. Stop conditions

architecture の研究そのものの終了条件【設計】。

| # | 条件 | 閾値の案 |
| --- | --- | --- |
| S1 | 機構を持つ正の component の family が足りない | S2 を満たしうる family の組が存在しない（S2 から導く。例えば prior の net 0.3 の family は、平均相関 0.1 でいくつ足しても上限 0.3/√0.1 = 0.95 < 1.0） |
| S2 | system の上限が production の目標に届かない | 公表の後の haircut・構造化した共分散・縮小の後の、system の真の Sharpe の上限 < 1.0 |
| S3 | cost で全て消える | 全ての component が、all-in の現実の cost（時刻と event 別）の後に prior の net ≤ 0 |
| S4 | 交互作用が必要な標本を満たさない | §10 の式で、必要な標本が選択の block を超える（現実の効果量では常に当たる） |
| S5 | 実効の探索の複雑さが予算を超える | 等価試行数が、選択の block で真の Sharpe 1.0 の検出力 0.5 を保てる数を超える |
| S6 | 独立な確認ができない | fresh の検出力（Lo の SE）< 0.5 になる真の system の Sharpe しか見込めない |
| S7 | 必要な標本が非現実的 | 独立な選択と推定の block に、合わせて 15 年を超える data が要る |
| S8 | 実効の breadth が小さすぎる | 全ての component が USD の因子だけに載る、または pair の空間の participation ratio < 3 |

**3 段の gate【設計】**:

| gate | 条件 |
| --- | --- |
| **component gate** | 単位は年率の Sharpe、評価の期間は推定の block の年数。prior は ledger（#496、278 行）の経験 Bayes（τ̂ ≈ 0 に対応する 0 への spike と slab）。component の包含は選択の block の max-T（FWER 10%）に数える。増分の情報は、既存の component に対する残差の IC が片側 5%（max-T の調整の後）で正。cost の stress（×1.5）で正、機構の文書、部分期間の符号の一致は補助。**standalone の Sharpe 1.0 は要求しない**（裁定 §8 の portfolio の注記と整合） |
| **system gate** | **G4 の prior を system の Sharpe に直接課した**事後の system の net Sharpe ≥ 1.0（**G4 は変えない**）。component の prior は、含意する system の prior が G4 の prior と一致するよう較正する。cost の stress、MaxDD ≤ 15%、集中の上限、部分期間の安定 |
| **production gate** | fresh での 1 回の確認、執行の検証、運用の頑健性 |

component gate を緩めて何でも通すことはしない。弱い component を大量に入れると、§22 の偽発見になる。

## 31. Independent reviews

4 つの独立な役（指示 §38）を、別の context で並行して走らせた。source・diff・指示を渡し、互いの結論は渡していない。lead は各指摘を記録・算術・合成の再計算で確かめてから採否を決めた。**全ての役が、修正しても結論（HOLD の維持）は強まるだけだと述べている。**

| 役 | BLOCKER | 主な指摘 | 対応 |
| --- | --- | --- | --- |
| Role 1 Quant System Architect | 0 | (1) A⁺ の射影は全 pair の予測がある時だけ有効。疎な view を歪める（EUR_CHF だけの予測で二乗ノルムの 36% しか残らない）。(2) 足し算は一次の近似で、予測の誤差の共分散による精度の加重が正しい。(3) cost は取引の関数で no-trade の帯を作る、が掛け算にしない本当の理由。(4) 2 段の最適化（通貨 → LP）より、pair の保有を決定変数にした 1 つの最適化。(5) 時刻が固定の component には多期間の最適化が要る。(6) 交互作用の表は cell の平均の SE で、β12 の SE（4σ/√N）ではない。(7) 比較の表が G に有利。H を「G から推定を除いたもの」に定義し直す。(8) Q14 は §29 と整合させ、H を既定に | 全て反映（§8・§9・§13・§17・§19・§10・§25〜§27・Q14）。合成の算術に β12 の要件と疎な view の歪みを追加 |
| Role 2 Statistician | **1** | **B1: component ごとの縮小を足すと、system の暗黙の prior が約 τ√k に緩む（G4 の抜け穴）**。R1: 1.13 は比べる基準が揃っていない。R2: 1.6〜2.6 の出典。R3: 「cell ≥ 600」は循環で楽観的。R4: component gate の単位・水準・prior が不明確。R5: 手続き（帰無の生成・統計量・paradigm・nested WF の位置）が未指定。R6: S1 は S2 と矛盾。R7: 文献の効果量に公表の後の haircut が要る | 全て反映（§22 のベイズの抜け穴と手続きの表、§30 の system gate・component gate、§1 の比べる基準、§10、§29 の haircut、S1 を S2 から導出、fresh の検出力に Lo の SE を追加） |
| Role 3 FX Microstructure | 1（理由づけについて。判定には影響なし） | **B1: 65% は FX の return の性質ではなく、iid の予測の誤差の仮定。netting の利得は同時の保有が要るが、FXID の family は時間が重ならない**。R1: USD の major が常に最安ではない（cross の方が安いもの、合成の cross は約 2 倍）。R2: 時刻の違う spread の転用。R3: cost は取引に、margin の比。R4: 当日決済・週末・発表の制約。R5: 2 区間は時間が重ならず USD の符号が逆。R6: breadth は pair の空間の値。R7: pair に固有なのは cost と jump の risk。R8: P1 の family に既存の判定を引き継ぐ | 全て反映（§13・§19・§18・§17・§1・§29）。介入の risk・live の約定は Red・market maker の気配・25 倍の leverage も追記 |
| Role 4 Adversarial | **2** | **B1: P1 を「HOLD のままの机上の作業」と提案していた（裁定 §10・§11 に反する）**。**B2: 合成の simulation の承認の出典が書かれていない**。R1: G の自由度が探索の台帳に入っていない。R2: 比較の表が G に有利。R3: 停止・HOLD の mechanism が緩い component gate で戻る。R4: 「裁定 §40」は指示の節の誤記、#504 の provenance の欠落。R5: JPY 0.85 の出典。R6: 「交互作用を事前登録したことは無い」は過大（#471）。R7: ARCH-D は判定を良く見せる造語で、実質は ARCH-C | B1: P1・P2 は REOPEN の承認の後だけと明記し、判断依頼 3 を書き換えた。B2: 指示 §36 の許可（synthetic / analytic calculation）を冒頭と script に明記。R7: **最終判定を ARCH-C にした**。他も全て反映（§23 の G の自由度の台帳、§26、§29 の引き継ぎと復活の禁止、§6 の文言、冒頭の provenance、synthetic.py は PAIRS を hardcode して data の module を import しない） |

**合成の記録の再生成**: 独立レビューの指摘で `synthetic.py` を直し（β12 の要件、疎な view、Lo の SE、PAIRS の hardcode、未使用の IC の表の削除）、merge の前の `synthetic.json` を作り直した（記録の上書きの禁止は、merge 済みの記録に適用する）。

**修正の後の再監査**: 新しい context で確認した（結果は PR の本文に記録する）。

## 32. Human + ChatGPT decision requests

1. **最終判定**: ARCH-C `COMPOSITION_DOES_NOT_SOLVE_THE_FUNDAMENTAL_LIMITATION` を採るか（HOLD を維持する）。
2. **設計の基準の記録**: Architecture H を既定とし、G を P2 の条件付きとする構造（§27）と、統計の設計（§22〜§24・§30。G4 の prior を system に直接課すこと、選択の block の max-T、独立な推定の block の事後 system Sharpe、fresh は system に 1 回）を、**将来の `FXID_REOPEN_REVIEW_PROPOSAL` が承認された場合の設計の基準**として記録するか（HOLD は解除しない）。
3. **再開の後の最初の cycle**: §29 の P1・P2（実 data を読まない）を、**REOPEN が承認された後の最初の cycle の案**として記録するか（HOLD の間は行わない）。

### 必須の回答（指示 §40）

| 問い | 回答 |
| --- | --- |
| Q1. strategy の単位で研究するのが正しいか | **正しくない**。原子は mechanism family が出す通貨の期待 return の view（§4・§5） |
| Q2. pair ではなく通貨の exposure を基本の単位にすべきか | **すべき**。FX の return は既に 7 次元の通貨の空間にあり、通貨の view は重複を解く。pair に固有なのは執行の cost と jump の risk（§13）。ただし FXID の当日決済の範囲の既知の family は時間が重ならず、netting の利得は小さい |
| Q3. 足す・掛ける・選ぶ のどれか | 層による。**edge の中は条件付けの掛け算（soft・縮小）、edge の間は精度の加重の合成（一次の近似として足し算）、最終は最適化**。選択（勝者総取り）は使わない。AND は硬い制約だけ |
| Q4. どの層を足し算・掛け算・最適化にするか | §27 の表 |
| Q5. 単独で edge の無い signal の交互作用を安全に検証する方法 | 経済的な理由の事前の記述、β12 の直接の検定、次数 ≤ 2、縮小、多重性の計上、必要な標本の事前の計算（§10）。**ただし現実の効果量では、1 日 1 回の intraday で数百年の data が要り、事実上検証できない** |
| Q6. 過去に特徴量・filter の組み合わせと strategy の組み合わせをどこまで試したか | 特徴量・filter・meta-label・Top-K は豊富（負か、検出力不足か、無効）。**機構の組み合わせは #497 の 1 本だけ**。β12 の直接の検定の事前登録は無い（§6） |
| Q7. multi-mechanism の system は実質的に未検証か | **実質的に未検証**。理由は、正の component の供給が無かったこと。未検証は有望を意味しない（§1） |
| Q8. strategy の ensemble より、通貨単位の予測の集約の方が合理的か | **合理的**（rank の議論による事前の支持）。Track 1 の負は signal の負で、architecture の反証ではない |
| Q9. AI / ML をどの層に置くか | **cost・slippage・vol・相関の予測**。方向の予測・meta-label・合成の重みには置かない（§16） |
| Q10. component に standalone の Sharpe 1.0 を要求すべきか | **要求しない**。ただし component gate は、ledger の経験 Bayes の prior・max-T の計上・残差の IC で厳しく置き、**G4 の prior は system の Sharpe に直接課す**（§30） |
| Q11. component の価値を限界的な portfolio の価値で評価すべきか | **すべき**。共分散は構造の重なり（§21）で作り、包含の決定を多重性に数える |
| Q12. 弱い component を多数集める時の偽発見をどう防ぐか | data で component を探さない、選択の block の max-T、nested walk-forward は選択の内側だけ、独立な推定の block の system の事後、component の prior を system の prior に整合させる（§22）。真の 0 の 100 本から in-sample 2.03 を作れる |
| Q13. fresh は最終の system 全体に使うべきか | **すべき**。全てを凍結してから 1 回（§24）。真の 1.0 でも検出力は 0.72 以下 |
| Q14. 推奨する architecture | **H を既定**（mechanism-first・通貨単位・文献の prior で固定・多期間の cost を意識した最適化）。**G は P2 で H を上回る場合だけ** |
| Q15. それを最小の cost で否定・支持する次の cycle | **P1（component の供給と system の上限）+ P2（pipeline の帰無の検証）**。実 data を読まない。**REOPEN が承認された後にだけ**行う。P1 で STOP になる見込みが高い（§29） |

---

**STOP（指示 §42）。** HOLD は解除しない。Human + ChatGPT の承認なしに merge しない。
