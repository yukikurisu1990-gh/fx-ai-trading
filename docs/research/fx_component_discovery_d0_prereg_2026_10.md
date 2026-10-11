# FXID_REOPEN_FOR_COMPONENT_DISCOVERY — D0 事前登録（2026-10-11、文献の探索の前）

**この文書は、新しい文献の探索（D1）を始める前に commit する。** 予算・既存の inventory・重複の分類・D1 の gate・ranking の規則・机上の経済性の方法・机上の kill の規則を固定する。結果を見て変えない。

権限: `docs/governance/fxid_limited_reopen_component_discovery_2026_10.md`。

## 1. 予算

| 項目 | 上限 |
| --- | --- |
| D1 の family | 5 |
| D3 で実証に進める family | 3 |
| family ごとの仮説 | 2 |
| family ごとの variant | 3 |
| data の取得の package | 2 |
| fresh | 0 |
| production | 0 |

## 2. 既存の inventory（重複の監査の基準）

**P1（PR #506）の 15 の family**（`scripts/research/fx_system_reopen_feasibility/prereg.py` の `FAMILIES`）:

| family | 中身 |
| --- | --- |
| F1 | dollar の日中の W 字 / fixing の在庫（EUR の欧州の朝、JPY の仲値の後、EUR の ECB の後） |
| F2 | 自国時間 / 顧客の flow |
| F3 | 機関の注文 flow |
| F4 | 月末の株式ヘッジ |
| F5 | fix の後の反転 |
| F6 | 東京の仲値の spike / gotobi |
| F7 | 指標の発表の repricing |
| F8 | 日中の momentum |
| F9 | 短期の平均回帰 |
| F10 | session の引き継ぎ |
| F11 | option cut |
| F12 | carry |
| F13 | cross-sectional / 時系列の momentum |
| F14 | classical premia の合成 |
| F15 | その他の日次の研究（T-R / T-R2 / T-V / Top-Five / next-five / M16） |

**それ以外の記録**:

| 区分 | 研究 |
| --- | --- |
| Round | Round 1（#464）、Round A（#468）、Round B′（#469 / #470） |
| inventory | C03 / C04 / C05（#478）、H-002 |
| PR | #471〜#497（#471 carry、#472 / #473 指標、#474 clock flow、#475 執行、#477 非 USD の指標、#479〜#482 model・Track 1、#484〜#488 T-R・T-V、#489 rerank、#490〜#495、#496 ledger、#497 classical premia） |
| 直近の cycle | PATSD Stage 0（#499）、FXID Cycle 1（#501）、R-A2b（#502）、#503 の文献（L1〜L18）、#505、#506 |

## 3. 重複の分類（`MECHANISM_ID` ごと）

| 分類 | 扱い |
| --- | --- |
| `GENUINELY_NEW` | 候補にできる |
| `PARTIAL_OVERLAP` | 重なりを明記して候補にできる。F1 との重なりは §5 の (8) で減点する |
| `DUPLICATE` | 候補にしない |
| `PREVIOUSLY_REJECTED` | 候補にしない |
| `IMPLEMENTATION_ONLY_DIFFERENCE` | 候補にしない（同じ mechanism を pair・時刻・indicator・保有期間だけ変えたもの） |
| `HORIZON_ONLY_DIFFERENCE` | 候補にしない |

**mechanism の記述の必須項目**: 誰が・なぜ・いつ・どの市場構造で・どちら側に価格の圧力を生むか。indicator の組み合わせ・stop の違い・保有期間の違い・ML の model・閾値・pair ごとの調整は、mechanism ではない。

## 4. D1 の gate（全て満たす候補だけ D2 へ）

1. economic mechanism が明確
2. 原典の実証の証拠がある（査読論文・NBER / CEPR などの working paper・中央銀行・BIS・定評ある学術の著者・取引所 / benchmark の管理者・信頼できる機関の研究。ブログ・SNS だけは不可）
3. FX である
4. retail が観測できる情報で実装できる
5. 日中・当日決済で成立しうる
6. 既存の family の duplicate ではない
7. 原典で、gross の効果が取引の cost より十分に大きい可能性がある
8. 最近の市場でも消えたことの強い証拠が無い
9. 独立な検証の経路がある

## 5. ranking の規則（5 を超えた場合、上位 5 だけ）

10 の基準をそれぞれ 0 / 1 / 2 で採点し、優先順位に応じた重み（10, 9, …, 1）で加重和を取る。同点は基準 1 から順に比べる。**Sharpe の大きさだけで順位を付けない。**

| # | 基準 | 2 点 | 1 点 | 0 点 |
| --- | --- | --- | --- | --- |
| 1 | mechanism の強さ | 支払う主体と理由が具体的で、制度で時刻が決まる | 主体は示されるが、時刻か方向が曖昧 | 説明が事後的 |
| 2 | 独立な証拠の質 | 2 つ以上の独立な原典（査読を含む） | 1 つの査読か、複数の WP | 1 つの WP だけ |
| 3 | post-cost の効果の大きさ | 原典で retail に近い cost の後に正 | interdealer の cost の後に正 | cost の後は未報告か負 |
| 4 | 証拠の新しさ | sample が 2015 年以降を含む | 2010〜2014 年まで | 2009 年以前まで |
| 5 | retail の観測可能性 | 公開の時刻・公開の data だけ | 公開の data だが取得が要る | 有料・非公開 |
| 6 | 実装の簡単さ | 固定の時刻・1 pair 以上で単純 | 条件付きの規則 | 複雑 |
| 7 | 予想される turnover | 1 日 1 回以下 | 1 日 2〜5 回 | それ以上 |
| 8 | F1 からの独立性 | 時刻も機構も別 | 時刻か機構の一方が重なる | 両方が重なる |
| 9 | 検証に使える履歴 | 文献の sample の外に 5 年以上 | 2〜5 年 | 2 年未満 |
| 10 | 予想される増分の portfolio の価値 | 相関が低いと予想（通貨・時刻・macro が別） | 一部が重なる | 大きく重なる |

## 6. D2 の机上の経済性の方法

**retail の cost**:

- 既存の記録（`artifacts/research/fxid_cycle1/cycle1_run2.json` の `r_a2.per_pair[pair].hourly_ny[h]`、OANDA の 2021–2025 の M15 の終値の spread の時刻の平均）の、該当する pair と時刻の往復の spread に、slippage 0.5 bp を足す。
- 記録に無い時刻や event の時刻は、R-A2b / Cycle 1 の event の倍率（08:30 の前後 ×1.44 以上など）を使い、使えなければ「評価不能」とする。

**3 つの scenario**（年率の retail の net の真の Sharpe）:

| scenario | 定義 |
| --- | --- |
| **Optimistic** | 原典の最も強い post-cost の効果を、retail の cost に置き換えたもの（haircut なし） |
| **Base** | 原典の効果（最近の原典があればそれを優先）を retail の cost に置き換え、公表の後の減衰を掛けたもの。減衰の率は、公表の後の独立な replication がある場合は 30%、無い場合は 50% |
| **Stress** | 減衰 70%、cost 1.5 倍、F1 との相関 0.5 を想定 |

**記録する量**: 原典の gross の効果・sample の期間・venue・bid / ask の仮定・執行の仮定・取引の頻度・horizon・retail の観測可能性・現代の retail の cost の推定・gross / cost の比・retail の net の範囲（O / B / S）・公表の日・減衰の懸念・既知の replication・mechanism の重なり・F1 との予想の相関。

## 7. 机上の kill の規則（D3 に進めない条件）

| # | 条件 |
| --- | --- |
| K1 | Base で、現実の retail の cost ≥ gross の効果 |
| K2 | Optimistic でも retail の net ≤ 0 |
| K3 | 非公開の dealer の data が要る |
| K4 | timing が M1 / tick 以下で、retail で実装できない |
| K5 | 文献の sample と、使える検証の data（fresh を除く）が完全に重なり、独立な検証ができない |
| K6 | 最近の証拠で明確に消えた |
| K7 | F1 と実質的に同一の mechanism |
| K8 | 年間の機会が少なすぎて、Base の net Sharpe の検出（片側 5%、検出力 80%）に、使える非 fresh の期間を超える年数が要る |

**候補が 0 でも成功とみなし、STOP する。**

## 8. D3 以降

D3 の freeze（family・仮説・方向・時刻・horizon・通貨・signal の源・執行の仮定・cost の model・variant・主の統計量・帰無・多重性・合否・取得の計画）は、D2 の後、実証の data に触れる前に、別の事前登録として commit する。
