# FXID Final Mechanism Feasibility Review — 最終報告（2026-10-05）

**`FXID_FINAL_MECHANISM_FEASIBILITY_REVIEW` · `NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` · `PRODUCTION_READINESS_NOT_CLAIMED`.**

**記号**:

| 記号 | 意味 |
| --- | --- |
| 【原典】 | 論文の本文・表を読んで確認した値（どこまで読んだかを各文献に書く） |
| 【既存の実測】 | この repo の既存の報告に記録された値（今回 data は読んでいない） |
| 【算術】 | この報告での計算 |
| 【推論】 | lead の判断 |

**維持する結論**（変えない）:

- `LONG_TERM_HOLD`
- `NO_FURTHER_SEEN_DATA_ALPHA_SEARCH`
- `STAGE0_RED_RETURN_TO_HUMAN`
- `FXID_CYCLE1_EXIT_CONDITION_II_FIRED_RETURN_TO_HUMAN`
- `R_A2B_ECON_PARTIAL`

R-A2b は Cycle 1 の後に設計した事後の検証で、独立の証拠ではない。

---

## 1. Executive Summary

**結論: 条件を満たす候補は 0 件。`FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE` を推奨する。**

FX の日中の価格形成には、文献で実証された、時刻に錨を下ろした仕組みが確かにある。

- fix の前後の dollar の W 字
- 自国の取引時間の自国通貨安
- 月末の株式ヘッジの調整
- 東京の仲値の需要

しかし、どれも次の 3 つのどれかに当たり、この programme の採用条件（§11 の 8 項目）を同時には満たさない。

1. **効果量が、OANDA retail の現実の cost と同程度か、それ以下**。最も強い原典（Krohn・Mueller・Whelan、J. Finance 2024）は、自らの cost の分析で、全 spread を払うと EUR・GBP・JPY の fix の取引は**負**になり、「平均的な trader には利用できるかは明らかでない」と結論している。
2. **効果が数秒〜15 分の中にあり、M15 では捕まえられない**（fix の直後の反転、東京の仲値の spike）。
3. **非公開の注文 flow が必要**（顧客の flow の予測力）。

**候補に最も近かったもの**: EUR/USD の自国時間の自国通貨安（Breedon & Ranaldo 2013）。interdealer の cost の後でも正（Sharpe 0.9〜1.3、1997〜2007 年）だが、他の pair は cost の後で負。retail の cost を足した最良の場合でも単一の pair で Sharpe 約 0.6【算術・仮定付き】で、G4（縮小後 1.0）に届かず、breadth も無い。

**FX デイトレードが不可能という意味ではない。** 現在の知識と data では、追加の研究と開発の費用を投じる独立した経済的根拠が足りない、という意味である。

## 2. 今回の承認範囲

| 区分 | 範囲 |
| --- | --- |
| 承認 | 文献調査（1 回）、既存研究の確認、既存の報告の数値を使った算術、報告書、独立レビュー、修正、PR（Amber） |
| 禁止 | 新しい価格 data の取得、既存の価格 data の新たな読み取り、追加の signal-free 統計、alpha・backtest・ML・戦略の実装、S1 / S2 の救済、OANDA への接続、fresh / OOS / dead / forward、CFD、G4 の確定、prior の凍結、Cycle 2、paper / demo / live |

**今回の作業は、web 上の論文・公的資料の本文の閲覧と、repo の文書の閲覧だけ**で、価格系列は 1 つも download していない。

## 3. PR #502 の merge 記録

| | |
| --- | --- |
| 確認 | OPEN、head `78cc6ff`（報告と一致）、変更 8 file（予期しない研究内容なし）、CI `contract-tests` / `test` success、独立レビュー 2 役 + 再監査が完了、未解決の BLOCKER なし |
| merge | `gh pr merge 502 --merge --match-head-commit 78cc6ff…` → merge `03ce27426fdf…`（2026-10-04T18:20:49Z） |
| master | `03ce274`（この作業の branch の起点） |
| master の CI | PR の CI は success。master の CI の結果は、この PR の本文に記録する |

## 4. 既存研究の結論（今回の判断の前提）

【既存の実測】repo の文書から。詳細は §11。

- **Round 1（#464）**: M15 / H1 の 8 family・26 戦略が全て net で負。trend と breakout は gross から負。全ての特徴量と horizon で IC が負。
- **Round B′（#469）**: 全ての horizon で VR < 1（z −14.7）。構造は実在するが、線形の最良の予測でも損益分岐の 6〜16%。
- **Round A（#468）**: 事前登録の 39 cell が全て不合格。
- **clock flow（#474）**: London fix・東京の仲値・NY 10:00 の option cut・London の開場・rollover の前後 1 時間を、**ランダムな方向で**検出力と cost だけ測った。方向の仮説は一度も検定していない。
  - 毎日の窓: 損益分岐の gross IR は 4〜59 で不可能。
  - 月末: London fix の前の窓は経済性が最良（損益分岐 IR 0.59 / 0.82）だが、どちらの panel でも検出力が無い。
- **#475**: `LONDON_FIX_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER`。
- **#478**: C04（fix flow）・C05（月末）は「検出力の不足で、反証ではない」。RED で、判断により停止中。C05 は新しい提案から外されている。
- **CPI・指標**:
  - #472（CPI の surprise、検出力不足）
  - #473（US 08:30 の全ての発表、1 時間、**検出力のある帰無**）
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
4. lead が、主要な引用（KMW の結論の文・Table 8、Melvin & Prins の「10% → 14 bp」「72% の反転」、Ito & Yamada の「after the reform … still available」と「1.8 bp … slightly above the transaction cost」、Breedon & Ranaldo の Sharpe 1.3 / 0.9、Ranaldo の「4 pips まで」、ABDV の「little movement thereafter」）を、変換した本文で再確認した。
5. 確認の水準は文献ごとに書く（abstract のみ / 本文 / 表）。確認していない効果量は書かない。

## 6. 検証した学術文献

確認の水準: **F** = 本文と表を読んだ、**WP** = working paper 版の本文（出版版の表とは違いうる）、**A** = abstract だけ。

| # | 文献 | 出版 | URL / DOI | 市場・期間・解像度 | 確認 |
| --- | --- | --- | --- | --- | --- |
| L1 | Krohn, Mueller, Whelan "Foreign Exchange Fixings and Returns around the Clock" | J. Finance 79(1) 2024, 541–578 | doi:10.1111/jofi.13306（WP: sites.insead.edu … fid=66802） | G9 対 USD、1999–2018、5 分の TRTH 気配（D5・CME で確認） | WP（Table 3・8 を含む）。出版版は abstract |
| L2 | Evans "Forex trading and the WMR Fix" | J. Banking & Finance 87 (2018) 233–247 | MPRA 81583 | 21 pair、2004–2013、1 分の Gain Capital（retail）の mid + EBS | F（Table 6） |
| L3 | Melvin & Prins "Equity hedging and exchange rates at the London 4 p.m. fix" | J. Financial Markets 22 (2015) 50–72 | ECB workshop 版 WP（2013-11） | G10 の 10 通貨、2004-04〜2012-12、5 分の EBS / Reuters | WP（係数は出版版で未確認） |
| L4 | Ito & Yamada "Puzzles in the Tokyo fixing in the forex market" | J. Int. Econ. 109 (2017) 214–234 | NBER w22820 | EBS Level 5、2006–2013（USD/JPY は 1999〜） | 本文の一部（data・spike・結論・Figure 6 の説明） |
| L5 | Ito & Yamada "Did the Reform Fix the London Fix Problem?" | NBER w23327 (2017) | nber.org/papers/w23327 | EBS Level 5、8 pair、2006-01〜2016-06（改革後は約 16 回の月末） | F（Table 2 は PDF の変換が崩れ、pair の対応は不確か） |
| L6 | Breedon & Ranaldo "Intraday patterns in FX returns and order flow" | J. Money, Credit and Banking 45(5) 2013, 953–965 | SNB WP 2011-04 | EBS、1997-01〜2007-06、6 pair、時間足 + BNP の顧客 flow 2005–07 | F（Table 2〜4） |
| L7 | Ranaldo "Segmentation and time-of-day patterns in foreign exchange markets" | J. Banking & Finance 33(12) 2009, 2199–2206 | SNB WP 2007-03 | Reuters FXFX の気配、4 時間の区間、1993–2005 | WP 本文（Table 4・cost の節） |
| L8 | Evans & Lyons "Order Flow and Exchange Rate Dynamics" | JPE 110(1) 2002, 170–180 | NBER w7317 | D2000-1 の dealer 間の取引、DM/$・¥/$、1996-05〜08、日次 | abstract + 本文の一部 |
| L9 | Evans & Lyons "How is macro news transmitted to exchange rates?" | JFE 88 (2008) | NBER w9433 | 同上 + Reuters のニュース | abstract + data の節 |
| L10 | Love & Payne "Macroeconomic news, order flows, and exchange rates" | JFQA 43(2) 2008, 467–488 | doi:10.1017/S0022109000003598 | dealer 間の取引 | A |
| L11 | Menkhoff, Sarno, Schmeling, Schrimpf "Information flows in foreign exchange markets" | J. Finance 71 (2016) 601–634 | City Research Online 13781 | 大手 1 行の顧客 flow、15 通貨、2001–2011、日次 | F |
| L12 | Andersen, Bollerslev, Diebold, Vega "Micro effects of macro announcements" | AER 93(1) 2003, 38–62 | NBER w8959 | 5 分の Reuters、5 通貨対 USD、1992–1998 | F |
| L13 | Elaut, Frömmel, Lampaert "Intraday momentum in FX markets" | J. Financial Markets 37 (2018) 35–51 | SSRN 2694985 | RUB/USD（MICEX）、2005–2014、tick | A（本文は入手できず） |
| L14 | Gao, Han, Li, Zhou "Market intraday momentum" | JFE 129 (2018) | SSRN 2440866 | SPY（株）、1993–2013 | WP（市場をまたいだ参考） |
| L15 | Bessho, Sugimoto, Suzuki（gotobi） | arXiv:2301.13204（**査読なし**） | arxiv.org/abs/2301.13204 | USD/JPY、2018–2020 | 本文（効果量は図だけ） |
| L16 | FSB "Foreign Exchange Benchmarks – Final Report" | FSB 2014-09-30 | fsb.org/2014/09/r_140930/ | 制度 | F |
| L17 | Camanho, Hau, Rey "Global Portfolio Rebalancing and Exchange Rates" | RFS 35(11) 2022 | NBER w24320 | 月次・fund 単位 | A |
| L18 | Chaboud et al.（指標発表と EBS） | Fed IFDP 823 (2004) | federalreserve.gov/pubs/ifdp/2004/823 | EUR/USD・USD/JPY、1999–2004 | A |

**確認できなかったもの**: Lyons の教科書（注文の分割の理論）、2015 年より後の月末の株式ヘッジの学術研究（Ito & Yamada の約 16 回を除く）、G10 の OTC 市場での日中の momentum の効果量、FX の発表の後の drift を報告する査読論文（見つからなかった）。

## 7. FX Fixing

**制度**【原典 L16・L5】:

- WMR の London 16:00 fix は、2015-02-15 から 5 分の窓（15:57:30〜16:02:30 London）になった（FSB の勧告 1）。
- ET では通常 11:00（英米の夏時間のずれの週は 10:00 / 12:00）。
- 東京の仲値は 9:55 JST（ET で 20:55、米国の夏時間中は 19:55）。ECB は 14:15 CET。

**fix の前後の dollar の W 字**【原典 L1】:

- 仕組み: dollar の需要に応じる dealer が、在庫の保有に対価を取る。
- dollar は各 fix の前に上がり、後に下がる。等しい重みの dollar の portfolio で:

  | 区間 | 効果 |
  | --- | --- |
  | 17:00 ET → 東京の仲値 | +2.1 bp / 日（t = 12.0） |
  | 東京の仲値の後 | −2.2 bp / 日（t = 9.2） |
  | 02:00 ET → London fix | +1.7 bp / 日（t = 4.1） |
  | London fix → 17:00 ET | −1.9 bp / 日（t = 5.5） |

- EUR は London fix の後に年 7.22% 上がる（約 2.9 bp / 日）。
- Europe の窓は不安定（火曜で t = 1.42、8〜10 月は有意でない）。
- **cost の後（Table 8、indicative の bid / ask の全額）**:

  | 取引 | gross | 全 spread | 50% の spread |
  | --- | --- | --- | --- |
  | EUR（ECB / London 周辺） | 年 13.75% | **−0.55%** | +6.6%（Sharpe 0.70） |
  | GBP（London） | 11.23% | **−2.74%** | — |
  | JPY（東京） | 12.87% | **−6.13%** | — |

  CME の firm な気配（2009–18）では、EUR +6.11%、GBP −4.83%、JPY −8.82%。
- 著者の結論（本文の 938 行目付近）: "returns from trading a relatively small window around the fix are usually more than offset by transaction costs"。東京の反転の戦略は、2013 年頃より後に EUR・GBP で負。

**月末の fix の周辺の反転**【原典 L2・L5】:

- 月末の fix の前後の価格変化は負の系列相関を持つ。
- Evans の取引規則は、**fix の価格で cost 0 で入る**という仮定で、pair によって混在（EUR/USD 15 分は年 +3.97%、GBP・JPY は負）。
- Ito & Yamada は、改革の後も「月末の利益は still available、15 分の保有は even stronger」とするが、根拠は約 16 回の月末だけで、窓の終わり（16:02:30）の直後の分単位の入りが前提。
- 月内（intra-month）は改革の後、全ての pair で負（EUR/USD −0.52 / −0.40 / −0.86 bp）。

**個人投資家が使える情報**: fix の時刻と月末の日付は公開されていて、事前に分かる。方向は W 字なら無条件（前は dollar 高、後は dollar 安）。

**既存の clock flow との重複**:

- #474 は同じ時刻（London fix・東京の仲値）の前後 1 時間を、ランダムな方向で測った。
- 毎日の窓は、損益分岐の gross IR が 4〜59 で不可能と記録している。これは L1 の「cost に負ける」と整合する。
- 月末の London fix の前の窓は、経済性は最良だが検出力が無い（C04 / C05 として停止中）。

## 8. Month-End Rebalancing

**仕組み**【原典 L3】:

- 株式の運用会社は、月の最後の 16:00 fix で通貨の hedge を再設定する。
- 注文は fix の約 1 時間前に銀行に届き、その大きさは月末の前日の株価の終値で決まる。

**回帰の結果**【原典 L3】:

- 月の最終営業日の 15:00〜16:00 London の通貨の return を、月末の前日までのその国の株式の月初来 return（どちらも横断面の平均に対する相対値）で回帰した。
- 係数 −0.0142（p = 0.00）、**R² = 0.03**。著者の言い換え: "a 10% equity appreciation leads to 14 basis points of currency depreciation"、"this seems like quite a small effect"。
- 16:00 から翌日の正午までに、fix の前の 1 時間の動きの約 72% が戻る。

**事前の予測可能性**:

- ある。前日の公開の株価の終値で、entry（15:00 London = 10:00 ET、ずれの週は 09:00 ET）の前に方向が決まる。
- ただし相対の株価の return の典型的な大きさは、原典から確認していない。
- cost は差し引かれておらず、取引規則も検定されていない。sample は 2012 年まで。

**Camanho, Hau, Rey**【A のみ】: fund 単位・月次の rebalancing と為替の関係で、日中の時刻の結果は無い。M15 の取引には使えない。

**既存の研究との重複**:

- #474 の月末の cell（方向はランダム、検出力不足）
- C05（停止中で、新しい提案から外されている）
- 株式を条件にした月末の hedge の flow（S21、停止中の family として除外）
- PATSD の F3（51 回、検出力が低い）

## 9. Institutional Order Flow

**原典で確かめたこと**:

| 文献 | 結果 | 公開されているか |
| --- | --- | --- |
| L8 | dealer 間の注文 flow は、日次の為替の変化の 64%（DM）・45%（¥）を同時点で説明する | 非公開。同時点の説明で、予測ではない |
| L9 | 指標の効果の少なくとも半分は flow を通じて価格に入る | 非公開 |
| L10 | 定時の発表の情報の約 3 分の 1 が flow を通じて取り込まれる | 非公開（abstract のみ） |
| L11 | 遅らせた顧客の flow で並べた long-short が年 10〜12%（Sharpe 1.3〜1.5）、bid / ask の後も有意。情報は数日で薄れる | **大手 1 行の顧客 flow で非公開** |

**評価**: 予測力のある結果は全て、非公開の flow を使っている。公開の価格から flow を推定する方法の、FX での実証は見つからなかった。注文の分割執行（Lyons）の理論の原典は確認できていない。測られた事実（VR < 1、IC 負）は、分割執行による数時間の継続の痕跡と逆である。

## 10. その他の有力メカニズム

1. **自国の取引時間の自国通貨安**【原典 L6・L7】:
   - 通貨は自国の取引時間に下がり、相手国の取引時間に上がる。
   - L6 の Table 2（EBS の mid、年率）: EUR/USD は EUR の時間に −8.4%、USD の時間に +10.0%（どちらも 1% 有意）。GBP/USD は −7.1% / +9.2%。
   - **EBS の firm な bid / ask を払った後は、EUR/USD だけが正**（Sharpe 1.3（朝の short）・0.9（午後の long））。他の pair は cost の後で負。
   - 仕組みは、地元の顧客が地元の時間に自国通貨を売る注文 flow で、flow で条件付けると残りの pattern は消える（Table 3）。
   - L7: EUR/USD の規則は、往復約 4 pip の cost まで正。
   - sample は 2005 年 / 2007 年まで。
2. **東京の仲値・gotobi**:
   - 【原典 L4】顧客の注文は dollar の買いに偏り、9:55 の直前の数秒〜数分で数 bp 上がり、数秒で戻る。仲値で切り替える 5 分 long → 5 分 short は平均 1.8 bp で、"slightly above the transaction cost"。
   - 【L15、査読なし】gotobi の日の 3:00〜9:55 JST の上昇を報告する。
3. **指標の発表の後の drift**:
   - 【原典 L12】価格の調整は "a jump immediately following the announcement, and little movement thereafter"。L18 も同様（abstract）。FX で 30 分後以降の drift を報告する査読論文は見つからなかった。
4. **日中の momentum**:
   - 【L13 は abstract のみ】RUB/USD の取引所。【L14】は株。G10 の OTC での効果量は確認できなかった。

## 11. 過去研究との重複監査

| 仮説の family | 重なる既存研究 | 既存研究での状態 | 区分 |
| --- | --- | --- | --- |
| 毎日の fix の W 字（L1） | #474 の毎日の窓（ランダムな方向、損益分岐 IR 4〜59）、R-A2b の NY の cost | 方向は未検定。経済性は既存の測定で不可能に近い | 経済性の部分は重複。方向は新規だが §13 で不合格 |
| 月末の fix の前の株式ヘッジ（L3） | #474 の月末の cell、C05（停止中・新規提案から除外）、S21（停止中の family）、PATSD F3 | 方向は未検定。**検出力の不足が拘束条件** | 重複（`DUPLICATE_OF_PREVIOUS_RESEARCH` + §13） |
| 月末の fix の後の反転（L2・L5） | #474 の London fix の後の窓 | 分単位で、M15 の cell では測れない | — |
| 注文 flow・分割執行（L8〜L11） | S1（除外）、R-A2b §12、Round 1 の session gate | 数時間の継続は VR < 1 に反する（検出力は十分） | 重複 + 実装不能 |
| 自国時間の自国通貨安（L6・L7） | Round 1 / Round A の session の分割（他の signal の gate として負）、C03（session の引き継ぎ、未検定） | **方向の仮説としては一度も検定していない** | 新規。§13 で不合格 |
| 東京の仲値・gotobi（L4・L15） | #474 の `tokyo_fix` の cell | 方向は未検定。毎日の損益分岐 IR 8.5〜8.9 | 経済性で重複 |
| 指標の発表の後の drift（L12） | #472、#473（**検出力のある帰無**）、#477、S2（保留） | US の 1 時間の surprise の方向は帰無 | 重複 |
| 日中の momentum（L13・L14） | S1（除外）、Round 1 の trend（gross 負）、B′ の VR < 1 | 反証（検出力は十分） | 重複 |

**否定と検出力の不足の区別**:

- 反証（検出力あり）は、数時間の継続（S1 と日中の momentum）と、US 08:30 の発表の 1 時間の方向（#473）。
- 検出力の不足は、月末の fix（C04 / C05）、CPI だけ（#472）、非 USD（#477）。
- 後者を、検出力の不足だけを理由に再探索することはしない。

## 12. 文献から確認した効果量

全て【原典】。bp / 日は著者の年率を 252 で割った換算を含む（その場合は換算と書く）。

| 仕組み | 効果（gross） | cost の扱い（原典） | 期間 |
| --- | --- | --- | --- |
| London fix の前の dollar（L1） | +1.7 bp / 日（basket） | Table 8: 全 spread で EUR・GBP・JPY とも負 | 1999–2018 |
| London fix の後の dollar 安（L1） | −1.9 bp / 日（basket）。EUR は +2.9 bp / 日（換算） | 同上 | 同上 |
| 東京の仲値の前後（L1・L4） | ±2.1〜2.2 bp / 日。5 分 + 5 分で 1.8 bp | JPY は全 spread で −6.13% / 年。L4 は「cost をわずかに上回る」 | 1999–2018 / 2006–13 |
| 月末の株式ヘッジ（L3） | 相対の株価の 10% につき 14 bp、R² = 0.03 | 無し | 2004–2012 |
| 月末の fix の後の反転（L5） | 月末 15 分で約 +2〜4 bp（pair の対応は不確か）、月内は負 | EBS の bid / ask を含むが、窓の終わりの直後の分単位の入り | 2006–2016-06 |
| 自国時間の自国通貨安（L6） | EUR/USD は年 −8.4% / +10.0%（約 3〜4 bp / 日、換算） | EBS の bid / ask の後、EUR/USD だけ正（Sharpe 1.3 / 0.9） | 1997–2007 |
| 指標の発表（L12） | 1 SD の雇用統計の surprise で DM/$ 約 0.16%、ただし即時 | — | 1992–1998 |
| 顧客の flow（L11） | 年 10〜12%、Sharpe 1.3〜1.5 | bid / ask の後も有意 | 2001–2011（非公開の flow） |

## 13. FX デイトレードとしての採算性

**使う cost**（【既存の実測】Cycle 1 / R-A2b、seen 2021–2025、20 pair の中央値）:

| 時間 | round-trip の spread |
| --- | --- |
| NY の 09:00〜09:30 の entry | 1.65 bp |
| EUR_USD の 09:00 | 1.36 bp |
| NY の 11 時台（London fix の時刻） | 1.64 bp |
| NY の 16 時台（当日決済の最後） | 2.54 bp |
| rollover（17 時台） | 9.2 bp |

- slippage は往復 0.5 bp、stress は 1.0 bp。
- **これは R-A2b が測った時間帯の値で、それ以外の時間帯（東京の仲値・London の朝）には使わない**。そこは評価不能と書く。
- 研究上の要求（R-A2b と同じ式）: 必要 gross / σ = cost / σ + S / √(k · n)、S = 1.0。

**評価**【算術。効果量は原典、σ と cost は既存の実測、仮定を明記】:

**(a) London fix → 16:45 ET の dollar 安（L1）**:

- 効果: basket 1.9 bp / 日、EUR 2.9 bp / 日（1999–2018 の平均。原典は全 spread で負）。
- σ: Cycle 1 の時刻ごとの M15 の vol（中央値）を 11:00〜16:45 の 23 本で合成し、√Σσ² ≈ 22 bp（自己相関 0 の仮定。VR < 1 なので実際はこれより小さい）。
- cost: (1.64 + 2.54) / 2 + 0.5 ≈ 2.6 bp。cost / σ ≈ 0.12。
- 追加分: dollar の basket は 1 つの因子なので k ≈ 1、n = 250 で 1/√250 = 0.063。
- 必要 gross / σ は約 0.18。効果の gross / σ は EUR で 2.9 / 22 ≈ 0.13、basket で 0.09。
- **不足**（`ECONOMICALLY_UNATTRACTIVE`）。原典の全 spread の結果（負）と整合する。

**(b) 月末の株式ヘッジ（L3）**:

- 原典の R² = 0.03 から、予測の相関は √0.03 ≈ 0.17。符号で取引する場合の、trade あたりの期待 gross / σ は約 0.17 × √(2/π) ≈ 0.14【算術。予測値が正規分布の場合】。
- cost: 月末の London fix の前の 1 時間の σ は 12.6〜17.4 bp【既存の実測、#474】。fix の時刻の round-trip の spread は 2.0〜2.1 bp【既存の実測、#474】に slippage 0.5 を足す。cost / σ は約 0.15〜0.21。
- **cost だけで、期待 gross を上回るか同程度**。n = 12 回 / 年の追加分（k = 3 なら 1/√36 = 0.17）を入れると、大きく不足する。
- `ECONOMICALLY_UNATTRACTIVE`。月末の fix の時刻の retail の spread の拡大は、この見積もりに入っておらず、更に不利。

**(c) 自国時間の自国通貨安、EUR/USD の USD の時間の long（L6）**:

- 原典の net（EBS の bid / ask の後）は年 +7%、Sharpe 0.9 なので、strategy の年率の vol は約 7.8%。
- retail の追加の cost: OANDA の EUR_USD の round-trip 1.36 + 0.5 bp に対し、EBS の内側の spread は約 1 bp と仮定する【推論】。差の約 1 bp × 250 日 ≈ 年 2.5%。
- net は約年 4.5%、**Sharpe は約 0.6（1997–2007 の平均、公表の後の減衰を考える前）**【算術】。
- 単一の pair で、他の pair は cost の後で負（breadth なし）。G4（縮小後 1.0）に届かない。
- `ECONOMICALLY_UNATTRACTIVE`（最も近いが不足）。

**(d) 東京の仲値の W 字（L1・L4）**: 17:00 ET の rollover の直後から入る必要があり、rollover の spread（9.2 bp）を避けると効果の大部分を逃す。東京の時間の spread の実測は R-A2b の範囲に無く、**評価不能**。原典の JPY は全 spread で −6.13% / 年。

**(e) 月末の fix の後の反転（L2・L5）・仲値の spike（L4）**: 効果は窓の終わりの 1〜15 分の中にあり、M15 の entry（11:15 ET の bar）では大部分を逃す。`NOT_IMPLEMENTABLE_WITH_AVAILABLE_INFORMATION`（解像度）。

**情報の公開から entry までの損失**: 指標の発表は数分で調整が終わる（L12）ので、M15 の終値の後の entry では、効果の大部分が既に失われている。fix 系は時刻が事前に分かるので損失は無いが、効果そのものが cost と同程度である。

## 14. 実装可能性

| 仕組み | 情報は公開か | 事前に分かるか | M15 で判断できるか | 当日決済できるか |
| --- | --- | --- | --- | --- |
| fix の W 字 | 時刻だけ（公開） | 可 | 可 | 可（London fix → 16:45） |
| 月末の株式ヘッジ | 株価の指数の終値（公開。ただし data の取得が要る） | 前日の夜に可 | 可（10:00〜11:00 ET） | 可 |
| fix の後の反転 | 公開 | 可 | **不可**（分単位） | 可 |
| 東京の仲値 | 公開 | 可 | **不可**（spike は秒単位、9:55 は M15 の境に無い） | 取引日の始まりに当たり、rollover の spread と衝突 |
| 自国時間の自国通貨安 | 時刻だけ | 可 | 可 | 可 |
| 顧客の注文 flow | **非公開** | — | — | — |
| 指標の発表の drift | 公開 | 発表の後 | 調整は数分で終わる | 可 |

## 15. 候補の比較

採用条件（裁定 §11）: (1) 機構、(2) 原典の実証、(3) 公開の情報、(4) M15、(5) 当日決済、(6) cost を超える可能性、(7) 非重複、(8) 追加の FX 履歴で検証できる。

| 仕組み | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 区分 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 毎日の fix の W 字 | ○ | ○ | ○ | ○ | ○ | **×**（原典で全 spread は負、§13a） | △ | △ | `ECONOMICALLY_UNATTRACTIVE` |
| 月末の株式ヘッジ | ○ | ○（2012 年まで） | ○ | ○ | ○ | **×**（§13b） | **×**（C05 停止中・新規提案から除外） | **×**（年 12 回、検出力の不足が拘束条件） | `DUPLICATE_OF_PREVIOUS_RESEARCH` / `ECONOMICALLY_UNATTRACTIVE` |
| 月末の fix の後の反転 | ○ | △（改革の後は約 16 回） | ○ | **×** | ○ | — | △ | × | `NOT_IMPLEMENTABLE_WITH_AVAILABLE_INFORMATION` |
| 東京の仲値・gotobi | ○ | ○（spike）/ △（長い drift は査読なし） | ○ | **×** | △ | ×（JPY は全 spread で負） | △ | — | `NOT_IMPLEMENTABLE_WITH_AVAILABLE_INFORMATION` / `INSUFFICIENT_EVIDENCE` |
| 自国時間の自国通貨安 | ○ | ○（2007 年まで、EUR/USD だけ） | ○ | ○ | ○ | **×**（retail で単一 pair の Sharpe 約 0.6、§13c） | ○ | △（pre-2016 の履歴は原典の期間と重なる） | `ECONOMICALLY_UNATTRACTIVE` |
| 機関の注文 flow | ○ | ○ | **×** | — | — | — | — | — | `NOT_IMPLEMENTABLE_WITH_AVAILABLE_INFORMATION` |
| 指標の発表の drift | △ | **×**（drift の実証なし） | ○ | × | ○ | — | **×**（#473 の検出力のある帰無、S2 保留） | — | `INSUFFICIENT_EVIDENCE` / `DUPLICATE_OF_PREVIOUS_RESEARCH` |
| 日中の momentum | △ | **×**（G10 OTC で未確認） | ○ | ○ | ○ | — | **×**（S1・VR < 1） | — | `INSUFFICIENT_EVIDENCE` / `DUPLICATE_OF_PREVIOUS_RESEARCH` |

## 16. 最終候補と採用・除外の理由

**最終候補: 0 件。** 全ての仕組みが、少なくとも 1 つの必須の条件を満たさない（§15）。採用条件は緩めていない。

「候補に最も近い」のは自国時間の自国通貨安（EUR/USD）だが、次の理由で不足する。

- 原典の net が interdealer の cost で、retail の cost を入れた最良の推定が単一の pair で Sharpe 約 0.6。
- 他の pair は原典で cost の後に負で、breadth が無い。
- 原典の期間（〜2007）の後の減衰が未知。L1 では、関連する東京の反転の戦略が 2013 年頃より後に負になっている。

## 17. 統計的な検証可能性

候補が残らないので、検証の設計は作らない。参考として、仮に自国時間の効果を検証する場合の問題を記録する。

- **net の効果 / σ が小さすぎる**: trade あたり約 0.04（Sharpe 0.6 を √250 で割る）。片側 5% の検定で検出力 80% を得るには、(2.49 / 0.04)² ≈ 3,900 日 ≈ 15 年の独立な data が要る【算術】。
- **時期の独立性が足りない**: pre-2016 の OANDA の履歴（2006〜2016）は、原典の期間（1997〜2007、KMW は 1999〜2018）と重なり、文献から独立な検証にならない。公表の後の独立な期間は、fresh（保護）と seen（使用済み）に当たる。

**帰無の案 C の問題**（裁定 §13 の整理）:

- 固定の entry 時刻に依存する。
- entry 時刻の違う候補をまとめた同時の帰無を作りにくい（全ての境で区間を分けると、保有中の依存が壊れる）。
- 前日以前の情報を使う規則に使えない。
- 保有中の return の条件付きの対称性を仮定する。

**限定的な検討の候補として維持する**が、標準の方式にはしない。実装と較正はしない。

## 18. 候補が残った場合の事前登録案

**該当しない**（候補 0 件）。

## 19. 候補が残らない場合の保留判断

**推奨: `FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE`。**

- 意味: FX デイトレードが不可能なのではなく、現在の知識と data では、追加の研究と開発の費用を投じる独立した経済的根拠が足りない。
- 文献の最も強い証拠（KMW）自身が、retail に近い cost では fix の取引が負になることを示している。
- この repo の既存研究（Round 1・B′・#473・Cycle 1・R-A2b）とも矛盾しない。
- 候補が残らなかったので、**別の戦略を追加して研究を続けることはしない**。Human が改めて指示するまで、研究を止める。

**維持するもの**:

- data の分割の方針（新しい履歴の前半で選択・後半で推定・fresh で確認）
- G4（縮小後 Sharpe 1.0）
- prior の未凍結（懐疑的な prior を主の検討案、他は感度）
- 帰無の案 C の限定的な扱い

どれも閾値は変えない。

**将来の再開の条件**【推論・提案】。次のどれかが新しく得られた場合に、Human が改めて判断する。

- (a) 原典で、retail の cost の後に正の、公開の情報だけの日中の FX の効果が報告される。
- (b) 執行の cost が大幅に下がる（例: 往復 1 bp 以下の執行の手段）。
- (c) 公開の情報で、機関の flow を事前に予測できる新しい data の source。

## 20. 独立レビュー結果

（下に記録する。）

## 21. Human + ChatGPT への判断依頼

1. **`FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE` を採るか**（FX デイトレードの研究を長期の保留にし、新しい指示まで止める）。
2. **保留の期間に維持するもの**: data の分割の方針・G4 の 1.0・prior の未凍結・帰無の案 C の限定的な扱いを、記録としてそのまま維持するか。
3. **再開の条件**（§19 の (a)〜(c)）を、将来の再開の判断の基準として記録するか。

### 裁定 §18 の問いへの回答

| 問い | 回答 |
| --- | --- |
| Q1. 文献で実証され、現在の個人投資家が利用できる FX デイトレードの仕組みはあるか | 文献で実証された時刻の仕組みはある（fix の W 字・自国時間の自国通貨安・月末の株式ヘッジ）。公開の情報で使えるものもある。しかし**現在の retail の cost の後に利益が出ると原典で示されたものは無い**（KMW は全 spread で負、B&R は interdealer の cost で EUR/USD だけ正） |
| Q2. 既存研究で既に否定されていないか | 数時間の継続（S1・日中の momentum）と、US の発表の 1 時間の方向は否定済み（検出力あり）。月末と fix は、方向は未検定だが、検出力の不足が拘束条件と記録済み（C04 / C05 停止中）。自国時間の自国通貨安は、方向の仮説としては未検定 |
| Q3. 効果量は現実の cost に比べて十分か | **不十分**。効果は 1.7〜4 bp / 日（gross）で、retail の往復 2.2〜2.6 bp と同程度。研究上の要求（cost / σ + 1/√(kn)）を満たすものは無い（§13） |
| Q4. 追加の FX 履歴を取得して検証する価値のある仮説が残ったか | **残っていない** |
| Q5. 候補が残った場合の最小の研究範囲 | 該当しない |
| Q6. 候補が残らなかった場合、長期保留にすべきか | **すべき**（`FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE`） |

---

**STOP（裁定 §21）。** 新しい指示まで何も実行しない。
