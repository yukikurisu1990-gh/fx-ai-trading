# Research Design Pass-Region Preflight — 設計

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Status: **`PASS_REGION_PREFLIGHT_SPECIFIED`**

Human + ChatGPT の裁定（PR #476 / #477 の conditional merge 条件）に従う。
**Gate v2 の threshold は一切変更しない。**

---

## 1. なぜ要るのか

Track 2 の最大の問題は threshold ではなかった。

> **Track 2 の signal を見る前に、現在の panel 長では Gate v2 の success region が
> 存在しないと判定できたはずなのに、Stage 1 まで進んだ。**

事前登録の Success 条項は Gate v2 の economic gate を要求する。その gate は
凍結時点で発火不能だった。**研究を始める前に、その研究が原理的に pass 可能かを
確認する preflight が無かった**——直すのはそこである。

役割分担を明示する。

| 段階 | 問い |
| --- | --- |
| **Pass-Region Preflight** | この研究計画は、現在の data horizon で原理的に decision-grade な答えを出せるか？ |
| Gate v2 Statistical | 実際の設計で `MDE ≤ MRE` か？ |
| Gate v2 Economic | その効果は cost 後に十分な価値を持つか？ |
| Final Adjudication | 実際の観測結果が hypothesis を支持したか？ |

## 2. 入力（**signal を一切使わない**）

使ってよい: planned panel length / calendar coverage / event frequency /
planned number of events / effective-N assumption と**その出所** / 事前指定の
variance 推定源 / Gate v2 の MRE / minimum net requirement / expected turnover /
measured execution cost / stressed cost / deciding panel 数 / breadth requirement /
multiple-testing burden（primary cell 数）/ horizon / portfolio degrees of freedom。

**使ってはならない**: realized signal return / gross alpha / net alpha /
observed sign / observed IC / observed Sharpe / observed p-value / 有利な通貨や
ペアの結果 / post-hoc event filtering。過去に signal を見た family についても、
**performance を ranking 材料に使わない**。過去 verdict を「十分反証済み family の
除外」に使うことだけは可。

## 3. ⭐ 中心にある閉形式

Gate v2 の 2 条件を σ について解くと、pass region は **dispersion 軸上の区間**になる。

    statistical   :  z(k) · σ / √effN  ≤  MRE      ⟺  σ ≤ MRE · √effN / z(k)
    plausibility  :  MRE · √f / σ      ≤  IR_max   ⟺  σ ≥ MRE · √f / IR_max

    pass region in σ  =  [ MRE·√f / IR_max ,  MRE·√effN / z(k) ]

区間が空でない条件は **MRE にも σ にも cost にも依存せず**、

    effN  ≥  ( z(k) / IR_max )² · f

`f = N / years`、`effN ≤ N` なので `effN / f ≤ years`。したがって

> **必要有効年数 = (z(k) / IR_max)²。これを下回る panel 長では、
> どんな設計も Gate v2 の合成判定を通らない。**

`z(k)` は primary cell 数 `k` に Bonferroni 補正を入れた
`z(1 − α/2k) + z(power)`。multiple-testing burden がそのまま必要年数を押し上げる。

| primary cells k | z(k) | 必要有効年数 |
| --- | --- | --- |
| 1 | 2.8016 | **3.488** |
| 2 | 3.0830 | 4.224 |
| 3 | 3.2356 | 4.653 |
| 4 | 3.3393 | 4.956 |
| 5 | 3.4175 | 5.191 |
| 8 | 3.5760 | 5.683 |

## 4. 残りの条件

**robustness**: `events_per_year × panel_years ≥ 60`（committed な
`MIN_EVENTS_PER_PANEL`）を**各**決定パネルで、かつパネル ≥ 2 枚。pooling 不可。

**economic net**: MRE は `max(2.5 + 300/f, 1.0)`。stressed が binding なので

    MRE(f)  ≥  COST_STRESS_MULTIPLE × cost  +  MIN_NET_MARGIN

これは frequency の**上限**を与える: `f ≤ 300 / (2·cost − 2)`（cost > 1 bp のとき）。
robustness が下限 `f ≥ 60 / years` を与えるので、**admissible frequency は区間**になる。

**breadth**: 設計が持つ通貨数が要求 breadth 以上か。

**variance**: σ の事前推定がある場合、それが §3 の区間に入るか。無い場合は
区間の存否だけを判定し、σ 推定の出所を要求する。

## 5. Verdict

| verdict | 意味 |
| --- | --- |
| **`PASS_REGION_EXISTS`** | 現在の seen data で Gate v2 を理論上通過可能な設計が存在 |
| **`MARGINAL_PASS_REGION`** | 数学的には可能だが、binding margin が 20% 未満。原則 primary 候補にしない |
| **`NO_DECISION_GRADE_PASS_REGION`** | どの合理的設計でも通れない |
| **`DATA_INTEGRITY_BLOCKED`** | power 以前に provenance / timestamp / coverage / access で研究不能 |
| **`PRIOR_FAMILY_CLOSED`** | 過去研究で同形仮説が十分に反証済み |

判定順序は固定: `PRIOR_FAMILY_CLOSED` → `DATA_INTEGRITY_BLOCKED` → 上の数式群。
**結果を見て順序を変えない。**

## 6. cost の扱い（§11）

cost は **economic net 条件にのみ**入る。horizon 条件にも robustness 条件にも
入らない。したがって:

* cost を下げる → statistical detectability は**動かない**、economic は同等以上
* cost を上げる → statistical は動かない、economic は悪化

v1 の逆転をここで再導入しないための構造上の保証であり、synthetic test で固定する。

## 7. Track 2 への遡及適用（§8、diagnostic のみ）

Track 2 の凍結設計（panel 1.996 年、primary cell 3、deciding panel 2 枚）を入れると、
必要有効年数 **4.653** に対し有効年数は `effN/f ≤ panel_years = 1.996`。
**signal を一切見ずに `NO_DECISION_GRADE_PASS_REGION`** が出る。

**Track 2 の verdict は変更しない。** 目的は、この preflight が今回の失敗を事前に
止められたことの確認だけである。`test_the_preflight_would_have_stopped_track_2`
が固定する。

## 8. 何を変えていないか

Gate v2 の MRE・IR_max・minimum net requirement・N floor・two-panel rule・
`EXCLUDED_FROM_GATE_V2` は**一切変更していない**。preflight はそれらから導かれる
必要条件を**先に**評価するだけで、緩めることはできない——数式が Gate v2 の定数を
import しているので、閾値を動かせば preflight も同じだけ動く。
