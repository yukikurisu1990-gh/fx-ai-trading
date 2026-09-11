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

**データは通った。設計が通らなかった。** Stage 0 は合格（補正後の日付一致
**103/103**、precision = recall = 1.0）。Stage 1 では 3 つの primary cell のうち
**1 つだけが decision-grade** で、それは検出力のある null（net −10.55 / −7.55 bp、
p 0.672 / 0.859）。残り 2 つは検出力不足。そして **3 つとも Gate v2 の economic
gate を落とす**——これは signal を見なくても決まる設計上の判定である。

---

## 1. Stage 0 — Data Integrity

### 1.1 Provenance（P1）

無料アーカイブ `Ehsanrs2/Forex_Factory_Calendar`。SHA256 先頭 `f4e92bca4168cfe6`、
**83,427 行**（既知値と一致）、2 パネル期間内 **18,882 行**。鍵なし・課金なし。

### 1.2 Currency mapping（P2）

全コード既知（`AUD / CAD / CHF / EUR / GBP / JPY / NZD / USD` に加え、宇宙外として
既知の `CNY` / `All`）。未知コード **0**。期間内の行数は EUR 4,000 / GBP 2,566 /
JPY 1,689 / AUD 1,369 / CAD 1,365 / NZD 951 / CHF 665（USD 5,087）。

### 1.3 ⭐ Date fidelity（P3）— アーカイブの日付は 1 日早い

公式の ECB / BoJ / RBA 発表日と突き合わせた結果。

| 通貨 | 系列 | 補正前 | 補正後 | 行数 | 公式日数 |
| --- | --- | --- | --- | --- | --- |
| EUR | Main Refinancing Rate | 0.8387 | **1.0** | 31 | 31 |
| JPY | BOJ Policy Rate | 0.1562 | **1.0** | 32 | 32 |
| AUD | Cash Rate | 0.85 | **1.0** | 40 | 40 |
| **pooled** | | | **1.0** | **103** | **103** |

precision も recall も 1.0。**余計な日付も欠けた日付もない。** 補正前に BoJ が
0.156 と最悪なのは、東京午前の発表が日付境界をほぼ毎回跨ぐからで、欠陥が実在する
ことの直接の証拠になっている。

### 1.4 ⭐ 同定できたのは「時刻」ではなく「日」（P4）

オフセット探索は **5 時間から 24 時間まで一律 0.94** で平坦、
`separated_from_runner_up` は **false**。つまりグリッドはこの範囲を区別できない。
データが支持する量は「アーカイブの日付が 1 暦日早い」であって、時刻ではない。
訓練は USD CPI 51 vintage（ALFRED）で行い、検証は非 USD で行った。

**したがって時刻は使わない。** Stage 1 が 1 日 horizon に限られ、entry が発表日の
**翌取引日**なのはこの理由による。

### 1.5 Forecast の事前性（P5、反証のみ）

`Forecast == Actual` の完全一致率 **14.28%**（上限 25%）。**208 系列のうち 83.65%**
が naive benchmark（`Previous`）を上回り、誤差比の中央値は **0.7277**。
forecast が事後に書かれたという反証は得られなかった。**証明ではない**——値の並び
だけから事前性を証明することはできない。

### 1.6 Revision backfill（P6、限界）

系列内で `Previous` が直前行の `Actual` と一致するのは **52.15%**（9,408 組）。
これは (a) 改訂が日常的である、(b) アーカイブが改訂値を back-fill している、の
**どちらとも整合し、区別できない**。これらの統計機関に vintage archive が無いので、
ALFRED でできる first-release 検証は非 USD では実行できない。**限界として記録する。**

### 1.7 Stage 0 verdict

事前登録の 3 条件すべてを満たし **合格**。手修正・補完は行っていない。

## 2. Stage 1 — Forward 1-day relative response

admissible events **483**（high-impact・非 USD・3 family・surprise ≠ 0）。

### 2.1 測定

| cell | N | effective N | events/yr | gross bp | cost bp | net bp | dispersion bp | MDE bp | p | breadth | concentration | 1 ペア往復 bp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| employment · momentum | 97 | 83.18 | 48.6 | -1.0117 | 9.5385 | -10.5502 | 22.7865 | 7.0007 | 0.6722 | 1/4 | 0.3203 | 7.3936 |
| employment · supplemental | 107 | 87.74 | 53.61 | 0.3627 | 7.9168 | -7.5542 | 22.0156 | 6.5857 | 0.8586 | 1/4 | 0.3577 | 6.1322 |
| inflation · momentum | 76 | 58.9 | 38.08 | -0.9342 | 6.641 | -7.5752 | 33.9126 | 12.3815 | 0.8181 | 1/6 | 0.3281 | 5.1463 |
| inflation · supplemental | 129 | 106.89 | 64.63 | 4.2533 | 5.0016 | -0.7483 | 28.655 | 7.7662 | 0.0915 | 3/7 | 0.2442 | 3.831 |
| policy_rate · momentum | 11 | 7.06 | 5.51 | -25.2433 | 9.306 | -34.5493 | 57.2167 | 60.3448 | 0.1714 | 1/6 | 0.9918 | 7.2227 |
| policy_rate · supplemental | 12 | 11.6 | 6.01 | -3.021 | 5.3787 | -8.3997 | 35.0894 | 28.8679 | 0.7346 | 2/6 | 0.9661 | 4.1188 |

### 2.2 ⭐ コストが支配している、そしてその理由は構成にある

`cost_bp` は **5.00〜9.54 bp**。内訳は「gross exposure ≈ 1.29 × 1 ペアあたり往復
3.83〜7.39 bp」。2 つの要因が重なっている。

1. **通貨を basket に対して持つと 20 ペアで実装される**ので、建てる notional は
   1 単位では済まない（unit audit が測った構成項）。共通ファクターを消すための
   構成が、そのままコストを増やしている。
2. **entry が UTC 日の最初のバー**なので、アジア early の薄い時間帯のスプレッドを
   払う。全バー中央値 2.5〜2.7 bp に対し **3.83〜7.39 bp**、最大 3 倍近い。

2 は「発表当日を触らない」という安全側の選択の代償であり、事前登録どおりである。
結果を見てから entry 時刻を動かすことはしない。

### 2.3 Feasibility Gate v2（prospective 適用）

| cell | MDE bp | MRE bp | statistical | net bp | stressed net bp | implied gross annual IR | economic |
| --- | --- | --- | --- | --- | --- | --- | --- |
| employment · momentum | 7.0006 | 8.6728 | **pass** | -0.0548 | -8.7825 | 2.6534 | fail |
| employment · supplemental | 6.5857 | 8.096 | **pass** | -0.6317 | -9.3593 | 2.6925 | fail |
| inflation · momentum | 12.3815 | 10.3782 | fail | 4.5569 | -1.2644 | 1.8885 | fail |
| inflation · supplemental | 7.766 | 7.1418 | fail | 1.3205 | -4.5008 | 2.0037 | fail |
| policy_rate · momentum | 60.3377 | 56.9465 | fail | 49.6041 | 42.2618 | 2.3363 | fail |
| policy_rate · supplemental | 28.8679 | 52.4168 | **pass** | 45.0745 | 37.7321 | 3.6621 | fail |

* **statistical**: employment のみ両パネル合格。inflation は両パネルで僅差の不合格
  （12.38 対 10.38、7.77 対 7.14）。policy_rate は片パネルのみ。
* **robustness**: policy_rate は **N = 11 / 12** で 60-event floor に遠く及ばない。
* **economic**: **6 セルすべて fail**。落としているのは 2 条件で、
  (a) stressed net（コスト ×2）が負、(b) implied gross annual IR が 1.89〜3.66 で
  上限 1.5 を超える。

⭐ **economic gate の判定は signal に依存しない。** MRE・dispersion・events/yr・cost
だけで決まる。つまり **仮にシグナルが強くても、この設計は取引に値しない**という
設計上の結論であり、Stage 1 の測定値とは独立に成立している。

### 2.4 家族ごとの判定

| family | decision-grade | supported | net（2 パネル） | p（2 パネル） |
| --- | --- | --- | --- | --- |
| employment | **yes** | no | −10.55 / −7.55 | 0.672 / 0.859 |
| inflation | no | no | −7.58 / −0.75 | 0.818 / 0.092 |
| policy_rate | no | no | −34.55 / −8.40 | 0.171 / 0.735 |

* **employment は検出力のある null。** MDE 7.00 / 6.59 が MRE 8.67 / 8.10 を下回り、
  実測 gross は −1.01 / +0.36 bp、p は 0.672 / 0.859、通貨 breadth は 1/4 と 1/4。
* **符号は 2 パネルで一致**しているが、一致しているのは **負の符号**であり、
  仮説が予測した方向ではない。事前登録どおり **反転はしない**。
* policy_rate は concentration 0.99 / 0.97 — net の 9 割以上が上位 10 事象、
  実質 1〜2 事象。N から見て当然で、判定に使わない。

## 3. 裁定

**`NON_USD_SURPRISE_DATA_NOT_DECISION_GRADE_SKIP`**（事前登録 §13 の C）。

事前登録の C は「data integrity **か power** が足りず未検定」と定義してある。
本件で足りなかったのは **power** であって data ではない——Stage 0 は合格している。
3 cell のうち 2 cell が statistical / robustness を通らないので、登録した family
として判定できていない。

**`NON_USD_SURPRISE_RELATIVE_CLOSED` は主張しない。** employment 単独は
decision-grade な null だが、family として閉じるには 3 cell が判定可能である必要が
あり、それは満たされていない。

## 4. Limitations

* **非 USD に vintage archive が無い。** actual が first release であることを
  ALFRED 相当の方法で証明できない（§1.6）。revision 整合 52.15% はどちらとも取れる。
* **日付検証は 3 中央銀行の政策決定 103 件のみ。** inflation / employment の各統計
  機関には無料の機械可読な公式リリース calendar が無く、BoE / BoC / RBNZ / SNB は
  自動取得経路をすべて拒否する（`exogenous.calendars` の既知の被覆限界）。
  1 日のずれという補正は東京午前から欧州午後まで幅のある発表時刻で検証されているが、
  **他 family への外挿は検証ではない。**
* **発表当日を測っていない。** 時刻が使えない以上これは必然だが、announcement
  効果が最も宿りやすい時間帯を捨てている。null は「翌日には無い」であって
  「当日にも無い」ではない。
* **entry 時刻のコスト。** §2.2 のとおり UTC 日初バーは高い。
* **seen data のみ。** fresh pool / OOS / dead window / forward epoch は未読。

## 5. 進めていないもの

Track 1 は `CLOCK_STRUCTURE_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER` の
まま凍結（Gate v2 は `assert_prospective` が機械的に拒否する）。G6 / intraday 昇格
は Stage 1 で base edge が成立した場合のみで、成立していないので進まない。ML は
未使用。regime / HTF は使っていない。有料データなし、broker 接続なし。
