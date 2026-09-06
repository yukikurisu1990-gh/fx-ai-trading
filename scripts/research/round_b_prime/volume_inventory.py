"""B′-VOL — is tick volume recoverable? Code and metadata only.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**No market-data content is read here and none may be.** This module inspects
source files and the archive manifest and answers four questions:

1. does the archive writer emit a `volume` field?
2. where does the research reader drop it?
3. would recovering it for the already-seen spans need a new content read?
4. can coverage be judged from existing metadata alone?

If answering any of them needed an archive file opened for content, the honest
outcome is to stop and say so. It does not: the writer's source, the reader's
`PRICE_KEYS` and the manifest are enough.

The result is a **referral**, not a finding. Whether tick volume carries
information beyond spread and realised volatility is a separate question for a
separately authorised round, and this module does not touch it.
"""

from __future__ import annotations

import inspect
import json
from typing import Any, Final

from scripts.research.exploratory_m15 import bars as bars_module
from scripts.research.exploratory_m15 import momentum, supplemental

MANIFEST: Final = (
    bars_module.REPO_ROOT / "artifacts" / "oanda_archive_2026-05-31" / "candles_manifest.json"
)
FETCH_SOURCES: Final[tuple[str, ...]] = (
    "scripts/fetch_oanda_candles.py",
    "scripts/fetch_oanda_archive.py",
)


def _source(path: str) -> str:
    target = bars_module.REPO_ROOT / path
    return target.read_text(encoding="utf-8") if target.is_file() else ""


def inventory() -> dict[str, Any]:
    """Everything Round B′ is allowed to establish about tick volume."""
    writers = {
        path: {
            "exists": bool(_source(path)),
            "mentions_volume": "volume" in _source(path),
            "emits_volume_field": '"volume"' in _source(path),
        }
        for path in FETCH_SOURCES
    }

    #: where the research reader discards it
    reader_source = inspect.getsource(bars_module)
    price_keys = list(bars_module.PRICE_KEYS)
    dropped = {
        "reader_price_keys": price_keys,
        "volume_in_price_keys": "volume" in price_keys,
        "reader_mentions_volume": "volume" in reader_source,
        "note": (
            "read_m1 copies only PRICE_KEYS out of each decoded row, so `volume` is "
            "present in the parsed dict and discarded before `to_m15` ever sees it; "
            "the M15 parquet caches therefore have no volume column and no "
            "aggregate of one."
        ),
    }

    #: the same is true of the other two routes, which share PRICE_KEYS
    routes = {
        "bars": bars_module.SOURCE_TEMPLATE,
        "supplemental": supplemental.SOURCE_TEMPLATE,
        "momentum": momentum.SOURCE_TEMPLATE,
    }

    #: coverage, from the manifest only -- no file is opened for content
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    m1 = [e for e in manifest["files"] if e["granularity"] == "M1" and e["days"] == 3650]
    coverage = {
        "manifest_fields": sorted(m1[0]) if m1 else [],
        "manifest_records_volume": any("volume" in str(k).lower() for k in (m1[0] if m1 else {})),
        "m1_files": len(m1),
        "common_first": max((e["first_time"][:10] for e in m1), default=None),
        "common_last": min((e["last_time"][:10] for e in m1), default=None),
        "total_rows": sum(e["row_count"] for e in m1),
        "note": (
            "the manifest records row counts and time bounds per file but no "
            "per-field statistics, so whether volume is populated (rather than "
            "merely present in the schema) cannot be judged from metadata alone"
        ),
    }

    recovery = {
        "requires_new_content_read": True,
        "requires_new_span": False,
        "reason": (
            "the field is in the archive rows but not in any M15 cache, so "
            "recovering it means re-decoding the already-seen spans. That is a "
            "re-read of EXPLORATORY_SEEN_DATA, not an extension of scope: the "
            "spans are already seen and cannot become unseen. It is still a "
            "market-data content read and therefore a separate authorisation."
        ),
    }

    return {
        "writers": writers,
        "reader": dropped,
        "route_templates": routes,
        "coverage_from_metadata": coverage,
        "recovery": recovery,
        "content_read_performed": False,
        "referral": (
            "TICK_VOLUME_INFORMATION_INVENTORY_CONFIRMED_PENDING_SEPARATE_AUTHORISED_RESEARCH"
        ),
        "first_question_if_authorised": (
            "is tick volume close to a deterministic function of spread and realised "
            "volatility, or does it carry information neither of them has? Nothing "
            "downstream is worth designing until that is answered."
        ),
    }


__all__ = ["FETCH_SOURCES", "MANIFEST", "inventory"]
