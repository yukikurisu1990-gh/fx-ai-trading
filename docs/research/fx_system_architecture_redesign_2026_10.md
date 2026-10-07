# ARCHITECTURE_NEUTRAL_FX_SYSTEM_REDESIGN — FX 自動売買 system の合成原理のゼロベース設計（2026-10-07）

**DESIGN ONLY · `NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` · `PRODUCTION_READINESS_NOT_CLAIMED`.**

**authoritative な state は変わらない: `FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE`**（`docs/governance/fxid_long_term_hold_ruling_2026_10.md`）。この文書は HOLD を解除せず、`FXID_REOPEN_REVIEW_PROPOSAL` でもない。研究を再開するとしたら、どの system architecture で行うのが最も合理的かを決めるための設計研究である。

**記号**:

| 記号 | 意味 |
| --- | --- |
| 【記録】 | repo の既存の報告・記録 |
| 【合成】 | `artifacts/research/architecture_redesign/synthetic.json`（`scripts/research/architecture_redesign/synthetic.py`、data を読まない合成と解析） |
| 【算術】 | この文書の計算 |
| 【設計】 | 提案 |

---

## 1. Executive Summary

**最終判定（提案）: ARCH-D — `ARCHITECTURE_SPECIFIED_BUT_COMPONENT_SUPPLY_IS_BINDING`**（ARCH-C の結論に、再開の時の設計の基準を加えたもの）。

1. **合成の構造の問いには答えが出る**。推奨は **Architecture G: mechanism-first・通貨単位・階層の予測の集約 + cost を意識した最適化**（§25・§27）。

   | 層 | 合成の仕方 |
   | --- | --- |
   | mechanism の中 | 事前登録した 1 つの状態変数による**条件付きの期待 return**（縮小を伴う掛け算・soft） |
   | mechanism の間 | **期待 return の空間での足し算**（family ごとの縮小と risk の予算） |
   | 重複の解消 | **通貨の exposure で netting** |
   | 最終の position と no-trade | **最適化**（net の効用、cost・turnover・上限・ES の制約） |
   | 執行 | 最も安い pair の表現を選ぶ |

   AND の gate は、cost・rollover・流動性の**硬い制約**にだけ使う。勝者総取りの選択は使わない。

2. **しかし合成の構造は、現在の根本の制約を解かない**。足し算・掛け算・ensemble・通貨の netting は、**正で・機構を持ち・cost の後に残る component**が複数あって初めて効く。

   | 指標【合成・記録】 | 値 |
   | --- | --- |
   | 近い 2 区間（EUR の朝 0.2〜0.75、JPY の仲値の後 約 0〜0.85）を最適に合成した上限 | 相関 0 で 1.13、0.3 で 1.00、0.5 で 0.93 |
   | 実際の関係 | どちらも同じ「dollar の日中の W 字」の機構の一部で、相関と機構の重なりは小さくない |
   | 事後の Sharpe 1.0（G4）に要る観測 | 1.6〜2.6【記録】。届かない |
   | #496 の算術【記録】 | s ≈ 0.07 の source をいくら足しても、上限は 0.22（ρ = 0.1） |

3. **最大の危険は、architecture の名前で偽発見を増やすこと**。【合成】真の Sharpe が全て 0 の候補 100 本から、in-sample の上位 5 本を等 risk で組むと:
   - in-sample の portfolio の Sharpe は平均 **2.03**
   - 独立な期間では **−0.003**

   「低相関の弱い component を集めると Sharpe 1.0」は、選択を含めた統計の設計なしには、ほぼ確実に偽物である。

4. **過去研究**【記録】:
   - 特徴量の組み合わせと gate の組み合わせは豊富（全て負か、検出力不足）。
   - **mechanism の違う component を同時に保有して portfolio として評価したのは #497 の 1 本だけ**（carry + momentum、TC-net 0.127、検出力不足、carry が 99%）。
   - 通貨単位の architecture は Track 1（#481）で 1 回試したが、**signal が gross で負**だったので、architecture の評価にはなっていない。
   - **交互作用を交互作用として事前登録したことは一度も無い**。
   - multi-mechanism の system は「実質的に未検証」と言えるが、未検証の理由は見落としではなく、**正の component の供給が無かった**ことにある。
5. **結論**: HOLD を維持する。推奨の architecture（G）と、その統計の設計（§22〜§24・§30）を、将来の `FXID_REOPEN_REVIEW_PROPOSAL` の基準の設計として記録することを提案する。次の最小の cycle（§29）は data を読まない。

## 2. What is an edge?

**定義【設計】**: edge とは、**情報集合 I_t の下での、ある通貨（または通貨の組）の、ある horizon h の条件付きの期待 return が、取引の cost を含めた 0 と違うこと**: E[r_{t→t+h} | I_t] ≠ 0、かつ |E[·]| > cost。

- edge は**情報・horizon・cost の 3 つ組**に付く性質で、「strategy」や「pair」には付かない。
- **経済的な edge** と**統計的な edge** を分ける。経済的な edge は「誰が・なぜ・いつ」その期待 return を支払うか（risk premium・dealer の在庫の対価・需要の集中）の説明を持つ。統計的な edge は、それを持たない。この programme は前者だけを component にする。

## 3. What is a signal?

**定義【設計】**: signal とは、**時刻 t に観測できる量を、edge の予測（期待 return の推定）に写す関数**の出力。`s_t = f(I_t)`。

- 単位は「期待 return / σ」（予測の強さ）であるべきで、BUY / SELL のような離散の命令ではない。
- 離散化（閾値）は、情報を捨て、閾値を自由度として加える。最終の position の段階まで遅らせる。

## 4. What is a strategy?

**定義【設計】**: strategy とは、次の **複合物**である: 情報集合・予測・timing・entry・exit・sizing・執行を、1 つの取引の規則に**束ねた**もの。

**結論**: **strategy は研究の原子として不適切**。理由は次の 4 つ。

- (a) 1 つの strategy は複数の自由度（閾値・保有期間・gate）を内蔵し、探索の数を隠す。
- (b) 同じ edge が別の strategy として何度も数えられる（例: §5 の 3 pair）。
- (c) strategy どうしの衝突と重複は、最終の position の前に解かなければならない。
- (d) cost と risk は、strategy ごとではなく portfolio で決まる。

**EUR の欧州の朝の short の分解**:

| 層 | この例での中身 |
| --- | --- |
| mechanism（経済的な edge の源泉） | dealer が fix での dollar の需要を在庫で受け、その対価を取る（KMW の W 字）。および自国の取引時間の顧客の flow（B&R） |
| 予測（alpha forecast） | 02:00〜08:15 ET の EUR の対 USD の期待 return < 0 |
| 執行の schedule | 02:00 に入り、08:15 に出る |
| strategy | 上の 3 つを束ねて、EUR_USD で取引したもの |

**JPY の仲値の後も、同じ機構の family の別の時刻の予測**であり、独立な strategy ではない。

## 5. What is a portfolio component?

**定義【設計】**: portfolio component とは、**1 つの mechanism family が出す、通貨単位の期待 return の vector（と、その不確実性）**。`μ^m_t ∈ R^8`（8 通貨、合計の制約で自由度 7）、horizon h_m、予測の分散 Σ^m_μ。

- component は**取引しない**。取引するのは、全ての component を集めた後の最適化だけ。
- component の単位は mechanism family で、strategy でも pair でもない。同じ機構の時刻の違う予測（EUR の朝・JPY の仲値の後）は、**1 つの component の中の別の要素**として扱い、別の component として数えない。

## 6. What previous research actually combined

【記録】repo の文書の監査（pre-R1 の結果は C-8 により文脈だけ）。

| 類型 | 代表的な研究 | 状態 | 結果 |
| --- | --- | --- | --- |
| **A. 特徴量の組み合わせ** | Phase 9 の LightGBM（C-8、leakage で無効）、Phase 27–29（C-8）、ML Step 4（C-8）、Round 1 の family H（#464、57 variant）、Track 1 の ridge、B′ の線形 | 検定済み | 全て負か、検出力不足（Round 1 H は family-wise の p = 0.699）。B′ は損益分岐の IC の 6〜16% |
| **B. filter / gate** | Round 1 の session・ATR・ADX・spread の gate、Round A の 39 cell（周辺のみで、交差なし）、#471 の carry × tick 量 | 検定済み | gate は全て net を下げた。Round A は 0/39（帰無の通過率 0.227） |
| **C. meta-label** | Phase 22.0e（C-8）、Round 1、#479 M13 | 検定済み | 全て負の base の上。#479 は「負の base への filter は何も証明しない」の kill 規則が発火 |
| **D. strategy の選択・Top-K** | Phase 9.17 / 9.19（C-8、無効）、Phase 28 A4（C-8）、#479 M01 | 検定済み | 負か無効 |
| **E. strategy の ensemble** | Phase 9.17 の selector（C-8）・Phase 28.0c AR3 の stacking（C-8）が走った唯一のもの。#480 A15 / A03 は設計だけ | ほぼ無い | 負か、設計のみ |
| **F. multi-family の portfolio** | **#497（carry + 12-1 momentum、等 risk、8 通貨、ECB 2000–2016）だけ**。#496 は算術だけ。#490 の 5 本は凍結したが**個別に評価** | 1 本だけ | TC-net 0.127（t ≈ 0.5）、judged 0.340。carry が 99%、2008 年以降は約 0。検出力不足 |
| **G. 通貨単位の portfolio** | Track 1（#481）。#478 以降は通貨の book が標準の harness（各 signal は単独で載せた）。#494 の M15 / M16 は book の欠陥で無効、#495 で修正 | 検定済み（signal は単独） | Track 1: net −0.84、**gross −0.47**（signal が負）。M16（修正後）は 0.276 の positive-exploratory |
| regime / MoE | Phase 28.0c AR1〜AR4（C-8、全て反証）、#479 M03（設計の欠陥で未検定）、M10 HMM（未実行） | 学習した gating は未検定 | — |
| 交互作用 | **事前登録の交互作用は一度も無い**（Round A は意図的に周辺のみ、B′ は「交互作用なし」を事前登録） | 未検定 | — |
| exit | Phase 24 の 87 cell（C-8。trailing 33・部分決済 27・regime 27）、Phase 9.18（C-8） | intraday のみ | 87 cell 全て REJECT（`still_overtrading`）。post-R1 は固定の horizon だけ。multi-day の barrier は未検定 |

## 7. Feature combination vs strategy combination

| 区別 | 中身 | 過去研究での量 |
| --- | --- | --- |
| 特徴量の組み合わせ（A） | 1 つの予測の入力を増やすこと。**1 つの edge の推定を改善しようとする**もので、分散化ではない | 豊富 |
| filter / gate（B）と meta-label（C） | 1 つの edge を**条件付きで使う**こと。分散化ではない | 豊富 |
| strategy の組み合わせ（D・E・F） | **別の edge を同時に持つ**こと。分散化はここだけ | ほぼ無い |

「indicator を複数使った」を「strategy の分散化を試した」と数えてはいけない。**この programme が分散化を試したのは、実質 #497 の 1 回**である。

## 8. Additive composition

`position ∝ Σ_m w_m · μ^m`

- **何を足すか**: 期待 return（予測）を足す。取引の命令や BUY / SELL の票を足さない。
- **重みの決め方の候補**:

  | 方式 | 自由度 | 安全性 |
  | --- | --- | --- |
  | 等 risk（事前に固定） | 0 | 最も安全。#497 はこれ |
  | prior の強さの比（文献の効果量で事前に固定） | 0 | 安全。外部の prior を使う（§32） |
  | 推定した平均・分散（mean-variance） | 多い | 推定誤差に弱い。縮小が必須 |
  | 推定した予測の精度（IC で重み付け） | 中 | 縮小と組で |

- **FX 固有の注意**: 足す前に、**通貨の空間へ射影**する（§13）。pair の予測をそのまま足すと、同じ通貨の bet を重複して数える。

## 9. Multiplicative composition

`adjusted_μ = μ_base · g(state) · c(cost) · …`

- **掛け算が正しいのは、1 つの edge の強さが状態によって変わる時**（例: dealer の在庫の対価は vol に比例する）。別の edge を掛けると、意味の無い積になる。
- **硬い掛け算（0 / 1 の gate）は標本を捨てる**。p の割合の標本だけが残ると、検出の SE は 1/√p 倍になる（§10）。
- **soft な掛け算（連続の g）は自由度を加える**。g の形を事前に固定するか（例: σ に比例）、縮小を伴う推定にする。
- **cost と risk は掛け算ではなく、最適化の項と制約で扱う**（§18〜§20）。cost を μ に掛けると、cost が小さい時に過大な position を取る。

## 10. Interaction effects

**理論**: E[R | A] = E[R | B] = 0 でも E[R | A, B] > 0 はありうる（XOR 型）。「単独で弱いものの組み合わせに意味は無い」とは言えない。

**検出の代償**【合成】（binary の状態変数、1 日 1 回 × 10 年 = 2,500 trade、片側 5%・検出力 80%）:

| 次数 | cell の標本の割合 | cell の trade | MDE（trade あたり net の平均 / σ） | 効果 0.1 での検出力 |
| --- | --- | --- | --- | --- |
| 0（base） | 1 | 2,500 | 0.050 | 1.00 |
| 1 | 1/2 | 1,250 | 0.070 | 0.97 |
| 2 | 1/4 | 625 | 0.100 | 0.80 |
| 3 | 1/8 | 312 | 0.141 | 0.55 |

**多重性**【合成】: 10 個の binary の状態変数の場合。

| 次数 | 組み合わせ | cell |
| --- | --- | --- |
| 1 | 10 | 20 |
| 2 | 45 | 180 |
| 3 | 120 | 960 |

**本物の交互作用と事後の filter の区別【設計】**:

1. **経済的な理由を事前に書く**（「なぜ A と B が同時の時だけ支払われるか」）。理由の無い交互作用は候補にしない。
2. **交互作用の項を直接検定する**（factorial の回帰: r = β0 + β1·A + β2·B + β12·A·B）。cell の中の平均だけを見ない。β12 が主効果と区別して有意であること。
3. **次数の上限**は §27。
4. **階層の縮小**: 交互作用の係数を 0 に向けて縮小する（prior の SD を主効果より小さく）。
5. **最小の標本**: cell の trade ≥ 600（次数 2 で 10 年、1 日 1 回の場合）。満たさない交互作用は検定しない。
6. **多重性**: 検定した全ての交互作用の cell を、max-T の候補の数に数える。
7. **過去の gate の再探索の禁止**: H-002・Round 1 の gate・Round A の 39 cell と同じ変数・同じ水準の組み合わせを、名前を変えて検定しない（重複の登録簿と照合する）。

## 11. Mixture-of-experts

`forecast = Σ_k P(regime_k | I_t) · model_k`

- **利点**: 状態で予測の仕組み自体が変わる時（trend ↔ range）に、1 つの model より適切。
- **危険**: model の数 × gating の自由度。gating を学習すると、暗黙の探索が増える（§28）。
- **過去**: 決定論的な分割（Phase 28 AR4、C-8）は最悪（−0.405）。学習した gating は未検定。
- **評価【設計】**: MoE は、**各 expert が単独で正の component として事前に成立している場合**だけ候補にする。expert が負の時に gating で救うのは、meta-model による救済の禁止に当たる。状態は 2 つまで、gating の変数は事前登録の 1 つ。

## 12. Hierarchical architecture

経済的な edge → 状態の条件付け → cost の条件付け → 確信度 → position の提案 → 通貨の netting → portfolio の risk の管理 → 執行。

- **評価**: 各層の役割を分けると、監査と自由度の数え上げがしやすい。ただし**層ごとに閾値を置くと、自由度が層の数だけ掛け算で増える**。
- **設計の原則【設計】**:
  - 推定する層は 2 つまで: mechanism の中の条件付きの μ と、mechanism 間の縮小。
  - 残りの層（cost・risk・netting・執行）は**事前に固定した規則か、最適化の制約**にする。
  - 確信度は、別の層ではなく**予測の不確実性 Σ_μ**として扱う。

## 13. Currency-level architecture

**射影**【合成】:

- 20 pair × 8 通貨の incidence 行列 A（pair の long = base +1・quote −1）の rank は **7**。
- 通貨の因子で説明できる pair の予測は、7 次元に収まる。
- 等分散・独立な pair 固有の雑音は、通貨の空間への射影で **65% が除かれる**（残りは 7/20 = 35%）。

**重複の例**【合成】: EUR_USD long + USD_JPY short + EUR_JPY long の 3 つの「strategy」は、通貨の exposure では **EUR +2・USD −2** で、JPY は相殺し、**1 つの bet の 2 倍**にすぎない。

**設計【設計】**:

- signal → 通貨の期待 return（z = A⁺ f、または mechanism が直接通貨で出す）→ 通貨の目標 exposure → pair の表現（§19）。
- **portfolio の原子は通貨にする**。

**例外と限界**:

- pair に固有の機構（EUR/CHF の floor、cross の局所の flow、ある pair だけの fix の慣行）は、通貨の因子に収まらない。**事前登録した pair の残差の component** としてだけ許す。
- 通貨の空間でも、USD の因子（PC1）が大きい（Cycle 1 の participation ratio は約 5、第 1 固有値の割合は約 0.32【記録】）。7 自由度は、独立な 7 つの bet ではない。
- Track 1（#481）は通貨の book で負だったが、**gross が負の signal だった**ので、通貨の architecture の反証ではない【記録】。

## 14. Signal conflicts and netting

例: 平均回帰 → EURUSD long、fix flow → EURUSD short、macro → USD long。

| 処理 | 評価 |
| --- | --- |
| 相殺（cancel out） | 期待 return の空間で足せば自然に起こる。**推奨（ただし予測の単位を揃えてから）** |
| 強い方が勝つ | 情報を捨て、閾値の自由度を足す。非推奨 |
| 確信度の加重和 | 確信度が予測の分散なら、ベイズの合成と同じ。推奨の形 |
| 期待 return の加重和 | 推奨（上と同じ） |
| 優先順位 | 監査しやすいが、恣意的。非推奨 |
| no-trade | 最適化で、合成した期待の net が cost を超えなければ自然に起こる |
| **通貨の exposure で netting** | **推奨**（§13） |
| 最適化に渡す | **推奨**（最終の段） |

**意見の不一致の情報**:

- 不一致は、**予測の分散（不確実性）の増加**として扱う。合成の μ が小さくなり、Σ_μ が大きくなれば、最適化は自然に size を下げる。
- 「不一致そのものを signal にする」（例: 不一致の時は vol が上がる）は、別の component の仮説で、事前登録が要る。

## 15. Regime architecture

| 方式 | 統計的な性質 | 評価 |
| --- | --- | --- |
| **硬い gate** `α · I(regime)` | 標本を p 倍に減らし、SE は 1/√p 倍。閾値が自由度 | 経済的に明確な場合だけ（例: rollover の前後は取引しない＝cost の制約） |
| **mixture** `Σ P(k) α_k` | expert × gating の自由度 | §11 の条件付きで |
| **条件付きの期待 return を直接推定**（状態を共変量にした縮小の回帰） | 全ての標本を使い、状態の効果を 0 に向けて縮小する（部分 pooling） | **最も安全。推奨** |

**trade-off の扱い【設計】**: 状態の効果は、**階層 model の部分 pooling**で推定する（状態ごとの効果を、全体の効果に向けて縮小する）。硬い gate の標本の損失も、自由な soft weighting の過学習も避けられる。状態変数は mechanism ごとに 1 つまで、事前登録する。

## 16. AI/ML placement

| 位置 | 多重性・過学習の危険 | 外部の検証 | 評価 |
| --- | --- | --- | --- |
| 価格の方向の直接の予測 | 最大（暗黙の交互作用の探索） | 難しい | **使わない**（Round 1 H・Phase 9・ML Step 4 は全て負か無効【記録】） |
| 期待 return の推定（mechanism の中） | 中〜大 | 中 | 事前登録の 1 つの状態変数の縮小の回帰まで。GBDT は使わない |
| edge が働く確率・no-trade の判断・meta-label | 大。負の base の救済になりやすい | 難しい | **base が正の時だけ**。今は使わない |
| regime の推定 | 中 | 中 | 状態変数の推定（vol の状態など）に限る |
| signal の合成・strategy の重み | 大 | 難しい | **ML にしない**。縮小と事前の重み |
| **cost の予測・slippage の予測** | 小（目的変数が方向ではない） | **易しい**（執行の data で検証できる） | **推奨** |
| **vol の予測・相関の予測** | 小 | 易しい | **推奨**（risk の層） |
| portfolio の配分 | 中 | 中 | 最適化（解析）で十分。ML にしない |
| 執行の timing | 小〜中 | 執行の data で | 将来の候補 |

**原則**:

- **ML を alpha の源泉にする architecture と、複数の経済的な mechanism を ML が統合する architecture を分ける**。前者は使わない。後者も、統合の重みは ML ではなく縮小で決める。
- ML は、**方向ではない量（cost・vol・相関・slippage）**の予測に置く。
- 負の base を meta-model で救うことは禁止。

## 17. Exit architecture

| exit | 分類 | 扱い |
| --- | --- | --- |
| 時間 stop | **edge の一部**（mechanism の horizon） | mechanism ごとに事前に固定（§15 の horizon の思想） |
| barrier（TP / SL） | **risk の管理** | portfolio の risk の制約で扱う。exit を edge の源泉にしない |
| regime の変化 | 予測の更新 | 最適化の再計算で自然に起こる |
| alpha の減衰 | 予測の更新 | 同上（μ が時間で減る形を mechanism ごとに事前に固定） |
| 反対の signal | 予測の更新 | 同上（期待 return の空間で netting） |
| portfolio の rebalance | 執行の方針 | turnover の制約・band |

**結論**: Architecture G では、**exit は独立した component ではない**。position は、目標の exposure が変わった時に変わる（rebalance）。「exit を工夫して負の alpha を正にする」ことはできない（Phase 24 の 87 cell は全て REJECT【記録】）。一方で、「exit は全部終わった」とも言えない（multi-day の barrier は未検定、post-R1 は固定の horizon だけ【記録】）。

## 18. Risk architecture

risk は、μ に掛ける scalar ではなく、**最適化の目的と制約**で扱う。

- **目的**: 分散（または ES）の罰則。
- **制約**:
  - 通貨ごとの exposure の上限
  - USD の因子（PC1）の exposure の上限
  - 1 つの mechanism family の risk の予算の上限（集中の制約）
  - turnover の上限
  - ES / tail の制約
  - margin
  - portfolio の vol target
- **Σ（共分散）**: 標本の相関ではなく、**構造化した推定**を使う（通貨の因子 + 時刻の重なり + 流動性の shock の共通の因子）。§21 の「低相関 = 独立ではない」を反映する。

## 19. Execution architecture

**alpha の層と執行の層を分ける【設計】**:

| 層 | 決めること |
| --- | --- |
| alpha の層 | 通貨の目標 exposure（何を、どちら向きに、どれだけ） |
| 執行の層 | どの pair を、いつ、どの注文の種類で、どれだけの cost で |

**最も安い表現**:

- 8 通貨の任意の exposure は、**USD を含む 7 つの major の pair**（EUR_USD・GBP_USD・AUD_USD・NZD_USD・USD_CAD・USD_CHF・USD_JPY）で張れる（全域木）【算術】。
- これらは PAIRS_20 の中で spread が概ね最も低い群に入る（R-A2b の 09:00 の往復: USD_JPY 1.17、GBP_USD 1.41、EUR_USD 1.36、AUD_USD 1.95、NZD_USD 2.54 bp【記録】）。
- cross は、cost が低い場合か、pair に固有の component の場合だけ使う。
- 最適な表現は、min Σ cost_p |x_p| s.t. Aᵀx = z の線形計画で求める【設計】。

**今回は設計だけ**で、実 data の取得・broker の接続はしない。

## 20. Component value vs standalone Sharpe

component の価値は 5 つの面で測る【設計】。

| 面 | 量 |
| --- | --- |
| standalone | E[R_i]、Sharpe_i（cost の後） |
| conditional | E[R_i \| state]（事前登録の状態だけ） |
| incremental | 既存の portfolio に足した時の ΔE[R]、ΔSharpe、ΔMaxDD、ΔES |
| information | 既存の component で説明できない return を、どれだけ説明するか（部分相関・残差の IC） |
| capital | margin・turnover・執行の cost あたりの貢献 |

**数式の要点**【算術】:

- 2 本の最適な合成の Sharpe = √((s1² + s2² − 2ρ s1 s2) / (1 − ρ²))。
- standalone 0.3 でも、ρ < 0 の相手には大きく貢献する。
- standalone 0.8 でも、既存と ρ ≈ 1 なら増分はほぼ 0。

## 21. Marginal portfolio value

**原則【設計】**: component の採否は、**限界的な portfolio の価値**で判断する。ただし、限界の価値は standalone より**推定の誤差が大きい**（共分散の推定が加わる）。

- 限界の価値の分母の共分散は、標本の相関ではなく、**構造の重なり**から作る:

  | 重なり | 中身 |
  | --- | --- |
  | return の相関 | 標本の値 |
  | tail の相関 | 下側の同時の発生 |
  | 通貨の因子の重なり | 同じ通貨の exposure（§13） |
  | 時刻の重なり | 同じ時間帯に position を持つ |
  | 流動性の重なり | 同じ流動性の shock（rollover・週末・指標の発表）に晒される |
  | macro の exposure | risk-on / off、USD の資金の逼迫 |
  | vol の状態の exposure | 高 vol で同時に壊れる |
  | 機構の重なり | 同じ経済的な説明（例: EUR の朝と JPY の仲値の後は同じ dollar の W 字） |
  | drawdown の重なり | DD の期間の一致 |

- **「低相関 = 独立」とは扱わない**。return の相関が 0.1 でも、同じ USD の流動性の shock で壊れるなら、分散化ではない。
- 限界の価値の推定の誤差を、**component の数 × 包含の決定**として、選択の多重性に数える（§22）。

## 22. False-discovery risk

**中心の問題**【合成】: 真の Sharpe が全て 0 の候補から上位 k 本を選んで、等 risk で組んだ場合（約 5 年、400 回の反復）。

| 候補 N | 選ぶ k | 共通因子の相関 | 選んだ component の in-sample の Sharpe | **portfolio の in-sample の Sharpe** | 独立な期間 |
| --- | --- | --- | --- | --- | --- |
| 20 | 5 | 0 | 0.56 | **1.24** | 0.00 |
| 100 | 5 | 0 | 0.91 | **2.03** | 0.00 |
| 100 | 10 | 0 | 0.79 | **2.48** | −0.01 |
| 100 | 5 | 0.3 | 0.76 | **1.15** | 0.00 |

**低相関の弱い component を集めることは、偽発見の portfolio を作る最も効率的な方法**である。component を増やすほど、in-sample の portfolio の Sharpe は上がる（√k）。

**比較【設計】**:

| 方法 | この構造への適合 |
| --- | --- |
| 階層 Bayes・部分 pooling・family の prior | **推奨**（component の効果を family と全体に向けて縮小。外部の文献を prior にできる） |
| FDR | component の段では有用、portfolio の段では不十分（選択の後の合成を扱わない） |
| max-T・経験的な帰無 | **推奨**（**選択の手続き全体**を帰無の data で回し、in-sample の portfolio の Sharpe の帰無の分布を作る＝portfolio 単位の max-T） |
| portfolio 単位の bootstrap | 依存を保つ block の bootstrap で補助 |
| nested walk-forward | **推奨**（選択・重み・包含を内側で再実行し、外側で評価） |
| deflated Sharpe・selection-adjusted Sharpe | 報告に使う（試行の数の入力が要る） |
| 実効の strategy の数 | 試行の数の入力（§23） |
| 事後の portfolio の Sharpe | **system gate の量**（§30） |
| BMA | 重みの決定には有用だが、選択の多重性は解かない |

**最も強い防御は、data で component を探さないこと**: component を、事前に機構と外部の prior（文献）で決め、N を小さく保つ。

## 23. Search-complexity control

**実効の探索の複雑さ** = 全ての自由度の積を、相関で割り引いたもの。

| 自由度 | 例 |
| --- | --- |
| 特徴量・signal の規則 | 窓の長さ・閾値 |
| 交互作用 | 状態変数 × 水準 |
| regime | 状態の数・gating |
| 保有期間 | horizon の候補 |
| pair・通貨の選択 | 対象の集合 |
| 重み | 推定の自由度 |
| gate・exit | 閾値・種類 |
| 執行 | 注文の種類・timing |
| portfolio への包含 | 2^N の部分集合 |

**管理の設計【設計】**:

1. **探索の台帳**: cycle の前に、全ての自由度を列挙し、候補の総数を事前登録する（Cycle 1 の max-T の等価試行数の方法）。
2. **予算**: 選択の block の長さで決める。10 年・試行 20 なら、検出力 0.73（真の 1.0）【記録 Cycle 1】。試行を 2 倍にすると、閾値はおよそ 0.1 上がる。
3. **固定するもの**: 保有期間（mechanism ごとに 1 点）・exit（時間 stop）・cost・risk の規則・執行は事前に固定し、探索の自由度に入れない。
4. **ML の暗黙の試行**は、交差検証の実効の自由度で数えるか、使わない（§28）。
5. 「試したのは 20 本だけ」は安全の根拠にならない。数えるのは自由度の総数。

## 24. Fresh / confirmation architecture

**比較**:

| 方式 | 評価 |
| --- | --- |
| component ごとに順に fresh で試す | fresh を何度も使い、最後の system は無検証の合成になる。**不採用** |
| **全てを development で凍結し、最終の system 全体だけを fresh で 1 回確認** | **推奨** |

**fresh の前に固定するもの**: component・parameter・交互作用・重み・risk の規則・執行の規則・no-trade の規則・cost の model。

**検出力**【合成】: fresh 4.9 年、片側 5%。

| 真の system の Sharpe | 0.5 | 0.7 | 1.0 | 1.3 | 1.5 |
| --- | --- | --- | --- | --- | --- |
| 検出力 | 0.30 | 0.46 | 0.72 | 0.89 | 0.95 |

**system の真の Sharpe が 1.0 でも、3 回に 1 回は fresh で落ちる。** fresh は programme の名前に依らず全体で 1 回しか使えない（HOLD の裁定 §7）。

## 25. Candidate system architectures

| 案 | 構造 |
| --- | --- |
| **A. 一枚岩の予測 model** | 全ての情報から直接 position を出す（GBDT / NN） |
| **B. 単一の edge + 掛け算の gate** | edge ごとに regime・cost・確信度を掛ける |
| **C. 足し算の multi-edge portfolio** | edge の予測（pair 単位）を足す |
| **D. mixture of experts** | regime で複数の model を soft / hard に切り替える |
| **E. 階層の hybrid** | edge の中は条件付きの model、edge の間は portfolio の統合 |
| **F. 通貨単位の潜在の alpha** | 通貨の exposure を先に決め、pair は執行の手段 |
| **G. mechanism-first・通貨単位・階層の予測の集約 + 最適化（E と F の統合）** | mechanism ごとに通貨の期待 return の vector を出す（事前登録の 1 つの状態変数で条件付け、縮小）→ 共通の予測の層（horizon と vol の正規化、family の縮小）→ 通貨の空間での足し算 → cost・turnover・上限・ES の最適化（no-trade はここで決まる）→ 最も安い pair の表現 |
| **H. 事前に固定した文献の schedule（推定なし）** | 文献の時刻の効果を、文献の効果量に比例した固定の重みで、通貨の空間で保有。data で何も推定しない。**比較の基準（null に近い単純な案）** |

**taxonomy**（§25 の裁定の要求、混同しないための区別）:

| 構造 | 中身 | この文書での扱い |
| --- | --- | --- |
| **条件付きの strategy** | Trend × Mean Reversion を「trend の状態でだけ平均回帰」と組むこと。1 つの新しい予測 | 交互作用（§10） |
| **multi-strategy の portfolio** | Trend の portfolio + 平均回帰の portfolio を同時に持つこと | 足し算（§8） |
| **mixture of experts** | regime が trend なら Trend、range なら平均回帰を使うこと | §11 |

## 26. Architecture comparison

H = 高い（良い）、M = 中、L = 低い（悪い）。overfit・多重性・sample の必要量・実装の複雑さは「低いほど良い」を H と書く。

| 基準 | A | B | C | D | E | F | **G** | H |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 経済的な解釈性 | L | H | M | M | H | H | **H** | H |
| 交互作用の捕捉 | H | M | L | H | M | L | **M** | L |
| 分散化 | M | L | M | M | H | H | **H** | M |
| 統計的な効率 | L | M | M | L | M | M | **M** | H |
| sample の必要量 | L | M | M | L | M | M | **M** | H |
| overfit の危険 | L | M | M | L | M | M | **M** | H |
| 多重性 | L | M | M | L | M | M | **M** | H |
| cost の意識 | M | M | L | M | M | M | **H** | L |
| FX 固有の適合（通貨の重複） | L | L | L | L | M | H | **H** | M |
| regime への頑健性 | M | L | M | M | M | M | **M** | L |
| 実装の複雑さ（低いほど H） | M | H | H | L | M | M | **L** | H |
| 監査性 | L | H | M | L | M | M | **M** | H |
| production の保守性 | L | H | M | L | M | M | **M** | H |
| 追加の data の要求 | L | M | M | L | M | M | **M** | H |
| 既存の repo との互換 | M | H | M | L | M | H（通貨の book） | **H** | M |
| AI/ML を安全に使えるか | L | M | M | L | M | M | **H**（ML を cost・vol・相関に限定できる） | H（ML なし） |

**読み方**:

- **G は、最も高度ではなく、統計の安全と FX 固有の適合の釣り合いが最も良い**。
- **H は統計的に最も安全**（推定なし）で、G の比較の基準（G が H を上回らなければ、推定の層は不要）。
- A と D は、現在の data と効果量では、自由度に対して標本が足りない。

## 27. Recommended architecture

**推奨: Architecture G**（比較の基準として H を併走させる）。

**層ごとの合成**（設問 Q4 の答え）:

| 層 | 合成の演算 | 理由 |
| --- | --- | --- |
| mechanism の中 | **条件付きの期待 return**（掛け算・soft、縮小、状態変数 1 つ、事前登録） | edge の強さが状態で変わることを表す。硬い gate は標本を捨てる |
| mechanism の間 | **足し算**（期待 return の空間、通貨の単位、family の縮小、事前の risk の予算） | 別の edge は加法的に貢献する |
| 通貨の重複 | **射影と netting** | rank 7、pair の雑音の 65% を除く |
| 衝突 | 期待 return の加重和（重み = 予測の精度） | 不一致は不確実性として size を下げる |
| cost・risk・turnover・集中 | **最適化**（目的と制約） | 掛け算の scalar では扱えない |
| no-trade | **portfolio の段**（net の効用 ≤ 0）＋硬い制約（rollover・流動性・data の欠損） | 個別には弱くても合わせて正、個別に正でも全部同じ USD なら縮小、を扱える |
| AND | 硬い制約だけ | — |
| 選択（勝者総取り） | **使わない** | 情報を捨て、分散を増やす |
| 執行 | 最も安い pair の表現（線形計画） | alpha と分離 |

**system の目的（§29 の要求）【設計】**:

> maximize  E[net return] − λ₁·Var − λ₂·Cost − λ₃·Turnover
> subject to 通貨の上限、USD の因子の上限、family の risk の上限、ES の上限、margin、vol target

- **model の不確実性（λ₅）は、目的の項ではなく、μ の縮小（事後の平均）と Σ_μ（予測の分散）で入れる**。
- 評価の量は、**事後の system の net Sharpe**（cost の stress の下）と MaxDD。

## 28. Proposed research programme

将来、`FXID_REOPEN_REVIEW_PROPOSAL` が承認された場合の構造の案【設計】。

| Phase | 中身 | 実 data | gate |
| --- | --- | --- | --- |
| P0 | architecture の決定（この文書） | なし | Human + ChatGPT |
| **P1** | **component の供給の調査**: 機構を持ち、外部の prior（文献）がある mechanism family の一覧と、prior の効果量・重なり（§21 の 9 つの重なり）の評価。**system の上限の解析**（構造化した共分散で、事後の system の Sharpe の上限を計算） | なし | 上限 < 1.0 なら STOP（§30） |
| P2 | **合成の pipeline の帰無の検証**: 選択・重み・包含を含む pipeline 全体を、合成の帰無と植え込んだ効果で走らせ、portfolio 単位の FWER と検出力を確かめる | なし（合成だけ） | FWER ≤ 10%、検出力の目標 |
| P3 | cost の較正と replication（文献の期間の内側の data。発見の証拠には使わない） | 別承認（Red） | cost の model の妥当性 |
| P4 | component の推定（独立な estimation の block） | 別承認（Red） | component gate |
| P5 | system の合成と凍結 | — | system gate |
| P6 | fresh での system 全体の 1 回の確認 | 別承認（Red） | production gate |

**外部の文献の使い方の区別**（§32 の要求）:

| 用途 | 可否 |
| --- | --- |
| 発見の証拠 | 不可 |
| 外部の prior | 可（P1・P4 の縮小の prior） |
| replication | 可（P3） |
| cost の較正 | 可（P3） |
| 執行の検証 | 可 |
| 独立な確認 | 文献の sample の期間と重なる data では不可 |

## 29. Minimal next cycle

**提案（実行しない）**: **P1 + P2 だけ。どちらも実 data を読まない。**

- **P1（component の供給と system の上限）**:
  - 現在知られている機構を持つ候補を、mechanism family ごとに 1 行にまとめる（dollar の日中の W 字【EUR の朝・JPY の仲値の後を 1 family として】、自国時間の顧客の flow【W 字と重なる】、月末の株式ヘッジ、carry・momentum【日次で、FXID の当日決済の範囲外】）。
  - それぞれに文献の効果量（retail の cost の後の推定）と、§21 の重なりで構造化した相関を置き、事後の system の Sharpe の上限を解析的に計算する。
  - **判定**: 縮小の後の上限 < 1.0 なら、architecture の如何に関わらず STOP（現在の推定では、ほぼ確実にここで止まる。§1 の 2）。
- **P2（pipeline の帰無の検証）**:
  - P1 が上限 ≥ 1.0 を示した場合だけ行う。
  - G と H を合成 data の上で走らせ、選択を含めた portfolio 単位の偽発見率と検出力を確かめる。G が H を検出力で上回らなければ、推定の層を外して H を採る。
- この 2 つで、**architecture の良し悪し（統計の安全）と、そもそも architecture を使う意味（component の供給）**の両方を、data を読まずに判断できる。数百の strategy の backtest はしない。

## 30. Stop conditions

architecture の研究そのものの終了条件【設計】。

| # | 条件 | 閾値の案 |
| --- | --- | --- |
| S1 | 機構を持つ正の component の family が足りない | prior の net Sharpe ≥ 0.3 の、機構の重ならない family が 3 未満 |
| S2 | system の上限が production の目標に届かない | 構造化した共分散と縮小の後の事後の system の Sharpe の上限 < 1.0 |
| S3 | cost で全て消える | 全ての component が、all-in の現実の cost の後に prior の net ≤ 0 |
| S4 | 交互作用の探索の複雑さが大きすぎる | 必要な交互作用の次数 > 2、または cell の trade < 600 |
| S5 | 実効の探索の複雑さが予算を超える | 等価試行数が、選択の block で検出力 0.5 を保てる数を超える |
| S6 | 独立な確認ができない | fresh の検出力 < 0.7 になる真の system の Sharpe（< 1.0）しか見込めない |
| S7 | 必要な標本が非現実的 | 独立な選択と推定の block に、合わせて 15 年を超える data が要る |
| S8 | 実効の breadth が小さすぎる | 通貨の空間の実効の breadth（participation ratio）< 3、または全ての component が USD の因子だけに載る |

**component gate / system gate / production gate**（§30 の要求）【設計】:

| gate | 条件 |
| --- | --- |
| **component gate** | 懐疑的な prior（μ 0、τ 0.4 を検討案）の下での事後の P(net の期待 > 0) ≥ 0.9、cost の stress（×1.5）で正、機構の文書、2 つの部分期間で符号が一致、増分の情報（既存の component に対する残差の IC が正で有意）。**standalone の Sharpe 1.0 は要求しない**（HOLD の裁定 §8 の portfolio の注記と整合） |
| **system gate** | 事後の system の net Sharpe ≥ 1.0（**G4 は変えない**）、cost の stress、MaxDD ≤ 15%、集中の上限、部分期間の安定 |
| **production gate** | fresh での 1 回の確認、執行の検証、運用の頑健性 |

**component gate を緩めて、何でも通すことはしない**。弱い component を大量に入れると、§22 の偽発見になる。

## 31. Independent reviews

（下に記録する。）

## 32. Human + ChatGPT decision requests

1. **最終判定**: ARCH-D `ARCHITECTURE_SPECIFIED_BUT_COMPONENT_SUPPLY_IS_BINDING`（合成の構造は根本の制約を解かない。HOLD を維持する）を採るか。それとも ARCH-C（`COMPOSITION_DOES_NOT_SOLVE_THE_FUNDAMENTAL_LIMITATION`）とするか。
2. **設計の基準の記録**: Architecture G と、§22〜§24・§30 の統計の設計（portfolio 単位の max-T、nested walk-forward、component / system / production の 3 段の gate、fresh は system に 1 回）を、将来の `FXID_REOPEN_REVIEW_PROPOSAL` の設計の基準として記録するか（HOLD は解除しない）。
3. **最小の次の cycle**（§29 の P1、data を読まない）を、HOLD のままの机上の作業として将来承認しうる候補として記録するか。今回は実行しない。

### 必須の回答（裁定 §40）

| 問い | 回答 |
| --- | --- |
| Q1. strategy の単位で研究するのが正しいか | **正しくない**。原子は mechanism family が出す通貨の期待 return の vector（§4・§5）。strategy は、予測・timing・exit・sizing・執行を束ねた複合物で、自由度を隠し、同じ edge を重複して数える |
| Q2. pair ではなく通貨の exposure を基本の単位にすべきか | **すべき**（rank 7、pair の雑音の 65% を除く、重複の解消）。例外は、事前登録した pair 固有の残差の component（§13）。pair は執行の手段 |
| Q3. 足す・掛ける・選ぶ のどれか | 層による。**edge の中は条件付けの掛け算（soft・縮小）、edge の間は期待 return の足し算、最終は最適化**。選択（勝者総取り）は使わない。AND は硬い制約だけ |
| Q4. どの層を足し算・掛け算・最適化にするか | §27 の表 |
| Q5. 単独で edge の無い signal の交互作用を安全に検証する方法 | 経済的な理由を事前に書き、交互作用の項を直接検定し（factorial）、次数 ≤ 2、階層の縮小、cell の trade ≥ 600、全ての cell を max-T に数え、過去の gate の再探索を禁止（§10・§27） |
| Q6. 過去に特徴量・filter の組み合わせと strategy の組み合わせをどこまで試したか | 特徴量・filter・meta-label・Top-K は豊富（全て負か、検出力不足か、無効）。**strategy（mechanism）の組み合わせは #497 の 1 本だけ**。交互作用の事前登録は 0（§6） |
| Q7. multi-strategy / multi-mechanism の system は実質的に未検証か | **実質的に未検証**。ただし理由は、正の component の供給が無かったこと（§1・§29）。未検証であることは、有望であることを意味しない（#496 の上限 0.22、§1 の 2） |
| Q8. strategy の ensemble より、通貨単位の予測の集約の方が FX では合理的か | **合理的**（§13）。Track 1 の負は signal の負で、architecture の反証ではない |
| Q9. AI / ML をどの層に置くか | **cost・slippage・vol・相関の予測**（方向ではない量）。方向の予測・meta-label・合成の重みには置かない（§16） |
| Q10. component に standalone の Sharpe 1.0 を要求すべきか | **要求しない**。component gate（事後の P(net > 0) ≥ 0.9 など）と、system gate（事後の system の Sharpe ≥ 1.0、G4 不変）に分ける（§30） |
| Q11. component の価値を限界的な portfolio の価値で評価すべきか | **すべき**。ただし共分散は、標本の相関ではなく構造の重なり（§21 の 9 項目）で作り、包含の決定を多重性に数える |
| Q12. 弱い component を多数集める時の偽発見をどう防ぐか | data で component を探さない（機構と外部の prior で事前に決める）、選択の手続き全体の帰無で portfolio 単位の max-T、nested walk-forward、階層の縮小、事後の system の Sharpe で判定（§22）。in-sample の portfolio の Sharpe は、真の 0 の 100 本から 2.03 を作れる |
| Q13. fresh は component ではなく最終の system 全体に使うべきか | **すべき**。全てを凍結してから 1 回（§24）。真の 1.0 でも検出力は 0.72 |
| Q14. 推奨する architecture | **G**（mechanism-first・通貨単位・階層の予測の集約 + cost を意識した最適化）。比較の基準として **H**（事前に固定した文献の schedule） |
| Q15. それを最小の cost で否定・支持する次の cycle | **P1（component の供給と system の上限の解析）+ P2（pipeline の合成の帰無の検証）**。どちらも実 data を読まない（§29）。P1 で上限 < 1.0 なら STOP |

---

**STOP（裁定 §42）。** HOLD は解除しない。Human + ChatGPT の承認なしに merge しない。
