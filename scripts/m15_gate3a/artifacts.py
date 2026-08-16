"""Metadata artifact validation + writing under a per-artifact **allowlist**.

Gate-3a/gate-5 metadata artifacts carry NO strategy metrics, predictions, model
outputs, trade-level rows or readiness claims. The previous design tried to
enforce that with a *denylist* of container shapes and literal label spellings,
and the third independent source-audit re-check (B-1) showed the denylist could
not hold: the same 300 records re-keyed as a dict-of-dicts scanned clean, a
claim embedded in a sentence scanned clean, and a Cyrillic or zero-width
homoglyph scanned clean — while the one construct governance expressly permits,
a prohibition list, was refused.

**What replaced it.** Each artifact this gate may write declares a schema: the
key vocabulary permitted anywhere in the payload, which of those keys may carry
a numeric leaf, which may carry a prohibition list, and the list/leaf/numeric
budgets implied by those declarations. A payload that resolves to a schema is
checked against it and everything outside it is refused, in **any** container
shape — re-keying cannot help, because the keys themselves must be declared.
A payload that resolves to no schema falls to a shape-agnostic backstop: the
inherited shape heuristics *plus* total numeric-leaf and total-leaf budgets that
a re-encoding cannot evade.

Claim detection is layered here rather than in :mod:`scripts.m15_gate3a.guards`:
that module's :func:`is_forbidden_status` is an exact whole-string predicate over
*labels*, which is the right contract for a label predicate and the wrong one for
a scrubber. This module folds NFKC, confusable (Cyrillic/Greek) homoglyphs,
combining marks and zero-width/format characters, then scans **substrings**, in
the manner :mod:`scripts.foundation_t2.scrub` already does in-repo.

**What this module actually guarantees (RF-15).** The previous docstring claimed
it "refuses to write under any protected real path". That was false and is not
restated. What is true:

* every write is preceded by :func:`scripts.m15_gate3a.guards.refuse_real_path`
  on both the output directory and the joined target, so a path naming or
  sitting under a tree in that module's protected set is refused — a set which
  deliberately does **not** contain ``artifacts/m15_gate3a`` (D-7);
* the writer **never overwrites**: an existing target is refused outright, which
  is what keeps the human-reviewed committed artifacts out of reach of a code
  path rather than a prefix list (D-7, §12.17);
* a refused write leaves nothing behind — no file, and no directory this call
  created (RF-9);
* nothing here reads a file. The module's only filesystem primitives are
  ``mkdir``, ``write_text`` and the existence/removal calls the refusal and
  clean-up paths need.

Containment of an *unrouted* caller is not a property this module has, and must
not be cited as one.

**Negative-control rule (R-1, §12.19).** This module mints no self-attestation.
It deliberately exposes no ``cleanliness_report``-style emitter: a ``clean``
flag beside a fixed ``checks`` list is exactly the one-valued field R-1 deletes
rather than reports. :func:`scan_gate3a` returns the findings themselves, and
both of its outcomes are reachable on every rule it implements.
"""

from __future__ import annotations

import math
import re
import unicodedata
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from scripts.ml_step4 import evidence

from .guards import FORBIDDEN_STATUSES, is_forbidden_status, refuse_real_path
from .pair_authority import PAIRS_20


class ArtifactScrubError(RuntimeError):
    """Raised when a gate-3a metadata artifact would leak forbidden content."""


# ---------------------------------------------------------------------------
# Character folding — the input to every claim decision
# ---------------------------------------------------------------------------

# Confusables that render as a Latin letter but carry a different code point.
# NFKC folds the fullwidth and mathematical forms; it does **not** fold these,
# which is why `"PАSS"` (U+0410) scanned clean before. Only visually identical
# pairs are listed: a fold that is not visually justified would refuse honest
# text without closing anything.
_CONFUSABLES: Final[dict[str, str]] = {
    # Cyrillic capitals
    "А": "A",
    "В": "B",
    "Е": "E",
    "З": "3",
    "К": "K",
    "М": "M",
    "Н": "H",
    "О": "O",
    "Р": "P",
    "С": "C",
    "Т": "T",
    "У": "Y",
    "Х": "X",
    "Ѕ": "S",
    "І": "I",
    "Ј": "J",
    "Ү": "Y",
    "Ӏ": "I",
    "Ԛ": "Q",
    "Ԝ": "W",
    # Cyrillic smalls
    "а": "a",
    "е": "e",
    "о": "o",
    "р": "p",
    "с": "c",
    "у": "y",
    "х": "x",
    "ѕ": "s",
    "і": "i",
    "ј": "j",
    "ԛ": "q",
    "ԝ": "w",
    "м": "m",
    "н": "h",
    "т": "t",
    # Greek capitals
    "Α": "A",
    "Β": "B",
    "Ε": "E",
    "Ζ": "Z",
    "Η": "H",
    "Ι": "I",
    "Κ": "K",
    "Μ": "M",
    "Ν": "N",
    "Ο": "O",
    "Ρ": "P",
    "Τ": "T",
    "Υ": "Y",
    "Χ": "X",
    # Greek smalls
    "α": "a",
    "ε": "e",
    "ι": "i",
    "κ": "k",
    "ν": "v",
    "ο": "o",
    "ρ": "p",
    "τ": "t",
    "χ": "x",
    "υ": "u",
    # Latin/other lookalikes not covered by NFKC
    "ı": "i",
    "ɡ": "g",
    "ǀ": "I",
    "Ⲓ": "I",
    "Ꭰ": "A",
    "Ꮮ": "L",
    "ᑭ": "C",
    "ᴏ": "O",
}

# Categories carrying no glyph: format (zero-width space/joiner, soft hyphen,
# BOM, word joiner), control, and combining marks left over after NFKD. Each is
# invisible in a rendered artifact, so none may separate a claim from itself.
_INVISIBLE_CATEGORIES: Final[frozenset[str]] = frozenset({"Cf", "Cc", "Mn", "Me"})


def _pin(text: str) -> str:
    """Pin a ``str``'s character data, defeating a two-faced subclass.

    ``str(text)`` re-enters an overridden ``__str__``, so a subclass can show
    one string to a check and another to the consumer. The same technique is
    used by :func:`scripts.m15_gate3a.path_authority.resolve_candidate`.
    """
    return str.__str__(text)


def _fold(text: str) -> str:
    """NFKC + confusables + NFKD + invisible-character removal."""
    folded = unicodedata.normalize("NFKC", _pin(text))
    folded = "".join(_CONFUSABLES.get(ch, ch) for ch in folded)
    folded = unicodedata.normalize("NFKD", folded)
    return "".join(ch for ch in folded if unicodedata.category(ch) not in _INVISIBLE_CATEGORIES)


def _spaced(text: str) -> str:
    """Folded text with every non-alphanumeric run collapsed to one space.

    Case is **preserved**: a label written in its registered casing is a label,
    while the same letters in lower-case prose ("buckets that pass the
    cost-hurdle") are English. That distinction is what lets the scrubber refuse
    ``"PASS"`` without refusing the committed effective-N spec.
    """
    return " " + re.sub(r"[^0-9A-Za-z]+", " ", _fold(text)).strip() + " "


def _dense(text: str) -> str:
    """Folded text with every non-alphanumeric character removed, upper-cased."""
    return re.sub(r"[^0-9A-Za-z]+", "", _fold(text)).upper()


# ---------------------------------------------------------------------------
# Forbidden claims
# ---------------------------------------------------------------------------

# Labels whose letters also spell ordinary English. A dense substring scan for
# these would refuse honest prose (the committed effective-N spec contains "pass
# the cost-hurdle"), so they are matched as **delimited tokens** — either in the
# label's registered upper-case spelling, or after a claim connector in any
# casing. Every other forbidden label is unique enough that a substring hit is a
# claim; new labels added to `FORBIDDEN_STATUSES` therefore default to the
# stricter treatment.
_AMBIGUOUS_CLAIM_KEYS: Final[frozenset[str]] = frozenset({"PASS", "MEETS", "ROBUST", "VALIDATED"})
_UNAMBIGUOUS_CLAIM_KEYS: Final[frozenset[str]] = (
    frozenset(_dense(s) for s in FORBIDDEN_STATUSES) - _AMBIGUOUS_CLAIM_KEYS
)
# Words that turn an ambiguous token into an assertion about the subject.
_CLAIM_CONNECTORS: Final[str] = (
    "STATUS|RESULT|VERDICT|OUTCOME|CONCLUSION|READINESS|GRADE|ASSESSMENT|RATING|DECISION"
)
_AMBIGUOUS_PATTERNS: Final[tuple[tuple[str, re.Pattern[str], re.Pattern[str]], ...]] = tuple(
    (
        key,
        re.compile(rf"(?<![0-9A-Za-z]){key}(?![0-9A-Za-z])"),
        re.compile(
            rf"(?<![0-9A-Za-z])(?:{_CLAIM_CONNECTORS})\s+{key}(?![0-9A-Za-z])",
            re.IGNORECASE,
        ),
    )
    for key in sorted(_AMBIGUOUS_CLAIM_KEYS)
)

# A forbidden label used as a dict key is a *disclaimer* when its value denies
# it. RF-8: truthiness was the previous proxy, which refused
# `{"PRODUCTION_READY": "no"}` (a denial) and passed `{"PRODUCTION_READY": False}`
# only by accident of the same rule. Denial is now an explicit, closed
# vocabulary; anything else — including a number, a container, or `True` — is an
# assertion and is refused.
_NEGATION_VALUES: Final[frozenset[str]] = frozenset(
    {
        "FALSE",
        "NO",
        "NOT",
        "NONE",
        "NEVER",
        "NA",
        "NOTCLAIMED",
        "NOTASSERTED",
        "NOTAPPLICABLE",
        "NOTPERFORMED",
        "DENIED",
        "REFUSED",
        "FORBIDDEN",
        "PROHIBITED",
        "BLOCKED",
        "ABSENT",
    }
)
# Deliberately absent: "PENDING", "TBD" and their kin. Those defer a claim rather
# than denying it, and the stricter reading of a research restriction wins — a
# key naming a forbidden status is refused unless its value actually denies it.


def _is_denial(value: Any) -> bool:
    """True iff *value* explicitly denies the claim its key would otherwise make."""
    if value is False:
        return True
    return isinstance(value, str) and _dense(value) in _NEGATION_VALUES


def _claim_keys(text: str) -> list[str]:
    """Forbidden-claim labels detected in *text*, by substring and by folding."""
    hits: list[str] = []
    dense = _dense(text)
    hits.extend(sorted(key for key in _UNAMBIGUOUS_CLAIM_KEYS if key and key in dense))
    spaced = _spaced(text)
    for key, exact, connected in _AMBIGUOUS_PATTERNS:
        if exact.search(spaced) or connected.search(spaced):
            hits.append(key)
    if is_forbidden_status(_fold(text)) and not hits:
        hits.append(dense)
    return hits


# ---------------------------------------------------------------------------
# Forbidden key vocabulary (RF-7)
# ---------------------------------------------------------------------------

# RF-7: the previous set was exact-match, so `sharpe_ratio`, `sharpeRatio`,
# `net_pnl`, `max_drawdown_pct`, `hit_rate`, `profit_factor`,
# `expectancy_per_trade` and `total_return` all passed. Matching is now over the
# key's **word tokens** (snake, kebab, camel and spaced spellings all split the
# same way), so a metric root cannot hide behind a qualifier.
_FORBIDDEN_KEY_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "sharpe",
        "sortino",
        "calmar",
        "expectancy",
        "pnl",
        "drawdown",
        "profit",
        "payoff",
        "equity",
        "backtest",
        "predictions",
        "prediction",
        "logits",
        "proba",
        "probability",
        "probabilities",
        "weights",
        "model",
        "trades",
        "return",
        "returns",
    }
)
_FORBIDDEN_KEY_PHRASES: Final[tuple[tuple[str, ...], ...]] = (
    ("hit", "rate"),
    ("win", "rate"),
    ("validation", "metrics"),
    ("holdout", "metrics"),
    ("trade", "level"),
    ("trade", "rows"),
    ("model", "binary"),
)


def _key_tokens(key: str) -> tuple[str, ...]:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", _fold(key))
    return tuple(t for t in re.split(r"[^0-9A-Za-z]+", text.lower()) if t)


def _forbidden_key_hit(key: str) -> str | None:
    tokens = _key_tokens(key)
    for token in tokens:
        if token in _FORBIDDEN_KEY_TOKENS:
            return token
    for phrase in _FORBIDDEN_KEY_PHRASES:
        span = len(phrase)
        for start in range(len(tokens) - span + 1):
            if tokens[start : start + span] == phrase:
                return "_".join(phrase)
    return None


# ---------------------------------------------------------------------------
# Per-artifact schemas — the allowlist
# ---------------------------------------------------------------------------

# Container budgets are DERIVED from committed authority, never chosen:
#   * a list may not be longer than the frozen 20-pair universe — every list in
#     every committed artifact is shorter, and the roster is the largest
#     collection this gate legitimately describes;
#   * a prohibition list may name every forbidden label, so its bound is the
#     size of the guards' `FORBIDDEN_STATUSES` set and tracks it;
#   * per schema, numeric leaves are bounded by (roster size + 1) x the number of
#     keys that schema declares numeric, and total leaves by roster size x the
#     size of the schema's key vocabulary.
_MAX_LIST_ITEMS: Final[int] = len(PAIRS_20)
_MAX_PROHIBITION_ITEMS: Final[int] = len(FORBIDDEN_STATUSES)
# The per-key half of the schema numeric budget, made explicit rather than left
# implicit in the product below. A declared numeric key describes ONE quantity,
# so the most it can legitimately carry is one value per roster entry plus one
# aggregate — which is exactly the factor the schema budget was already derived
# from. The mutation workstream reproduced 340 float price values parked under
# the declared numeric key `pip_size` (chunked into 17 lists of 20, so neither
# the list bound nor the schema-wide budget of 357 fired) scanning with
# `findings=[]`. A declared key is a licence to hold *a* number, not a series.
_MAX_VALUES_PER_NUMERIC_KEY: Final[int] = _MAX_LIST_ITEMS + 1

# The committed `design_m15_inventory.json` `required_schema_per_file` block —
# the only per-file record shape this gate has committed authority for. Its key
# count and numeric-field count are what bound an *undeclared* payload, so the
# backstop invents no threshold of its own. Transcribed verbatim, including the
# confusable `eligible_event_count` (C-8): only the two *lengths* are consumed
# below, and re-spelling the transcription would silently move a derived bound
# while claiming to quote a committed artifact.
_COMMITTED_PER_FILE_KEYS: Final[tuple[str, ...]] = (
    "filename",
    "pair",
    "sha256",
    "size_bytes",
    "row_count",
    "eligible_event_count",
    "ts_min_utc",
    "ts_max_utc",
    "gap_report",
    "pip_size",
)
_COMMITTED_PER_FILE_NUMERIC_KEYS: Final[tuple[str, ...]] = (
    "size_bytes",
    "row_count",
    "eligible_event_count",
    "pip_size",
    "missing_minute_count",
    "max_gap_minutes",
)
_UNDECLARED_MAX_NUMERIC_LEAVES: Final[int] = _MAX_LIST_ITEMS * len(_COMMITTED_PER_FILE_NUMERIC_KEYS)
_UNDECLARED_MAX_LEAVES: Final[int] = _MAX_LIST_ITEMS * len(_COMMITTED_PER_FILE_KEYS)


@dataclass(frozen=True)
class ArtifactSchema:
    """The permitted schema for one gate-3a artifact.

    ``allowed_keys`` is the complete key vocabulary: any key appearing at any
    depth must be in it. ``numeric_keys`` is the subset whose values may carry a
    numeric leaf, so a price series cannot be parked under a descriptive key.
    ``prohibition_list_keys`` are the keys under which a forbidden label is
    *named as prohibited* rather than asserted — the one usage playbook §10
    permits, and the construct the previous denylist refused.

    Being in ``numeric_keys`` licenses at most
    :data:`_MAX_VALUES_PER_NUMERIC_KEY` values for that key across the whole
    payload, not an array of arbitrary length: see
    :func:`_scan_declared`.
    """

    stem: str
    artifact_names: frozenset[str]
    allowed_keys: frozenset[str]
    numeric_keys: frozenset[str]
    prohibition_list_keys: frozenset[str] = frozenset()

    @property
    def filename(self) -> str:
        return f"{self.stem}.json"

    @property
    def max_numeric_leaves(self) -> int:
        return _MAX_VALUES_PER_NUMERIC_KEY * len(self.numeric_keys)

    @property
    def max_leaves(self) -> int:
        return _MAX_LIST_ITEMS * len(self.allowed_keys)

    def list_bound(self, key: str | None) -> int:
        if key is not None and key in self.prohibition_list_keys:
            return _MAX_PROHIBITION_ITEMS
        return _MAX_LIST_ITEMS


def _schema(
    stem: str,
    keys: tuple[str, ...],
    numeric: tuple[str, ...],
    *,
    artifact_names: tuple[str, ...] = (),
    prohibition_lists: tuple[str, ...] = (),
) -> ArtifactSchema:
    """Build a schema with every vocabulary folded to its comparison casing."""
    return ArtifactSchema(
        stem=stem,
        artifact_names=frozenset(n.lower() for n in (artifact_names or (stem,))),
        allowed_keys=frozenset(k.lower() for k in (*keys, *numeric, *prohibition_lists)),
        numeric_keys=frozenset(k.lower() for k in numeric),
        prohibition_list_keys=frozenset(k.lower() for k in prohibition_lists),
    )


# Key vocabularies are the committed artifacts' own, extended only where a
# committed ruling names the extension: `design_m15_inventory` gains the
# populated-inventory record list, the six missing-minute quantities approved by
# the contract Gate-decision §5 (D-3), and the pinned-term renames required by
# §12.20 (R-2); `scrub_report` gains the prohibition-list vocabulary playbook
# §10 permits. Nothing else is invented here.
_SCHEMAS: Final[tuple[ArtifactSchema, ...]] = (
    _schema(
        "design_m15_derivation_manifest",
        (
            "aggregation_config_hash",
            "aggregation_contract",
            "aggregation_script_git_sha",
            "aggregation_script_path",
            "artifact",
            "bucket_convention",
            "byte_reproducible_from_source",
            "derivation_identity_required_at_implementation",
            "design_end_utc",
            "design_span_cut",
            "design_start_utc",
            "event_label_eligibility",
            "excludes_dead_window",
            "gate",
            "imputation",
            "incomplete_buckets",
            "input_identity",
            "metadata_only",
            "mid_price_construction_at_aggregation",
            "missing_minute_policy",
            "ohlc_rule",
            "personal_paths",
            "pip_size_authority",
            "purpose",
            "raw_candles_committed",
            "raw_rows_committed",
            "role",
            "scrub",
            "secrets",
            "source_checksum_authority",
            "source_epoch_id",
            "source_inventory_path",
            "source_pairs",
            "source_timeframe",
            "spread_field",
            "status",
            "synthetic_weekend_bars",
            "timezone",
            "value_pinned_tests_required_before_any_real_read",
        ),
        ("source_file_count",),
    ),
    _schema(
        "design_m15_inventory",
        (
            "all_ts_max_within_design_end",
            "all_ts_min_within_design_start",
            "artifact",
            # C-8 / §12.20 — `eligible_event_count` is admissible as a *key* and
            # NOT as a numeric one. The committed `design_m15_inventory.json`
            # uses it inside `required_schema_per_file` to *describe* a field
            # ("count of n_source_bars==15 buckets"), so removing it from the
            # vocabulary outright would make committed evidence — which D-7 says
            # is populated by human-reviewed PR diff and which this PR may not
            # edit — stop scanning clean. Leaving it in `numeric_keys` was the
            # worse failure the contract/specification audit named: the
            # scrubber would silently accept a continuation that *populated*
            # the confusable name, and confusing it with the effective-N spec's
            # traded-event quantity clears the frozen floors by orders of
            # magnitude and disarms `INSUFFICIENT_SAMPLE`. Declared here, the
            # committed descriptive usage stays clean while a populated
            # `eligible_event_count: 21500` is reported as
            # `gate3a_undeclared_numeric_field`. §12.20's pinned name
            # `complete_bucket_count` is the only spelling that may carry the
            # quantity; retiring the old key from the vocabulary lands with the
            # inventory schema extension at the continuation, in the same
            # human-reviewed diff that repopulates the artifact.
            "eligible_event_count",
            "filename",
            "files",
            "gap_report",
            "gate",
            "metadata_only",
            "pair",
            "raw_rows_committed",
            "reason_not_populated_now",
            "required_aggregate_assertions",
            "required_schema_per_file",
            "scrub",
            "sha256",
            "status",
            "ts_max_utc",
            "ts_min_utc",
        ),
        (
            "absent_source_minute_count",
            "complete_bucket_count",
            "cost_hurdle_eligible_bar_count",
            "dead_window_bars_present",
            "expected_source_minute_count",
            "file_count",
            "max_gap_minutes",
            "max_unavailable_gap_minutes",
            "missing_minute_count",
            "observed_source_minute_count",
            "pip_size",
            "raw_traded_event_count",
            "rejected_source_minute_count",
            "row_count",
            "size_bytes",
            "usable_source_minute_count",
        ),
    ),
    _schema(
        "forward_epoch_adoption_manifest",
        (
            "adoption_for_research_only",
            "artifact",
            "as_of_utc",
            "committed_source_epoch_ts_max_utc",
            "earliest_data_complete_estimate_utc",
            "earliest_feasible_adoption_estimate_utc",
            "feasibility_finding",
            "forward_epoch_source",
            "forward_epoch_start_floor_utc",
            "forward_inventory_sha256",
            "frozen_requirement",
            "gate",
            "holdout_span_utc",
            "metadata_only",
            "no_overlap_proof",
            "note_committed_epoch",
            "personal_paths",
            "production_ready",
            "raw_rows_committed",
            "retention_binding",
            "scrub",
            "secrets",
            "status",
            "to_be_fixed_when_adopted_at_a_future_gate_3a_continuation",
            "validation_span_utc",
            "verdict",
        ),
        (
            "committed_forward_epoch_bars_in_repo",
            "elapsed_months_approx",
            "elapsed_since_forward_floor_as_of_2026_07_07_days_approx",
            "holdout_min_span_months",
            "purge_embargo_m15_bars",
            "total_min_forward_span_months_approx",
            "validation_min_span_months",
        ),
    ),
    _schema(
        "forward_epoch_inventory",
        (
            "artifact",
            "filename",
            "files",
            "gate",
            "metadata_only",
            "raw_rows_committed",
            "reason",
            "required_schema_when_populated",
            "role",
            "scrub",
            "sha256",
            "status",
            "ts_max_utc",
            "ts_min_utc",
        ),
        ("file_count", "size_bytes"),
    ),
    _schema(
        "no_overlap_proof",
        (
            "artifact",
            "assert",
            "boundary_constants_utc",
            "committed_365d_ba_epoch_ts_max_utc",
            "committed_365d_ba_epoch_ts_min_utc",
            "consequence",
            "dead_window_end",
            "dead_window_start",
            "design_end",
            "design_start",
            "forward_epoch_floor",
            "gate",
            "id",
            "lhs",
            "machine_checkable_assertions",
            "metadata_only",
            "overall",
            "policy",
            "raw_rows_committed",
            "requirement",
            "result",
            "rhs",
            "scrub",
            "source",
            "source_metadata_evidence",
            "t1_feature_warmup_leakage_addressed",
        ),
        ("files_checked",),
    ),
    _schema(
        "effective_n_estimator_spec",
        (
            "artifact",
            "correlation_estimation_data",
            "cross_pair_discount",
            "daily_aggregation_dependence_note",
            "definitions",
            "failure_handling",
            "frozen_parameters",
            "gate",
            "granularity",
            "holdout",
            "horizon_overlap_factor",
            "metadata_only",
            "must_report_raw_and_effective",
            "no_strategy_metrics_computed_at_gate3a",
            "per_pair_effective",
            "per_role",
            "portfolio_effective",
            "purpose",
            "raw_event_count",
            "raw_rows_committed",
            "reporting",
            "scrub",
            "status",
            "trade_count_floor",
            "validation",
        ),
        ("H_m15_bars", "N_eff_holdout_floor", "raw_holdout_trade_floor"),
    ),
    _schema(
        "cost_table_plan_or_metadata",
        (
            "all_in_cost_formula",
            "artifact",
            "asia",
            "claim_scope",
            "data_source_restriction",
            "europe",
            "gate",
            "granularity",
            "median_quoted_spread",
            "metadata_only",
            "must_produce_before_gate7_authorisation",
            "no_raw_data_read_at_gate3a",
            "option_selected",
            "p90_session_spread",
            "p95_session_spread",
            "pip_conversion_policy",
            "rationale",
            "raw_rows_committed",
            "scrub",
            "sessions_utc",
            "statistics",
            "stress_forms",
            "us",
        ),
        ("execution_padding_pip", "flat_slippage_cell_pip"),
        artifact_names=("cost_table_plan", "cost_table_plan_or_metadata"),
    ),
    _schema(
        "scrub_report",
        (
            "artifact",
            "assertions",
            "checked_artifacts",
            "content_kind",
            "credentials_or_secrets",
            "findings",
            "gate",
            "google_drive_or_r2_secrets",
            "holdout_metrics_committed",
            "metadata_only",
            "model_binaries_committed",
            "model_outputs_committed",
            "personal_or_local_paths",
            "predictions_committed",
            "raw_candles_committed",
            "raw_price_rows_committed",
            "result",
            "strategy_performance_metrics_committed",
            "trade_level_outputs_committed",
            "validation_metrics_committed",
        ),
        ("checked_artifact_count",),
        prohibition_lists=(
            "forbidden_labels",
            "prohibited_labels",
            "forbidden_statuses",
            "prohibited_statuses",
        ),
    ),
)

_SCHEMAS_BY_STEM: Final[dict[str, ArtifactSchema]] = {s.stem.lower(): s for s in _SCHEMAS}
_SCHEMAS_BY_ARTIFACT: Final[dict[str, ArtifactSchema]] = {
    name: s for s in _SCHEMAS for name in s.artifact_names
}
# The longest registered forbidden label: a prohibition-list entry longer than
# this is not a label, so the exemption from claim scanning does not reach it.
_MAX_PROHIBITION_ENTRY_LEN: Final[int] = max(len(s) for s in FORBIDDEN_STATUSES)

# The gate-3a artifact filenames, derived from the schema table so the two
# cannot drift (the previous literal tuple had neither consumer nor test).
EXPECTED_ARTIFACT_FILES: Final[tuple[str, ...]] = tuple(s.filename for s in _SCHEMAS)


def artifact_schema(name: str) -> ArtifactSchema | None:
    """The declared schema for an artifact stem, filename or ``artifact`` value."""
    if not isinstance(name, str):
        return None
    key = _pin(name).strip().lower()
    if key.endswith(".json"):
        key = key[: -len(".json")]
    return _SCHEMAS_BY_STEM.get(key) or _SCHEMAS_BY_ARTIFACT.get(key)


# ---------------------------------------------------------------------------
# Shared leaf checks
# ---------------------------------------------------------------------------


def _is_numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _non_finite(value: Any) -> bool:
    """D6 / RF-10: ``json.dumps`` emits the non-standard ``NaN`` / ``Infinity``.

    RF-10: this inspected values only, so a non-finite **key** was unscanned and
    silently stringified to ``"NaN"`` by ``json.dumps``. Keys are now checked on
    the same predicate.
    """
    return isinstance(value, float) and not math.isfinite(value)


def _scan_key_claims(key: Any, value: Any, findings: list[str]) -> None:
    """Claim / metric checks for a dict key, with the RF-8 disclaimer exemption."""
    if not isinstance(key, str):
        return
    denial = _is_denial(value)
    hits = _claim_keys(key)
    if hits and not denial:
        findings.append(f"gate3a_forbidden_status_key:{key}")
    metric = _forbidden_key_hit(key)
    if metric is not None and not denial:
        findings.append(f"gate3a_forbidden_key:{key}")


def _scan_value_claims(value: Any, findings: list[str], *, exempt: bool) -> None:
    if not isinstance(value, str) or exempt:
        return
    for hit in _claim_keys(value):
        findings.append(f"gate3a_forbidden_status_value:{hit}")


# ---------------------------------------------------------------------------
# Declared scan — the allowlist proper
# ---------------------------------------------------------------------------


@dataclass
class _Counters:
    numeric: int = 0
    leaves: int = 0
    #: numeric leaves seen per *declared numeric* key, for the per-key bound.
    per_numeric_key: dict[str, int] = field(default_factory=dict)


def _scan_declared(
    obj: Any,
    schema: ArtifactSchema,
    findings: list[str],
    counters: _Counters,
    *,
    numeric_allowed: bool,
    exempt: bool,
    key_label: str | None,
) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if not isinstance(key, str):
                findings.append(f"gate3a_non_string_key:{key!r}")
                if _non_finite(key):
                    findings.append("gate3a_non_finite_key")
                # F2-3: report the key AND scan what sits under it. The previous
                # `continue` did neither: 30 x 8 numeric price rows under a
                # single `int` key reported `gate3a_non_string_key:0` and the
                # entire subtree beneath it was never examined, so one
                # unrenderable key exempted a whole dataset. A non-string key
                # declares nothing, so nothing below it may carry a numeric
                # leaf, and the label it passes down must not be the *parent's*
                # — `{"pip_size": {0: [...]}}` would then report a violation
                # against `pip_size`, a key that really is declared numeric.
                _scan_declared(
                    value,
                    schema,
                    findings,
                    counters,
                    numeric_allowed=False,
                    exempt=exempt,
                    key_label=f"non_string_key({key!r})",
                )
                continue
            pinned = _pin(key)
            folded = pinned.strip().lower()
            if folded not in schema.allowed_keys:
                findings.append(f"gate3a_undeclared_key:{pinned}")
            _scan_key_claims(pinned, value, findings)
            child_exempt = exempt or folded in schema.prohibition_list_keys
            _scan_declared(
                value,
                schema,
                findings,
                counters,
                numeric_allowed=folded in schema.numeric_keys,
                exempt=child_exempt,
                key_label=folded,
            )
        return
    if isinstance(obj, (list, tuple)):
        bound = schema.list_bound(key_label)
        if len(obj) > bound:
            findings.append(f"gate3a_list_longer_than_declared:{key_label}")
        for item in obj:
            _scan_declared(
                item,
                schema,
                findings,
                counters,
                numeric_allowed=numeric_allowed,
                exempt=exempt,
                key_label=key_label,
            )
        return
    counters.leaves += 1
    if counters.leaves > schema.max_leaves:
        findings.append("gate3a_leaf_cardinality_exceeded")
    if _non_finite(obj):
        findings.append(f"gate3a_non_finite_value:{key_label}")
    if _is_numeric(obj):
        counters.numeric += 1
        if counters.numeric > schema.max_numeric_leaves:
            findings.append("gate3a_numeric_cardinality_exceeded")
        if not numeric_allowed:
            findings.append(f"gate3a_undeclared_numeric_field:{key_label}")
        elif key_label is not None:
            # F2-2: a declared numeric key may hold a value per roster entry
            # plus an aggregate — the very factor `max_numeric_leaves` is
            # derived from — and not a series. Without this, 340 prices chunked
            # into 17 lists of 20 sat under `pip_size` with `findings=[]`:
            # every chunk was within the list bound and the total was under the
            # schema-wide budget, which is a budget for ALL numeric keys
            # together.
            seen = counters.per_numeric_key.get(key_label, 0) + 1
            counters.per_numeric_key[key_label] = seen
            if seen > _MAX_VALUES_PER_NUMERIC_KEY:
                findings.append(f"gate3a_numeric_series_under_declared_key:{key_label}")
    elif isinstance(obj, str):
        _scan_value_claims(obj, findings, exempt=exempt)
        if exempt and len(_pin(obj)) > _MAX_PROHIBITION_ENTRY_LEN:
            findings.append(f"gate3a_prohibition_entry_too_long:{key_label}")
    elif obj is not None and not isinstance(obj, bool):
        findings.append(f"gate3a_undeclared_value_type:{type(obj).__name__}")


# ---------------------------------------------------------------------------
# Undeclared backstop — shape-agnostic, plus the inherited shape heuristics
# ---------------------------------------------------------------------------

# Inherited O-2 / R-5 heuristics. They are a denylist and are kept only as a
# backstop for payloads that declare no schema: >= 2 dicts each carrying >= 6
# numeric (non-bool) immediate values (a full BA row has 8 numeric sides), and
# >= 2 numeric arrays of length >= 4 (the columnar encoding of the same rows).
# Both counts are taken over a container's members whether that container is a
# `list`/`tuple` or a `dict` — counting them in lists alone was itself the
# re-keying route (F2-2). B-1 showed shape heuristics can be re-keyed around at
# all, which is why the cardinality budgets below run alongside them and count
# leaves rather than shapes.
_ROW_LIKE_MIN_RECORDS: Final[int] = 2
_ROW_LIKE_MIN_NUMERIC_FIELDS: Final[int] = 6
_COLUMNAR_MIN_SERIES: Final[int] = 2
_COLUMNAR_MIN_LENGTH: Final[int] = 4


def _numeric_field_count(d: dict) -> int:
    return sum(1 for v in d.values() if _is_numeric(v))


def _row_like_count(values: Any) -> int:
    """How many of *values* are row-like records (a dict of >= 6 numeric fields)."""
    return sum(
        1
        for value in values
        if isinstance(value, dict) and _numeric_field_count(value) >= _ROW_LIKE_MIN_NUMERIC_FIELDS
    )


def _is_numeric_series(value: Any) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) >= _COLUMNAR_MIN_LENGTH
        and all(_is_numeric(v) for v in value)
    )


def _scan_undeclared(
    obj: Any, findings: list[str], counters: _Counters, *, key_label: str | None = None
) -> None:
    if isinstance(obj, dict):
        series_count = sum(1 for v in obj.values() if _is_numeric_series(v))
        if series_count >= _COLUMNAR_MIN_SERIES:
            findings.append("gate3a_columnar_numeric_series")
        # F2-2: the row-like count applied to `list`/`tuple` items only, so the
        # identical records re-keyed as a dict-of-dicts were counted nowhere.
        # 15 x 8 price rows that way land on exactly 120 numeric leaves — the
        # undeclared budget, which bounds but does not exceed — and scanned with
        # `findings=[]`. The record count is a property of the records, not of
        # the container they were poured into.
        if _row_like_count(obj.values()) >= _ROW_LIKE_MIN_RECORDS:
            findings.append("gate3a_row_like_numeric_records")
        for key, value in obj.items():
            if not isinstance(key, str):
                findings.append(f"gate3a_non_string_key:{key!r}")
                if _non_finite(key):
                    findings.append("gate3a_non_finite_key")
                # Same labelling rule as the declared scan: a finding raised
                # under a non-string key names that key, never the parent's.
                _scan_undeclared(value, findings, counters, key_label=f"non_string_key({key!r})")
                continue
            pinned = _pin(key)
            _scan_key_claims(pinned, value, findings)
            _scan_undeclared(value, findings, counters, key_label=pinned)
        return
    if isinstance(obj, (list, tuple)):
        if _row_like_count(obj) >= _ROW_LIKE_MIN_RECORDS:
            findings.append("gate3a_row_like_numeric_records")
        numeric_rows = sum(1 for x in obj if _is_numeric_series(x))
        if numeric_rows >= _ROW_LIKE_MIN_RECORDS:
            findings.append("gate3a_row_like_numeric_arrays")
        for item in obj:
            _scan_undeclared(item, findings, counters, key_label=key_label)
        return
    counters.leaves += 1
    if counters.leaves > _UNDECLARED_MAX_LEAVES:
        findings.append("gate3a_leaf_cardinality_exceeded")
    if _non_finite(obj):
        findings.append(f"gate3a_non_finite_value:{key_label}")
    if _is_numeric(obj):
        counters.numeric += 1
        if counters.numeric > _UNDECLARED_MAX_NUMERIC_LEAVES:
            findings.append("gate3a_numeric_cardinality_exceeded")
    elif isinstance(obj, str):
        _scan_value_claims(obj, findings, exempt=False)


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

_UNSCANNABLE: Final[tuple[type[BaseException], ...]] = (
    TypeError,
    ValueError,
    OverflowError,
    RecursionError,
)


def resolve_schema(payload: Any, artifact: str | None) -> tuple[ArtifactSchema | None, list[str]]:
    """Resolve the declared schema for *payload*, reporting any mismatch.

    A payload may declare itself through its own ``artifact`` field; a writer
    additionally supplies the filename stem. When both are present they must
    agree — otherwise a payload could carry a permissive artifact's schema while
    being written under another artifact's name.
    """
    findings: list[str] = []
    self_declared: ArtifactSchema | None = None
    if isinstance(payload, dict):
        raw = payload.get("artifact")
        if isinstance(raw, str):
            self_declared = artifact_schema(raw)
            if self_declared is None and _pin(raw).strip():
                findings.append(f"gate3a_undeclared_artifact_name:{_pin(raw)}")
    by_filename = artifact_schema(artifact) if artifact is not None else None
    if artifact is not None and self_declared is not None and by_filename is not self_declared:
        findings.append(f"gate3a_artifact_name_mismatch:{artifact}")
        return None, findings
    return (by_filename or self_declared), findings


def scan_gate3a(payload: Any, *, artifact: str | None = None) -> list[str]:
    """Base scrubber findings PLUS the gate-3a allowlist / claim prohibitions."""
    findings: list[str] = []
    try:
        findings.extend(evidence.scan_payload(payload))
    # Reachable: a deeply nested payload raises RecursionError inside the base
    # scanner. Pinned by
    # test_a_payload_the_scanner_cannot_traverse_is_a_finding_not_a_crash.
    except _UNSCANNABLE as exc:
        findings.append(f"gate3a_unscannable_payload:{type(exc).__name__}")
    # RF-11: a payload declared clean that `serialise` cannot write used to die
    # with a bare `TypeError` at the write. It now fails here, as a scrub error.
    try:
        evidence.serialise(payload)
    except _UNSCANNABLE as exc:
        findings.append(f"gate3a_unserialisable_payload:{type(exc).__name__}")
    schema, resolution_findings = resolve_schema(payload, artifact)
    findings.extend(resolution_findings)
    counters = _Counters()
    try:
        if schema is None:
            _scan_undeclared(payload, findings, counters)
        else:
            _scan_declared(
                payload,
                schema,
                findings,
                counters,
                numeric_allowed=False,
                exempt=False,
                key_label=None,
            )
    except RecursionError:
        findings.append("gate3a_payload_too_deeply_nested")
    return sorted(set(findings))


def assert_gate3a_clean(payload: Any, *, artifact: str | None = None) -> None:
    findings = scan_gate3a(payload, artifact=artifact)
    if findings:
        raise ArtifactScrubError(f"gate-3a artifact not clean: {findings}")


def validate_metadata_artifact(payload: Any, *, artifact: str | None = None) -> None:
    """Fail closed unless the payload is a scrub-clean metadata object.

    RF-22 / RF-27: the vacuity floor is explicit. A bare label, a number or
    ``None`` is not a metadata artifact, and neither is an empty container —
    each used to be accepted under a mutation of the type test alone.
    """
    if isinstance(payload, (dict, list)) is False or isinstance(payload, bool):
        raise ArtifactScrubError(
            f"metadata artifact must be an object or array, got {type(payload).__name__}"
        )
    if len(payload) == 0:
        raise ArtifactScrubError("metadata artifact must not be empty")
    assert_gate3a_clean(payload, artifact=artifact)


def _validate_name(name: Any) -> str:
    """Pin and validate a bare ``*.json`` artifact filename (RF-6).

    The checks used to run against the object handed in, so a ``str`` subclass
    overriding ``endswith``, ``__eq__`` or ``__contains__`` answered them one way
    and gave ``out / name`` a different string. The character data is pinned once
    and every later use — including the join — reads the pinned value.
    """
    if not isinstance(name, str):
        raise ArtifactScrubError(f"artifact name must be a str, got {type(name).__name__}")
    text = _pin(name)
    if "\x00" in text:
        raise ArtifactScrubError("artifact name containing a NUL byte refused")
    if not text.endswith(".json"):
        raise ArtifactScrubError(f"artifact name must end with .json, got {text!r}")
    if (
        text != Path(text).name
        or Path(text).is_absolute()
        or any(sep in text for sep in ("/", "\\", ":"))
    ):
        raise ArtifactScrubError(f"artifact name must be a bare filename, got {text!r}")
    if not text[: -len(".json")].strip().strip("."):
        raise ArtifactScrubError(f"artifact name needs a non-empty stem, got {text!r}")
    return text


def _missing_ancestors(out: Path) -> list[Path]:
    """Directories that do not exist yet, deepest first."""
    missing: list[Path] = []
    probe = out
    while True:
        try:
            if probe.exists():
                return missing
        except (OSError, ValueError):  # pragma: no cover - defensive
            return missing
        missing.append(probe)
        if probe.parent == probe:
            return missing
        probe = probe.parent


def write_metadata_artifact(out_dir: str | Path, name: str, payload: Any) -> Path:
    """Validate + write a scrub-clean gate-3a metadata artifact.

    Order matters and is part of the contract: both path refusals run before any
    directory is created, the payload is validated against the schema its
    filename declares, an existing target is refused rather than overwritten
    (D-7 — the committed artifacts are populated by human-reviewed PR diff, not
    by a code path), and any failure at the write itself removes the partial file
    and every directory this call created (RF-9).
    """
    text = _validate_name(name)
    out = Path(out_dir)
    refuse_real_path(out)
    target = out / text
    refuse_real_path(target)
    validate_metadata_artifact(payload, artifact=text)
    serialised = evidence.serialise(payload)
    if target.exists():
        raise ArtifactScrubError(
            f"refusing to overwrite an existing artifact: {text} (D-7: existing evidence is "
            "never rewritten by a code path)"
        )
    created = _missing_ancestors(out)
    try:
        out.mkdir(parents=True, exist_ok=True)
        target.write_text(serialised, encoding="utf-8")
    except (OSError, ValueError) as exc:
        with suppress(OSError):
            target.unlink()
        for directory in created:
            with suppress(OSError):
                directory.rmdir()
        raise ArtifactScrubError(f"artifact write failed for {text!r}: {exc}") from exc
    return target
