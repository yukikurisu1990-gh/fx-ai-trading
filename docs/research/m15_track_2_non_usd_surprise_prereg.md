# Track 2 — Non-USD Macro Surprise → Currency-Level Relative Response: 事前登録

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Status at freeze: **`TRACK_2_PREREGISTERED_NOT_YET_EXECUTED`**

本文書は **Track 2 の signal / return を一切見る前**に凍結する。コミット順序が
凍結の証拠。Feasibility Gate v2 は `d2d35db1d851e230155f0975e01427db6a0a1d48`
で先に凍結済みで、本 Track はその **最初の prospective 適用対象**である。

Human + ChatGPT の裁定（#475 merge 後：Gate v2 → Track 2 の順、Track 1 は凍結）
に従う。

---

## 0. 事前に開示する「見たもの」

凍結の意味を正確にするため、本文書を書く時点で見たものを列挙する。**いずれも
signal でも return でもない。**

* 無料アーカイブの**スキーマ**（列名、通貨コード、行数 83,427、SHA256 先頭
  `f4e92bca4168cfe6`）と、パネル期間内の通貨別行数。
* アーカイブの**タイムスタンプ欠陥の性質**。同一通貨・同一系列の中に
  `12:15 UTC` 台と `19:30 / 20:30 UTC` 台が混在しており、後者は既知の
  「16〜17 時間早い」欠陥に一致する（`2021-05-06 19:30 UTC` + 17h =
  `2021-05-07 12:30 UTC` = 米雇用統計の正しい時刻）。前者はその補正を当てると
  逆にずれる。**したがって欠陥は一定オフセットではない可能性が高い。**

この 2 点は Stage 0 が何を測るべきかを決めるための scoping であって、Stage 0 の
合否そのものではない。合否規則は下の §3 で凍結する。

## 1. 何を新規性として認められたか

Human + ChatGPT は本 Track の新規性を承認済み。過去の USD pooled absolute 1h
family とは **population（非 USD）/ target（通貨レベルの相対応答）/ horizon
（1 日）/ portfolio construction（通貨バスケット中立）** が異なる。

## 2. データ来源

| 役割 | 来源 | 鍵 | 課金 |
| --- | --- | --- | --- |
| actual / forecast / previous / event 名 / 通貨 | HuggingFace `Ehsanrs2/Forex_Factory_Calendar` の `forex_factory_cache.csv` | 不要 | 無料 |
| **公式の発表日**（ground truth） | ECB / BoJ / RBA の公式サイトの機械可読識別子（`scripts/research/exogenous/calendars.py`、master 済み） | 不要 | 無料 |
| FX バー | 既読の 2 決定パネル（`round_a.panels`） | — | — |

有料データは取得しない（CME / Databento を含む）。broker 認証・demo・paper・live
執行は行わない。読むのは seen data のみ。

## 3. Stage 0 — Data Integrity（**先に実行し、落ちたら Stage 1 を実行しない**）

signal 性能を一切見ずに、非 USD の actual / forecast / event-date の整合性を監査する。

### 3.1 検査項目

| id | 検査 | 方法 |
| --- | --- | --- |
| **P1** | provenance | ダウンロードした bytes の SHA256 と行数を記録。既知値と一致するか |
| **P2** | currency mapping | 全行の通貨コードが既知集合に入るか。G10 8 通貨の行数を報告 |
| **P3** | **date fidelity** | ECB / BoJ / RBA の政策決定行を**公式発表日**と突き合わせる。一致率と `archive_date − official_date` の分布を報告 |
| **P4** | offset の一貫性 | P3 のズレが**単一の定数**で説明できるか。説明できない＝補正不能 |
| **P5** | forecast の事前性（反証のみ） | (a) `Forecast == Actual` の完全一致率、(b) `Forecast` が naive benchmark（`Previous`）より actual に近いか |
| **P6** | revision backfill | 非 USD に vintage は無いので**限界として記録**。アーカイブ内部の整合（当該系列の `Previous` が直前行の `Actual` と一致するか）だけ測る |

### 3.2 合否（結果を見る前に凍結）

**Stage 0 は次をすべて満たすときのみ合格**:

1. **P3 の日付一致率 ≥ 95%**（ECB / BoJ / RBA の照合可能行の合計に対して）。
2. **P2 の通貨コード既知率 = 100%**。
3. **P5 が反証しない**: 完全一致率が 25% 未満、かつ `Forecast` の平均絶対誤差が
   `Previous` の平均絶対誤差より小さい。

### 3.3 補正の扱い

日付補正は **1 つだけ**、事前に宣言する: アーカイブのタイムスタンプに単一の定数
`ARCHIVE_OFFSET_HOURS` を加える。その値は **USD 行から**（ALFRED vintage の
ground truth で）推定し、**非 USD 行では検証にのみ使う**。訓練と検証を分ける。

補正後も §3.2 の 1 を満たさない場合、**手修正・補完・per-currency の個別補正で
救済しない**。verdict は `NON_USD_SURPRISE_DATA_NOT_DECISION_GRADE_SKIP`。

### 3.4 timestamp と date の分離

1 日研究に必要なのは **date fidelity** であって timestamp fidelity ではない。
date しか信頼できない source を推定時刻で 1h に昇格させることはしない。Stage 1 は
1d relative response に限る。

## 4. Stage 1 — hypothesis（Stage 0 合格時のみ）

> 非 USD の macro surprise は、event currency の他通貨バスケットに対する
> **forward relative return** を持つか？

**forward** が要点。date しか信頼できないので、entry は **発表日の翌 UTC 日の
最初の M15 バーの open**、exit は **その 1 取引日後の close**。発表当日の反応は
測らない。これは仮説を弱くする側の選択であり、intraday leak を構造的に不可能に
する。

## 5. Target — currency level

pair 単位ではない。event currency `c` について

    target = r_c − mean( r_k : k ∈ G10 \ {c} )

`r_k` は `scripts/research/clock_flow/currency.py` が既に持つ 8 通貨 × 20 ペアの
構成をそのまま使う（1 つの構成、既にテスト済み）。USD はバスケットに**含める**
ので、共通 USD ファクターが結果を作ることはない。ポジションは中立化された
±1 で、gross exposure は 2 単位に正規化される。

## 6. Signal

    surprise = first-release actual − pre-release consensus
    z = surprise / rolling_sd(surprise, expanding, min 12, strictly backward)

`rolling_sd` は同一 event 系列内で、当該行より**前**の surprise のみから計算する。

### 符号（economic mechanism から事前固定、結果後に反転しない）

| family | 符号 | 機構 |
| --- | --- | --- |
| inflation | **+1** | 高いインフレはタカ派 → 当該通貨高 |
| employment | **+1**（失業率と claims は **−1**） | 強い雇用はタカ派 → 当該通貨高 |
| policy_rate | **+1** | 予想より高い政策金利はタカ派 → 当該通貨高 |

測定された効果が逆向きなら family を**落とす**。反転はしない。

## 7. Cells — small family

**primary は 3 つだけ**: `inflation` / `employment` / `policy_rate`。
event zoo を作らない。diagnostic cell（通貨別、high-impact 部分集合など）は
primary と明確に分離し、family-wise の判定には使わない。

## 8. Horizon

primary は **1 day**。追加 horizon の sweep は行わない。

## 9. Cost

**realistic market-order execution** を baseline にする（Track 3 が passive を
weak と判定したので、楽観的な passive コストで成立させない）。通貨ポジションを
20 ペアで実装する際の gross exposure 倍率を掛け、stress として ×2 も併記する。

## 10. Feasibility Gate v2 の適用

Gate v2（`d2d35db`）を **prospective に**適用する。

* **Statistical**: MDE ≤ minimum relevant effect（両決定パネル）
* **Economic**: MRE − cost ≥ margin（base と ×2）、implied gross annual IR ≤ 1.5
* **Robustness**: 各決定パネルで `n_events ≥ 60`、パネル 2 枚

## 11. 報告する量

`N` / `effective N` / `gross` / `realistic cost` / `net` / `expectancy per event` /
`MDE` / `minimum relevant effect` / statistical gate / economic gate /
confidence interval / family-max p / currency breadth / panel consistency /
tail dependence / top-event concentration。

## 12. Two-panel 原則

power 不足を理由に結果後に決定パネルを pool して success を主張しない。
pooling は diagnostic のみ。primary success には panel consistency を要求する。

## 13. Success / Kill（凍結）

**Success（A）** — 次をすべて満たす:
Gate v2 の statistical・economic・robustness を通過、**両決定パネルで符号が一致**、
currency breadth ≥ 4 通貨が同符号、family-wise evidence（family-max p < 0.05）、
tail 依存が過度でない（上位 10 事象が net の 50% 未満）。
→ `NON_USD_SURPRISE_RELATIVE_EDGE_SUPPORTED_EXPLORATORY`、Human + ChatGPT へ返す。
**fresh replication には進まない。**

**Kill（B）** — decision-grade に検定できて null。
→ `NON_USD_SURPRISE_RELATIVE_CLOSED`。以後 basket 変更・horizon 変更・符号反転・
ML 救済・regime 救済はしない。

**Skip（C）** — data integrity か power が足りず未検定。
→ `NON_USD_SURPRISE_DATA_NOT_DECISION_GRADE_SKIP`。

## 14. 進まないもの

G6 / intraday 昇格は Stage 1 で base edge が成立した場合のみ検討。ML は base 成立
まで未使用。regime / HTF は Stage 1 では使わない。Track 1 は凍結のまま。
