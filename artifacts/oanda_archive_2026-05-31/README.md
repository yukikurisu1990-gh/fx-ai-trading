# OANDA Archive 2026-05-31 — 10-year FX candle snapshot

Emergency preservation snapshot taken on 2026-05-31 (Japan time)
immediately before OANDA practice account API access was scheduled
to be revoked due to tier downgrade.

## Scope

- **Source environment**: `practice` (OANDA practice account)
- **Captured at (UTC)**: 2026-05-31T15:47:13.798111+00:00
- **Pair universe**: PAIRS_20 (canonical 20 pairs from
  `scripts/stage23_0a_build_outcome_dataset.py::PAIRS_20`)
- **Granularities**: M1, M5, M15, H1, H4, D
- **History depth**: 3650 days (~10 years)
- **Price mode**: BA (bid + ask OHLC; matches existing `_BA.jsonl` schema)
- **Schema authority**: `scripts/stage23_0a_build_outcome_dataset.py::load_m1_ba`
  fields = time, bid_o, bid_h, bid_l, bid_c, ask_o, ask_h, ask_l, ask_c

## Outcome

- Files manifested: **120 / 120**
- Completed by fetcher: 119
- Pre-existing (skipped): 1 (smoke-test EUR_USD daily)
- Failed: 0
- Total rows: **93,897,607**
- Total bytes: **17.54 GB**
- Total elapsed: **149.3 min**

## Coverage range (UTC)

| Granularity | Files | Rows | Earliest | Latest |
|---|---|---|---|---|
| M1 | 20 | 72,449,857 | 2016-06-02T13:17:00.000000000Z | 2026-05-29T20:59:00.000000000Z |
| M5 | 20 | 14,873,783 | 2016-06-02T13:20:00.000000000Z | 2026-05-29T20:55:00.000000000Z |
| M15 | 20 | 4,968,432 | 2016-06-02T13:15:00.000000000Z | 2026-05-29T20:45:00.000000000Z |
| H1 | 20 | 1,242,677 | 2016-06-02T13:00:00.000000000Z | 2026-05-29T20:00:00.000000000Z |
| H4 | 20 | 310,887 | 2016-06-02T13:00:00.000000000Z | 2026-05-29T17:00:00.000000000Z |
| D | 20 | 51,971 | 2016-06-01T21:00:00.000000000Z | 2026-05-28T21:00:00.000000000Z |

## Per-pair × per-granularity row counts

| Pair | M1 | M5 | M15 | H1 | H4 | D |
|---|---|---|---|---|---|---|
| AUD_CAD | 3,692,191 | 745,077 | 248,471 | 62,130 | 15,539 | 2,593 |
| AUD_JPY | 3,686,457 | 745,262 | 248,517 | 62,141 | 15,545 | 2,599 |
| AUD_NZD | 3,685,303 | 744,586 | 248,428 | 62,125 | 15,540 | 2,595 |
| AUD_USD | 3,457,024 | 740,772 | 248,349 | 62,125 | 15,538 | 2,592 |
| CHF_JPY | 3,692,243 | 743,689 | 248,267 | 62,130 | 15,541 | 2,595 |
| EUR_AUD | 3,637,612 | 744,458 | 248,446 | 62,128 | 15,540 | 2,594 |
| EUR_CAD | 3,704,226 | 745,086 | 248,474 | 62,130 | 15,539 | 2,593 |
| EUR_CHF | 3,515,833 | 742,913 | 248,428 | 62,132 | 15,540 | 2,594 |
| EUR_GBP | 3,577,851 | 744,260 | 248,465 | 62,130 | 15,541 | 2,595 |
| EUR_JPY | 3,638,281 | 744,327 | 248,434 | 62,122 | 15,538 | 2,594 |
| EUR_USD | 3,607,252 | 743,885 | 248,469 | 62,131 | 15,539 | 2,593 |
| GBP_AUD | 3,698,474 | 744,642 | 248,379 | 62,117 | 15,537 | 2,592 |
| GBP_CHF | 3,684,823 | 743,895 | 248,332 | 62,134 | 15,544 | 2,598 |
| GBP_JPY | 3,692,772 | 745,158 | 248,489 | 62,136 | 15,544 | 2,598 |
| GBP_USD | 3,586,423 | 743,445 | 248,465 | 62,134 | 15,543 | 2,597 |
| NZD_JPY | 3,700,439 | 744,969 | 248,457 | 62,148 | 15,558 | 2,612 |
| NZD_USD | 3,566,798 | 743,003 | 248,436 | 62,146 | 15,554 | 2,608 |
| USD_CAD | 3,613,836 | 743,631 | 248,472 | 62,156 | 15,564 | 2,618 |
| USD_CHF | 3,375,234 | 736,505 | 248,167 | 62,135 | 15,547 | 2,601 |
| USD_JPY | 3,636,785 | 744,220 | 248,487 | 62,147 | 15,556 | 2,610 |

## File-byte total per pair

| Pair | Total bytes | Total MB |
|---|---|---|
| AUD_CAD | 959,529,209 | 915.1 |
| AUD_JPY | 924,772,175 | 881.9 |
| AUD_NZD | 958,671,602 | 914.3 |
| AUD_USD | 909,639,059 | 867.5 |
| CHF_JPY | 960,525,685 | 916.0 |
| EUR_AUD | 948,211,428 | 904.3 |
| EUR_CAD | 963,688,829 | 919.0 |
| EUR_CHF | 922,119,732 | 879.4 |
| EUR_GBP | 935,046,422 | 891.7 |
| EUR_JPY | 948,589,142 | 904.6 |
| EUR_USD | 942,242,955 | 898.6 |
| GBP_AUD | 963,428,233 | 918.8 |
| GBP_CHF | 959,054,061 | 914.6 |
| GBP_JPY | 961,194,772 | 916.7 |
| GBP_USD | 938,312,623 | 894.8 |
| NZD_JPY | 923,755,665 | 881.0 |
| NZD_USD | 933,125,204 | 889.9 |
| USD_CAD | 943,465,875 | 899.8 |
| USD_CHF | 892,473,282 | 851.1 |
| USD_JPY | 948,768,795 | 904.8 |

## Retention policy notes

This preservation snapshot is **independently captured raw input**
under PR #361 §6's dependency-inventory framework.
Per PR #361 §7 retention principle, the raw JSONL files sit under
`data/` (gitignored) on local disk and the SHA-256 + row-count +
timestamp-range manifest at `candles_manifest.json` provides the
durable provenance record. The raw data is **NOT** committed to
git (size + anti-pattern avoidance).

If this archive is to become a binding authority for a future
dataset epoch (per the PR #361 / PR #362 / PR #363 contract),
a separately authorised retention step (per Gate P2) must establish
a content-addressed immutable storage destination for the bytes
themselves — the manifest alone is insufficient (PR #361 §7).

## File list (full inventory)

See `candles_manifest.json` for per-file SHA-256, row count,
size_bytes, first_time, last_time.