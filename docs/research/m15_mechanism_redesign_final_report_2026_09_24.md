# Mechanism Redesign cycle — 最終統合報告（2026-09-24）

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` ·
`PRODUCTION_READINESS_NOT_CLAIMED`

2026-09-24 Human + ChatGPT 裁定（「candidate の調整から mechanism の発見へ」）への最終報告。

> **merge 時の確定（第 2 裁定 §1–§4）**:
> M15 = `INVALID_IMPLEMENTATION_BOOK_MISMATCH`、M16 = `INVALID_IMPLEMENTATION_BOOK_MISMATCH`
> （凍結は USD versus 7-currency basket、実際は USD versus AUD/CAD/CHF。既存の数値は hypothesis の判定に使わない）。
> M11 / M01 = `POSITIVE_EXPLORATORY_NOT_DECISION_GRADE`、M10 = `NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`（fresh へ進めない）。
> 本報告の「net」は `NET_INCLUDING_APPROXIMATE_INTEREST_DIFFERENTIAL_AND_ASSUMED_MARKUP` で、**実際の OANDA financing ではない**。
> M15 / M16 の修正版の実行は `POST_RESULT_IMPLEMENTATION_CORRECTED_EXPLORATORY_ONLY`（M16 の結果を見た後）。
> 保護情報の定義を metadata・属性・公表文・政策決定文まで拡張し、D-M3 は
> `JPY_RATE_RELATED_FORWARD_CONFIRMATION_CONTAMINATED_BY_EXTERNAL_INFORMATION_EXPOSURE`（JPY 金利の mechanism に限る）。
> 詳細は `scripts/research/mechanism_redesign/post_run.py`。

数値の出典: `artifacts/research/mechanism_redesign/development.json`（1 回の実行、HEAD `0ee7160`、
dirty 0）。記録の読み方は `scripts/research/mechanism_redesign/post_run.py`。

---

## Executive Summary

- **mechanism 再設計**:
  - 過去の evidence を読み直し、G10 FX spot の expected-return mechanism を**27 候補**に作り直した（A〜J の 10 family をすべて含み、有料データの候補 4 を含む）。
  - 閉じた family の rename と、U1..U5 の救済は、情報集合と定式で照合して外した。
  - 構造上の発見が 1 つある。**これまでの track は、1 本（T5）を除いてドル factor を中立化した相対 book で測られていた。** 金利や macro の情報でドル factor を target にしたことは無かった。
- **選択と実行**:
  - Stage 0（request-level exclusion での取得）と signal-blind feasibility を通った **5 本を凍結し、1 回実行した**: M15 dollar carry、M11 macro momentum、M16 米国 vs 他国の macro momentum（ドル）、M01 Taylor gap、M10 流動性 premium。
  - 実行の前に独立 review を 5 回受け、pre-alpha amendment を 4 回入れた。carry の会計、pair book、保護暦日、凍結の閉包を直している。
- **実行後の統合 review で、ドル factor の 2 本（M15 / M16）に book 構成の欠陥が見つかった。**
  - 凍結した設計は「USD 対 7 通貨 basket」だった。実際に走ったのは「USD 対 AUD / CAD / CHF」で、EUR / GBP / JPY / NZD は恒久的に 0 になっていた。
  - **M15 / M16 は凍結した mechanism の検定として無効**とする。唯一の MARGINAL だった M16 を結果の後に作り直すことは救済の形になるので、**再実行はしていない**。
- **有効な 3 本の結果**:

  | track | primary の net Sharpe | verdict |
  |---|---|---|
  | M11 | +0.159 | POSITIVE_EXPLORATORY（頑健性なし） |
  | M01 | +0.080 | POSITIVE_EXPLORATORY（検出力の上限） |
  | M10 | −0.450 | NOT_SUPPORTED |

- **全体の数**:
  - null を超えた（p ≤ 0.05）track は **0 本**で、最小 p は無効の M16 を除くと 0.198。
  - **decision-grade の candidate は 0 本**。
  - **年 5% に届く candidate は無い。**
- **最大の bottleneck は signal quality と検出力の両方**。月次 macro の signal は 17 年でも有効標本数が 5〜23 個しかない。
- **次の一手**:
  - ドル factor の book を直した**新しい事前登録**（判断事項 1）。
  - retail の financing を実測すること。
  - FX spot の単一 candidate では検出力の天井を越えられない、という前提に立った研究計画の見直し。

---

## Identity

| 項目 | 値 |
|---|---|
| #492 | final head `84d7832`、merge `b06436a`（merge commit、CI success） |
| #493 | final head `5465f91`、merge `c95c11f`（merge commit、CI success） |
| master（両 merge 後） | `c95c11f`（CI success） |
| 本 cycle の branch | `research/m15-mechanism-redesign`（1 PR にまとめる。Amber、Human + ChatGPT の merge 承認待ち） |
| 凍結の履歴 | `dcc26df`（初版 `2815e1dd…`）→ `bfa3ad1`（`e1399851…`）→ `0e7bcaa`（`21f7c0fb…`）→ `cc65ccb`（`4f89edc9…`）→ `0ee7160`（**最終 `a4413d63…`**）。すべて alpha の前 |
| 実行 | 1 回、2026-09-23T21:25:29Z、HEAD `0ee7160`、dirty 0、`--workers 14`。記録 `development.json` / `development_started.json`（commit `a5f25aa`） |

---

## Prior Cycle Finalization

- #492 → #493 の順で merge した。head を変えずに merge するため merge commit にした。
- 記録として採るのは `development_run4.json`。qualifier は **`POST_EXECUTION_SHARED_DEFECT_CORRECTED_EXPLORATORY_RESULT`**（`mechanism_redesign/prior_cycle.py`）。
- `development_run2.json` は INVALID のまま保持する。C-1〜C-6 は削除も弱化もしない。
- U1..U5 の status は裁定 §3 のとおり。禁止する救済（horizon / sign / subset / smoothing / staleness / threshold / lag / feature / low-turnover / leverage / nonlinear）は `FORBIDDEN_U1_U5_RESCUES` に記録した。

## D-5 Policy

`scripts/research/data_access/request_policy.py` を追加した。

- **保護暦日は request の段階で外す。** 判定は**参照期間**で行う。月次は 2016-05 と 2021-05 … 2025-11、四半期は 2016Q1 と 2021Q3 … 2025Q3 まで。
- 境界の指定は `str` の厳密な `YYYY-MM-DD` だけを受け、parse した日付で比較する。str subclass と曖昧な綴りは拒否する。
- **bulk-only の provider は例外承認まで取得しない。** 対象は H.4.1 zip・SNB cube・BoJ 全系列・Fed JSON・BIS bulk zip で、承認は 0 件。
- **provider が bound を無視したら保存せずに拒否する**（filter はしない）。`providers.alfred` は期間の無い request を拒否する。
- 外部 macro series の memory parse（D-5）と FX fresh pool の読み取りを区別して記録した（`prior_cycle.D5_DISTINCTION`）。**FX の fresh pool は読んでいない。**

---

## Mechanism Universe（27 候補、`universe.py`）

A: M01 Taylor gap・M02 市場経路 vs fundamentals・M15 dollar carry・M21 政策循環・M25 OIS（有料）。
B: M03 曲線の状態遷移・M19 breakeven（閉鎖）。
C: M04 国債の先行・M05 株式下落→安全通貨・M20 交易条件指数。
D: M06 通貨 network。
E: M07 非同期市場の伝達。
F: M08 日本の対外証券投資・M09 euro 圏 BoP・M22 季節的な送金・M27 CLS flow（有料）。
G: M10 流動性 premium・M26 CME 先物の order flow（有料）。
H: M11 macro momentum・M12 予測分散（有料）・M16 米国 vs 他国 macro → ドル・M17 EPU・M18 CLI・M23 財政。
I: M13 vol 状態 × beta・M24 option risk reversal（有料）。
J: M14 ドル funding stress。

各候補には template の 23 field をすべて書いた。mechanism、なぜ FX が遅れるか、情報源、horizon、
持続性、turnover、breadth、データ、timing と改訂、先行研究との重なり、新規性、gross / net の見込み、
capacity、leverage、複雑さ、過剰適合のリスク、情報利得である。

## Prior-Overlap Audit（`ranking.OVERLAP_AUDIT`）

- **rename / 閉鎖として除外**:
  - M03（T3 曲線）、M04（S01）、M05（T1 / U5）、M06（T4 / H-003）、M13（S24 / T1）、M19（S28）、M20（T2）、M21（C01）
  - M07 は無料版が clock/fix と同型。M22 は event 数が少なく過剰適合。M23 は符号が定まらない。
- **データ・経路の理由で除外**:
  - M08（bulk-only）、M09（breadth 1）、M12 / M24 / M25 / M26 / M27（有料）
- **pre-alpha review で訂正したもの**:
  - M14 は初版で「U5 の rename」としたが、それは過剰一般化だった。U5 は XS book で測られており、ドル方向は未測定である。**ELIGIBLE だが 5 本の枠の 6 番目**なので選んでいない。
  - M01 は初版で「政策金利が無い」としたが、それは ALFRED 経路の制約で、BIS の SDMX で取れた。

## Signal-Blind Ranking

- **prior score**（§18 の概念式を幾何平均の比にしたもの。判断の集計）:

  | 候補 | score |
  |---|---|
  | M15 | 2.47 |
  | M11 | 1.82 |
  | M16 | 1.75 |
  | M01 | 1.48 |
  | M21 | 1.34（rename で除外） |
  | M10 | 1.21 |
  | M17 | 1.18 |
  | M14 | 0.65 |

- **Stage 0**（ALFRED と BIS、request-level exclusion）:
  - M17 EPU は ALFRED が期間指定を無視した（D-M2）ので、route を止めた。
  - M18 は vintage の再構成が重い。M02 は無料では 3 通貨しか無い。
- **signal-blind feasibility**（`feasibility_amendment.json`、return を使わない）:

  | 候補 | long の有効標本数 | recent |
  |---|---|---|
  | M15 | 5.0（符号 regime 6 個） | 全期間ドル買い |
  | M11 | 13.2 | — |
  | M16 | 23.1 | — |
  | M01 | 6.2 | — |
  | M10 | recent のみ 3.8 年 | — |

## Selected Tracks と凍結

- 最終凍結は `a4413d63…`。凍結の payload には次を含めた。
  - signal の式、book の設定、ドル track の deviation
  - 判定 P&L（**spot + carry accrual − spread cost − 仮定 financing markup 0.25%/年**）
  - null（circular shift 1000 回、seed 20260924）
  - E1〜E8、Stage 2 の適格条件、verdict の規則
  - 検出力の上限（有効標本数 10 未満は POSITIVE_EXPLORATORY まで）
  - rename gate と、その評価ができない場合の扱い（NOT_EVALUABLE）
  - nuisance の感度集合
  - 32 file のコード閉包の hash、入力 manifest の hash
- driver は次のどれかに当たると、計算を始める前に止まる。
  - 記録・開始記録が既にある
  - digest が合わない
  - tree が dirty
  - 入力が manifest と一致しない

---

## 各 track の結果

### M15 dollar carry — **INVALID（book の欠陥）**

- **Mechanism**: 外国の平均金利が米金利を上回る間は、ドル factor が carry premium を払う（Lustig–Roussanov–Verdelhan）。
- **Why FX should lag**: 遅れではなく risk premium。
- **Information source / Data**: OECD MEI の 3 か月銀行間金利 8 通貨（ALFRED）。carry の欠損は BIS の政策金利で埋め、BoJ のゼロ金利期は 0% と置いた（判断）。
- **Timing**: m+1 月末。
- **Revision**: CURRENT_VINTAGE_ONLY。
- **Power**: 有効標本数 5.0。
- **book の欠陥**:
  - 凍結は USD 対 7 通貨 basket だった。band 0.10 の下では外国の脚（各 0.071）が売買されず、実際の book は **USD ±0.43 対 AUD / CAD / CHF 各 ∓0.14** になった。
  - 記録上の値は次のとおり（**欠陥のある book の数字**）。
    - net +0.080: spot +0.035% + carry +1.49% − spread 0.09% − financing 0.585%
    - null p 0.458
  - 設計どおりの book に当たる感度行（band 0.05）は net 0.102。**POST_HOC_EXPLORATORY で、verdict は付けない。**
- **Stage 2**: 実行していない。
- **5% / 10% capacity**: 現実的な risk の範囲外。
- **Verdict**: `INVALID_AS_A_TEST_OF_THE_FROZEN_MECHANISM_BOOK_CONSTRUCTION_DEFECT`。
- **経済的な読み**: 仮に book を度外視しても、spot に予測力は無く（spot のみの gross Sharpe 0.003）、net は carry と markup の仮定で決まる（net がゼロになる markup は約 0.61%/年）。

### M11 macro data momentum — POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE

- **Mechanism**: インフレの加速と失業率の低下が相対的に大きい国の通貨は上がる（Dahlquist–Hasseltoft）。
- **Why FX should lag**: macro は月次で少しずつ届き、注意が限られるため反応が遅れる（under-reaction）。
- **Data**: OECD の CPI 前年比（EUR は HICP 指数から作る）と調和失業率。**貿易収支は入れていない**（U1 の救済にしないため）。
- **Timing**: m+2 月末。GBP は m+3。四半期の series は +2 か月。
- **Revision**: CURRENT_VINTAGE_ONLY。
- **Sample / Power**: long 17.7 年、有効標本数 13.2、MDE 0.466。
- **Null**: percentile 0.781、p 0.220（null の p95 は 0.385）。
- **Stage 1**: 実行。
- **Stage 2**: 不適格（percentile < 0.80）。
- **Gross / Net**: 0.275 / **0.159**（年 +1.77%）。spot のみの net は 0.186、carry +0.56%、financing 0.86%。
- **Incremental information**: incIC +0.0085。
- **Turnover / Cost**: 3.6 RT/年、年 1.28%。
- **Stability**: 正のブロックは 40/70。
- **Breadth**: LOO の最悪は USD の −0.040 で、E5 は偽。
- **Concentration**: top10 が 0.854 で、E6 は偽。
- **DD**: −28.8%。
- **Cost stress**: ×1.5 で 0.102、×2 で 0.044。
- **Leverage / Margin**: 5% に必要なのは vol 31%・gross 9.8・DD −82%。10% は vol 63%。**現実的な risk の範囲外。**
- **頑健性**: change window 6 / 12 / 24 か月で net が −0.234 / +0.159 / +0.553 と**符号を跨ぐ**。recent（2.2 年）は −0.83。
- **Verdict**: POSITIVE_EXPLORATORY。failure は CONCENTRATION。

### M16 米国 vs 他国の macro momentum → ドル — **INVALID（book の欠陥）**

- **Mechanism**: M11 と同じ入力で、M11 の book が中立化して捨てていた USD 成分を測る。
- **book の欠陥**: M15 と同じ欠陥がある。
- **記録上の値**（欠陥のある book の数字）:
  - net +0.293、p 0.132、percentile 0.869、有効標本数 23.1
  - E1〜E7 は真、E8 は偽（0.293 < 0.30）
  - 凍結規則上は MARGINAL
- **設計どおりの感度行**（band 0.05）: net 0.279。**POST_HOC_EXPLORATORY。**
- **book を度外視しても、Sharpe 0.3 級の edge の証拠ではない。** 理由は次のとおり。
  - 5 本の最小 p が 0.132 以下になる確率は、帰無でも約 50%。
  - Stage 2 の signal t は 0.92（重複を補正していないので過大）。
  - E6 は余裕 0.003、E8 は不足 0.007 で、どちらも閾値すれすれ。markup を 0.22% にすれば E8 は通る。
  - recent（2.1 年）は net −0.15。
  - change window の感度で net は 0.09〜0.42。
  - 縮小推定での期待 Sharpe は 0.1 前後。
- **Verdict**: `INVALID_AS_A_TEST_OF_THE_FROZEN_MECHANISM_BOOK_CONSTRUCTION_DEFECT`（記録上の MARGINAL は履歴として残す）。

### M01 Taylor gap — POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE（検出力の上限）

- **Mechanism**: fundamentals が要求する政策金利と、実際の政策金利の差。
- **Why FX should lag**: 市場は観測できる金利差に錨を下ろす。
- **Data**: CPI・失業率・BIS の政策金利（SDMX、`detail=dataonly`）。
- **Timing**: 政策金利は m+1。
- **Revision**: 失業率は CURRENT_VINTAGE_ONLY。
- **Power**: 有効標本数 6.2 で、上限に掛かる。
- **Null**: percentile 0.803、p 0.198。
- **Stage 2**: 不適格（core のうち E4 が偽）。
- **Gross / Net**: 0.185 / **0.080**。
- **P&L の中身**: spot は +3.49%（spot のみの net 0.296）だが、**carry が −1.48%**（gap が −政策金利を含むので anti-carry になる）。
- **Incremental information**: incIC +0.0031。
- **Turnover / Cost**: 2.3 RT/年、年 1.14%。
- **Stability**: 正のブロックは 30/70。
- **Breadth**: USD 抜きの LOO は −0.149。
- **Concentration**: top10 が 173%。
- **DD**: −49%。
- **Cost stress**: ×2 で −0.024。
- **Capacity**: 5% に必要なのは vol 62%。範囲外。
- **Rename gate**: carry とは 0.321、M11 とは 0.352 で、どちらも DISTINCT。
- **Verdict**: POSITIVE_EXPLORATORY。failure は CONCENTRATION。有効標本数が 10 未満なので、**負の方向にも正の方向にも決められない**。

### M10 流動性 premium — NOT_SUPPORTED_IN_SEEN_DEVELOPMENT

- **Data**: seen の M15 cache の bid / ask。
- **Timing**: 翌営業日から使う。
- **Span**: recent のみ 3.8 年。
- **Power**: 有効標本数 0.5（過小推定）、MDE 1.00。
- **Null**: percentile 0.185、p 0.815。
- **Gross / Net**: −0.257 / **−0.450**。
- **Incremental information**: incIC −0.0087。
- **Cost**: 年 2.04%（financing 1.28% が spread 0.76% を上回る）。
- **Breadth**: LOO は全て負。
- **Rename gate**: vol ratio とは 0.109 で DISTINCT。
- **Verdict**: NOT_SUPPORTED。failure は **SIGNAL_FAILURE**。検出力の無い null であって refutation ではなく、family は閉じない。

---

## Cross-Track Comparison（primary、long は 17.7 年、M10 は recent 3.8 年）

| track | gross | net | spot のみ net | carry / 年 | turnover | cost / 年 | null pct | p | incIC | 有効標本 | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M15 | 0.144 | 0.080 | −0.005 | +1.49% | 1.1 | 0.67% | 0.543 | 0.458 | +0.011 | 5.0 | **INVALID（book）** |
| M11 | 0.275 | 0.159 | 0.186 | +0.56% | 3.6 | 1.28% | 0.781 | 0.220 | +0.009 | 13.2 | POSITIVE_EXPLORATORY |
| M16 | 0.364 | 0.293 | 0.366 | −0.19% | 2.1 | 0.76% | 0.869 | 0.132 | +0.005 | 23.1 | **INVALID（book）** |
| M01 | 0.185 | 0.080 | 0.296 | −1.48% | 2.3 | 1.14% | 0.803 | 0.198 | +0.003 | 6.2 | POSITIVE_EXPLORATORY（上限） |
| M10 | −0.257 | −0.450 | −0.306 | −0.25% | 4.2 | 2.04% | 0.185 | 0.815 | −0.009 | 0.5 | NOT_SUPPORTED |

- track 間の日次 net の相関は |ρ| ≤ 0.48。
- M11 と M01 は 0.30。入力を共有するためで、rename gate は DISTINCT。

## Null / Gate Findings

- 5 本とも p > 0.05。**null を超えた track は 0 本。**
- 5 本を同じ null に当てたので、1 本以上が 5% を切る確率は帰無でも 23%。最小 p（M16、無効）が 0.132 以下になる確率は約 50%。
- 凍結した gate は正しく当てられていた（Role 1 が記録から再計算して確認）。
- ただし、E6 と E8 の knife-edge が示すように、**閾値の近くでは仮定 1 つで判定が変わる**。
- 検出力の上限（有効標本数 10 未満）は M15 / M01 / M10 に掛かった。

## Positive Candidates

- **decision-grade / development candidate: 0 本**（M16 の MARGINAL は book の欠陥で無効）。
- **observed positive（非 decision-grade）**:
  - M11（net +0.159、頑健性なし）
  - M01（+0.080、上限・集中）
  - M15 / M16 の記録値（無効な book の数字）
  - M15 / M16 の band 0.05 の感度行（設計どおりの book、post-hoc）

## Negative Candidates

- **SIGNAL_FAILURE**: M10。
- **COST_FAILURE**: 無し。
- **CONCENTRATION**: M11・M01（正の net だが E5 / E6 が偽）。
- **IMPLEMENTATION_FAILURE**: M15 / M16（book 構成の欠陥）。

## Remaining Candidate Space

- **book を直したドル factor**: M15 / M16。**新しい事前登録**としてのみ扱う（判断事項 1）。
- **M14**（ドル funding stress）: ELIGIBLE だが、5 本の枠から外れた。
- **point-in-time vintage が要るもの**:
  - M18 CLI
  - M11 / M01 の失業率（季節調整の係数に保護期間が入っている）
- **request-level exclusion を保証できる経路が見つかれば**: M17 EPU。
- **有料**（下の表）。

## Paid-Data Opportunities（design-only、購入しない）

| 候補 | provider | 費用の桁（未確認） | 得られる情報 | 無料の代替 |
|---|---|---|---|---|
| M24 option risk reversal | Bloomberg / LSEG / CME | 年間 数百万円〜 | tail hedge 需要 | 無し |
| M25 OIS | Bloomberg / LSEG / ICE | 同上 | term premium を除いた政策期待 | 2 年金利（S01 で閉鎖） |
| M26 CME 先物の order flow | CME DataMine | 月 数万〜数十万円 | 約定方向・出来高 | 無し |
| M27 CLS flow | CLS | 年間 数百万円〜 | 実決済の flow | COT（閉鎖） |
| M12 予測分散 | Consensus / Bloomberg ECO | 年間 数十万〜数百万円 | 予測の不一致 | US の SPF のみ |

**今回の結果から、有料データが必要だという根拠は出ていない。** 足りなかったのはデータの種類ではなく、検出力と signal の質である。

---

## Engineering Findings（alpha 判定とは別）

1. **pre-alpha review は 5 回行い、そのたびに欠陥が見つかった。**
   - carry が spot の P&L に入っていなかった（M15 の mechanism そのものを測っていない）。
   - carry が pair book と一致しなかった。long で 12.5% の過小、recent で通貨ごとの歪み、JPY の欠損期間は 84% の過小。
   - GBP の 3 か月平均が保護暦日に掛かっていた。
   - 凍結の閉包に抜けがあった。
   - rename gate の比較対象が凍結文と食い違っていた。
2. **それでも実行後に book 構成の欠陥が見つかった。**
   - `band_rebalance` の同符号時の counter-leg 規則と、ドル track の小さな外国脚が相互作用した。
   - **return 無しの合成入力で book を 1 回走らせれば見えた**が、どの review も走らせていなかった。
   - 今後は、**凍結前に合成入力で book の exposure を確かめることを Stage 0 に入れる**べきである。
3. 凍結 digest は、コード閉包（driver から静的 import を辿った 32 file）と入力 manifest（外部 34 series + cache 104 file）を覆う。driver は記録・dirty・manifest の不一致があれば計算前に止まる。
4. D-5 policy を data_access に実装した。ALFRED が bound を無視する series が存在する（D-M2）ことが実証された。

## Protected Data Status

- **FX の fresh pool・historical OOS・dead window・forward epoch は読んでいない。**
  - FX の return は long が ECB 1999-01-04 … 2016-06-01、recent が 2021-04-27 … 2025-12-26。
  - cache の最大時刻は 2025-12-28 23:45（seen の開発 corpus 内）。
  - Role 2 が撹乱テストを 141 件行い、先読みは 0 件だった。
- **外部データの露出（すべて保存・計算に残っていない。開示は `acquisition_amendment.json` と `post_run.py`）**:
  - **D-M1**: ALFRED の metadata page 約 200 回で、2026 年の最新観測値がメモリで parse された。
  - **D-M2**: EPU の JPY 全系列の応答を parse し、標準偏差まで計算してから拒否した。
  - **D-M2b**: EPU の USD / EUR を保存したが、削除した。
  - **D-M3**: BIS の属性列にあった **2026 年の BoJ の政策決定の記述を lead が読んだ**。forward epoch の JPY 金利に関する知識として、将来の Formal Confirmation の汚染要因になる。
  - **CPI 前年比**: recent の 2021-05 … 2022-04 は分母が fresh pool で、保存されている。JPY は 2020 年の水準を逆算できる。
  - **HICP の基準年 2025=100**: 2025-12 の水準を推定できる。
  - **GBP 失業率**: 保護暦日に掛かる 6 つの stamp を保存している（読む側で落としている）。

---

## Final Answers

1. **net positive candidate はあったか？**
   - 有効な track では M11（+0.159）と M01（+0.080）の 2 本。どちらも decision-grade ではなく、M11 は頑健性が無く、M01 は検出力の上限に掛かっている。
   - M15 / M16 の正の値は book の欠陥のため無効。
2. **price information を超える incremental value はあったか？**
   - 実質的に無い。incIC は最大でも +0.011（無効の M15）。有効な track では +0.009 以下で、ゼロと区別できない。
3. **null を超えた candidate はあったか？**
   - **無い。** p ≤ 0.05 は 0 本。有効な track の最小 p は 0.198。
4. **年 5% net は現実的な risk で射程か？**
   - **無い。** 5% に必要な vol は M11 で 31%（DD −82%）、M01 で 62%。無効の M16 でさえ 17%（DD −69%）。
5. **年 10% net はどうか？**
   - **無い。**
6. **今回の最大の bottleneck は？**
   - **signal quality と検出力。**
   - 月次の macro や金利の signal は、17 年あっても有効標本数が 5〜23 個しかなく、Sharpe 0.3 級を 1 本では決められない。
   - 見えている正の値は閾値の上に乗っているだけで、仮定（financing markup・change window）で動く。
   - cost は主因ではない。financing の仮定は M15 の正負を決めうる。
7. **次に進むべきものは？**
   - **new mechanism ではなく、「測れる形の研究計画」への切り替え。** 具体的には次の 3 つ。
     - (a) ドル factor の book を直した**新しい事前登録**。M16 は設計どおりの book では一度も判定されていない。
     - (b) retail の financing（broker の swap 記録）を**実測**すること。carry が効く track の正負を決める。
     - (c) FX spot の単一 candidate では検出力の天井を越えられないことを前提に、**Formal Confirmation の forward epoch の使い方を設計すること**。
   - same candidate deepening（救済）・有料データ・nonlinear ML・multi-source optimization は勧めない。

---

## Human + ChatGPT Decisions Needed

1. **M15 / M16（ドル factor）を、book を直した新しい事前登録で測り直すか。**
   - 欠陥は book の実装にあり、mechanism は一度も設計どおりに測られていない。
   - ただし、M16 は結果を見た後であり、設計どおりの book に当たる感度行（M16 net 0.279）も既に見ている。
   - 測り直す場合は、**post-hoc であることを明記した新しい事前登録**になり、confirmation の証拠には数えられない。
2. **保護暦日への露出の扱い。**
   - D-M1 / D-M3 の metadata 経由の露出があった。特に D-M3 では、lead が forward epoch の BoJ 政策決定を読んでいる。
   - CPI 前年比・HICP の基準年・GBP 3 か月平均の保存もある。
   - 決めてほしいこと: 次の取得で「metadata / 属性 / 基準年を含めて、保護期間の情報を含む応答を受けない」ところまで request-level exclusion を拡げるか。JPY の金利を使う track の将来の Formal Confirmation を、この知識のもとでどう扱うか。
3. **本 PR（mechanism redesign・4 回の pre-alpha amendment・1 回の実行・無効化の記録・本報告）の merge 可否**（Amber）。
