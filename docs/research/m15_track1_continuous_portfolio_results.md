# Track 1 — Continuous Currency Portfolio 開発実行結果

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED` · `EXPLORATORY_SEEN_DATA`

## 結論

**`CONTINUOUS_CURRENCY_PORTFOLIO_ARCHITECTURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`（Case C）。**

事前登録した primary book は、seen development data の out-of-fold 2.94 年で
**net Sharpe `-0.8425`、net 年率 `-0.084198`（10% vol target）**。**cost 前の gross Sharpe が既に `-0.4688`**
なので、コストは負けの原因ではない。kill 条項 9 個のうち 7 個が発火した。経済 band は `economically_weak`。

これは「この architecture が seen development data 上で支持されなかった」という判定であり、
`FX_HAS_NO_EDGE` ではない。規則に従い、ここで停止して Human + ChatGPT に返す。

---

## 1. Identity

| 項目 | 値 |
| --- | --- |
| stack merge | #478 → `a0780e3`、#479 → `3b4d0a9`（status を gate に範囲限定）、#480 → `3bbb7f5`。最終 master CI green |
| PR A（事前登録 + 実装） | #481、凍結 head `f1939fd`、CI green |
| PR B（実行 + 結果） | 本 PR（#481 の上に stack） |
| 凍結 hash | `aa0888089e4dcf5988bc6b734bb8e036262ed5c2efe4755d59fd9244176c85f1` |
| 実行 | `driver develop` 1 回、start marker `2026-09-14T01:09:01Z`、所要 18 秒、HEAD との差分 0 |
| artifact | `artifacts/research/continuous_portfolio/{prereg,development,development.started}.json` |

## 2. Architecture（凍結どおり）

```
7 features → pooled ridge（実効 df 3.0、5 日先 通貨 excess return）→ μ/σ → trailing PC1 除去
→ capped sum-zero target（|w| ≤ 0.25, gross 1）→ band 0.10 → ex-ante vol target 10%（≤ 5×）
→ traded delta のみ課金（Σ|Δ| × 1.703 bp）→ 翌日 P&L
```

## 3. H-003 Novelty Boundary

- ridge は全 6 fold で **20 日 z と 60 日 z に負、5 日 z と trend age に正**の係数を付けた。
  つまり primary は persistence book ではなく、**中期 reversal + 短期 momentum** の形。
- primary の日次 net P&L は、unfitted な 20 日 reversal rule と相関 `0.6357`、60 日 reversal rule と
  `0.4889` だった。20 日 reversal rule（net Sharpe `0.3141`）は primary 以上の Sharpe を持ち、相関も 0.5 以上
  なので、kill `a_resembling_unfitted_rule_does_as_well` が発火した。**fit は、似ている unfitted rule に対して
  価値を足していない（むしろ引いた）。**
- 60 日 benchmark の良い方（reversal、`0.5188`）も primary を上回り、`does_not_beat_the_unfitted_benchmark`
  も発火。resemblance flag（相関 ≥ 0.7）は立っていない（最大 `0.6357`）。

## 4. Data Used

- seen 連続 corpus `2021-04-26 … 2025-12-28`、3 つの guarded route 経由（観測 `2021-04-27 … 2025-12-26`）。
- usable days `2021-07-19 … 2025-12-26`、out-of-fold 判断日 `2023-01-17 … 2025-12-26`（764 日、P&L 763 日）、
  実測 259.824 取引日/年。
- 診断用に公開 BIS 政策金利（EUR は deposit facility に補正）。H1 と中銀カレンダーは `features.build` が読む（宣言済み）。

## 5. Protected Data Confirmation

| span | 状態 |
| --- | --- |
| fresh pool `2016-06-02 … 2021-04-25` | **未読**（corpus の最初の観測日は 2021-04-27、`assert_not_protected` 通過） |
| historical OOS（`2025-12-29` 以降） | **研究利用なし**（route が `2025-12-29` 以降を拒否、最終観測日 2025-12-26） |
| dead window / forward epoch | **未読** |
| broker 認証 API / demo / paper / live | **未使用** |
| Track 3 overlay、非線形モデル | **未実行** |

## 6. Prediction Frequency

毎取引日、8 通貨の expected return を 1 つずつ（763 日 × 8 = 6,104 予測）。**予測頻度は売買頻度ではない**:
position が変わった日は 56.5%（band 内なら売買しない）。

## 7. Actual Portfolio Turnover

| 指標 | primary（10% vol target） | 参考: unlevered 診断 |
| --- | --- | --- |
| 平均 currency gross | 4.29 | 0.98 |
| 通貨片道 notional / 年 | 219.5 | 45.6 |
| round trip / 年 | 109.7 | 22.8 |
| **round trip / 年 / 単位 gross** | **`25.567`** | 23.3 |

signal-free 較正（cap 付き target、band 0.10）の 15.7 より多い。実際の target は 20 日半減期より持続性が低く、
leverage の変動（hysteresis 10%）も売買を足す。kill 閾値 50 は下回った。

## 8. Cost Decomposition

| 項目 | 値 |
| --- | --- |
| pair 往復 | 2.58 bp（Track 3 実測の中点） |
| routing 倍率（課金） | 1.32（片側あたりの比を両側に適用、孤立 position で Track 2 の約 2 倍、ランダム trade で faithful の約 1.7 倍） |
| 課金 | Σ\|Δ\| × 1.703 bp、差分のみ |
| **annual cost drag（資本あたり）** | **`0.037374`**（3.74%/年） |
| cost / 単位 gross exposure | 87.1 bp/年 |
| faithful（equal-split pair book）cost | 2.57%/年 → net Sharpe `-0.7262` |
| ×1.5 / ×2 stress | net Sharpe −1.0288 / −1.2147 |
| financing | P&L から除外。政策金利 carry accrual は +0.08%/年（無視できる） |

## 9. Currency Expected-Return Model

pooled ridge、7 特徴、実効 df は全 fold で 3.0 に一致。係数の符号は全 fold で安定（20 日 z −、60 日 z −、
5 日 z +、trend age +、dispersion share −）。rank IC（診断のみ）: 生 μ の 5 日 IC 平均 3.18%（非重複 t 1.19）、
1 日 IC −0.33%（t −0.22）。**IC がわずかに正でも、portfolio の gross は負**。

## 10. Factor Neutralization

raw → neutralized score の日次相関 0.90（情報損失は小さい）。保有 exposure と第 1 主成分の |cos| 平均 0.094、
factor P&L 合計 −0.17%（gross 合計が負なので占有率は出ない）。neutralization を外した診断 book は net −0.79、
gross −0.42 で、neutralization は結果を変えていない。

## 11. Portfolio Mapping

primary（vol-normalized）net −0.84 / gross −0.47。診断: linear −0.77 / −0.42、rank −0.78 / −0.28。
どの mapping でも gross は負。

## 12. Efficiency Bundle

| 診断（1 つだけ変える） | net Sharpe | gross Sharpe | RT/年 |
| --- | --- | --- | --- |
| primary（band 0.10） | −0.8425 | −0.4688 | 109.7 |
| band なし | −0.9294 | −0.3255 | 181.0 |
| band 0.15 | −0.3806 | −0.0966 | 82.2 |
| DD governor（deployment 診断） | −0.7244 | −0.3433 | 83.9 |

band は turnover を下げたが、gross 自体が負なので救えない。**band 0.15 の数字は診断であり、結果後の band
最適化は禁止**（事前登録 §16）。

## 13. Walk-Forward Design

expanding window、初期 1.5 年、step 0.5 年、purge 5 日 + embargo 1 日。6 fold、test 130/130/130/130/130/114 日
（最終日は翌日リターンが無いので P&L は 113 日）。60 日未満の fold はなく、全 fold が fold 比率に数えられた。

## 14. Baselines

| | net Sharpe | gross Sharpe | net 年率 |
| --- | --- | --- | --- |
| B0 cash | 0 | 0 | 0 |
| B1 persistence 60 日 | −0.9306 | −0.7249 | −8.98% |
| B1 reversal 60 日 | 0.5188 | 0.7249 | +5.00% |
| B2 linear・bundle なし（unlevered） | −0.4447 | −0.0271 | −1.55% |
| **primary** | **−0.8425** | **−0.4688** | **−8.42%** |

⭐ **B1 reversal の正の数字は候補ではない。** これは C08 の閉鎖 family を符号反転したもので、事前登録で
「primary が上回るべき benchmark」として置いたもの。結果を見た後に符号を反転して採用することは禁止されており
（事前登録 §16、CLAUDE.md「A failed rule is not an inverted rule」）、2.94 年の Sharpe 0.52 は標準誤差
約 0.58 の範囲で 0 と区別できない。**`POST_HOC_EXPLORATORY` として記録するだけ**である。

## 15. Gross Results

gross 年率 `-0.046824`（10% vol target）、gross Sharpe `-0.4688`。unlevered では gross −1.03%/年。

## 16. Cost-Adjusted Results

net 年率 `-0.084198`、net Sharpe `-0.8425`。faithful cost でも −0.7262。

## 17. Net Sharpe

`-0.8425` → band `economically_weak`。

## 18. Annual Return

net −8.42%/年（10% vol target）、unlevered −1.81%/年。**net 5%/年は射程外**（符号が負）。

## 19. Realized Volatility

実現 vol `0.099943`（target 10% に対し 0.9994）。unlevered 2.37%/年。

## 20. Vol-Targeted Scenarios（実際に走らせた book）

| target | net 年率 | 実現 vol | max DD | 平均 leverage | cap 要求日比率 |
| --- | --- | --- | --- | --- | --- |
| 8% | −6.92% | 8.51% | −27.1% | 3.87 | 22.0% |
| 10% | −8.42% | 9.99% | −32.0% | 4.41 | 46.4% |
| 12% | −8.99% | 10.84% | −33.7% | 4.68 | 65.3% |

**leverage は負の edge を救わない。** 12% では cap が 65% の日で効き、実現 vol は target に届かない。

## 21. Required Leverage

10% vol に必要な上限なし leverage は平均 5.08（unlevered vol 2.37%）。cap 5× を要求した日は 46.4%
（kill 閾値 50% の直下）。

## 22. Drawdown

max DD −32.0%（10% vol target）、unlevered −6.9%。

## 23. Temporal Stability

fold 別 net Sharpe: −1.07 / **+0.44** / −0.34 / −0.51 / −2.63 / −0.33 → 正は 1/6。分散 regime 別 net も
両方負（高分散 −11.5%、低分散 −13.2%、累計）。

## 24. Currency Breadth

通貨別 gross P&L（累計）: GBP +5.1%、CAD +3.0%、NZD +0.9%、JPY −1.3%、AUD −3.2%、EUR −5.1%、CHF −5.8%、
USD −7.3%。最大の正の通貨（GBP）を除くと gross −18.9%、USD leg を除いても −6.4%。

## 25. Tail Concentration

net 合計が負なので top 1/5/10 日占有率は定義されない。上位 5 日を除いた net −33.7%（累計）、
3 robust σ clip 後 −6.04%/年、±3σ 内の日 −3.29%/年、日次歪度 −0.84、超過尖度 5.84。
**利益が少数日に偏っているのではなく、普通の日から負けている。**

## 26. Cost Stress

base −0.8425 / ×1.5 −1.0288 / ×2 −1.2147 / faithful −0.7262。コストを 0 にしても gross −0.4688。

## 27. Complexity vs Incremental Value

- 最も単純な B2（fitted μ、linear、neutralization・cap・band・vol target なし）: gross ≈ 0（−0.03）、net −0.44。
- primary（full bundle）: gross −0.47、net −0.84。
- 1 つずつ変えた診断は、どれも gross を 0 以上に戻さない（band 0.15 の −0.10 が最も近い）。
- fitted model は、それが似ている unfitted 20 日 reversal rule（net +0.31）より悪い。

**複雑さは増分価値を生まなかった。** B2 と primary の差がどの要素から来るかは、要素を 1 つずつ外す診断では
特定できていない（B2 は cap も外しており、cap だけを外す診断は事前登録していない）。これを事後に探すことは
しない。

## 28. Kill / Survive

| kill 条項 | 発火 |
| --- | --- |
| net Sharpe ≤ 0 | **yes** |
| net Sharpe < 0.20 | **yes** |
| 3 robust σ clip 後の平均 ≤ 0 | **yes** |
| 最大通貨除外後 gross ≤ 0 | **yes** |
| 正の fold が半数未満 | **yes** |
| 60 日 benchmark（良い方の符号）を上回らない | **yes** |
| 似ている unfitted rule が primary 以上 | **yes** |
| turnover > 50 RT/年/単位 gross | no（25.6） |
| cap 5× 要求日 > 50% | no（46.4%） |

Case A / B の条件は 1 つも満たさない。

## 29. Track 3 Status

未実行（今回未承認）。

## 30. Fresh Status

fresh pool `2016-06-02 … 2021-04-25` は**未読のまま**。historical OOS・dead window・forward epoch も未使用。

---

## 事後の禁止事項の遵守

結果を見た後に行っていないこと: feature 追加、horizon 変更、符号反転、通貨除外、band 最適化、leverage 最適化、
regime filter 追加、非線形モデル追加、保護 span の読み取り、2 回目の実行。

## 次に進まないこと

Case C のため停止する。fresh pool・Track 3・複雑 ML・paper-forward・B1 reversal の採用には進まない。
