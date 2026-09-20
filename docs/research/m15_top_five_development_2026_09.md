# Top-Five development 結果（2026-09-21）

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Authority: 2026-09-21 Human + ChatGPT 裁定
freeze digest: **`28100ebedfea45765371585df5c4308fee261e2496a9798acca79c920158962c`**
（旧 `29ba80d6…` は `SUPERSEDED_PRE_EXECUTION`）

**5 本すべてを凍結後に実行した。設計は 1 度も動かしていない。**
本文書が引く数値はすべて `artifacts/research/top_five/development.json` の実測値である。

---

## 0. 結論を先に

**5 本のうち net が正だったのは 1 本だけで、それも marginal である。**

| | 候補 | 情報 | 最終 status |
| --- | --- | --- | --- |
| T1 | S05 | 株式 volatility | `T1_S05_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` |
| T2 | S06 | 原油 | `T2_S06_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` |
| T3 | S02 | 金利 curve 形状 | `T3_S02_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`（長 span は `DATA_NOT_DECISION_GRADE`） |
| T4 | S10 | 通貨間伝播 | `T4_S10_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` |
| **T5** | **S26** | **越境証券 flow** | **`T5_S26_MARGINAL_DEVELOPMENT_CANDIDATE`** |

**本 cycle は 5 通りの探索 + T3 内の 2 符号探索**である（`FIVE_WAY_..._PLUS_A_TWO_SIGN_SUB_SEARCH_WITHIN_T3`）。
p 値を formal proof として扱わない。

---

## 1. 共通基準での比較（裁定 §35）

| key | 日数 | gross SR | net SR | incremental IC | turnover | 正の四半期 | rename gate |
| --- | ---: | ---: | ---: | ---: | ---: | :---: | :---: |
| T1 長 | 4,321 | +0.139 | −0.435 | +0.0131 | 191.3 | 29/68 | — |
| T1 近 | 1,211 | +0.336 | −0.500 | +0.0066 | 283.8 | 9/19 | — |
| T2 長 | 4,233 | −0.354 | −0.786 | −0.0027 | 136.0 | 21/67 | — |
| T2 近 | 1,205 | +0.519 | −0.253 | +0.0047 | 247.6 | 8/19 | — |
| T3 長 H1/H2 | — | — | — | — | — | — | `DATA_NOT_DECISION_GRADE` |
| T3 近 **H1** | 1,210 | −0.622 | −1.487 | −0.0140 | 270.3 | 3/19 | DISTINCT |
| T3 近 **H2** | 1,210 | +0.622 | −0.247 | +0.0140 | 270.3 | 8/19 | DISTINCT |
| T4 長 | 4,085 | +0.258 | −1.435 | +0.0013 | 537.5 | 20/65 | DISTINCT |
| T4 近 | 840 | −0.409 | −2.890 | −0.0289 | 759.8 | 3/14 | DISTINCT |
| T5 長 | 4,331 | +0.037 | −0.017 | +0.0024 | 16.7 | 34/68 | DISTINCT |
| **T5 近** | **548** | **+0.726** | **+0.672** | **+0.0221** | **16.1** | **6/9** | **DISTINCT** |

> `top_N_day_contribution` は net が負の track では符号が反転するため意味を持たない。
> net が正の T5 近 span についてのみ解釈する。

### benchmark（同じ窓・同じ執行層）

| key | FX own momentum 20d | mean reversion 20d |
| --- | ---: | ---: |
| T1 近 / T2 近 / T3 近 | −0.794 | −0.007 |
| T4 近 | −1.040 | +0.267 |
| **T5 近** | −1.269 | **+0.550** |
| T1 長 / T2 長 | +0.094 / +0.067 | −0.617 / −0.598 |

---

## 2. 失敗の分類（裁定 §32）— 「failed」で一括りにしない

### T1（株式 volatility）— `COST_FAILURE`

**gross は両 span で正**（長 +0.139 / 近 +0.336）で、incremental IC も正（+0.0131 / +0.0066）。
**情報が無いのではない。** しかし実測 turnover が 191 / 284 RT/年で、
凍結した補正値 82.5 を 2.3〜3.4 倍超え、net は −0.435 / −0.500 になる。
**その情報を取りに行く費用が、情報の価値を上回っている。**

### T2（原油）— 長 span `SIGNAL_FAILURE` / 近 span `COST_FAILURE`

**2 つの span で失敗の種類が違う。** 長 span は gross からして負（−0.354、incremental IC −0.0027）で、
交易条件という機構が 17 年の panel では支持されない。近 span は gross +0.519 と正だが
turnover 248 RT/年で net −0.253。

### T3（金利 curve 形状）— 長 span `DATA_FAILURE` / 近 span `COST_FAILURE`

**長 span は data が足りなかった。** 10y は 5 通貨とも揃ったが、**2y leg が揃わない** —
USD 2y は 2020 年開始、GBP 2y は 2016 年開始で、1999–2016 に組めるのは
**EUR / CHF / CAD の 3 通貨だけ**（cross-section 幅の中央値 3）。
連続する decision day が 60 日に満たず `DATA_NOT_DECISION_GRADE` とした。

#### 符号の多重性 — 凍結が効いた場所

近 span では H1 と H2 の両方を走らせた。**両者は定義上の鏡像**である（PnL 相関 **−0.993**）:

| | gross SR | net SR | incremental IC |
| --- | ---: | ---: | ---: |
| T3-H1（steepening → 通貨高） | −0.622 | −1.487 | −0.0140 |
| T3-H2（steepening → 通貨安） | +0.622 | −0.247 | +0.0140 |

**「H2 の gross が正だったので curve theory が支持された」とは言えない。**
H2 の gross が正であることと H1 の gross が負であることは同じ 1 つの事実であり、
2 通りの探索のうち片方を選んで見出しにすることを凍結が禁じている。
そして **net はどちらも負**なので、そもそも選ぶ対象が無い。

もし旧 freeze のまま H1 だけを primary として走らせていれば、
「curve shape は明確に負」という結論になっていた。
両符号を事前登録したことで、**実際には「どちらの向きにも net は無い」**と言えるようになった。

### T4（通貨間伝播）— `SIGNAL_FAILURE` + `COST_FAILURE`

近 span は **gross も負**（−0.409、incremental IC −0.0289）。
turnover は長 538 / 近 760 RT/年で、net は −1.435 / −2.890 と **5 本で最悪**。
これは実行前に予想されていた — 凍結文が「gate を通っても cost で落ちる公算が高い」と書いている。

**rename gate は通った。** 自通貨 lag-1 残差との相関は閾値 0.8 未満で、
H-003 / Track 1 の言い換えではない。ただし**別物であることは役に立たなかった**。

### T5（越境証券 flow）— net 正、ただし marginal

`T5_S26_MARGINAL_DEVELOPMENT_CANDIDATE`。

**支持する側の事実:**
- 近 span で gross +0.726 / net +0.672 / 年 net **+6.85%**
- turnover 16.1 RT/年と 5 本で最小、年 cost 0.55%
- **cost を 2 倍にしても net Sharpe 0.618** で崩れない（×1.5 で 0.645）
- rename gate 通過 — 1/2/3 か月ラグの USD basket return との相関 **0.096**。
  **2 か月遅れの USD momentum ではない**
- 6/9 四半期が正

**marginal に留める 6 つの理由:**

1. **検出力の高い方の span が平坦。** 長 span は 4,331 日（17.2 年）で gross +0.037 / net −0.017。
   近 span の **8 倍の標本が何も示さない**。
2. **事前登録した Stage 2 が null。** 3 条件を満たしたので凍結規則どおり自動進行し、
   2 変数線形回帰を走らせた結果、signal 係数は **t = +0.72**（観測 4,232、R² 0.0008）。
   観測単位の予測力としては測れない。
3. **breadth が 1。** USD を抜くと net Sharpe が +0.67 から **−0.12** へ落ちる。
4. **集中が重い。** 上位 5 日が net の **52%**、上位 1 日で 11%。
5. **価格のみの baseline に僅差。** 同じ 548 日で 20 日 mean reversion book が **+0.550**。
   外部データを一切使わない baseline との差は **+0.12 しかない**。
6. **data が 2023-01 で終わる。** vintage 2 か月を足すと使用可能域は 2021-04 〜 2023-06 の
   **2.17 年**だけ。

---

## 3. leverage と年間利益（裁定 §22–§28）

**broker ceiling を hurdle にしない。** 実測 net Sharpe から、realistic な target risk で
年間 return へ変換できるかを見る。

T5 近 span（net Sharpe 0.672、実行時の margin 利用率 12.5%）:

| target vol | 年 net | risk leverage | margin 利用率 |
| ---: | ---: | ---: | ---: |
| 8% | 5.38% | 3.44x | 17.2% |
| 10% | 6.72% | 4.29x | 21.5% |
| 12% | 8.06% | 5.15x | 25.8% |
| 15% | 10.08% | 6.44x | 32.2% |

| 目標 | 必要 target vol | risk leverage | margin 利用率 | broker ceiling 内 |
| --- | ---: | ---: | ---: | :---: |
| **年 5% net** | 7.44% | 3.20x | 16.0% | ✅ |
| **年 10% net** | 14.88% | 6.39x | 32.0% | ✅ |

**ただしこれは「net Sharpe 0.672 が本物なら」という条件つきである。**
§2 の 6 つの留保、とくに長 span の平坦さと Stage 2 の null がその条件を弱くしている。

他の 4 本は net Sharpe ≤ 0 なので、**leverage で救わない**（凍結が明示的に禁じている）。

---

## 4. cross-track correlation（裁定 §36 — 診断のみ）

PnL 相関は **すべて |corr| < 0.08**（T3 の H1/H2 は定義上の鏡像 −0.993 を除く）。
最大は T4 近 × T5 近 の +0.073。

**5 本は互いに独立な情報を見ていた**と言える。
しかし **net 正は T5 の 1 本だけ**なので、**合成する対象が無い**。
portfolio 化は本 cycle では行わない（次フェーズの prereg 対象）。

---

## 5. engineering の発見（裁定 §40）— verdict を救うためのものではない

**`E-002` — 実測 turnover が band law を全 track で上回った。**

| track | 凍結した補正値 | 実測 | 超過率 |
| --- | ---: | ---: | ---: |
| T1 | 82.5 | 283.8 | 3.4x |
| T2 | 82.5 | 247.6 | 3.0x |
| T3 | 34.8 | 270.3 | 7.8x |
| T4 | 191.5 | 759.8 | 4.0x |
| T5 | 9.7 | 16.1 | 1.7x |

band law は「forecast が lookback どおりに減衰する」前提で turnover を出す。
5 日差分の z-score も cross-section rank も月次 z も、その前提を満たさない。
**turnover の見積もりが構造的に低い**ということであり、
cost を軸に判定してきた本 programme の過去の feasibility 計算すべてに関わる。

**この発見で今回の verdict を救わない。** band を広げれば T1 / T2 の net は改善しうるが、
それは結果を見た後の band optimization であり、凍結が明示的に禁じている。
次の cycle で**事前に**決めるべき設計事項として記録する。

---

## 6. 保護データの状態

| 対象 | 状態 |
| --- | --- |
| fresh pool `2016-06-02 … 2021-04-25` | **未読** |
| historical OOS | **未読** |
| dead window | **未読** |
| forward Formal Confirmation epoch | **未読** |

取得した 8 source はすべて seen window 内に切り落とされている（TIC は vintage 適用後の日で判定）。
近 span の FX panel は既存の guarded cache 3 本が連続被覆しており、**archive の新規読み取りはゼロ**。

broker: public margin 仕様のみ使用。authenticated API / demo / paper / live には触れていない。
paid data: 購入していない。

---

## 7. この結果が主張していないこと

- **「cross-asset が無理」とは言っていない。** T1 は gross と incremental IC が正で、cost で落ちた
- **「原油が無理」とは言っていない。** 長 span では機構が支持されなかったが、近 span の gross は正だった
- **「curve shape が無理」とは言っていない。** 長 span は data 不足で検定できておらず、
  近 span はどちらの符号も net 負だった、というだけである
- **「flow が有望」とも言っていない。** T5 は 5 本で唯一の net 正だが、
  **検出力の高い span は平坦**で、事前登録した Stage 2 は null である
- **どれも formal confirmation ではない。** fresh / OOS / dead / forward には進んでいない
