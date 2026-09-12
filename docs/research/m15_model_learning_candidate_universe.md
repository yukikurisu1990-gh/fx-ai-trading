# Model-Learning Candidate Universe と Development 実行 — 結果

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Status: **`MODEL_LEARNING_NOT_DECISION_GRADE_WITH_AVAILABLE_SEEN_DATA`**（裁定 §46 Case C）

成果物は `artifacts/research/model_learning/design.json` と
`artifacts/research/model_learning/development.json`。

---

## 0. 一行で

18 の model / target / architecture 方向を role 別ゲートにかけた結果、
**DEVELOPMENT_ADMISSIBLE は 0**。

* **14 ECONOMICALLY_UNREACHABLE** — 実測ボラティリティに対して自分の取引コストを
  払えない
* **3 SEARCH_BUDGET_EXCEEDED** — 3.174 年の out-of-fold は 1 回の選択も支えられない
* **1 PRIOR_FAMILY_CLOSED** — `assert_prospective` がコードで拒否

そして **3 トラックの development は既に 1 度走っており、3 本とも事前登録した合格
規則を満たさなかった。** その実行は訂正前のゲートの下で行われたので、記録であって
証拠ではない。

## 1. ⭐ レビューが決定的な欠陥を 2 方向から見つけた

2 ロール（裁定 §44 の上限）。Role 1 が BLOCKER 5、Role 2 が BLOCKER 5。
**両者が独立に同じ欠陥に到達した** — economic condition の分母。すべて再現した。

### 決定的な 1 件 — ボラティリティの分母

初稿は `annual_vol_bp = 800` を「設計上の選択」と称して**宣言**していた。
コストは **gross leg notional** の bp、ボラティリティは**レバレッジ後資本**の bp。
Role 2 が prereg の Track A baseline そのものを組んで実測: span 別 **430 / 370 /
225 bp**。私も signal-free な固定 book（アルファベット順に 4 通貨 +0.25 / 4 通貨
−0.25、gross 1.0）で **377.7 bp** を実測。

⭐ **800 までレバレッジを掛ければコストも同じ倍率で増える。レバレッジは相殺するので、
どの倍率でも天井 1.5 を越えられない。**

訂正後の hurdle は `turnover × roundtrip / vol_per_gross`（break-even）で、
日次バスケットは **2.272**、日次ペアは **1.721**。両方とも天井 1.5 超え。

### もう 1 件 — 探索予算が期待値を抑えていた

`E[max] ≤ MRIE` は誤り率ではない。3.174 年では:

| 選択の規模 | null pass 確率 | 必要年数（α=0.05） |
| --- | --- | --- |
| 1 track × 1 config | **0.1865** | **10.82** |
| 2 track × 1 config | 0.3383 | 15.28 |
| 3 track × 1 config | **0.4617** | **18.00** |

⭐ **初稿が「買える」と報告した 3×1 の shape は、null pass 確率 0.46 だった。**
訂正後は **どの shape も買えない**。

### その他の BLOCKER / required fix（抜粋）

* ⭐ **capacity がコストとともに増えていた** — Gate v1 の逆転を再導入し、
  しかも「daily は weekly より大きな予算を得る」ことをテストで**固定**していた。
  訂正後は頻度によらず一定（1.688 @ IR 1.5、0.188 @ IR 0.5）。
* ⭐ **capacity が 4.674 年を使っていた** — expanding walk-forward の第 1 fold は
  **1.5 年**。fold 加重平均は 2.846 年。
* ⭐ **`historical_oos` を "never read" と書いていた** — これは
  `HISTORICAL_EXPLORATORY_OOS_PRISTINE_CLAIM_WITHDRAWN` で撤回された主張であり、
  しかもテストが固定していた。sibling の inventory の文言をそのまま複写して訂正。
* ⭐ **凍結ハッシュが覆う範囲が主張より遥かに狭かった** — レビューが 9 つの定数を
  動かしてハッシュ不変を実演し、**span の日付を length 保存で動かすと guard が緩み
  ハッシュは動かない**ことまで示した（guard が保護対象の辞書から境界を取っていた）。
  訂正: 境界は `PROTECTED_SPANS` から取り、spec は span の実日付・PAIRS_20・実測 vol・
  天井・leakage controls・feature モジュールの SHA-256 を覆う。
* ⭐ **木の実効自由度が学習率で操作できた** — 1e-4 で 1000 本 31 葉が「3.10」に。
  葉数で下限クリップ。
* ⭐ **H-014 を development span に誤帰属**（ledger は "both deciding panels"）。
  帰属を検査するはずのテストが **id の存在しか見ていなかった**。
* **PAIRS_20 を手書きして 4 つ間違えていた**（`CAD_JPY` と `NZD_CAD` は archive に
  存在しない）。archive の tuple を import するよう修正。

## 2. ⭐ 「バーは標本ではない」

| | |
| --- | --- |
| コーパスの M15 行数（実測・20 ペア） | **2,328,316** |
| 有効独立観測数 | **3,015** |
| 1 有効観測あたりのバー数 | **772.2** |

そして**この数字は 2 つの予算のどちらにも入らない**。両方とも年で表される。

## 3. 候補表（訂正後）

| ID | role | verdict |
| --- | --- | --- |
| M01 currency cross-sectional ranking | ranking | ECONOMICALLY_UNREACHABLE |
| M02 residual factor-adjusted return | return | ECONOMICALLY_UNREACHABLE |
| M03 regime-conditioned gain, multi-timeframe | return | ECONOMICALLY_UNREACHABLE |
| M04 cross-sectional trade/skip | trade/skip | ECONOMICALLY_UNREACHABLE |
| M05 holding-period selection | horizon | ECONOMICALLY_UNREACHABLE |
| M06 volatility-scaled allocation | portfolio | ECONOMICALLY_UNREACHABLE |
| M07 event-proximity conditional return | return | SEARCH_BUDGET_EXCEEDED |
| M08 cross-asset context conditional return | return | SEARCH_BUDGET_EXCEEDED |
| M09 dispersion/correlation representation | regime | ECONOMICALLY_UNREACHABLE |
| M10 HMM per-regime mapping | regime | ECONOMICALLY_UNREACHABLE |
| M11 learned factor representation | regime | ECONOMICALLY_UNREACHABLE |
| M12 excursion-conditional exit design | execution | SEARCH_BUDGET_EXCEEDED |
| M13 hurdle-clearing probability + threshold | trade/skip | ECONOMICALLY_UNREACHABLE |
| M14 intraday session-state return | return | ECONOMICALLY_UNREACHABLE |
| M15 structural-break state | regime | ECONOMICALLY_UNREACHABLE |
| M16 activity-state opportunity gate | trade/skip | ECONOMICALLY_UNREACHABLE |
| M17 rate-differential conditional residual | return | PRIOR_FAMILY_CLOSED |
| M18 boosted-tree cross-sectional ranking | ranking | ECONOMICALLY_UNREACHABLE |

**低頻度の 3 件（M07 / M08 / M12）だけが経済条件を通り、そこで探索予算に落ちる** —
3.174 年では 1 通りも試せないため。

⭐ **M18（既定の選択肢）は経済条件で先に落ちるが、capacity でも 72 対 1.688 で
43 倍超過する。** Round 1 の ML の失敗は不運ではなく予算超過だった。

## 4. Development 実行の記録（訂正前のゲートの下）

事前登録（`FROZEN_HASH_AT_EXECUTION = 6d0809fd…`）に従い、3 トラックを各 1 構成、
1 度ずつ実行した。コーパスは **2021-04-27 … 2025-12-26、1,213 取引日**、
fold は 6（初期学習 388 日、以降 130 日ずつ）。

| track | model net IR | baseline net IR | 増分 | stressed | 合格 |
| --- | --- | --- | --- | --- | --- |
| A M01 ranking | **+0.234** | −0.983 | +1.217 | −0.085 | **✗** |
| B M03 regime gain | +0.005 | +0.005 | **0.000** | −0.938 | **✗** |
| C M13 hurdle filter | **−1.485** | −1.008 | −0.477 | −2.487 | **✗** |

**3 本とも不合格。** 落ちた条項:

* **A** — 正の fold が 4/6（要 3/4）、ストレスコストで負、**上位 10 日が net の
  3.05 倍**（残りが負）。最大ドローダウン −593 bp に対し累計 +291 bp。
  ⭐ 「baseline を +1.217 上回る」は **baseline が −0.983 だから**であって edge の
  証拠ではない。事前登録した第 1 条項の弱点であり、そう報告する。
* **B** — ⭐ **増分が厳密に 0.000**。regime gain は日ごとの正のスカラーであり、
  book は毎日 gross 1.0 に正規化されるので、**スカラーは正規化で完全に割り戻される**。
  符号が反転しない限り regime 項は何も動かさない（6 fold とも gain は正）。
  つまり **この実行は仮説を検定していない** — 設計の欠陥であって結果ではない。
  日ごとに一定の状態が効きうるのは**エクスポージャの大きさ**を通じてだけで、
  それは return generator ではなく portfolio allocation の役割である。
* **C** — base opportunity（Track A baseline を全部取る）の無条件期待値が
  **−372.9 bp/年**。事前登録した kill rule が「base が負ならフィルタは証拠にならない」
  と定めており、それが先に発火する。加えてフィルタ後の再正規化が turnover を
  49.5 → 142.5 に増やし、コストを 168 → 485 bp に押し上げた。

### ⭐ 実行が明かした 1 件（事後観察、判定には使わない）

fitted model の実測 turnover は **36.7 往復/年**であって、事前登録が capacity 予算を
買うために仮定した 252 ではない。訂正後の hurdle でその turnover を使えば
break-even は 0.331 になり経済条件は通るが、**そのとき許される有効パラメータは
IR 0.5 で 0.188 個**であり、当てはめた 4.2 個は 22 倍超過する。
**事後に再ゲートはしない**（事前登録が禁じる）。方向だけ開示する。

## 5. Seen training data inventory

| span | 期間 | 役割 | 汚染 |
| --- | --- | --- | --- |
| momentum_2021_2023 | 2021-04-26 … 2023-04-25 | deciding panel | H-007〜H-021 の 15 本 |
| supplemental_2023_2025 | 2023-04-26 … 2025-04-24 | deciding panel | H-006〜H-021 の 15 本 |
| development_2025 | 2025-04-25 … 2025-12-28 | screening のみ | 18 本、約 1,200 構成 |

3 つは連続、合計 **4.674 年**。それぞれ自分の guarded route を持ち、本パッケージは
境界を再実装せず、パスもファイル名も作らない。

⭐ **約 1,200 構成という既往の multiplicity は補正しない。** seen data 上の何をしても
補正できない。

## 6. Protected data confirmation

fresh pool `2016-06-02 … 2021-04-25`、dead window、forward epoch は **never read**。
historical OOS slice は **"one decoded row per pair; no value reached an output"** —
inventory と同じ文言で、`never read` とは書かない（撤回された主張だから）。

`assert_not_protected` は **`PROTECTED_SPANS` から**境界を取り、パース済みの `date` で
比較する。「厳密な `YYYY-MM-DD` でなければ拒否」という初稿の主張は**誇張**だった
（`date.fromisoformat` は ISO basic / week 形式も受ける）ので訂正した — 境界の意味は
保たれるが、主張がコードより広かった。

## 7. 変異テスト

**34/34 kill**（初回 28/34）。生存 6 件がそのまま 6 本のテストになった。共通する形は
**「現行データでは結論が変わらないが、機構は壊れている」**:

* 必要年数の計算から多重性の項を落とす — 1 選択では `(1−α)^(1/1)` が `1−α` に
  一致するので、M=1 だけ見るテストでは見えない。
* capacity を再び hurdle で課金する — 日次候補は全部その行に到達する前に経済条件で
  落ちるので、カタログのどの候補も通らない。
* 天井超えの achievable IR を許す — カタログは全部 0.5 なので発火しない。
* 選抜が phase の上限を無視する — 何も選ばれないのでループ本体が走らない。
* corpus が span 外の行を検査しない — 実キャッシュは正しいので発火しない。
* spec が span の実日付を覆わなくなる。

## 8. この実行が主張しないこと

`EDGE_CONFIRMED` も `PRODUCTION_READY` も使わない。到達しうる最大は
`DEVELOPMENT_MODEL_CANDIDATE` であり、**そこにも届いていない**。
fresh pool は未読のまま、自動実行もしていない。
