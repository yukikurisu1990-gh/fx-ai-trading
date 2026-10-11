# FX Feasibility Constraint Frontier — 役割の記録（2026-10-11）

事前登録（`docs/research/fx_constraint_frontier_prereg_2026_10.md`、`732fa49`、2026-10-11T14:29:28Z）の commit の後に、別の context の agent に渡した指示の文面（逐語）と、出力の要点。出力の全文は agent の会話の記録にあり、repo には要点だけを残す。

- 3 つの調査は、事前登録の commit の後に並行して起動した。どの agent も価格の data を読んでいない。account の作成・login・取引・demo・data の取得・購入をしていない。
- 数値は、agent が頁の本文から引用したもの（`[V]`）と、検索の要約からのもの（`[S]`、未検証）を区別した。
- 候補の母集団の抽出（§8 の表の元）は、事前登録の commit の前に別の agent が repo の文書だけから行った。

## 1. Role C1 — execution / broker の frontier

### 1.1 指示（逐語）

```text
You are Role C1 (Execution / Broker Frontier researcher) in a pre-registered FX research programme. Repo C:\Users\yukik\fx-ai-trading (read docs/research/fx_constraint_frontier_prereg_2026_10.md §2–§4 first; also docs/research/fx_frontier_expansion_fast_track_final_2026_10.md §11 for OANDA measured spreads). STRICT RULES: public web information only. Do NOT create accounts, log in, trade, use demo, deposit, or call any broker API. Do NOT read FX price data in the repo. Do not modify repo files. Return your output as your final message.

Task: build a public retail FX broker cost/execution table, separating ADVERTISED (published) from MEASURED (independent measurement) values. Brokers to cover (at least): Japanese domestic — SBI FXトレード, GMOクリック証券(FXネオ), GMOコイン(外国為替FX, has public API), みんなのFX/LIGHT FX (トレイダーズ証券), 外為どっとコム, DMM FX, 松井証券 MATSUI FX, 楽天証券/楽天FX, ヒロセ通商 LION FX, auカブコム/三菱UFJ eスマート, OANDA証券 (Japan, incl. MT4/API and any commission/東京サーバー courses), FXTF, ゲインキャピタル/FOREX.com Japan; and international retail references usable by Japanese residents only if clearly legal (otherwise mark NOT_AVAILABLE_TO_JP_RESIDENT): IG, Interactive Brokers (IDEALPRO: commission ~0.2 bp + raw spread), Saxo.
For each: advertised spread for USD/JPY, EUR/USD, GBP/USD, EUR/JPY, GBP/JPY, AUD/JPY (in pips AND converted to bp of price using approximate current levels; show the conversion), whether 原則固定 and which hours are excluded (e.g., early morning JST, around releases), commission, minimum lot, published 約定率 / slippage settings (スリッページ許容幅), rejection policy, spread widening policy, swap/rollover (bid-ask asymmetry of swap points if published, in bp per night approx), order constraints, and CRUCIALLY whether automated trading is allowed and via what (public REST/stream API, MT4/MT5 EA, none; any prohibition on automated/high-frequency/スキャルピング trading in terms). Also any independent measurements (e.g., third-party spread surveys) of actual average spreads.
Also give the source URL and access date for every number, and quote the exact text for each key number (to prevent fabricated numbers). If a page could not be accessed, say so; never estimate a published value.
Finally compute, per the prereg §3 rules: E1 = median advertised normal-time spread across brokers that ALLOW automated trading (per pair: USD/JPY, EUR/USD at least) + slippage 0.35 bp; E2 = minimum credible continuously-offered (non-campaign) advertised spread among automated-allowed accounts + 0.2 bp; include commission in bp. List excluded hours. Note which brokers are excluded from E1/E2 because automation is not allowed. Output under 3000 words with tables.
```

### 1.2 出力の要点（ADVERTISED、2026-10-11 に取得）

| 区分 | 内容 |
| --- | --- |
| 自動売買の禁止 | SBI FXトレード（約款 §32 ③）、DMM FX（約款 第7条、約定の無効化あり）、GMOクリック証券 FXネオ（規程 第34条）、みんなのFX（約款 第22条）、LIGHT FX（同じ発行者、推定）、外為どっとコム、ヒロセ通商（公式の経路なし） |
| 限定 | 松井証券（社内のリピート注文、外部 API の注文は狭い spread の対象外）、三菱UFJ eスマート証券（社内のシステムトレード） |
| 自動売買が可能で、通常時の spread を公表 | OANDA証券 スタンダード MT5、OANDA NY プロ（REST）、FXTF MT4（ゼロ spread + 手数料、2026-01-19 から、campaign ではない）、サクソバンク証券（OpenAPI、5 万 USD 以下） |
| 公表なし | GMOコイン（変動制、API の手数料 0.002% = 往復 0.4 bp）、楽天 MT4、IG 証券 |
| 対象外 | Interactive Brokers 証券（日本の居住者の投機的な FX の取引なし）、FOREX.com Japan（取得できず）、OANDA MT4（新規の開設は 2026-03-27 で終了） |
| E1（中央値 + 0.35） | USD/JPY **0.66 bp**、EUR/USD **0.76**、EUR/JPY 0.75、GBP/USD 1.06、GBP/JPY 1.02、AUD/JPY 1.09 |
| E2（最小 + 0.2） | USD/JPY **0.33 bp**（Saxo、5 万 USD 以下）、EUR/USD **0.53**（FXTF）、EUR/JPY 0.48、GBP/USD 0.68、GBP/JPY 0.59、AUD/JPY 0.79 |
| 原則固定の時間帯 | 国内の多く・FXTF は 9:00〜翌 3:00 JST（夏 20:00〜14:00 ET、冬 19:00〜13:00 ET）。Saxo は 8:00〜翌 3:59 JST。rollover の 17:00〜19:00 ET・週の開始と終了・主要な指標の発表の前後は全て除外 |
| MEASURED | 独立の測定は 1 つの blog だけ（FXTF MT4、2026-09、1 分の snapshot 36,185 件、USD/JPY 中央値 0.0 pips、P95 約 3.8、FOMC 約 5.9。spread だけ）。broker の自社の提示率（SBI USD/JPY 0.18 銭 94.58% など）。**OANDA の実測（PR #508）は、OANDA 自身の NY プロの公表値の約 2.2 倍** |
| 未記録 | swap の bid / ask の非対称（JavaScript の表で抽出できず）、約定率・拒否の data（どの broker も公表なし） |

## 2. Role C4 — 独立な data の入手可能性

### 2.1 指示（逐語）

```text
You are Role C4 (Independent-data availability researcher) in a pre-registered FX research programme. Repo C:\Users\yukik\fx-ai-trading (read docs/research/fx_constraint_frontier_prereg_2026_10.md §6 and §8.4, and docs/research/fxid_cycle1_data_feasibility_final_report_2026_10.md lines ~140–225 for what is already known). STRICT RULES: public web information only; do NOT download, purchase, register for, or request any data; do NOT read FX price data in the repo; do not modify files. Return output as your final message.

Task: survey historical FX data sources that contain BID and ASK (or spread) at intraday resolution (tick, M1, M15, H1) and, separately, Sunday-reopen coverage, by era: pre-1990, 1990s, 2000s, 2010–2016-05. Candidate sources: OANDA (v20 candles price=BA from 2005? per-pair start), Dukascopy (tick bid/ask, terms on automated download), TrueFX/Integral (from 2009), HistData.com (tick bid/ask; M1 bid-only; terms), GAIN Capital / FOREX.com rate data archive (ratedata.gaincapital.com, from 2000?), FXCM (tick data from 2015? ), Olsen Data (paid, from 1986?), LSEG/Refinitiv Tick History (paid, from 1996), EBS Data Mine, CME (FX futures, not spot), Kibot, TickData LLC, Massive/Polygon, Bloomberg, academic (WRDS? Olsen HF datasets used in papers), ECB/BIS (daily only), Federal Reserve H.10 (daily noon buying rates, no bid/ask).
For each: pairs, start date, resolution, bid/ask availability, whether Sunday open is included, price (free / paid with published price if any), licence/terms for research use (quote the relevant text and URL), and known quality issues (indicative quotes vs executable, retail broker feed vs interbank). Quote exact text and give URL + access date for every claim; never estimate. Then summarise: (a) free sources whose terms permit research use, with earliest bid/ask intraday date; (b) free sources with unknown/restrictive terms; (c) paid sources and prices. Under 2500 words.
```

### 2.2 出力の要点

| 時代 | intraday の bid / ask |
| --- | --- |
| 1990 年より前 | Olsen だけ（有料、1986〜、「indicative」な統合の quote、価格は非公表） |
| 1990 年代 | Olsen、LSEG Tick History（1996-01〜、FX の Super RIC は「not a firm price」）、EBS（1996-12 / 1997-01〜 `[S]`）。全て有料 |
| 2000 年代 | HistData（tick の bid / ask、2000-05〜、無料、**規約が見つからない**、M1 は bid だけ）、Dukascopy（2003-05〜 `[S]`、**自動の取得と database の構築を禁止**）、OANDA（「2005 年から」、規約は未検証）、TickData（2008-05〜、有料）、TrueFX（2009-05〜 `[S]`、「internal purposes」を許すが派生物を禁止）、Kibot（2009-09-28〜、$990）、Massive（2009-09-25〜、有料）。GAIN Capital の archive は DNS で解決できない |
| 2010〜2016-05 | 上と同じ（GAIN を除く）。FXCM の公開の candle は 2017 年から |

- **日曜の再開の被覆は、どの源も文書で確認できない**（Olsen は「weekends are not actively omitted」）。
- 研究の利用を明確に許す無料の源は無い（TrueFX は派生物の禁止の範囲が不明）。lead は事前登録 §8.4 の規則で「規約が不明」に数えた。

## 3. Role C5 — 公表の後の減衰（haircut）の監査

### 3.1 指示（逐語）

```text
You are Role C5 (Publication-decay / haircut auditor) in a pre-registered research programme. Repo C:\Users\yukik\fx-ai-trading (read docs/research/fx_constraint_frontier_prereg_2026_10.md §7). STRICT RULES: public literature only; do NOT read FX price data; do not modify files; do NOT look at or reason about any specific candidate strategy's results — your output must be candidate-independent. Return output as your final message.

Task: build an evidence-based prior distribution for the retention factor d = (true out-of-sample / post-publication effect) / (published in-sample effect) for trading anomalies, with emphasis on (i) cross-market equity anomaly decay studies and (ii) FX-specific evidence. Sources to check (verify each number with an exact quote and URL/DOI; if you cannot access the paper text, say so and mark the number UNVERIFIED; never invent numbers): McLean & Pontiff (2016, JF) out-of-sample vs post-publication decline; Chen & Zimmermann (2020/2022) ; Jacobs & Müller (2020, JFE) international post-publication; Hou, Xue & Zhang (2020, RFS) replication; Harvey, Liu & Zhu (2016) multiple testing haircut (their suggested Sharpe haircut ~50%); Jensen, Kelly & Pedersen (2023, JF) "Is there a replication crisis"; Falck, Rej & Thesmar (2022) "Why and how systematic strategies decay"; Penasse (2022) "Understanding alpha decay"; Bailey & López de Prado deflated Sharpe; FX: Neely, Weller & Ulrich (2009, JFQA) technical rules adaptive markets; Olson (2004); Menkhoff, Sarno, Schmeling & Schrimpf (2012) currency momentum; Burnside et al. carry; any studies on FX intraday anomaly persistence (e.g., fix-related effects after 2015 WMR reform; Krohn, Mueller & Whelan follow-ups), and post-publication evidence for FX anomalies.
Deliver: (1) a table of studies with the decay/retention estimate, sample, market, and exact quote; (2) a proposed Beta(a,b) prior for d_pub (literature-published effects) with mean, median, 10th/90th percentiles, and the justification; (3) a separate statement about d_desk (effects predicted at a desk with NO direct empirical evidence): whether any external study gives a direct value; if not, say so plainly and state what the literature implies as an upper bound (d_desk should not exceed d_pub); (4) where the current fixed 50% haircut falls in your d_pub distribution (percentile). Under 2500 words.
```

### 3.2 出力の要点

| 研究 | 残存率 d |
| --- | --- |
| McLean & Pontiff（2016） | 公表の前の sample の外 0.74、公表の後 0.42 |
| Falck, Rej & Thesmar（2021/22） | Sharpe の slope 0.57、中央値 0.55、国際 約 0.4、新しい公表ほど減衰が大きい |
| Jensen, Kelly & Pedersen（2023） | 平均 約 0.69、ただし in-sample の値への回帰の slope 0.25〜0.43 |
| Chen & Zimmermann（2020、2022） | 統計の bias だけで 0.85〜0.90（上限） |
| Jacobs & Müller（2020） | 米国以外の株式では公表の後の減衰が無い（分断された市場） |
| Harvey & Liu（2015） | 「50% の haircut は経験則にすぎない」。Sharpe < 0.4 では 50% 超、> 1.0 では 25% 以下 |
| Neely, Weller & Ulrich（2009、FX の technical rule） | 0〜0.57（family による） |
| Olson（2004） | 約 0（1990 年代） |
| Hutchinson ほか（2022、FX の carry・momentum・value） | Sharpe +0.39 → −0.32（負） |
| Krohn, Mueller & Whelan（2024） | 2014〜2019 で東京の fix の反転は小さいが有意（著者の sample の中で、公表の後の証拠ではない） |

- **d_pub の prior: Beta(1.2, 2.2)**、平均 0.353、中央値 0.322、10%点 0.072、90%点 0.686。FX の証拠に重みを置いた。
- **d_desk の直接の値は無い**。文献は d_desk ≤ d_pub（確率的に）の上限だけを与える。
- **固定の 50% は d_pub の 73 パーセント点**で、証拠に比べて楽観的。
