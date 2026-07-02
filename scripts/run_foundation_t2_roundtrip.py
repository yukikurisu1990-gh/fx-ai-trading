"""CLI for the Foundation T2 retention deposit + round-trip harness.

Prepares a metadata-only multi-span deposit manifest from committed PR-B.1
evidence, resolves the primary destination, and — only if the destination is
safely available with credentials — would deposit / restore / verify. In this
environment the real primary destination is NOT configured/credentialed and no
env-var / network / cloud access is performed, so the harness STOPS BEFORE
DEPOSIT and writes honest metadata-only evidence (it never fakes success).

Usage::

    python scripts/run_foundation_t2_roundtrip.py --run-id t2-all-spans-001 \\
        --git-sha <sha> --base-master-sha <sha> --generated-at <iso> \\
        --authorisation-ref "<operator authorisation>"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.foundation_t2.constants import (  # noqa: E402
    RETENTION_PROBE_REMAINS_UNRESOLVED,
    T2_CREDENTIALS_UNAVAILABLE,
    T2_DEPOSIT_NOT_PERFORMED,
    T2_EXECUTION_ATTEMPTED_WITH_AUTHORISATION,
    T2_EXECUTION_STOPPED_BEFORE_DEPOSIT,
    T2_RESTORE_NOT_PERFORMED,
    T2_ROUNDTRIP_NOT_PERFORMED,
    T2_SPANS,
)
from scripts.foundation_t2.destination import (  # noqa: E402
    DestinationUnavailableError,
    resolve_primary_destination,
)
from scripts.foundation_t2.evidence import build_roundtrip_report, write_evidence  # noqa: E402
from scripts.foundation_t2.manifest import T2ManifestError, build_deposit_manifest  # noqa: E402
from scripts.foundation_t2.scrub import EvidenceScrubError  # noqa: E402

DEFAULT_OUTPUT_ROOT = _REPO_ROOT / "artifacts" / "foundation_t2"


def _render_markdown(report: dict) -> str:
    lines = [
        "# Foundation T2 round-trip harness + pre-deposit stop evidence",
        "",
        "**Execution stopped before deposit.** No deposit, no restore/download, "
        "and no round-trip verification were performed; the retention probe "
        "remains unresolved. This PR delivers the T2 harness and honest "
        "pre-deposit stop evidence only.",
        "",
        f"- run_id: `{report['run_id']}`",
        f"- destination_logical_alias: `{report['destination_logical_alias']}`",
        f"- target_spans: {', '.join(report['target_spans'])}",
        f"- top_level_status: `{report['top_level_status']}`",
        f"- real_cloud_deposit_status: `{report['real_cloud_deposit_status']}`",
        f"- retention_probe_status: `{report['retention_probe_status']}`",
        "",
        "## Per-span status",
        "",
        "| span | deposit | restore | round-trip |",
        "| --- | --- | --- | --- |",
    ]
    for s in report["per_span_status"]:
        lines.append(
            f"| {s['span_id']} | {s['deposit_status']} | {s['restore_status']} | "
            f"{s['roundtrip_status']} |"
        )
    lines += [
        "",
        "## SHA-256 provenance",
        "",
        "SHA-256 values in the manifest are copied verbatim from committed "
        "PR-B.1 metadata; they were not recomputed in this PR and no raw "
        "candidate bytes were read.",
        "",
        "## Non-scope",
        "",
        "Metadata-only evidence. No raw rows, credentials, env values, signed "
        "URLs, tokens, or local absolute paths. Retention probe remains "
        "unresolved; byte-admissibility not approved; new epoch not authorised; "
        "ML Step 4 not authorised. No production change, no model / backtest / "
        "trading metric. Backup HDD and IPFS sidecar NOT executed (deferred). "
        "Harness round-trip mechanics are validated synthetically in tests; no "
        "real cloud round-trip was performed here.",
        "",
    ]
    return "\n".join(lines)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_foundation_t2_roundtrip",
        description="Foundation T2 deposit + round-trip harness (metadata-only evidence).",
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--git-sha", default=None)
    parser.add_argument("--base-master-sha", default=None)
    parser.add_argument("--generated-at", default=None)
    parser.add_argument("--authorisation-ref", default="UNSPECIFIED_OPERATOR_AUTHORISATION")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        manifest = build_deposit_manifest(_REPO_ROOT, args.run_id, spans=T2_SPANS)
    except T2ManifestError as exc:
        sys.stderr.write(f"[T2 stop] file set ambiguous: {exc}\n")
        return 2

    # Resolve the primary destination. In this environment it is unavailable
    # (no credentials / configuration; no env-var / network access performed),
    # so the harness stops before deposit and never fakes success.
    destination = resolve_primary_destination()
    real_deposit_status = T2_EXECUTION_STOPPED_BEFORE_DEPOSIT
    reason = None
    try:
        destination.observe("mock://probe/none")  # unavailable stub raises
    except DestinationUnavailableError as exc:
        reason = str(exc) or T2_CREDENTIALS_UNAVAILABLE

    destination_available = reason is None

    per_span = [
        {
            "span_id": block["span_id"],
            "file_count": block["file_count"],
            "deposit_status": "NOT_PERFORMED",
            "restore_status": "NOT_PERFORMED",
            "roundtrip_status": "NOT_PERFORMED",
            "reason": reason or T2_CREDENTIALS_UNAVAILABLE,
        }
        for block in manifest["spans"]
    ]

    # Do NOT claim "attempted with authorisation" unless the destination was
    # actually available. On the stopped path only the honest did-not-happen
    # statuses are recorded — the harness never fakes an attempt or a success.
    if destination_available:
        extra_statuses = [T2_EXECUTION_ATTEMPTED_WITH_AUTHORISATION]
        retention_probe_status = RETENTION_PROBE_REMAINS_UNRESOLVED
    else:
        extra_statuses = [
            T2_EXECUTION_STOPPED_BEFORE_DEPOSIT,
            reason or T2_CREDENTIALS_UNAVAILABLE,
            T2_DEPOSIT_NOT_PERFORMED,
            T2_RESTORE_NOT_PERFORMED,
            T2_ROUNDTRIP_NOT_PERFORMED,
            RETENTION_PROBE_REMAINS_UNRESOLVED,
        ]
        retention_probe_status = RETENTION_PROBE_REMAINS_UNRESOLVED

    report = build_roundtrip_report(
        args.run_id,
        manifest,
        git_sha=args.git_sha,
        base_master_sha=args.base_master_sha,
        generated_at=args.generated_at,
        authorisation_reference=args.authorisation_ref,
        real_deposit_status=real_deposit_status,
        top_level_status=T2_EXECUTION_STOPPED_BEFORE_DEPOSIT,
        retention_probe_status=retention_probe_status,
        per_span=per_span,
        extra_statuses=extra_statuses,
    )
    markdown = _render_markdown(report)

    output_dir = Path(args.output_root) / args.run_id
    try:
        paths = write_evidence(output_dir, manifest, report, markdown)
    except EvidenceScrubError as exc:
        sys.stderr.write(f"[T2 stop] evidence scrub failed: {exc}\n")
        return 3

    sys.stdout.write(
        f"T2 harness run '{args.run_id}': real deposit "
        f"{real_deposit_status}; evidence written under {output_dir}\n"
    )
    for name, path in paths.items():
        sys.stdout.write(f"  {name}: {Path(path).name}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
