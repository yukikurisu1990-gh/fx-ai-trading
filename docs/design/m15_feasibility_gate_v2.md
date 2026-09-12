# Research Feasibility Gate v2 — 設計と凍結

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Status: **`FEASIBILITY_GATE_V2_PROSPECTIVE_ONLY`** ·
**`FEASIBILITY_GATE_V1_LEGACY_FROZEN`**

本文書は Human + ChatGPT の裁定（PR #475 merge 後、Gate v2 を Track 2 より先に
design-only で作る）に従う。**Track 2 の signal / return を一切見る前に**凍結する。
実装は `scripts/research/feasibility/`、契約テストは
`tests/research/test_feasibility_gate_v2.py`。

---

## 1. なぜ v1 を置き換えるのか

Gate v1 は

    decidable  ⟺  MDE ≤ 2 × cost

だった。これは **statistical power と transaction cost を同一の条件に混ぜている**。
Track 3 がその帰結を実地で示した:

* コストが**上がる**と hurdle も上がるので、悪化した設計が powered になる
  （`ny_option_cut pre · month-end` は passive 執行で headroom が −1.566 → +0.356、
  MDE は 7.956 のまま不動）。
* コストが**下がる**と hurdle も下がるので、安くなった設計が powered を**失う**
  （`london_fix pre · month-end` は median C が 65% 下がるのに headroom が
  −8.406/−4.327 → −12.534/−6.732）。

つまり v1 の `decidable` は cost の**下限**を、payable は**上限**を与えており、
両者はコスト軸上の帯を定義していた。コストを下げると帯から下に抜ける。
「コストを下げれば研究がしやすくなる」という前提と噛み合わない。

Gate v2 はこれを **2 つの問いに分離**する。

| gate | 問い |
| --- | --- |
| **A. Statistical Feasibility** | この sample size / variance / dependence で、研究上意味のある最小効果を十分な power で検出できるか？ |
| **B. Economic Feasibility** | その効果が実現したとして、現実的なコストの後に十分な経済価値が残るか？ |
| **C. Robustness** | そもそも二枚のパネルで判定できるだけの事象数があるか？ |

## 2. Gate v1 は削除しない

`FEASIBILITY_GATE_V1_LEGACY_FROZEN`。
`scripts/research/fxunits.py` の `COST_MULTIPLE_FOR_HURDLE = 2.0` と
`scripts/research/clock_flow/frontier.py` の `decidable` は**そのまま残す**。
過去の verdict は Gate v1 での判定として保存し、書き換えない。
テスト `test_gate_v1_is_left_frozen` がこの定数の不変を固定する。

## 3. 遡及適用の禁止（機械強制）

`FEASIBILITY_GATE_V2_PROSPECTIVE_ONLY`。適用対象は **Track 2 以降の新規研究のみ**。

以下は **コードが拒否する**（`RetroactiveApplicationError`）。散文の約束ではなく
`assert_prospective()` が `EXCLUDED_FROM_GATE_V2` を見て例外を投げる:

`track_1_clock_structure` / `exploratory_round_1` / `exploratory_round_2` /
`round_b_prime` / `monetizability` / `prior_macro_surprise` / `cot_positioning` /
`carry` / `track_3_execution_frontier`

Track 1 を Gate v2 で救済することは禁止（cell 再列挙、month-end / London fix の
新基準救済、IR threshold 変更、panel pooling、M1 化、parameter 変更）。
Track 1 の status は `CLOCK_STRUCTURE_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER`
で凍結。再開には新しい独立データ・本質的に新しい measurement・明確に異なる
economic mechanism のいずれかが要る。

## 4. 単位

`#474` で確立した規約を継承。すべて **mid の basis point**、観測ごと変換、
`scripts.research.fxunits` を通す。pips / fractional return を混在させない。
`verify_unit_consistency` が完成レコードを歩き、テストが固定する。

## 5. Design の記述

gate は「設計」を次の 5 つで受け取る。N と frequency を**別入力**にしているのが
要点で、期間を伸ばして N を増やしても MRE は動かない。

| 項目 | 意味 |
| --- | --- |
| `n_events` | 決定パネル上の事象数 |
| `effective_n` | dependence 調整後の有効標本数 |
| `dispersion_bp` | 事象あたり gross の標準偏差 |
| `events_per_year` | 設計の**頻度**（N ではない） |
| `label` | 記録用 |

MDE は `POWER_MULTIPLIER × dispersion_bp / sqrt(effective_n)`、
`POWER_MULTIPLIER = z(0.975) + z(0.80) = 2.802`（両側 5%、power 80%）。

## 6. Minimum Relevant Effect — 本設計の最大の論点

MDE と比較する相手は **事前に定義された最小関連効果**であって、その設計自身の
コストではない。

    MRE_bp = max(
        REFERENCE_ROUNDTRIP_COST_BP + MIN_ANNUAL_NET_RETURN_BP / events_per_year,
        MIN_RELEVANT_EFFECT_FLOOR_BP,
    )

**`REFERENCE_ROUNDTRIP_COST_BP` はプログラム全体の凍結参照値であり、設計自身の
実測コストではない。** ここが §9 の要求そのもの：コストが変わっても statistical
power threshold が動かないようにする。設計のコストは **Economic gate でのみ**使う。

なぜ「純粋にコストを含まない MRE」にしないのか。含めないと MRE は「取引が無料
だったら意味を持つ最小効果」になり、現実に取引できない大きさになる（日次設計で
1 bp 未満）。それは経済的に意味のある閾値ではない。参照コストを**定数として**
置くことで、MRE は経済的に意味を保ちつつ、どの設計のコスト測定からも独立になる。

### 凍結する定数と根拠

| 定数 | 値 | 根拠 |
| --- | --- | --- |
| `REFERENCE_ROUNDTRIP_COST_BP` | 2.5 | Track 3 が 2 パネルで実測した market-order 往復 2.6902 / 2.4660 bp の中間を丸めた値。**参照であって設計のコストではない。** |
| `MIN_ANNUAL_NET_RETURN_BP` | 300.0 | 年 3% の net。これを下回る家族に研究資源を割かないという programme の判断。 |
| `MIN_RELEVANT_EFFECT_FLOOR_BP` | 1.0 | これより小さい効果は microstructure と operational uncertainty から分離できない、という運用上の下限。 |
| `MIN_NET_MARGIN_BP` | 0.5 | execution uncertainty / model error / degradation の余裕。Track 3 は執行方式を現実的な代替に変えるだけで往復が 0.8 bp 動くことを実測した。0.5 はそれより小さく、意図的に控えめ。 |
| `MAX_PLAUSIBLE_GROSS_IR` | 1.5 | unit audit の 3 つの例示 IR の中央値。このプログラムが produce した gross IR は 1.5 に近づいたことがない。 |
| `COST_STRESS_MULTIPLE` | 2.0 | 既存の stress 慣行を継承。 |
| `MIN_EVENTS_PER_PANEL` | 60 | committed な `MIN_EVENTS_PER_DECIDING_PANEL` をそのまま使う。 |

いずれも Track 2 の結果を見る前に凍結する。結果を見てからの変更は禁止。

## 7. A. Statistical Feasibility Gate

    pass  ⟺  MDE_bp ≤ MRE_bp   （両決定パネルで）

コストはここに一切入らない。入力は N、effective N、dispersion、events_per_year、
alpha、power のみ。

## 8. B. Economic Feasibility Gate

「MRE の大きさの効果が実現したとして、コスト後に価値が残るか」を問う。3 条件。

1. **net margin**: `MRE_bp − cost_bp ≥ MIN_NET_MARGIN_BP`
2. **stressed net margin**: 同じ式を `COST_STRESS_MULTIPLE × cost_bp` で。
3. **plausibility**: `implied_gross_annual_IR ≤ MAX_PLAUSIBLE_GROSS_IR`、ここで

        implied_gross_annual_IR = MRE_bp × sqrt(events_per_year) / dispersion_bp

   3 番目が要る理由。頻度の低い設計では MRE が大きくなり、statistical gate は
   自動的に通る。そのとき本当の制約は「そんなに大きな効果が存在しうるか」であって、
   それは統計の問題ではなく経済の問題である。unit audit の break-even gross IR を、
   **設計自身のコストではなく凍結参照から**作り直したものが上式にあたる。

コストは base / stressed の両方で報告する。設計の実測コストを**完全に**使う。

## 9. C. Robustness Gate

最小限に留める。`n_events ≥ MIN_EVENTS_PER_PANEL` を**両方の決定パネル**で満たし、
パネルが 2 枚あること。power 不足を理由に結果を見てからパネルを pool することは
禁止（pooling は diagnostic のみ）。

## 10. 合成判定

    research_feasible = statistical AND economic AND robustness

3 つは**別々に報告**する。それが v2 の存在理由なので、合成値だけを見せない。

## 11. コスト変化に対する挙動（契約テスト）

`tests/research/test_feasibility_gate_v2.py` が synthetic example で固定する。

| example | 操作 | statistical | economic |
| --- | --- | --- | --- |
| **A** | 同じ N / variance でコスト半減 | 不変 | 同等以上 |
| **A′** | コスト倍増 | 不変 | 悪化 |
| **B** | N 増加（frequency 固定） | 改善 | 不変 |
| **C** | variance 増加 | 悪化 | — |
| **D** | gross effect requirement 未達 | — | fail |

v1 との対比もテストで固定する: 同じ入力で v1 の `MDE ≤ 2×cost` はコスト半減に
よって **verdict を反転させる**が、v2 の statistical verdict は動かない。

## 12. 何が binding になるかは設計ごとに違う（合成例）

**入力は説明のための合成値**であり、どの設計の実測でもない。示したいのは
「3 つの gate が別々の仕事をする」という一点。

| design（合成） | N | effective N | dispersion bp | events/yr | cost bp | MDE bp | MRE bp | statistical | net bp | implied IR | economic |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| daily calendar | 519 | 415.0 | 45.0 | 252.0 | 2.69 | 6.19 | 3.69 | fail | 1.00 | 1.30 | fail |
| non-USD macro 1d | 200 | 160.0 | 60.0 | 100.0 | 2.50 | 13.29 | 5.50 | fail | 3.00 | 0.92 | pass |
| month-end clock cell | 25 | 25.0 | 10.7 | 12.5 | 3.11 | 6.00 | 26.50 | pass | 23.39 | 8.76 | fail |

読み方:

* **daily calendar** は統計でも経済でも落ちる。経済側を落としているのは base net
  1.00 ではなく **stressed net**（3.69 − 5.38 = −1.69）で、cost ×2 の列が効いている。
* **non-USD macro 1d** は経済的には成立するが**検出力が足りない**。この形なら
  必要なのはコスト改善ではなく事象数である——v1 ではこの区別が付かなかった。
* **month-end clock cell** は逆。MRE 26.50 は MDE 6.00 よりはるかに大きいので統計は
  自動的に通り、**そんな効果は存在しそうにない**（implied gross IR 8.76）という
  経済の問題だけが残る。plausibility 条項が無ければこの設計は「feasible」と出る。

この表は `test_the_documented_illustration_matches_the_gate` が再計算して照合する。

## 13. ⭐ 合成判定が要求する最小観測年数（凍結後に**導出**した性質、式・定数は不変）

本節は Track 2 への最初の適用で判明した、**既に凍結した式そのものの帰結**である。
threshold も formula も unit convention も変更していない。変えたのは記述だけで、
これを書かないことは gate の性質を隠すことになる。

statistical は `2.802·σ/√effN ≤ MRE`、economic の plausibility は
`MRE·√f/σ ≤ 1.5`（`f` = events per year）。後者を σ について解いて前者に入れると

    effN ≥ (2.802 / 1.5)² · f  =  3.489 · f

`f = N / years` かつ `effN ≤ N` なので、**合成判定は `years ≥ 3.489` を必要とする。**
MRE にも dispersion にも cost にも signal にも依存しない。

本プログラムの決定パネルは **1.996 年**である。したがって:

* **この 2 枚のパネル上では、どの設計も合成判定を通らない。** Track 2 の 6 セルの
  `effN/f` は 1.28〜1.93 で、いずれも 3.489 に届かない。§12 の合成例 3 行も
  1.60 / 1.65 / 2.00 で同じく届かない。
* したがって「economic gate が落ちた」という観測は、**その設計についての所見
  ではなく、パネル長についての所見**として読まなければならない。Track 2 の結果
  文書はその区別を明示している。
* 事前登録の Success 条項（economic gate を要求する）は、**凍結時点で発火不能
  だった**。これは事前登録の欠陥であり、隠さず記録する。

これは gate の誤りではない。年次 IR を 1.5 以下と主張しながら 80% の検出力を持つ
には数年分の独立観測が要る、というのは統計的に正しい。**正しい gate が、この
プログラムの持つデータ地平を測ってしまった**というのが所見である。

`test_the_composite_requires_three_and_a_half_years` がこの導出を固定する。

## 14. 凍結

本文書・実装・契約テストを 1 コミットで凍結し、その SHA を記録する。以後
Track 2 の signal / return を見た後に threshold・式・単位規約を変更しない。
