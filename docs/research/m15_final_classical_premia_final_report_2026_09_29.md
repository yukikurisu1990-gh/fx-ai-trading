# FINAL_CLASSICAL_PREMIA_LONG_SPAN_CYCLE — 最終統合報告（2026-09-29）

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` · `PRODUCTION_READINESS_NOT_CLAIMED`.**

Human + ChatGPT 向け。数字の出所は全て次の 2 つである。

- `artifacts/research/classical_premia/execution.json`（1 回だけの実行記録）
- その日次 series（`execution_daily.parquet`）

事前登録は `docs/research/m15_final_classical_premia_prereg_2026_09_29.md`。

---

## 1. Executive Summary

| 項目 | 結果 |
| --- | --- |
| #496 | **MERGED**。head `660d846` → merge `24921e1`、master CI success |
| primary hypothesis | 断面 carry（BIS 政策金利の順位）+ 12-1 の断面 momentum（spot）を等リスクで合成した **composite 1 本**。ECB 長 span 2000-02 … 2016-06、8 通貨 |
| power（実行前） | 16.58 年、Sharpe の SE 0.246、MDE 0.69、真の Sharpe 0.3 の検出力 **0.23** |
| TC-net | **+1.36%/年、Sharpe 0.127**（正。ただし t ≈ 0.5） |
| judged economic net（central） | **+3.65%/年、Sharpe 0.340**（t ≈ 1.4） |
| primary null（通貨 label の置換） | judged の percentile **0.9775、p = 0.023** → 上側。TC-net は 0.81 / p = 0.19 で null と区別できない |
| carry の寄与 | judged の **99%**（+3.61%/年）→ `FAMILY_CONCENTRATION_CAVEAT` |
| momentum の寄与 | judged の 1%（+0.04%/年）。収益ではなく **2008–09 の hedge** として効いた |
| positive candidate か | 事前登録の判定では **`POSITIVE_EXPLORATORY_NOT_DECISION_GRADE`**（研究として正の exploratory） |
| fresh 提案条件（F1〜F8） | **満たさない**。F7 FAIL（fresh 4.9 年の検出力 0.19）。それ以外は PASS |
| 年 5% feasibility | 形式上は届く（要 vol 14.7%、DD −39%）。ただし閾値ぎりぎりで、**markup 1% か cost ×1.5 で不整合**。2009–2016 の Sharpe は約 0 → **実務上は射程外** |
| programme disposition | 凍結した規則では **B. `POSITIVE_EXPLORATORY_BUT_NOT_CONFIRMATION_READY`**。報告者の推奨は **`LONG_TERM_HOLD` / `NO_FURTHER_SEEN_DATA_ALPHA_SEARCH`**（§31。判断は Human + ChatGPT） |

**一文で**: 事前登録した composite は、全期間を pool すると判定上「正」で、帰無の上側に来た。しかしその中身は 2000–2007 年の短 JPY carry の受取で、2008 年以降は 0 である。fresh で確かめる検出力も無い。

## 2. Identity

| | |
| --- | --- |
| #496 final head | `660d846f479e869578dd2649badfaaf576b8639a` |
| #496 merge SHA | `24921e1b4e8472fdc83f7145e1406b9c611f59f3`（2026-09-28T16:07:20Z） |
| master CI（`24921e1`） | success |
| 新 PR | **#497**（`research/m15-final-classical-premia`）、Amber、Human + ChatGPT の merge 承認待ち |
| commit A | `6c9177c` 設計・事前登録・実装・pre-alpha review の修正 |
| commit B1 | `e8b2dd2` `FROZEN_DIGEST` |
| commit B2 | `0f61aa7` ledger `INTENT` |
| commit B3 | `f9356c3` ledger `STARTED` |
| commit C | `5449640` 実行記録 |
| commit D | この報告と post-run review（PR の最終 head と CI は PR 本文に記す） |
| freeze digest | `401b2b5c31f30444e7edac881a1a1391b323e8026e2ddc588b9805e06fb39f69` |
| execution HEAD | `f9356c3b8c86b3e1858c35cb8f7d009b636ccde0`（STARTED を足した commit） |
| execution timestamp | compute 開始 2026-09-28T22:20:26Z → 終了 22:23:28Z（workers 6、warning 0） |
| dirty path count | 0 |
| ledger | INTENT（22:19:46Z）→ STARTED（22:20:11Z）→ COMPLETED の 3 行。hash chain が通り、記録と artifact の sha256 が一致する |
| push の時刻 | INTENT と STARTED は compute の前に remote にあった（remote reflog: B2 07:19:55、B3 07:20:19 JST、compute 開始 07:20:26 JST） |

## 3. Why This Is The Final Seen-Data Cycle

#496 の programme-level の証拠は次のとおりだった。

- null と区別できる経済的な正の証拠は 0 本。
- tier A の TC-net の平均は +0.07。
- 検出力の天井は低い。
- 年 5% に要る Sharpe は 0.50〜0.77。

これを受けて裁定は、single-signal の逐次探索を終え、事前確率が高く未検定で残っていた「長 span の古典的 premia」を **1 本の合成として 1 回だけ** 測ることにした。この cycle の後は、同じ seen data の掘り直しをしない。

## 4. Prior Programme Evidence

#496 の最終報告のとおり（278 行の ledger、tier A〜E）。

- 長 span（1999–2016）で過去に測ったのは、USD factor の carry（M15）、20 日の momentum benchmark、実質為替の valuation だけ。
- 断面 carry と 6〜12 か月の断面 momentum は未検定だった（独立の監査で確認。事前登録 §6a）。

## 5. Preregistered Primary Hypothesis

G10 の既存 8 通貨で、断面 carry（family A）と 12-1 の断面 momentum（family B）を事前に固定した等リスク合成として月次で持つと、cost 後（TC-net）と近似 financing 込み（judged net）の両方が正で、no-information null の上側に来る。

- 検定するのは composite だけ。family 単独は診断である。
- best-of-N・horizon の選択・符号反転・結果後の変更は無い。

## 6. Currency Universe

AUD CAD CHF EUR GBP JPY NZD USD（`top_five.UNIVERSE` と同一。追加なし）。

## 7. Long Historical Span

- ECB 参照レート 1999-01-04 … 2016-06-01。
- decision day は 196（2000-02-01 … 2016-05-02）、P&L は 4,178 営業日（16.58 年）。

## 8. Data Sources

**新しい取得はしていない**（`NO_NEW_ACQUISITION_REQUIRED`）。

- FX: T-V で取得済みの ECB 参照レート。
- 政策金利: mechanism redesign で取得済みの BIS。
- 3 か月金利: OECD。financing の感度基準だけに使った。

入力 parquet 23 本と取得記録 2 本の hash は、凍結 digest に入っている。

## 9. Protected-Data Compliance

- fresh pool 2016-06-02 … 2021-04-25・historical OOS・dead window・forward は**読んでいない**。
- FX の最後の行は 2016-06-01。
- 政策金利の cache には 2021-05 以降の値もあるが、2016-06 … 2021-04 の値は無い。build はその日以前の値しか使わない（Role 2 が独立に確認）。
- authenticated broker・有料 data・ML は使っていない。
- 開示: post-run Role 2 は、金利 parquet の `tail()` を表示したときに 2025-09 … 11 の政策金利の値を見た。FX でも保護 window でもない。

## 10. Carry Definition

- BIS 政策金利の月末値を、月末の**翌暦日**から signal に使う。decision day には必ず前月末の値が届く（Role 2 が 196 日 × 8 通貨で確認）。
- 高金利を long、低金利を short。rank weight を使う。

**近似**（事前に開示済み）:

- JPY は、BIS に値が無いゼロ金利期間に 0% を置く。
- 期間の始めの 4 セルに、直前の値（0.15、0.05）が残った。
- 2016 のマイナス金利は 0%。
- 2009–15 のゼロ金利下限では、数 bp の差に満額の順位差が付く。

## 11. Momentum Definition

- 対 USD の spot log return の 12-1（営業日 [t−251, t−21] の和）、月次保有。
- AMP (2013) の formation 窓と保有を採った。
- excess return ではなく spot で作ったのは、alpha 前に決めた意図的な逸脱である（carry との機械的な重なりを避けるため）。

## 12. Composite Construction

- 各 family を rank weight（Σ|w| = 1）→ ex-ante vol 1 に揃え、0.5 / 0.5 で合成した。2 資産の厳密な equal risk contribution である。
- 通貨 gross の cap は 5 で、掛かった月は 0。
- 平均の通貨 gross は 2.70。

## 13. Risk Scaling

- t−252 … t−1 の 252 営業日の標本共分散（point-in-time）で、ex-ante vol を 10% にした。実現 vol は 10.74%。
- **開示（post-run Role 2 の REQUIRED_FIX）**: 2 つの sleeve は実現ベースで強く逆相関だった。
  - 日次 spot の相関は −0.79（2008 年は −0.94）。ex-ante の家族間相関の平均は +0.06 だった。
  - 各 sleeve の実現 vol は carry 16.4%・momentum 16.6% で、ex-ante の約 10.7% を大きく超えた。
  - composite が 10% 近くに収まったのは、**大きな 2 本の脚が打ち消し合った差**だからである。
  - 2008 年は carry −34.7%・momentum +27.5%、2009 年は carry +32.6%・momentum −29.6%。
  - 2008H2–2009 を除くと相関は −0.30（Spearman −0.16）。
  - 実行前の power で置いた相関の仮定（−0.2〜+0.2）は、この book を表していない。

## 14. Financing Model

既存の `APPROXIMATE_RESEARCH_FINANCING`（#495）をそのまま使った。

- USD numeraire の routing、carry = Σx(r − r_USD) × 暦日 / 365。
- markup は 0 / 0.5 / 1 / 2%（pair notional・年）、金利基準は 2 つ。
- actual OANDA financing ではない。full retail net は `FULL_RETAIL_NET_UNKNOWN`。

## 15. Power Analysis（実行前、`power.json`）

| 項目 | 値 |
| --- | --- |
| 年数 | 16.58 |
| MDE（80%） | 0.69 |
| 真の Sharpe 0.2 / 0.3 / 0.5 の検出力 | 0.13 / 0.23 / 0.53 |
| 有効標本数 | composite 11.6、carry **0.58**（16 年でほぼ 1 つの静的な賭け）、momentum 17.7 |

F4（有効 N ≥ 10）は実行前から PASS と分かっていた。

## 16. Null Design

**primary: 通貨 label の置換**

- 両 family に同じ置換 π を全期間で当てる。恒等置換は除く。
- 2,000 draw（distinct 1,960）、seed 20260929。
- carry が静的な賭けなので、時間方向の shift では carry premium が帰無に残ってしまう。そのため pre-alpha review（Role 1 R5）で primary をこちらにした。

**secondary: joint circular shift**（報告のみ）

- 2,000 draw、seed 20260930。

## 17. Pre-Alpha Reviews

- **Role 1（economics）**: BLOCKER 0、REQUIRED_FIX 5 件。
  - spot momentum の逸脱の明記
  - family の cost 按分
  - 通貨寄与の numeraire 依存
  - required risk の数値化
  - 静的な carry を帰無が吸収する問題
- **Role 2（timing / leakage / governance）**: BLOCKER 1 件（ディスク満杯。実行の前提条件）、REQUIRED_FIX 5 件。
  - digest の除外行 bypass
  - 失敗 run の黙った再実行
  - git の fail-open
  - 日次 series の保存
  - commit 手順
- **再監査**（新しい context）: 全て RESOLVED。新しい REQUIRED_FIX 3 件（JSON の CRLF・`.gitattributes`・按分の説明）も修正した。
- test は 49 本、research test 一式は 2,108 passed。

全て alpha 前に修正して凍結した（事前登録 §13）。

## 18. Execution Provenance

§2 のとおり。

1. commit A → B1（digest）→ B2（INTENT、push）→ B3（STARTED、push）。
2. compute を **1 回**実行した。
3. attempt の印・生の結果・日次 series・月次 target を判定の前に atomic に書き、記録と COMPLETED を書いた。

結果確認後の再実行はしていない。

## 19. Primary Composite Result

| 項目 | 値 |
| --- | --- |
| gross spot | +1.59%/年、Sharpe 0.148 |
| gross economic（spot + carry） | +5.02%/年、Sharpe 0.467 |
| **TC-net**（financing 抜き） | **+1.36%/年、Sharpe 0.127** |
| **judged net（policy、markup 0.5%）** | **+3.65%/年、Sharpe 0.340** |
| judged の 8 セル | policy: 0% 4.80 / 0.5% 3.65 / 1% 2.50 / 2% **0.21**%。3m: 4.84 / 3.69 / 2.55 / **0.25**%。符号は全セルで正 |
| turnover | 6.64 round trips/年（gross 1 単位あたり 2.46） |
| transaction cost | 0.23%/年 |
| carry（受取） | +3.44%/年（policy）/ +3.48%（3m） |
| markup（central） | −1.15%/年 |
| 安定性 | judged の正の暦年 13/17、TC-net は 11/17 |
| breadth | 通貨別の judged 寄与が正の通貨は 5/8 |
| LOO（1 通貨を除いて作り直し） | judged は 8/8 で正（最小は JPY を除いたとき +1.58%/年）。**TC-net は JPY を除くと −0.11%/年** |
| 集中度 | judged の top-10 日の寄与 0.45。TC-net は 1.21 |
| max DD | judged −28.6%（2007-07 → 2008-10）、TC-net −31.6% |
| primary null | judged の percentile 0.9775 / p 0.023。TC-net は 0.8065 / p 0.194 |
| secondary null | judged 0.9545 / p 0.046。TC-net 0.855 / p 0.145 |
| 時系列の t（参考） | judged ≈ 1.4、TC-net ≈ 0.5（しかも有効 N は 11.6） |

**読み方（post-run Role 1 の REQUIRED_FIX 1・3）**

- 帰無を超えたのは judged だけである。judged の優位は **carry の受取**から来ていて、spot（TC-net）は帰無と区別できない。
- label 置換の帰無は中心が −0.19 である。ランダムな book も markup を払うからで、「帰無超え」の一部は単にその分である。
- **期間の偏り**（日次 series からの記述統計。判定は変えない）:

  | 期間 | judged | TC-net Sharpe |
  | --- | --- | --- |
  | 2000–2007 | Sharpe 0.75、+8.3%/年 | 0.40 |
  | 2000–2003 のみ | Sharpe 1.11、+11.0%/年 | — |
  | 2008–2016 | Sharpe −0.07、−0.7%/年 | −0.15 |
  | 2010–2016 | Sharpe −0.03 | — |

  - span の前半と後半で見ても、前半 0.69、後半 −0.04 になる。
  - 2000–07 は文献（MSSS 2012、AMP 2013）がこの仮説を立てた標本と重なる。したがってこれは文献の **in-sample の再現**であり、新しい証拠とは言いにくい。
  - fresh pool に最も近い 2008 年以降の regime では 0 である。

## 20. Carry Diagnostic（診断のみ）

- carry 単独の book（同じ vol target・cost・financing）: judged +3.06%/年・Sharpe 0.287、TC-net −0.12%/年・Sharpe −0.01、max DD −40.5%。
- carry 単独は **spot では何も稼いでいない**。金利差の受取だけで正になっている（古典的な forward premium puzzle の形）。

## 21. Momentum Diagnostic（診断のみ）

- momentum 単独の book: judged +1.21%/年・Sharpe 0.111、TC-net +1.40%/年・Sharpe 0.128、max DD −35.3%。
- spot は正だが小さく、単独でも帰無と区別できる大きさではない。

**どちらも次 cycle へ昇格させない**（裁定 §40）。

## 22. Family Contribution

| | judged（central）年率 | 比率 | spot | carry | TC-net |
| --- | ---: | ---: | ---: | ---: | ---: |
| carry | +3.61% | **98.9%** | +0.61% | +3.59% | +0.55% |
| momentum | +0.04% | 1.1% | +0.98% | −0.16% | +0.81% |

- `FAMILY_CONCENTRATION_CAVEAT`（片 family ≥ 80%）が付いた。
- momentum の spot 利益（+0.98%）は、負の carry と markup の按分でほぼ消えた。
- momentum が composite の中で果たしたのは、2008–09 の carry 崩壊に対する hedge である（§13）。
- **「2 つの premium が両方寄与した」とは言えない**（post-run Role 1 の REQUIRED_FIX 4）。

## 23. Currency Contribution

通貨別の judged の寄与（cross-section 平均を引いた numeraire に依らない分解、年率）:

| 通貨 | 寄与 |
| --- | ---: |
| AUD | +0.30% |
| CAD | −0.34% |
| CHF | −0.44% |
| EUR | −0.16% |
| GBP | +0.31% |
| **JPY** | **+3.04%** |
| NZD | +0.22% |
| USD | +0.72% |

- **JPY が judged の 83%** を占める。
- composite は **84% の日に JPY を short** していた（平均 exposure −0.44）。
- JPY の寄与は spot +2.15%・carry +1.14% で、大きい年は 2006、2013（+11.3%）、2014（アベノミクスの円安）である。
- 凍結した `CURRENCY_CONCENTRATION_CAVEAT` は judged の LOO で定義しているので付かない（JPY を除いても judged は +1.58%）。しかし **TC-net は JPY を除くと負**になる。
- 経済的には、**特定通貨への強い依存がある**（post-run Role 1 の REQUIRED_FIX 2）。

## 24. Cost / Financing Stress

| | judged（central）Sharpe | TC-net Sharpe | judged（markup 2%、policy / 3m）Sharpe |
| --- | ---: | ---: | --- |
| cost ×1 | 0.340 | 0.127 | 0.020 / 0.024 |
| cost ×1.5（markup も ×1.5） | 0.276 | 0.116 | −0.204 / −0.200 |
| cost ×2 | 0.212 | 0.106 | −0.428 / −0.425 |

- 金利基準（policy と 3 か月）の違いは無視できる。
- 結果を左右するのは **markup** で、2% では 0、cost stress を掛けた adverse では負になる。

## 25. Annual 5% Feasibility

| 項目 | 値 |
| --- | --- |
| judged（central）Sharpe | 0.340 |
| 年 5% に要る vol | 14.7% |
| その vol での max DD（比例） | −39.2% |
| gap stress（最大通貨に 1 日 20% の逆行）の 1 日損失 | −40%（vol 15%） |
| 凍結した規則 | `REQUIRED_RISK_INCONSISTENT` = false（vol 15%・DD −40% の閾値の**内側に 0.3pt・0.8pt**） |

**ただし**（post-run Role 1 の REQUIRED_FIX 5）:

- markup 1% なら Sharpe 0.233 で、要 vol 21.5%・DD −59% → 不整合。
- cost ×1.5 なら要 vol 18.1% → 不整合。
- DD を vol target 10% で比例させると −42% → 不整合。
- 2009–2016 の Sharpe は約 0 で、この regime では届かない。

**結論: 形式上は B の範囲内だが、central の markup 0.5% という楽観的な仮定の上でだけ成り立つ。実務上、年 5% は現実的な risk の射程外である。**

- 実際に大きな 1 日損失があった: 2007-08-16 −6.5%、2015-01-15 −5.1%（CHF の short）。
- leverage で救うことはしない（§32）。

## 26. Annual 10% Feasibility

要 vol は 29.5%。**届かない。**

## 27. Forward Eligibility F1–F8

| 条件 | 判定 | 根拠 |
| --- | --- | --- |
| F1 clean tier A | **PASS** | 事前登録・1 回だけ・結果後の修正なし。post-run review 2 役とも BLOCKER なし |
| F2 null | **PASS** | primary null の judged percentile 0.9775、p = 0.023 |
| F3 conservative financing | **PASS（辛うじて）** | markup 2% で policy +0.21%/年、3m +0.25%/年（Sharpe 約 0.02） |
| F4 有効 N ≥ 10 | **PASS（実行前から既知）** | 11.6（大半は momentum の回転） |
| F5 breadth / LOO / 集中 | **PASS** | currency caveat なし（judged の LOO 8/8）、top-10 日 0.45、正の暦年 13/17。ただし TC-net は JPY を除くと負（§23） |
| F6 保護情報の汚染 | **PASS** | fresh pool に関わる汚染は無い（D-M3 は forward の JPY 金利確認だけが対象）。この composite は JPY の政策金利を使うので、**forward での確認には D-M3 が掛かる** |
| F7 fresh で判断が変わるか | **FAIL** | 観測 Sharpe 0.34 を真としても、fresh 4.9 年単独の片側検出力は 0.186 < 0.20 |
| F8 provenance | **PASS** | freeze digest・input hash・INTENT / STARTED / COMPLETED の hash chain・push 順・artifact hash を Role 2 が独立に確認 |

→ **F1〜F8 全 PASS ではない。`FRESH_CONFIRMATION_PROPOSAL` は出さない。**

## 28. Fresh Pool Decision

- fresh pool（2016-06-02 … 2021-04-25）は**今回も読んでいない**。
- 今後これに使う価値は **低い**。
  - 観測 Sharpe 0.34 を真としても検出力は 0.19。
  - 2008 年以降の regime（Sharpe 約 0）が fresh の期間に近いなら、検出力はさらに低い。
  - 一度使えば二度と確認に使えない。
- この composite で fresh を消費することは推奨しない。

## 29. Programme Decision

- **凍結した規則による disposition: B. `POSITIVE_EXPLORATORY_BUT_NOT_CONFIRMATION_READY`**
  - 研究の判定は POSITIVE で、gap large ではなく、risk inconsistent でもない。F7 が FAIL なので A ではない。
  - post-run review に BLOCKER は無いので、報告者はこの機械的な判定を上書きしない。
- ただし B は次の条件の**全て**の上でだけ成り立つ。
  1. 2000–2016 を pool したとき（2008 年以降だけなら 0）
  2. markup 0.5%（1% では risk 不整合）
  3. JPY を含むとき（JPY を除くと TC-net は負）
  4. carry の受取を含む judged のとき（spot の TC-net は帰無と区別できない）
- **報告者の推奨: programme は `LONG_TERM_HOLD` / `NO_FURTHER_SEEN_DATA_ALPHA_SEARCH` に移す。**
  - B の中身は、古典的な短 JPY carry premium の in-sample 再現である。
  - fresh で確かめる検出力が無く、年 5% の射程にも実務上入らない。
  - この「B だが hold」の扱いは、Human + ChatGPT の判断事項として §33 に上げる。
- `FX_RESEARCH_PAUSED` と `FX_HAS_NO_EDGE` は使わない。

## 30. What Would Reopen Research

裁定 §38 のとおり。

- genuinely new な情報源
- 実質的に長い clean history
- 明示的な仮説を持つ高情報量の有料 data
- 十分な forward の蓄積
- 新しい market microstructure の情報
- financing / execution の経済性の実質的な改善
- Human + ChatGPT の新しい裁定

この cycle から言える具体的なこと:

- 古典的 carry は、retail の markup（0.5% 以上）と 2008 年以降の regime の下では、残るものがほとんど無い。
- **実際の broker financing が 0.5% を大きく下回ると分かれば**、判断は変わりうる。ただし broker trigger（#496 §22）の B1（financing を除いた edge が null を超える）は、この composite の TC-net では満たさない。

## 31. Final Answers

1. **long-span carry + momentum composite は TC-net で positive だったか？**
   → **正だったが弱い**。+1.36%/年、Sharpe 0.127（t ≈ 0.5）。帰無と区別できない（p = 0.19）。2004–2016 と JPY 除外では負。
2. **approximate financing を含めても positive だったか？**
   → **central（markup 0.5%）では正**。+3.65%/年、Sharpe 0.340。8 セル全てで正だが、markup 2% では約 0（+0.2%/年）。2008 年以降は central でも約 0。
3. **null / no-information behaviour を超えたか？**
   → **judged は事前登録の primary null を超えた**（p = 0.023。secondary も p = 0.046）。ただし優位の源は carry の受取で、spot（TC-net）は超えていない。時系列では 0 と区別できない（t ≈ 1.4、有効 N 11.6）。
4. **carry と momentum の両 family が意味のある寄与をしたか？**
   → **しなかった**。judged の 99% は carry。momentum は収益ではなく、2008–09 の carry 崩壊の hedge として効いただけ。
5. **特定通貨への極端な依存は無いか？**
   → **ある（経済的に）**。JPY が judged の 83% で、84% の日に JPY を short していた。凍結した caveat（judged の LOO）は付かないが、JPY を除くと TC-net は負。
6. **年 5% net は realistic risk で射程か？**
   → **実務上は射程外**。形式上は vol 14.7%・DD −39% で閾値の内側だが、markup 1% または cost ×1.5 で不整合になる。2009–2016 では Sharpe が約 0。
7. **年 10% は？**
   → **届かない**（要 vol 29.5%）。
8. **fresh pool を 1 回の confirmation に使う価値があるか？**
   → **無い**。F7 FAIL（検出力 0.19）。直近の regime では 0。
9. **active research として続けるか、LONG_TERM_HOLD へ移すか？**
   → 凍結した規則の disposition は B。報告者の推奨は **LONG_TERM_HOLD / NO_FURTHER_SEEN_DATA_ALPHA_SEARCH**。
10. **次に Human + ChatGPT が判断すべきことは何か？**
    → §33 の 1 点（B の扱い）と、#497 の merge。

## 32. Post-Run Independent Review

役割は 2 つ。どちらも別 session で、source と保存した出力を読み直した。再実行はしていない。互いの結論は渡していない。

**Role 1（economics / interpretation / business capacity）— BLOCKER 0**

- 凍結した判定（status・caveat・business gap・required risk・F2〜F5・F7・disposition B）を独立に再計算し、一致した。
- REQUIRED_FIX 5 件。全てこの報告に反映した。

  | 指摘 | 反映先 |
  | --- | --- |
  | 期間の集中 | §19 |
  | 短 JPY carry | §23 |
  | 有意性の源は carry の受取 | §19・§31 Q3 |
  | momentum は hedge | §22 |
  | B が knife-edge | §25・§29 |

- 推奨: 機械的なラベルは B のまま、programme は長期 hold とする。

**Role 2（implementation / timing / leakage / portfolio / financing / provenance）— BLOCKER 0、run は VALID**

- 生の parquet から独立に再実装し、target weight・spot P&L・cost・carry（両基準）・markup・headline を全て機械精度で再現した（差は最大 4.4e-16）。
- 次を確認した。
  - timing: carry は前月値、covariance は t−1 まで、P&L は t+1
  - 2016-06-01 より後の行が無い
  - cost は decision day だけに掛かる
  - 分解の合計が一致する
  - provenance: commit 順・push 時刻・ledger の chain・digest・artifact hash
- REQUIRED_FIX 1 件: sleeve の実現 vol と逆相関を開示する → §13 に反映した。
- 開示事項: 閾値ぎりぎりの値、JPY の stale 値、金利 cache の 2025 値の表示 → §9・§10・§25 に反映した。

**lead の判断**

- BLOCKER は無く、run は INVALID ではない。REQUIRED_FIX は全て報告の開示・記述で満たした。
- 数値の判定・凍結した規則は変えていない。
- 2 役の推奨（B は条件付きで、実務上は hold）は証拠と一致する。そのため §29 で推奨として Human + ChatGPT に上げる。

## 33. Human + ChatGPT Decisions Needed

1. **disposition B をどう扱うか。**
   - 凍結した規則の結果は B（`POSITIVE_EXPLORATORY_BUT_NOT_CONFIRMATION_READY`）である。
   - しかし中身は 2000–07 の短 JPY carry の受取で、2008 年以降は 0、fresh の検出力は 0.19、年 5% は実務上射程外である。
   - 報告者は、B を研究記録として残したうえで、programme を **`LONG_TERM_HOLD` / `NO_FURTHER_SEEN_DATA_ALPHA_SEARCH`** に移すことを推奨する。
2. **PR #497 の merge 承認**（Amber）。

---

**STOP（裁定 §46）。** ここで止まり、次の cycle には進まない。以下のどれも行わない。

- fresh / forward / OOS / dead の読み取り
- broker 認証
- 有料 data
- ML
- 2 本目の仮説
- 別 horizon
- 最適化した ensemble
