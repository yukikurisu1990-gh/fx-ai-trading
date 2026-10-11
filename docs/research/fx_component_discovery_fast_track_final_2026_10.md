# FXID_REOPEN_FOR_COMPONENT_DISCOVERY — 最終報告（2026-10-11）

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` · `PRODUCTION_READINESS_NOT_CLAIMED`.**

**記号**:

| 記号 | 意味 |
| --- | --- |
| 【原典】 | 論文の本文・表を text に変換して読み、確認した値 |
| 【記録】 | repo に commit 済みの記録 |
| 【D2】 | `artifacts/research/fx_component_discovery/d2_desk.json`（sha256 `98d2fa07b46b91fb88be06b7b94ae34091308d9638612132ccf277714e01912a`） |
| 【算術】 | この文書の計算 |

---

## 1. Executive Summary

**最終判定: DISCOVERY-A — `NEW_COMPONENT_SUPPLY_NOT_FOUND`。STOP B（机上の経済性で全て消える）。** state は **`FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE` に自動的に戻る**。

| 段階 | 結果 |
| --- | --- |
| D1 | 3 つの独立な探索で、31 の mechanism を、原典の本文と照合しながら調べた。**D1 の gate を通ったのは 1 つの family だけ**: 中央銀行の発表の日の不確実性の premium（Mueller・Tahbaz-Salehi・Vedolin、J. Finance 2017）。2 つの探索が独立に同じ family に行き着いた |
| D2 | その family（FOMC と BoJ の 2 つの窓）は、**事前登録の kill の規則 K8（Base で判定）に当たった**: Base の検出に 104 年、使える期間 7.1 年。Optimistic と Stress は参考（下表） |

**D2 の結果**【D2】（年率の retail の net Sharpe、当日決済の窓 18:00 → 16:45 ET）:

| scenario | FOMC | BoJ | family の合成（独立と仮定） | 検出に要る年数 | 使える非 fresh の独立な年数 |
| --- | --- | --- | --- | --- | --- |
| Optimistic | 0.38 | 0.78 | 0.87 | 8.1 | 7.1 |
| Base | 0.12 | 0.21 | 0.24 | 104 | 7.1 |
| Stress | −0.04 | −0.05 | 0 | — | 7.1 |

- **2 つ以上の distinct な family という要件は、D1 の段階で既に満たせなかった**（D1 を通ったのは 1 family）。D2 は、その 1 family も机上で消えることを示した。
- **独立レビューで見つかった D2 の誤りと逸脱**（§11・§12）は、どれも Base の kill を変えない:
  - BoJ の σ の過小評価（直すと kill は強まる）
  - Optimistic の定義の逸脱（S2 を使うと Optimistic は K8 に当たらないが、kill は Base で判定する）
  - Base で差を使ったこと（事後の選択）
  - 使える年数の読み方
- **D3（候補の freeze）以降は実行していない**。data の取得（D4）も、実証（D5）も、P2 も行っていない。
- **FX のデイトレードが不可能という意味ではない**。限定の予算の中で、retail の cost の後に検証できる新しい mechanism の供給が見つからなかった、という意味である。

## 2. #506 merge record

| 項目 | 記録 |
| --- | --- |
| 確認 | OPEN、head `ba446f7`（報告と一致）、変更 11 file（予期しない差分なし）、CI `contract-tests` / `test` success、独立レビュー + 再監査が完了、未解決の BLOCKER なし |
| merge | `0de76b8e40a5…`（2026-10-11T04:24:26Z） |
| master | `0de76b8`。master の CI は success を確認してから次に進んだ |

## 3. Limited REOPEN authority

`docs/governance/fxid_limited_reopen_component_discovery_2026_10.md`（commit `2aea25d`）に記録した。

- 範囲は `NEW_COMPONENT_DISCOVERY` だけ。
- 全面的な再開ではない。
- 失敗した場合は自動的に HOLD に戻る。
- fresh（2016-06-02 … 2021-04-25）は読まない。
- trading / account を変える endpoint は禁止。
- FX のみ。
- ML による alpha の生成と、交互作用の自由探索は禁止。

## 4. Search budget

D0 の事前登録（`docs/research/fx_component_discovery_d0_prereg_2026_10.md`、`2aea25d`、文献の探索の前）で固定した。

| 項目 | 上限 | 使った量 |
| --- | --- | --- |
| D1 の family | 5 | 1（gate を通った数） |
| 実証の family | 3 | 0 |
| 仮説 / family | 2 | — |
| variant / family | 3 | — |
| data の取得 | 2 package | **0** |
| fresh | 0 | 0 |
| production | 0 | 0 |

## 5. Previous mechanism inventory

D0 §2 に固定した:

- P1 の 15 の family（F1〜F15）
- Round 1 / Round A / Round B′
- C03 / C04 / C05
- H-002
- #471〜#497
- PATSD Stage 0
- FXID Cycle 1
- R-A2b
- #503（文献 L1〜L18）・#505・#506

## 6. New literature search methodology

- 探索の空間を 3 つに分け、独立な調査役が並行して探した。
  - (1) flow・hedging・calendar・balance sheet
  - (2) option・volatility・positioning
  - (3) 市場をまたいだ伝達・macro の伝播
- 原典は、査読論文・NBER / CEPR などの working paper・中央銀行・BIS・定評ある著者・機関の研究に限った。ブログ・SNS・vendor は根拠にしない。
- PDF を text に変換して、本文と表を読んだ。要約の道具の数値は使わない（過去に数値の捏造があった）。本文を入手できなかったものは `NOT_VERIFIED` と書いた。
- **lead（この報告の作成者）が、主要な値を本文で再確認した**:
  - MTV の 10.77 / 10.30 / 41% / 17.59 / 14.77 / Sharpe 0.377 / pre-window 7.89 / post-window 2.39 / BoJ の Sharpe 1.07〜1.32
  - Lucca & Moench の "major currencies do not exhibit abnormal pre-FOMC announcement returns"
- 価格の系列は 1 つも download していない。

## 7. Full discovered mechanism list

V は `VERIFIED_FROM_TEXT`、NV は `NOT_VERIFIED`。

| 探索 | MECHANISM_ID | 原典（確認） | 結論 |
| --- | --- | --- | --- |
| (1)(3) | **CB_ANNOUNCEMENT_DAY_UNCERTAINTY_PREMIUM**（FOMC・BoJ） | Mueller, Tahbaz-Salehi, Vedolin, JF 72(3) 2017（V）。確認しない証拠: Lucca & Moench, JF 2015 Table 9（V） | **D1 通過 → D2 で K8 kill** |
| (2) | M-OV1 FX の option の取引量 → 翌日の USD | Czech, Della Corte, Huang, Wang, BoE SWP 964（2022）・CDI WP 26-01（2026）（V） | D1 で不合格（gate 4: 主の data は EMIR / DTCC の非公開の規制 data で K3、gate 5: 日次で当日決済の証拠なし、gate 7: gross ≈ retail の cost） |
| (2) | M-PIN option の strike への pinning | FX の原典なし（NV） | 不合格（gate 2・3） |
| (2) | M-GAMMA dealer の gamma | Anderegg, Ulmann, Sornette, JIMF 2022（abstract） | 不合格（vol の効果で方向なし、data が非公開） |
| (2) | M-RETAIL retail の positioning の逆張り | Kaourma et al., JIFMIM 2025（abstract）、Nolte & Nolte（V、逆の符号） | 不合格（非公開、方向が争われている、分単位） |
| (2) | M-COT CFTC の positioning | #472（記録） | `PREVIOUSLY_REJECTED` |
| (2) | M-VRP / RR 変動の premium・risk reversal | Della Corte, Ramadorai, Sarno JFE 2016 ほか（V） | `HORIZON_ONLY_DIFFERENCE`（月次） |
| (2) | M-FUT 先物 → spot の価格発見 | Rosenberg & Traub, NY Fed SR 262（V） | 不合格（秒単位、K4） |
| (1) | 四半期末の dealer の balance sheet / dollar funding | Kloks, Mattille, Ranaldo（2024）、Correa, Du, Liao | 不合格（swap / CIP の効果で spot の方向なし） |
| (1) | FX の spot と swap の流動性の波及 | Krohn & Sushko, BIS WP 836 | 不合格（cost の側だけ） |
| (1) | hedging の経路 | Liao & Zhang, IFDP 1283 | 不合格（日中・暦ではない） |
| (1) | 月末の債券の index の hedge | 原典なし | `PARTIAL_OVERLAP`（F4・F1。駆動の要因は株価ではなく index の rebalance）。原典が無いので gate 2 で不合格 |
| (1) | 日本の年度末の資金の還流 | 原典なし | 不合格（年 1 回） |
| (1) | 投信など日本の投資家の flow | 月次の論文のみ | 不合格 |
| (1) | Norges Bank の事前公表の買い | 学術の証拠なし | 不合格 |
| (1) | CLS の決済の窓 | return の証拠なし | 不合格 |
| (1) | 曜日 × 時刻 | Khademalomoom & Narayan（abstract、NV） | `IMPLEMENTATION_ONLY_DIFFERENCE`（F2 / F10） |
| (1) | 祝日の前 | 1995 年の先物の論文（abstract） | 帰無 |
| (1) | 企業の hedge・顧客の flow | L11 | 重複（F2 / F3）・非公開 |
| (1) | 介入の時刻 | — | 不合格（予測できない、年の回数が少ない） |
| (3) | OIL_TO_CAD_LAGGED_DAILY | Ferraro, Rogoff, Rossi（V）、BIS WP 551（V） | 不合格（日次、弱い・一時的） |
| (3) | CROSS_ASSET_1MIN_LEAD_LAG | Basnarkov et al.（V） | 不合格（K4） |
| (3) | TRIANGULAR_ARB_LAG | Foucault, Kozhan, Tham RFS 2017（V） | 不合格（K4） |
| (3) | SAFE_HAVEN_NEXT_DAY_REVERSAL | Ranaldo & Söderlind RoF 2010（V） | 不合格（日次、経済的な大きさの報告なし） |
| (3) | SESSION_HANDOFF_TRANSMISSION | Cai, Howorka, Wongswan IFDP 863（V） | `DUPLICATE`（F10 / C03） |
| (3) | EQUITY_DIFFERENTIAL_TO_FX | Cenedese et al. 2016（V、負） | 不合格 |
| (3) | G10_CROSS_CURRENCY_LAGGED | Harris, Shen, Yilmaz JIMF 2022（NV） | 不合格（日次 / 月次、F13） |
| (3) | 金利 → FX の日中 | 15 分以上の原典なし | 不合格 |
| (3) | US の指標 → Asia の時間 | 原典なし | `DUPLICATE`（F7） |
| (3) | vol の状態に条件付けた drift | 原典なし | `INSUFFICIENT_EVIDENCE` |
| (3) | EIA の在庫 → CAD | 原典なし（NV） | 不合格 |

## 8. Duplicate / overlap audit

**CB_ANNOUNCEMENT_DAY_UNCERTAINTY_PREMIUM: `PARTIAL_OVERLAP`**:

| 比較の対象 | 関係 |
| --- | --- |
| F7 / #472 | #472 の Stage A は、中央銀行の会合の日の**動きの大きさ**だけを測った（1.58 / 1.63 倍、方向なし）。発表の日に dollar を売る方向の検定はしていない。#473 は US 08:30 の surprise の方向で、別の mechanism（news） |
| F12 carry | 金利で並べた変種（pf3）は carry と重なる |
| F1 | 4pm → 4pm の窓は fix の時刻を含むが、主張は「他の日に対する発表の日の増分」で、mechanism は別 |

**M-OV1**（option の取引量）は `GENUINELY_NEW` だが、D1 の gate 5・7 で不合格。他の全ての候補は、§7 のとおり重複・過去の不合格・実装だけの違い・原典なしのどれか。

## 9. D1 gate

| 候補 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 結果 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CB_ANNOUNCEMENT_DAY_UNCERTAINTY_PREMIUM | ○ | ○（ただし Lucca & Moench が pre-FOMC の部分に反対） | ○ | ○ | △（原典の窓は 4pm → 4pm で 17:00 をまたぐ。当日決済の窓への移しは未検定） | ○（部分的な重なり） | △（gross 約 10.8 bp 対 cost 約 2.7 bp） | ○（消えた証拠も、残っている証拠も無い） | △（使える独立な期間が短い） | **通過** |
| M-OV1 | ○ | ○ | ○ | △ | **×** | ○ | **×** | ○ | △ | 不合格 |
| 他の全て | — | — | — | — | — | — | — | — | — | 不合格（§7） |

**D0 からの逸脱**（独立レビュー Statistics の指摘）: D0 §4 は 9 項目の**全て**を満たすことを求めるが、この候補は gate 5・7・9 が △ のまま通した。候補を進める向きに寛大な逸脱で、結果は kill なので判定に影響しない。

**ranking**: D1 を通ったのは 1 つなので、上位 5 の選択は要らない。参考の rubric の点数は 70 / 110 と 72 / 110（2 つの探索が独立に採点。M-OV1 は 60）。

## 10. Selected families

1 つ: `CB_ANNOUNCEMENT_DAY_UNCERTAINTY_PREMIUM`（FOMC と BoJ の 2 つの窓。同じ mechanism なので 1 family）。

**mechanism**【原典】:

| 項目 | 中身 |
| --- | --- |
| 誰が・なぜ | VaR に制約された金融仲介者が、世界の dollar を売って外貨を買いたい需要を仲介する。予定された発表の日には、政策金利の不確実性も負うので、その対価を求める |
| 結果 | 発表の前に外貨が安く値付けされ、発表の日を通じて期待として上がる |
| いつ | 制度の calendar（FOMC 年 8 回、BoJ） |
| 方向 | dollar（BoJ では円）を売る。高金利の通貨ほど大きい |
| **条件**（独立レビュー FX の指摘） | 下の表を参照 |
| 他の中央銀行 | MTV は、BoJ 以外の中央銀行（ECB・BoE など）に効果を見つけていない。それで FOMC と BoJ だけを対象にした |

**方向の条件**（独立レビュー FX の指摘）:

| 項目 | 中身 |
| --- | --- |
| model の条件 | 金融仲介者が dollar を売るのは、**外国の金利が米国の金利より高い場合**（MTV の本文の十分条件）。premium は金利差に比例する（命題 2） |
| 最近の体制 | 2017〜2019 年と 2022〜2025 年は、USD の金利が主要通貨の大半より高い。dol の代理では、model は符号を予測しない |
| 検証の期間への影響 | **seen の 4.7 年の大半はこの体制で、独立な検証の期間が model の前提と合わない**（K8 を強める） |
| 低金利の portfolio（pf1） | 原典でも cost の後に有意でない（net 2.13 bp、t 0.44） |

## 11. Desk economics

【原典】MTV 2017:

| 項目 | 値 |
| --- | --- |
| 市場 | G9 対 USD |
| 期間 | 1994-01 … 2013-12、FOMC 160 回 |
| 解像度 | 5 分の Olsen の気配 |
| return の窓 | 4pm → 4pm ET |
| dol の発表の日 | 10.77 bp（t 2.27）、他の日 0.47 bp、差 10.30 bp |
| 年率の Sharpe | 0.51（年 8 回で年率化） |
| interbank の bid / ask の後（Table X） | 8.02 bp・Sharpe 0.377 |
| pre-window（4pm → 2:15pm） | 発表の日 − 他の日の差 7.89 bp |
| post-window（2:15pm → 4pm） | 同 2.39 bp |
| BoJ（1998–2013、232 回、円の対価で再計算） | pf3 は発表の日 17.59 bp 対 他の日 2.82 bp（差 14.77、t 2.27）。発表の日の年率の Sharpe は pf1 1.07・pf3 1.32（年 15 回で年率化、**gross、cost の報告なし**） |

**確認しない独立な証拠**【原典】: Lucca & Moench（JF 2015）Table 9、1994-09 … 2011-03、132 回。

- pre-FOMC の 2pm → 2pm の窓で、USD-EUR −0.064%（−6.4 bp）、USD-JPY 0.083%（+8.3 bp）。どちらも標準誤差 約 5〜6 bp で有意でない。
- MTV の pre-window の 7.89 bp と同程度の大きさで、**2 通貨の検出力の低い帰無**であり、反証ではない（独立レビュー Quant・FX の指摘で「否定」から訂正）。
- 符号の向きの規約は、読んだ範囲では確認できていない。

**scenario**（D0 §6）:

| scenario | 効果 | 減衰 | cost |
| --- | --- | --- | --- |
| Optimistic | 発表の日の全体の return | なし | 1.0 倍 |
| Base | 発表の日 − 他の日（carry など毎日の部分を除く） | 50%（公表の後の独立な replication を確認できないため） | 1.0 倍 |
| Stress | 同上 | 70% | 1.5 倍 |

**retail の cost**【記録・算術】:

- 当日決済の窓: 18:00 ET（rollover の後）に入り、16:45 ET に出る。
- 往復 = (18 時台の spread + 16 時台の spread) / 2 + 0.5 bp。
- FOMC は USD の 7 major の平均 **2.66 bp**、BoJ は AUD_JPY・NZD_JPY・GBP_JPY の平均 **3.54 bp**。

**1 回の event の σ**【算術】: gross の効果 ÷（年率の Sharpe ÷ √年の回数）。FOMC 60 bp（原典の t 2.27 を再現する: 10.77 ÷ (60 / √160) = 2.27）、BoJ 51 bp。

**BoJ の σ の過小評価**（独立レビュー Quant の指摘）:

- BoJ の Sharpe 1.32 は、原典自身の t 値と整合しない。平均の t 2.76（n = 232）からは σ ≈ 97 bp、差の t 2.27 からは σ ≈ 99 bp で、記録の 51 bp の約 1.9 倍。pf3 の全期間の日次の σ も約 82 bp。
- σ ≈ 97 bp では、BoJ の Optimistic の net Sharpe は約 0.41（記録 0.78）、family の合成の Optimistic は約 0.56（約 20 年）になる。**直すと kill は強まる**。
- 記録（`d2_desk.json`）は作り直さず、この開示で扱う。

**現在の年の回数**: FOMC 8 回、BoJ 8 回（2016 年以降の決定会合）。

## 12. Cost feasibility

【D2】:

| 窓 | scenario | gross（bp / 回） | retail の cost | gross / cost | net（bp / 回） | 年率の net Sharpe | 検出の年数（80%） | K1 | K8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FOMC | O | 10.77 | 2.66 | 4.05 | 8.11 | 0.38 | 42 | 不 | **該当** |
| FOMC | B | 5.15 | 2.66 | 1.94 | 2.49 | 0.12 | 448 | 不 | **該当** |
| FOMC | S | 3.09 | 3.99 | 0.78 | −0.90 | −0.04 | — | **該当** | **該当** |
| BoJ | O | 17.59 | 3.54 | 4.97 | 14.05 | 0.78 | 10 | 不 | **該当** |
| BoJ | B | 7.39 | 3.54 | 2.09 | 3.85 | 0.21 | 135 | 不 | **該当** |
| BoJ | S | 4.43 | 5.31 | 0.83 | −0.88 | −0.05 | — | **該当** | **該当** |

**事前登録の判定**（K1・K8 は Base で判定、D0 §7）:

- Base の family の合成 0.24 → **検出に 104 年 > 使える 7.1 年 → K8 で kill**。
- K1 は Base では不該当。

**参考**（判定に使わない）:

- Optimistic 0.87（8.1 年）、Stress 0（Stress では cost ≥ gross）。
- 合成は FOMC と BoJ が独立で、最適な重みの場合の上限で、候補に有利な向きの仮定である。

**使える非 fresh の独立な期間**: 7.1 年（文献の sample の外。2014-01 … 2016-05 の 2.4 年と、seen の 2021-04 … 2025-12 の 4.7 年）。Optimistic の family の合成でも 8.1 年 > 7.1 年。

**Optimistic を参考に留める理由**（kill は Base で判定するが、境界に近いので開示する。8.1 対 7.1）:

- Optimistic は 2013 年に終わる sample の、全体の return（carry を含む）の値。
- BoJ の値は cost の報告が無い gross。
- Lucca & Moench は pre-FOMC の部分を主要通貨で否定する。

Base（104 年）は、どの解釈でも K8 に当たる。

**D2 の事後の選択と感度**（独立レビューの指摘で開示。どれも Base の kill を変えない）:

| 項目 | 内容 | 判定への影響 |
| --- | --- | --- |
| Optimistic の定義の逸脱 | D0 §6 の「原典の最も強い post-cost の効果」は Table X の S2（net 19.15 bp、Sharpe 0.783）で、記録は dol（10.77）を使った。S2 を使うと FOMC の Optimistic は約 0.69、family は約 1.04（約 5.7 年）で、**Optimistic は K8 に当たらない**（BoJ の σ を直すと約 0.80・約 9.6 年で当たる）。S2 は、発表で引き締めかどうか（発表の時点で決まる）で符号を反転し、金利差が正の通貨だけを使うので、事前の実装には難がある | なし（kill は Base。S2 の Base でも family は 38 年以上） |
| Base で差（発表の日 − 他の日）を使った | D0 §6 は「原典の効果」とだけ書く。差を使うのは事後の選択で、kill の向きに偏る。根拠は、当日決済の窓は rollover をまたがず carry を得ないこと（MTV の return は金利差を含む超過 return） | なし（全体の return の Base でも family 0.32・約 60 年。公表の後の replication を認めて減衰 30% にしても 0.54・約 21 年） |
| 使える年数 7.1 | D0 の「使える非 fresh の期間」を「文献の sample の外の非 fresh の期間」と読んだ（K5 と重なる読み方）。2014-01 … 2016-05 の 2.4 年は OANDA の archive に無く、取得（D4 の 1 package）が要る。文献の期間（1994〜2013）を含めて読めば Optimistic は K8 を通るが、Base は通らない | なし |
| 窓の移し | retail の窓は前日の 16:00〜18:00 を落とすが、これは MTV の pre-window の中にある。均等に生じるなら約 0.7 bp の損失（未検定） | なし |
| dol の代理 | PAIRS_20 に NOK・SEK が無く、USD の 7 major で代理した（原典の Table I の超過 return で約 11.2 bp と同程度）。通貨が少ないので σ はやや大きいはず | なし |
| cost | 入りの 18 時台は時刻の平均で、rollover の直後の広い spread を含まず、18:00 ちょうどの約定は記録より高い可能性がある。出の 16:45 に event の日の spread の拡大を掛けていない | なし（cost を下げても Base は数十年） |
| Stress | D0 §6 の「F1 との相関 0.5」を入れていない | なし（family が 1 つ） |

## 13. Candidate freeze

**該当しない**（D2 で全ての候補が kill、D3 に進む候補が 0）。

## 14. Data acquisition manifest

**該当しない**（取得 0）。

## 15. Data provenance

新しい data の取得は無い。使った記録:

| 種類 | 記録 |
| --- | --- |
| cost | `artifacts/research/fxid_cycle1/cycle1_run2.json`（集計の記録。sha256 は【D2】の `cost_record_sha256` に保存） |
| 算術 | `scripts/research/fx_component_discovery/d2_desk.py`（commit `8349958`、13:41:56 JST） |
| 実行 | head `8349958`（commit の直後で dirty 0）、command `python -X utf8 -m scripts.research.fx_component_discovery.d2_desk`、13:41:56〜13:41:58 JST の間 |
| 記録 | `e30779a`（13:41:58 JST）、sha256 `98d2fa07…` |
| D1 の記録 | `docs/research/fx_component_discovery_d1_record_2026_10.md`（時刻の順序・原典の抽出の hash・探索の空間の対応） |

**provenance の不足の開示**（独立レビュー Adversarial Governance の指摘）:

- `d2_desk.json` 自体には、cost の記録の sha256 しか入っていない。head・dirty・timestamp・command は、上の表と git にある。
- code と記録の commit は 2 秒差で、「記録の前に code」は名目である。ただし test が記録を再計算して完全一致を要求する。
- D1 の探索の開始が D0 の後であることは、git では証明できない。証拠は、作業用の file の mtime（全て D0 の commit の後）と session の記録である。

## 16. Component tests

**該当しない**（D5 は未実行）。

## 17. Multiplicity

D1 で、31 の mechanism を、事前登録の gate と kill の規則で選別した。

- 実証の検定は行っていないので、検定の多重性の補正は発生していない。
- 探索の数そのものは、将来この family を再検討する場合の試行の数として記録する。

## 18. Independent estimation

**該当しない**。

## 19. Component gate results

**該当しない**（実証に進んだ component が 0）。

## 20. Surviving distinct families

**0**（D2 の後）。D1 の後でも 1 で、要件の 2 に届かない。

## 21. Architecture H integration

**該当しない**。

## 22. Portfolio feasibility

**該当しない**（D7 は 2 family 以上が条件）。

## 23. System prior calibration

PR #506 の契約（`τ² · tr(R⁻¹)` と tail の制約）を維持した。今回は使う段階に至らなかった。

## 24. Conditional P2

**実行しない**（D7 を通らない）。

## 25. H vs G if applicable

**該当しない**。

## 26. Final system feasibility

**不成立**（distinct な family が 0）。

## 27. Independent reviews

4 つの独立な役（指示 §34）を、別の context で並行して走らせた。互いの結論は渡していない。**4 役とも BLOCKER なし、DISCOVERY-A / STOP B を支持**（kill は Base の 104 年 対 7.1 年で、どの合理的な変種でも変わらない）。

| 役 | REQUIRED FIX | 対応 |
| --- | --- | --- |
| **Quant** | (1) BoJ の σ の過小評価（原典の t 値から約 97 bp）、(2) K8・K1 は Base で判定（「全ての scenario」は事前登録の外）、(3) Optimistic の定義の逸脱（S2 なら Optimistic は K8 に当たらない） | §11・§12・§1 に開示（kill は不変か強まる）。記録は作り直さない |
| **Statistics** | K8 の判定の枠組み（Base を先に書く） | §12・§1。NON-BLOCKING（Base の差は事後の選択、7.1 年の読み方、D1 の gate の寛大な逸脱、探索の数の不整合 29 → 31）も反映 |
| **FX Economics** | (1) 方向は金利差の条件付き（2017–19・2022–25 は体制が合わない）、(2) Lucca & Moench は % の単位で、反証ではなく「確認しない」、(3) 探索の空間の項目ごとの対応 | §10・§11・§7、D1 の記録の §3。NON-BLOCKING（他の中央銀行に効果なし、月末の債券は PARTIAL_OVERLAP、M-OV1 の gate 4 は × と K3、入りの cost） |
| **Adversarial Governance** | (1) §27 が空、(2) 記録の provenance の不足、(3) D1 の時刻を証明できない | §27 を記入、§15・§28 に開示、D1 の記録（作業用の file の mtime は全て D0 の commit の後）を commit。HOLD の裁定を sha256 で固定する test を追加 |

**修正の後の再監査**: 新しい context で確認した（結果は PR の本文に記録する）。

## 28. Governance compliance

| 項目 | 状態 |
| --- | --- |
| HOLD の裁定 | 変更なし（test で固定） |
| 限定の再開の範囲 | NEW_COMPONENT_DISCOVERY だけ。D3 以降に進んでいない |
| fresh・OOS・dead・forward の読み取り | 無し |
| 価格 data の取得・broker / OANDA の接続 | 無し（取得 0） |
| 取引・account の変更 | 無し |
| ML による alpha・交互作用の探索 | 無し |
| 予算の延長 | 無し（STOP の後に候補を足していない） |
| 事前登録 | D0（`2aea25d`）は、commit の順序で文献の探索の結果より前（探索の開始の時刻は git では証明できない。§15） |
| provenance | 記録の sha256・cost の記録の sha256・code の commit・実行の head と command（§15）。記録の file 自体の項目は不足（§15 で開示） |
| HOLD の裁定の不変 | test で sha256 を origin/master の値に固定 |
| FX のみ | はい |

## 29. Final verdict

**DISCOVERY-A — `NEW_COMPONENT_SUPPLY_NOT_FOUND`**（STOP B）。

- 限定の予算の中で、Architecture H に供給できる、retail の cost の後に検証できる新しい economic mechanism の family は、1 つも見つからなかった。D1 で 1 つ、D2 で 0。
- state は **`FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE` に戻る**。
- STOP の後に候補を足して予算を延ばすことはしない。

**記録として残すもの**（将来、再開の trigger が観測された場合の参考。今回は候補ではない）:

| 対象 | 残す理由 |
| --- | --- |
| CB の発表の日の premium | 機構は明確で、制度の calendar に固定され、retail で観測できる。年の回数が少なく、独立な検証の期間が足りない。執行の cost が大きく下がっても、Base の検出の年数は数十年のまま |
| M-OV1 | 新しい mechanism だが日次で、FX のデイトレードの範囲の外 |

## 30. Human + ChatGPT decision request

1. **DISCOVERY-A** を受け入れ、state を `FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE` に戻すことを確認するか。
2. **governance の記録**（限定の再開の範囲と、その終了）を、この PR とともに merge するか。
3. **今後**: FX のデイトレードの研究は、HOLD の裁定 §9 の再開の trigger（特に、all-in の往復の cost ≤ 1.0 bp の継続、または新しい独立な文献）が観測されるまで、何も行わないことを確認するか。

---

**STOP（指示 §40 の B）。** data の取得・実証・fresh・取引には進まない。Human + ChatGPT の承認なしに merge しない。
