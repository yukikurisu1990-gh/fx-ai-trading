# FXID_REOPEN_FOR_COMPONENT_DISCOVERY — D1 の探索の記録（2026-10-11）

D1（新しい mechanism の発見）の provenance を残す記録（独立レビュー Adversarial Governance・Statistics の指摘で追加）。

## 1. 時刻の順序

| 出来事 | 時刻（JST） | 根拠 |
| --- | --- | --- |
| D0 の事前登録の commit `2aea25d` | 2026-10-11 13:31:27 | git |
| D1 の 3 つの探索の起動 | D0 の commit と push の直後 | 作業の session の記録。git では示せない |
| 探索が作った原典の text の抽出（20 file） | 13:33:13 〜 13:38:50 | 作業用の file の mtime（下表）。**全て D0 の commit の後** |
| D2 の code の commit `8349958` | 13:41:56 | git |
| D2 の記録の commit `e30779a` | 13:41:58 | git |

**限界**:

- 探索の開始が D0 の後であることは、git では証明できない。証拠は、作業用の file の mtime と session の記録だけである。
- D2 の code と記録の commit は 2 秒差で、「記録の前に code」は名目である。ただし test が記録を再計算して完全一致を要求する。

## 2. 原典の text の抽出（作業用。著作権のため commit しない）

| mtime（JST） | sha256 の先頭 16 桁 | file | 原典 |
| --- | --- | --- | --- |
| 13:33:13 | a7b108ee024e0f09 | ifdp1283.txt | Liao & Zhang, Fed IFDP 1283 |
| 13:33:17 | b73314e5437e09e6 | frr.txt | Ferraro, Rogoff, Rossi, NBER w17998 |
| 13:33:29 | d9a1cefbb1de8066 | boe964.txt | Czech et al., BoE SWP 964 |
| 13:33:37 | 5898ba1d34182d62 | chw.txt | 探索 (2) の補助の資料 |
| 13:34:17 | 4306c7f32ff91a6f | cdi2601.txt | Della Corte et al., CDI WP 26-01 |
| 13:35:00 | a7f1f4e2f7a93bde | cpsv.txt | Cenedese, Payne, Sarno, Valente |
| 13:35:32 | 3753b9e9591166bf | bis551.txt | Kohlscheen, Avalos, Schrimpf, BIS WP 551 |
| 13:35:32 | 874f03f44bda1471 | ranaldo_qe.txt | 探索 (1) の四半期末の資料 |
| 13:35:52 | 4ccbf16a547b70dd | mtv.txt | Mueller, Tahbaz-Salehi, Vedolin, JF 2017 |
| 13:36:33 | 5c443eb26967204b | nolte.txt | Nolte & Nolte |
| 13:36:39 | 2070d36f6335289e | cwpe.txt | 探索 (3) の補助の資料 |
| 13:36:57 | a149491540851b5c | lm.txt | Lucca & Moench |
| 13:37:09 | 3e7d649e31090ef1 | cdl.txt | Correa, Du, Liao |
| 13:37:23 | 80ee0b7b3812ef9e | rs.txt | Ranaldo & Söderlind |
| 13:37:24 | 56a177f32c3f2e2e | boj23.txt | BOJ Review 2023-E-7 |
| 13:37:48 | 171a1d25e524a140 | vrp.txt | Della Corte, Ramadorai, Sarno, JFE 2016 |
| 13:37:55 | 0c2863990ea582b8 | sr262.txt | Rosenberg & Traub, NY Fed SR 262 |
| 13:38:16 | 0249f2b19f02c38e | cg.txt | Chen & Gwati |
| 13:38:20 | 44e2c361ab9d51da | torok.txt | Török |
| 13:38:50 | e6b944715996bf20 | ta.txt | 探索 (3) の補助の資料 |

## 3. 探索の空間の対応（指示 §7 の各項目 → 最終報告 §7 の行、または既存の family）

| 指示の項目 | 対応 |
| --- | --- |
| benchmark / fixing flow | F1・F5（既存）、Norges Bank の行 |
| dealer inventory | F1（既存） |
| commercial hedging | 企業の hedge・顧客の flow の行（F2 / F3） |
| international equity hedging | F4（既存）、月末の債券の行の比較 |
| international bond hedging | 月末の債券の index の hedge の行 |
| cross-border payment flow | CLS の行、日本の年度末の還流の行 |
| option expiry / option hedging | M-PIN・M-GAMMA の行、F11（既存） |
| volatility risk premium | M-VRP / RR の行 |
| liquidity provision | 四半期末・Krohn & Sushko の行、M-FUT の行 |
| funding / dollar liquidity | 四半期末の dollar funding の行 |
| central-bank operation timing | CB の発表の日の premium の行、Norges Bank の行 |
| intervention-related structure | 介入の時刻の行 |
| public positioning proxies | M-RETAIL・M-COT の行 |
| futures positioning transmission | M-COT・M-FUT の行 |
| macro surprise propagation | US の指標 → Asia の時間の行、F7（既存） |
| rate-differential repricing | 金利 → FX の日中の行、T-R（既存） |
| cross-currency relative value | G10_CROSS_CURRENCY_LAGGED の行、TRIANGULAR_ARB_LAG の行 |
| lead-lag between FX pairs | TRIANGULAR_ARB_LAG の行 |
| lead-lag between rates / FX | 金利 → FX の日中の行 |
| lead-lag between equity / FX | CROSS_ASSET_1MIN_LEAD_LAG・EQUITY_DIFFERENTIAL_TO_FX・SAFE_HAVEN の行 |
| commodity-currency transmission | OIL_TO_CAD・EIA の在庫の行 |
| geographic session handoff | SESSION_HANDOFF_TRANSMISSION の行（F10 / C03） |
| institutional benchmark execution | F1・F5（既存）と Norges Bank の行。**新しい原典は見つからなかった** |
| predictable liquidity demand | 投信などの日本の投資家の flow の行、Norges Bank の行。**新しい原典は見つからなかった** |
| dealer balance-sheet constraints | 四半期末の dealer の balance sheet の行 |
| settlement / calendar effects | CLS・曜日 × 時刻・祝日の前の行、F6（既存） |
| month / quarter / year-end institutional flows | 月末の債券・四半期末・日本の年度末の行、F4（既存） |
| public option-market information | M-OV1・M-VRP / RR の行 |
| volatility-state conditional premia | vol の状態に条件付けた drift の行 |

**探索した mechanism の数**: 最終報告 §7 の表の 31 行（3 つの探索の合計。重複の family は 1 行に統合）。
