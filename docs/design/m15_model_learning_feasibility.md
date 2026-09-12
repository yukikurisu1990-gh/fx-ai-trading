# Model-Learning Feasibility — 二つの予算と role 別ゲート（レビュー修正後）

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Status: **`MODEL_LEARNING_NOT_DECISION_GRADE_WITH_AVAILABLE_SEEN_DATA`**

実装は `scripts/research/model_learning/`、契約テストは
`tests/research/test_model_learning_{budgets,design,development}.py`。

---

## 1. なぜ別問題なのか（裁定 §3）

4.674 年の seen history を **alpha の存在証明のために pool する**ことと、
**conditional structure の推定に使う**ことは別の feasibility 条件を持つ。
前者の条件は前フェーズの `effN ≥ (z/IR_max)²·f` で、1.996 年のパネルでは満たせない。
**その裁定は再検討しない。**

後者の条件は「p 値を出せるか」ではなく「**推定できるか**」であり、以下の 2 つに
分解される。どちらも **signal-blind**。

---

## 2. Capacity budget — 何個のパラメータを載せてよいか

年 `T` 日・1 日あたり `D_eff` 本の独立ベット、パラメータ `p` 個、目標年次 IR を
`IR` とする。

1. `IR = ρ·√(D_eff·T)` なので `R²_true = IR²/(D_eff·T)`。
2. `N_eff = D_eff·T·years` 行に `p` 個を当てはめる最小二乗の optimism は `p/N_eff`。
3. 定数より良い out-of-sample の条件は `R²_true > p/N_eff` — **`D_eff` も `T` も消える**。

> ### `p  ≤  (1 − retention) × IR_annual² × train_years`

⭐ **サンプリング頻度も断面の広さもこの予算を緩めない。**
**「1 ペアあたり 116,418 本ある」は「何個のパラメータを載せてよいか」の答えにならない。**

### レビューが直した 3 点

* ⭐ **`IR` は gross であって net ではない。** `ρ` はモデルが当てはめる forward
  return との相関であり、optimism も同じ行に課される。初稿の注記は「net」と書いて
  隣のコードと **14.9 倍**矛盾していた。net 側は economic 条件が扱う。
* ⭐ **`IR` は「必要な」比ではなく「到達しうる」比でなければならない。** 初稿は
  hurdle `(min_net + turnover×cost)/vol` を capacity に直接入れていたため、
  **コストが下がるとパラメータ予算も下がる** — Gate v2 が排除したはずの
  **Gate v1 の逆転**を再導入し、しかもテストで固定していた。
* ⭐ **`years` はコーパスではなく「最短 fold の学習年数」。** expanding
  walk-forward の第 1 fold は 1.5 年で当てはめる。4.674 年を使うのは、その fold が
  持っていない年数を使うことである。

### 4.674 年／1.5 年が許す量

| 到達すると宣言する年次 IR | 全コーパス 4.674 年 | **最短 fold 1.5 年** |
| --- | --- | --- |
| 0.50（本フェーズの宣言値） | 0.584 | **0.188** |
| 1.00 | 2.337 | 0.750 |
| 1.50（凍結された妥当性天井） | 5.258 | **1.688** |

⭐ **天井いっぱいの IR を宣言しても、最短 fold で許されるのは 1.688 個。**
実際の宣言値 0.5 では **0.188 個** — つまり係数 1 本も載らない。

## 3. Search budget — 何通り試してよいか

`Y` 年の out-of-fold で測った年次 IR の標準誤差は約 `1/√Y`。`M_eff` 個から最良を
選ぶのは `M_eff` 個の雑音推定値の最大値を取ることである。

> ### `P(best clears MRIE | all worthless) = 1 − Φ(MRIE·√Y)^M_eff  ≤  α`

⭐ **初稿は「期待値」を抑えていた。期待値は誤り率ではない。**
`E[max] ≤ MRIE` は、3 選択で **null pass 確率 0.46**、1 選択ですら **0.19** の
フェーズを許可する。

### 訂正後に必要な年数（α = 0.05、MRIE = 0.5）

| 選択の規模 | null pass（3.174 年） | 必要 out-of-fold 年数 |
| --- | --- | --- |
| 1 track × 1 config | 0.1865 | **10.82** |
| 1 track × 2 config | 0.2354 | 12.48 |
| 2 track × 1 config | 0.3383 | 15.28 |
| 3 track × 1 config | 0.4617 | **18.00** |

**利用可能なのは 3.174 年。** ⭐ **買えるのは 0 通り** — 前フェーズが別の軸で
当たったのと同じ形の壁である。

## 4. Economic condition — 両レビューが独立に見つけた欠陥

初稿:

```
required_gross_IR = (min_annual_net_bp + turnover × roundtrip_bp) / annual_vol_bp
```

3 つ間違っていた。

* ⭐ **単位が合っていない。** `roundtrip_bp` は **gross leg notional** の bp、
  `annual_vol_bp` は宣言値 800 bp の **レバレッジ後資本**。本フェーズが実際に持つ
  book（4 通貨ロング・4 通貨ショート、gross 1、最適化なし）の実測年次ボラティリティは
  **377.7 bp**（span 別 370〜430）。比は約 **2.1 倍**設計を有利に見せていた。
  800 までレバレッジを掛ければコストも同じ倍率で増えるので、**レバレッジでは救えない。**
* ⭐ **capacity がコストとともに増えていた**（Gate v1 の逆転）。
* ⭐ **300 bp の最低純収益は「比」の話ではない。** 与えられた IR のもとでは
  **レバレッジ**の話であり、そう報告する。

### 訂正後

```
break_even_annual_ir = turnover × roundtrip_bp / vol_per_gross      （レバレッジは相殺）
capacity は「到達すると宣言した IR」×「最短 fold の年数」で課金（コストに依存しない）
```

### バスケット往復 3.406 bp・実測 vol 377.7 bp

| 頻度 | 年間コスト | **break-even gross IR** | 到達可能 | 許されるパラメータ |
| --- | --- | --- | --- | --- |
| monthly (12) | 40.9 bp | 0.108 | ✓ | 1.688 |
| fortnightly (26) | 88.6 bp | 0.234 | ✓ | 1.688 |
| weekly (52) | 177.1 bp | 0.469 | ✓ | 1.688 |
| twice weekly (104) | 354.2 bp | 0.938 | ✓ | 1.688 |
| **daily (252)** | **858.3 bp** | **2.272** | **✗** | **0** |

ペア単位（往復 2.58 bp）の daily も **1.721** で天井超え。

⭐ **日次リバランスは、1 bp も稼ぐ前に gross 年次 IR 2.27 を要求する。**
そして許されるパラメータ数は頻度によらず一定になった — **安くすることが不利に
ならない**、という Gate v2 の性質がようやく満たされている。

## 5. Role 別ゲート（裁定 §28）

| role | 追加要求 |
| --- | --- |
| **direction / return generator** | target が cost-adjusted であること |
| **ranking** | 断面 ≥ 6、有効独立 ≥ 3、rank stability の測り方を宣言 |
| **trade / skip** | **base opportunity を名指し**、かつ **base expectancy を kill rule として宣言** |
| **holding-period selection** | 選択肢の horizon が 2 つ以上 |
| **regime representation** | downstream consumer と ablation を宣言し、**consumer のパラメータを合算して**課金 |
| **portfolio allocation** | 既に生き残った parent candidate が必要 |
| **execution management** | 「edge ではなくコストを測る」と宣言 |

共通: leakage controls の宣言が空でないこと、宣言する achievable IR が
`(0, 1.5]` にあること。

## 6. 見た瞬間に拒否する形（裁定 §38）

random split / 20 ペアを独立 20 資産として扱う / Round 1 の形（高容量 × direction ×
生の価格特徴量）/ 閉じた family（Gate v2 と同じ `assert_prospective`）。

木のアンサンブルの実効自由度は `trees × leaves × rate` を **葉数で下限クリップ**する。
レビューが学習率 1e-4 で 1000 本 31 葉を「3.10 パラメータ」に落として見せたため
（本フェーズの headline を反証する挙動だった）。

## 7. 凍結された定数

| 定数 | 値 |
| --- | --- |
| `MINIMUM_RELEVANT_INCREMENTAL_IR` | 0.5 |
| `REQUIRED_SIGNAL_RETENTION` | 0.5 |
| `WITHIN_FAMILY_CONFIG_CORRELATION` | 0.70 |
| `ALPHA` | 0.05（Gate v2 から import） |
| `MAX_PLAUSIBLE_GROSS_IR` | 1.5（同上） |
| `MIN_ANNUAL_NET_RETURN_BP` | 300（同上、レバレッジ条件として使用） |
| `MEASURED_ANNUAL_VOL_PER_GROSS_BP` | **377.7（実測）** |
| `HIGH_CAPACITY_PARAMETERS` | 50 |

これらのうち **span の実日付・PAIRS_20・実測 vol・天井・leakage controls・
feature モジュールの SHA-256** は `prereg.specification()` に入り、凍結ハッシュが
覆う。初稿では 7 定数中 5 つがハッシュの外にあり、レビューが 9 つの定数を動かして
ハッシュが変わらないことを実演した。
