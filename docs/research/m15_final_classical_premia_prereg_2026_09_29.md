# FINAL_CLASSICAL_PREMIA_LONG_SPAN_CYCLE — 事前登録（2026-09-29）

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` · `PRODUCTION_READINESS_NOT_CLAIMED`.**

- 裁定: Human + ChatGPT、2026-09-29（#496 MERGE APPROVED と本 cycle の承認）。
- 凍結の実体は `scripts/research/classical_premia/prereg.py`、digest は `driver.FROZEN_DIGEST`。
- この文書は理由を説明するもので、値が食い違ったら code が正である。

**この文書は alpha を 1 つも見ずに書いた。** 実データから計算したのは次の 2 つだけで、どちらも return と signal を突き合わせていない（P&L・IC・Sharpe は計算していない）。

- span の長さ
- 月次 target weight の持続性（`artifacts/research/classical_premia/power.json`）

## 1. なぜこれが seen data での最後の cycle か

programme-level の証拠（#496 の最終報告）は次のとおり。

- null と区別できる経済的な正の証拠は 0 本。
- tier A の TC-net の縮小平均は +0.07。
- Sharpe 0.3 の検出力は、17.7 年で 0.24、fresh の 4.9 年では 0.10。
- 年 5% に要る TC-net Sharpe は 0.50〜0.77。

これを受けて、single-signal の逐次探索は終了した。

未検定で残っていて、事前確率が高いのは次の 2 つである。

- 公開の長 span（1999–2016）での古典的な断面 carry
- 同じ span での中期の通貨 momentum

この 2 つを**最初から 1 つの合成**として事前登録し、1 回だけ測る。

- 意味のある経済的証拠が出なければ、同じ seen data の掘り直しをやめる（`LONG_TERM_HOLD` / `NO_FURTHER_SEEN_DATA_ALPHA_SEARCH`）。
- それは `FX_HAS_NO_EDGE` ではない。

## 2. Primary hypothesis（1 本だけ）

> G10 の既存 8 通貨（AUD CAD CHF EUR GBP JPY NZD USD）で、断面 carry（family A）と 12-1 の断面 momentum（family B）を、事前に固定した等リスク合成として月次で持つ。すると 2000-02 … 2016-06 の seen の長 span で、transaction cost 後（TC-net）と近似 financing 込み（judged net）の両方が正になり、no-information null の上側に来る。

- 検定するのは **composite だけ**。
- carry 単独・momentum 単独は分解の診断で、次 cycle へ昇格させない（§14・§40）。
- best-of-N・horizon の選択・符号反転・結果後の rule 変更は禁止。

## 3. Universe と span

| 項目 | 値 |
| --- | --- |
| 通貨 | 8 通貨（`top_five.UNIVERSE` と同一。test で照合）。追加なし |
| FX | ECB 参照レート 1999-01-04 … 2016-06-01。T-V で取得済みで、既に `EXPLORATORY_SEEN_DEVELOPMENT_DATA` |
| 最初の decision day | 2000-02-01。12-1 の formation と 252 営業日の共分散窓の両方が揃う最初の月初 |
| 最後の P&L 日 | 2016-06-01 |
| decision day の数 | 196 |
| span | 4,178 営業日（16.58 年） |
| 保護 data | fresh pool 2016-06-02 … 2021-04-25・historical OOS・dead window・forward は読まない |

## 4. Data sources と保護 data の遵守

**新しい取得はしない（`NO_NEW_ACQUISITION_REQUIRED`）。** 必要な系列は全て既に取得され、seen 化されている。

| 系列 | 出所 | 取得の bound |
| --- | --- | --- |
| FX | ECB（T-V、#488） | request に `endPeriod=2016-06-01` |
| 政策金利 | BIS SDMX（mechanism redesign、#494） | endPeriod 付き。content hash を `signals._load` が照合し、参照期間が保護暦日に掛かる観測は読まずに止まる |
| 3 か月金利 | OECD（同上） | financing の**感度基準だけ**に使う。signal には使わない |

guard は次の 3 つが重なる。

- `panel.long_span_panel` は seen window の外の行を落とし、`assert_no_protected_day` で最後に確認する。
- `data.build` は、どの行も 2016-06-01 を越えないことを parsed date で確認する。
- 凍結 digest は、入力 parquet 23 本と取得記録 2 本の sha256 を含む。

cache の金利 file には recent span（2021-05 以降）の値も入っている。`_align` は各日にその日以前の値しか使わないので、2016-06-01 までの span には届かない。

## 5. Carry の定義（family A）

- **金利**: BIS 政策金利の月末値。
- **signal の置き方**: 第 m 月の値を、m 月末の**翌暦日**から使う。
  - decision day（月初の営業日）には必ず前月末の値が届く。
  - 月末が週末・休日でも、1 か月古い値にはならない。
  - 当日の値は使わない。
  - 初版は「月末に置いて 1 営業日 lag」だったが、月末が休日の月は 1 か月古い値になっていた（pre-alpha Role 1 N1）。
- **会計の置き方**: m 月末の当日から（#495 の `policy_rates_contemporaneous` と同じ）。
- **score**: s_c = r_c（水準）。USD も順位に入る。高金利を long、低金利を short。
- **JPY の 0% 期間**: BIS に数値が無いゼロ金利・量的緩和の期間だけ、#495 で凍結した 0% を置く（期間は test で #495 と一致を確認）。
- **欠損**: decision day に 1 通貨でも金利が無ければ、fail-closed で止まる。

**なぜ政策金利か**（§8。signal を見ずに 3 条件で決めた）:

1. **timing**: 政策金利は公表時刻が明確で、月末値は月末に確定している。OECD の 3 か月金利は月平均なので、lag を置かないと look-ahead になり、置くと 1 か月古くなる。
2. **availability**: BIS は 8 通貨とも 1999-01 から揃う。OECD の JPY 3 か月金利は 2002-04 まで、CHF は 1999-08 まで無い。
3. **economic closeness**: forward points を決めるのは短期の銀行間金利なので、経済的には 3 か月金利の方が近い。ただし G10 の順位はほぼ一致し、programme の financing 会計（#495）の primary 基準も同じ政策金利である。signal と会計が同じ金利なら、「高金利通貨を持って金利差を受け取る」という carry の定義そのものになる。

政策金利・3 か月金利・その他を alpha で比べることはしない。

**記録しておく近似**（どれも順位への影響は無視できる）:

- `_align` は最後の値を最大 75 日運ぶ。そのため JPY の 0% 期間の始めには、直前の BIS 値がしばらく残る。
- 2016 年の JPY のマイナス金利（−0.1%）は 0% と置かれる。
- 2009–2015 の USD / EUR / JPY / CHF は数 bp しか違わないが、rank weight は満額の差を付ける。AMP の標準的な扱いである。

## 6. Momentum の定義（family B）

- **return**: R_c = 通貨 c の対 USD 日次 log return（spot のみ）。R_USD = 0。
- **formation 12-1**: m_c(t) = Σ R_c over 営業日 [t−251, t−21]。過去 12 か月の return で、直近 21 営業日（約 1 か月）を飛ばす。
- **holding**: 1 か月（重なりの無い月次 rebalance）。
- 過去の勝ち通貨を long、負け通貨を short。1 / 3 / 6 / 9 / 12 か月は走らせない。

**なぜこの rule か**（§9）:

- Asness–Moskowitz–Pedersen (2013) の通貨 momentum は「直近 1 か月を飛ばした過去 12 か月の return、月次 rebalance」である。資産クラス横断の canonical 定義として、formation の窓と保有期間をそこから採った。
- Menkhoff et al. (2012) は formation 1〜12 か月を並べているが、そこから選ぶのは horizon selection になるので採らない。
- 直近 1 か月を飛ばすのは、短期の反転と、programme が既に測った数日の family との重なりを避けるためである。

**文献の定義からの意図的な逸脱（spot で作る）**: AMP (2013) と MSSS (2012) の通貨 momentum は、forward から作る excess return（金利差を含む）で formation を作る。ここでは spot だけを使う。これは alpha を見る前に決めた（pre-alpha Role 1 R1 の指摘で明記した）。

- 金利差込みで作ると、momentum の順位が carry の順位を機械的に含み、「2 つの別の premium を合成する」前提が崩れる。
- carry は family A が持つ。

### 6a. 過去の momentum 研究の監査（§10）: rename ではない

repo の全 momentum / carry の研究を独立の調査役（読み取りだけ）が監査した。

| 過去の項目 | 中身 | 今回との違い |
| --- | --- | --- |
| H-003（Round 1 family G、#464） | 2025 年の M15 bar、20 **pair** の trailing return で順位付けし（主に逆張り）、24 時間〜5 日保有 | pair 単位・日中〜数日・2025 年のみ。今回は通貨単位・12 か月 formation・1999–2016 |
| M15 multi-day family（H-005〜H-007、#465–#467） | M15 timeframe の lb480_h480（約 5 日）の reversal / momentum、pair ごとの time series | 数日・pair の time series。mechanism の「M15」（dollar carry）とは別物 |
| H-012 B′-4 monthly TSMOM（#469） | pair ごとの 1〜3 か月の符号、skip なし、2 年 panel | time series・pair 単位・skip なし・長 span ではない |
| Track 1（H-023、#481/#482） | 8 通貨の ridge。5 / 20 / 60 日の excess return z-score、5 日 target、第 1 主成分を除去 | 最長 60 日・学習した重み・2023–25 の out-of-fold |
| cross-pair relative strength（family G = H-003、pre-R1 の CSI） | pair / 日中の強弱。ML の特徴量 | portfolio ではなく特徴量 |
| `fx_own_momentum_20d`（Top-Five 以降の benchmark） | 長 span 上の 20 日・skip なし・日次の断面 momentum。control と benchmark としてだけ使った | **長 span で計算済みの唯一の価格 momentum**。20 日・skip なしで、12-1 とは formation が 12 倍違う。値（T1 / T2 / T4 の control で net 約 +0.07〜+0.17）は既知として開示する |
| H-016 carry（#471） | BIS 政策金利の順位で上下 k = 2 / 3 通貨、2021–25 の 2 年 panel | 断面 carry だが 2 年 panel だけ。長 span では未検定 |
| M15 dollar carry（#494 / #495） | 外国金利平均 − 米金利の符号で USD factor | USD factor であって断面ではない |
| M01 rename gate `CARRY_LEVEL_XS` | 長 span の 3 か月金利の断面 z-score と M01 score の相関（0.321）。P&L は計算していない | 断面 carry の P&L は未計算 |

**結論**: 今回測るのは **long-horizon classical cross-sectional currency momentum premium**（と長 span の断面 carry）である。

- 1999–2016 で 6〜12 か月 formation の断面 momentum を測った過去の検定は無い。
- 同じ span で rank の断面 carry を測った検定も無い。

補足: #496 の報告 §19 は、長 span の momentum を「4〜6 日の momentum 類似」と書いている。実際に長 span で計算されたのは 20 日の benchmark（上の表）である。

## 7. Ranking と合成

- **rank weight**（AMP 2013）: w_c = rank(s_c) − mean(rank)（同順位は平均順位）を Σ|w| = 1 に正規化する。8 通貨全部を使い、上位 / 下位 k の選択を持たない。
- **family の vol を 1 に揃える**: u_k = w_k / σ_k。
  - σ_k は decision day t の**前日まで**（t−252 … t−1）の 252 営業日の、対 USD return の標本共分散から出す。
  - R_t は t の fix（14:15 CET）で初めて確定するので、t の fix で執行する weight には使わない（pre-alpha Role 2 N-2）。
- **合成**: composite = 0.5·u_carry + 0.5·u_momentum。**2 資産の equal risk contribution は相関に依らず w_k ∝ 1/σ_k に一致する**ので、これは厳密な ERC である（test で RC の一致を確認）。return から weight を推定しない。
- **leverage**: ex-ante vol 10% へ。通貨 gross が 5.0 を超える月は 5.0 に縮める（power 計算時点で cap に掛かった月は 0）。
- **holding**: 次の decision day まで exposure を一定に持つ。transaction cost は decision day の Δx にだけ掛かる。
- **年率化**: 252 営業日 / 年（programme の規約）。ECB の暦は約 256 日 / 年なので、年率 return は約 1.5% 小さめに出る（保守側）。

## 8. Financing と会計

既存の `APPROXIMATE_RESEARCH_FINANCING`（#495）を**そのまま**使う。

- **routing**: USD numeraire。P&L = x · R。pair notional = Σ_{c≠USD}|x_c|。
- **carry**: Σ x_c (r_c − r_USD) × 暦日 / 365。
- **金利基準**:
  - primary: 当時の政策金利
  - 感度: lag 付き 3 か月金利
- **markup**: 0 / 0.5% / 1% / 2%（pair notional・年）。central は 0.5%、adverse は 2%。

**行の定義**

| 行 | 定義 |
| --- | --- |
| gross spot | x · R |
| TC-net | `NET_EX_TRANSACTION_COSTS_EXCLUDING_FINANCING` = spot − cost |
| judged net | `TOTAL_ECONOMIC(basis, m)` = spot + carry − cost − m × notional（8 セル） |
| full retail net | `FULL_RETAIL_NET_UNKNOWN` |

actual OANDA financing とは呼ばない。

**headline**: TC-net と judged net（central）を必ず並べる。

- carry を含む book では、carry premium の主部は judged 側に出る。
- それでも裁定 §35 に従い、**TC-net ≤ 0 は失敗**として扱う。
- この要求は、carry 通貨が spot でも正でなければ通らないことを意味し、forward premium puzzle の下では厳しい。裁定どおりに実装している。

**寄与の分解**（pre-alpha Role 1 R2・R3 で修正した）:

- **family 別**: spot と carry は線形なので厳密に分ける。transaction cost は各 family が**実際に売買した量**（|Δx_f|）の比で、markup は外国脚の |x_f| の比で按分する。
- **通貨別**: cross-section 平均を引いた return / 金利（x_c(R_c − R̄)、x_c(r_c − r̄)）で測る。Σx = 0 なので合計は変わらず、numeraire に依らない。

## 9. Power（実行前、`power.json`）

| 項目 | 値 |
| --- | --- |
| 年数 | 16.58 |
| Sharpe の SE | 0.246 |
| 検出下限（両側 5%） | 0.48 |
| MDE（80%） | 0.69 |
| 真の composite Sharpe 0.2 / 0.3 / 0.5 の検出力 | **0.13 / 0.23 / 0.53** |
| 月次 target の lag-1 自己相関 | carry 0.994、momentum 0.834、composite 0.888 |
| 有効標本数 | composite **11.6**、carry **0.58**、momentum 17.7 |

- 2 family の相関の仮定は ρ ∈ {−0.2, 0, 0.2}（文献による。このデータでは測っていない）。
- 各 family の真の Sharpe が 0.2 なら、composite は 0.26〜0.32 で、検出力は 0.18〜0.25。
- **carry はほぼ静的な 1 つの賭け**になる。16 年間、おおむね高金利 AUD / NZD 対 低金利 JPY / CHF を持ち続ける。
- composite の有効標本数は target weight だけで決まり、**F4（≥ 10）は実行前から PASS と分かっている**。その大半は momentum の回転から来る。
- 検出力は低いが、裁定 §19 のとおり走らせる。

## 10. Null（§20）

**primary: 通貨 label の置換**（pre-alpha Role 1 R5 で circular shift から変えた）

- **方法**: 各 draw で 8 通貨の置換 π（恒等置換を除く）を 1 つ引き、**両 family の score の列に同じ π を全期間で**当てる（通貨 i に通貨 π(i) の score を渡す）。book・共分散・return・金利・cost・markup は実際のままにする。
- **draw**: 2,000 draw、seed 20260929（8! − 1 = 40,319 通りから）。
- **保つもの**: score の時系列（持続性・turnover の性質）・2 family の関係・断面の分布・rank weight・vol scaling・会計。
- **壊すもの**: score と、その通貨自身の return・金利の対応（= 情報）。
- **検出力の注意**: AUD / NZD、EUR / CHF のように強く相関する通貨があるので、多くの置換は実際の賭けのほぼ写しになる。4 万通りという数ほどの検出力は無い（再監査の観察）。
- **変えた理由**: carry の target はほぼ静的なので、時間方向の shift では shift 後もほぼ同じ賭けが残る。すると帰無の中心が carry premium そのものを含み、carry premium を検定できない。label 置換は「高金利の**その**通貨群が稼いだのか」を問うので、静的な carry premium も含めて検定できる。

**secondary（報告のみ、判定に使わない）: joint circular shift**

- carry と momentum の日次 score panel を**同じ k 行**だけ巡回させる。k ~ 一様整数 [252, n−252]、2,000 draw、seed 20260930。
- 静的な賭けを含むので中心は 0 ではない。静的な断面を超える timing の情報だけを見る。

**統計量と p**

- 統計量: composite judged net Sharpe（central、判定用）と TC-net Sharpe（併記）。
- p = (1 + #{null ≥ 観測}) / (1 + draw)、percentile = mean(null < 観測)。

## 11. 判定（alpha 前に固定）

**研究の判定**（上から順に評価する。None・非有限は「満たさない」）:

1. post-run review が material defect を BLOCKER とした → `INVALID`（修正 run はしない）
2. TC-net ≤ 0 または judged（central）≤ 0 → `NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`（failure class 付き）
3. primary null（label 置換）の judged の percentile < 0.80 → 同上
4. どちらかの family の composite 内寄与が −0.5 × 合計より小さい → 同上
5. 1 通貨を除いて作り直したとき、judged が正の universe が 6/8 未満 → 同上
6. それ以外 → `POSITIVE_EXPLORATORY_NOT_DECISION_GRADE`

**caveat**（どちらも自動失格ではない）:

- `FAMILY_CONCENTRATION_CAVEAT`: 片 family が 80% 以上。
- `CURRENCY_CONCENTRATION_CAVEAT`: LOO のどれかで judged ≤ 0。

**business**（裁定 §35 を数値に固定した。pre-alpha Role 1 R4）:

- `REQUIRED_SHARPE_GAP_LARGE`: judged Sharpe + 1/√年数 < 0.50。1 標準誤差の上端でも、年 5% の要求 0.50 に届かない。
- `REQUIRED_RISK_INCONSISTENT`: 次のどれか。
  - judged Sharpe ≤ 0
  - 年 5% に要る vol（0.05 / Sharpe）が 15% を超える
  - 観測した最大 DD をその vol へ比例で伸ばした値が −40% より深い
- 15% は裁定 §31 の vol scenario の上端。#496 の算術では、vol 15% で年 5% を狙うと 10 年 DD の中央値は −39% になる。

**F1〜F8**: `prereg.FORWARD_ELIGIBILITY` のとおり。

- 数値で機械的に判定するもの:
  - F2: primary null で percentile ≥ 0.95、または p ≤ 0.05
  - F3: adverse markup で両基準とも正
  - F4: 有効 N ≥ 10（実行前から PASS と分かっている）
  - F5
  - F7: 観測 Sharpe がおよそ 0.36〜0.58 のときだけ通る。それより強い結果は fresh で判断が変わらないので FAIL になる。
- review と report で確定するもの: F1・F6・F8。

**disposition**（code で機械的に出し、F1・F6・F8 は report で確定する）:

| 条件 | disposition |
| --- | --- |
| INVALID | Human へ返す |
| POSITIVE かつ F1〜F8 全 PASS かつ risk inconsistent でない | A. `FRESH_CONFIRMATION_PROPOSAL`（提案だけで、fresh は開かない） |
| POSITIVE かつ gap large でも risk inconsistent でもない | B. `POSITIVE_EXPLORATORY_BUT_NOT_CONFIRMATION_READY` |
| それ以外 | C. `LONG_TERM_HOLD` / `NO_FURTHER_SEEN_DATA_ALPHA_SEARCH` |

**secondary sensitivity**（primary の判定には使わない）:

- cost ×1.5 / ×2（markup も同倍率）
- financing 8 セル
- 診断用の carry 単独 / momentum 単独
- secondary null（circular shift）

## 12. 実行の provenance（§25・§26、pre-alpha Role 2 R-2・R-5 で 2 段階にした）

1. **commit A**: 設計・事前登録・実装・test・pre-alpha review の修正と、その再監査。
2. **commit B1**: `driver.FROZEN_DIGEST` に凍結 digest を入れる。digest はこの 1 行（正確な形の 1 行だけ）を除いて計算するので、入れても digest は変わらない。push する。
3. **commit B2**: `python -m scripts.research.classical_premia.ledger intent` で ledger に `INTENT` 行を書く（freeze digest・親 HEAD・dirty 0・UTC）。
   - 書く条件: digest の一致・clean tree・親 commit の push 済み・ledger が空。
   - commit・push して、GitHub に実行前の時刻を残す。
4. **start**: `driver start` を実行する。次の条件がそろうときだけ `STARTED` を書き、**計算せずに終わる**。
   - ledger が `INTENT` 1 行だけ
   - INTENT を足した commit が HEAD で push 済み
   - tree が clean
   - digest が一致
   - 空き容量 ≥ 5 GB
   - 読み込まれた `scripts.*` が全て閉包の中

   書いた `STARTED` は commit・push する（commit B3）。
5. **compute**: `driver compute` を 1 回だけ実行する。
   - 走る条件: ledger が `INTENT, STARTED`、STARTED の commit が HEAD で push 済み、clean、記録なし。
   - まず生の結果（`execution_raw.json`）・日次 series（`execution_daily.parquet`）・月次 target を**判定の前に** atomic に書く。
   - 次に判定を足した `execution.json` を書き、最後に `COMPLETED` を書く。
   - git の失敗は例外（fail-closed）。例外は捕まえない。compute が落ちても、push 済みの `STARTED` が残る。
6. **commit C**: 実行記録と ledger。
7. **commit D**: post-run の独立 review と最終報告。

結果確認後の再実行はしない。post-run で material defect が見つかったら、その run を INVALID とし、Human + ChatGPT へ返す。

## 13. pre-alpha review の記録

独立の 2 役（別 session）が source を読み直した。どちらにも期待する結論は渡していない。

| 役 | BLOCKER | REQUIRED_FIX | 主な指摘 |
| --- | --- | --- | --- |
| Role 1（economics） | 0 | 5 | R1 spot momentum の文献からの逸脱を明記、R2 family の cost 按分、R3 通貨寄与の numeraire 依存、R4 required risk の数値化と disposition の機械化、R5 carry の静的な賭けを帰無が吸収する |
| Role 2（timing / leakage / governance） | 1（ディスク満杯。実行の前提条件） | 5 | R-1 FROZEN_DIGEST の除外行 bypass、R-2 失敗 run の黙った再実行、R-3 git の fail-open、R-4 日次 series の保存、R-5 commit B の手順 |

- 全て受け入れて修正した。NON_BLOCKING も全て修正するか記録した。
- Role 2 が挙げた欠けていた test 11 本を足し、test は 47 本になった。
- 修正は別の新しい context の再監査に掛けてから凍結する。

**再監査**（別の新しい context、source から再導出）:

- 上の指摘は全て RESOLVED。
- 実データで確認した（P&L は計算していない）:
  - 196 の decision day × 8 通貨の carry signal が、全て前月の BIS 値と一致した（look-ahead なし）。
  - span 内に金利の欠損は無い。
  - `power.json` は現在の code で再現する。
- 新しい REQUIRED_FIX は 3 件で、どれも修正した:
  - NEW-1: JSON の取得記録の hash を CRLF 正規化にした（checkout の改行に依らない digest）。
  - NEW-2: `.gitattributes` に `artifacts/research/classical_premia/** -text` を足した（記録の hash を clone 後も照合できる）。
  - NEW-3: 記録の中の按分の説明を実装に合わせた。
- NON_BLOCKING も全て修正した:
  - compute 開始時の attempt の印（途中で落ちたときの黙った再実行を防ぐ）
  - A を `A_CONDITIONAL_PENDING_F1_F6_F8` と表示する
  - None で落ちない
  - strict JSON
  - test 名
- test は 49 本。
