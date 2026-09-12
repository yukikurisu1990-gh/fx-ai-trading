# Model-Learning Feasibility — 二つの予算と role 別ゲート（凍結）

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Status: **`CURRENT_SEEN_DATA_FX_RESEARCH_SPACE_EXHAUSTED_FOR_SIMPLE_HYPOTHESIS_TESTING`**

実装は `scripts/research/model_learning/`、契約テストは
`tests/research/test_model_learning_budgets.py` と
`tests/research/test_model_learning_design.py`。

---

## 1. なぜ別問題なのか（裁定 §3）

4.674 年の seen history を

* **alpha の存在証明のために pool する** — 今回は行わない
* **conditional structure の推定に使う** — 今回の対象

は、**別の feasibility 条件を持つ**。前者の条件は前フェーズが出した
`effN ≥ (z/IR_max)²·f` で、`effective_years = panel_years × share ≤ panel_years`
により 1.996 年のパネルでは満たせない。**その裁定は再検討しない。**

後者の条件は「p 値を出せるか」ではなく「**推定できるか**」であり、以下の 2 つに
分解される。どちらも **signal-blind**（price を 1 バイトも読まずに計算できる）。

---

## 2. Capacity budget — 何個のパラメータを載せてよいか

年 `T` 日・1 日あたり `D_eff` 本の独立ベットを持つ設計、パラメータ `p` 個、
目標年次 IR を `IR` とする。

1. `D_eff` 本を束ねた portfolio は `IR = ρ·√(D_eff·T)` に達する。よって
   `R²_true = ρ² = IR²/(D_eff·T)`。
2. `N_eff = D_eff·T·years` 行に `p` 個を当てはめる最小二乗の optimism は
   `p/N_eff`。
3. 定数より良い out-of-sample を得る条件は `R²_true > p/N_eff`、すなわち

```
IR² / (D_eff·T)  >  p / (D_eff·T·years)
```

**`D_eff` も `T` も消える。**

> ### `p  ≤  (1 − retention) × IR_annual² × train_years`

⭐ **サンプリング頻度も断面の広さもこの予算を緩めない。** M15 を M1 にすれば行は
15 倍になるが 1 行あたりの signal は 1/15 になる。通貨を増やせば行は増えるが
1 ベットあたりの signal は同じだけ減る（目標 IR は既に束ねた後の量だから）。
**「1 ペアあたり 116,418 本ある」は「何個のパラメータを当てはめてよいか」の答えに
ならない** — このプログラムは過去にそれを答えとして扱った。

### 4.674 年が許す量

| 目標年次 IR | break-even | retention 0.5 |
| --- | --- | --- |
| 0.25 | 0.292 | 0.146 |
| 0.50 | 1.169 | 0.584 |
| 0.75 | 2.629 | 1.315 |
| 1.00 | 4.674 | 2.337 |
| 1.25 | 7.303 | 3.652 |
| **1.50（凍結された妥当性天井）** | **10.517** | **5.258** |

⭐ **あらゆる頻度・あらゆる許容ボラティリティを通じた有効パラメータ数の絶対上限は
5.258**、そしてそこに届くには IR がちょうど天井の 1.5 でなければならない。

### 成り立たない場合（隠さず書く）

* 最小二乗の結果である。木のアンサンブルの `p` は **実効自由度**で、素朴な
  パラメータ数よりはるかに大きい。本実装の近似は**高めに外す**（予算を甘く見積もる
  近似は overfitting を許可する近似だから）。
* モデル形が signal を表現できることを仮定している。誤特定は左辺を悪くするだけ。
* `IR` は **net** の年次比。cost が壊す gross の大きな `R²` は、パラメータを多く
  許してお金を生まない。
* **downstream で価値が出る表現**（regime state、volatility forecast）は、
  予算を **consumer の IR** に対して課す。`role_gate` がそれを強制する。
* shrinkage 付きモデルにはバイアス項もあるので、この式は**保持率の上界**であって
  約束ではない。

---

## 3. Search budget — 何通り試してよいか

`Y` 年分の out-of-fold で測った年次 IR の標準誤差は約 `1/√Y`。真には等しく無価値な
`M_eff` 個から最良を選ぶと、勝者の推定値は
`E[max of M_eff standard normals]/√Y` だけ膨らむ。採用に値する最小の改善
`MRIE` をそれが飲み込まないためには

> ### `z_max(M_eff)  ≤  MRIE × √validation_years`

⭐ **ここでも年であってバーではない。** そして
`M_eff = 1 + (M_nominal − 1)(1 − ρ_config)` なので、**隣接するハイパーパラメータは
安く、本当に異なるアーキテクチャは高い** — grid search の予算の使い方とは逆である。

`z_max` は Blom 近似 `Φ⁻¹((m−0.375)/(m+0.25))`。小さい `m` で真値を **0.02 ほど
上回る**（m=2 で 0.589 対 0.564）。予算にとっては**安全な向き**：探索の代金を
わずかに高く請求するので、通った設計は厳密値でも通る。

### phase 予算 — トラックごとではなく phase 全体に課す

同じ 3.174 年の out-of-fold で 3 トラックを選ぶのは、**1 つの標本に対する 3 回の
選択**である。トラックごとに課すのは予算を 3 回使うことになる。

| tracks × configs | M_eff | inflation | 可否 |
| --- | --- | --- | --- |
| 1 × 7 | 2.80 | 0.463 | ✓ |
| 1 × 8 | 3.10 | 0.500 | ✓（境界） |
| 2 × 2 | 2.60 | 0.435 | ✓ |
| **3 × 1** | **3.00** | **0.488** | **✓** |
| 3 × 2 | 3.90 | 0.590 | ✗ |
| 4 × 1 | 4.00 | 0.600 | ✗ |

⭐ **買えるのは「3 トラック × 1 構成」「2 × 2」「1 × 7」だけ。** 本フェーズは
3 × 1 を採る — **ハイパーパラメータ探索はどこにも存在しない。**

### この予算がカバーしないもの

3 つの seen span には既に 21 本の記録された仮説・約 **1,200 構成**が当たっている。
その multiplicity は実在し、本フェーズのものではなく、**本フェーズの当てはめだけを
数える予算では補正できない**。開示はするが補正はしない。それを本当に守るのは
誰も見ていないデータでの評価であり、それは今回ではない。

---

## 4. Economic condition — capacity の抜け穴を塞ぐ

capacity は `IR²` に比例するので、**高い目標 IR を宣言するだけで大きなモデルが
買える**。買わせない。目標比は**設計自身の経済から計算**する。

```
required_gross_IR = (min_annual_net_bp + turnover × roundtrip_bp) / annual_vol_bp
```

これが凍結天井 1.5 を超える設計は即座に拒否。capacity はこの **required** 比で
評価し、希望値では評価しない。`annual_vol_bp` は**宣言されたボラティリティ目標**
（設計上の選択）で、レバレッジで hurdle を越えられないよう 1000 bp で上限を置く。

### バスケット往復 3.406 bp・vol 800 bp での帯

| 頻度 | 年間コスト | 必要 gross IR | 許される有効パラメータ |
| --- | --- | --- | --- |
| monthly (12) | 40.9 bp | 0.426 | 0.424 |
| fortnightly (26) | 88.6 bp | 0.486 | 0.551 |
| weekly (52) | 177.1 bp | 0.596 | 0.831 |
| twice weekly (104) | 354.2 bp | 0.818 | 1.563 |
| **daily (252)** | **858.3 bp** | **1.448** | **4.899** |

⭐ **速く回すほど capacity は増えるが、それは「誰も見たことのない edge を要求する」
ことと引き換えでしかない。** 週次リバランスで許されるのは **1 個未満**、つまり
定数（＝手作りルール）しか載らない。日次だけが 4.9 個という使える予算を持ち、
その代償に必要 IR は天井の 1.448 になる。

---

## 5. Role 別ゲート（裁定 §28）

direction generator 用の 5 条件を機械的に全用途へ当てない。共通の 2 予算 +
economic 条件に加えて、role ごとの前提を要求する。

| role | 追加要求 |
| --- | --- |
| **direction / return generator** | target が cost-adjusted であること |
| **ranking** | 断面 ≥ 6、有効独立 ≥ 3、rank stability の測り方を宣言 |
| **trade / skip** | **base opportunity を名指し**、かつ **base expectancy を kill rule として宣言** |
| **holding-period selection** | 選択肢の horizon が 2 つ以上 |
| **regime representation** | downstream consumer と ablation を宣言し、**consumer のパラメータを合算して**課金 |
| **portfolio allocation** | 既に生き残った parent candidate が必要 |
| **execution management** | 「edge ではなくコストを測る」と宣言（return hurdle は課さない） |

共通: leakage controls の宣言が空でないこと。

## 6. 見た瞬間に拒否する形（裁定 §38）

約束ではなくコードで拒否する。

* **random split** — `TEMPORAL_ARCHITECTURES` 以外は予算計算の前に拒否。
* **20 ペアを 20 個の独立資産として扱う** — `effective_units ≥ units` は拒否
  （H-003 が 96% と測った誤り）。
* **Round 1 の形** — 高容量モデル × direction target × 生の価格特徴量。
* **閉じた family** — Gate v2 と同じ `assert_prospective` を通す。ゲートを
  乗り換えて family を再開する動きを塞ぐ。

## 7. 凍結された定数

| 定数 | 値 | 根拠 |
| --- | --- | --- |
| `MINIMUM_RELEVANT_INCREMENTAL_IR` | 0.5 | 採用に値する最小の年次 IR 改善 |
| `REQUIRED_SIGNAL_RETENTION` | 0.5 | 自分の signal の半分も残らない当てはめは選択がほぼ雑音 |
| `WITHIN_FAMILY_CONFIG_CORRELATION` | 0.70 | 同一アーキテクチャの隣接設定 |
| `MAX_PLAUSIBLE_GROSS_IR` | 1.5 | Gate v2 から import（restate しない） |
| `MIN_ANNUAL_NET_RETURN_BP` | 300 | 同上 |
| `DEFAULT_ANNUAL_VOL_BP` / cap | 800 / 1000 | 宣言されたボラティリティ目標とレバレッジ上限 |
| `HIGH_CAPACITY_PARAMETERS` | 50 | Round 1 形の認識用。許容量の 10 倍上 |

いずれも本フェーズ中に変更しない。変更は `prereg.FROZEN_HASH` を壊す。
