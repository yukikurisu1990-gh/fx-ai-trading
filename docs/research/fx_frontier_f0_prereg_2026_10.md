# FXID_FRONTIER_EXPANSION — F0 の事前登録（2026-10-11、仮説の生成の前）

**この文書は、original な仮説の生成（Track A）と、cost の測定（Track B）を始める前に commit する。** 役割の分離・期間の構成・予算・ranking・power-first の gate・component の gate・Track B の仕様を固定する。

権限: `docs/governance/fxid_frontier_expansion_reopen_2026_10.md`。

## 1. 役割の分離（data の leakage の firewall、指示 §16）

| 役割 | 担当 | 制限 |
| --- | --- | --- |
| **Role H（Hypothesis Architect）** | mechanism と仮説を作る | **価格・return の data を読まない・計算しない**。repo の既存の報告（過去の研究の結論）と公開の文献・制度の情報だけを使う |
| **Role D（Data Custodian）** | data の入手可能性・schema・期間の被覆だけを確かめる | **条件付きの return を計算しない**。target の return を見ない |
| **Role E（Evaluator）** | 事前登録の freeze の後に、初めて target の return を読む | 事前登録の検定だけを 1 回実行する |

- H・D・E は別の context の agent で行い、指示の文面を記録に残す。
- lead は、Track B（spread だけで、target の return を含まない）と統合を担う。
- lead は、事前登録の前に target の return を計算しない。

## 2. 期間の構成（指示 §27。同じ期間を役割を変えて再利用しない）

| 役割 | 期間 | data |
| --- | --- | --- |
| **選択（S）** | **2021-04-26 … 2025-12-28**（seen、4.67 年） | 承認済みの route（`patsd_stage0.data.load_pair`）の M15 bid / ask、20 pair。同じ期間の公開の macro・金利などの情報 |
| **独立な推定（E）** | **2010-01-01T00:00Z … 2016-05-31T21:00Z**（約 6.4 年、intraday は未読） | OANDA の historical の read-only の取得（`scripts/research/fxid_cycle1/acquisition_guard.py` の境界の規則で、上限は request の段階で除外） |
| 予備（使わない） | 2006-01-01 … 2009-12-31 | — |
| **使わない** | fresh `2016-06-02 … 2021-04-25`、OOS `2025-12-29 … 2026-02-28`、dead `2026-03-01 … 2026-04-24`、forward `≥ 2026-04-25` | — |

- E の期間に、pair と解像度の取得できる被覆が 3 年未満しか無い family は、E の段で STOP する。
- S と E の順序は、後で入れ替えない。

## 3. 重複の分類（指示 §15）

| 分類 | 実証に進めるか |
| --- | --- |
| `NEW_MECHANISM` | 進める |
| `NEW_INFORMATION_FOR_EXISTING_MECHANISM` | **事前に観測できる、本当に新しい情報源を持つ場合だけ**進める |
| `DUPLICATE` | 進めない |
| `PREVIOUSLY_REJECTED` | 進めない |
| `EXECUTION_VARIANT` | 進めない |
| `HORIZON_VARIANT` | 進めない |

比較の対象: F1〜F15、C03 / C04 / C05、H-002、Round 1 / A / B′、#471〜#497、#503、#505、#506、#507（その 31 の mechanism を含む）。

## 4. data を見る前の ranking（指示 §13）

12 の基準を 0 / 1 / 2 で採点し、重み 12, 11, …, 1 で加重和を取る。同点は基準 1 から順に比べる。

| # | 基準 | 2 点 | 1 点 | 0 点 |
| --- | --- | --- | --- | --- |
| 1 | 経済的な必然性 | 取引しなければ制度上・会計上の損失がある | 強い動機がある | 任意 |
| 2 | 予想される flow の大きさ | 日次の取引量の 1% 以上の推定 | 0.1〜1% | それ未満か不明 |
| 3 | timing の精度 | 分の単位で制度が決める | 時間の単位 | 日の単位以上 |
| 4 | 方向の明確さ | 事前に符号が一意 | 条件付きで一意 | 曖昧 |
| 5 | 公開の観測可能性 | 公開・無料・当時に入手可 | 公開だが取得が要る | 非公開・有料 |
| 6 | 予想される turnover | 1 日 1 回以下 | 1 日 2〜5 回 | それ以上 |
| 7 | 執行の cost | Track B の frontier の低い pair・時刻で執行できる | 中程度 | 高い（rollover・event の瞬間など） |
| 8 | 機会の頻度 | 毎日かほぼ毎日 | 週に 1〜数回 | 月 1 回以下 |
| 9 | F1 からの独立性 | 時刻も機構も別 | 一方が重なる | 両方が重なる |
| 10 | data の入手可能性 | S と E の両方で、取得済みか無料 | 一方は取得が要る | 入手できない |
| 11 | 検証の実現性 | power-first の gate（§5）を余裕で通る | 境界 | 通らない |
| 12 | portfolio の分散の可能性 | 通貨・時刻・macro が既存と別 | 一部が重なる | 大きく重なる |

## 5. power-first の gate（指示 §18。data を読む前に適用する）

各 family の **Base の予測の retail の net Sharpe** を s_B とする。年率で、Role H が mechanism・制度・外部の prior から、data を見ずに導き、根拠とともに事前登録に記録する。retail の cost は Track B の frontier の、該当する pair と時刻の値を使う。直接の実証の証拠が無い効果には、50% の haircut を掛ける。

**最低限の経済的に有用な効果**: m = 1 / √3 ≈ 0.58。最大 3 family が独立で、等しい大きさの場合に、system の Sharpe 1.0 に届く大きさ。

**gate**（全て満たす family だけ、data を取得・読む）:

| # | 条件 |
| --- | --- |
| PF1 | s_B ≥ m（経済的に有用） |
| PF2 | 選択の block S（T_S = 4.67 年）で、事前登録の検定の検出力が 0.5 以上: s_B · √T_S ≥ z_{1 − 0.10 / V}。V は登録した variant の総数（≤ 6）。V = 6 なら s_B ≥ 1.11、V = 3 なら s_B ≥ 0.98 |
| PF3 | 独立な推定の block E（T_E = 取得できる年数）で、片側 5% の検出力が 0.5 以上: s_B · √T_E ≥ 1.645 |
| PF4 | 機会が年 12 回以下の family は、効果が非常に大きいか、独立な横断の breadth が本当にある場合だけ（指示 §19） |

参考として、m での検出力も記録する（判定には使わない）。

## 6. component の gate（指示 §30。S の 1 回の検定で判定）

| # | 条件 |
| --- | --- |
| C1 | gross の期待値 > 0 |
| C2 | retail の net の期待値 > 0。**多重性の調整後**に有意: V の variant にわたる family-wise 10%（Bonferroni か max-T。事前登録で指定） |
| C3 | 経済的に意味のある大きさ: S での net Sharpe の点推定 ≥ 0.3 |
| C4 | cost を 1.5 倍にしても、net の点推定 > 0 |
| C5 | 方向が mechanism と一致 |
| C6 | S の前半と後半で、net の符号が同じ |
| C7 | 独立な推定の経路がある（E の被覆が 3 年以上） |
| C8 | F1 と他の component と、別の mechanism |
| C9 | 検出の horizon が現実的（PF2・PF3 を満たした設計のまま） |

primary の仮説で判定する。secondary の variant で primary を救済しない。

## 7. 独立な推定（指示 §31）

- E で、事前登録の同じ規則の net Sharpe を推定する。
- **通過の条件**: 片側 t > 1.28（p < 0.10）で、符号が S と同じ。
- 効果は、懐疑的な prior N(0, 0.4²) で縮小する（Architecture H の入力）。

## 8. Track B の仕様（指示 §20〜§24）

| 項目 | 仕様 |
| --- | --- |
| data | S の期間の M15 bid / ask の終値の spread（承認済みの route、20 pair）。spread だけで、target の return を使わない |
| 時間帯 | NY 現地時刻で、Tokyo（19:00〜02:00 ET）・London の開場（03:00〜04:00）・London の朝（04:00〜08:00）・NY 08 時台・NY 09 時台・NY 10 時台・London fix（11:00 前後）・NY の午後（12:00〜16:00）・rollover の前（16:00〜17:00）・rollover の後（17:00〜19:00） |
| 統計 | pair × 時間帯ごとの spread の中央値・p25・p75・p90。event の時刻（08:30・10:00 ET の bar）と他。曜日。夏時間と冬時間 |
| all-in の往復 | entry と exit の spread の半分ずつ + slippage 0.5 bp（**推定**。実約定の data は無い） |
| 1.0 bp の区別 | all-in ≤ 1.0 bp（spread ≤ 0.5 bp）の bar の割合で、「一瞬だけ」（< 5%）・「一部の pair だけ」・「特定の時間帯だけ」・「継続的」（その pair と時間帯の bar の 50% 以上）を区別する |
| 評価 | 1.0 bp を絶対の条件にしない。component の評価は「gross − 現実の all-in の cost」で行う |

## 9. 記録（provenance、指示 §50）

全ての decision-bearing な実行で、次を保存する。data を読んだ後に事前登録を変えた場合、その実行は decision-bearing として無効。

- 事前登録の SHA
- code の SHA
- 入力・dataset の hash
- command
- 時刻
- dirty の状態
- 出力の hash
- seed
- 環境
