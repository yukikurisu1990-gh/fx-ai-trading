# Track 1 — Continuous Currency Portfolio 事前登録

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

正本は `scripts/research/continuous_portfolio/prereg.py`。本文書はその写しで、
凍結は **specification の canonical JSON + 判定が読む数値を計算する全モジュールの
正規化済みソース**に対する SHA-256 で行う（`FROZEN_HASH`）。`development.run()` は
最初の行で `assert_frozen()` を呼び、不一致なら 1 バイトも読まずに止まる。
凍結値は**レビュー修正が終わった直後・実行の直前**に記録する。

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
  →  capped sum-zero weights (gross 1, |w_c| ≤ 0.25)
  →  no-trade band 0.10（sum-zero 保持、単独 breach には counter-leg）
  →  ex-ante vol target 10%（leverage ≤ 5×、hysteresis 10%）
  →  traded delta x_t − x_{t−1} のみ  →  cost = Σ|Δ| × 1.703 bp
  →  P&L = x_t · r_{t+1}（翌日のリターンのみ）
```

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
   ridge は 0 や負の重みも付けられる。**C08 形の unfitted persistence は Baseline 1 として
   走らせ、primary が明確に上回らなければ kill**（`does_not_beat_the_unfitted_benchmark`）—
   閉鎖 family を再現するだけの primary は閉鎖 family そのものだから。
4. **連続重み + 部分 rebalance** が binary top/bottom 選択を置き換え、book は entry/exit では
   なく target の差分を売買する。

## 4. Data

seen 連続 corpus `2021-04-26 … 2025-12-28`（`EXPLORATORY_SEEN_DATA`、3 つの guarded route
経由のみ）。daily 通貨 excess return（PAIRS_20 の signed pair return の通貨平均を断面 demean）。
診断用に公開 BIS 政策金利を corpus span に**フィルタして**読む（carry accrual 診断のみ）。

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

## 8. Portfolio mapping（primary 固定 + 診断 2）

| | mapping |
| --- | --- |
| **primary** | **vol-normalized**: `μ_c / σ_c`（σ は trailing 60 日）、demean |
| 診断 | linear score `μ`、rank-normalized |

## 9. Factor neutralization

trailing 120 日の通貨 excess return 共分散の第 1 主成分（demean・単位長）を score から
射影除去。重み cap `|w_c| ≤ 0.25`（USD・JPY を含む単一通貨集中の上限）、sum-zero、gross ≤ 1。
**情報損失の診断**: raw score と neutralized score の日次相関、両者の rank IC、
neutralization を外した book（`diag_no_factor_neutralisation`）。

## 10. Efficiency bundle

| 要素 | 固定値 | 根拠 |
| --- | --- | --- |
| **no-trade band** | **0.10**（per-currency、sum-zero 保持、単独 breach に counter-leg） | 下表の signal-free 較正 |
| band 診断 | none、0.15（**最大 3**） | |
| vol target | ex-ante 10%、trailing 60 日共分散（past-only） | risk normalization であって alpha ではない |
| leverage | 上限 5×、hysteresis 10%（変化が 10% を超えた時だけ更新） | |
| DD governor | **deployment 診断のみ**: DD > 10% で exposure 半減、DD > −5% へ回復で解除 | primary には入れない |

### Signal-free band 較正（20 日半減期 AR(1) 合成 target、`construction.band_calibration`）

| band | 年間 turnover | alpha capture |
| --- | --- | --- |
| 0 | 34.17 | 1.0000 |
| 0.05 | 23.15 | 0.9888 |
| 0.08 | 18.08 | 0.9708 |
| **0.10** | **15.69** | **0.9576** |
| 0.15 | 11.27 | 0.9131 |

sum-zero 制約と counter-leg 規則を入れた実装可能版の band 0.10 が、#480 の動作点
（capture 0.958）を再現する。**市場データも signal も一切入っていない**。

## 11. ⭐ Cost model — 差分にのみ課金

```
3.406 bp = 2.58（Track 3 実測 pair 往復）× 1.32（Track 2 実測、孤立 basket position の routing）
課金 = Σ_c |x_t − x_{t−1}| × 1.703 bp（= turnover 1 単位 Σ|Δ|/2 あたり 3.406 bp）
```

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
| **B1** | unfitted persistence: 60 日 excess return z をそのまま μ として **primary と同じ構成 + bundle** に通す（C08 形） |
| **B2** | primary の fitted μ を linear 重み・neutralization なし・cap なし・毎日 full rebalance・vol target なし |
| **Primary** | §2 |

## 13. 指標

prediction 日数 / 予測数 / position update 日数 / 通貨片道 notional/年 / RT/年（capital と
単位 gross あたり）/ 平均 currency gross・pair gross notional / 投資日比率 / leverage 平均・p95 /
gross・cost・faithful cost・net 年率 / 実現 vol / gross・net Sharpe（**実測 trading days/年で年率化**）/
max DD / fold 別 net Sharpe と正の fold 比率 / 通貨別 gross P&L、最大通貨の正 P&L 占有率、
最大通貨を除いた gross P&L、USD・JPY 占有率 / **top 1・5・10 日の net 占有率**、上位 5 日を
除いた net / 分散 regime 別 net / raw→neutralized score 相関 / rank IC（1d・5d、診断のみ）/
vol scenario 8・10・12%（return・vol・DD・leverage を比例、Sharpe 不変）/ carry accrual。

## 14. Adjudication（primary の base cost のみを読む）

### Kill（どれか 1 つで Case C）

1. net Sharpe ≤ 0
2. net Sharpe < 0.20（年率収益が経済的に無視できる）
3. 上位 5 日を除くと net ≤ 0（極端な tail 依存）
4. 最大通貨を除くと gross ≤ 0（単一通貨支配）
5. 正の fold が半数未満
6. **primary net Sharpe ≤ B1 net Sharpe**（unfitted の閉鎖 family 形を超えない）
7. turnover > 50 RT/年（単位 gross あたり）
8. 平均 leverage > 5×（10% vol target で）

### Case A — `CONTINUOUS_CURRENCY_PORTFOLIO_DEVELOPMENT_CANDIDATE`

kill なし、かつ net Sharpe ≥ 0.5、正の fold が過半、どの通貨も正 P&L の半分以下、
top 10 日 ≤ net の半分、×1.5 コストで net Sharpe > 0。

### Case B — `MARGINAL_CONTINUOUS_PORTFOLIO_CANDIDATE`

kill なし、かつ net Sharpe ≥ 0.3、正の fold が過半、どの通貨も正 P&L の半分以下、
top 10 日 ≤ net の半分。

### Case C — `CONTINUOUS_CURRENCY_PORTFOLIO_ARCHITECTURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`

それ以外。`FX_HAS_NO_EDGE` とは言わない。

**経済 band**（資本配分の解釈、p 値 gate ではない）: <0.30 weak / 0.30–0.50 marginal /
0.50–0.80 potentially useful / >0.80 strong。
**負の baseline に対する増分は、それ単独では決して生存理由にならない**（テストで固定）。

## 15. Search budget（事前凍結）

feature set 1（7 features）/ model class 1 / horizon 1 / primary mapping 1 + 診断 2 /
primary band 1 + 診断 2 / fitted model 1 / baseline 3 / 診断 book 9 /
**ハイパーパラメータ探索なし**（penalty は宣言 df に解く）/ **診断からの選択は禁止**
（判定は primary のみ）/ AutoML なし。

## 16. 結果後に禁止

feature 追加 / horizon 変更 / 符号反転 / 通貨除外 / band 最適化 / leverage・vol target 最適化 /
regime filter 追加 / 非線形モデル追加 / 保護 span の目的を問わない読み取り。

## 17. 停止規則

Case A/B/C のどれでも**停止**して Human + ChatGPT へ返す。fresh・Track 3・複雑 ML・
paper-forward へは自動で進まない。
