# FXID_FRONTIER_EXPANSION — Track A（ORIGINAL_MECHANISM_DISCOVERY）の記録（2026-10-11）

**Role H（Hypothesis Architect）** の出力の記録。

- 別の context の agent で行った。
- **価格・return の data を読んでいない**: repo の既存の報告と、3 回の web 検索だけ。
- 使った cost と σ は、repo が既に報告した集計（Cycle 1 §11–§12、R-A2b §7–§11）だけ。
- 時刻: F0 の事前登録の commit（`53d5d9f`、2026-10-11 20:24 JST）の後に起動した。

## 1. 市場の配管の地図（ET、夏時間 / 冬時間）

| ET | 出来事 | 動く balance sheet | 理由 | 既存の inventory |
| --- | --- | --- | --- | --- |
| 17:00 | rollover / value date の roll | retail と PB の financing、LP | T+2 の roll、LP の quote の引き上げ（約 9.2 bp） | cost のみ |
| 日曜 17:00〜19:00 | 週の開始（Wellington / Sydney） | 週末の gap の risk を負う LP | 2 日分の news、薄い板 | 未登録（H-07） |
| 19:00 / 20:00 | 東京の開場 | 日本の銀行・輸出企業・投信の信託銀行 | 仲値に向けた顧客の注文 | F1 / F2 |
| 19:55 / 20:55 | 東京の仲値（9:55 JST） | 日本の企業・投信 / NISA・輸入企業（gotobi） | 契約と NAV が TTM で決まる | F1、F6 |
| 20:10 / 21:10 | 日銀の国債買入の通知（10:10 JST） | 日銀・国債のディーラー | 政策の実施 | 未登録（H-05） |
| 20:15 / 21:15 | 人民銀行の CNY の基準値（9:15 北京） | 本土の銀行・CNH のディーラー・Asia の代理（AUD / NZD） | 本土の取引の幅が基準値で決まる | 未登録（H-01） |
| 01:00〜03:00 | CLS の決済 | 決済銀行 | pay-in の期限 | #507 で不合格 |
| 03:00 | London の開場 | Asia の book・欧州の企業 | book の引き継ぎ | F2 / F10 / C03 |
| 02:00〜08:15 | 欧州の指標・ECB の参照 rate | EUR の企業・会計 | ECB の rate での請求と会計 | F1 の EUR の窓 |
| 08:00 / 08:30 / 10:00 | NY の開場・US の指標 | 全て | news | F7、#473（検出力のある帰無） |
| 10:00 | NY の option cut | option のディーラーの delta hedge | 満期の gamma | F11、M-PIN・M-GAMMA は不合格 |
| 11:00 | WMR の 4 pm fix | benchmark の運用者・index の hedge | 義務的な benchmark の執行 | F1、F4、F5 |
| 13:00 | US 国債の入札の結果 | primary dealer・海外の実需 | 金利の再評価 | 未登録（H-04） |
| 14:00（年 8 回） | FOMC | 全て | 政策 | CB premium は K8 で kill（#507） |
| 15:00 | CME の FX 先物の清算 | 先物の証拠金 | 変動証拠金 | M-FUT は不合格 |
| 月末・四半期末 | fix の rebalance・G-SIB / CIP の funding | hedge 付きの投資家・銀行 | hedge の再設定・window dressing | F4、C04 / C05 |
| 月初（2024 年以降） | NISA / 投信の積立の決済、翌日の TTM での換算 | 信託銀行経由の家計 | 目論見書が TTM での換算を求める | 未登録（H-02） |
| 6 月下旬・12 月上旬 | 日本の配当の海外の保有者への支払い | 海外の custodian | 本国通貨の mandate | 未登録（H-03） |

## 2. original な候補と Base の予測（data を使わない）

式: s = √(n·k) · (h·g − c) / σ。

| 記号 | 意味 |
| --- | --- |
| n | 年の機会 |
| k | 実効の breadth |
| g | haircut の前の gross（bp） |
| h | 直接の証拠が無いための haircut。Base 0.5、Optimistic 1 |
| c | retail の all-in の往復 |
| σ | 保有の窓の σ |

| ID | mechanism | 分類 | n × k | g | c | σ | **s_B** | Optimistic |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H-01 | CNY の基準値の surprise の Asia への伝達 | NEW_MECHANISM | 250 × 1.3 | 0.32 | 2.5 | 17 | **−2.48** | −1.96 |
| H-02 | 月初の投信の換算（東京の仲値） | NEW_INFORMATION_FOR_EXISTING_MECHANISM（F1 / F6） | 24 × 1 | 3 | 2.2 | 16 | **−0.21** | +1.16 |
| H-03 | 日本の配当の季節の円売り | NEW_MECHANISM | 10 × 1 | 4 | 2.2 | 30 | **−0.02** | +0.40 |
| H-04 | 国債の入札の結果 → USD | NEW_INFORMATION（F7）、方向が曖昧 | 100 × 1.5 | 0.4 | 1.9 | 11.6 | **−1.79** | −1.16 |
| H-05 | 日銀の買入の規模の surprise | NEW_MECHANISM | 6 × 1 | 7 | 3.0 | 40 | **+0.03** | +0.46 |
| H-06 | 公開の SDR の strike への pinning | NEW_INFORMATION（F11） | 100 × 2 | 0.8 | 2.35 | 22 | **−1.25** | −0.48 |
| H-07 | 週末の gap の流動性の反転 | **HORIZON_VARIANT（F9）**、進めない | 15 × 2.5 | 6 | 2.7 | 26 | **+0.07** | +1.48 |

- 共通の prior: price impact は約 3 bp / $1B（Evans–Lyons 2002 の 1996 年の値を、現在の厚みで約 10 分の 1 にしたもの）。分単位で価格の発見が終わる場合、M15 の entry で得られるのは 15〜25%。
- data を見ずに捨てたもの（行なし）: 週末の前のディーラーの持ち高の調整（F9 の DUPLICATE）、国債の利払いの換算（日次の取引量の約 0.03%）、CLS の pay-in（既に不合格）、IMM / MSCI の見直しの日（年 4 回以下）、くりっく 365 の建玉（M-RETAIL、既に不合格）、17:00 の rollover の歪み（約 9 bp の cost）。

## 3. ranking（F0 §4、最大 156）

| ID | 点 |
| --- | --- |
| H-02 | 112 |
| H-07 | 92 |
| H-05 | 85 |
| H-03 | 83 |
| H-01 | 81 |
| H-06 | 72 |
| H-04 | 70 |

## 4. power-first の gate（F0 §5）

| 候補 | s_B | PF1（≥ 0.58） | PF2 | PF3 | PF4 | 結果 |
| --- | --- | --- | --- | --- | --- | --- |
| 全 7 候補 | −2.48 〜 +0.07 | **×** | × | × | 一部 ○ | **全て不合格** |

**参考**: m = 0.58 での検出力は、S で約 0.35、E で約 0.43。

**F0 §5 の式の不整合**（Role H の指摘）:

- 本文の z_{1−0.10/V} と、例（V = 6 で 1.11、V = 3 で 0.98）が合わない。例は z_{1−0.05/V} に相当する。
- どちらの読み方でも、全ての候補は PF1 の段階で不合格なので、判定に影響しない。
- F0 は凍結した事前登録なので変えず、最終報告で erratum として記録する。

## 5. Role H の構造的な所見

| 種類 | 必要なもの |
| --- | --- |
| **日次の intraday の候補** | c/σ ≈ 0.06〜0.08 の下で s_B ≥ 0.76（PF2 の厳しい読み方）に届くには、0.5·g/σ ≥ 0.07 + 0.76/√250、すなわち g/σ ≥ 0.24（pair・日あたり）。cost が無い場合の gross の年率の Sharpe で、pair あたり約 3.8 |
| **比較** | 公表された最も強い intraday の FX の効果（KMW の fix の W 字）は、cost なしで 1.24〜1.82、CME の firm な気配で 0.52〜0.99 |
| **年 12〜24 回の event の候補** | 1 回あたり 10〜17 bp の残る gross が要る（σ ≈ 30 bp） |

**結論**: 直接の証拠が無い効果への 50% の haircut と retail の cost が重なると、本当に original な intraday の mechanism は、構造的に gate を通れない。通りうるのは直接の post-cost の証拠がある効果だけで、それらは既に inventory にある（主に F1）。

**Role H の推奨**: どの family も事前登録しない。
