# Top-Five 最終統合報告（2026-09-21）

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Authority: 2026-09-21 Human + ChatGPT 裁定 §53 / §54

> **結論を 1 行で。**
> 5 本のうち net が正だったのは T5 の 1 本だけで、**その +0.838 は、
> その窓の 95% 検出下限 1.32 を下回っている**。
> すなわち本 cycle は「どの情報源に edge があるか」を決着させていない。
> **決着しなかったこと自体が、この窓では決着できないという測定結果である。**

---

## 1. Identity

| | |
| --- | --- |
| PR | **#490**（branch `research/m15-top-five-freeze`） |
| 実行時 freeze digest | `28100ebedfea45765371585df5c4308fee261e2496a9798acca79c920158962c` |
| 現在の freeze digest | `8279f6b55112ff953cd9bf01b584447bc53b9db5b6745dd1cc9cd8d1501f3a3f` |
| 旧 freeze（履歴保持） | `29ba80d68a5462fe015a6f2566d3c0b63319d0549de7b9a4d34a890f2339b1ca` — `SUPERSEDED_PRE_EXECUTION` |
| merge SHA | **無し（未 merge）** — 下の「なぜ自動 merge しなかったか」を読むこと |
| CI | `413b1dd` で **green**（test 10m55s / contract-tests 57s）。本文書の追記コミットは次の head |
| mutation | **検証 23 件すべて検出**（当初 20 件中 17 件 → 中核契約 3 件を塞いで再検証） |
| 主な artefact | `artifacts/research/top_five/{acquisition,development,stage2_t5}.json` |

### なぜ #490 を自動 merge しなかったか — **裁定手順からの逸脱の申告**

裁定 §44 は「#490 = freeze の完成」を想定し、その内容が green なら追加 Human 確認なしで
merge してよいとしている。§45 は **merge 後に**取得と実行へ進めとしている。

**私はその順序を守らなかった。** 取得も実行も #490 と同じ branch で行ったので、
#490 は現在 freeze / acquisition / execution の 3 つを 1 本に含んでいる。

その結果、§44 の merge 許可が与えられた範囲より PR の中身が広い。
§51 は execution / result PR を **Amber / Human + ChatGPT merge approval 待ち**と定めている。
repository 規約（「tier をまたぐなら高い方が全体を支配する」「研究制限は厳しい読みを採る」）
と合わせると、**#490 は execution-evidence PR として扱うのが正しい**。

→ **#490 は merge せず、Human + ChatGPT の merge approval を待つ。**
これは cycle 途中の確認要求ではなく、裁定 §51 が定めた終端状態である。

---

## 2. Freeze Corrections

**「5 本を凍結して 1 度走らせた」だけではない。** 結果を見た後に 3 件の訂正が入っている。
記録は `prereg.POST_EXECUTION_CORRECTIONS`
（status `CORRECTED_AFTER_RESULTS_WERE_SEEN_NOT_A_CLEAN_PREREGISTERED_RUN`）。

| | 種類 | 内容 | 裁量 |
| --- | --- | --- | --- |
| **C-1** | leakage 閉塞 | `signals._two_year` が取得層を迂回して parquet を直読みし、保護 pool と forward epoch の行（通貨により 510–2,092 行、最大 2026-09-15）が slope 計算へ入っていた。近 span の score **3 日**（2021-05-11 / 2021-05-26 / 2021-05-27）が保護 pool の値に依存 | **無し** |
| **C-2** | 単位バグ + **新しい定数** | staleness 上限を行数で数え、union index の空白を **1 行で 1,792 日**跨いでいた。暦日へ修正。ただし **75 日は新しく選んだ値** | **有り** |
| **C-3** | 欠けていた null | `constant_long_usd` を benchmark へ追加 | 正の結果を弱める方向のみ |

**C-1 と C-2 は実行前に閉じているべきだった。** 5 本を凍結してから走らせる設計の目的は、
まさにこの種の事後調整を不可能にすることだった。
初稿は「fresh pool 未読」と書いていたが、**C-1 の leg についてそれは偽だった**。

**C-2 の裁量が結果に効く大きさ**は §7 の感度表が示す — 凍結値 75 は試した 9 点で
net Sharpe **第 1 位**であり、報告値は楽観側の端である。

→ 次の cycle への持ち越し: **外部 series を読む経路を 1 本に強制し、
そこを通らない読み出しを test で禁じる。**

---

## 3. xlrd Dependency

research 用途に限定して追加。version 固定。`.xls` は **data parsing のみ**に使い、
embedded macro の類は一切実行しない。production dependency へは波及させていない。
取得した file の sha256 は `acquisition.json` に記録済み。

---

## 4. Data Acquisition Record

8 source、すべて public / free、**すべて HTTP 200**。保護 span は **request 自体から除外**
（download-then-filter は行っていない）。範囲判定は**パース済みの日付**で行い、文字列比較はしない。

| source | provider | coverage | 行 | 頻度 | 公表時刻と適用 lag |
| --- | --- | --- | ---: | --- | --- |
| `vix` | CBOE | 1999-01-04 … 2025-12-26 | 5,582 | daily | close 22:15 CET（長 2 営業日 / 近 1 営業日） |
| `wti` | U.S. EIA | 1999-01-04 … 2025-12-26 | 5,076 | daily 観測 / 水曜公表 | 1–7 暦日遅れ（両 span 7 営業日） |
| `ust_10y` | U.S. Treasury | 1999-01-04 … 2025-12-26 | 5,525 | daily | 21:30–24:00 CET（2 営業日） |
| `bund_10y` | Deutsche Bundesbank | 1999-01-04 … 2025-12-23 | 5,618 | daily | 夕刻（2 営業日） |
| `boe_10y` | Bank of England | 1999-01-04 … 2025-12-24 | 5,578 | daily | 夕刻（2 営業日） |
| `boc_10y` | Bank of Canada | 2001-01-02 … 2025-12-24 | 5,024 | daily | 22:30 CET（2 営業日） |
| `snb_10y` | Swiss National Bank | 1999-01-04 … 2025-07-31 | 5,442 | daily | 同等以降（2 営業日） |
| `tic_s1` | U.S. Treasury (TIC) | 1998-11 … 2023-01 | 233 | monthly | 第 m 月の値は m+2 月中旬公表。**使用は m+2 月末以降** |

provider / URL / request parameters / 取得時刻 / HTTP status / content hash / coverage /
頻度 / 公表タイミングはすべて `acquisition.json` に記録されている。

**取得中に見つけて直した parser の誤り 3 件**（いずれも沈黙する種類のもの）:

1. `vix` が全 NaN — `pd.DataFrame({"vix": series}, index=datetime_index)` が RangeIndex の
   Series を DatetimeIndex へ再 index して全消ししていた。**「全部が保護されていた」ように見えた。**
2. `bund_10y` が全 NaN — 最終列は値ではなく flag 列（`No value available`）だった。
3. `tic_s1` が全 0.0 — `"2,012,796"` という文字列で、`header=None` のとき `thousands=","` が効かない。
   標準偏差 0 なら落ちる guard を入れた。

---

## 5. Protected Data Status

| 対象 | 状態 |
| --- | --- |
| fresh pool `2016-06-02 … 2021-04-25` | **未読**（C-1 修正後） |
| historical OOS | **未読** |
| dead window | **未読** |
| forward Formal Confirmation epoch | **未読**（C-1 修正後） |

**C-1 の修正前は 1 行目と 4 行目が偽だった。** 新たな read を行ったのではなく、
**既に取得済みの file を切り落とさずに使っていた**という性質の事故である。
現在は `sources.is_seen` を通し、`assert_no_protected_day` で二重に押さえている。

近 span の FX panel は既存の guarded cache 3 本が連続被覆しており、
**M15 archive の新規読み取りはゼロ**。
broker は public margin 仕様のみ。authenticated API / demo / paper / live には触れていない。
paid data は購入していない。

---

## 6. Top-Five Final Prereg & Results

**共通の留保:** panel は両 span とも spot only で **carry leg を持たない**
（`CARRY_LEG_ABSENT_ON_BOTH_SPANS_SPOT_ONLY`）。凍結時の開示は長 span と T3 / T5 だけを
名指ししていたので、実物より狭かった。効きは T1 と T3 が最も強い。

**共通の検出力:** 年率 Sharpe の標準誤差は概ね `1/√年数` なので、
その窓で 95% 有意に検出できる最小の |Sharpe| は `MDE95 ≈ 1.96/√年数` である。

### T1 · S05 — 株式 volatility → G10 FX

| 項目 | 長 span | 近 span |
| --- | ---: | ---: |
| mechanism | risk repricing が資金調達通貨（JPY / CHF）へ波及する | 同 |
| data / timing | VIX close 22:15 CET、lag 2 営業日 | lag 1 営業日 |
| fixed rule | z-score 化した VIX shock を凍結 beta（JPY/CHF 正、AUD/NZD 負）へ射影 | 同 |
| 日数 / 年 | 4,321 / 17.15 | 1,211 / 4.81 |
| **MDE95** | **0.473** | **0.894** |
| gross SR | +0.139 | +0.336 |
| **net SR** | **−0.435** | **−0.500** |
| incremental IC | +0.0131 | +0.0066 |
| turnover（単位 gross） | 54.2 | 52.4（凍結 82.5 内） |
| 年 cost | 6.52% | 9.67% |
| 正の block | 29/68 | 9/19 |
| breadth（LOO 最悪） | −0.60 | −0.77 |
| tail | 解釈不能（net 負） | 同 |
| maxDD | −0.924 | −0.584 |
| leverage / margin | 3.53x / 17.6% | 5.42x / 27.1% |
| 年 5% / 年 10% capacity | **到達不能** | **到達不能** |
| verdict | `T1_S05_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` — `COST_FAILURE` | |

gross は両 span で正、incremental IC も正。turnover は凍結範囲内なので
**費用は想定どおり**であり、gross（+0.34）が想定 drag（約 0.77 Sharpe 単位）に届かない。
**「情報は確かにある」とまでは書かない** — incremental IC +0.0066 は日次 cross-section 相関の
平均が 0.7% ということで、**別個に有意だとは検定していない**。

### T2 · S06 — 原油交易条件 → 商品通貨

| 項目 | 長 span | 近 span |
| --- | ---: | ---: |
| data / timing | WTI 水曜公表、lag 7 営業日 | 同 |
| 日数 / 年 | 4,233 / 16.80 | 1,205 / 4.78 |
| **MDE95** | **0.478** | **0.896** |
| gross SR | −0.354 | +0.519 |
| **net SR** | **−0.786** | **−0.253** |
| incremental IC（価格超） | −0.0027 | +0.0047 |
| **incremental IC（T1 超）** | **−0.0115** | **−0.0019** |
| turnover（単位 gross） | 42.3 | 50.4 |
| 年 cost | 4.63% | 8.43% |
| 正の block | 21/67 | 8/19 |
| breadth（LOO 最悪） | −0.95 | −0.59 |
| maxDD | −1.601 | −0.259 |
| leverage / margin | 3.22x / 16.1% | 4.91x / 24.6% |
| 年 5% / 年 10% capacity | 到達不能 | 到達不能 |
| verdict | `T2_S06_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` — 長 `SIGNAL_FAILURE` / 近 `COST_FAILURE` | |

**凍結が名指しで要求した cross-track control が、この track の本当の結論である。**
T2 の beta は T1 の beta と +0.856 相関しているので、「FX 自身の価格を超える増分」では足りない。
**T1 を超える増分は両 span とも負**であり、T2 は T1 が既に持つ情報に何も足していない。

### T3 · S02 — sovereign curve 形状 → G10 FX

**長 span は `T3_S02_DATA_NOT_DECISION_GRADE`。** 10y は 5 通貨揃うが **2y leg が揃わない** —
USD 2y は 2020 年開始、GBP 2y は 2016 年開始で、1999–2016 に組めるのは
EUR / CHF / CAD の 3 通貨だけ（cross-section 幅の中央値 3）。
連続 decision day が 60 日に満たない。

近 span（1,190 日 / 4.72 年、**MDE95 = 0.902**）は**両符号を事前登録して両方走らせた**。
両者は定義上の鏡像である（PnL 相関 **−0.993**）。

| | gross SR | **net SR** | incremental IC | 正の block | breadth |
| --- | ---: | ---: | ---: | :---: | ---: |
| **T3-H1**（steepening → 通貨高） | −0.749 | **−1.638** | −0.0135 | 2/19 | −1.89 |
| **T3-H2**（steepening → 通貨安） | +0.749 | **−0.148** | +0.0135 | 8/19 | −0.65 |

turnover は単位 gross あたり **57.9**（凍結補正値 34.8 の **1.66 倍**）で、
**5 本で唯一 turnover 想定を超えた track**。年 cost 9.23%、maxDD −0.829 / −0.209、
leverage 4.68x / margin 23.4%。年 5% / 年 10% とも到達不能。

**multiplicity の解釈:** H2 の gross が正であることと H1 の gross が負であることは
**同じ 1 つの事実**であり、2 通りの探索のうち片方を選んで見出しにすることを凍結が禁じている。
**net はどちらも負**なので、そもそも選ぶ対象が無い。
旧 freeze のまま H1 だけを primary にしていれば「curve shape は明確に負」という結論になっていた。
両符号を登録したことで、**「どちらの向きにも net は無い」**と言えるようになった。

carry 欠落が最も強く効く track でもある — 金利の形を signal にしながら、金利 carry を
落とした panel の上で測っている。**次に carry leg を入れて組み直す価値がある唯一の track。**

verdict: `T3_S02_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`（長 span は `DATA_NOT_DECISION_GRADE`）。

### T4 · S10 — 通貨ネットワーク伝播 → G10 FX

| 項目 | 長 span | 近 span |
| --- | ---: | ---: |
| 日数 / 年 | 4,085 / 16.21 | 840 / 3.33 |
| **MDE95** | **0.487** | **1.074** |
| gross SR | +0.258 | **−0.409** |
| **net SR** | **−1.435** | **−2.890** |
| incremental IC | +0.0013 | −0.0289 |
| turnover（単位 gross） | 153.3 | 153.5（凍結 191.5 内） |
| 年 cost | 18.31% | **25.88%** |
| 正の block | 20/65 | 3/14 |
| breadth（LOO 最悪） | −1.74 | −3.33 |
| maxDD | −2.636 | −1.157 |
| leverage / margin | 3.51x / 17.5% | 4.95x / 24.8% |
| verdict | `T4_S10_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` — `SIGNAL_FAILURE` + `COST_FAILURE` | |

**5 本で最悪の net。** これは実行前に予想されていた — 凍結文が「gate を通っても cost で
落ちる公算が高い」と書いている。turnover は凍結範囲内だが**絶対水準が桁違い**で、
1 日 signal なので当然である。
**rename gate は通った**（自通貨 lag-1 残差との相関が閾値 0.8 未満）ので
**H-003 / Track 1 の言い換えではない**が、別物であることは役に立たなかった。

### T5 · S26 — 越境証券投資フロー（TIC）→ USD

| 項目 | 長 span | 近 span |
| --- | ---: | ---: |
| data / timing | TIC 月次、m+2 月末以降にのみ使用、staleness 上限 75 暦日 | 同 |
| 窓（score が使える域） | 1999-06-30 … 2016-06-01 | **2021-04-28 … 2023-06-14** |
| 日数 / 年 | 4,331 / 17.19 | **555 / 2.20** |
| **MDE95** | **0.473** | **1.321** |
| gross SR | +0.037 | **+0.891** |
| **net SR** | **−0.017** | **+0.838** |
| 年 net | −0.18% | **+8.57%** |
| incremental IC | +0.0024 | **+0.0255**（5 本最大） |
| turnover（単位 gross） | 6.0 | **6.4**（5 本最小、凍結 9.7 内） |
| 年 cost | 0.57% | **0.54%** |
| cost ×1.5 / ×2.0 | — | **+0.811 / +0.784** |
| 正の block | 34/68 | 6/9 |
| **breadth（LOO USD）** | −0.16 | **+0.059** |
| tail（top5 / top10） | — | **0.41 / 0.80** |
| maxDD | −0.595 | **−0.098** |
| leverage / margin（実行時） | 2.77x / 13.9% | **2.51x / 12.5%** |
| rename gate | DISTINCT（最悪 0.180） | **DISTINCT**（horizon 整合で最悪 0.398、閾値 0.8） |
| **verdict** | `T5_S26_MARGINAL_DEVELOPMENT_CANDIDATE` | |

**`MARGINAL` を「証拠がある」と読んではならない。** §7 を読むこと。

---

## 7. T5 の検出力 — 本 cycle の中心的な測定結果

**+0.838 は、その窓の 95% 検出下限 1.321 を下回っている。**
つまりこの窓では、**仮に本物の +0.838 の edge があったとしても確認できない。**

`stage2_t5.json` の permutation（T5 の score を **circular shift** し、自己相関と turnover を
保ったまま return との対応だけ壊す、500 回、seed 20260921）が測ったもの:

| | 値 | 読み方 |
| --- | ---: | --- |
| 凍結 Stage 2 の 3 条件が**帰無のもとで**通る率 | **42%** | 裁定 `multiplicity_note` が要求した数字。**gate を通った事実に情報は薄い** |
| 回帰の signal 係数 | t = **+0.94** | 前方補完の重複を補正しておらず**過大** |
| その permutation p 値 | **0.314** | 帰無の 31% が実測以上の t を出す |
| 零情報 null の net SR 95 パーセンタイル | **+1.13** | 実測 +0.838 は**その内側**（null 平均 −0.02） |

T5 が最も通りやすいのは偶然ではない。**net > 0 という条件は cost drag を超えることを
要求するが、T5 の drag は年 0.5% しかない**ので、gross がわずかでも正なら通ってしまう。

### nuisance 定数の感度（C-2 の裁量が効く大きさ）

| `max_staleness_days` | 日数 | T5 net | 定数 long-USD net | 増分 | 価格のみ MR20 net |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 45 | 533 | +0.738 | +0.408 | +0.331 | +0.599 |
| 60 | 544 | +0.620 | +0.505 | +0.116 | +0.539 |
| 62 | 546 | +0.666 | +0.452 | +0.214 | +0.526 |
| 70 | 552 | +0.721 | +0.386 | +0.335 | +0.564 |
| **75（凍結）** | **555** | **+0.838** | **+0.260** | **+0.578** | +0.487 |
| 80 | 558 | +0.780 | +0.312 | +0.468 | +0.502 |
| 90 | 566 | +0.752 | +0.326 | +0.426 | +0.496 |
| 120 | 587 | +0.813 | +0.218 | +0.595 | +0.691 |
| 400 | 785 | +0.557 | +0.221 | +0.336 | +0.442 |

**凍結値 75 は 9 点中 net Sharpe 第 1 位** — 報告値は楽観側の端である。
一方で **符号はどの点でも正**、**価格のみ baseline も全点で上回る**。
→ **向きは頑健だが、大きさは信用してはならない。**

### その他の留保

- **検出力の高い span が平坦。** 長 span は 7.8 倍の標本（17.19 年、MDE95 0.473）で net −0.017。
- **breadth が 1。** USD を抜くと +0.838 → **+0.059**。USD が gross PnL の **91%**。
- **独立な状態が 24 個**。555 日は独立標本数ではない。SR の t 値は 1.24。
- **集中。** 上位 5 日が net の 41%、上位 10 日で 80%。
- **価格のみ baseline との差が小さい。** MR20 は net +0.487 / **gross +0.846** — gross は
  T5 の +0.891 とほぼ同じ。**T5 の優位は turnover が 1/5 で cost を払わない点から来ており、
  gross の情報量の差ではない。**
- **data が 2023-01 で終わる。**

> ### ⚠ 改訂（revision）— 公表 lag 規約では解決しない残存 look-ahead
>
> `REVISION_CAVEAT` = `TIC_PUBLISHED_FILE_CARRIES_CURRENT_REVISIONS_NOT_THE_VINTAGE_AVAILABLE_AT_DECISION_TIME`
>
> **取得した TIC ファイルは「いま公開されている値」であり、決定時点で入手できた値ではない。**
> 第 m 月の値は m+2 月中旬に速報が出た後も改訂され続けるので、
> 本 cycle が m+2 月末に使っている数字には、**その時点では存在しなかった改訂が含まれている。**
>
> **公表タイミングの lag 規約はこれを直さない。** lag 規約が保証するのは
> 「その日までに**公表されていた**か」であって、「その日に**その値だった**か」ではない。
> 両者は別の要件である。
>
> 直すには vintage（ALFRED 形式の as-of-date 付き系列）が要るが、
> TIC の public 配信は vintage を持たない。**無料の範囲では塞げない。**
>
> **影響の向きは不明だが、楽観側に働く可能性が高い。** 改訂は一般に
> 「後から見て正しかった値」へ寄るので、それを事前に使えば実力以上に見える。
> **T5 の +0.838 はこの分も含んでいる。** §15 の P-1（flow データの購入）は、
> 標本を伸ばすだけでなく**この問題も同時に解く**点で価値がある。

---

## 8. Cross-Track Comparison

| | net SR（良い方の span） | MDE95 | gross | incremental IC | turnover | 年 cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| T1 | −0.435 | 0.473 | +0.139 | +0.0131 | 54.2 | 6.5% |
| T2 | −0.253 | 0.896 | +0.519 | −0.0019（T1 超） | 50.4 | 8.4% |
| T3-H2 | −0.148 | 0.902 | +0.749 | +0.0135 | 57.9 | 9.2% |
| T4 | −1.435 | 0.487 | +0.258 | +0.0013 | 153.3 | 18.3% |
| **T5** | **+0.838** | **1.321** | +0.891 | **+0.0255** | **6.4** | **0.5%** |

**4 本を殺したのは cost である。** T1 / T2 / T3 はいずれも gross が正なのに、
年 6–9% の cost がそれを飲み込んだ。T5 だけが年 0.5% で済んでいる。
**turnover が 8 倍違うことが、5 本の運命をほぼ決めている。**

**近 span では、signal を一切見ない定数 long-USD book が T1 / T2 / T3 / T4 をすべて上回る。**
定数 book 自身の net は窓によって **−0.191（T4 の窓）… +0.591（T2 の窓）** と動き、
2021–2025 のドル高をどれだけ含む窓かで決まるだけなので **edge の証拠ではない**。
だが **4 本が「何も見ない book」に負けた**という事実は、それらの gross の小ささを示す
（T4 近は定数 book も負の窓だが、−0.191 対 −2.890 でなお T4 が負けている）。

## 9. Cross-Track Correlation（診断のみ）

PnL 相関はすべて **|r| ≤ 0.073**（T3 の H1/H2 は定義上の鏡像 −0.993 を除く）。
最大は T4 近 × T5 近 の +0.073。**5 本は互いに独立な情報を見ていた。**

## 10. Signal / Cost / Data の切り分け

| 分類 | 該当 |
| --- | --- |
| `SIGNAL_FAILURE` | T2 長（gross から負）、T4 近（gross から負） |
| `COST_FAILURE` | T1 両 span、T2 近、T3 近（両符号）、T4 長 |
| `DATA_FAILURE` | T3 長（2y leg が 3 通貨しか揃わない） |
| `CONCENTRATION_FAILURE` | 該当なし（net 正が 1 本しかないため判定対象が無い） |
| `IMPLEMENTATION_FAILURE` | 該当なし（ただし §2 の C-1 / C-2 は実装の欠陥である） |

### 「負けた」と「決着していない」を分ける

**一様に負の点推定で区間がゼロを跨ぐなら、それは反証ではなく検出力不足の null である。**
この規律を本 cycle の結果にも当てると:

| | net SR | MDE95 | 帯の外か |
| --- | ---: | ---: | :---: |
| T2 長 | −0.786 | 0.478 | **外（明確に負）** |
| T3-H1 近 | −1.638 | 0.902 | **外** |
| T4 長 | −1.435 | 0.487 | **外** |
| T4 近 | −2.890 | 1.074 | **外** |
| T1 長 | −0.435 | 0.473 | 内（境界） |
| T1 近 | −0.500 | 0.894 | 内 |
| T2 近 | −0.253 | 0.896 | 内 |
| T3-H2 近 | −0.148 | 0.902 | 内 |
| T5 長 | −0.017 | 0.473 | 内（平坦） |
| **T5 近** | **+0.838** | **1.321** | **内** |

**10 本の測定のうち、ノイズ帯の外にあるのは 4 本だけ**で、そのすべてが**負**の側である。
**正の側でノイズ帯の外に出た測定は 1 つも無い。**
`NOT_SUPPORTED`（支持されなかった）は全 track で正しいが、
**`REFUTED`（反証された）と書けるのは上の 4 本だけ**である。

## 11. 候補の分類

- **Positive candidates:** **無し**（検出下限を超えた正の測定が存在しない）
- **Marginal candidates:** **T5 · S26** — `MARGINAL_DEVELOPMENT_CANDIDATE`。
  残す根拠は測れた Sharpe ではなく、**Sharpe と独立に成り立つ構造**である:
  (1) turnover が 5 本で最小、cost 2 倍でも崩れない（**4 本を殺した失敗様式に構造的に強い**）、
  (2) incremental IC が 5 本で最大、(3) 情報源が価格に対して外生、
  (4) nuisance 定数をどこへ動かしても符号は正で、価格のみ baseline を全点で上回る
- **Negative candidates:** T1 · S05、T2 · S06、T3 · S02（近 span）、T4 · S10
- **Data-blocked candidates:** T3 · S02（長 span、`DATA_NOT_DECISION_GRADE`）

## 12. Leverage / Margin の解釈

**三概念を混ぜない。**

1. `max_leverage=5` は placeholder であり、**feasibility の hard limit ではない**
2. broker の 20x / 25x は **margin ceiling** であって **運用の risk budget ではない**
3. risk を決めるのは **vol targeting** である

T5 近 span の実測 vol-per-unit-gross は **4.08%**。

| target vol | 年 net | portfolio gross | margin 利用率 | scaled maxDD | 2% 逆行 gap | margin 残 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8% | 6.70% | 1.96x | 9.8% | −7.66% | −3.92% | 90.2% |
| 10% | 8.38% | 2.45x | 12.2% | −9.58% | −4.90% | 87.8% |
| 12% | 10.05% | 2.94x | 14.7% | −11.50% | −5.88% | 85.3% |
| 15% | 12.56% | 3.67x | 18.4% | −14.37% | −7.35% | 81.6% |

**margin は binding していない。** 制約は margin ではなく **drawdown と検出力**である。
「20x まで使えるから低い Sharpe でも十分」という読み方は裁定 §27 が明示的に禁じている。

## 13. 年 5% net の実現可能性

| | |
| --- | --- |
| 必要 target vol | **5.97%** |
| portfolio gross | 1.46x |
| margin 利用率 | 7.3% |
| scaled maxDD | −5.72% |
| 2% 逆行 gap | −2.92% |

**機械的には到達可能。ただし「net SR 0.838 が本物なら」という条件つきであり、
§7 のとおりその前提は検証されていない**（permutation p = 0.314、検出下限 1.321）。
§7 の感度帯（net +0.557 … +0.838）を当てると必要 target vol は **5.97% … 8.98%** へ動く。

他の 4 本は net ≤ 0 なので **到達不能**であり、**leverage で救わない**（凍結が明示的に禁止）。

## 14. 年 10% net の実現可能性

| | |
| --- | --- |
| 必要 target vol | **11.94%** |
| portfolio gross | 2.92x |
| margin 利用率 | 14.6% |
| scaled maxDD | **−11.44%** |
| 2% 逆行 gap | −5.85% |

同じ条件つき。感度帯を当てると必要 target vol は **11.94% … 17.95%**、
それに伴い scaled maxDD は **−11.4% … −17.2%** へ悪化する。
**年 10% は「届くかもしれない」であって「届く」ではない。**

## 15. Paid-Data Opportunities（proposal のみ。購入していない）

| # | source | 何が測れるようになるか | なぜ public では足りないか | 期待情報利得 |
| --- | --- | --- | --- | --- |
| P-1 | TIC の延長・高頻度化（商用 flow データ） | T5 の唯一の実質的制約は **555 日 / 24 状態**。月次・2023-01 打ち切りがそのまま検出力の上限になっている | TIC public は m+2 公表で 2023-01 まで。週次・日次の実 flow は無料では存在しない | **決定的** — 検出下限 1.32 を下げる唯一の非 Red 経路 |
| P-2 | G10 の 2y sovereign yield 履歴（1999–2016） | T3 長 span が `DATA_NOT_DECISION_GRADE` を脱する。現状 5 通貨中 3 通貨しか揃わない | 各中銀の public series が 2016 年・2020 年開始 | 中 — T3 に 17 年の検出力を与える |
| P-3 | carry leg つき G10 excess return panel | 全 track の共通留保（spot only）を解消。T1 / T3 に最も効く | 無料の日次 forward / deposit rate 履歴が G10 全通貨で揃わない | 中 — 機構と測定対象を一致させる |

**優先は P-1。** T5 以外の 4 本は data ではなく cost と gross で落ちているので、
data を買っても救われない。

## 16. Engineering Findings

### `E-002` — turnover は単位 gross あたりで比べる（**初稿は誤っていた**）

初稿は「実測 turnover が band law を全 track で 1.7〜7.8 倍上回った」と書いていた。
**単位の取り違えだった。** `one_way_traded` は **leverage 適用後**の建玉変化、
band law の turnover は **gross 1 単位あたり**。平均 portfolio gross が 2.5–5.4 なので、
生の値を比べると leverage 倍だけ過大に見える。

気づいた経緯: band law が 18.3 とする 20 日 momentum book が 134.4 RT/年 と出た。
**7.3 倍という比が score の作り方に依らない**ことから、平均 gross 4.5 に行き当たった。

単位を揃えると超過は **T3 の 1 本だけ**（57.9 対 34.8）。
**cost 自体は正しく課金されている**（`charged_cost` は実際の建玉変化に課す）ので
verdict は 1 つも変わらない。変わったのは理由の書き方
（「費用が想定を超えた」→「情報が想定どおりの費用に届かない」）で、後者の方が正しい。

### `M-001` — 帰無通過率を添えない事前登録 gate は、検定ではない

凍結 Stage 2 の 3 条件は**帰無のもとで 42% 通る**。T5 が自動進行したことは設計上
「何かを示した」ように読めるが、実際にはコイン投げ 1.25 回分の情報しかない。
**通過率は track ごとに違い、turnover が低いほど高くなる** —
同じ規則が track によって全く違う厳しさで効いていた。

→ 次の cycle では **gate を凍結する時点で各 track の帰無通過率も計算して一緒に凍結する**。
通過率が 20% を超える gate は、gate ではなく足切りとして扱う。

### `M-002` — 経済的内容を持たない定数は、必ず感度を併記する

`max_staleness_days` は事務上の上限にすぎないのに、net Sharpe を 0.28 動かした。
**結果を見た後に選んだ定数は、選び直さない代わりに格子を開示する。**

## 17. Candidate Inventory Update

| 候補 | 従前 | 本 cycle 後 |
| --- | --- | --- |
| S05 cross-asset risk repricing | 未検証 | `NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`（COST） |
| S06 commodity terms of trade | 未検証 | `NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`（T1 超で負） |
| S02 sovereign curve shape | 未検証 | 近 `NOT_SUPPORTED` / 長 `DATA_NOT_DECISION_GRADE` |
| S10 currency-network propagation | 未検証 | `NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`（最悪 net） |
| S26 international capital flow | 未検証 | `MARGINAL_DEVELOPMENT_CANDIDATE`（未確認） |
| S07 / S25 | 本 cycle 対象外 | 変更なし |

## 18. Remaining Expected-Return Sources

本 cycle は **5 本を潰したのではなく、5 本のうち 4 本について
「この cost 構造では monetize できない」ことを示した**。残る方向は 3 つ。

1. **同じ情報を、より低い turnover で使う。** 5 本の運命をほぼ決めたのは turnover である
   （6.4 対 50–153 RT/年）。T1 / T3 の gross は正なので、**signal の持続性を上げる**
   （＝月次・四半期の情報へ寄せる）と符号が変わる**可能性がある**。**これは新しい情報源ではなく、
   既存 4 本の再設計である。**

   > **これは仮説であって、測定結果ではない。** 本 cycle では**測っていない**。
   > 「T1 を半減期 60 日へ寄せたらどうなるか」を今ここで走らせることは、
   > 凍結が `FORBIDDEN_RESCUES` に挙げる **horizon optimization / band optimization**
   > そのものであり、**結果を見た後に失敗した track を救う行為**にあたる。
   > やるなら**次の cycle で、結果を見る前に事前登録して**走らせる。
   > 根拠として提示できるのは「gross が正で、cost がそれを上回った」という
   > 既に測れている事実までである。
2. **carry leg を入れた panel。** 共通留保の解消。T3 に最も効く。
3. **flow 情報の延長（P-1）。** T5 の検出力問題を解く唯一の非 Red 経路。

## 19. Recommended Next Step

**本 cycle はここで STOP する。** 6 本目・fresh confirmation・multi-source optimization・
非線形 ML・paid acquisition・paper forward はいずれも行わない（裁定 §56）。

Human + ChatGPT へ返す判断は 2 つ:

1. **#490 の merge 可否**（§1 のとおり execution evidence を含むため Amber）
2. **次に何をやるか** — 私の推奨は **§18-1（低 turnover 化による既存 4 本の再設計）を、
   結果を見る前に事前登録して走らせること**である。
   理由は「**4 本とも gross は正なのに cost で死んだ**」という共通構造が、
   本 cycle で最もはっきり測れた事実だからである。新しい情報源を 1 本足すより、
   **同じ情報を 1/8 の回転で使う**方が、期待される改善が大きく、追加の data 取得も要らない。

   **この推奨の裏付けとして、私は低 turnover 版を走らせていない。**
   走らせれば horizon optimization になるからである（§18-1 の注記）。
   推奨の根拠は「gross が正だった」「cost がそれを上回った」という
   **既に測れている 2 つの事実だけ**である。

**programme-level の判断（FX research の継続・停止）は設定していない**（裁定 §55）。

---

## 20. 裁定 §54 — 7 つの問いへの回答

### 1. FX 自身の価格情報を超える incremental expected-return information が見えたものはあるか？

**見えた、と言えるほどの検定はしていない。**
incremental IC の符号は T1（+0.0131 / +0.0066）、T3-H2（+0.0135）、T5（+0.0024 / **+0.0255**）で正、
T2 長（−0.0027）と T4 近（−0.0289）で負だった。
しかし **これらの IC に対して個別の有意性検定は行っていない**ので、
言えるのは「符号がこうだった」までである。
**T2 については更に強いことが言える** — T1 を control に入れると増分は両 span とも負で、
**T2 は T1 が既に持つ情報に何も足していない**。

### 2. gross だけでなく net でも positive な source はあるか？

**T5 の 1 本だけ**（近 span net +0.838 / 年 +8.57%）。
ただし §7 のとおり **その窓の 95% 検出下限 1.321 を下回っており、
零情報 null の 95 パーセンタイル +1.13 の内側**にある。
**「net で正だった」は事実、「net で正である」は未確認。**

### 3. その edge は cost / timing / concentration に対して安定か？

- **cost:** **非常に強い。** ×2 でも +0.784（−0.054 しか落ちない）。5 本で唯一、
  cost が結論を決めなかった track である。
- **timing:** **弱い。** 理由が 2 つある。
  (i) 経済的内容を持たない staleness 上限を 45→400 日で動かすと net が
  +0.56 … +0.84 と動き、**凍結値が最大**。
  (ii) **より重い方:** 取得した TIC は**現在の改訂値**であって決定時点の vintage ではない
  （`REVISION_CAVEAT`）。公表 lag 規約は「公表されていたか」を保証するだけで
  「その値だったか」は保証しない。**無料の範囲では塞げず、楽観側に働く可能性が高い。**
- **concentration:** **弱い。** 上位 10 日が net の 80%、USD が gross PnL の 91%、
  USD を抜くと net が +0.059 へ落ちる。**breadth は実質 1。**

→ **3 つのうち 1 つだけが強い。**

### 4. realistic な target vol / leverage / margin で年 5% net に届く candidate はあるか？

**機械的には T5 のみ** — target vol 5.97%、portfolio gross 1.46x、margin 利用率 7.3%、
scaled maxDD −5.72%。margin は全く binding しない。
**ただしこれは net SR 0.838 を真値としたときの計算**であり、その前提は未確認である。
感度帯を当てると必要 target vol は 5.97% … 8.98%。
他の 4 本は net ≤ 0 なので**到達不能**。

### 5. 年 10% net まで届く candidate はあるか？

**同じ条件つきで T5 のみ** — target vol 11.94%、gross 2.92x、margin 14.6%、
**scaled maxDD −11.44%**。感度帯では maxDD が −17.2% まで悪化しうる。
**「届く」とは書けない。「前提が本物なら届く」である。**

### 6. 複数 candidate が弱く positive なら、multi-source portfolio prereg へ進む価値があるか？

**今回は前提が成立していないので、進む価値は無い。**
cross-track 相関は |r| ≤ 0.073 と理想的に低く、**合成できるなら合成する価値は高かった**。
しかし **net 正は 1 本だけ**で、それも零情報 null と区別がついていない。
**1 本しかないものは portfolio ではない。**
（post-hoc multi-source portfolio optimization は未承認でもある。）

### 7. 全部弱ければ、次に必要なのは new free information / paid information / new economic mechanism / execution improvement のどれか？

**`execution improvement`。** ただし「執行の巧拙」ではなく **turnover 設計**という意味である。

根拠は本 cycle で最もはっきり測れた事実である —
**T1 / T2 / T3 はいずれも gross が正なのに、年 6〜9% の cost がそれを飲み込んだ。**
唯一生き残った T5 の年 cost は 0.5% で、**turnover が 8 倍違うことが 5 本の運命をほぼ決めた。**
しかも T5 の gross（+0.891）は、外部データを一切使わない 20 日 mean-reversion book の
gross（+0.846）とほとんど変わらない。**T5 が勝ったのは情報量ではなく回転の少なさである。**

→ 次に効くのは新しい情報源ではなく、**既にある 4 本の情報を、月次〜四半期の持続性へ
寄せて 1/8 の回転で使う設計**である。追加の data 取得も、新しい機構の発明も要らない。

**ただしこれは仮説であり、本 cycle では測っていない**（§18-1 の注記を読むこと）。
今ここで低 turnover 版を走らせることは `FORBIDDEN_RESCUES` の
**horizon optimization** にあたるので、**次の cycle で事前登録してから**走らせる。

**次点は `paid information`（P-1: flow データの延長）** — ただしこれは
「T5 を確認したい」場合の道であって、「収益を増やしたい」場合の道ではない。

---

## 21. この報告が主張していないこと

- **どれも formal confirmation ではない。** 両 span とも `EXPLORATORY_SEEN_DEVELOPMENT_DATA`
  であり、fresh pool / historical OOS / dead window / forward epoch には進んでいない
- **「flow が有望」とは言っていない。** T5 は零情報 null と区別がついていない
- **「flow が無望」とも言っていない。** 上は**検出力が無い**という意味であって、
  効果が無いと示されたのではない
- **「cross-asset / 原油 / curve shape が無理」とは言っていない。** 4 本のうち
  ノイズ帯の外で負だったのは T2 長・T3-H1・T4 の 3 本分の測定だけである
- **Sharpe が最大だから winner、とは扱っていない**（裁定 §37）
- **programme-level の判断はしていない**（裁定 §55）
