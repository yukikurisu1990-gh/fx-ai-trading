# FX research programme — Programme Redesign と Evidence Synthesis 最終報告（2026-09-28）

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

この cycle は**新しい alpha を 1 つも計算していない**。以下のどれもしていない:

- backtest・再実行・符号反転・horizon の救済・通貨 subset の救済
- 多 source の最適化・非線形 ML
- fresh・OOS・dead・forward の読み取り
- broker 認証・有料 data の利用

ここにあるのは次の 3 つだけ:

- 過去の記録から読み取った数字: `artifacts/research/programme/ledger.json`
- #495 の financing cell（記録済み）
- signal を使わない算術: `scripts/research/programme/feasibility_math.py`

数字の出所はすべて `artifacts/research/programme/synthesis.json`。

**用語**: 「TC-net」は transaction cost を引いた後で financing を引く前の値（`NET_EX_TRANSACTION_COSTS_EXCLUDING_FINANCING`）。Sharpe を pool するときは全てこの 1 つの定義を使う。

---

## 1. Executive Summary

1. **この programme には、null と区別できる経済的な正の証拠が無い。**
   - tier A の経済的検定で、null percentile が 0.9 以上のものは 0 本。
   - p ≤ 0.05 は 1 本で、帰無の下での期待は 0.4 本。その 1 本も、記録された family-max では p = 0.12 になる。
   - family-wise で通った cell は、programme 全体で 1 つだけある（CPI 4h、2023–25 panel で family-max p = 0.040）。その cell は、もう一方の決定 panel では family-max p = 0.99 で、事前登録の判定（両 panel が必要）は NOT_SUPPORTED。
   - mechanism 単位で数えた gross の符号は、tier A+B+C で 8 本が正、8 本が負。
2. **縮小推定は「平均はほぼ 0、ばらつきは測れていない」と言っている。**
   - tier A の TC-net の真の平均は μ̂ = +0.07（SE ≥ 0.13）。
   - mechanism 間のばらつきの点推定は τ̂ = 0。ただし 95% 上限は **0.55** ある。
   - tier A は 6 本しかないので、「どの mechanism も弱い」とは言い切れない。**言えるのは「区別できるほどの証拠が無い」まで**である。
3. **seen data の検出力が天井になっている。**
   - 真の Sharpe 0.3 を 80% の検出力で見つけるには **87 年**要る。
   - 手元の最長は 17.7 年（seen 全体でも 22.4 年）で、検出力は 0.24（0.30）。
   - 保護中の fresh pool は 4.9 年で、単独なら検出力 **0.10**。
4. **年 5% に要る TC-net Sharpe は、vol 10% で 0.50〜0.77**（financing の cell による）。
   - 全 cost 後の Sharpe 0.5 で運用しても、10 年の最大 DD の中央値は −23%、DD が 20% を超える確率は 66%。
   - 確率的 vol・gap を入れると、下位 10% は −41〜−44%。
   - 真の Sharpe を programme の推定から引くと（financing drag を引いた全 cost 後の値）、10 年後に損失で終わる確率が **50%**。
   - 年 10% には TC-net 1.0〜1.27 が要る。
   - **現在の証拠では、年 5% は research-feasible と言えない。年 10% は届かない。**
5. **forward の情報量は、候補の事前の不確実性で決まり、確認の手段としては弱い。**
   - 36 か月の forward の Sharpe の SE は 0.58。
   - tier A の事前分布（SD 0.57）なら、事後 SD は 29% 縮む。
   - forward 単独で z > 1.96 になる確率は 9%。
6. **閉じたのは「試した情報集合 × 定式化 × seen の文脈」だけ。**
   - 政策金利 carry、CPI surprise、COT は 2 年 × 2 panel で決まらなかった。これは閉じたのではなく**検出力不足**である。
   - 公開の長い span での古典的 premia（断面 carry、1〜12 か月の momentum）は**未検定**のまま残っている。
7. **推奨: 次の cycle を「単一 signal を探す cycle」にしない。**
   - Human + ChatGPT に 3 つの判断を上げる（§28）。
   - `FX_RESEARCH_PAUSED` は自動では立てない。

## 2. Identity

| | |
| --- | --- |
| #495 | MERGED。final head `9dda962`（9dda9626859e…）、merge commit **`b98a228`**（b98a228009d6…）、2026-09-27T22:42:46Z |
| master CI（`b98a228`） | **success** |
| この branch | `research/m15-programme-redesign`（master `b98a228` から） |
| 分類 | **Amber**。research の evidence 解釈の layer で、protected path の `scripts/**` に M15 research の解釈を置く。merge は Human + ChatGPT の承認待ち（§37） |
| 実行したもの | ledger の組み立て、synthesis、signal-blind の算術（合成乱数による DD simulation を含む） |
| 実行していないもの | alpha・backtest・再実行・data 取得・network 接続・保護 data の読み取り |

保持する status（裁定どおりで、変更していない）:

| track | status |
| --- | --- |
| M15 | `M15_CORRECTED_FINANCING_NOT_DECISION_GRADE`（`POST_RESULT_IMPLEMENTATION_CORRECTED_EXPLORATORY_ONLY`） |
| M16 | `M16_CORRECTED_POSITIVE_EXPLORATORY_NOT_DECISION_GRADE`（同上） |
| M11 | `POSITIVE_EXPLORATORY_NOT_DECISION_GRADE` |
| M01 | `POSITIVE_EXPLORATORY_NOT_DECISION_GRADE` |
| M10 | `NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` |

M15 / M16 の post-result 修正は、共通の実装・会計の修正として受け入れた。ただし clean・decision-grade・confirmation の証拠には昇格させていない。ledger ではどちらも tier **C** である。

## 3. Complete Evidence Ledger

`artifacts/research/programme/ledger.json`: **278 行**、34 cycle、5 part。

| part | 範囲 | 行数 |
| --- | --- | ---: |
| A | M15 archive の探索 round（#464–#470）: Round 1 / 2、supplemental、momentum、Round A、B′、monetizability | 11 |
| B | economic edge / exogenous / expectation benchmark / Track 2（#471–#477） | 124 |
| C | Track 1 portfolio / model learning / T-R / T-R2 / T-V（#478–#488） | 46 |
| D | Top-Five / next-five / mechanism redesign / USD-factor financing（#490–#495） | 50 |
| E | pre-R1 era（Phase 9–29、ML Step 4。別の harness） | 47 |

**field**

- 裁定 §5 の全 field を持つ: track、family、仮説、mechanism、情報源、price-only か、book 型、span、年数、有効 N、event 数、gross / net の年率と Sharpe、financing、turnover、年間 cost、IC、増分 IC、null percentile、p、安定性、LOO、集中度、DD、status、qualifier、保護 data の caveat、closure の範囲。
- `source` が、出所の artifact の key path か文書の節を指す。**記録が無い値は null で、推測していない。**
- 解釈用の派生列を足した:
  - `sharpe_ex_financing`: pool 用の単一定義。
  - `judged_net_sharpe_incl_approx_financing`: carry と markup を込めた値。
  - `null_stats_basis`: null 統計がどの P&L で測られたか。mechanism redesign は judged P&L。
  - `rate_exposure`: D-M3 の範囲。
  - `effective_n_kind`: Top-Five の値は distinct signal states で、有効 N ではない。
  - `annual_cost_unit`: model learning の行は bp/年。

**抽出と再現性**

- part B〜E は抽出役 4 つが書き起こした。抽出 script（`scripts/research/programme/extract/`）は repo の source だけを読み、再実行すると part が byte 単位で一致して再生成されることを確認した。
- part A の抽出役は、repo への書き込みと script の実行を permission classifier に拒否された。lead はその script を代わりに実行していない。
- part A は lead が結果文書と artifact から独立に書き起こした（`build_ledger_A.py`、11 行）。
  - この時代の結果は pips/pair と bar 単位の `sharpe_like` で記録されているので、年率の field は null にし、`sharpe_like` は notes にだけ残した（比較できないため）。

**過去の記録は書き換えていない。** ledger は interpretation layer である。ラベルを揃えたのは 1 件だけ（#495 の total 行の financing 表記）で、数値は変えていない。

## 4. Evidence Tiers（§11）

| tier | 定義 | 行数 |
| --- | --- | ---: |
| **A** | 事前登録・1 回・1 つの仮説の primary・事後修正なし・無効でない・多数の cell からの選択でない | 19 |
| **B** | 事前凍結された grid の cell（horizon / model / 符号 / universe の変種）、多数から選ばれた cell（Round 2 の best of 39）、事前登録の無い探索 | 42 |
| **C** | 結果を見た後の実装修正を経たもの（Top-Five 全体、next-five run4、COT、Track 2 の第 2 稿、T-R の universe-closed 再実行、#495） | 63 |
| **D** | secondary span・感度・benchmark・事後診断。pre-R1 era は全て D（別 harness で Sharpe の定義が揃わず、Phase 27–29 は provenance 監査 #356 が未解消） | 119 |
| **E** | 無効・置き換え済み（next-five run2、mechanism redesign の M15/M16、Phase 9 の leakage 期、T-V の leak 版、COT 初版の統計など） | 35 |

**以下の分析は tier 別に出し、主たる推定は A（と A+B）にした。C を含む推定は感度としてだけ示す。**

## 5. Net / Financing Definitions

| ledger の `financing_included` | net の意味 |
| --- | --- |
| `NONE` | **`NET_EX_TRANSACTION_COSTS_EXCLUDING_FINANCING`**（過去の「net」の大半） |
| `RESEARCH_CARRY_POLICY_RATES` | 政策金利差の research carry。broker markup なし（#471 carry） |
| `APPROXIMATE_CARRY_AND_MARKUP` | `NET_INCLUDING_APPROXIMATE_INTEREST_DIFFERENTIAL_AND_ASSUMED_MARKUP`（`APPROXIMATE_RESEARCH_FINANCING`、#495 の total） |
| 全行 | **`FULL_RETAIL_NET_UNKNOWN`** |

**近似 financing は実際の broker financing ではない。** OANDA の financing 履歴は認証が要り、今回は取得を禁止されている。

**financing を除いた正の値は上方に偏っている。** 同じ run の judged net（近似 carry + 仮定 markup 込み）と並べると、はっきりする:

| track | TC-net（financing 抜き） | judged net（近似 financing 込み） |
| --- | ---: | ---: |
| M01 | 0.30 | **0.08** |
| M11 | 0.19 | 0.16 |
| M16 | 0.35 | 0.28 |
| M15 | 0.007 | 0.10 |

- M01 の judged net が 0.08 に落ちるのは、carry が負（−1.5%/年）だからである。
- M15 は逆向きで、正の carry が加わって値が上がる。
- mechanism redesign の null percentile・p・LOO・集中度・DD は、**judged P&L の上で**測られている。

## 6. Effective Hypothesis Count（§8）

post-R1（part A〜D、無効を除く）:

| 数え方 | 数 |
| --- | ---: |
| 別の mechanism | **32** |
| primary の cell（horizon / model / 符号 / universe の変種を含む） | **108**（事前登録 105、事前登録なし 3） |
| 測定した行（感度・secondary・benchmark を含む） | **212** |
| 結果を見た後に修正された行 | 63 |
| 無効行 | 19 |
| pre-R1 era の行 | 47（こちらにも数百 config の探索がある。development 2025 だけで約 1,200 config） |

- 「本当に試した仮説」の数は、数え方によって **32〜212** の幅がある。
- 独立な検定の数はそれより少ない。同じ span・同じ panel・近い mechanism を共有しているからである。例えば Top-Five の long は全て、1999–2016 の ECB 参照レートを使っている。
- この数には、次の探索は入っていない。どれも、そこから選んだ候補を後で replication にかけた:
  - Round 1 の 51 config と walk-forward の 52 config
  - Round A の 39 cell
  - B′ の 7 horizon

## 7. Multiple-Testing Assessment（§9）

- **経済的な検定で単独の p ≤ 0.05 が出たのは 2 回で、どちらも US CPI surprise の多数の cell の中の 1 つである。**

  | cell | 2023–25 panel: cell p / family-max p | 2021–23 panel: cell p / family-max p | development 2025: family-max p |
  | --- | --- | --- | --- |
  | CPI 1h | 0.0498 / **0.124** | 0.44 / 0.906 | — |
  | CPI 4h | 0.0249 / **0.040** | 0.62 / 0.99 | 0.75 |

  - **CPI 4h は、1 つの panel で family-wise に通った programme 唯一の cell である。**
  - 事前登録の判定は、2 つの決定 panel の両方を要求していた。もう一方の panel では family-max p = 0.99 なので、判定は `MACRO_SURPRISE_DIRECTIONAL_EDGE_NOT_SUPPORTED`。
  - programme には数十の family 検定があり、1 つの panel での family-wise 通過が 1 回あることは、帰無の期待の範囲に収まる。
- Round 2 の reversal は family-wise で p = 0.053 だった。best の 3 日を除くと 0.157 になる。supplemental では `FAILED` した（family-max で p = 0.9757）。
- 統計的に強い棄却は、Round B′ の variance ratio（p = 0.005）の 1 本だけである。これは**価格経路の構造であって収益ではない**。収益化しても round trip cost の 6–16% にしか届かなかった。
- **programme 全体の多重性を考えると、どの単独の「有意」も偽陽性の期待値の範囲に収まる。**

## 8. Programme-Level Null Comparison（§10）

既存の null artifact（permutation、circular shift、bootstrap、family-max）の記録値だけを使った。経済的な検定だけを数え、B′ の構造検定は除いた。

| tier | p のある検定 | p ≤ 0.05 | 帰無での期待 | P(≥ 実数) | percentile のある検定 | ≥ 0.9 | 平均 percentile（z vs 一様） |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| A | 8 | 1 | 0.40 | 0.34 | 3 | 0 | 0.59（z 0.54） |
| A+B | 14 | 2 | 0.70 | 0.15 | 3 | 0 | 0.59（z 0.54） |
| A+B+C | 54 | 2 | 2.70 | 0.76 | 12 | 0 | 0.515（z 0.18） |
| C のみ | 40 | 0 | 2.00 | 1.00 | 9 | 0 | 0.49（z −0.11） |

**符号**（mechanism 単位。鏡像を除き、同じ span は二重に数えず、定義は 1 つ）:

| tier | gross 正 / 負 | TC-net 正 / 負 |
| --- | --- | --- |
| A | 4 / 2（P = 0.34） | 3 / 3 |
| A+B+C | 8 / 8（P = 0.60） | 6 / 12 |

**読み方:**

- **p ≤ 0.05 の数は、帰無で期待される数と区別できない。**
- null percentile が 0.9 以上の検定は、どの tier でも 0 本。最大は 0.839（M16 の ex-financing、tier C）。
- **gross の符号にも偏りは無い。** 当初の集計では 39 本中 26 本が正（p = 0.027）だった。これは鏡像、同じ span の二重計上、定義の混在から生じた見かけで、review で撤回した（§29）。
- tail 確率は、検定が独立だと仮定して計算している。p の定義も cycle ごとに違う。目安として読むこと。

## 9. Positive Observation Audit（§23）

**勝者の一覧ではない。**

- 各行に qualifier と、forward 最低条件（§21）で落ちる項目を並べた。
- 「不明」は記録が無いという意味で、合格ではない。
- MDE は、その span での検出下限である。

| track | tier | 年数 | gross / TC-net / judged | null | MDE | 落ちる条件 |
| --- | --- | ---: | --- | --- | ---: | --- |
| T5（TIC flow）recent | C | 2.2 | 0.89 / 0.84 / — | p 0.314（t は過大） | 1.89 | F1、F2（long は −0.02）。有効 N は signal states で不明 |
| U2（中銀 B/S）recent | C | 3.0 | 0.48 / 0.42 / — | 記録なし | 1.62 | F1、F2（long −0.07）、F5（集中度 1.49） |
| U4 recent | C | 3.9 | 0.09 / 0.01 / — | 記録なし | 1.42 | F1、F2（long −0.38）、F3、F5（LOO −0.24、集中度 51.8） |
| T-R2 D | B | 4.8 | 0.83 / **0.05** / — | 記録なし | 1.28 | F1、F3、F5（LOO −1.03）、F6。cost 8.2%/年、turnover 60 |
| T-V C | A | 12.6 | 0.14 / 0.13 / — | 記録なし（増分 IC は NW t −3.34） | 0.79 | F3、F5（LOO −0.27、集中度 2.07）。名目平均回帰より有意に悪い |
| M11 | A | 17.7 | 0.22 / 0.19 / 0.16 | pct 0.781、p 0.22（judged） | 0.67 | F2、F3、F5、F6（carry が JPY を含む）。recent は −0.50 |
| M01 | A | 17.7 | 0.32 / 0.30 / **0.08** | pct 0.803、p 0.20（judged） | 0.67 | F2、F4（有効 N 6.2）、F5、F6 |
| M16 total | C | 17.7 | 0.36 / 0.35 / 0.28 | pct 0.809、p 0.19 | 0.67 | F1、F2、F6。recent は −0.50。long の値は実行前から分かっていた |

- **観測された値が、その span の検出下限を超えたものは 1 本も無い。**
- 縮小推定（§10）では、tier A の事後平均はどれも 0.07 である（τ̂ = 0 のため）。

## 10. Signal Quality Distribution（§12）

**方法（empirical Bayes）**

- モデル: 観測 Ŝᵢ ~ N(θᵢ, 1/年数ᵢ)、真の効果 θᵢ ~ N(μ, τ²)。
- 周辺尤度を grid で最大化した（μ ∈ [−2, 2]、τ ∈ [0, 2]、境界に当たったら flag）。τ の 95% 上限は profile likelihood で出した。
- 同じ mechanism の別の span は、年数で重み付けて 1 つにまとめた。
- 同じ span の変種（例: T-R2 D は T-R C の horizon 変種）と、符号の鏡像は数えていない。
- Sharpe は全て TC-net（financing 抜き）を使った。

割合は予測分布 N(μ̂, τ² + SE(μ̂)²) で出した。これは「新しく試す mechanism の真の値がこれを超える確率」にあたる。τ̂ = 0 でも、0% や 100% のような縮退した値にはならない。

| 対象 | 本数 | 素朴平均 | μ̂ | SE(μ̂) 下限 | τ̂ | τ の 95% 上限 | 真の値 > 0（τ̂ / τ 上限） | > 0.3（同） | > 0.5（同） |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| **tier A（主）、TC-net** | 6 | −0.175 | **+0.07** | 0.13 | **0** | **0.55** | 70% / 55% | 4% / 34% | 0% / 22% |
| tier A、gross | 6 | +0.126 | +0.215 | 0.13 | 0 | 0.42 | 95% / 69% | 26% / 42% | 1% / 26% |
| A+B+C（感度）、TC-net | 18 | −0.38 | −0.325 | 0.14 | 0.49 | 0.78 | 26% / 34% | 11% / 21% | 5% / 15% |
| A+B+C（感度）、gross（financing を含まない行だけ） | 16 | — | +0.035 | — | 0 | 0.25 | 69% / 56% | 0% / 15% | 0% / 3% |

tier A+B は tier A と同じ値になるので、表から除いた。B の比較可能な唯一の行（T-R2 D）が、同じ span の変種として T-R C にまとめられるためである。独立な頑健性の確認にはならない。

**読み方:**

- **tier A の証拠が言えるのは「平均は 0 に近く、mechanism 間の違いは検出できない」まで。**
  - 6 本しかないので、τ の上限 0.55 は広い。
  - 「真の Sharpe が 0.5 を超える mechanism が 2 割ある」可能性も、データからは排除できない。
  - **証拠が弱いのであって、弱い効果が証明されたのではない。**
- tier A の gross の平均は 0.215、TC-net は 0.07。**平均的に Sharpe 約 0.15 分を cost が食っている。**
- C を含む推定では τ̂ = 0.49 になる。これは主に **cost の違い**から来ている。Top-Five の T4（−1.68）と T3（−1.64）が大きく引っ張っている。gross で推定すると τ̂ = 0 になるので、signal の質のばらつきではない。
- 注意:
  - Sharpe の SE を √(1/年数) と置いているので、遅い signal（有効標本 5〜25）では不確実性を過小評価する。
  - mechanism 同士が span を共有しているので、SE(μ̂) は下限である。

## 11. Power Landscape（§13）

両側 5%、検出力 80%。Sharpe の SE ≈ √(1/T) とした。

| 真の Sharpe | 0.1 | 0.2 | 0.3 | 0.5 | 0.7 | 1.0 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 必要年数 | 785 | 196 | **87** | 31 | 16 | 7.8 |

| 研究の型 | 使える年数 | MDE | 検出力 S=0.2 / 0.3 / 0.5 |
| --- | ---: | ---: | --- |
| 日次連続 book（recent） | 4.7 | 1.29 | 0.06 / 0.10 / 0.19 |
| 日次連続 book（long、ECB） | 17.7 | 0.67 | 0.13 / 0.24 / 0.56 |
| 月次 macro（long） | 17.7 | 0.67 | 同上が**上限**（有効標本 5–25） |
| USD factor（breadth 1、符号 regime 6–28） | 17.7 | 0.67 | 同上が上限 |
| 断面 factor（8 通貨） | 17.7 | 0.67 | 0.13 / 0.24 / 0.56 |
| seen の全長 | 22.4 | 0.59 | 0.16 / 0.30 / 0.66 |
| **fresh pool**（長さだけで、中身は読んでいない） | 4.9 | **1.27** | 0.07 / 0.10 / 0.20 |
| event 駆動 | event 数が律速（例: 4 中銀 × 8 回 × 20 年 ≈ 640 件） | — | — |

**family と track の違い**: family 内の K 本を事前固定の等ウェイトで 1 つの統計量にまとめると、真の効果が family 共通なら、必要年数は (1+(K−1)ρ)/K 倍に縮む。共通でなければ、平均で薄まる。

## 12. Single-Signal Assessment（§14）

**単一 signal を 1 本ずつ検定する方法は、この programme の主な方法として続ける理由が無い。**

- 1 本あたりの検出力は 0.1〜0.3。
- 検定するたびに seen の span が減り、多重性が増える。
- 手元の年数では、事前登録を守っても、Sharpe 0.3 級の真の効果を 4 回に 3 回見逃す。
- 32 の mechanism で null を超えたものは 0 本だった。これは「効果が無い」とも「検出力が無い」とも矛盾しない。**2 つを区別できないこと自体が、この方法の限界である。**

## 13. Family-Level Assessment（§16）

best-of-N を使わない設計は 3 つある。

- (a) **事前固定の family 平均**: family の全 cell を等リスクで平均し、1 つの net Sharpe を 1 回だけ検定する。
- (b) **omnibus**: 全 cell の統計量の二乗和などを、circular shift の null と比べる。
- (c) **階層モデル**: §10 と同じ形で、family の μ を推定する。

どれも問うのは「family に共通の効果があるか」で、「どの cell が勝つか」ではない。

制約が 3 つある:

- seen data で検定し直すと、各 cell の結果を既に知っているので **tier D** にしかならない。
- 新しい family を検定するには、新しい情報源か保護 data（fresh・forward）が要る。
- fresh pool は 4.9 年しかない。K = 5、ρ = 0.3、真の s = 0.2 の family でも、合成 Sharpe は 0.30 で、検出力は 0.10 にとどまる。

## 14. Fixed Multi-Source Assessment（§17・§18）

**事前固定の方式**（当てはめたウェイトは使わない）: 等ウェイト、等リスク、事前に定めた family ウェイト、直交 bucket（USD factor / 断面 / 金利 / flow / 価格）。

**低い相関は、それだけでは集約の理由にならない（§18）。** 情報を持たない signal 同士も低相関だからである。

- 合成で Sharpe が上がるのは、各 source の **cost 後の**真の効果が正のときだけ。
- cost 後の s が 0 の source は、何本足しても 0 のままである。
- 倍率 √(N/(1+(N−1)ρ)) は gross にも net にも同じようにかかる。したがって cost を 1 本ごとに引いた後の s が問題になる。

**これまでの証拠に当てはめると:**

- null を超えた source は **0 本**。
- tier A の TC-net の平均は +0.07。
- この s を置くと、N を無限に増やしても上限は s/√ρ で、ρ = 0.1 なら **0.22** にとどまる。

## 15. Aggregation Feasibility Scenarios（§19）

S_p = s·√(N/(1+(N−1)ρ))。s は cost 後の真の Sharpe。**s・N・ρ は観測から選ばず、固定の格子に置いた。**

| s ＼ (ρ, N) | ρ=0 N=10 | ρ=0.1 N=10 | ρ=0.1 N=20 | ρ=0.3 N=10 | 上限 s/√ρ（ρ=0.1 / 0.3） |
| --- | ---: | ---: | ---: | ---: | --- |
| 0.05 | 0.16 | 0.12 | 0.13 | 0.08 | 0.16 / 0.09 |
| 0.10 | 0.32 | 0.23 | 0.26 | 0.16 | 0.32 / 0.18 |
| 0.20 | 0.63 | 0.46 | 0.53 | 0.33 | 0.63 / 0.37 |
| 0.30 | 0.95 | 0.69 | 0.79 | 0.49 | 0.95 / 0.55 |

**目標に届く最小の N**（「届かない」は 1,000 本でも届かないという意味）:

| 目標 Sharpe | s=0.1, ρ=0.1 | s=0.2, ρ=0 | s=0.2, ρ=0.1 | s=0.2, ρ=0.3 | s=0.3, ρ=0.1 | s=0.3, ρ=0.3 |
| --- | --- | ---: | ---: | --- | ---: | --- |
| 0.5 | 届かない | 7 | **15** | 届かない | 4 | 12 |
| 0.6 | 届かない | 9 | 81 | 届かない | 6 | 届かない |
| 0.75 | 届かない | 15 | 届かない | 届かない | 15 | 届かない |

**年 5% に要る 0.5〜0.77 に届くには、cost 後の真の s ≥ 0.2 の独立な source が、ρ ≤ 0.1 で 15 本以上要る。**

## 16. TC / Financing Impact（§21・§22）

**drag は Sharpe の単位で扱う。** transaction cost も markup も gross notional に比例し、notional は vol target に比例する。そのため drag ÷ vol は、vol を変えても変わらない。

**transaction cost**: 記録された gross − TC-net（primary の比較可能な 22 行）は次のとおり。

- 最小 0.013、p25 0.06、中央値 0.40、p75 0.85。
- 遅い月次 book（M01・M11・T-V）は 0.01〜0.04。
- 日次・週次の book（Top-Five T1・T2・T4、T-R、T-R2）は 0.4〜2.5。
- **Top-Five の 4 本を殺したのは cost** で、turnover は 8 倍だった。

**financing**（`APPROXIMATE_RESEARCH_FINANCING_RANGE`、**実際の broker financing ではない**）: #495 の M16 cell の値で、USD-factor book の参照値である。

| cell | markup（/pair notional/年） | Sharpe の低下 |
| --- | ---: | ---: |
| optimistic | 0 | 0 |
| central | 0.5% | 0.068 |
| （中間） | 1% | 0.137 |
| conservative | 2% | **0.274** |

- M15 は markup の cell によって total の符号が変わる。M16 は 8 cell すべてで正のまま。
- 断面 book のように gross notional ÷ vol が違う book では、この値も変わる。
- **full retail net は全行で不明**（`FULL_RETAIL_NET_UNKNOWN`）。

## 17. Annual 5% and 10% Feasibility（§20）

**各列の意味**

- 全 cost 後の Sharpe = 目標 / vol。DD はこの値で決まる。
- TC-net の要求値 = その値 + financing の drag。
- gross の要求値は、さらに transaction cost の drag を足したもの（central financing、中央値の book）。

**要求 Sharpe**

| 目標 @ vol | 全 cost 後 | TC-net 要求（fin 0 / 0.5% / 2%） | gross 要求（中央値の book） |
| --- | ---: | --- | ---: |
| 5% @ 8% | 0.63 | 0.63 / 0.69 / 0.90 | 1.10 |
| 5% @ 10% | **0.50** | **0.50 / 0.57 / 0.77** | 0.97 |
| 5% @ 12% | 0.42 | 0.42 / 0.49 / 0.69 | 0.89 |
| 5% @ 15% | 0.33 | 0.33 / 0.40 / 0.61 | 0.80 |
| 5% @ 20%（stress のみ） | 0.25 | 0.25 / 0.32 / 0.52 | 0.72 |
| 10% @ 8% | 1.25 | 1.25 / 1.32 / 1.52 | 1.72 |
| 10% @ 10% | **1.00** | **1.00 / 1.07 / 1.27** | 1.47 |
| 10% @ 12% | 0.83 | 0.83 / 0.90 / 1.11 | 1.30 |
| 10% @ 15% | 0.67 | 0.67 / 0.74 / 0.94 | 1.14 |

**DD**（10 年、4,000 path、加算 equity。margin の強制決済は入れていない）

| 目標 @ vol | iid 正規: 中央値 / 下位 10% / P(>20%) | 確率的 vol: 下位 10% | gap: 下位 10% | 真の Sharpe を programme の推定から: 中央値 / P(10 年後に損失) |
| --- | --- | ---: | ---: | --- |
| 5% @ 8% | −16.7% / −26.4% / 30% | −33.5% | −29.8% | −28.9% / 50% |
| 5% @ 10% | −22.9% / −36.4% / 66% | −44.3% | −41.4% | −36.1% / 50% |
| 5% @ 12% | −29.2% / −47.5% / 87% | −55.5% | −54.2% | −43.3% / 50% |
| 5% @ 15% | −39.2% / −64.4% / 98% | −72.9% | −74.0% | −54.1% / 50% |
| 10% @ 10% | −16.9% / −25.4% / 28% | −36.9% | −27.9% | −36.1% / 50% |
| 10% @ 15% | −30.5% / −47.7% / 92% | −61.7% | −53.9% | −54.1% / 50% |

最後の列の前提: 真の Sharpe は tier A の新候補の分布（TC-net の平均 0.07 から central の financing drag 0.068 を引いた全 cost 後の平均 0.002、SD 0.57）から引いた。

**読み方:**

- **vol を上げて要求 Sharpe を下げる道は、DD で閉じている。** vol 15% なら年 5% の TC-net 要求は 0.33〜0.61 まで下がるが、DD の中央値は −39% になる。
- DD は条件付きの値である。iid 正規の列は「真の Sharpe が要求値ちょうどで、iid 正規」という条件での値で、**最も楽観的**である。
  - vol の塊（確率的 vol）と gap は、下位 10% を 7〜10 ポイント悪くする。
  - 真の Sharpe が programme の推定（全 cost 後の平均 0.002、SD 0.57）から来るなら、10 年後に損失で終わる確率は 50% になる。
- 「Sharpe 0.1 × 20 倍 leverage」は使わない（裁定で禁止）。
  - vol 20% は stress としてだけ示した。
  - gap の simulation には margin の強制決済が入っていない。leverage が高い book では、CHF 2015 のような gap は DD ではなく**強制決済**になる。

**結論:**

- 年 5% を DD 20% 程度に抑えて狙うには、**TC-net で Sharpe 0.63〜0.90（vol 8%）の book が要る。** 現在の証拠に、そこへ近い source は無い（tier A の平均 0.07、最大の観測値 0.30）。
- 年 10% は TC-net 1.0 以上が要り、この programme の証拠からは遠い。

## 18. What Is Actually Closed（§24）

**閉じたのは「この情報集合 × この定式化 × この seen の文脈」だけで、「FX に edge は無い」とは言わない。** span が短い検定は「閉じた」のではなく、「検出力不足で決まらなかった」に近い。各項目に MDE を付けた。

| 閉じたもの | 範囲 | span と MDE |
| --- | --- | --- |
| M15 の multi-day reversal / momentum（lb480_h480、PAIRS_20） | 両方向とも 3 span で null と区別できない。active 探索から外した | 各 span 約 2 年、MDE ≈ 2.0 |
| M15 の textbook rules・15 本の戦略・reversal の sweep | development 2025 で cost 後すべて負。walk-forward でも選べない | 0.7 年。cost が gross を大きく上回った（検出力の話ではない） |
| M15 の価格経路構造（VR < 1）の収益化 | 構造は実在する（p = 0.005）が、収益化しても cost の 6–16% | cost との比で閉じた |
| US CPI surprise・COT・survey consensus | 事前登録の判定（2 つの決定 panel の両方）で NOT_SUPPORTED。ただし CPI 4h は 2023–25 panel で family-max p 0.040 と、family-wise で通った（2021–23 panel では 0.99） | 各 panel 2 年。event 単位の MDE が観測値を上回る（CPI 4h: MDE 19.1、観測 net 15.3 pips/pair-event）。**検出力不足に近い** |
| Track 1 portfolio・model learning M01/M03/M13 | 事前登録の pass rule を満たさない（Track 1 の net −0.84） | out-of-fold 2.9 年、MDE ≈ 1.6 |
| 市場利回り repricing（5 日）・実質為替 valuation | 5 日は cost で負。valuation は名目平均回帰より**有意に悪い**（NW t −3.34） | 4.8 年（MDE 1.28）/ 12.6 年（MDE 0.79） |
| Top-Five T1–T4、next-five U1・U3・U4・U5、M10 | NOT_SUPPORTED_IN_SEEN_DEVELOPMENT。T4・T1・T2 は cost で負 | long 17 年（MDE 0.67）、recent 2〜4.8 年 |
| M15 USD factor | FINANCING_NOT_DECISION_GRADE | 17.7 年、MDE 0.67、有効標本 5 |

## 19. What Remains Open（§25）

| 種類 | 中身 |
| --- | --- |
| **未検定** | **公開の長い span（1999–2016）での古典的 premia**。対象は断面 carry（G10、long-short）と 1〜12 か月の通貨 momentum。long span で検定したのは、USD factor の carry（M15）、4〜6 日の momentum 類似、valuation だけ。ほかに options / risk-reversal（有料）、高頻度の order flow（有料）、cross-asset の大半、family 単位の事前固定の合成 |
| **検出力不足** | 政策金利 carry（2 panel × 2 年、MDE ≈ 2.0。**閉じたのではなく決まらなかった**）、CPI・COT・consensus、Sharpe 0.3 前後の効果全般、月次 macro（M11・M01・M16）、USD factor、20 日の市場利回り repricing（gross 0.83 だが cost で net 0.05） |
| 負だが反証ではない | multi-day reversal / momentum（区間が 0 を跨ぐ）、U2（long −0.07） |
| data で封鎖 | T3・U3・U5・M10 の long、非 USD surprise（vintage が無い） |
| 有料のみ | consensus の vintage、options、tick / order book の長い履歴 |
| financing 不明 | 全行の full retail net。financing を除いた positive は上方に偏っている（M01 は 0.30 → 0.08） |
| 確認で封鎖 | forward（採用待ち）、fresh pool（保護中） |
| 汚染 | JPY 金利に関係する forward 確認（D-M3） |

## 20. Protected Information Ledger（§28）

| 対象 | 状態 | 範囲 |
| --- | --- | --- |
| FX fresh pool 2016-06-02 … 2021-04-25 | **未読** | 全 FX track の将来の確認用 |
| historical OOS slice | `HISTORICAL_EXPLORATORY_OOS_PRISTINE_CLAIM_WITHDRAWN`（R1 が 20 行を decode） | formal evidence に使えない |
| dead window | 未読 | — |
| forward epoch（FX 価格） | 未読。`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS` | — |
| **D-M3**（lead が 2026 年の BoJ 政策決定を読んだ） | **`JPY_RATE_RELATED_FORWARD_CONFIRMATION_CONTAMINATED_BY_EXTERNAL_INFORMATION_EXPOSURE`** | **JPY 金利に関係する forward 確認だけ**。signal か judged P&L が政策金利・短期金利・利回りを使う track が対象（M01・M11・M16 の judged、carry 系、M15、T-R/T-R2）。FX 価格の forward 全体とは扱わない |
| D-M1 ALFRED の metadata（2026 年の最新観測）・D-M2 EPU | external information exposure | その series の確認では開示が要る |
| D-5 next-five の bulk response | 保護期間の行を memory 上で parse し、保存前に切った | U1–U5 の source |
| C-1 Top-Five の保護 parquet 行 | 報告値の前に閉じた | Top-Five |
| CPI 前年比の分母・HICP 2025=100・SA 係数 | 保護期間の水準が逆算可能な形で保存された（逆算はしていない） | M01・M11・M16 |
| ML Step 4 の holdout | CONSUMED | M1 lineage（終了） |
| seen として消費済みのもの | M15 archive の 3 window、公開 pre-2016 の FX と macro | holdout には使えない |

## 21. Forward Eligibility（§26・§27）

**最低条件 F1〜F8**（全部満たしても、forward は別の Red gate である）:

| 条件 | 内容 |
| --- | --- |
| F1 | tier A |
| F2 | null percentile ≥ 0.95、または p ≤ 0.05。family-max の p が記録されていればそれを使い、**同じ mechanism の全ての決定 span で**成り立つこと |
| F3 | TC-net から conservative の financing drag（0.274）を引いても正 |
| F4 | 有効 N ≥ 10（distinct signal states は不明扱い） |
| F5 | 最悪の LOO > 0、かつ top-10 日の寄与 < 1 |
| F6 | D-M3 の対象でない |
| F7 | forward の長さで意思決定が変わる |
| F8 | 凍結 digest・manifest・1 回限りの実行が commit されている |

**tier A・B・C の primary 102 行に当てた結果、F1〜F6 を全て満たす行は 0 本だった。**

- 最も多く満たしたのは T5 recent（F3・F5・F6）で、F1 と F2 で落ちる。
- M16 total（F3・F4・F5）は、F1・F2・F6 で落ちる。

**forward の情報量（§27）**: 事前分布に、forward の観測（SE = √(1/年)）を加えた場合。

| forward の長さ | 6 か月 | 12 か月 | 24 か月 | 36 か月 |
| --- | ---: | ---: | ---: | ---: |
| Sharpe の SE | 1.41 | 1.00 | 0.71 | 0.58 |
| 事後 SD の縮小（tier A の新候補の事前分布 N(0.07, 0.57²)） | 7% | 13% | 22% | **29%** |
| forward 単独で z > 1.96 になる確率（片側 2.5%、同じ事前分布） | 3.8% | 5.0% | 7.3% | **9.4%** |
| 事後 SD の縮小（狭い事前分布 N(0.1, 0.15²)） | 0.6% | 1.1% | 2.2% | 3.2% |

**読み方:**

- 候補について何も分かっていない（事前分布が広い）ほど、forward から学べることは多い。それでも 36 か月で SD は約 3 割しか縮まない。
- forward 単独で有意になる確率は 1 割に届かない。
- **forward は「確かめる」ためのもので、「探す」ためのものではない。** 今は、確かめる候補が無い。

## 22. Broker Financing Trigger（§29）

**条件（全て必要）:**

| 条件 | 内容 |
| --- | --- |
| B1 | financing を除いた edge が正で、null percentile ≥ 0.95 |
| B2 | financing の不確実性が結論を左右する（cell の間で符号が変わる。#495 の cell から読んだ） |
| B3 | 有効 N ≥ 10 |
| B4 | 実際の financing で意思決定が変わる |
| B5 | それより大きな不確実性（検出力・汚染・data の質）が支配していない |

| | B1 | B2 | B3 | B4 | B5 | 判定 |
| --- | --- | --- | --- | --- | --- | --- |
| **M15** | ✗（ex-fin 0.007、pct 0.43） | ✓（markup で total の符号が変わる） | ✗（有効 N 5.0） | ✗ | ✗（tier C、D-M3） | **満たさない** |
| M16 | ✗（ex-fin 0.35、pct 0.84 < 0.95） | ✗（8 cell で符号は変わらない） | ✓（23.1） | ✗ | ✗（tier C、D-M3） | 満たさない |

- **M15 は trigger を満たさない**（裁定の確認どおり）。
- trigger の限界: carry を収穫する book（M15 のように spot ≈ 0 で、edge が financing そのもの）では、B1 は原理的に成り立たない。
  - その場合に問うべきなのは「carry が retail の markup を上回るか」である。
  - M15 の carry 込み total も percentile 0.60 で、null を超えていない。
- **今 broker financing を認証で取っても、どの判断も変わらない。**

## 23. Paid Data Trigger（§30）

**条件:**

| 条件 | 内容 |
| --- | --- |
| P1 | 無料 data では検定できない、事前に書いた具体的な仮説がある |
| P2 | その data の期間・頻度・breadth で、想定する効果に検出力がある |
| P3 | point-in-time で、保護期間を request で除外できる |
| P4 | 費用が情報量に見合う |
| P5 | Human + ChatGPT の承認 |

- **現時点では、有料 data の候補仮説が 1 つも書かれていない。P1 の時点で満たさない。** ledger の行には当てていない。
- 有料 data の価値は「新しい signal」にあるのではない。event 数や breadth で有効標本を増やし、§11 の年数の制約を破れるかどうかにある。

## 24. STOP / CONTINUE Conditions（§31・§32・§33）

**STOP**（どれか 1 つで、終了か保留の判断を Human + ChatGPT に上げる）:

| 条件 | 内容 |
| --- | --- |
| S1 | 検出力のある設計でも null と区別できない状態が続き、残りの未検定領域が有料 data か forward しかない |
| S2 | 年 5% に要る TC-net Sharpe（vol 10% で 0.50〜0.77）が、programme の縮小推定の上位でも届かないと確かめられた |
| S3 | 保護 data を使う以外に情報を増やす手段が無く、その使用が承認されない |
| S4 | financing を含めた retail net が、どの現実的な仮定でも負 |

**CONTINUE:**

| 条件 | 内容 |
| --- | --- |
| C1 | 事前固定の family 単位の設計で、検出力 ≥ 0.5 を持てる対象がある |
| C2 | 未検定の情報源に、経済的な理由と point-in-time の入手経路がある |
| C3 | 目的を「年 5% の戦略」から「情報の測定」へ明示的に変え、その予算を認める |

**現状の評価:**

- **S1 は、無料 data と seen の範囲では当てはまりつつある。** ただし公開の長い span に古典的 premia という未検定の領域が残っているので、完全には当てはまらない。
- **S2 は、点推定では当てはまる**（平均 0.07）。ただし tier A の τ の上限（0.55）を考えると、「確かめられた」とまでは言えない。
- **C2 は、公開の長い span の断面 carry・中期 momentum について成り立ちうる。**
  - 長い span は既に seen である。ただしこの定式化は未検定なので、事前登録すれば tier A になりうる。
  - その場合の検出力は 17.7 年で Sharpe 0.3 に対して 0.24 で、C1 は満たさない。
- **C3 は人の判断事項である。**

`FX_RESEARCH_PAUSED` は自動では立てない。

## 25. Programme Path Comparison（§15）

どの path でも、decision-bearing な結論には forward での Formal Confirmation が要る。したがって B・C は forward の**前の選別**であって、forward の代わりではない。

| path | 情報量 | 検出力 | overfit risk | data 要件 | 時間 | engineering | forward 消費 | broker / 有料 | 5% との関係 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A 単一 signal の逐次探索 | 低 | 低（0.1–0.3） | **高** | 中（無料 data は大半を使った） | 選別 1 本 1 cycle ＋ 確認 3 年以上 | 中 | 候補ごと | retail 判断には financing | 低 |
| B family 単位の事前登録 | 中 | 中（family 共通の効果があるときだけ） | 低 | 新 source か保護 data | 選別 1–2 cycle ＋ 確認 3 年以上 | 中 | family で 1 回 | 同上 | 中〜低 |
| C 事前固定の多 source 合成 | 中 | 中（cost 後 s が 0 の source は足しても 0） | 中（source の選び方） | 既存 source（seen で結果を知っていれば tier D） | 選別 1 cycle ＋ 確認 3 年以上 | 中 | 1 回 | 同上 | 低（s = 0.2 の source が ρ = 0.1 で 15 本要る。推定 s は約 0.07） |
| D forward を待つ | 低（36 か月で SE 0.58） | 非常に低 | なし | なし | 3 年以上 | 低 | 消費する | 同上 | 低（確かめる候補が無い） |
| E 保留・終了 | なし | — | なし | なし | — | なし | 保存 | 不要 | なし |

## 26. Recommended Research Architecture

1. **path A（単一 signal の逐次探索）はやめる。** 32 の mechanism で 0 本という結果と、検出力の算術が同じことを言っている。続けると、多重性と seen の消費だけが増える。
2. **続けるなら、1 cycle に 1 つだけにする。**
   - やることは事前固定の合成（C）か、family 単位の検定（B）。1 つの統計量を 1 回だけ検定し、best-of-N は使わない。
   - 実行前に検出力を計算して記録する。
   - 候補は「事前登録済みで、一度も結果を見ていない組み合わせ」に限る。最も自然な候補は、公開の長い span での断面 carry と中期 momentum を**事前固定の等リスク**で合成したもの。
   - その検出力も 17.7 年で 0.24〜0.56（真の Sharpe 0.3〜0.5）しかない。この事実を先に受け入れる必要がある。
3. **forward と fresh pool は「確かめる」ためだけに使い、「探す」ためには使わない。** 今は確かめる候補が無いので、どちらも消費しない。
4. **broker financing と有料 data は、trigger（§22・§23）を満たすまで取らない。**
5. **判断の目的を明示的に選ぶ。**
   - 年 5% を目的とするなら、現在の証拠は STOP 側に近い。
   - 情報の測定を目的とするなら、予算と終了条件を先に決める。

## 27. Final Answers to 10 Questions

1. **positive evidence は null と区別できるか。** → **できない。**
   - tier A の経済的検定で、percentile 0.9 以上は 0 本。
   - p ≤ 0.05 は、期待 0.4 本に対して 1 本（family-max では 0.12）。
   - family-wise で通ったのは 1 panel の 1 cell（CPI 4h）だけで、もう一方の panel では通らなかった。
   - mechanism 単位の gross の符号は 8 対 8。
   - EB では μ̂ = +0.07（SE ≥ 0.13）、τ̂ = 0（上限 0.55）。
2. **単一 signal の探索を続けるか。** → **主な方法としては続けない。** 1 本あたりの検出力は 0.1〜0.3 で、続けても多重性と seen の消費が増えるだけ。
3. **family-level testing をするか。** → **条件付きで可。**
   - 新しい source、または未検定の定式化で行う。
   - 1 つの統計量、事前の検出力計算、best-of-N なしを条件とする。
   - seen の再利用は tier D にしかならない。
4. **弱い source の固定集約をするか。** → **年 5% の手段としては期待できない。**
   - cost 後の真の s = 0.2 の独立な source が、ρ = 0.1 で 15 本要る。
   - 推定される s は約 0.07 で、集約の上限は約 0.2。
   - 情報の測定として 1 回試す価値はある。
5. **年 5% は research-feasible か。** → **現在の証拠では、そう言えない。**
   - TC-net で Sharpe 0.50〜0.77（vol 10%）と、DD の中央値 −23% を受け入れる必要がある。
   - そこに近い source が無い。
6. **年 10% は。** → **届かない**（TC-net 1.0〜1.27 が要る）。
7. **forward の価値は。** → **今は低い。**
   - 36 か月で事後 SD が 3〜29% 縮む（事前分布の広さによる）。
   - 単独で有意になる確率は 1 割未満。
   - 価値が出るのは、null を超えた候補ができてから。
8. **broker financing の価値は。** → **今は低い。** M15 は trigger を満たさない。M16 も満たさない。
9. **有料 data の価値は。** → **具体的な仮説と検出力の計算が先。** 今は P1 を満たす候補が無い。
10. **次の cycle で何をするか。** → **次は「判断の cycle」で、「探索の cycle」ではない。**
    - Human + ChatGPT が §28 の 3 点を決める。
    - 続ける場合は、事前固定の合成 1 本か family 検定 1 本だけにし、実行前に検出力を記録する。

## 28. Human + ChatGPT Decisions（最大 3）

1. **FX alpha の研究を続けるか（path B/C）、保留・終了するか（path E）。**
   - 無料 data と seen の範囲では、STOP の S1 と S2（点推定）が当てはまりつつある。
   - 未検定の領域は、公開の長い span の古典的 premia と、有料・保護 data だけが残っている。
2. **続けるなら、目的を「年 5% の戦略」から「情報の測定」に変えるか。**
   - 変えるなら、予算（cycle 数）と終了条件を決める。
   - 年 5% を目的のままにするなら、TC-net 0.5〜0.77 の Sharpe と、DD の中央値 −17〜−23% を前提として受け入れることになる。
3. **保護 data（fresh pool 4.9 年、forward）を、事前固定の合成または family の 1 回の検定に使ってよいか。**
   - 使っても、単独の検出力は Sharpe 0.3 に対して 0.10 程度しかない。
   - 使えば、その span は二度と確認に使えない。

## 29. Review（§34）

役割は 3 つ。いずれも lead とは別の session で、source と diff を読み直した。他の役割の結論は渡していない。

**Role 1 — 統計・多重検定・検出力・evidence synthesis**

- **BLOCKER 1 件**: 主たる縮小推定が tier C を A と同じ重みで pool していた。C を含む τ̂ は cost が支配する Top-Five の T4・T3 で決まっていた。M16 の forward prior は、M16 自身の C 行を含む pool から作られていた。
  - **修正**: 主たる推定を A / A+B にした。C を含む推定は感度扱いにした。τ の 95% 上限を出すようにした。新候補の事前分布は tier A から作り、M16 の prior は削除した。
- **REQUIRED FIX 7 件**:
  - R1: Sharpe の定義が混在していた（M01 は spot-only で 0.30、judged では 0.08）。→ 定義を 1 つにした。
  - R2: M11 の D-M3 判定が漏れていた。→ `rate_exposure` を追加した。
  - R3: F2 が cell 単独の p で通っていた。→ family-max の p を使い、全決定 span で成り立つことを要求した。
  - R4: gross の符号の binomial 検定が、鏡像と span の重複を数えていた（26/39 → 8/16）。→ mechanism 単位で数えるようにした。
  - R5: Round 2 の best of 39 を tier A にしていた。`sharpe_like` を比較可能な値として扱っていた。→ best of 39 を tier B にし、`sharpe_like` は notes に移した。
  - R6: τ = 0 の扱いが脆く、境界にも flag が無かった。→ 両方直した。
  - R7: 既知の答えと照合するテストが無かった。→ DerSimonian–Laird との比較、境界、binomial、forward、同じ span の二重計上のテストを追加した。
- **NON_BLOCKING**: T-R2 の二重計上、片側/両側のラベル、事前分布の SD、有効 N の意味、F3 の実装。全て修正した。
- **ACCEPTED**: 22 行の書き起こしが一致した。基本の算術も正しかった。

**Role 2 — FX 経済・retail business・portfolio feasibility**

- **BLOCKER 1 件**: drag を vol に依存しない年率 % で置いていた。vol を上げると要求 Sharpe が下がって見える向きに誤っていた。conservative の drag も、記録された不利な端点より小さかった。
  - **修正**: drag を Sharpe の単位で扱うようにした。financing は #495 の cell から、transaction cost は記録された gross − net から取るようにした。
- **REQUIRED FIX 8 件**:
  - TC と financing が 1 つの数値に混ざっていた。→ 列を分けた。
  - `annual_cost` の単位が混在していた。→ bp の行に flag を付けた。
  - path C の到達本数が算術的に誤っていた。→ 算術から計算するようにした。
  - 集約の cost に関する注意書きが逆向きだった。→ 書き直した。
  - path 比較が不公平だった（B・C も forward が要る）。→ 列を追加した。
  - carry・CPI・COT を閉じすぎていた。→ MDE を付けて、検出力不足に移した。長い span の古典的 premia を未検定に追加した。
  - DD を過小評価していた。→ 確率的 vol・gap・Sharpe の不確実性の変種を追加した。
  - financing の符号の変化を手で打ち込んでいた。→ artifact から読むようにした。
- **NON_BLOCKING**: B5 が汚染を見ていなかった。carry book での trigger の限界、stale な artifact、eligibility の並び順、片側のラベル。全て修正した。
- **ACCEPTED**: 近似 financing を実際の broker financing と書いた箇所は無い。「FX に edge は無い」とも書いていない。どの関数も許可を返さない。

**修正後の再監査**（別の新しい context）: §29a に記す。

**Role 3（governance）**: 置いていない。代わりに、Role 1・2 と再監査が保護 data・許可・status の扱いを確認した。

**lead の判断**

- 両 role の BLOCKER と REQUIRED FIX は全て、証拠を確かめたうえで受け入れた。
- 却下したものは無い。
- 修正の結果、結論は変わらなかった。ただし 2 点は言い方を弱めた:
  - 当初の「mechanism の真の効果の 5% 以下しか 0.5 を超えない」は、C を含む推定から出ていたので撤回した。tier A では「区別できるほどの証拠が無い（τ の上限 0.55）」とした。
  - 当初の「gross に小さな正の傾き」（26/39）も、見かけだったので撤回した。

### 29a. 再監査

別の新しい context で、source と出力を読み直した。修正の主張は信用せずに再導出している。

**RESOLVED 22 件**:

- 統計: S-B1、S-R1、S-R3、S-R4、S-R5、S-R6、S-NB1〜4、S-NB7。
- 経済: E-B1、E-R1〜5、E-R7、E-R8、E-N1、E-N3〜5。
- 付随の確認:
  - MR の judged の値（M01 0.0804・M11 0.1593・M10 −0.4502）は、artifact と一致した。
  - part A は builder から byte 単位で再生成できた。

**PARTIALLY_RESOLVED 3 件**（どれも修正した）:

| 項目 | 残っていた問題 | 修正 |
| --- | --- | --- |
| S-R2 | D-M3 の判定が、非 USD の政策金利 surprise（T2 policy_rate）と BoJ 声明の tone（U3）を漏らしていた | 判定の対象に追加した |
| S-R7 | 既知の答えと照合するテストが、年数重みの pooling・null の数・予測の割合・forward の確率で欠けていた | 追加した |
| E-R6 | CPI の closure の文言が、4h の family-wise 通過（family-max p 0.040）を落としていた | 本文 §7・§18 と `rules.CLOSED` を直した |

**新しく見つかった defect**:

- **REQUIRED FIX 2 件**（どちらも修正した）:
  - τ̂ = 0 のとき、割合が 0% / 100% に縮退していた。「tier A の全 mechanism の真の値が正」と読めてしまう。→ 予測分布 N(μ̂, τ² + SE²) に変えた。
  - CPI の文言。→ 上の E-R6 と同じ修正。
- **NON_BLOCKING 4 件**:
  - gross の推定に #495 の carry 込みの gross が混ざっていた。→ financing を含まない行だけにした。
  - percentile が family-max の p を上書きできた（潜在的な問題）。→ family-max を優先するようにした。
  - 事前分布からの DD が、financing 抜きの平均を全 cost 後として使っていた。→ central の drag を引くようにした。これで 10 年後に損失で終わる確率は 46% から 50% になった。
  - A+B が A と同一なのに、独立の確認のように見えた。→ そう明記した。
- **受け入れた（未修正）もの**:
  - part B〜E の builder は import した時点で書き込むので、テストに組み込んでいない。lead が手で再実行し、byte 単位で一致することを確認した。
  - MR の F5 は judged P&L の LOO で、F3 は spot の TC-net で判定している。どちらも記録どおりの値なので、そのまま使った。

修正後の状態:

- test: 45 本すべて通過。
- research test 一式: 2,053 passed、101 skipped（data の opt-in が要るもの）。
- 結論: 変わらなかった。

**governance role（Role 3）**: 独立には置いていない。代わりに Role 1・2 と再監査が次を確認した:

- 保護 data を読んでいない。
- 許可を返す関数が無い。
- status が変わっていない。
- 近似 financing を実際の broker financing と書いていない。

---

**STOP（§39）。** この報告で cycle を止め、Human + ChatGPT に返す。この PR は Amber で、merge は承認待ちである。
