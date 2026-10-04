# FXID Final Mechanism Feasibility Review — 最終報告（2026-10-05）

**`FXID_FINAL_MECHANISM_FEASIBILITY_REVIEW` · `NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` · `PRODUCTION_READINESS_NOT_CLAIMED`.**

**記号**:

| 記号 | 意味 |
| --- | --- |
| 【原典】 | 論文の本文・表を読んで確認した値（どこまで読んだかを §6 に書く） |
| 【既存の記録】 | この repo の commit 済みの報告・記録の値。今回、価格 data は読んでいない |
| 【算術】 | この報告での計算 |
| 【推論】 | lead の判断や仮定 |

**維持する結論**（変えない）:

- `LONG_TERM_HOLD`
- `NO_FURTHER_SEEN_DATA_ALPHA_SEARCH`
- `STAGE0_RED_RETURN_TO_HUMAN`
- `FXID_CYCLE1_EXIT_CONDITION_II_FIRED_RETURN_TO_HUMAN`
- `R_A2B_ECON_PARTIAL`

R-A2b は Cycle 1 の後に設計した事後の検証で、独立の証拠ではない。

---

## 1. Executive Summary

**結論: 採用条件を全て満たす候補は 0 件。`FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE` を推奨する。**

FX の日中には、文献で実証された、時刻に錨を下ろした仕組みが確かにある。

- dealer が fix での dollar の需要を在庫で受け、その対価を取ることで生じる、dollar の日中の W 字（Krohn・Mueller・Whelan、J. Finance 2024）
- 自国の取引時間の自国通貨安（Breedon & Ranaldo、JMCB 2013）
- 月末の株式ヘッジの調整（Melvin & Prins、JFM 2015）

**そのうち 2 つの区間は、公開の情報だけで M15 で判断でき、当日決済でき、retail の cost の後でも小さな正の net の可能性がある**。

| 区間 | 原典の根拠 | retail の cost の後の推定【算術・仮定付き】 |
| --- | --- | --- |
| 欧州の朝の EUR の short（02:00 → 08:15 ET） | B&R の EBS の firm な bid / ask の後で Sharpe 1.3（1997–2007）、KMW の CME の firm な気配・全 spread で Sharpe 0.99（2009–2018） | Sharpe 約 0.2〜0.75（時期と仮定による） |
| 東京の仲値の後の JPY（仲値 → 02:00 ET） | KMW の half spread で Sharpe 0.77（1999–2018） | 1999–2018 の平均では約 0.8〜0.9。CME（2009–2018）を基にすると約 0。KMW 自身が、2013 年以降は half spread で JPY は横ばいと書いている |

**それでも候補にしない理由**:

1. **この programme の要求に届かない**。必要 gross / σ（cost / σ + 1/√(k · n)、単一の pair で k = 1、n = 250）は EUR 0.131・JPY 0.126 で、原典の gross / σ は EUR 0.078〜0.115・JPY 0.115〜0.119。真の値がこれでは、G4（縮小後 Sharpe 1.0）にも届かない。
2. **独立した検証の道が無い**（条件 8）。追加で取れる pre-2016 の FX 履歴は、文献がこの効果を見つけた期間（1997–2018）の中にあり、独立の検定にならない。公表の後の期間は fresh（保護）と seen（使用済み）に当たる。
3. **最近の期間で弱まっている兆候**（JPY の東京の反転は 2013 年以降、half spread で横ばい。EUR の fix の後の区間は CME で Sharpe 0.08）。

その他の仕組みは、非公開の flow が必要、効果が分単位で M15 では捕まえられない、効果量が cost に負ける、既存研究と重複する、のどれかに当たる（§15）。

**FX デイトレードが不可能という意味ではない。** 現在の知識・cost・data では、追加の研究と開発の費用を投じる独立した経済的根拠が足りない、という意味である。執行の cost が大幅に下がれば、上の 2 区間は再検討の価値がある（§19）。

## 2. 今回の承認範囲

| 区分 | 範囲 |
| --- | --- |
| 承認 | 文献調査（1 回）、既存研究の確認、既存の記録の数値を使った算術、報告書、独立レビュー、修正、PR（Amber） |
| 禁止 | 新しい価格 data の取得、既存の価格 data の新たな読み取り、追加の signal-free 統計、alpha・backtest・ML・戦略の実装、S1 / S2 の救済、OANDA への接続、fresh / OOS / dead / forward、CFD、G4 の確定、prior の凍結、Cycle 2、paper / demo / live |

**今回の作業は、web の論文・公的資料の閲覧と、repo の文書・commit 済みの集計の記録（`artifacts/research/fxid_cycle1/cycle1_run2.json` の時刻ごとの集計）の閲覧だけ**で、価格系列は 1 つも読んでいない。

## 3. PR #502 の merge 記録

| | |
| --- | --- |
| 確認 | OPEN、head `78cc6ff`（報告と一致）、変更 8 file（予期しない研究内容なし）、CI `contract-tests` / `test` success、独立レビュー 2 役 + 再監査が完了、未解決の BLOCKER なし |
| merge | `gh pr merge 502 --merge --match-head-commit 78cc6ff…` → merge `03ce27426fdf…`（2026-10-04T18:20:49Z） |
| master | `03ce274`（この作業の branch の起点） |
| master の CI | `03ce274` の CI は success（独立レビュー Role 2 が確認） |

## 4. 既存研究の結論（今回の判断の前提）

【既存の記録】詳細は §11。

- **Round 1（#464）**: M15 / H1 の 8 family・26 戦略が全て net で負。trend と breakout は gross から負。全ての特徴量と horizon で IC が負。
- **Round B′（#469）**: 全ての horizon で VR < 1（z −14.7）。線形の最良の予測でも損益分岐の 6〜16%。
- **Round A（#468）**: 事前登録の 39 cell が全て不合格。
- **H-002**: session / ATR / ADX / spread の gate は CLOSED（price だけの、gate としての条件付け）。
- **clock flow（#474）**: London fix・東京の仲値・NY 10:00 の option cut・London の開場・rollover の**前後 1 時間**を、**ランダムな方向で**検出力と cost だけ測った。方向の仮説は一度も検定していない。
  - 毎日の窓: 損益分岐の gross IR は 4.1〜58.7 で不可能。
  - 月末: London fix の前の窓は経済性が最良（IR 0.59 / 0.82）だが、どちらの panel でも検出力が無い。
- **#475**: `LONDON_FIX_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER`。月末の London fix の前の窓の実測の cost は、中央値 2.925 / 2.886 bp（slippage を除く）。
- **#478**: C04（fix flow）・C05（月末）は「検出力の不足で、反証ではない」。RED で、**両方とも判断により停止・提案不可**。C03（session の引き継ぎ）は `NO_DECISION_GRADE_PASS_REGION`。
- **#489**: 22.5 年で C05 に `PASS_REGION_EXISTS`（拘束条件は event_floor）と記録。
- **CPI・指標**:
  - #472（CPI の surprise、検出力不足）
  - #473（US 08:30 の全ての発表、1 時間、**検出力のある帰無**。**未 merge の PR** の記録）
  - #477（非 USD、検出力不足）
- **S1**: 除外。**S2**: 現行の案は保留（#502 の裁定）。
- **PATSD Stage 0（#499）・FXID Cycle 1（#501）・R-A2b（#502）**: 上記のとおり。

## 5. 文献調査の方法

1. 3 つの独立した調査役に分けた。
   - 既存研究の重複監査（repo の文書だけ）
   - fix と月末
   - 注文 flow とその他
2. 原典の優先順位は、査読済み論文 → 中央銀行・NBER の working paper → 著者の公開資料 → 二次資料。
3. **PDF の本文を text に変換して読んだ**（方法・結果・表）。web の要約の道具の出力は信頼しない。
   - 実際に、KMW の要約が「fix の前の 40〜50 bp」「Sharpe 1.5〜2.0」という本文に無い数値を作っていたので、捨てた。
4. lead と独立レビュー（Role 1）が、主要な引用と表を、変換した本文で再確認した。
   - KMW の Table 8（全ての行）と、§V・§VI の結論の文
   - Melvin & Prins の「10% → 14 bp」「72% の反転」
   - Ito & Yamada の 2 本
   - Breedon & Ranaldo の Table 2
   - Ranaldo の cost の節
   - ABDV
   - MSS の cost の扱い
5. 変換した text は作業用で、commit していない（著作権のため）。引用は論文の節・表の番号で示す。

## 6. 検証した学術文献

確認の水準: **F** = 本文と表、**WP** = working paper 版の本文（出版版の表とは違いうる）、**A** = abstract だけ。

| # | 文献 | 出版 | URL / DOI | 市場・期間・解像度 | 確認 |
| --- | --- | --- | --- | --- | --- |
| L1 | Krohn, Mueller, Whelan "Foreign Exchange Fixings and Returns around the Clock" | J. Finance 79(1) 2024, 541–578 | doi:10.1111/jofi.13306。WP: https://sites.insead.edu/facultyresearch/research/file.cfm?fid=66802 | G9 対 USD、5 分の TRTH の indicative な気配。Table 3 は 2019-12 まで、Table 8 は 1999-01〜2018-12（どちらも 5,009 観測と記載）。CME は 2009–2018 | WP（Table 3・8、§V・§VI）。出版版は abstract |
| L2 | Evans "Forex trading and the WMR Fix" | J. Banking & Finance 87 (2018) 233–247 | https://mpra.ub.uni-muenchen.de/81583/ | 21 pair、2004–2013、1 分の Gain Capital（20 超の銀行の気配を集約）の mid + EBS | F（Table 6） |
| L3 | Melvin & Prins "Equity hedging and exchange rates at the London 4 p.m. fix" | J. Financial Markets 22 (2015) 50–72 | https://www.ecb.europa.eu/events/pdf/conferences/131216/Third_FX_Workshop_MELVIN_PRINS_Equity%20hedging%20and%20exchange%20rates%20Nov%202013.pdf | G10 の 10 通貨、2004-04〜2012-12、5 分の EBS / Reuters | WP（係数は出版版で未確認） |
| L4 | Ito & Yamada "Puzzles in the Tokyo fixing in the forex market" | J. Int. Econ. 109 (2017) 214–234 | https://www.nber.org/papers/w22820 | EBS Level 5、2006–2013（USD/JPY は 1999〜） | 本文の一部（data・spike・結論・Figure 6 の説明） |
| L5 | Ito & Yamada "Did the Reform Fix the London Fix Problem?" | NBER w23327 (2017) | https://www.nber.org/system/files/working_papers/w23327/w23327.pdf | EBS Level 5、8 pair、2006-01〜2016-06（改革後は約 16 回の月末） | F（Table 2 は変換が崩れ、pair の対応は不確か） |
| L6 | Breedon & Ranaldo "Intraday patterns in FX returns and order flow" | J. Money, Credit and Banking 45(5) 2013, 953–965 | https://www.snb.ch/public/asset/en/www-snb-ch/publications/research/working-papers/2011/working_paper_2011_04/publications0_en/working_paper_2011_04.n.pdf | EBS、1997-01〜2007-06、6 pair、時間足 + BNP の顧客 flow 2005–07 | F（Table 1〜4） |
| L7 | Ranaldo "Segmentation and time-of-day patterns in foreign exchange markets" | J. Banking & Finance 33(12) 2009, 2199–2206 | https://www.snb.ch/public/asset/en/www-snb-ch/publications/research/working-papers/2007/working_paper_2007_03/publications0_en/working_paper_2007_03.n.pdf | Reuters FXFX、4 時間の区間、1993–2005 | WP（cost の節。Table 4 は変換で列が崩れ、数値の対応は不確か） |
| L8 | Evans & Lyons "Order Flow and Exchange Rate Dynamics" | JPE 110(1) 2002, 170–180 | https://www.nber.org/papers/w7317 | D2000-1、DM/$・¥/$、1996-05〜08、日次 | abstract + 本文の一部 |
| L9 | Evans & Lyons "How is macro news transmitted to exchange rates?" | JFE 88 (2008) | https://www.nber.org/papers/w9433 | 同上 + Reuters のニュース | abstract + data の節 |
| L10 | Love & Payne "Macroeconomic news, order flows, and exchange rates" | JFQA 43(2) 2008, 467–488 | doi:10.1017/S0022109000003598 | dealer 間の取引 | A |
| L11 | Menkhoff, Sarno, Schmeling, Schrimpf "Information flows in foreign exchange markets" | J. Finance 71 (2016) 601–634 | https://openaccess.city.ac.uk/id/eprint/13781/ | 大手 1 行の顧客 flow、15 通貨、2001–2011、日次 | F |
| L12 | Andersen, Bollerslev, Diebold, Vega "Micro effects of macro announcements" | AER 93(1) 2003, 38–62 | https://www.nber.org/papers/w8959 | 5 分の Reuters、5 通貨対 USD、1992–1998 | F |
| L13 | Elaut, Frömmel, Lampaert "Intraday momentum in FX markets" | J. Financial Markets 37 (2018) 35–51 | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2694985 | RUB/USD（MICEX）、2005–2014 | A（本文は入手できず） |
| L14 | Gao, Han, Li, Zhou "Market intraday momentum" | JFE 129 (2018) | https://ssrn.com/abstract=2440866 | SPY（株）、1993–2013 | WP（市場をまたいだ参考） |
| L15 | Bessho, Sugimoto, Suzuki（gotobi） | arXiv:2301.13204（**査読なし**） | https://arxiv.org/abs/2301.13204 | USD/JPY、2018–2020 | 本文（効果量は図だけ） |
| L16 | FSB "Foreign Exchange Benchmarks – Final Report" | FSB 2014-09-30 | https://www.fsb.org/2014/09/r_140930/ | 制度 | F |
| L17 | Camanho, Hau, Rey "Global Portfolio Rebalancing and Exchange Rates" | RFS 35(11) 2022 | https://www.nber.org/papers/w24320 | 月次・fund 単位 | A |
| L18 | Chaboud et al.（指標発表と EBS） | Fed IFDP 823 (2004) | https://www.federalreserve.gov/pubs/ifdp/2004/823/ifdp823.htm | EUR/USD・USD/JPY、1999–2004 | A |

- **出版版の書誌**（巻・頁）は、独立レビューの記憶と一致するが、原典の出版版の page では確かめていない。
- **確認できなかったもの**: Lyons の教科書（注文の分割の理論）、2015 年より後の月末の株式ヘッジの学術研究（L5 の約 16 回を除く）、G10 の OTC での日中の momentum の効果量、FX の発表の後の drift を報告する査読論文（見つからなかった）。

## 7. FX Fixing

**制度**【原典 L16・L5・L1】:

- WMR の London 16:00 fix は、2015-02-15 から 5 分の窓（15:57:30〜16:02:30 London）になった（FSB の勧告 1）。
- ET では通常 11:00（英米の夏時間のずれの週は 10:00 / 12:00）。
- 東京の仲値は 9:55 JST で、**ET では冬（EST）19:55、夏（EDT）20:55**（L1 の脚注 8）。
- ECB の参照 rate は 14:15 CET（ET では約 08:15）。

**fix の前後の dollar の W 字**【原典 L1】:

- 仕組み: dollar の需要に応じる dealer が、在庫の保有に対価を取る。
- dollar は各 fix の前に上がり、後に下がる。等しい重みの dollar の portfolio で:

  | 区間 | 効果 |
  | --- | --- |
  | 17:00 ET → 東京の仲値 | +2.1 bp / 日（t = 12.0） |
  | 東京の仲値の後 | −2.2 bp / 日（t = 9.2） |
  | 02:00 ET → London fix | +1.7 bp / 日（t = 4.1） |
  | London fix → 17:00 ET | −1.9 bp / 日（t = 5.5） |

- Europe の窓は不安定（火曜で t = 1.42、8〜10 月は有意でない）。
- **Table 8（cost を含む取引の結果）**: 窓は、EUR が **ECB の fix**（02:00 → 08:15 → 17:00 ET）、GBP が London fix（02:00 → 11:00 → 17:00 ET）、JPY が東京の仲値（17:00 → 仲値 → 02:00 ET）。年率の return（Sharpe）:

  | 行 | EUR の前 | EUR の後 | EUR 両方 | GBP の前 | GBP の後 | GBP 両方 | JPY の前 | JPY の後 | JPY 両方 |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | cost なし（BA0%） | 7.08（1.24） | 6.68（0.90） | 13.75（1.47） | 4.96（0.67） | 6.27（1.50） | 11.23（1.32） | 4.67（1.44） | 8.21（1.82） | 12.87（2.33） |
  | 半分の spread（BA50%） | 3.56（0.62） | 3.04（0.41） | 6.60（0.70） | 1.52（0.20） | 2.73（0.65） | 4.24（0.50） | −0.12（−0.06） | 3.49（0.77） | 3.37（0.60） |
  | 全 spread（BA100%） | 0.04（0.00） | −0.59（−0.09） | −0.55（−0.06） | −1.92（−0.27） | −0.82（−0.21） | −2.74（−0.33） | −4.91（−1.55） | −1.22（−0.28） | −6.13（−1.12） |
  | CME の firm な気配・全 spread（2009–2018） | **5.53（0.99）** | 0.58（0.08） | 6.11（0.65） | 0.06（0.01） | −4.89（−0.99） | −4.83（−0.51） | −11.23（−2.25） | 2.41（0.52） | −8.82（−1.27） |

  本文は CME の EUR の ECB fix の取引の Sharpe を 0.61 と書き、表の 0.65 と食い違う。
- **著者の評価**（§V の Table 8 の議論）:
  - "returns from trading a relatively small window around the fix are usually more than offset by transaction costs. Second, holding the currency positions for a longer window that allows to exploit the persistent drift patterns throughout the day may lead to positive excess returns, at least for traders that are able to get reasonably good conditions to trade."
  - 結論（§VI）: "arbitrageurs with deep enough pockets can likely exploit the predictable return patterns even after taking into account transaction costs"。
  - Figure 9 の説明（50% の spread）: 東京の反転は、2013 年頃から EUR・GBP で負、JPY で横ばい。
- **indicative の spread は実効の cost より広い**（L1 §IV、Gilmore & Hayashi・Gargano et al. を引用し、最大 75% の縮小を示唆）。
  - Table 8 から逆算すると、EUR の indicative な往復の spread は約 2.8 bp / 日（全 spread の行と cost なしの行の差 7.04% / 252）【算術】。
  - OANDA の EUR_USD の実測（往復約 1.4 bp）は、BA50% の行（約 1.4 bp）に近い【推論】。

**月末の fix の周辺の反転**【原典 L2・L5】:

- 月末の fix の前後の価格変化は、負の系列相関を持つ。
- Evans の Table 6 の取引規則は、**fix の価格で cost 0 で入る**という仮定。15 分の保有で AUD/USD 9.2%・EUR/GBP 8.3%・EUR/USD 3.97% など正の pair があり、GBP/USD・USD/JPY は負。
- Ito & Yamada は、改革の後も「月末の利益は still available、15 分の保有は even stronger」とするが、根拠は約 16 回の月末だけで、窓の終わり（16:02:30）の直後の分単位の入りが前提。
- 月内は改革の後、全ての pair で負（EUR/USD −0.52 / −0.40 / −0.86 bp）。

**個人投資家が使える情報**: fix の時刻と月末の日付は公開されていて、事前に分かる。W 字の方向は無条件（前は dollar 高、後は dollar 安）。

**既存の clock flow との重複**:

- #474 は fix の時刻の**前後 1 時間**を、ランダムな方向で測った。
- L1 の取引は **6〜9 時間の区間**（02:00 → 08:15 など）で、方向を持つ。**区間も方向も既存研究と異なり、未検定**である。

## 8. Month-End Rebalancing

**仕組み**【原典 L3】:

- 株式の運用会社は、月の最後の 16:00 fix で通貨の hedge を再設定する。
- 注文は fix の約 1 時間前に銀行に届き、その大きさは月末の前日の株価の終値で決まる。

**回帰の結果**【原典 L3】:

- 月の最終営業日の 15:00〜16:00 London の通貨の return を、月末の前日までの株式の月初来 return（**どちらも横断面の平均に対する相対値**）で回帰した。
- 係数 −0.0142（p = 0.00）、**R² = 0.03**。著者の言い換え: "a 10% equity appreciation leads to 14 basis points of currency depreciation"、"this seems like quite a small effect"。
- 16:00 から翌日の正午までに、fix の前の 1 時間の動きの約 72% が戻る。

**事前の予測可能性**:

- ある。前日の公開の株価の終値で、entry（15:00 London = 10:00 ET、ずれの週は 09:00 ET）の前に方向が決まる。
- 株価指数の data の取得が別に要る。
- cost は差し引かれておらず、取引規則も検定されていない。sample は 2012 年まで。

**Camanho, Hau, Rey**【A のみ】: fund 単位・月次の rebalancing と為替の関係で、日中の時刻の結果は無い。

**既存研究との重複**:

- #474 の月末の cell（方向はランダム、検出力不足）
- #475（実測の cost）
- C05（停止・提案不可）
- S21（株式を条件にした月末の hedge の flow。停止中の family として除外済み）
- PATSD の F3（51 回）

## 9. Institutional Order Flow

| 文献 | 結果 | 公開されているか |
| --- | --- | --- |
| L8 | dealer 間の注文 flow は、日次の為替の変化の 64%（DM）・45%（¥）を同時点で説明する | 非公開。同時点の説明で、予測ではない |
| L9 | 指標の効果の少なくとも半分は flow を通じて価格に入る | 非公開 |
| L10 | 定時の発表の情報の約 3 分の 1 が flow を通じて取り込まれる | 非公開（abstract のみ） |
| L11 | 遅らせた顧客の flow で並べた long-short が年 10.3〜12.4%（Sharpe 1.26〜1.45）。**cost は quoted の spread の 50%** で差し引いた（本文の脚注） | **大手 1 行の顧客 flow で非公開** |

**評価**: 予測力のある結果は全て、非公開の flow を使っている。公開の価格から flow を推定する FX の実証は見つからなかった。測られた事実（VR < 1、IC 負）は、分割執行による数時間の継続の痕跡と逆である。

## 10. その他の有力メカニズム

1. **自国の取引時間の自国通貨安**【原典 L6・L7】:
   - L6 の Table 1 では、Europe の取引時間は 07:00〜15:00（NY + 5 時間）、US は 08:00〜16:00 NY。
   - L6 の Table 2（EBS の mid、年率）: EUR/USD は EUR の時間（EUR の開場 → USD の開場）に −8.4%、USD の時間に +10.0%。GBP/USD は −7.1% / +9.2%。
   - **EBS の firm な bid / ask を払った後**（Table 2 の最後の列）は、EUR/USD だけが正: 朝の short +6%（Sharpe 1.3）、午後の long +7%（Sharpe 0.9）。他の pair は cost の後で負。
   - 仕組みは、地元の顧客が地元の時間に自国通貨を売る注文 flow。flow で条件付けると、残りの pattern は消える（Table 3）。
   - L7: EUR/USD の規則は、往復約 4 pip の cost まで正。
   - **L1 の EUR の ECB の fix の前の区間（02:00 → 08:15 ET）は、L6 の EUR の時間の short とほぼ同じ区間で、2009–2018 の CME の firm な気配でも Sharpe 0.99**。2007 年より後も、同じ現象が別の data で残っていた。
2. **東京の仲値・gotobi**:
   - 【原典 L4】顧客の注文は dollar の買いに偏り、9:55 の直前の数秒〜数分で数 bp 上がり、数秒で戻る。仲値で切り替える 5 分 long → 5 分 short は平均 1.8 bp で、"slightly above the transaction cost"。
   - 【原典 L1】数時間の区間では、仲値の後に dollar 安（JPY の後の区間で、cost なし 8.21%・Sharpe 1.82、BA50% 3.49%・0.77、CME 2.41%・0.52）。
   - 【L15、査読なし】gotobi の日の 3:00〜9:55 JST の上昇を報告する。
3. **指標の発表の後の drift**: 【原典 L12】"a jump immediately following the announcement, and little movement thereafter"。L18 も同様（abstract）。FX で 30 分後以降の drift を報告する査読論文は見つからなかった。
4. **日中の momentum**: 【L13 は abstract のみ】RUB/USD の取引所。【L14】は株。G10 の OTC での効果量は確認できなかった。

## 11. 過去研究との重複監査

| 仮説の family | 重なる既存研究 | 既存研究での状態 | 区分 |
| --- | --- | --- | --- |
| fix の W 字の数時間の区間（L1。EUR の ECB 前、JPY の仲値の後、など） | #474 は fix の**前後 1 時間**だけ（毎日は損益分岐 IR 4.1〜58.7） | **6〜9 時間の区間と方向は未検定** | 新規。§13 で不合格 |
| 月末の fix の前の株式ヘッジ（L3） | #474 の月末の cell、#475（実測の cost）、C05（停止・提案不可）、S21（停止中の family）、PATSD F3 | 方向は未検定。**検出力の不足が拘束条件**（#489 では 22.5 年で PASS_REGION_EXISTS、event_floor） | `DUPLICATE_OF_PREVIOUS_RESEARCH`（停止中の family）+ §13 |
| 月末の fix の後の反転（L2・L5） | #474 の月末の `london_fix post` の cell（M15、MDE 7.17 / 4.42、検出力 なし / あり、損益分岐 IR 1.25 / 1.61） | 1 時間の窓は測った。分単位の効果は M15 では測れない | 部分的に重複 + 実装不能 |
| 注文 flow・分割執行（L8〜L11） | S1（除外）、R-A2b §12、Round 1 の session gate | 数時間の継続は VR < 1 に反する（検出力は十分） | 重複 + 実装不能 |
| 自国時間の自国通貨安（L6・L7） | **H-002（session gate、CLOSED）**、**C03（session の引き継ぎ、`NO_DECISION_GRADE_PASS_REGION`。horizon と economic_net_under_stress で不合格、未実行）**、Round 1 / Round A の session の分割 | H-002 は他の signal の gate で、時刻と通貨で方向を決める仮説ではない。C03 は session の引き継ぎの相対の動きで、経済性の机上の判定で落ちた（実行せず） | 方向の仮説としては未検定（ただし C03 の経済性の判定と方向は整合）。§13 で不合格 |
| 東京の仲値・gotobi（L4・L15） | #474 の `tokyo_fix` の cell（毎日は損益分岐 IR 8.48 / 8.88。月末の前の窓は検出力あり、IR 1.83 / 2.30） | 1 時間の窓は経済的に不可能に近い。数時間の区間（L1 の仲値の後）は未検定 | 1 時間は重複、数時間は新規。§13 で不合格 |
| 指標の発表の後の drift（L12） | #472、#473（検出力のある帰無、未 merge の PR）、#477、S2（保留） | US の 1 時間の surprise の方向は帰無 | 重複 |
| 日中の momentum（L13・L14） | S1（除外）、Round 1 の trend（gross 負）、B′ の VR < 1 | 反証（検出力は十分） | 重複 |

**否定と検出力の不足の区別**:

- 反証（検出力あり）は、数時間の継続（S1 と日中の momentum）と、US 08:30 の発表の 1 時間の方向（#473）。
- 検出力の不足は、月末の fix（C04 / C05）、CPI だけ（#472）、非 USD（#477）。
- 後者を、検出力の不足だけを理由に再探索することはしない。

## 12. 文献から確認した効果量

全て【原典】。bp / 日は著者の年率を 252 で割った換算を含む（換算と書く）。

| 仕組み | 効果（gross） | cost の扱い（原典） | 期間 |
| --- | --- | --- | --- |
| EUR の ECB の fix の前（L1） | 7.08% / 年（約 2.8 bp / 日、換算）、Sharpe 1.24 | BA50% 3.56%（0.62）。全 spread 0.04%（0.00）。CME 5.53%（0.99） | 1999–2018。CME は 2009–2018 |
| JPY の仲値の後（L1） | 8.21% / 年（約 3.3 bp / 日、換算）、Sharpe 1.82 | BA50% 3.49%（0.77）。全 spread −1.22%。CME 2.41%（0.52） | 同上 |
| EUR の ECB の後・GBP の London の後（L1） | 6.68% / 6.27% | CME で EUR 0.58%（0.08）、GBP −4.89%（−0.99） | 同上 |
| 自国時間の自国通貨安、EUR/USD（L6） | −8.4% / +10.0% / 年（約 3〜4 bp / 日、換算） | EBS の bid / ask の後、+6%（1.3）/ +7%（0.9） | 1997–2007 |
| 月末の株式ヘッジ（L3） | 相対の株価の 10% につき 14 bp、R² = 0.03 | 無し | 2004–2012 |
| 月末の fix の後の反転（L5） | 月末 15 分で約 +2〜4 bp（pair の対応は不確か）、月内は負 | EBS の bid / ask を含むが、窓の終わりの直後の分単位の入り | 2006–2016-06 |
| 東京の仲値の spike（L4） | 5 分 + 5 分で 1.8 bp | 「cost をわずかに上回る」 | 1999–2013 頃 |
| 指標の発表（L12） | 1 SD の雇用統計の surprise で DM/$ 約 0.16%、ただし即時 | — | 1992–1998 |
| 顧客の flow（L11） | 年 10〜12%、Sharpe 1.3〜1.5 | quoted の spread の 50% で差し引いた後も有意 | 2001–2011（非公開の flow） |

## 13. FX デイトレードとしての採算性

**使う cost と σ**【既存の記録 + 算術】:

- 出典は `artifacts/research/fxid_cycle1/cycle1_run2.json` の `r_a2.per_pair[pair].hourly_ny[h]`（`spread_bp_mean` = その時刻の M15 の終値の spread の平均、`vol_bp_std` = M15 の return の標準偏差）。seen 2021–2025、NY 現地時刻、夏時間は正しく扱う。
- 区間の σ は、M15 の vol を区間の本数で二乗和して平方根を取る（自己相関 0 の仮定。VR < 1 なので実際はこれより小さく、cost / σ は過小評価に、すなわち候補に有利な向きになる）。
- slippage は往復 0.5 bp。
- 研究上の要求（R-A2b と同じ式）: 必要 gross / σ = cost / σ + S / √(k · n)、S = 1.0。単一の pair を毎日取引するなら k = 1、n = 250 で、1/√250 = 0.063。

**(a) EUR の欧州の朝の short（02:00 → 08:15 ET。L1 の EUR の ECB の前 ≒ L6 の EUR の時間の short）**:

- EUR_USD の実測: 02 時台の spread 1.39 bp、08 時台 1.50 bp。往復 = 1.39 / 2 + 1.50 / 2 + 0.5 = 1.94 bp。σ（02:00〜08:15 の 25 本）= 28.6 bp。cost / σ = 0.068。
- 原典の gross / σ:
  - L1（1999–2018）で 0.078（Sharpe 1.24 / √252）〜0.098（2.8 bp を今の σ で割る）。
  - L6（1997–2007）で 0.115。
- **必要 gross / σ = 0.068 + 0.063 = 0.131 > 0.078〜0.115**。不足。
- 参考の net の Sharpe【算術】:

  | 根拠 | 推定 |
  | --- | --- |
  | L1 を基に | 0.16〜0.48 |
  | L6 を基に | 約 0.74 |
  | CME（2009–2018、firm な往復の spread を 0.4 bp と仮定【推論】）を基に | 0.29（slippage を含む）〜0.52（含まない） |

**(b) JPY の東京の仲値の後（仲値 → 02:00 ET。L1 の JPY の後の区間）**:

- USD_JPY の実測: 20〜21 時台の spread 1.25 bp、02 時台 1.19 bp。往復 1.72 bp。σ（20:00 / 21:00 → 02:00）= 25.6〜29.0 bp、中間 27.3 bp。cost / σ = 0.063。
- 原典の gross / σ は 0.115〜0.119（1999–2018）。**必要 0.126 に僅かに届かない**。
- net の Sharpe:
  - 1999–2018 の平均で 0.82〜0.89【算術】。
  - **CME（2009–2018）を基にすると −0.2〜+0.07**。
  - L1 の Figure 9 の説明では、2013 年以降、half spread で JPY は横ばい。
- 当日決済（17:00 から 17:00 の取引日の中）・rollover を避けることは満たす。

**(c) London fix → 16:45 ET の dollar 安（L1 の後の区間）**:

- 20 pair の中央値の実測: 11 時台の spread 1.64、16 時台 2.54。往復 2.6 bp。σ（11:00〜16:45 の 23 本）≈ 22 bp。
- 必要 = 0.12 + 0.063 ≈ 0.18。
- 原典の gross / σ は、EUR で 2.9 / 22 ≈ 0.13、basket で 1.9 / 22 ≈ 0.09。basket の σ は単一の pair より小さいので、basket の比は過小評価だが、basket は単一の因子（k ≈ 1）である。
- CME では、EUR の後の区間は Sharpe 0.08、GBP は −0.99。**不足**。

**(d) 月末の株式ヘッジ（L3）**:

- R² = 0.03 から、予測の相関は約 0.17。符号だけで取引する場合の trade あたりの gross / σ は約 0.14【算術。予測と return が同時正規の場合】。|signal| > 1 SD だけで取引すると約 0.26（取引の数は減る）。
- R² は横断面の平均を引いた相対の return についての値なので、単一の pair の σ に対しては更に小さくなる（結論を強める向き）。
- cost: #475 の実測（月末の London fix の前の窓、slippage を除く中央値 2.925 / 2.886 bp）+ 0.5 bp。σ は #474 の月末の分散 12.6〜17.4 bp。cost / σ は約 0.20〜0.27。
- 横断面の long-short（k ≤ 9、n = 12）で 1/√108 = 0.096。**必要 0.30〜0.37 > 0.14〜0.26**。`ECONOMICALLY_UNATTRACTIVE`。

**(e) 月末の fix の後の反転（L2・L5）・仲値の spike（L4）**: 効果は窓の終わりの 1〜15 分の中にあり、M15 の entry では大部分を逃す。`NOT_IMPLEMENTABLE_WITH_AVAILABLE_INFORMATION`（解像度）。

**情報の公開から entry までの損失**: 指標の発表は数分で調整が終わる（L12）ので、M15 の終値の後の entry では効果の大部分が失われる。fix 系は時刻が事前に分かるので、この損失は無い。

## 14. 実装可能性

| 仕組み | 情報は公開か | 事前に分かるか | M15 で判断できるか | 当日決済できるか |
| --- | --- | --- | --- | --- |
| fix の W 字の数時間の区間 | 時刻だけ（公開） | 可 | 可 | 可（EUR 02:00 → 08:15、JPY 仲値 → 02:00、London fix → 16:45。いずれも 17:00 をまたがない） |
| 月末の株式ヘッジ | 株価指数の終値（公開、取得が要る） | 前日の夜に可 | 可（10:00〜11:00 ET） | 可 |
| fix の後の反転 | 公開 | 可 | **不可**（分単位） | 可 |
| 東京の仲値の spike | 公開 | 可 | **不可**（秒単位、9:55 は M15 の境に無い） | 可 |
| 自国時間の自国通貨安 | 時刻だけ | 可 | 可 | 可 |
| 顧客の注文 flow | **非公開** | — | — | — |
| 指標の発表の drift | 公開 | 発表の後 | 調整は数分で終わる | 可 |

## 15. 候補の比較

採用条件（裁定 §11）: (1) 機構、(2) 原典の実証、(3) 公開の情報、(4) M15、(5) 当日決済、(6) cost を超える可能性、(7) 非重複、(8) 追加の FX 履歴で検証できる。

| 仕組み | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 区分 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **EUR の欧州の朝の short**（L1・L6） | ○ | ○（1997–2018、CME 2009–18 を含む） | ○ | ○ | ○ | △（net は正の可能性。必要 gross / σ に届かない、§13a） | ○ | **×**（下記） | `ECONOMICALLY_UNATTRACTIVE`（programme の要求に対して） |
| **JPY の仲値の後**（L1） | ○ | ○（ただし 2013 年以降は横ばい） | ○ | ○ | ○ | △（平均では正、最近は約 0、§13b） | ○ | **×** | `ECONOMICALLY_UNATTRACTIVE` |
| London fix の後の dollar 安（L1） | ○ | ○ | ○ | ○ | ○ | **×**（§13c、CME で EUR 0.08・GBP −0.99） | ○ | × | `ECONOMICALLY_UNATTRACTIVE` |
| 月末の株式ヘッジ（L3） | ○ | ○（2012 年まで） | ○ | ○ | ○ | **×**（§13d） | **×**（C05・S21 は停止中） | **×**（年 12 回、検出力の不足が拘束条件） | `DUPLICATE_OF_PREVIOUS_RESEARCH` / `ECONOMICALLY_UNATTRACTIVE` |
| 月末の fix の後の反転（L2・L5） | ○ | △（改革の後は約 16 回） | ○ | **×** | ○ | — | △ | × | `NOT_IMPLEMENTABLE_WITH_AVAILABLE_INFORMATION` |
| 東京の仲値の spike・gotobi の長い drift（L4・L15） | ○ | ○ / △（長い drift は査読なし） | ○ | **×** / △ | ○ | — | △ | — | `NOT_IMPLEMENTABLE_WITH_AVAILABLE_INFORMATION` / `INSUFFICIENT_EVIDENCE` |
| 機関の注文 flow（L8〜L11） | ○ | ○ | **×** | — | — | — | — | — | `NOT_IMPLEMENTABLE_WITH_AVAILABLE_INFORMATION` |
| 指標の発表の drift（L12） | △ | **×**（drift の実証なし） | ○ | × | ○ | — | **×**（#473 の帰無、S2 保留） | — | `INSUFFICIENT_EVIDENCE` / `DUPLICATE_OF_PREVIOUS_RESEARCH` |
| 日中の momentum（L13・L14） | △ | **×**（G10 OTC で未確認） | ○ | ○ | ○ | — | **×**（S1・VR < 1） | — | `INSUFFICIENT_EVIDENCE` / `DUPLICATE_OF_PREVIOUS_RESEARCH` |

**条件 8 が「×」の理由**（EUR の朝・JPY の仲値の後）:

- (i) 追加で取得できる pre-2016 の履歴（OANDA 2006–2016）は、文献がこの効果を見つけて報告した期間（L6 1997–2007、L1 1999–2018）の中にあり、効果の存在の独立な検定にならない。確かめられるのは「その期間の OANDA の cost でも正か」だけ。
- (ii) 公表の後の期間（2019 年〜）は、fresh（2016-06〜2021-04、保護）・seen（2021–2025、使用済み）・保護期間に当たる。
- (iii) 検出力: net の Sharpe を 0.5 とすると、10 年の data での片側 5% の検出力は約 0.47、0.3 なら約 0.24【算術】。
- (iv) 真の Sharpe が 0.2〜0.75 なら、どれだけ data があっても G4（縮小後 1.0）は満たせない。

## 16. 最終候補と採用・除外の理由

**最終候補: 0 件。** 全ての仕組みが、少なくとも 1 つの必須の条件を満たさない（§15）。採用条件は緩めていない。逆に、誤った算術で落としてもいない（独立レビューの指摘で、最も強い区間を評価に入れ直した）。

**最も候補に近い 2 区間**:

| 区間 | 除外の理由 |
| --- | --- |
| EUR の欧州の朝の short | 2009–2018 の firm な気配でも残った、最も堅い証拠を持つ区間。retail の cost の後の net は正の可能性がある（Sharpe 約 0.2〜0.75）が、programme の要求（必要 gross / σ 0.131、G4 1.0）に届かず、単一の pair で、独立な検証の期間が無い |
| JPY の東京の仲値の後 | 長期の平均では正だが、最近の期間（CME 2009–18、2013 年以降）は約 0 |

## 17. 統計的な検証可能性

候補が残らないので、検証の設計は作らない。

**参考**（EUR の欧州の朝の区間を仮に検証する場合）:

- net の効果 / σ は、trade あたり約 0.01〜0.047（Sharpe 0.16〜0.74 を √252 で割る）。
- 中間の 0.03 なら、片側 5% の検定で検出力 80% を得るには (2.49 / 0.03)² ≈ 6,900 日 ≈ 27 年の独立な data が要る【算術】。
- §15 の条件 8 の (i)・(ii) により、独立な期間を用意できない。

**帰無の案 C の問題**（裁定 §13 の整理）:

- 固定の entry 時刻に依存する。
- entry 時刻の違う候補をまとめた同時の帰無を作りにくい（全ての境で区間を分けると、保有中の依存が壊れる）。
- 前日以前の情報を使う規則に使えない。
- 保有中の return の条件付きの対称性を仮定する。

なお fix の W 字は方向が無条件（時刻だけ）なので、符号の randomization の帰無は「時刻と方向の結びつきが無い」に当たり、案 C の entry の前の情報の問題は生じない【推論】。**限定的な検討の候補として維持する**が、標準の方式にはしない。実装と較正はしない。

## 18. 候補が残った場合の事前登録案

**該当しない**（候補 0 件）。

## 19. 候補が残らない場合の保留判断

**推奨: `FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE`。**

- 意味: FX デイトレードが不可能なのではなく、現在の知識・cost・data では、追加の研究と開発の費用を投じる独立した経済的根拠が足りない。
- 最も強い原典（L1）の証拠は、時刻の W 字が実在し、firm な気配でも EUR の欧州の朝の区間が利益を出したことを示す。しかし、programme の要求（G4 1.0）を満たすには効果が小さく、独立な検証の期間も無い。
- 候補が残らなかったので、**別の戦略を追加して研究を続けることはしない**。Human が改めて指示するまで、研究を止める。

**維持するもの**:

- data の分割の方針（新しい履歴の前半で選択・後半で推定・fresh で確認）
- G4（縮小後 Sharpe 1.0）
- prior の未凍結（懐疑的な prior を主の検討案、他は感度）
- 帰無の案 C の限定的な扱い

どれも閾値は変えない。

**将来の再開の条件**【推論・提案】。次のどれかが新しく得られた場合に、Human が改めて判断する。

- (a) **執行の cost が大幅に下がる**（例: EUR_USD の往復が slippage を含めて 1 bp 以下）。その場合、EUR の欧州の朝の区間の必要 gross / σ は約 0.10 に下がり、原典の gross / σ（0.078〜0.115）と重なる。
- (b) 原典で、retail の cost の後に正の、公開の情報だけの日中の FX の効果が、新しい独立な期間で報告される。
- (c) 公開の情報で、機関の flow を事前に予測できる新しい data の source。

## 20. 独立レビュー結果

2 つの独立な役を、別の context で並行して走らせた。source・原典の text・契約を渡し、互いの結論は渡していない。lead は各指摘を原典の text と repo の記録で確かめてから採否を決めた。

### Role 1（学術文献・経済性）

確認された点: 引用と数値の大部分は原典と一致した。KMW の basket の bp と t 値、Table 8、MP の −0.0142 / R² = 0.03 / 14 bp / 72%、IY の 2 本、ABDV、B&R の 0.06 / 0.07 と Sharpe 1.3 / 0.9、Ranaldo の 4 pip、EL の 64% / 45%、MSS の 10.31 / 12.43% を照合した。

**BLOCKER 2 件（両方修正済み、結論は維持）**:

| # | 指摘 | 対応 |
| --- | --- | --- |
| B1 | 最も強い区間（EUR の欧州の朝の short。B&R の Sharpe 1.3、KMW の CME の firm な気配・全 spread 2009–18 の Sharpe 0.99）を評価せず、弱い区間（USD の時間の long、0.9）で「最良でも Sharpe 0.6」としていた。KMW の東京の反転を、EUR の減衰の証拠として誤って使っていた | EUR_USD と USD_JPY の時刻ごとの実測を使い、EUR の朝の区間（§13a）と JPY の仲値の後の区間（§13b）を評価し直した。最良の推定は Sharpe 約 0.2〜0.75 で、programme の要求に届かない。除外の根拠を、要求の不足と条件 8 に置き直した |
| B2 | 「全 spread ≈ retail」は根拠がなく、逆向きの可能性が高い（KMW の indicative の EUR の往復は約 2.8 bp、OANDA は約 1.4 bp） | 「retail に近い cost で負」を削った。OANDA ≈ BA50% を【推論】として明記した |

**REQUIRED FIX 7 件（全て修正済み）**:

| # | 指摘 |
| --- | --- |
| R1 | 東京の仲値の ET の換算が逆（冬 19:55 EST、夏 20:55 EDT） |
| R2 | Table 8 の EUR は London ではなく ECB の fix の区間 |
| R3 | KMW の引用を一部だけにしていた。後半（長い区間は正の超過 return の可能性）と §VI の結論も引用した |
| R4 | σ の出典（11〜15 時台の値は Cycle 1 の報告に無い）。commit 済みの記録の key を明記し、basket の σ の注意を足した |
| R5 | 月末の IC の単位（横断面の相対値）、閾値の規則での約 0.26、横断面の long-short の k ≤ 9 でも不足、を明記した |
| R6 | MSS の cost は quoted の spread の 50% |
| R7 | retail の往復 2.2〜2.6 bp を、全ての仕組みに当てはめていた。実測のある時刻と pair に限った |

**NON-BLOCKING（反映）**:

- USD の時間の entry と exit の時刻の cost
- Gain Capital の性質
- Evans の Table 6 の正の pair
- KMW の Table 3 と Table 8 の期間の違い
- 出版版の書誌は未照合であることの明記

### Role 2（既存研究・governance）

**BLOCKER なし。** 確認された点:

- 変更は 1 file だけで、新しい data の読み取り・alpha・backtest は無い。
- S1 / S2 の扱い、5 つの維持する結論、G4 1.0、prior の未凍結、Cycle 2 なし、候補 0 件（≤ 3）、21 節、Q1〜Q6、3 件の判断依頼。
- §3 の merge と master の CI（success）。
- #474 / #475 / #478 / Round A / B′ / #472 / #473 / F3 の数値。

**REQUIRED FIX 5 件（全て修正済み）**:

| # | 指摘 | 対応 |
| --- | --- | --- |
| 1 | §13 の値（11 時台 1.64・16 時台 2.54・11〜15 時台の vol）の出典が報告ではなく、commit 済みの記録 | `cycle1_run2.json` の key と集計の方法（pair の中央値、spread の平均）を明記した |
| 2 | 月末の cost の拡大を「含まない」としていたが、#475 に実測がある（2.925 / 2.886 bp） | その値を使った |
| 3 | 月末の fix の後・東京の仲値の月末の cell の既存の測定（#474）が §11 に無い | 足した |
| 4 | 自国時間の行に、H-002（CLOSED）と C03（`NO_DECISION_GRADE_PASS_REGION`）が無い | 足し、方向の仮説としては未検定であることを論じた |
| 5 | 「最良の場合 Sharpe 0.6」は支えられていない（Role 1 の B1 と同じ） | 同上 |

**NON-BLOCKING（反映）**:

- C04 も提案不可
- #489 の `PASS_REGION_EXISTS`
- #473 は未 merge の PR
- 引用を作業用の text の行番号ではなく、論文の節で示す
- URL を補完した
- B&R の net と EBS の spread の仮定に表の番号と【推論】を付けた

**修正の後の再監査**: 新しい context で確認した（結果は PR の本文に記録する）。

## 21. Human + ChatGPT への判断依頼

1. **`FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE` を採るか**（FX デイトレードの研究を長期の保留にし、新しい指示まで止める）。
2. **保留の期間に維持するもの**: data の分割の方針・G4 の 1.0・prior の未凍結・帰無の案 C の限定的な扱いを、記録としてそのまま維持するか。
3. **再開の条件**（§19 の (a)〜(c)、特に執行の cost の条件 (a)）を、将来の再開の判断の基準として記録するか。

### 裁定 §18 の問いへの回答

| 問い | 回答 |
| --- | --- |
| Q1. 文献で実証され、現在の個人投資家が利用できる FX デイトレードの仕組みはあるか | **ある**。fix の前後の dollar の W 字（特に EUR の欧州の朝の区間）は、公開の情報（時刻）だけで M15 で判断でき、当日決済でき、firm な気配の全 spread でも 2009–2018 に正だった（L1 の CME）。retail の cost の後の net も、小さな正の可能性がある（Sharpe 約 0.2〜0.75、推定）。ただし規模は小さく、この programme の要求には届かない |
| Q2. 既存研究で既に否定されていないか | fix の W 字の数時間の区間は、方向も区間も未検定（#474 は前後 1 時間をランダムな方向で測っただけ）。数時間の継続（S1・日中の momentum）と US の発表の 1 時間の方向は否定済み（検出力あり）。月末は、検出力の不足が拘束条件の停止中の family |
| Q3. 効果量は現実の cost に比べて十分か | **cost は越えうるが、programme の要求には不十分**。必要 gross / σ（EUR 0.131・JPY 0.126）に対し、原典の gross / σ は 0.078〜0.119。cost の評価は、実測のある NY の時間帯と、EUR_USD・USD_JPY の時刻ごとの実測の範囲に限る |
| Q4. 追加の FX 履歴を取得して検証する価値のある仮説が残ったか | **残っていない**。pre-2016 の履歴は文献の発見の期間の中にあり、独立な検証にならない（§15 の条件 8） |
| Q5. 候補が残った場合の最小の研究範囲 | 該当しない |
| Q6. 候補が残らなかった場合、長期保留にすべきか | **すべき**（`FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE`）。再開は §19 の条件による |

---

**STOP（裁定 §21）。** 新しい指示まで何も実行しない。
