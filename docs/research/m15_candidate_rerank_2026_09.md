# 候補 inventory 全面 rerank と signal-blind feasibility（2026-09-19）

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Human + ChatGPT 裁定（2026-09-19）§10–§18 による。#484 の 28 候補 / 21 distinct directions を、
T-R・T-R2・T-V の実行結果と family closure を織り込んで全面的に評価し直す。
古い ranking はそのまま使わない。

---

## 0a. この文書の authority と、その限界（レビュー時に最初に読むこと）

**裁定そのものは repo に入っていない。** 本文書・本 PR の code は「2026-09-19 の
Human + ChatGPT 裁定 §2–§46」を約 40 箇所で引用し、それを根拠に `WORKFLOW_STATUS` を
書き換え、ledger の status を確定させ、test の guard 1 本を削除している。しかし
`grep -rl "2026-09-19"` が返すのは**本 PR が触れたファイルだけ**であり、裁定の本文も
節番号の一覧も committed record として存在しない。

本 repo の先例（supplemental read の authorisation を結果 doc の §0 に記録した例）に従うなら、
**裁定本文は独立した record として commit されるべき**である。本セッションは裁定本文を
保持していないため、これを捏造せずに**未解決として明示**する。

→ **Human への依頼**: 裁定本文を record として本 PR に添付するか、引用が正確であることを
確認してほしい。それが済むまで、本文書の「§N による」という記述は
**検証不能な引用**であり、`WORKFLOW_STATUS` の書き換えと guard 削除はその上に乗っている。

## 0b. 本 round の結論で最も重要なこと

**span を伸ばしても、探している効果は決められない。** §1 で詳述するが、
22.5 年でも真の Sharpe 0.3 に対する検出力は **0.30** であり、
両側 80% 検出力で 0.3 を検出するには **87.2 年**（片側なら 68.7 年、`capacity.sample_years_needed`）を要する。
初稿は S05・S02 に `DECISION_CAPABLE` を付けていたが、
**それは本文書自身の判定基準（「検出可能 Sharpe が現実的な 0.2–0.5 を上回る span は決められない」）に反する**。
現在の verdict は `BEST_AVAILABLE_SPAN_STILL_UNDERPOWERED_FOR_A_REALISTIC_EDGE` であり、
**これは pass ではない**。

---

## 0c. 確定した status（§2–§8）

| track | 正式 status |
| --- | --- |
| T-R fast | `MARKET_YIELD_REPRICING_FAST_5D_MEASURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` |
| T-R2 slow | `MARKET_YIELD_SLOW_REPRICING_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` |
| family | `MARKET_YIELD_REPRICING_SIMPLE_DIRECTIONAL_FAMILY_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`（scope 限定 CLOSED） |
| T-V | `REAL_EXCHANGE_RATE_VALUATION_NOT_SUPPORTED_IN_DEVELOPMENT` |

closure が**閉じる**のは public daily sovereign-yield data / simple fast directional repricing /
simple slow directional repricing / subsequent G10 FX directional return の 4 点。
**閉じない**のは OIS・market-implied policy path・rate futures・intraday rate repricing・curve shape・
term-premium information・rates options・distributional policy-path information の 8 つ（いずれも未観測）。

## 1. rerank を支配したのは mechanism ではなく **span** である — ただし span でも足りない

今回いちばん重要な発見は、どの候補についてでもない。**検出力**についてである。
両側 5%・検出力 80% で分離できる年率 Sharpe は概ね `2.80 / √年数`。
この定数は本 repo の committed gate が既に `power_multiplier = 2.8016` として持っている
（`scripts/research/feasibility/inventory.py`）。新発見ではない。

年数は**すべて committed な decision-day 数 ÷ 252** から出す。初稿は長 span に
calendar 年、近 span に 252 日年を使い、さらに近 span を 1,182 日としていたが、
`market_yields/prereg.py` の `DECISION_DAYS` は **1,213** である。

| span | decision days | 年数 | 分離できる net Sharpe | 真 Sharpe 0.3 での検出力 |
| --- | --- | --- | --- | --- |
| seen M15 corpus `2021-04-27 … 2025-12-26` | 1,213 | 4.81 | **1.28** | 0.10 |
| ECB 日次 FX `1999-01-04 … 2016-06-01` | 4,458 | 17.69 | 0.67 | 0.24 |
| **上記 2 つ（保護 pool を挟んで disjoint）** | **5,671** | **22.50** | **0.59** | **0.30** |

現実的な単一 source の edge は net Sharpe 0.2〜0.5。
**4.8 年の seen corpus では、その帯域のどこも 0 と区別できない。**
T-R も T-R2 も正の gross を出しながら何も決められなかったのは、これが理由である。

### ただし、長い span はこれを解決しない

初稿はここで止まり、S05・S02 に `DECISION_CAPABLE` を付けた。**それは同じ基準に照らして誤りである。**
0.59 は依然として現実的な 0.2–0.5 の上端に食い込むだけで、帯域を分離しない。直接計算すると
pooled 22.5 年の両側検出力は真 Sharpe **0.2 で 0.16、0.3 で 0.30、0.5 で 0.66**。
両側 80% で 0.3 を検出するには **87.2 年**必要である。

**検定の側数は 1 つに統一した。** 本文書は一貫して**両側 5%**である（方向こそが問われているため）。
既存の record はそうではない: `capacity.sample_years_needed` は docstring のとおり**片側**で、
committed な T-R record は同じ 1213 日 span に **1.13** を与える（本文書は 1.28）。
どちらも誤りではないが、**混ぜて引用すると必ず引用した側に有利になる**。
片側 68.7 年 / 両側 87.2 年 — どちらにせよ到達可能などの span の 3〜4 倍である。

**本 programme が合法的に到達できるどの span も、探している効果に対して検出力不足である。**
長い span に価値があるのは、真 0.3 での検出力を 0.10 から 0.30 に動かすからであり、
また **disjoint な 2 span で符号一致を要求できる**からであって、決定的な検定が手に入るからではない。

符号一致も過大評価しない: 事前に方向を指定した場合、**帰無仮説の下で 2 span 一致する確率は 0.25**。
真 Sharpe 0.2–0.5 でも一致確率は 0.53–0.85 にすぎない。これは period robustness の screen であって
検定ではなく、pooled 有意性と符号一致の**両方を事後に引用できるようにすると、通る経路が増えるだけ**である。
→ **pre-registration では primary statistic を 1 本に決めること。**

したがって候補の価値は「prior の強さ」より **「情報源に長い無料履歴があり、読んでよい FX 履歴と突き合わせられるか」**
で決まる。ただしその順位付けは **「最も検出力不足でなく、closed family の外にある」** という意味であって、
**「この候補は決められる」ではない。**

### committed gate との未解決の緊張（§1a）

本 repo には既に signal-blind の feasibility gate がある
（`scripts/research/feasibility/inventory.py`）。初稿はこれを引用も再実行もしていなかった。
再実行した結果:

| plan | 22.5 年 panel での verdict | binding constraint |
| --- | --- | --- |
| C10 equity risk regime | `NO_DECISION_GRADE_PASS_REGION` | `economic_net_under_stress` |
| C09 yield differential | `NO_DECISION_GRADE_PASS_REGION` | `economic_net_under_stress` |
| C11 commodity link | `NO_DECISION_GRADE_PASS_REGION` | `economic_net_under_stress` |
| C01 中銀決定 response | **`PASS_REGION_EXISTS`** | `economic_net_under_stress` |
| C05 月末 rebalance flow | **`PASS_REGION_EXISTS`** | `event_floor` |

**binding constraint は span ではなく cost である。**
`PASS_REGION_EXISTS` の 2 行は `years_short: 0.0`（span は足りている）。
残る 3 行も span が律速ではない — C09 0.113 / C10 0.849 / C11 0.113 と、不足は僅少である。
つまり本文書の「span が inventory を並べ替える」という主張は、
committed gate に通すと**選んだ 2 本については span が律速ではなかった**ことになる。

ただし C↔S の対応は 1 対 1 ではない（C10 は conditioning 仮説、S05 は directional source。
C09 は T-R が既に閉じた利回り差の *level*）。
よって**これは verdict ではなく未解決の緊張として記録する**。pre-registration が解くべき論点である。


## 2. reachability は**未解決**である（初稿の最大の誤り）

初稿はここを「仮定せず実測した（重要な副産物）」と書いていた。**実測はしたが、記録していない。**
本 round の観測は in-session の直接 request で行われ、**gated probe route を通っておらず、artefact を残していない。**
そして本 repo には **5 日前の committed probe** がある:
`artifacts/research/edge_sources/public_data_availability.json`（`checked_utc 2026-09-14`、
`scripts/research/public_data_probe/availability_check.py` が出力）。

**両者が正反対なのは 2 host である**（残る 2 host は「片方が言い、片方が言わない」であって矛盾ではない）。

| host | 本 round の報告 | committed probe (2026-09-14) | status |
| --- | --- | --- | --- |
| `fred.stlouisfed.org` | UNREACHABLE（3 回失敗） | **全 17 series が HTTP 200**（`BAMLH0A0HYM2`・`VIXCLS`・`DGS2/DGS10` を含む） | **CONFLICTED** |
| `api.statistiken.bundesbank.de` | REACHABLE（10y 日次 200） | SSL CERTIFICATE_VERIFY_FAILED | **UNVERIFIED** |
| `data.snb.ch` | REACHABLE（curve cube 200） | SSL CERTIFICATE_VERIFY_FAILED | **UNVERIFIED** |
| `home.treasury.gov` | REACHABLE（1995 年まで全年 200） | HTTP 404 | **CONFLICTED**（別 URL の可能性が高いが再現不能） |
| `www.bankofcanada.ca` | REACHABLE（Valet 10y 200） | Valet 2y metadata 200 — **一致** | REACHABLE |
| `cdn.cboe.com` / `www.eia.gov` / `stats.bis.org` | REACHABLE | probe の対象外 | **THIS_ROUND_ONLY** |
| `data-api.ecb.europa.eu` | REACHABLE | 別 host（`data.ecb`）が TLS 失敗。ただし T-V の取得全体を担った実績が強い証拠 | REACHABLE |
| `query1.finance.yahoo.com` | REACHABLE だが不使用 | probe 対象外 | §41 により official を優先 |
| `dataservices.imf.org` | UNREACHABLE（DNS） | probe 対象外 | UNREACHABLE |

**SSL 失敗は「到達不能」ではない。** committed probe 自身の `note` が
「`SSL/403 failures are unverified-from-this-environment, not unavailable`」と明記しており、
これは publisher についての言明ではなく **prober 側の trust store の問題**である。
したがって Bundesbank・SNB は **矛盾ではなく `UNVERIFIED`**（片方が到達可能と言い、片方は何も言わない）。
初稿の修正版はこれを CONFLICTED と誤記していた。**真の矛盾は FRED と Treasury の 2 件だけ**である。

また **probe が対象にしていない 3 host（CBOE・EIA・BIS）は `THIS_ROUND_ONLY`** とする。
**矛盾が無いことは裏づけではない。** 本 round の artefact 無し観測しか根拠が無く、
それは本文書自身が不十分と宣言した証拠階級である。

**再現できない観測 2 つは互いを決着させない。** よって本文書は勝者を選ばず、
`REACHABILITY` に `UNRESOLVED_CONFLICTS_WITH_COMMITTED_PROBE` を記録し、
**reachability を根拠にどの候補も退場させない**。

これが効く箇所は 2 つある。

- **S07 は「data を失った」ではない。** 初稿は FRED 不達を根拠に
  `DATA_UNAVAILABLE_WITH_CURRENT_FREE_SOURCES` として ranking から実質除外していた。
  しかし唯一記録のある測定は、**まさにその series (`BAMLH0A0HYM2`) が 200 を返した**と言っている。
  → `DATA_POSITION_UNRESOLVED_PENDING_AN_APPROVED_PROBE_RE_RUN`。
- **S02 の長辺（10y）は「取得可能」と確立していない。** 4 publisher のうち 3 つが CONFLICTED である。

### なぜ今ここで再測定しないか

`availability_check.py` の docstring は **"Do not re-run without approval"** と明記し、
`EDGE_SOURCES_PROBE_APPROVED=1` の opt-in gate を持つ。
**これは approval を要する act であり、session が自分の判断で解決してよいものではない。**
→ Human の承認の下で probe を再実行し、その artefact を commit するのが唯一の解き方である。

### VIX の本数について

初稿は「VIX 9,276 本・長 span 内 4,381・近 span 内 **1,389**」と記録していた。
**最後の値は算術的に不可能である**: `2021-04-27 … 2025-12-26` の平日は **1,219 日**しかなく、
同じ dict が同 span の decision days を 1,213 と書いている。
1,389 は **上限を適用せず request 当日まで数えた**場合の値と整合する
（= fresh pool・OOS slice・forward epoch の暦をまたぐ）。
**VIX は保護 data ではないので read 境界は侵していない**が、数値は誤りで、
3 つとも artefact から再現できない。→ **3 つとも撤回**した。

**残るのは 1990-01-02 という series 開始日だけ**で、これは committed probe の
FRED `VIXCLS` declared range が独立に裏づけている。


## 3. 新証拠で ranking から外れた候補（§11）

| ID | 旧順位 | 処遇 | 理由 |
| --- | --- | --- | --- |
| **S01** front-end 金利 repricing | **1** | 実行済み CLOSED | T-R / T-R2 として実行、両方 NOT_SUPPORTED、family closure |
| **S13** 実質為替 valuation | **2** | 実行済み CLOSED | T-V として実行。cost ではなく **incremental IC −5.57pp (t −3.34)** |
| **S03** 会合日 repricing（T-E 主） | 4 | **除外** | §4 の詳細は下記 |
| **S04** 指標発表日 repricing（T-E 副） | 6 | **除外** | 同上 + 非 US の無料公式時刻付きカレンダーが存在しない |
| **S16** 金利 × vol 閾値 | 9 | 除外 | S01 の増分。自身の順序規律で「S01 の線形 baseline が正でない限り検定しない」。baseline は 2 回とも正にならず family は closed |
| **S08** 金利 vol 状態 | 18 | 除外 | 同上 |
| **S17** event 日 cross-asset | 15 | 除外 | S03・S04 の増分で、両方除外 |
| **S28** breakeven repricing | 12 | **closure 内** | breakeven は public sovereign yield 2 本の差であり、rule は simple directional repricing。data も rule も closure が覆う。加えて breadth 1〜2 |
| S14 / S15 / S10 / S12 | 11/17/16/19 | 大幅 penalty | price-only または conditioning のみ。H-023・H-024・H-003・H-017 と重複 |

既存の除外（S11・S19・S23・S24 = 改名/救済、S09 = 構造的不成立、S21 = 停止中 family、
S18/S20/S22 = データ不可）は**そのまま維持**する。

### S03 / T-E の再評価 — §15 が求めた検査に通らない

§15 は「T-R の failed signal に event filter を掛けただけではないか」を確認せよと指示している。**そのとおりだった。**

- S03 の方向情報は **2 年金利の当日変化** — closure が覆う *public daily sovereign-yield の simple directional repricing* そのものである。
  無料データで得られる会合日の測度は日次変化なので、event で条件付けることは
  **同じ closed な量のきれいな部分集合を選ぶ**ことであって、別の情報を供給することではない。
- closure は **intraday rate repricing を閉じていない**。しかし intraday 金利は無料では取得できない。
  **本当に新しくなる版は、作れない版である。**
- opportunity 層は既に測定済みで、**cost advantage は無いと分かっている**:
  H-018/H-019 は event 日の絶対変動が 1.13〜1.63 倍（H-018 が 1.33 と 1.13、H-019 が 1.58 と 1.63）である一方、**spread は 1.01〜1.05 倍広く**、
  round trip を超える日の **event/非 event 比**は **1.00**（1.0042 と 0.9958 = unity）と記録している。
  これは「全日が cost を超える」という意味ではなく、**「cost 超過率が event 日で動かない（通常日が既に超えている）」**である。H-019 自身の status は
  「a forward-known opportunity anchor with **nothing to point it at**」。
  そこに closed な金利 signal を向けても、この事実は変わらない。
- 検出力: 無料で取得できる中銀は 4 行のみ（Fed・ECB・BoJ・RBA）。
  **GBP・CAD・NZD・CHF には anchor が無い。** 年 34.4 事象、seen corpus で約 160 事象、
  net 0.5 に事象あたり約 12 bp が必要。

→ **T-E は選択しない。** §28 に従い `EVENT_REPRICING_DATA_NOT_DECISION_GRADE` として記録し、backtest しない。
これは「event 情報に価値が無い」ではない（§12）。**方向 source が closed でないものに替わるまで保留**である。


#### この除外が乗っているのは closure ではなく **判断**である

レビューで指摘された整合性の問題: closure の `FORBIDS` が名指しするのは
lookback sweep・EWMA half-life sweep・threshold tuning であって、**event conditioning は入っていない**。
本文書自身が「closure を言い換えで広げてはならない」と書いている以上、
**S03 の除外を「closure の内側だから」と言うことはできない**。

正確な基礎は次の 3 点である。

1. 方向 source が closed な量である（= 新しい情報ではない）。
2. event 母集団を使う価値を作るはずの **cost advantage は測定済みで、存在しない**（H-018/H-019）。
3. 検出力の天井が年 34.4 事象・8 通貨中 4 通貨分しかない。

→ これは **「乏しい検定枠を割かない」という判断**であって、closure の適用ではない。
**新しい証拠が出れば、closure を覆さなくても後のセッションが再開してよい。**
`rerank.EXCLUSION_BASIS` に、どの除外が closure 由来でどれが判断由来かを明示した。

同じ理由で **S28 と S02 の非対称は明示した**。両方とも「sovereign yield の差」であるため、
区別を暗黙にしてはならない。裁定は **curve shape を「closure が届かない情報集合」として列挙し、
breakeven は列挙していない**。この区別が薄すぎるとレビュアーが判断する場合、
整合的な解決は **S28 を取り上げ直すこと**であって、**S02 を言い換えで閉じることではない**。
### S02 の再評価（§16 が求めた明示的再評価）

#484 で T-E と競っていた S02 は、**§4 の closure が curve shape を明示的に閉じていない**ので生き残る。
言い換えによる除外はできない。ただし prior は下がる:

- 同じ情報源（sovereign yield）の *level* が 2 回失敗した直後の、**同じ data に対する第 2 仮説**である。
- T-R / T-R2 の rate book の実測 IC は測定したどの horizon でも負だった。
- 必要な非 US 日次 10 年系列の**取得可能性は未解決**である。#484 時点で probe されておらず、
  本 round の in-session 観測（到達可能）と committed probe（Bundesbank・SNB は TLS 失敗、Treasury は 404）が**食い違っている**（§2）。

→ **順位 4 で残す**（旧 3 位）。後述のとおり SECOND として選ぶが、それは prior の強さによるのでも
data の質によるのでもなく、**closed family の外にあり、到達しうる最長 span に届く**からである。

## 4. 新しい ranking（§13・§14）

比較原則: `P(real edge) × 経済的規模 × persistence × breadth × 資本利用 × 情報利得`
÷ `cost × complexity × overfit risk × data burden × engineering burden`。厳密な score ではなく理由を明示する。

| 新順位 | ID | 方向 | なぜこの位置か |
| --- | --- | --- | --- |
| **1** | **S05** cross-asset risk repricing | B | **情報集合が本 programme で未検定**（H-002 は price-only の session/ATR 条件付け）。VIX は 1990-01-02 から無料日次（開始日は committed probe が裏づけ）→ 長 span の FX と揃い、**22.5 年 / 検出可能 0.59**。disjoint 2 span で符号一致を要求できる。**ただし真 0.3 での検出力は 0.30 にすぎない**。弱点は breadth（risk 軸 1 本 ≒ 実効 2〜3） |
| **2** | **S06** commodity terms of trade | B | 未検定（C11 未実行）、EIA が公式に日次配信（**開始年は本 repo の記録では裏づけられない** — 唯一裏づけのある原油系列は FRED の Brent 1987-05-20 開始）、mechanism が**通貨固有の実質所得**で S05 の単一 risk 軸とは別の経済主張。弱点は実効 breadth 1〜1.5 |
| **3** | **S07** credit spread / funding stress | B | 未検定・長 span。ICE 指数に無料の一次公表者は無いが、**data position は UNRESOLVED であって「失われた」ではない**（committed probe は当該 series が 200 と記録、§2）。S05 と同じ risk 軸でもある → S05 の robustness check が適所 |
| **4** | **S02** curve slope / curvature | A | closure が明示的に閉じていない。data は tier-1 公式で 1999 年より前まで届く。turnover 8〜18 は全候補中最小。**弱いのは prior であって feasibility ではない** |
| 5 | S25 中銀 balance sheet | A | 未検定・無料だが月次。長 span なら約 209 観測、seen corpus だけなら 56 で negative を閉じられない |
| 6 | S10 通貨 network 伝播 | C | §31 の重複監査が要る（H-003 / Track 1）。intraday 版は turnover 100 超、data は 4.7 年の seen corpus のみ |
| 7 | S14 multi-horizon price state | E | price-only。Track 1 の 5/20/60 線形結合が gross 負（H-023）、H-024 が復活を禁止 |
| 8 | S15 latent regime | E | return source ではなく conditioning。正の base が存在しない。H-017 が先例（vol filter が carry を 15/15 で悪化させた） |
| 9 | S12 相関 breakdown | D | H-003・H-024 と重複、自身の capacity 注記で年 2% 未満 |
| 10 | S26 国際資本 flow (TIC) | H | H-021 とは別物（現物 flow ≠ 先物投機）だが月次・6 週 lag・US 中心・availability 未 probe |
| 11 | S27 中銀 communication tone | A | 事象数は S03 と同じ天井。時刻付き過去テキストの機械取得は未検証、scoring に NLP（§33 で Human 判断） |

## 5. 誤った一般化はしない（§12）

以下は**この結果から導けない**:

- 「rates 全部が無理」— closed なのは simple public daily sovereign-yield directional family のみ。
  OIS・market-implied policy path・rate futures・intraday rate repricing・curve shape・term premium・
  rates options・distributional policy-path information は**いずれも無傷**。
- 「valuation 全部が無理」— 1 span 上の spot-only formulation 1 本が失敗しただけ。
- 「non-price 全部が無理」— その大半はまだ取得すらしていない。
- 「ML 全部が無理」— 積み上げる base となる stage 1 がまだ出ていないだけ。
- 「event 全部が無理」— opportunity 構造は実在が確立している。欠けているのは **closed でない方向 source**。
- 「cross-asset 全部が無理」— **方向 source として一度も検定していない**。
- 「cross-sectional 全部が無理」— H-023 は線形 architecture 1 本を否定しただけで、明示的に `FX_HAS_NO_EDGE` ではない。

## 6. signal-blind feasibility（§19–§22）

alpha を見る前に算定した。**初稿の数値は 2 箇所で誤っており、どちらも有利な方向に外れていた。**

- `vol/単位 gross = 0.030` を「3 つの異なる signal の book で共通して観測された値」としていたが、
  実測は **0.023288**(Track 1)・**0.026103**(T-R2)・**0.032375**(T-V) で、0.030 は**範囲の上端**である。
  `drag = cost / vol` なので、これは cost drag を約 **29% 過小評価**していた。
  → `capacity.VOL_PER_UNIT_GROSS`（committed record から導出され、test で再導出される **0.023288**）を使う。
- `half_life = 252/turnover/2` という逆算は band law と矛盾していた
  （turnover 8 を 15.8 日と呼ぶが、`band_law(16)` 自身は 16 日 book の turnover を 21.1 と言う）。
  → **half-life で parameterise し、`capacity.required_daily_ic` に委譲**した。package 内の band law と cost 規約は 1 つになる。

修正後（`ONE_WAY_BP` も literal をやめ `continuous_portfolio.CHARGED_ONE_WAY_BP` に束縛）:

| half-life | turnover (RT/年) | cost drag (IR) | net 0.3 に必要な日次 IC（breadth 2.5） |
| --- | --- | --- | --- |
| 60 日 | 8.39 | 0.123 | 1.99% |
| 20 日 | 18.28 | 0.267 | **2.71%** |
| 16 日 | 21.06 | 0.308 | 2.87% |
| 5 日 | 43.36 | 0.634 | **4.44%** |

これは committed な `market_yields.prereg.feasibility()` が同一構成で出す値と**一致する**
（20 日: drag 0.267 / IC 2.71%、5 日: 0.634 / 4.44%）。初稿の表（0.204 / 2.37%、0.511 / 3.84%）は一致していなかった。

### decision capability

| ID | verdict | 根拠 |
| --- | --- | --- |
| **S05** | `BEST_AVAILABLE_SPAN_STILL_UNDERPOWERED_FOR_A_REALISTIC_EDGE` | 22.5 年で検出可能 0.59、真 0.3 で検出力 0.30。到達できる中で最良だが**決められない** |
| **S02** | `BEST_AVAILABLE_SPAN_STILL_UNDERPOWERED_FOR_A_REALISTIC_EDGE` | S05 と同じ span。加えて**長辺 data が取得可能と確立していない**（§2） |
| S06 | `AS_ABOVE_AND_BREADTH_LIMITED` | span は同じ、実効 breadth 1.5 → 必要 IC が S05 比で約 29% 増 |
| S07 | `DATA_POSITION_UNRESOLVED_PENDING_AN_APPROVED_PROBE_RE_RUN` | §2 の conflict。**「失われた」ではない** |
| S25 / S26 | `MARGINAL_MONTHLY_SAMPLING_CANNOT_CLOSE_A_NEGATIVE` | 月次。近 span だけでは 56 観測 |
| **S03/S04 (T-E)** | `EVENT_REPRICING_DATA_NOT_DECISION_GRADE` | §3 のとおり。backtest しない |

**`DECISION_CAPABLE` はどの候補にも付かない。** 初稿は S05・S02 に付けていたが、
本文書自身の判定基準に反する（§0b・§1）。


### cost 規約は片方の span でしか測っていない

`1.703 bp` は Track 3 が **2021–2025 の OANDA** で実測した往復コストである。
長 span は **ECB の日次 reference rate** — bid/ask を持たない単一の fix であり、
G10 cross は EUR fix 2 本から三角計算される。
**1999–2016 に G10 spot を売買する実コストがいくらであったにせよ、それはこの数字ではない。**

したがって「22.5 年の net Sharpe」を pooled で語ることは、
**実測した cost regime と仮定した cost regime を混ぜる**ことになる。
しかも混ぜる先は、本 programme のすべての verdict を決めてきた軸である。

→ pre-registration は、**長 span の cost 仮定を明示して stress する**か、
**2 span の net を分けて報告する**かのいずれかを選ばねばならない。黙って pooled にしてはならない。
（`feasibility_2026_09.COST_CONVENTION_IS_SPAN_LOCAL`）

## 7. 有料データの評価（§18、design-only・購入しない）

| ID | 内容 | provider | 概算コスト | 可能になる仮説 | 無料代替が不十分な理由 | 期待情報利得 |
| --- | --- | --- | --- | --- | --- | --- |
| **S20** | G10 FX option の 25-delta risk reversal / IV skew（日次） | Bloomberg / Refinitiv、または CME（自社上場分） | terminal 級で年 USD 20–30k 規模、CME の historical dataset は USD 1–5k 規模。**公開価格表からの桁の目安であり見積ではない。照会していない** | risk reversal は**市場自身が付けた非対称性の価格** — 通貨が下がる保険と上がる保険の価格差。spot から導出できない forward-looking な方向期待で、本 programme が一度も観測していない instrument | FX の optionality を無料で価格付けるものは存在しない。spot からの実現 skew は backward-looking な price 統計で、既に何度も閉じた型 | **高い。** 未取得のうち最強の prior。negative でも「もう 1 本の formulation」ではなく**別の情報集合そのもの**を閉じられる |
| — | G10 の OIS curve / 短期金利先物履歴 | Bloomberg / Refinitiv / 各取引所 | terminal 級または dataset 単位。照会していない | **market-implied policy path** — closure が明示的に開けたまま残したもの。closed family は実現 2 年利回りを使ったが、OIS は期待経路を直接価格付けし term premium と分離する | 無料の代替が 2 年 sovereign yield であり、それがちょうど閉じた。G10 の無料 OIS 履歴は無い | **中程度。** きれいな instrument で金利方向を再開できるが、closed family の失敗は現実的 cost での monetisability であり、OIS がそれを変える保証はない |
| S22 | intraday 株価指数先物 | 各取引所 / vendor | dataset 単位、中程度 | session 間 cross-market 伝達 | price-only 版は C03・H-002 で閉鎖済み | **低い。** intraday horizon は本 programme が繰り返し致命的と測った turnover を伴う |

## 8. 選択した 2 本（§23–§26）

**呼称について。** 初稿はこれを「Track A / Track B」と呼んでいた。**本 repo ではこの 2 語は凍結語彙**であり、
Track A = Exploratory、Track B = Formal Confirmation（凍結した候補 1 本を**未読の forward data** で 1 回だけ走らせる）を指す。
ここで使う 2 span は**どちらも既に seen** であり、**どちらも Formal Confirmation にはなり得ない**。
よって **LEAD / SECOND** と呼ぶ。

| | 呼称 | 候補 | 情報集合 |
| --- | --- | --- | --- |
| **LEAD** | cross-asset risk repricing → G10 FX | **S05** | 外部資産（株式 volatility）の repricing |
| **SECOND** | sovereign curve shape → G10 FX | **S02** | 金利 curve の**形状**（level ではない） |

どちらも `EXPLORATORY_ON_SEEN_DATA_NEITHER_IS_A_FORMAL_CONFIRMATION`。

**2 本にした理由**: §23 は最大 2 本を許すが 2 本を要求しない。S06 は実効 breadth が最も狭い。
S07 は data position が未解決（§2）。証拠が支えるのは 2 本である。

**この 2 本にした理由**: ranked 候補のうち、closed family から最も遠く、到達しうる最長 span に届き、
かつ互いに情報が独立（外部資産の repricing と金利 curve の形状）で、
**一方の結果を使わずにもう一方を freeze できる**（§26）。

### この選択が**主張していないこと**

- **「決められる」とは言っていない。** 2 本とも `BEST_AVAILABLE_SPAN_STILL_UNDERPOWERED_FOR_A_REALISTIC_EDGE`。
- **S02 の長辺 data は取得可能と確立していない**（§2 の 3 publisher が CONFLICTED）。
- **committed gate を同じ panel 長で再実行すると、対応する plan は `NO_DECISION_GRADE_PASS_REGION` のまま**で、
  binding constraint は span ではなく `economic_net_under_stress` である（§1a）。
- したがって**どちらを pre-register しても、`UNRESOLVED` で返る可能性が高い検定を登録することになる**。
  それは Human が承知の上で選ぶべき選択であって、本文書が既成事実にしてよいものではない。


## 9. 進め方

- LEAD を先に実行。**SECOND の signal・horizon・benchmark・threshold・universe は LEAD の結果で変更しない**（§26）。
  両方とも独立に freeze する。
- 各 track は **Stage 1: fixed / unfitted rule のみ**（§32）。Stage 1 で経済的証拠がゼロなら complex ML へ進まない（§33）。
- 許される結論は §46 の A〜E のみ。
- 5% / 10% 年率 net に必要な Sharpe・target vol・risk leverage・portfolio gross・margin 利用率・DD を算定するが、
  **net edge ≤ 0 なら leverage で救わない**（§35）。

### pre-registration の前に片付けるべきこと（本 PR では解けない）

1. **裁定本文の record 化**（§0a）。本文書と code は検証不能な引用の上に乗っている。
2. **`availability_check.py` の承認付き再実行と artefact の commit**（§2）。
   S07 の生死と S02 の長辺の取得可能性はこれでしか決まらない。
3. **committed gate との緊張の解消**（§1a）。span ではなく `economic_net_under_stress` が
   binding であるという読みが正しければ、**次に取り組むべきは候補ではなく cost 構造**である。
4. **primary statistic を 1 本に決める**（§1）。pooled 有意性と符号一致の両方を
   事後に引用できる状態にしない。

**いずれも Human の判断を要する。** 本文書はどれも既成事実にしていない。

### この文書が主張していないことの要約

- `DECISION_CAPABLE` な候補は**存在しない**。
- reachability は**測定済みではない**。
- S07 は**退場していない**。
- LEAD / SECOND は **Formal Confirmation ではなく、なり得ない**。
- **実データの再読取り許可はどこにも発生していない。** 両 span が seen であることは
  「もう一度読んでよい」ことを意味しない。新しい read は operation・span・pairs・timeframe・
  approved head を名指しした explicit な Human + ChatGPT の act を要する。
