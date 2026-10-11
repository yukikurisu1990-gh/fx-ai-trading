# FX Feasibility Constraint Frontier — 最終報告（2026-10-11）

`PRODUCTION_READINESS_NOT_CLAIMED`. 権限: `docs/governance/fx_feasibility_constraint_frontier_review_2026_10.md`。事前登録: `docs/research/fx_constraint_frontier_prereg_2026_10.md`（`732fa49`）。

**記録の略号**:

| 略号 | 中身 |
| --- | --- |
| 【P】 | 事前登録 |
| 【R】 | 役割の記録 `docs/research/fx_constraint_frontier_role_records_2026_10.md`（agent への指示の逐語と出力の要点） |
| 【S】 | 合成の較正の記録 `artifacts/research/fx_constraint_frontier/synthetic_contracts.json`（sha256 `f2d433da…`） |
| 【F】 | frontier の行列の記録 `artifacts/research/fx_constraint_frontier/frontier.json`（sha256 `2900dcc7…`） |
| 【I】 | 入力 `scripts/research/fx_constraint_frontier/inputs.json`（公開の調査から事前登録の規則で転記） |
| 【算術】 | この報告の中の計算 |

## 1. Executive Summary

**最終の分類: CONSTRAINT-A — `NO_REASONABLE_CONSTRAINT_RELAXATION_MAKES_FXID_FEASIBLE`**。

**この事前登録の reasonable な frontier の範囲では、production の目標（system 単位の事後の net Sharpe ≥ 1.0）への合理的な経路が無かった**。「何を変えても無理」という意味ではない。

| 問い | 答え（数字） |
| --- | --- |
| **主因は何か** | **edge の供給（効果の大きさ × 公表の後の残存率）が、cost に比べて小さいこと**。現実の点（残存率 d の中央値 0.32、horizon は G-FLAT）では、net > 0 の候補を全て最適に合成しても、system の真の Sharpe の上限は **0.47**（E2: 自動売買が可能な口座の最良の公表の cost）。検出の問題の前に、1.0 に届く材料が無い |
| cost だけで救えるか | **いいえ**。4 つの候補の全てで、critical cost は負（cost 0 でも、使える独立の年数で検出力 0.5 に届かない） |
| horizon だけで救えるか | **いいえ**。mechanism が当日に完了する（G-FLAT）なら、延長は σ を増やすだけで Sharpe は下がる。持続の上限（G-PERSIST）でも、E0 の下で最大 +0.31（K4） |
| 統計の契約で救えるか | **いいえ**。合成の較正で S1〜S4 は事前登録の採用の基準を満たさず、**S0 を維持**。最も近い S3 / S4 でも検出力の上積みは +0.06〜+0.07（基準は +0.10） |
| 独立の年数で救えるか | **いいえ**。G4 の system の prior（τ = 0.4）の下で、真の system の Sharpe 1.33 でも独立な推定の block が約 33 年要る。K1 / K2 は文献の sample と重なり、独立に使える pre-2016 の期間は有料の 1986〜1990 年代だけ |
| 50% の haircut は妥当か | **楽観的**。文献の公表の後の減衰から作った分布 Beta(1.2, 2.2) の **73 パーセント点**（中央値 0.32） |
| H-07（K4） | 現実の点で net < 0（E0 2.7 bp、d の中央値）。cost の改善は適用されない（週の開始は全ての broker の原則固定の時間帯の外）。**`UNRESOLVED_BOUNDARY_CANDIDATE` のまま**で、data で反証されたわけではない |

**最も感度の高い点**（sensitivity だけで、feasible の根拠にしない）: 残存率の 90 パーセント点・最良の公表の cost・持続の上限・有料の data を全て重ねても、system は約 1.33 で、G4 に約 33 年要り、使える年数（17.67 年）を超える。**どの点も feasible にならなかった**（672 点のうち 0）。

## 2. #508 merge record

| 項目 | 値 |
| --- | --- |
| PR | #508 |
| 確認した head | `0ae7bfd`（CI success、unexpected な diff なし、未解決の BLOCKER 0） |
| merge | `d71ed657e766dcb39c09edbd3cfec16209270c25`、2026-10-11T14:12:07Z（`--match-head-commit` で head を固定） |
| master | `d71ed65` |
| master の CI | success（run 38146219782、2026-10-11T14:24:19Z 完了）。その後にこの programme を開始 |

## 3. Authoritative state

- **`FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE`**（`docs/governance/fxid_long_term_hold_ruling_2026_10.md`、sha256 を test で固定、不変）。
- FRONTIER-A は `NO_ORIGINAL_MECHANISM_SURVIVES_UNDER_CURRENT_PREREGISTERED_FRONTIER_CONTRACT` と読む（権限の文書 §1）。`FX_HAS_NO_EDGE`・`FX_DAY_TRADING_IS_IMPOSSIBLE`・`H-07_IS_FALSIFIED` などの意味は持たない。
- H-07 は `UNRESOLVED_BOUNDARY_CANDIDATE`。
- PR #508 の Track B は、OANDA の対象の pricing の tier × seen の期間 × 20 pair × 調べた M15 の時間帯の観測。

## 4. Frozen candidate universe

【P】§8。新しい候補は作っていない。

| ID | 候補 | 状態 | mechanism | horizon | n × k | g（bp） | c（E0） | σ | 証拠の時期 | 検証の問題 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| K1 | F1 EUR の欧州の朝 | `ECONOMICALLY_UNATTRACTIVE`、HOLD の near-miss | fix の dollar の需要の在庫・home-hours | 02:00→08:15 ET（6.25h） | 250 × 1 | 2.8（KMW） | 1.94 | 28.6 | 1997–2018 | pre-2016 は文献と重なる |
| K2 | F1 JPY の仲値の後 | 同上、「最近は約 0」 | W 字の仲値の後の脚 | 仲値→02:00 ET（約 5.5h） | 250 × 1 | 3.3（KMW） | 1.72 | 27.3 | 1999–2018、**2013 年以降は平坦** | 古い証拠・同上 |
| K3 | 中銀の発表日の premium（FOMC + 日銀） | `NEW_COMPONENT_SUPPLY_NOT_FOUND`（K8） | VaR に制約された仲介者 | 18:00→16:45 ET | 8 + 8 | 10.30 / 14.78 | 2.66 / 3.54 | 60 / 98 | 1994–2013 | 低頻度、σ が大きい |
| K4 | H-07 週末の再開 | `UNRESOLVED_BOUNDARY_CANDIDATE` | 週末の gap の risk を負う LP | 日曜 17:00〜19:00 ET（2h） | 15 × 2.5 | 6（desk の prior） | 2.7（測定なし） | 26 | 無し | 直接の証拠なし、cost も未測定 |

- 参考だけ（H0〜H3 の範囲の外）: R1 #497 古典の premia（TC-net 0.127）、R2 M16（0.276）、R3 T5 · S26（長い期間 −0.017）。月次・日次の book で、≤ 48h の objective の frontier の中に入らない。
- 除外（復活させない）: 【P】§8.3。

## 5. Current failure decomposition

現行（E0・H0・d = 0.5 の固定・S0・使える年数）【F】:

| ID | s | 要る年数（S0、検出力 0.5） | 使える年数 | 主な理由 |
| --- | --- | --- | --- | --- |
| K1 | −0.30 | ∞ | 4.67 | cost > 残存の gross（break-even 1.40 bp < 1.94） |
| K2 | −0.04 | ∞ | 4.67 | 同上（break-even 1.65 < 1.72）、古い証拠 |
| K3 | +0.16 | > 60 | 7.1 | 低頻度・大きい σ |
| K4 | +0.07 | > 60 | 4.67 | 直接の証拠なし、cost の測定なし |

d を監査の中央値 0.32 にすると、K1 −0.57、K2 −0.38、K3 +0.05、K4 −0.18【F】。

## 6. Execution-cost frontier

【R】§1、【I】。

| 水準 | 内容 | K1（EUR_USD） | K2（USD_JPY） | K3 | K4 |
| --- | --- | --- | --- | --- | --- |
| E0 | OANDA の実測（MEASURED） | 1.94 | 1.72 | 2.66 / 3.54 | 2.7（測定なし） |
| E1 | 自動売買が可能な口座の公表の中央値 + 0.35（ADVERTISED） | 0.76 | 0.66 | E0（時間帯の外） | E0（週の開始は除外） |
| E2 | 最良の公表 + 0.2（ADVERTISED） | 0.53 | 0.33 | E0 | E0 |
| E3 | 理論の 1.0 bp（sensitivity） | 1.0 | 1.0 | 1.0 | 1.0 |
| E4 | 0.75 / 0.5 bp（sensitivity） | | | | |

- **E1 / E2 は公表の値で、実測ではない**。OANDA の実測は OANDA 自身の公表の約 2.2 倍だった。自動売買が可能な口座の約定・slippage・拒否の公表の記録は無い。
- E1 / E2 は 1.0 bp（HOLD の trigger A の値）を下回るが、**trigger A は「all-in の継続的な実測」を求めており、公表の値はそれを満たさない**。trigger A は観測されていない。
- K3 と K4 の執行の時刻は、全ての口座の原則固定の時間帯の外にあり、【P】§3 の規則で E0 を使った。

## 7. Retail broker comparison

【R】§1.2。**主要な国内の業者（SBI・DMM・GMOクリック・みんなのFX・外為どっとコム・ヒロセ）は、約款で自動売買を禁止している**。0.2 銭（約 0.13 bp）の狭い原則固定の spread の多くは、自動売買ができない口座のもの。自動売買が可能で通常時の spread を公表している口座は、OANDA（MT5・NY プロ）・FXTF（MT4）・Saxo（OpenAPI）の 4 つ。Saxo の固定の spread が API の注文に適用されるかは未確認。

## 8. Critical-cost analysis

【F】`critical`（S0、使える年数、d の中央値、最初の窓）:

| ID | break-even の cost | 検出力 0.5 に要る s | critical cost | 意味 |
| --- | --- | --- | --- | --- |
| K1 | 0.90 bp | 1.68 | **−2.14** | cost 0 でも 4.67 年では届かない |
| K2 | 1.06 bp | 1.68 | **−1.84** | 同上 |
| K3（FOMC の窓） | 3.31 bp | 1.27 | **−23.6** | 同上 |
| K4 | 1.93 bp | 1.68 | **−5.20** | 同上 |

- **cost だけで救える component は無い**。E2 で net が正になるのは K1（+0.20）と K2（+0.42）だが、K2 でも検出に 55 年要る。

## 9. Holding-horizon frontier

【P】§4。σ(H) = σ₀√(H/H₀)、NY 17:00 をまたぐ夜ごとに financing 0.2 bp（範囲の下端、feasibility に有利）、日次の候補は金曜の entry を失う（n × 0.8）。

| ID | H0 | H1 G-FLAT | H1 G-PERSIST | H3 G-FLAT | H3 G-PERSIST |
| --- | --- | --- | --- | --- | --- |
| E0: K1 | −0.57 | −0.31 | −0.09 | −0.26 | +0.03 |
| E0: K2 | −0.38 | −0.21 | +0.07 | −0.19 | +0.18 |
| E0: K3 | +0.05 | +0.04 | +0.04 | +0.02 | +0.08 |
| E0: K4 | −0.18 | −0.07 | +0.26 | −0.06 | +0.31 |
| E2: K1 | +0.20 | +0.04 | +0.26 | −0.01 | +0.28 |
| E2: K2 | +0.42 | +0.13 | +0.42 | +0.06 | +0.42 |

（d の中央値、【F】。）

## 10. Critical-horizon analysis

- **G-FLAT（mechanism が当日に完了）では、延長は Sharpe を上げない**。E0 で負の値が 0 に近づくのは、cost / σ が薄まるからで、正にはならない。E2 では延長で下がる。
- **G-PERSIST は上限**で、mechanism の記録に持続の根拠がある場合だけ realistic（【P】§4）。fix の flow（K1 / K2）と発表日（K3）には持続の根拠が無い。K4 は記録に horizon が無い。
- **critical horizon は無い**: H3（≤ 48h）でも、どの候補も検出力 0.5 の s（1.68）に届かない。
- 逸脱の度合い: H1 は当日決済からの逸脱（点 2）、H2 は 3、H3 は 4（【P】§10）。

## 11. Statistical-contract alternatives

【P】§5.3: S0（現行、variant の Bonferroni）、S1（system 先行の Bayes、部分 pooling）、S2（2 段の portfolio 先行）、S3（階層の family）、S4（Li–Ji の実効の試行数）。全ての契約の最後は同じ G4（system の prior τ = 0.4 を system に直接）。

## 12. Synthetic null calibration

【S】、反復 20,000、seed 20261011。component の FWER（null の family を E の後まで残す確率）:

| scenario | S0 | S1 | S2 | S3 | S4 |
| --- | --- | --- | --- | --- | --- |
| Z0（全て 0） | 0.004 | 0.002 | **0.081** | 0.003 | 0.007 |
| P（古い prior） | 0.005 | **0.163** | 0.097 | 0.003 | 0.008 |

- S1 の閾値 p₁ = 0.99 は Z0 だけで較正した（S0 の 0.00405 以下）。**古い prior（平均 0.6）の下で S1 の FWER は 0.163 に上がる**。
- system の偽の GO は全ての契約・scenario で ≤ 0.002。

## 13. Synthetic power comparison

component の検出力【S】:

| scenario | S0 | S1 | S2 | S3 | S4 |
| --- | --- | --- | --- | --- | --- |
| W1（0.4） | 0.047 | 0.019 | 0.249 | 0.057 | 0.071 |
| W2（0.4 × 2） | 0.094 | 0.044 | 0.427 | 0.115 | 0.141 |
| M1（0.8） | 0.299 | 0.142 | 0.664 | 0.369 | 0.376 |
| M2（0.8 × 2） | 0.511 | 0.303 | 0.904 | 0.607 | 0.614 |
| M3（0.8 × 3） | 0.651 | 0.448 | 0.977 | 0.747 | 0.757 |
| 平均 | 0.320 | 0.191 | 0.644 | 0.379 | 0.392 |

**G4 の GO の率**（真の system が約 1.39 の M3 でも）: S0 0.014、S1 0.010、S2 0.078、S3 0.028、S4 0.023。**どの契約でも G4 は事実上通らない**。G4 の判定（τ = 0.4、E 6.4 年）は、観測の system の Sharpe 約 1.98 を要求する【算術: 1 + 1 / (0.16 × 6.4)】。

## 14. Selected statistical contract

**S0（現行）を維持**（【S】`selection`、【P】§5.5 の規則）。

| 契約 | 偽陽性（基準 1） | 検出力 +0.10（基準 2） | bias（基準 3） | 結果 |
| --- | --- | --- | --- | --- |
| S1 | ×（P で 0.163） | ×（0.191） | ○ | 不採用 |
| S2 | ×（Z0 で 0.081） | ○（0.644） | ×（+0.058、S0 は −0.061） | 不採用 |
| S3 | ○ | ×（+0.059） | ○ | 不採用 |
| S4 | ○ | ×（+0.071） | ○ | 不採用 |

- 選択は合成の結果だけで行い、候補の行列の計算（`88ee224` 以降）の前に記録を commit した（`522af5d`）。
- **critical contract**: S3 / S4 にすると、検出力 0.5 に要る s は 4.67 年で 1.68 → 1.52 / 1.53、7.1 年で 1.27 → 1.15 / 1.16【F】。候補の s（最大 0.42）からは遠い。
- 現行の契約は「false-negative factory」かという問いへの答え: **component の段では S0 は保守的**（S3 / S4 は同じ偽陽性で約 2 割高い検出力）**だが、結論を決めているのは component の契約ではなく、G4 の判定と効果の大きさ**。

## 15. Publication-decay / haircut audit

【R】§3。

- **d_pub ~ Beta(1.2, 2.2)**: 平均 0.353、中央値 0.322、10%点 0.072、90%点 0.686。株式の公表の後の減衰（0.42〜0.57）と、より完全な FX の減衰（technical rule は 1990 年代に約 0、carry・momentum・value は公表の後に負）の間で、FX に重みを置いた。
- **固定の 50% は 73 パーセント点**（楽観的）。Harvey & Liu も「経験則」とし、Sharpe < 0.4 では 50% 超の haircut を示す。
- **d_desk の直接の値は無い**。文献は d_desk ≤ d_pub の上限だけを与える。K4 には d_pub の分布を上限として使った（K4 に有利）。
- 監査は候補を見ずに行い、候補の結果の前に入力に固定した（`88ee224`）。

## 16. Data-length frontier

**component**（S0、検出力 0.5、1 family が真の s）【F】【算術: 合成の検索】:

| 真の s | 要る独立の年数 |
| --- | --- |
| 0.5 | 40 |
| 1.0 | 12 |
| 1.27 | 7（7.1 年で届く最小の s） |
| 1.68 | 4（4.67 年で届く最小の s） |

**G4**（system の事後 ≥ 1.0 の確率 0.5、E = 0.58 · Y）【算術: Y = 1 / (0.58 · 0.16 · (S − 1))】:

| 真の system の Sharpe | 要る独立の年数 |
| --- | --- |
| 1.1 | 108 |
| 1.2 | 54 |
| 1.33 | 33 |
| 1.5 | 22 |
| 2.0 | 11 |

5 / 10 / 15 / 20 / 30 年の各水準で、**現実の点の候補（s ≤ 0.42）はどれも decision-grade にならない**（s 0.42 の要る年数は 55 年）。

## 17. Independent-data availability

【R】§2、【I】。

| ID | 文献の sample | current | 規約が不明の無料 | 有料 |
| --- | --- | --- | --- | --- |
| K1 | 1997–2018 | 4.67 | 4.67 | 15.67（Olsen 1986–1996 + seen） |
| K2 | 1999–2018 | 4.67 | 4.67 | 17.67（1986–1998 + seen） |
| K3 | 1994–2013 | 7.1 | 7.1 | 7.1（定時の発表は 1994 年以降） |
| K4 | 無し | 4.67 | 20.67（HistData 2000-05〜 + seen） | 35.07（Olsen 1986〜 + seen） |

- 文献の sample と重なる期間は replication / calibration にだけ使い、independent confirmation には使わない（【P】§6）。
- 研究の利用を明確に許す無料の intraday の bid / ask は見つからなかった。**日曜の再開の被覆は、どの源も文書で確認できない**（K4 の data の前提が未確認）。
- 1990 年代以前の intraday は indicative な quote で、執行の cost の転用は難しい。
- 有料の data の購入は Human の承認が要る（行っていない）。

## 18. Objective frontier

【P】§10。O0〜O5 は採用案ではなく、frontier を見るだけ。

| 目的 | 近い点 | 現実の点での system の上限（d の中央値） | feasible |
| --- | --- | --- | --- |
| O0 FX・当日・retail・自動 | E0・H0 | 0.05 | × |
| O1 ≤ 24h | E0・H1 G-FLAT | 0.04 | × |
| O2 ≤ 36h | E0・H2 G-FLAT | 0.02 | × |
| O3 ≤ 48h | E0・H3 G-FLAT | 0.02 | × |
| O4 当日・低 cost の国内の執行 | E1 / E2・H0 | 0.25 / 0.47 | × |
| O5 ≤ 24 / 36h・低 cost | E2・H1 / H2 G-FLAT | 0.14 / 0.07 | × |

（system の上限 = net > 0 の候補の √Σs²、検出を問わない参考の量、【F】`s_sys_all_positive_reference`。）

## 19. Candidate-by-constraint matrix

【F】`matrix`: cost 6 水準 × horizon 4 × horizon の model 2（H0 は 1）× d 4（p10 / 中央値 / 固定 50% / p90）× 年数 4 = **672 点**。抜粋（H0、G-FLAT、current の年数）:

| cost | d | K1 | K2 | K3 | K4 | system の上限 |
| --- | --- | --- | --- | --- | --- | --- |
| E0 | 中央値 | −0.57 | −0.38 | +0.05 | −0.18 | 0.05 |
| E0 | 固定 50% | −0.30 | −0.04 | +0.16 | +0.07 | 0.18 |
| E0 | p90 | −0.01 | +0.31 | +0.28 | +0.33 | 0.54 |
| E1 | 中央値 | +0.08 | +0.23 | +0.05 | −0.18 | 0.25 |
| E1 | p90 | +0.64 | +0.93 | +0.28 | +0.33 | 1.21 |
| E2 | 中央値 | +0.20 | +0.42 | +0.05 | −0.18 | 0.47 |
| E2 | 固定 50% | +0.48 | +0.76 | +0.16 | +0.07 | 0.92 |
| E2 | p90 | +0.77 | +1.12 | +0.28 | +0.33 | 1.43 |
| E4 0.5 bp | 中央値 | +0.22 | +0.32 | +0.18 | +0.34 | 0.55 |

- component が decision-grade になる点は、d の p90 か固定 50% で、かつ持続の上限か有料の data を伴う点だけ（K2 は 20 点、K4 は 54 点、全て sensitivity）。**d の中央値の点では 0**。
- feasible な system の点は、sensitivity を含めて **0 / 672**。

## 20. Binding constraint decomposition

| ID | 1 位 | 2 位 | 3 位 |
| --- | --- | --- | --- |
| K1 | gross が小さい（d の中央値で break-even 0.90 bp） | cost（E0 1.94） | 年数（文献と重なる） |
| K2 | 古い証拠（2013 年以降は平坦） | gross が小さい（break-even 1.06 bp） | cost |
| K3 | 頻度が低い（年 16） | σ が大きい（60 / 98 bp） | 年数（7.1） |
| K4 | 直接の証拠なし（d_desk） | cost が未測定で、改善の対象外（週の開始） | 日曜の data の被覆が未確認 |
| system | **edge の供給**（現実の点で上限 0.47 < 1.0） | G4 の判定 × 独立の年数（1.33 でも 33 年） | 統計の契約（影響は小さい） |

## 21. Pareto frontier

- **逸脱の点の定義された点**（d の中央値・G-FLAT・E0〜E2・H0〜H3・年数の 4 水準）の中で feasible は 0。Pareto frontier は空。
- 逸脱が小さい順の最良の点（参考）: E2・H0（逸脱 2）で system の上限 0.47。それ以上の逸脱（horizon・有料の data）は上限を上げない。

**Shapley の寄与**（【P】§11、feasibility の余裕 M = ln(使える年数 / 要る年数)、−5 で打ち切り）【F】:

| 対象 | cost | horizon | 契約 | 年数 | d |
| --- | --- | --- | --- | --- | --- |
| system | 0 | 0 | 0 | 0 | 0 |
| K1 | +0.92 | −0.46 | 0 | 0 | −0.46 |
| K2 | +1.62 | −1.44 | 0 | 0 | −0.18 |
| K3 | 0 | 0 | 0 | 0 | 0 |
| K4 | 0 | 0 | 0 | 0 | 0 |

- **system・K3・K4 の Shapley は全て 0** で、**情報を持たない**: 32 の組み合わせの全てで余裕が下限 −5 に張り付いた（事前登録の設計の限界）。K1 / K2 では cost が唯一の正の寄与。horizon と d は負（G-FLAT の延長は σ を増やし、監査の d の中央値 0.32 は固定の 0.5 より小さい）。契約の switch は S0 → S0 で 0。

## 22. Minimal feasible relaxation

**無し**（【F】`classification.minimal_feasible = null`）。

## 23. Final classification

**CONSTRAINT-A — `NO_REASONABLE_CONSTRAINT_RELAXATION_MAKES_FXID_FEASIBLE`**。

- **この事前登録の reasonable な frontier の範囲（cost E0〜E2、horizon ≤ 48h、契約 S0〜S4、独立の年数は有料まで、d は文献の監査の中央値）では、production の目標への合理的な経路が無かった**。
- 主因: **edge の供給**。cost・horizon・契約・年数の単独の緩和でも、組み合わせでも、現実の点で system の上限は 1.0 に届かない。
- `FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE` を維持する。

## 24. Reopen proposal if applicable

**該当しない**（feasible な点が無い）。`FXID_REOPEN_AT_FEASIBLE_FRONTIER_PROPOSAL` は作らない。

**HOLD の trigger への含意**（判定ではなく材料）:

- trigger A（all-in ≤ 1.0 bp の継続）: 自動売買が可能な口座の**公表**の値は 0.33〜0.76 bp だが、実測ではない。実測で確認されても、現実の点の system の上限は 0.47（E2）で、trigger A だけでは G4 への経路にならない。
- 必要なのは edge の供給の側（trigger B・C: 文献の sample の後の新しい独立の証拠、事前に観測できる新しい flow の情報源）。

## 25. Independent reviews

（下に記録する。）

## 26. Governance compliance

| 項目 | 状態 |
| --- | --- |
| fresh・OOS・dead・forward | 読んでいない。価格の data は一切読んでいない（合成と、repo の既存の記録と、公開の情報だけ） |
| 取引・account・login・demo・入金 | 無し（broker の調査は公開の頁だけ） |
| data の取得・購入 | 無し（入手可能性と価格の調査だけ） |
| 新しい alpha・mechanism・indicator・ML | 無し。候補は記録の 4 つ（と参考の 3 つ）だけ |
| G4 | 1.0 を維持。system の prior τ = 0.4（#506）を変えていない |
| 事前登録の順序 | 事前登録 `732fa49`（14:29:28Z）→ 調査の起動 → 合成の code `b34bf79` → 合成の記録 `522af5d`（契約を凍結）→ 行列の code と入力 `88ee224` → 行列の記録 `4afb68d`。結果を見て frontier を広げていない |
| 契約の選択 | 合成だけで、候補の行列の前に凍結 |
| HOLD の裁定 | 不変（test で sha256 を固定） |
| provenance | 記録に head・dirty 0・事前登録の sha256 と commit・code の sha256・入力の sha256・command・時刻・seed・反復・環境（Python 3.12.10、numpy・scipy の版）を保存。記録は上書きを拒否 |

**開示**:

- **E1 / E2 は公表の値**（ADVERTISED）で、実測ではない。swap の非対称は抽出できず、financing は範囲の下端 0.2 bp / 夜（有利な側）を使った（1.0 bp の sensitivity も記録）。
- **【P】§5.2 の scenario C は文面どおり**（cost の誤差が真の net を動かす）に実装した。「推定だけが cost の誤差で偏る」という別の読み方は検証していない。
- **Shapley の system・K3・K4 の値は −5 の下限に張り付き、情報を持たない**（§21）。代わりに system の上限（検出を問わない参考の量）で判断を補った。この参考の量は事前登録の分類の規則には使っていない。
- K4 の H0 = 2 時間、K2 の H0 = 5.5 時間は、記録の窓からの lead の設定（【P】§8.1 の窓の記述）。
- 入力の転記は lead が事前登録の規則で行い、【R】と【I】に根拠を残した。
- 日次の候補の H1〜H3 で金曜の entry を失う（n × 0.8）設定は、【P】§4 の「週末をまたがない」の実装。

## 27. Human + ChatGPT decision request

1. **CONSTRAINT-A を受け入れ、`FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE` を維持することを確認するか**。
2. **この PR の記録**（合成の契約の比較・broker の公開の frontier・減衰の監査・独立の data の入手可能性）を、HOLD の trigger の評価の基準として merge するか。特に:
   - 50% の固定の haircut に代わり、**d_pub ~ Beta(1.2, 2.2)** を将来の desk の評価の既定にするか。
   - 主要な国内の業者が自動売買を禁止している点を、trigger A の評価の前提として記録するか。
3. **今後の方針**: 主因は edge の供給なので、cost・horizon・契約の側の再検討ではなく、trigger B・C（新しい独立の証拠・新しい flow の情報源）が観測されるまで HOLD を続けるか。それとも、目的（FX・当日・retail・自動）の外側（月次の premia など）を Human が別に検討するか。
