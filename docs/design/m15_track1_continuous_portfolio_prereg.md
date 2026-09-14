# Track 1 — Continuous Currency Portfolio 事前登録

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

正本は `scripts/research/continuous_portfolio/prereg.py`。本文書はその写しで、
凍結は **specification の canonical JSON + 判定が読む数値を計算する全モジュールの
正規化済みソース**に対する SHA-256 で行う（`FROZEN_HASH`）。`development.run()` は
最初の行で `assert_frozen()` を呼び、不一致なら 1 バイトも読まずに止まる。
凍結値は**レビュー修正が終わった直後・実行の直前**に記録する。

**凍結: `FROZEN_HASH = aa0888089e4dcf5988bc6b734bb8e036262ed5c2efe4755d59fd9244176c85f1`**
（2026-09-14、commit `4a60fbe` の内容に対して計測、CRLF export でも同値。development の読み取りは未実施。
artifact: `artifacts/research/continuous_portfolio/prereg.json`）。

権限: Human + ChatGPT 裁定（2026-09-14）— Track 1 core + efficiency bundle の
prereg・実装・seen-data development 実行。**未承認**: Track 3 overlay、fresh pool、
historical OOS、dead window、future confirmation epoch、broker 認証アクセス、
paper-forward、demo/live、非線形モデル。

---

## 1. 研究問い

8 通貨の relative expected return を継続的に推定し、factor-neutral な通貨ポートフォリオ
として保有し、**target weight との差分だけ**を低 turnover で rebalance することで、
G10 FX spot において **cost 後に意味のある年間収益 / Sharpe** を作れるか。

`one signal = one trade` でも `one prediction = one round trip` でもない。
経済量は **実現 portfolio turnover × 約定可能コスト**、成功単位は
**primary book 自身の portfolio-level net Sharpe と年間収益**（baseline に対する増分ではない）。

## 2. Architecture

```
features (currency state)  →  ridge expected relative return μ (8,)
  →  vol-normalized scores μ/σ  →  trailing leading-factor neutralization
  →  capped sum-zero target weights (gross 1, |w_c| ≤ 0.25)
  →  no-trade band 0.10（sum-zero 保持、同符号 breach のみなら counter-leg）
  →  ex-ante vol target 10%（leverage ≤ 5×、hysteresis 10%）
  →  traded delta x_t − x_{t−1} のみ  →  cost = Σ|Δ| × 1.703 bp
  →  P&L = x_t · r_{t+1}（翌日のリターンのみ）
```

⭐ **cap 0.25 と gross 1 は target にかかる**。保有 book は両方を超えうる — **band の分とは限らない**
（sum-zero 復元で counter-leg が自分の target を行き過ぎ、gross の超過は通貨をまたいで累積する。
Role 2 再監査の反例: |w| = 0.45 > cap + band 0.35。合成 40 年で gross 最大 1.35）。
上限は主張せず、実現した最大 weight・gross>1 の日比率を報告する。

## 3. ⭐ H-003 / C08 novelty boundary（実行前に明示）

**H-003**（Round 1 role G）: pair-level relative strength。gross の 96% が通貨 exposure、
matched time-series control に負けた。**C08**（inventory）: currency-level の
**rank persistence**（「強い通貨は強いまま」）を H-003 同形 family として閉鎖。

Track 1 の差異（すべてコードの性質）:

1. **予測単位**: 8 通貨の連続 expected-return vector。pair は執行にのみ現れる。
2. **共通 exposure は構成で処理**: 重みは sum-zero なので等加重バスケットは P&L から
   恒等的に消え、さらに通貨断面の trailing leading factor を**重みを作る前に**
   score から射影除去する。H-003 の失敗は「知らなかった exposure」だったが、本 book は
   事前に除去し、事後に残差を測る。
3. **仮説は条件付き推定であって persistence ではない**: 3 horizon の強さは 7 入力中の 3 つで、
   ridge は 0 や負の重みも付けられる。**C08 形の unfitted rule は Baseline 1 として
   persistence と reversal の両符号で走らせ、primary が良い方を明確に上回らなければ kill**
   （`does_not_beat_the_unfitted_benchmark`）— 閉鎖 family も、その符号反転も、再現するだけの
   primary はその family そのものだから。
4. **連続重み + 部分 rebalance** が binary top/bottom 選択を置き換え、book は entry/exit では
   なく target の差分を売買する。

⭐ レビュー（Role 1 BLOCKER）: 初稿の Baseline 1 は正符号だけで、60 日 z に負の係数を学習した
合成 reversal book が、符号反転 B1（Sharpe 2.32）に負けたまま Case A（1.46 vs 正符号 B1 −2.87）
になった。ridge が内部で「符号反転」をやれてしまい、結果後禁止の「sign flip」を素通りする。

## 3a. ⭐ この corpus への先行曝露（実行前の開示）

設計はこの corpus に対して盲目ではない。**#479 Track A** は同じ seen corpus で pooled ridge を
7 特徴で学習し（うち 6 つが本 book と同じ: excess return 5/20/60d z、realised vol 20d z、
dispersion share 20d z、beta to common factor 60d。残り 1 つは beta to risk factor 60d）、
宣言 df 4.2・**1 日** target で fold ごとの係数を出力した。Track B は trend age を使った。
#479 の 3 track はすべて development gate で不合格。その結果が見えた**後で**、本設計は
risk-factor beta を外し、trend age を加え、target を 5 日に、df を 3.0 にした。各変更には
architecture 上の理由があり、どれも out-of-fold 経済量の比較で選んでいないが、選んだのは
#479 の出力を見たセッションである。したがって本 run は**データの意味でも特徴選択の意味でも**
`EXPLORATORY_SEEN_DATA`。

## 4. Data

seen 連続 corpus `2021-04-26 … 2025-12-28`（`EXPLORATORY_SEEN_DATA`、3 つの guarded route
経由のみ）。daily 通貨 excess return（PAIRS_20 の signed pair return の通貨平均を断面 demean）。
usable days `2021-07-19 … 2025-12-26`（1,154 日、欠損なし・連続。日付のみ確認、リターン・fit なし）。

その他の読み取り（すべて宣言）:

* `features.build` は本 book が使わない H1 特徴のために 20 ペアの H1 を同じ guarded route で
  読み、`artifacts/track_a_scratch/exogenous/s1_calendar.json`（中銀会合カレンダー）も読む。
* carry 診断用に公開 BIS 政策金利 parquet を読む。FX データではない。1 row group なので
  span 外の行も decode されてから捨てられる。**EUR は amendment A-1 に従い deposit facility**
  （2024-09-18 以前は BIS 値 − 0.50、`economic_edge/rates.py` の実測差 +0.500）。

## 5. Protected data

fresh pool `2016-06-02 … 2021-04-25` / dead window / forward epoch — **never read**。
historical OOS slice — 既存の境界事故記録（one decoded row per pair）を尊重し**研究利用しない**。
`assert_not_protected` が `PROTECTED_SPANS` から境界を取る。

## 6. Model

| 項目 | 固定値 |
| --- | --- |
| class | pooled ridge over (day, currency) rows |
| features（7、5 family） | excess return 5d/20d/60d z（multi-horizon・currency-relative）、trend age（persistence）、realised vol 20d z（vol state）、dispersion share 20d z（dispersion）、leave-one-out beta to common factor 60d（correlation/factor） |
| target | **forward 5-day 累積通貨 excess return**（absolute direction ではない） |
| capacity | 各 fold 内で ridge penalty を **実効自由度 3.0** に解く（宣言値、チューニングなし） |
| 標準化 | 学習 fold のみ |

horizon 5 日は sweep ではなく architecture から: band で保持される book は数日持続する
情報を必要とし、1 日 label は最も雑音の大きい量で数日保有する position を学習させる。
**P&L は保有 book の日次で測るので Sharpe に重複リターンは入らない** — 重複するのは
学習 label だけで、fold の purge が除く。

## 7. Walk-forward

expanding window、初期学習 1.5 年、step 0.5 年、**purge 5 日 + embargo 1 日**、random split なし。
各 test 日はそれより前に学習した 1 つの fold のモデルだけで予測される。

実 corpus の fold 幾何（日付のみ）: 6 fold、test 日数 130 / 130 / 130 / 130 / 130 / 114、
最初の test 日 `2023-01-17`。**test 60 日未満の fold は報告するが正の fold 比率には数えない**
（宣言。現在の幾何では該当なし）。

## 8. Portfolio mapping（primary 固定 + 診断 2）

| | mapping |
| --- | --- |
| **primary** | **vol-normalized**: `μ_c / σ_c`（σ は trailing 60 日）、demean |
| 診断 | linear score `μ`、rank-normalized |

## 9. Factor neutralization

trailing 120 日の通貨 excess return 共分散の第 1 主成分（demean・単位長）を score から
射影除去。**target** 重み cap `|w_c| ≤ 0.25`、sum-zero、gross ≤ 1（保有 book は超えうる、上限は主張しない）。
**情報損失の診断**: raw score と neutralized score の日次相関、両者の rank IC、
neutralization を外した book（`diag_no_factor_neutralisation`）。
**残差の事後測定**（保有 exposure で毎日）: 第 1 主成分との |cos|、factor loading × factor
return の P&L とその gross 占有率。cap と band を通ると直交性は崩れるので、除去したことではなく
残ったものを測る。

## 10. Efficiency bundle

| 要素 | 固定値 | 根拠 |
| --- | --- | --- |
| **no-trade band** | **0.10**（per-currency、sum-zero 保持、同符号 breach のみなら counter-leg） | 下表の signal-free 較正 |
| band 診断 | none、0.15（**最大 3**） | |
| vol target | ex-ante 10%、trailing 60 日共分散（past-only） | risk normalization であって alpha ではない |
| leverage | 上限 5×、hysteresis 10%（変化が 10% を超えた時だけ更新） | |
| DD governor | **deployment 診断のみ**: DD > 10% で exposure 半減、DD > −5% へ回復で解除 | primary には入れない |

### Signal-free band 較正（20 日半減期 AR(1) 合成 target、`construction.band_calibration`）

| band | turnover（正規化 target） | capture（正規化 target） | turnover（cap 0.25 target） | capture（cap 0.25 target） |
| --- | --- | --- | --- | --- |
| 0 | 34.17 | 1.0000 | 32.91 | 1.0000 |
| 0.05 | 23.31 | 0.9898 | 22.96 | 0.9792 |
| 0.08 | 18.33 | 0.9734 | 18.08 | 0.9575 |
| **0.10** | **15.85** | **0.9610** | **15.70** | **0.9377** |
| 0.15 | 11.47 | 0.9177 | 11.29 | 0.8858 |

band 0.10 は #480 の動作点（capture 0.958、cap なし）を正規化 target で再現する。primary の
cap 付き写像では capture は **0.938** に下がる（Role 1 観察 O-2 — band の選択根拠は cap なし較正
だったことを開示）。vol target の leverage 変動による売買は較正に入らない。
**市場データも signal も一切入っていない**。

## 11. ⭐ Cost model — 差分にのみ課金

```
3.406 bp = 2.58（Track 3 実測 pair 往復）× 1.32（Track 2 実測、孤立 basket position の routing）
課金 = Σ_c |x_t − x_{t−1}| × 1.703 bp（= turnover 1 単位 Σ|Δ|/2 あたり 3.406 bp）
```

* ⭐ **課金の大きさの正確な記述**（Role 1 R-3）: 1.32 は Track 2 の「1 通貨 対 残り 7 通貨」の
  孤立 position で、**片側 1 単位あたり**の pair notional。課金はそれを**両側**の Σ|Δ| に掛けるので、
  孤立 position に対しては Track 2 の実測 routing の**約 2 倍**（開くだけで 3.406 bp、pair book の
  実費は 1.703 bp）、ランダムな sum-zero trade では faithful cost の**約 1.7 倍**。#480 から継承した
  規約で、保守側にしか働かない（book を良く見せることはできない）。判定はこの課金で行い、
  faithful cost での net Sharpe を並べて報告する。
* **課金しないもの**: prediction ごと、signal ごと、pair ごとの独立 round trip、変化のない
  position の close/reopen。
* **faithful cost**（equal-split pair book の片道 notional × pair 往復の半分）を横に報告し、
  判定には使わない（保守側の課金のみで判定）。
* stress ×1.5、×2（**同じ position**、コストだけ変える）。
* **financing は P&L から除外**し、政策金利 carry accrual を診断として報告。

報告単位: pair-level cost、routing multiplier、traded gross notional、annual turnover、
annual cost drag、stressed cost、cost per unit capital、cost per unit gross exposure。

## 12. Baselines

| | 定義 |
| --- | --- |
| **B0** | cash（net ≡ 0） |
| **B1** | unfitted persistence: 60 日 excess return z をそのまま μ として **primary と同じ構成 + bundle** に通す（C08 形）。**符号反転版（reversal）も同じ構成で走らせ、判定は良い方を読む** |
| unfitted rules | 同じ rule を 5 日・20 日 z でも両符号で走らせる（計 6 book、60 日の 2 つが B1）。primary と日次 net P&L の相関を測る |
| **B2** | primary の fitted μ を linear 重み・neutralization なし・cap なし・毎日 full rebalance・vol target なし |
| **Primary** | §2 |

## 13. 指標

prediction 日数 / 予測数 / position update 日数 / 通貨片道 notional/年 / RT/年（capital と
単位 gross あたり）/ 平均 currency gross・pair gross notional / 投資日比率 / leverage 平均・p95 /
gross・cost・faithful cost・net 年率 / 実現 vol / gross・net Sharpe（**実測 trading days/年で年率化**）/
max DD / fold 別 net Sharpe と正の fold 比率 / 通貨別 gross P&L、最大通貨の正 P&L 占有率、
最大通貨を除いた gross P&L、USD・JPY 占有率 / **top 1・5・10 日の net 占有率**、上位 5 日を
除いた net / 分散 regime 別 net / raw→neutralized score 相関 / rank IC（1d・5d、診断のみ）/
vol scenario 8・10・12%（**実際にその vol target で走らせた book** — 10% book の比例拡大ではない。
比例拡大は leverage 上限 5× を無視し、「12%」行の実現 vol が 9.8%・平均 leverage 6.0 になった）/
target が leverage 上限以上を要求した日比率・上限なしで必要な leverage・実現 vol / target / 保有 book の最大
weight と gross>1 の日比率 / factor 残差（|cos|、factor P&L 合計と gross>0 のときの占有率）/
unfitted rule 6 本の net Sharpe と primary との日次 P&L 相関 / 上位 2 通貨を除いた gross、
USD leg を除いた gross / carry accrual（EUR は deposit facility）/ 5 日 IC の t は重複しない 5 日おき。

## 14. Adjudication（primary の base cost のみを読む）

### Kill（どれか 1 つで Case C）

1. net Sharpe ≤ 0
2. net Sharpe < 0.20（年率収益が経済的に無視できる）
3. **各日を median ± 3 robust σ（1.4826 × MAD）に clip した日次 net の平均 ≤ 0、または測定不能**（利益が極端な日にしかない）
4. 最大通貨を除くと gross ≤ 0（単一通貨支配）
5. 正の fold が半数未満（test 60 日未満の fold は数えない）
6. **primary net Sharpe ≤ max(B1 persistence, B1 reversal) の net Sharpe**（unfitted の閉鎖 family 形を、どちらの符号でも超えない）
7. **どの horizon・符号でも、primary と日次 net P&L の相関 ≥ 0.5 の unfitted rule が primary 以上の
   net Sharpe**（fit が、似ている単一の unfitted rule に何も足していない）
8. turnover > 50 RT/年（単位 gross あたり）
9. **10% vol target で target が leverage 5× 以上を要求する日が半数超**（上限なしの要求で数える）

⭐ 7 の理由（Role 1 再監査 N-4）: 60 日 B1 だけでは、持続的な逆張り信号を 5 日 z に埋め込んだ
合成 book が B1（−0.16 / −0.29）を相手に Case A（1.48）になった — CLAUDE.md で dropped の
multi-day reversal family に近い形。**報告義務**: 相関 0.7 以上の unfitted rule があれば、case に
かかわらず最終報告で「primary はその rule に似ている」と明記する。

⭐ 9 の理由: 初稿の「平均 leverage > 5×」は上限 = 閾値で発火せず（Role 1 R-2）、次の「保有 leverage が
上限にある日」は hysteresis で回避できた（Role 1 N-2: 保有 4.545 のまま要求 25、張り付き 0/405 日）。

### Case A — `CONTINUOUS_CURRENCY_PORTFOLIO_DEVELOPMENT_CANDIDATE`

kill なし、かつ net Sharpe ≥ 0.5、正の fold が過半、どの通貨も正 P&L の半分以下、
×1.5 コストで net Sharpe > 0、**上位 2 通貨を除いた gross > 0**、**USD leg を除いた gross > 0**。

### Case B — `MARGINAL_CONTINUOUS_PORTFOLIO_CANDIDATE`

kill なし、かつ net Sharpe ≥ 0.3、正の fold が過半、どの通貨も正 P&L の半分以下、
**上位 2 通貨を除いた gross > 0**、**USD leg を除いた gross > 0**。

⭐ **top 1/5/10 日占有率は報告のみで判定に入れない**（Role 1 再監査 N-1 BLOCKER）。初稿は
「top 10 日 ≤ net の半分」を A/B 両方に置いていたが、約 850 日では普通の 10 日だけで約 26 日次
標準偏差、net 合計は約 52.5 × Sharpe 日次標準偏差なので、**tail の形にかかわらず実現 Sharpe ≈ 1.0 を
要求**していた（合成 MC で Case B 到達 0/150）。裁定の経済 band（0.30–0.50 marginal）を判定規則が
黙って 1.0 に引き上げていたことになる。

⭐ **kill 3 も同じ理由で置き換えた**（Role 1 最終再検証 REQUIRED FIX）。「上位 5 日を除くと net ≤ 0」は
上位 5 日が約 14 日次標準偏差あるため、**裾が厚いと実現 Sharpe 0.3〜0.4 の book を約半数 kill** した。
いったん「両側 1% winsorize 平均 ≤ 0」に置き換えたが、Role 1 の次の再検証で**外れ日が 1%（850 日で
約 8.5 日）を超える lottery を一切捕まえない**ことが示された（外れ日 13 日・普通の日は年率 −5.15% の book が
Case A まで通った）。個数・分位点で切る規則は、その個数より広い lottery に盲目になる。そこで
**σ 単位で切る**: 各日を median ± 3 robust σ に clip した平均で判定する。

合成 iid 850 日、各 6,000 回 × 2 真値（`tail_kill_mc2`）での発火率（実現 SR 0.3–0.5 / 0.5–0.8）:

| 日次 net の形 | 旧: 上位 5 日除外 | 1% winsorize | **採用: 3 robust σ clip** |
| --- | --- | --- | --- |
| 正規 | 0.001 / 0.000 | 0.000 / 0.000 | **0.000 / 0.000** |
| t6 | 0.19–0.23 / 0.000 | 0.000 / 0.000 | **0.000 / 0.000** |
| Laplace | 0.28–0.32 / 0.000 | 0.000 / 0.000 | **0.000–0.001 / 0.000** |
| t4 | 0.44–0.49 / 0.01–0.02 | 0.000–0.003 / 0.000 | **0.003–0.005 / 0.000** |
| t3 | 0.65–0.71 / 0.06–0.09 | 0.007–0.015 / 0.000–0.001 | **0.008–0.024 / 0.000–0.001** |
| 歪度 +0.5 / +1 | 0.13 / 0.38–0.42 | 0.000 / 0.000 | **0.000 / 0.006–0.028** |
| **歪度 +2** | 0.82–0.86 / 0.04 | 0.000 / 0.000 | **1.000 / 0.94–0.96** |
| 歪度 −1 | 0.000 | 0.000 | **0.000** |
| lottery 外れ 6 日（15σ） | 1.000 / 1.000 | 1.000 / 0.999 | **1.000 / 1.000** |
| lottery 外れ 10 日（8σ） | 1.000 / 0.41–0.47 | **0.001 / 0.000** | **1.000 / 0.69–0.72** |
| lottery 外れ 13 日（8σ） | 1.000 / 0.34–0.40 | **0.000 / 0.000** | **1.000 / 0.99** |
| lottery 外れ 17・25 日（8σ） | 0.99–1.00 / 0.06–0.29 | **0.000** | **1.000 / 1.000** |
| lottery 外れ 40 日（6σ） | 0.63–0.65 / 0.000 | 0.000 | **1.000 / 1.000** |
| lottery 外れ 40・80 日（4σ） | 0.18–0.46 / 0.000 | 0.000 | **0.86–0.98 / 0.14–0.58** |

**採用規則の既知の性質（開示）**:

* 対称な厚い裾（t3 まで）は罰しない。
* **歪度で急に立ち上がる**: |skew| ≲ 1 では発火率 ≤ 0.03、**歪度 +1.41 で約 0.5**、+2 で ≈ 1.0
  （その利益は 3σ を超える日に実際にある）。FX の日次 portfolio P&L で現実的な歪度は |skew| ≲ 1。
* ⭐ **Sharpe の高い lottery は通る**（Role 1 最終再検証）。clip は外れ日を捨てずに +3σ として数えるので、
  外れ日が多いほど「貸し」が付く。実現 SR 0.8–1.2 帯での kill 率: 13 日 × 8σ **0.19**、17 日 × 8σ 0.68、
  25 日 × 6σ 0.43、40 日 × 4σ **0.001**（いずれも普通の日は赤字）。Role 1 の再現例（外れ 13 日、普通の
  837 日は年率 −5.15%、net Sharpe 0.98）は **この kill では Case A に届く**。外れ日を捨てる trim にすると
  lottery はすべて捕まるが、歪度 +1 の健全な book を SR 0.3–0.5 / 0.5–0.8 / 0.8–1.2 で 0.99 / 0.88 / 0.50
  kill するため採らなかった。**この見逃しを受け入れるかは Human + ChatGPT の判断事項**として記録する。
  結果報告では、Case にかかわらず top 1/5/10 日占有率・上位 5 日除外 net・clip 後年率・普通の日（±3σ 内）の
  年率・**日次歪度と超過尖度**を並べ、primary が Case A/B なら lottery 形でないことを数値で示す義務を負う
  （普通の日の年率は健全な歪度 +1 の book でも負になりがちなので、歪度と併せて読む）。
* scale（MAD）が小さい・測れない book は kill 側に倒れる（P&L がちょうど 0 の日が 50% で約 0.57）。
  primary は vol target 付きの連続保有 book で、ほぼ常に invested。
* 上位 5 日を除いた net と top 1/5/10 日占有率は報告する。

**判定規則の到達可能性（合成 MC、全通貨に等しい持続情報を持つ book、各 100 seed、正規ノイズ）**:
実現 Sharpe 0.3〜1.0 の run で kill 発火 0、Case B 到達 8/100（両強度）。
**「上位 2 通貨を除いた gross > 0」は、他の B 条件をすべて満たす分散 book の 4/29・3/32（約 11〜14%）を
落とす**（USD 条件は 0。Role 1 の独立再実行では 0〜8%）。1 ペア集中を検出するための代金として事前に
受け入れ、ここに開示する。

**kill 7（似ている unfitted rule）の既知の限界（Role 1 最終再検証、開示）**:
(a) 本物の分散 book でも誤発火しうる — 独立な edge を 2 つ持つ primary に対し、片方だけを知る unfitted
rule との相関は平均 0.62 で、合成 57 run 中 12（約 21%）で kill が発火した（約 3 年で √2 の Sharpe 比を
検出できない検出力の限界）。(b) 回避されうる — 手で情報のない傾きを足した μ では相関 0.40 で rule
（Sharpe 2.19）に負ける primary（1.23）が Case A になった（df 3.0 の ridge が自然にこうなる経路は未提示）。
閾値 0.5 は結果前の宣言値で、結果後に変更しない。

⭐ 追加 2 条件の理由（Role 1 R-4）: sum-zero book では 1 通貨を除いても同じペアの反対 leg の
P&L が残る。USD/JPY だけの賭けは最大通貨占有率が**ちょうど 0.5** で「≤ 0.5」を通り、
「最大通貨を除いた gross」も正のまま — 単一通貨条項は 1 ペア賭けに構造的に盲目だった。

### Case C — `CONTINUOUS_CURRENCY_PORTFOLIO_ARCHITECTURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`

それ以外。`FX_HAS_NO_EDGE` とは言わない。

**経済 band**（資本配分の解釈、p 値 gate ではない）: <0.30 weak / 0.30–0.50 marginal /
0.50–0.80 potentially useful / >0.80 strong。
**負の baseline に対する増分は、それ単独では決して生存理由にならない**（テストで固定）。

## 15. Search budget（事前凍結）

feature set 1（7 features）/ model class 1 / horizon 1 / primary mapping 1 + 診断 2 /
primary band 1 + 診断 2 / fitted model 1 / baseline 3（B1 は 2 符号）/ unfitted rule book 6（B1 を含む）/ 診断 book 11
（unlevered、vol target 8%・12%、mapping 2、band 2、neutralization なし、cost ×1.5・×2、DD governor）/
**ハイパーパラメータ探索なし**（penalty は宣言 df に解く）/ **診断からの選択は禁止**
（判定は primary のみ）/ AutoML なし。

## 16. 結果後に禁止

feature 追加 / horizon 変更 / 符号反転 / 通貨除外 / band 最適化 / leverage・vol target 最適化 /
regime filter 追加 / 非線形モデル追加 / 保護 span の目的を問わない読み取り。

## 16a. 凍結と実行の束縛

凍結 hash が見るもの: specification 全体（本文書の数値すべて）+ `continuous_portfolio` の計算
モジュール 5 つ + `model_learning` の features / corpus / walkforward / `__init__`（保護 span 境界）+
`exploratory_m15` の `__init__` と 3 route + `feasibility` の inventory / preflight（コスト定数）の正規化済みソース。

`driver develop`（正式な実行経路）:

1. `development.started.json` か `development.json` が既にあれば止まる（**実行は 1 回**。marker 後に
   失敗した run は記録された事象であって、無料の再試行ではない）。
2. hash 対象・prereg・driver の**内容**を `git show HEAD:` と比較し、差があれば止まる
   （`git status` ではないので `assume-unchanged` でも隠せない。パスは repo root 基準で cwd に依存しない）。
3. `assert_frozen()` の後、**読む前に** start marker（時刻・commit・凍結 hash）を書く。
4. `development.run()` は fit の前に usable days の連続性を確認する。

hash が見ないもの（開示）: ライブラリのバージョン、キャッシュの中身。`development.run()` を driver
を経ずに直接呼べば 1〜3 は働かない（`assert_frozen` は働く）。marker は排他作成（同時起動の片方は止まる）だが
**この checkout の中でしか効かない**（別 worktree / clone には marker が無い）。checkout 比較はディスク上の
ファイルを見るので、同一プロセス内でロード済み関数を差し替えれば通る。いずれも自分で仕込まない限り起きない
経路で、実行記録（commit・凍結 hash・開始時刻）は PR B に commit される。

## 17. 停止規則

Case A/B/C のどれでも**停止**して Human + ChatGPT へ返す。fresh・Track 3・複雑 ML・
paper-forward へは自動で進まない。
