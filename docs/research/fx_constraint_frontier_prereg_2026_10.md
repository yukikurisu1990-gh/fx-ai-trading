# FX Feasibility Constraint Frontier — 事前登録（2026-10-11、分析の前）

**この文書は、broker の調査・合成の較正・haircut の監査・data の長さの計算・frontier の行列のどれよりも前に commit する。** 指示 §52 に従い、cost・horizon・年数・haircut の model・統計の契約・候補の母集団と、それらから feasible / 分類を決める規則を固定する。結果を見て frontier を広げない。

権限: `docs/governance/fx_feasibility_constraint_frontier_review_2026_10.md`。新しい alpha は探さない。target の return は読まない。

## 1. 共通の式（desk）

候補 c について、1 回の機会の gross を g（bp）、all-in の往復の cost を c（bp）、保有の窓の σ を σ（bp）、年の機会を n、実効の breadth を k、効果の残存率（decay / haircut）を d とする。

- 年率の net Sharpe: **s = √(n · k) · (d · g − c) / σ**
- 年率の gross Sharpe: s_g = √(n · k) · d · g / σ
- break-even の cost: c* = d · g
- 検出に要る年数（片側 α、検出力 1 − β）: **T(α, β) = ((z_{1−α} + z_{1−β}) / s)²**

入力の値は §8 の凍結した表だけを使う。表に無い値は推定しない（`NOT_RECORDED` の候補は、その段で計算しない）。

## 2. 制約の軸と範囲（凍結）

| 軸 | 水準 | 内容 |
| --- | --- | --- |
| **cost** | E0 | PR #508 の Track B の OANDA の実測（該当する pair・時間帯の中央値 + slippage 0.5 bp） |
| | E1 | 現実的な低 cost の retail broker。§3 の調査の、**自動売買が可能な**国内 / 海外の retail の口座の、公表の通常時の spread の**中央値** + slippage の範囲 |
| | E2 | 信頼できる最良の retail の執行。campaign ではなく継続的に提供される公表の spread の**最小**（自動売買が可能な口座） + slippage の範囲の下端 |
| | E3 | 理論の 1.0 bp（all-in の往復）。HOLD の trigger A の値。**実在を主張しない** |
| | E4 | 0.75 bp と 0.5 bp。**sensitivity だけ**で、feasible な点の根拠に使わない |
| **horizon** | H0 | 現行: NY 17:00 の前に決済 |
| | H1 | ≤ 24 時間、週末をまたがない |
| | H2 | ≤ 36 時間、週末をまたがない |
| | H3 | ≤ 48 時間、週末をまたがない |
| **統計の契約** | S0〜S4 | §5 |
| **独立の年数** | 5 / 10 / 15 / 20 / 30 年 | §6 |
| **effect の残存率 d** | 監査の分布 | §7。0 / 25 / 50 / 75% の点の grid では選ばない |

## 3. cost の軸の規則（Track C1）

- 公開の情報だけ（account の作成・login・取引・demo をしない）。
- 記録は `ADVERTISED`（公表）と `MEASURED`（実測）を分ける。公表の spread を実測の all-in と同じものとして扱わない。
- 区別する項目: 公表の spread・通常時の spread・実測の spread・手数料・slippage・約定の拒否・spread の拡大の方針・rollover（swap）・注文の制約・最小の取引単位・**自動売買（API / EA）の可否**。
- 実約定の slippage の data が無い場合は、範囲で扱う: **slippage は 0.2〜0.5 bp（片道の合計ではなく往復）**。E1 は範囲の中央 0.35 bp、E2 は下端 0.2 bp。
- **自動売買ができない口座の spread は、E1 / E2 の根拠にしない**（Human の目的 O0 は automated）。参考として別に記録する。
- 公表の spread が「原則固定」で、時間帯（例: 早朝・指標の発表）を除外している場合、除外の時間帯を記録し、候補の執行の時刻がその中にある場合は E0 の値を使う。

## 4. horizon の軸の規則（Track C2）

- 新しい alpha を探さない。既存の mechanism の自然な保有の窓だけを使う。
- 各 horizon の per-trade の値:
  - σ(H) = σ₀ · √(H / H₀)（H₀ は現行の保有時間）。
  - cost は 1 往復で不変。保有が NY 17:00 をまたぐ場合、**financing（swap の bid / ask の非対称）f bp / 夜** を加える。f は §3 の調査の値、無ければ範囲 0.2〜1.0 bp / 夜。
  - **G-FLAT**（既定）: mechanism は H₀ の中で完了し、g(H) = g。延長は雑音だけを加える。
  - **G-PERSIST**（上限）: g(H) = g · √(H / H₀)。per-trade の gross の S/N を保ったまま、cost / σ だけが √(H / H₀) で薄まる。**horizon の延長の利益の上限**で、mechanism の記録に持続の根拠がある場合だけ realistic とする。
  - 機会の数 n は不変（1 日 1 回以下の mechanism の場合）。
- H2 / H3 は、デイトレードの目的からの逸脱の度合いを明記する。自動採用しない。

## 5. 統計の契約の比較（Track C3、合成の較正）

### 5.1 合成の model

- family の数 F = 6、family ごとの window / pair の variant W = 4。
- variant の推定の誤差: block の長さ T 年で、年率の Sharpe の推定 ŝ ~ N(θ, 1 / T)。family の中の variant の誤差の相関 ρ_w = 0.7（「相関の強い window」の scenario では 0.9）。
- 選択の block S（T_S = 4.67 年）と独立な推定の block E（T_E = 6.4 年が既定、§6 で変える）は独立。
- family の間の誤差の相関は 0（「共通の USD factor」の scenario では 0.3）。
- variant の真の値は family の値 + N(0, 0.1²) の異質性。
- system の真の Sharpe は、採用した family の真の値の、相関 R の下の最適な合成 √(θᵀ R⁻¹ θ)。
- 乱数の seed は 20261011 から決定的に。反復は scenario ごとに 20,000。

### 5.2 scenario（凍結）

| ID | 中身 |
| --- | --- |
| Z0 | 全て 0 |
| W1 | 1 family が弱い（真の net Sharpe 0.4） |
| W2 | 2 family が弱い（0.4、0.4） |
| M1 | 1 family が中程度（0.8） |
| M2 | 2 family が中程度・低相関（0.8、0.8） |
| M3 | 3 family が中程度・低相関（0.8 × 3、真の system 約 1.39） |
| U | M2 と同じで、family の間の誤差の相関 0.3（共通の USD factor） |
| P | 全て 0 で、Bayes の契約の prior の平均だけが 0.6（**古くなった prior**） |
| C | M2 と同じで、family ごとの cost の誤差 N(0, 0.15²)（S と E で共通、真の net を動かす） |
| R | M2 と同じで、ρ_w = 0.9（相関の強い window） |

### 5.3 契約（凍結）

全ての契約の最後は同じ **G4 の判定**: E の block で、採用した family の合成の推定 Ŝ_E に **system の prior N(0, τ_sys²)、τ_sys = 0.4**（PR #506 の契約）を課し、事後の平均 Ŝ_E · τ²T_E / (τ²T_E + 1) ≥ 1.0 なら GO。component の縮小の和で G4 を迂回しない。

| 契約 | 選択の block S | E の block |
| --- | --- | --- |
| **S0（現行）** | 全ての F·W の variant に Bonferroni（片側 family-wise 10%）。かつ点推定 ≥ 0.3、S の前半と後半で符号が同じ | 片側 t > 1.28 かつ S と同じ符号の family だけ残す。その後 G4 |
| **S1（system 先行の Bayes）** | family ごとに variant を相関を考慮して平均し、family の間で経験 Bayes の正規の階層 model で部分 pooling。事後の P(θ > 0) ≥ p₁ の family を採用 | 採用した family をそのまま G4（component の E での有意を要求しない） |
| **S2（2 段の portfolio 先行）** | family の平均の事後の P(θ > 0) ≥ 0.5（正の事後の確率と mechanism だけ） | 凍結した portfolio 全体の E の推定に片側 α = 0.10 の単一の検定。通れば G4 |
| **S3（階層の family）** | family ごとに variant を相関を考慮して平均（family の推定）。F family に Bonferroni（片側 family-wise 10%） | S0 と同じ |
| **S4（重複を減らした頻度論）** | F·W の variant に、**実効の試行数 M_eff**（相関行列の固有値による Li–Ji の方法）での Bonferroni（片側 family-wise 10%）。点推定 ≥ 0.3、前後半の符号 | S0 と同じ |

- S1 の閾値 p₁ は、**Z0 の scenario だけ**で、component の偽陽性の率（1 つ以上の null の family を採用する確率）が S0 の Z0 の値以下になる最小の値に較正する。実の候補は使わない。
- S1 / S2 の prior: family の prior の平均は 0（P の scenario だけ 0.6）。

### 5.4 指標

| 指標 | 定義 |
| --- | --- |
| component の FWER | 1 つ以上の null（真の値 0）の family を、E の block の後まで残す確率 |
| system の偽の GO | GO で、かつ採用した portfolio の真の system の Sharpe < 1.0 |
| 検出力（component） | 1 つ以上の真の family を、E の block の後まで残す確率 |
| 検出力（G4） | 真の system ≥ 1.0 の scenario での GO の確率 |
| bias | GO の場合の、事後の system の Sharpe − 真の system の Sharpe の平均 |

### 5.5 採用の規則（指示 §22、結果の前に凍結）

S1〜S4 のうち、次を全て満たす契約を「S0 より優れる」とする:

1. Z0 と P の component の FWER が、S0 の Z0 の値 + 0.01 以下、かつ 0.10 以下。system の偽の GO の率が、全ての scenario で S0 の値 + 0.01 以下。
2. W1・W2・M1・M2・M3 の component の検出力の平均が、S0 より 0.10 以上高い。
3. bias の平均が、S0 より 0.05 以上大きくない。
4. 調整する定数が 3 つ以下。
5. governance で監査できる（判定が決定的で、事前に固定できる）。

複数が満たす場合は、検出力の平均が最も高いもの。差が 0.02 以内なら、定数の少ない方。どれも満たさなければ **S0 を維持**する。**選んだ契約は、§9 の実の候補の計算の前に、記録に凍結する**（合成の結果の commit を、候補の行列の計算の commit より前に置く）。

## 6. data の長さの軸（Track C4）

- protected fresh は読まない。必要な独立の年数を理論で求める。
- 候補 × 契約ごとに、独立の年数 5 / 10 / 15 / 20 / 30 年で、**decision-grade**（§9 の定義）になるかを計算する。
- **G4 の年数**: system の真の Sharpe S で P(GO) = Φ((S − 1 − 1 / (τ²T)) · √T)。P(GO) ≥ 0.5 には T ≥ 1 / (τ² (S − 1))。
- **入手可能性**（公開の情報だけ。有料の data は買わない）: pre-1990 / 1990 年代 / 2000 年代 / 2010 年以降の bid / ask の historical FX の data の源・解像度・期間・価格を調べる。
- **文献との重なり**: 文献の sample と重なる期間は、replication / calibration には使えるが、independent confirmation には使わない。候補ごとに、独立に使える年数 = 入手可能な年数 − 文献の sample と重なる年数 − seen の期間 − protected の期間。

## 7. haircut の監査（Track C5 の前提、候補と独立）

- H-07 を見て決めない。複数の市場の anomaly と FX の文献の、**公表の後の効果の減衰（post-publication decay）と replication の研究**から、残存率 d の分布を作る。
- d を点にせず、分布（Beta）を置き、平均と分位点を記録する。
- **区別**: 文献で公表された効果の減衰（d_pub）と、直接の証拠の無い desk の予測の割引（d_desk）は別の量である。d_desk に外部の研究の直接の値が無い場合、その旨を記録し、d_pub の分布を上限の参考にする。
- 現行の 50% の固定の haircut と比べ、分布のどの分位点に当たるかを記録する。

## 8. 凍結した候補の母集団

repo の記録からの抽出（新しい候補は作らない）。値は記録の値だけ。略号: MR = `fxid_final_mechanism_feasibility_review_2026_10.md`、P1F = `fx_system_p1_p2_fast_track_final_2026_10.md`、CD = `fx_component_discovery_fast_track_final_2026_10.md`、FA = `fx_frontier_track_a_record_2026_10.md`、CP = `m15_final_classical_premia_final_report_2026_09_29.md`、UF = `m15_usd_factor_financing_final_report_2026_09_24.md`、T5R = `m15_top_five_final_report_2026_09_21.md`。

### 8.1 計算する候補（intraday・当日、H0〜H3 の中）

| ID | 候補 | 状態（記録） | mechanism | n × k | g（bp、出典） | c（E0、bp） | σ（bp） | d の種類 | 文献の sample |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **K1** | F1 EUR の欧州の朝（02:00 → 08:15 ET、EUR_USD の売り） | `ECONOMICALLY_UNATTRACTIVE`（MR:355）、HOLD の near-miss | fix の dollar の需要の dealer の在庫（KMW）と home-hours の自国通貨安（Breedon–Ranaldo） | 250 × 1 | **2.8**（KMW L1、約 2.8 bp / 日、MR:274）。参考 3.3（L6 の gross/σ 0.115 × 28.6、MR:298） | 1.94（MR:295） | 28.6 | d_pub | 1997–2018 |
| **K2** | F1 JPY の東京の仲値の後（仲値 → 02:00 ET、JPY の買い） | `ECONOMICALLY_UNATTRACTIVE`（MR:356）、「最近の期間では弱まり…約 0」 | W 字の仲値の後の脚 | 250 × 1 | **3.3**（L1、MR:275）。**2013 年以降は half spread で平坦**（MR:174、MR:315） | 1.72（MR:310） | 27.3 | d_pub、かつ古い証拠 | 1999–2018 |
| **K3** | 中銀の発表日の premium（FOMC + 日銀、1 family） | `NEW_COMPONENT_SUPPLY_NOT_FOUND`（K8 で kill、CD:23） | VaR に制約された仲介者の発表日の premium（MTV 2017） | FOMC 8 × 1、日銀 8 × 1 | FOMC **10.30**（dol の差、t = 2.27、CD:199）、日銀 **14.78**（Base 7.39 = 差 × 50%、CD:242-247） | FOMC 2.66、日銀 3.54（CD:223-224） | FOMC 60、日銀 51（記録。日銀は t からは約 97〜99 で過小、CD:230-231） | d_pub | 1994–2013 |
| **K4** | H-07 週末の再開の流動性の反転（日曜 17:00〜19:00 ET） | **`UNRESOLVED_BOUNDARY_CANDIDATE`**（今回の裁定） | 週末の gap の risk を負う LP の在庫 | 15 × 2.5 | **6**（Role H の prior、直接の証拠なし、FA:55） | 2.7（**測定なし**、FA:150） | 26 | **d_desk** | なし |

- K3 の family の Sharpe は、2 つの窓を独立として √(s_FOMC² + s_BoJ²)（CD:28 と同じ）。
- K3 の日銀の σ は、記録の 51 と、t から含意する 98 の両方で計算する（98 を既定、51 を sensitivity）。
- K1 の g は 2.8 を既定、3.3 を sensitivity。
- 候補の間の相関の記録は無いので 0 とする（§9 の 5）。

### 8.2 参考だけの候補（保有が月次・日次の book で、H0〜H3 の範囲の外）

| ID | 候補 | 状態（記録） | 記録の値 |
| --- | --- | --- | --- |
| R1 | #497 古典の premia（carry + 12-1 momentum） | `POSITIVE_EXPLORATORY_BUT_NOT_CONFIRMATION_READY`（CP:348） | TC-net Sharpe 0.127、gross 0.148、cost 0.23% / 年、vol 10.74%（CP:205-211、CP:132）。2008–2016 は負（CP:233） |
| R2 | M16 US 対 他国の macro の momentum → USD | `M16_CORRECTED_POSITIVE_EXPLORATORY_NOT_DECISION_GRADE`（UF:229） | net ex-financing 0.348、total central 0.276（UF:212-216）。最近の 2.1 年は −0.50（UF:227） |
| R3 | T5 · S26 TIC の flow → USD | `T5_S26_POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE`（T5R:29-30）、結果を見た後の訂正の記録 | 最近 2.2 年 net +0.838（MDE95 1.321）、長い期間 −0.017（T5R:279-287） |

- R1〜R3 は、objective の frontier（O0〜O5、≤ 48h）の外にあることを示すためだけに載せ、feasible な点の根拠に使わない。

### 8.3 除外（復活させない）

EUR の ECB の fix の後・London fix の後・月末の hedge・仲値の直後の spike / gotobi・機関の order flow・発表の drift・intraday momentum・R-A2b の NY 09:00 / 09:30（cost の環境の検査で component ではない）・M-OV1・H-01〜H-06・M15 の dollar carry と T1〜T4。理由は各記録（MR:323-363、RA:504-505、CD:110、FA:49-54、UF:27、T5R:39）。

### 8.4 独立に使える年数（§6 の規則の適用）

| 候補 | 文献の sample | 独立に使える期間（fresh を除く） |
| --- | --- | --- |
| K1 | 1997–2018 | seen 2021-04-26 … 2025-12-28（4.67 年。F1 の return は未計算、MR:60）。pre-2016 は文献と重なる |
| K2 | 1999–2018 | 同上 4.67 年 |
| K3 | 1994–2013 | 2014-01 … 2016-05（2.4 年）+ seen 4.67 年 = 7.1 年（CD:259） |
| K4 | なし | pre-2016 の入手可能な bid / ask の全期間（§6 の調査）+ seen 4.67 年 |

- 入手の deviation: 規約が研究の利用を許す無料の data は 0、規約が不明の無料の data は 1（確認の Red の承認が要る）、有料は 2。

## 9. feasibility の定義（指示 §40、凍結）

候補（または system）が、ある frontier の点で **feasible** とは、次を全て満たすこと:

1. **mechanism**: repo の記録に mechanism がある。
2. **net > 0**: その点の cost・horizon・d の中央値で、s > 0。
3. **現実的な検出の経路**: その点の契約で、component の検出力 ≥ 0.5 に要る年数が、**独立に使える年数**（§6）以下。
4. **偽陽性の制御**: 契約が §5.5 の 1 を満たす（S0 か、選ばれた契約）。
5. **G4 への合理的な経路**: その候補を含む system（凍結した母集団の中の、同じ点で net > 0 の候補の最適な合成。候補の間の相関は記録の値、無ければ 0）の真の Sharpe S_sys で、P(GO) ≥ 0.5 に要る年数 1 / (τ²(S_sys − 1)) が、独立に使える年数以下。
6. **独立な確認**: fresh の 4.9 年（2016-06-02 … 2021-04-25）で、system の片側 5% の検出力 ≥ 0.5（S_sys · √4.9 ≥ 1.645）。

**decision-grade** = 3 と 5 を満たすこと。

**要る年数の計算（凍結）**:

- 独立に使える年数 Y を、選択の block T_S = 0.42 · Y と推定の block T_E = 0.58 · Y に分ける（現行の 4.67 : 6.4 の比）。
- component の検出力は、§5 の合成の model で「1 family が真の s、他の 5 family が 0」の scenario を、その契約で回した値（反復 20,000）。Y は 1 年刻み（1〜60 年）で探し、検出力 ≥ 0.5 の最小の Y を「要る年数」とする。60 年でも届かなければ「> 60」。
- G4 の要る年数は、T_E = 0.58 · Y で P(GO) ≥ 0.5 となる最小の Y、すなわち Y ≥ 1 / (0.58 · τ² · (S_sys − 1))。
- s ≤ 0 の点は、要る年数を ∞ とする。

## 10. 目的の frontier と逸脱の度合い（Pareto、凍結）

| 変更 | 目的からの逸脱の点 | 備考 |
| --- | --- | --- |
| 統計の契約 S0 → 選ばれた契約 | 0（目的は変えない。governance の変更） | §5.5 で選ばれた場合だけ |
| cost E0 → E1 | 1 | broker の変更。自動売買の可否を含む |
| cost E0 → E2 | 2 | |
| cost E3 / E4 | 採らない | sensitivity だけ（実在を主張しない） |
| horizon H1 | 2 | 当日決済からの逸脱 |
| horizon H2 | 3 | |
| horizon H3 | 4 | |
| 独立の年数: 規約が研究の利用を許す無料の data | 0 | |
| 独立の年数: 規約が不明の無料の data | 1 | 規約の確認と取得の Red の承認 |
| 独立の年数: 有料の data | 2 | 購入は Human の承認 |
| d | 採らない | d は経験の prior で、選ぶ変数ではない（監査の中央値を使う。分位点は sensitivity） |

- 目的の水準: O0 = FX・当日・retail・自動、O1 = ≤ 24h、O2 = ≤ 36h、O3 = ≤ 48h、O4 = 当日・低 cost の国内の執行、O5 = ≤ 24 / 36h・低 cost の retail。**採用案ではなく、frontier を見るだけ**。
- **最小の逸脱の feasible な点**: 逸脱の点の合計が最小の feasible な点。同点は、feasibility の余裕（独立に使える年数 / 要る年数の比）の大きい方。

## 11. 寄与の分解（指示 §47〜§48）

- 連続の指標 **feasibility の余裕 M = ln(独立に使える年数 / 要る年数)**（net ≤ 0 なら M = −∞ を −5 で打ち切る）を、候補ごと・system で計算する。
- 5 つの switch（cost: E0 → E2、horizon: H0 → H1、契約: S0 → 選ばれた契約、年数: 現行の E の 6.4 年 → 無料の最大、d: 0.5 → 監査の中央値）について、32 の組み合わせの M から **Shapley 値**を計算する。
- 失敗の理由を、gross が小さい・cost・頻度が低い・年数が足りない・統計の gate・古い証拠・相関が高い・horizon・portfolio の集中、に分ける。

## 12. 最終の分類の規則（指示 §49、凍結）

1. 現行の O0 に近い点（逸脱 ≤ 1）に feasible な system がある → **CONSTRAINT-G**
2. 単独の switch（逸脱 ≤ 2）で feasible な system が現れ、その switch が cost → **B**、horizon → **C**、契約 → **D**、年数 → **E**
3. 単独では無いが、逸脱の合計 ≤ 4 の組み合わせで現れる → **F**
4. それ以外 → **A**（「何を変えても無理」ではなく、**この事前登録の reasonable な frontier の範囲では、production の目標への合理的な経路が無かった**と書く）

feasible な点がある場合（B〜G）だけ、`FXID_REOPEN_AT_FEASIBLE_FRONTIER_PROPOSAL` を作る。実証は Human の承認待ち。

## 13. 記録（provenance）

code の commit、入力の hash、command、時刻、dirty の状態、出力の hash、seed、環境を、全ての計算の記録に保存する。記録は上書きを拒否する。
