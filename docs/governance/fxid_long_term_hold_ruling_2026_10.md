# FXID — 長期保留への移行の裁定（2026-10-06）

**最終 state: `FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE`**
**理由の token: `NO_JUSTIFIED_ALPHA_CYCLE_AT_CURRENT_COST_DATA_AND_EVIDENCE`**

`PRODUCTION_READINESS_NOT_CLAIMED`.

**この文書の位置づけ**: FXID（FX intraday system discovery）の研究状態についての **authoritative な記録（single source of truth）**。他の文書は、この文書を参照し、内容を複製しない。

---

## 1. Final ruling

Human + ChatGPT は、`FXID_FINAL_MECHANISM_FEASIBILITY_REVIEW` の最終報告（PR #503）を確認し、次の state を正式に採用した。

> **`FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE`**

FXID の active alpha discovery を停止し、長期保留へ移行する。

## 2. Scope

| 区分 | 範囲 |
| --- | --- |
| 対象 | FXID の研究系列（#500 の再設計 → Cycle 1（#501）→ R-A2b（#502）→ Final Mechanism Feasibility Review（#503））と、その目標（FX のみ・OANDA retail・M15 / H1・当日決済の自動売買） |
| 対象外 | 他の市場、CFD、swing。これらの研究は、この裁定によって承認も否定もされない（別の承認が要る） |

## 3. What the ruling means

次の要素を同時に考えると、**次の alpha research cycle に研究費用・時間・fresh data を投じることを正当化できる独立した根拠が、現時点では存在しない**。

- execution cost
- production の目標（G4）
- 利用可能な data
- 独立な検証ができるか
- 既存研究の結果
- 文献で確認された効果量

## 4. What it does NOT mean

この裁定は、次のどれも意味しない。この裁定を引用して、次のどれも主張してはならない。

- FX の日中に edge が存在しない、という判定ではない（文献上の時刻の構造は実在し、near-miss がある。§6）。
- FX のデイトレードで利益を上げることが原理的にできない、という判定ではない。
- あらゆる戦略を検証した、という判定ではない。検証したのは、この programme の記録にある仮説と、文献で確認した仕組みだけである。
- M15 の解像度では利益が出せない、という判定ではない。
- 過去の RED や HOLD を変えるものではない。逆に、過去の結論を GREEN に変えるものでもない。

## 5. Evidence summary

| 段階 | 記録 | 結論 |
| --- | --- | --- |
| 再設計 | `docs/research/fx_intraday_system_discovery_redesign_2026_10.md`（#500） | 案 A″。cycle 1 は data の実現性と signal-free の統計だけ |
| Cycle 1 | `docs/research/fxid_cycle1_data_feasibility_final_report_2026_10.md`（#501） | `FXID_CYCLE1_EXIT_CONDITION_II_FIRED_RETURN_TO_HUMAN`（5 窓のうち 4 窓で、必要 gross が 4 時間の σ の 15% を超えた） |
| R-A2b | `docs/research/fxid_ny_intraday_economics_followup_2026_10.md`（#502） | `R_A2B_ECON_PARTIAL`（09:00 / 09:30 ET は基準内だが余裕は薄い。post-hoc で独立の証拠ではない）。S1 は除外、S2 の現行の案は保留 |
| 最終の机上の検討 | `docs/research/fxid_final_mechanism_feasibility_review_2026_10.md`（#503） | 採用条件（8 項目）を全て満たす候補は 0 件 |

**0 件になった理由**（3 層）:

**A. Economic magnitude**: 最も有力な EUR の欧州の朝の区間でも、現在の execution cost と production の要求を前提にすると、必要な gross に届かない。

| 区間 | 必要 gross / σ（programme の要求） | 文献の gross / σ |
| --- | --- | --- |
| EUR の欧州の朝の short | 0.131 | 0.078〜0.115 |
| JPY の東京の仲値の後 | 0.126 | 0.115〜0.119 |

必要 gross / σ = (all-in の往復 cost) / σ + 1/√(k · n)。単一の pair で k = 1、n = 250。

**B. Independent validation**: 将来取得できる pre-2016 の履歴は、主要な論文（Breedon & Ranaldo 1997–2007、Krohn・Mueller・Whelan 1999–2018）がその効果を発見し評価した期間の中にある。それを取得して同じ効果を確かめても、**独立した新しい確認とは言えない**。

**C. Recent weakening / implementation limitations**:

- 最近の期間での弱まり（JPY の仲値の後は 2013 年以降と CME 2009–2018 で約 0）
- 非公開の注文 flow が必要（機関の注文 flow）
- M15 より短い解像度が必要（fix の後の反転・仲値の spike）
- 既存の programme で重複・停止済み（月末 = C05、発表の後の drift = #473 の帰無と S2 の保留、日中の momentum = S1 の除外）
- 機会の数が少なすぎる（月末は年 12 回）

これらの**複合の理由**で、候補は 0 件になった。単に backtest で負けたからではない（この系列では alpha の backtest を行っていない）。

## 6. Near-miss mechanisms

**`NO_EDGE` とは記録しない。** 次の 2 つを near-miss として残す。どちらも active candidate ではない。

**EUR の欧州の朝の short（概ね 02:00 ET → 08:15 ET）**:

- 関連する効果が Breedon & Ranaldo（JMCB 2013）と Krohn・Mueller・Whelan（J. Finance 2024）の双方で確認されている。
- firm な気配・全 spread を使った期間でも、正の Sharpe が報告された（B&R の EBS 1997–2007 で 1.3、KMW の CME 2009–2018 で 0.99）。
- 現在想定する retail の執行に置き換えた机上の推定では、net の Sharpe は概ね **0.2〜0.75** の可能性がある。
- ただし programme の要求 `G4 = shrunk Sharpe ≥ 1.0` には届かないので、alpha cycle を正当化しない。

**JPY の東京の仲値の後**: 長期の平均では正の効果があるが、最近の期間では弱まり、2013 年以降と CME 2009–2018 では約 0 に近い。

## 7. Why no alpha cycle is justified

§5 の A・B・C が同時に成り立つため。

- 最も有力な区間でも、真の値が文献の推定どおりなら G4 を満たせず、cycle は最初から失敗が決まる（A）。
- 追加で取れる data では独立な確認ができない（B）。
- 他の仕組みは、実装できないか、重複か、弱まっている（C）。

fresh data は programme の名前に依らず全体で 1 回しか使えないので、根拠の無い cycle に使うことは損失が大きい。

## 8. Preserved statistical / governance settings

将来、研究を再開する場合の baseline として保存する。削除しない。

| 設定 | 保存する内容 |
| --- | --- |
| **data の分割** | 新しく独立な FX 履歴が将来利用できる場合の基本の考え方は、**selection block・独立な estimation block・保護された fresh の confirmation** を分けること。具体的な期間は再開の時に設計し直す。**2021–2025 の seen data を、新しい独立な data に戻してはならない** |
| **G4** | 基本案 `shrunk / posterior expected net Sharpe ≥ 1.0` を維持する（0.8 には下げない）。ただし、将来、複数の低相関の strategy を portfolio にする研究になった場合に、**個々の strategy に必ず Sharpe 1.0 を要求するという意味にはしない**。production の portfolio 全体の目標との関係は、将来改めて設計する |
| **prior** | **未凍結**のまま。`μ = 0, τ = 0.4` は懐疑的な検討案として記録するが、正式な恒久の prior としては固定しない。研究対象の参照クラスが変われば、prior も設計し直す |
| **帰無の案 C**（entry 時刻で区切った block の符号の randomization） | **限定的な候補**としてだけ保存し、標準の手法にはしない |
| fresh / seen の状態 | fresh は保護のまま。seen は seen のまま |

**帰無の案 C の制約**:

- 固定の entry 時刻の family 向け
- 複数の entry 時刻を同時に扱いにくい
- 区間の分割で依存の構造を壊すおそれ
- 前日以前の情報を使う strategy には、そのまま使えない
- 条件付きの対称性などの仮定がある

再開した場合は、その strategy に合った帰無を改めて設計する。

## 9. Restart triggers

次のどれかが**新しく成立した場合にだけ**、`FXID_REOPEN_REVIEW_PROPOSAL` を Human + ChatGPT へ提出してよい。**研究を自動で再開してはならない。** trigger の成立は、提案を出す資格を生むだけである。

**Trigger A — execution cost の大幅な改善**（最も具体的な trigger）:

- 例えば EUR/USD の欧州の朝の区間について、**実際の対象の時間帯の `ALL_IN_ROUND_TRIP_COST ≤ 1.0 BP` が継続的に成り立つ**こと。
  - all-in の往復 = spread + slippage + execution friction。**spread ≤ 1 bp ではない**。
  - 1 回の観測では trigger にしない。継続的で再現可能な執行の条件であること。
- この条件で、EUR の朝の区間の必要 gross / σ はおよそ 0.10 に下がり、文献の 0.078〜0.115 と重なる可能性がある。
- **1 bp 以下になったら自動的に alpha 研究を始める、という意味ではない。** `FXID_REOPEN_REVIEW_PROPOSAL` を提出する資格が生じるだけである。

**Trigger B — 新しい独立な文献**: 主要な論文の sample の終わりの後の独立な期間で、次を全て満たす edge が、査読論文・中央銀行の研究などで新たに確認された場合。

- FX intraday
- 公開の情報だけ
- 現実的な取引 cost を差し引いた後
- 再現可能
- 経済的に意味がある

SNS・ブログ・broker の marketing・backtest の紹介は trigger にしない。

**Trigger C — 公開の flow の情報**: 機関の注文 flow などを、dealer の非公開の情報なしに、**取引の前に**合理的に推定できる、新しい公開の data source や市場制度が登場した場合。

**Trigger D — 市場構造・取引環境の重大な変化**: 例えば次のもの。

- retail の spread の構造的な低下
- 執行と slippage の大幅な改善
- 新しい低 cost の venue
- retail から使える新しい FX microstructure の data
- 取引制度の変更で新しい公開の flow が生じること

**trigger にならないもの**:

- 「AI の model が進化した」
- 「新しい indicator を思いついた」
- 「LightGBM などをもう一度試す」

## 10. Actions prohibited during HOLD

保留の間、FXID について次を行わない。**再開の trigger が観測された場合でも、agent はこれらを自動で行わない。**

- 新しい alpha hypothesis の考案・実装・検証、新しい strategy 案の追加
- price data の取得・新たな読み取り
- alpha の計算・backtest・ML の学習
- signal-free の統計や max-T などの simulation の追加
- fresh / OOS / dead / forward の読み取り
- broker の認証・OANDA への接続
- paper / demo / live trading
- G4 の変更・prior の凍結・Cycle 2 の開始
- CFD や他の市場への拡張（FXID の範囲として）

## 11. Reopen procedure

1. trigger（§9）が成立したと考える場合、まず **`FXID_REOPEN_REVIEW_PROPOSAL`** を Human + ChatGPT へ提出する。提案には次を書く。
   - 何が変わったか
   - なぜ以前の HOLD の理由（§5 の A・B・C）が解消されたか
   - どの仮説を再評価するのか
   - 新しい独立な data は何か
   - cost はいくらか（all-in の往復、継続的な観測の根拠）
   - どの程度の edge が必要か（必要 gross / σ）
   - 最小限どこまで実行すべきか
2. **Human + ChatGPT の新たな明示の承認**を受けるまで、§10 の作業は一切行わない。
3. 承認された場合も、data の取得・読み取り・学習・評価は、それぞれ別の Red の gate として扱う（`autonomous_development_policy.md`）。

## 12. Relationship to previous programme rulings

次は全て**変更せずに維持**する。過去の RED や HOLD を事後に GREEN に変えない。

| programme | 裁定 |
| --- | --- |
| 旧 programme（`EXPECTED_RETURN_SOURCE_DISCOVERY`） | `LONG_TERM_HOLD`、`NO_FURTHER_SEEN_DATA_ALPHA_SEARCH` |
| PATSD（`docs/governance/patsd_stage0_ruling_2026_09_30.md`） | `STAGE0_RED_RETURN_TO_HUMAN` |
| FXID Cycle 1 | `FXID_CYCLE1_EXIT_CONDITION_II_FIRED_RETURN_TO_HUMAN` |
| R-A2b | `R_A2B_ECON_PARTIAL` |
| 最終の机上の検討 | `FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE`（この文書） |

**seen の状態は変えない**。seen の span は全て seen のまま、保護期間（fresh / OOS / dead / forward）は保護のまま。

## 13. Provenance

| PR | merge | 内容 |
| --- | --- | --- |
| #500 | `957fa3d` | 再設計 |
| #501 | `1b05255` | Cycle 1 |
| #502 | `03ce274` | R-A2b |
| **#503** | **`332719e`**（2026-10-05T23:39:01Z。merge の前の head は `58967b7`、CI `contract-tests` / `test` success、独立レビュー 2 役 + 再監査が完了、未解決の BLOCKER なし） | Final Mechanism Feasibility Review |

- 主要な文献は `docs/research/fxid_final_mechanism_feasibility_review_2026_10.md` の §6（L1〜L18、URL / DOI 付き）。
- この裁定の文書は closeout の PR（governance だけ）で追加した。新しい研究の code・strategy・simulation・data の読み取りは含まない。

## 14. Human + ChatGPT approval date

**2026-10-06**（Human + ChatGPT の最終裁定「FXID を正式に LONG_TERM_HOLD へ移行」）。

この文書の merge には、Human + ChatGPT の追加の承認が要る。
