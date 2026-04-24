# Phase 9.10 — Cost-aware backtest (Phase A) Design Memo

**Status**: Design phase (2026-04-25)
**Dependency**: Phase 9.1-9.8 完了 (master tip `be9ae30`)
**Owner**: くりす
**Related**: `docs/phase9_roadmap.md` §6.12

---

## 1. 目的

Phase 9.1-9.8 で確立した D3 scaffolding と Phase 9.9 相当で実行した multi-pair ML 選択 backtest の結果 (Sharpe 0.351 / PnL 230k pip / 10 ペア) に対し、**取引コストを組み込んだ上でエッジが残るか**を検証する。

### 1.1 なぜ必要か (2026-04-25 時点の backtest 結果から導出)

現行 `scripts/compare_multipair_v2.py` の結果:

| 指標 | 値 | 問題点 |
|------|-----|--------|
| ヒット率 | 58.3% | 良好 |
| TP / SL | 3 pip / 2 pip | **EUR/USD 典型 spread 1 pip を引くと edge 消失** |
| Signal rate | 91.0% | **毎分トレードは非現実的** |
| Gross EV/trade | +0.90 pip | **spread 後 -0.10 pip (赤字)** |
| Sharpe (gross) | 0.334 | spread 後の実態不明 |

**Go/No-Go gate**: この phase でスプレッド後 Sharpe ≥ 0.20 かつ PnL > 0 を達成できない場合、Phase 9.11 以降の投資は無意味。戦略設計見直しに進む。

---

## 2. 変更範囲と非変更範囲

### 2.1 In Scope

1. `Quote` DTO に `bid` / `ask` optional フィールド追加 (既存 `.price` mid は維持)
2. `OandaQuoteFeed` が bid/ask を populate
3. `fetch_oanda_candles` に `--price BA` モード追加
4. `Candle` DTO / `CandleFileBarFeed` / `CandleReplayQuoteFeed` で bid/ask 伝搬
5. `PaperBroker` が bid/ask を使って buy/sell 別約定
6. `BidAskSpreadModel` — bid/ask 欠損時に合成 spread を注入するオプション
7. cost-aware backtest script (`scripts/compare_multipair_v3_costs.py`)
8. TP/SL/confidence grid search script (`scripts/grid_search_tp_sl_conf.py`)

### 2.2 Out of Scope (後続 phase 送り)

- ATR-based dynamic TP/SL → Phase 9.12
- 経済指標 filter → Phase 9.12
- 本番 Kelly sizing → Phase 9.13
- OANDA demo 実走 → Phase 9.14

### 2.3 既存契約の維持 (変更なし)

- `QuoteFeed` Protocol: `get_quote(instrument) -> Quote` の signature 不変
- `run_exit_gate` / `MetaDecider` / `MetaCycleRunner` の API 不変
- 既存テストは全て green 維持

---

## 3. PR 分割計画

| PR | 対象 | 規模目安 | 依存 |
|----|------|---------|------|
| **A-1** | `Quote` bid/ask 拡張 + `OandaQuoteFeed` 対応 | ≤200 行 | master |
| **A-2** | `PaperBroker` bid/ask fill + `BidAskSpreadModel` | ≤250 行 | A-1 |
| **A-3** | `fetch_oanda_candles --price BA` | ≤150 行 | master (独立) |
| **A-4** | `Candle` 拡張 + `CandleFileBarFeed` / `CandleReplayQuoteFeed` bid/ask 伝搬 | ≤300 行 | A-1, A-3 |
| **A-5** | `compare_multipair_v3_costs.py` + EUR/USD 1 年データの BA 取得 | ≤500 行 | A-4 |
| **A-6** | `grid_search_tp_sl_conf.py` + 最終結果レポート | ≤400 行 | A-5 |
| **A-7** | `docs/design/phase9_10_closure_memo.md` (Go/No-Go 判定) | docs only | A-6 |

---

## 4. 詳細設計

### 4.1 Quote DTO 拡張 (PR #A-1)

```python
@dataclass(frozen=True)
class Quote:
    price: float                  # mid (既存、必須)
    ts: datetime                  # 既存、必須
    source: str                   # 既存、必須
    bid: float | None = None      # 新規、optional
    ask: float | None = None      # 新規、optional

    def __post_init__(self) -> None:
        # 既存 tz check
        if self.ts.tzinfo is None:
            raise ValueError(...)
        # 新規: bid/ask が両方指定されたら price が (bid+ask)/2 であること
        if self.bid is not None and self.ask is not None:
            expected_mid = (self.bid + self.ask) / 2.0
            if abs(expected_mid - self.price) > 1e-9:
                raise ValueError(
                    f"Quote.price ({self.price}) != (bid+ask)/2 ({expected_mid})"
                )
```

**後方互換**: 既存呼び出し側 (`Quote(price=X, ts=T, source=S)`) は一切変更不要。

### 4.2 PaperBroker bid/ask fill (PR #A-2)

```python
def place_order(self, request: OrderRequest) -> OrderResult:
    self._verify_account_type_or_raise(self._account_type)
    quote = self._quote_feed.get_quote(request.instrument) if self._quote_feed else None

    if quote is None:
        base_price = self._nominal_price
    elif quote.bid is not None and quote.ask is not None:
        # bid/ask populated → use side-aware price
        base_price = quote.ask if request.side == "buy" else quote.bid
    else:
        # fallback: mid + synthetic spread via BidAskSpreadModel
        half_spread = self._spread_model.half_spread(request.instrument)
        base_price = quote.price + half_spread if request.side == "buy" else quote.price - half_spread

    fill_price = self._slippage.apply(base_price, request.side)
    ...
```

`BidAskSpreadModel` Protocol:
```python
class BidAskSpreadModel(Protocol):
    def half_spread(self, instrument: str) -> float:
        """Return half of the synthetic bid-ask spread in price units."""
        ...

class FixedPipSpreadModel:
    """1 pip = 0.0001 for most, 0.01 for JPY pairs."""
    def __init__(self, spread_pip: float = 1.0): ...
```

### 4.3 fetch_oanda_candles --price BA (PR #A-3)

OANDA の `price=BA` はレスポンスに `bid` と `ask` の両方を返す:
```json
{
  "time": "2026-04-23T20:00:00Z",
  "bid": {"o": 1.16798, "h": 1.16803, "l": 1.16796, "c": 1.16800},
  "ask": {"o": 1.16802, "h": 1.16807, "l": 1.16800, "c": 1.16804},
  "volume": 17
}
```

JSONL 出力形式 (`--price BA` 時):
```json
{"time": "...", "volume": 17,
 "bid_o": 1.16798, "bid_h": 1.16803, "bid_l": 1.16796, "bid_c": 1.16800,
 "ask_o": 1.16802, "ask_h": 1.16807, "ask_l": 1.16800, "ask_c": 1.16804}
```

従来の `--price M` モード (default) は変更なし (`o/h/l/c` のみ)。

### 4.4 cost-aware backtest (PR #A-5)

`compare_multipair_v3_costs.py` のエントリー/エグジット:

```python
# Long entry: pay ask at t+1 open
entry_price = row["ask_o"]  # next bar open ask

# TP check (long): bid_high reaches entry + TP
for k in range(1, horizon + 1):
    if future_bars[k]["bid_h"] >= entry_price + tp_pip * pip_size:
        return "TP", entry_price + tp_pip * pip_size

# SL check (long): bid_low reaches entry - SL
    if future_bars[k]["bid_l"] <= entry_price - sl_pip * pip_size:
        return "SL", entry_price - sl_pip * pip_size

# Timeout: exit at bid_close of bar t+horizon
return "TIMEOUT", future_bars[horizon]["bid_c"]
```

Short サイドは bid/ask を逆転 (entry at bid_o, TP check ask_l, SL check ask_h).

### 4.5 Grid search (PR #A-6)

```python
# 掃引対象 = 100 組合せ (5 × 4 × 5)
TP_CANDIDATES = [5, 8, 10, 15, 20]  # pip
SL_CANDIDATES = [3, 5, 8, 10]        # pip
CONF_CANDIDATES = [0.45, 0.50, 0.55, 0.60, 0.65]

for tp, sl, conf in itertools.product(...):
    # Re-label with new TP/SL, re-run backtest
    sharpe, pnl, signal_rate = run_backtest(tp, sl, conf)
    results.append((tp, sl, conf, sharpe, pnl, signal_rate))

# Output: heatmap-ready table
```

---

## 5. テスト戦略

- **PR #A-1**: `Quote(price=1.5, bid=1.498, ask=1.502)` の consistency check; `Quote(price=1.5)` (bid/ask なし) も動作
- **PR #A-2**: mock `QuoteFeed` で `Quote(bid=1.498, ask=1.502)` を返し、buy → fill=1.502, sell → fill=1.498 を検証
- **PR #A-3**: mock OANDA response (BA 形式) を使った fetch の roundtrip
- **PR #A-4**: JSONL → `Candle` → `Quote` の bid/ask 伝搬 e2e
- **PR #A-5**: 合成 candle (明確な TP/SL hit) で spread 後 PnL の算出を golden number pin
- **PR #A-6**: 小規模 grid (TP={5,10}, SL={3,5}, conf={0.5}) で smoke

---

## 6. Go/No-Go 判定 (closure memo で記載)

| 判定 | 条件 | 次 phase |
|------|------|---------|
| **GO** | spread 後 SELECTOR Sharpe ≥ 0.20 かつ PnL > 0 かつ signal rate ≤ 30% の組合せが grid 上に存在 | Phase 9.11 進行 |
| **SOFT GO** | Sharpe ≥ 0.15 の組合せは存在するが ≥ 0.20 不達 | Phase 9.12 (quality improvement) を先行し、再判定 |
| **NO-GO** | どの組合せでも Sharpe < 0.15 または PnL ≤ 0 | 戦略設計を見直し — roadmap 再策定 |

---

## 7. リスク

| リスク | 緩和 |
|--------|------|
| OANDA BA 取得が API 2 倍コスト | 一度取得したら parquet 化して回避 (Phase 9.11 で本格化) |
| No-Go 判定時の scope 膨張 | 本 phase では **判定のみ**。再設計は別 phase で scope 切り |
| bid/ask 欠損 candle (希少) | `BidAskSpreadModel` fallback で continuity 維持 |
| `Quote` post_init の consistency check が既存 fixture を壊す | tolerance 1e-9 で浮動小数点誤差吸収、誤差超過は明示的 raise |

---

## 8. 補足: 検証用データの整備

Phase 9.10 の backtest データは既存の `data/candles_*_M1_365d.jsonl` (price=M) とは別に、**`data/candles_*_M1_365d_BA.jsonl`** として取得する。ファイル名 suffix `_BA` で mid 版と共存。

fetch コマンド例:
```bash
python scripts/fetch_oanda_candles.py \
    --instrument EUR_USD --granularity M1 --days 365 \
    --price BA \
    --output data/candles_EUR_USD_M1_365d_BA.jsonl
```

---

## 9. タイムライン (想定)

- PR #A-1 (Quote): Day 1 — 小規模、即日 merge 目標
- PR #A-2 (PaperBroker): Day 1-2
- PR #A-3 (fetch BA): Day 2
- PR #A-4 (Candle 伝搬): Day 3
- **データ取得**: Day 3-4 (10 ペア × 365 日 × BA モード、bulk fetch)
- PR #A-5 (v3 cost backtest): Day 4-5
- PR #A-6 (grid search + 実行): Day 5-6
- PR #A-7 (closure memo + 判定): Day 7

合計 1 週間。
