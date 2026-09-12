# Track 2 — Non-USD Macro Surprise → Currency-Level Relative Response: 結果

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Status: **`NON_USD_SURPRISE_DATA_NOT_DECISION_GRADE_SKIP`**

事前登録は `docs/research/m15_track_2_non_usd_surprise_prereg.md`（`8c4e171` で凍結、
signal / return を見る前）。Feasibility Gate v2 は `d2d35db` で先に凍結済みで、
本 Track はその**最初の prospective 適用**である。成果物は
`artifacts/research/track2/stage0.json` と同 `stage1.json`。

---

## 0. 一行で

**どの family も decision-grade に達しなかった。** 3 つの primary cell はいずれも
Gate v2 の statistical gate を通らず（MDE 8.47〜65.33 対 MRE 5.48〜56.95）、
p 値は 0.166〜0.804 で null と区別できない。符号は機構の予測と逆側で、
`employment` は 2 パネルで符号すら一致しない。

Stage 0 は合格した（補正後の日付一致 **103/103**）。**足りなかったのは power で
あって data ではない**——ただし後述 §4 のとおり、data 側にも解消できない限界がある。

そして **Gate v2 の合成判定は 3.489 年の有効観測を要求する**のに対し決定パネルは
1.996 年しかない。だから economic gate が全セルで落ちたのは、**この設計について
の所見ではなくパネル長についての所見**である。

---

## 1. ⭐ 初稿は無効だった — レビューが 3 つの BLOCKER を出した

本文書は 2 稿目である。初稿の Stage 1 の数値は**すべて無効**で、2 つの独立した
レビューロールが同じ 2 点を別々に発見した。私は自分で再現して確認した。

| # | 初稿の誤り | 影響 |
| --- | --- | --- |
| B1 | Stage 1 が **+1 暦日**の補正を使っていた。Stage 0 が推定・検証したのは **+5 時間**である。Stage 0 自身の採点器に +1 日を通すと **0.3689** で、事前登録の 0.95 床を割る（無補正の 0.6311 より悪い） | 全数値が無効 |
| B2 | **日曜の再開セッション（12 バー、約 3 時間）を取引日として数えていた**。employment の 68% / 61% がそこに入っていた。`clock_flow` の `MIN_BARS_FOR_A_TRADING_DAY = 48` を再利用していなかった | コストが 2〜3 倍に膨れ、horizon が 1 日ではなくなっていた |
| B3 | Gate v2 の合成判定が **`effN ≥ 3.489 × events/yr`** を要求する（= 3.489 年）ことを書いていなかった。パネルは 1.996 年 | economic gate の結論が設計の所見として読めてしまう |

さらに required fix として、admission に archive の impact ラベルを使っていた
（事前登録は diagnostic と規定）、success 規則が**符号の向きを要求していなかった**、
breadth を net の正負で数えていた、2 パネルのコストを平均して両方を裁定していた、
成果物を unit 監査に通していなかった、drop 件数を報告していなかった——を修正した。

**B1 の前提自体が誤っていた。** 無補正でも 103 行中 65 行は既に正しい日付を持つ。
欠陥は「日付が 1 日早い」ではなく**夕方 UTC の行に限られた時刻の欠陥**である。

## 2. Stage 0 — Data Integrity

### 2.1 Provenance と currency mapping

SHA256 先頭 `f4e92bca4168cfe6`、**83,427 行**（既知値と一致）、2 パネル期間内
**18,882 行**。未知の通貨コード **0**。鍵なし・課金なし。

### 2.2 Date fidelity — 公式 ECB / BoJ / RBA との照合

| 通貨 | 補正前 | 補正後（+5h） | 行数 | 公式日数 |
| --- | --- | --- | --- | --- |
| EUR | 0.8387 | **1.0** | 31 | 31 |
| JPY | 0.1562 | **1.0** | 32 | 32 |
| AUD | 0.85 | **1.0** | 40 | 40 |
| pooled | | **1.0** | **103** | **103** |

precision も recall も 1.0。BoJ が補正前に最悪なのは、東京午前の発表が日付境界を
跨ぐからで、欠陥が時刻由来であることの直接の証拠になる。

⭐ **同定できたのは「≥5 時間」であって特定の時刻ではない。** オフセット profile は
5〜24 時間で一律 **0.94** の平坦、`separated_from_runner_up` は false。訓練は
USD CPI **51** vintage（ALFRED）、検証は非 USD で分離してある。
**この不定区間の中で採点が大きく変わる**——5 時間なら 1.0、24 時間なら 0.3689。
argmax の同点処理が結果を決めているので、**この源の時刻は使えない**。Stage 1 が
1 日 horizon に限られ、entry が発表日の翌取引日なのはこの理由による。

### 2.3 Forecast の事前性（反証のみ）

事前登録した母集団（全非 USD 行）で完全一致率 **0.1428**（上限 0.25）、
**208 系列の 83.65%** が naive benchmark を上回り誤差比中央値 **0.7277**。合格。

⚠ **ただし Stage 1 が実際に使う母集団では 0.3621 で上限を超える**（1,798 行）。
事前登録の判定は登録どおり全非 USD 行で行い verdict は変えないが、**研究が触る行
に限ると事前性の反証が通らない**ことは記録する。政策金利は予想どおり出ることが
多く、それらは zero-surprise として落ちるので機械的には説明がつくが、説明がつく
ことと反証されないことは別である。

### 2.4 Revision backfill（限界）

系列内で `Previous` が直前行の `Actual` と一致するのは **0.5215**（9,408 組）。
「改訂が日常的」とも「back-fill」とも整合し**区別できない**。非 USD に vintage
archive が無いので ALFRED 相当の first-release 検証は実行できない。

## 3. Stage 1 — Forward 1-day relative response

補正は **Stage 0 の成果物から読む**（2 つの定数が食い違った初稿の反省）。
部分セッション（<48 バー）を除外した結果、パネルごとに **103 / 106 日**が
取引日から外れた。admissible は非 USD 12,605 行 → family 一致 1,895 →
actual/forecast 欠損 −97、zero surprise −651 → **1,147**。

### 3.1 測定と Gate v2

| cell | N | effN | events/yr | gross bp | cost bp | net bp | dispersion bp | MDE bp | MRE bp | statistical | p (gross) | breadth | concentration | 1 ペア往復 bp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| employment · momentum | 137 | 117.23 | 68.64 | -5.051 | 4.7684 | -9.8193 | 41.6565 | 10.7802 | 6.8706 | fail | 0.1659 | 5/7 | 0.2294 | 3.5897 |
| employment · supplemental | 120 | 90.0 | 60.12 | 2.3412 | 4.1971 | -1.8559 | 44.6251 | 13.1803 | 7.49 | fail | 0.5717 | 5/7 | 0.3135 | 3.1645 |
| inflation · momentum | 201 | 161.09 | 100.71 | -3.5896 | 3.9868 | -7.5764 | 43.0624 | 9.5068 | 5.4789 | fail | 0.2389 | 4/7 | 0.159 | 2.9953 |
| inflation · supplemental | 195 | 150.15 | 97.7 | -2.7594 | 3.3022 | -6.0616 | 37.0327 | 8.4682 | 5.5706 | fail | 0.2984 | 5/7 | 0.1672 | 2.4724 |
| policy_rate · momentum | 11 | 7.7 | 5.51 | -8.7414 | 5.3151 | -14.0565 | 64.6978 | 65.3299 | 56.9465 | fail | 0.6632 | 4/6 | 0.9951 | 4.1252 |
| policy_rate · supplemental | 12 | 7.86 | 6.01 | -3.2414 | 4.7852 | -8.0266 | 45.8089 | 45.7832 | 52.4168 | pass | 0.8041 | 4/6 | 0.9693 | 3.6643 |

* **statistical gate は 6 セル中 5 セルで fail。** 通ったのは policy_rate の片方
  だけで、そこは N = 12 なので robustness で落ちる。
* **p 値は 0.166〜0.804。** 何も出ていない。
* **符号は機構の予測と逆。** `sign_is_the_hypothesised_one` は 3 family とも false。
  employment は 2 パネルで符号すら一致しない（−5.05 / +2.34）。事前登録どおり
  family は**落とす**。反転はしない。
* policy_rate は concentration 0.995 / 0.969 — net のほぼ全部が上位 10 事象、
  実質 1〜2 事象。N から見て当然で、判定には使わない。

### 3.2 コスト — 日曜を外したら参照値に戻った

1 ペア往復は **2.47〜4.13 bp**。初稿は 3.83〜7.39 bp と報告していたが、その超過分は
**日曜セッションの薄いスプレッド**だった。往復コスト 3.30〜5.32 bp の内訳は
gross exposure 約 1.29 × 1 ペア往復で、**通貨を basket に対して持つと 20 ペアで
実装される**という構成項は残る（ドル要因を消す構成がそのまま turnover を増やす）。

### 3.3 ⭐ economic gate が全セルで落ちた理由はパネル長である

statistical は `2.802·σ/√effN ≤ MRE`、economic の plausibility は
`MRE·√f/σ ≤ 1.5`。両立には

    effN ≥ (2.802 / 1.5)² · f = 3.489 · f

すなわち **3.489 年**の有効観測が要る。決定パネルは **1.996 年**、本 Track の 6 セルの
`effN/f` は **1.28〜1.93**。**このパネル上ではどの設計も合成判定を通らない。**

したがって「economic gate が落ちた」を「この設計は取引に値しない」と読んではなら
ない。読むべきは「**2 年のパネルでは年次 IR を 1.5 以下と主張しつつ 80% の検出力を
持つ設計は存在しえない**」であり、これは Gate v2 の誤りではなく、正しい gate が
このプログラムのデータ地平を測ってしまったという所見である。
Gate v2 設計文書 §13 に導出を追記した（**式も定数も変更していない**）。

**帰結**: 事前登録 §13 の Success 条項は economic gate を要求するので、**凍結時点で
発火不能だった**。事前登録側の欠陥として記録する。

## 4. 裁定

**`NON_USD_SURPRISE_DATA_NOT_DECISION_GRADE_SKIP`**（事前登録 §13 の C）。

C は「data integrity **か power** が足りず未検定」と定義してある。3 cell とも
statistical gate を通らないので、登録した family として判定できていない。

**`NON_USD_SURPRISE_RELATIVE_CLOSED` は主張しない。** 検出力のある null が 1 つも
無いので、family を閉じる根拠がない。

## 5. Limitations

* **非 USD に vintage archive が無い**（§2.4）。actual が first release である
  ことを証明できない。
* **Stage 1 が使う母集団では forecast の事前性反証が通らない**（0.3621、§2.3）。
* **日付検証は 3 中央銀行の政策決定 103 件のみ。** inflation / employment の統計
  機関には無料の機械可読な公式 calendar が無く、BoE / BoC / RBNZ / SNB は自動取得
  経路をすべて拒否する。**他 family への外挿は検証ではない。**
* **発表当日を測っていない。** 時刻が使えない以上必然だが、announcement 効果が
  最も宿りやすい時間帯を捨てている。null は「翌日には無い」であって「当日にも
  無い」ではない。
* **合成判定はこのパネル長では発火しえない**（§3.3）。
* **entry コストは entry バーの終値スプレッドを使う**（`fxunits` の既存規約）。
  始値での約定に対する 15 分の前方参照で、コスト側にのみ効く。
* **seen data のみ。** fresh pool / OOS / dead window / forward epoch は未読。

## 6. 進めていないもの

Track 1 は `CLOCK_STRUCTURE_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER` の
まま凍結（Gate v2 の `assert_prospective` が機械的に拒否する）。G6 / intraday 昇格
は base edge が成立した場合のみで、成立していない。ML は未使用。regime / HTF は
使っていない。有料データなし、broker 接続なし。
