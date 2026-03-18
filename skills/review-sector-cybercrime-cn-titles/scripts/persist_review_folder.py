#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from review_logging import ReviewLogger

VALID_DECISIONS = {"accept", "reject"}
VALID_PRIORITIES = {"low", "medium", "high"}
WORKSPACE_ROOT_ENV = "REVIEW_SECTOR_CYBERCRIME_CN_ROOT"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require_non_empty_string(value: Any, error_message: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(error_message)
    return value


def validate_string_list(value: Any, *, field_name: str, error_prefix: str) -> list[str]:
    if not isinstance(value, list):
        raise SystemExit(f"{error_prefix} requires a '{field_name}' array.")

    validated: list[str] = []
    for entry_index, entry in enumerate(value, start=1):
        if not isinstance(entry, str) or not entry.strip():
            raise SystemExit(
                f"{error_prefix} has invalid {field_name}[{entry_index}]; expected a non-empty string."
            )
        validated.append(entry)
    return validated


def resolve_manifest_relative_path(manifest_path: Path, relative_path: str) -> Path:
    return (manifest_path.parent / relative_path).resolve()


def workspace_root() -> Path:
    override = os.environ.get(WORKSPACE_ROOT_ENV)
    if override:
        return Path(override).expanduser().resolve()

    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "batches").exists():
            return candidate
    return current


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise SystemExit("Manifest requires a non-empty 'files' array.")

    return {
        "skill": require_non_empty_string(manifest.get("skill"), "Manifest requires a non-empty 'skill'."),
        "input_dir": require_non_empty_string(
            manifest.get("input_dir"), "Manifest requires a non-empty 'input_dir'."
        ),
        "run_dir": require_non_empty_string(manifest.get("run_dir"), "Manifest requires a non-empty 'run_dir'."),
        "files": files,
    }


def normalize_review_item(
    review_item: dict[str, Any],
    expected_item: dict[str, Any],
    *,
    error_prefix: str,
) -> dict[str, Any]:
    if not isinstance(review_item, dict):
        raise SystemExit(f"{error_prefix} must be an object.")

    if review_item.get("source_file") != expected_item["source_file"]:
        raise SystemExit(f"{error_prefix} must preserve 'source_file'.")
    if review_item.get("item_index") != expected_item["item_index"]:
        raise SystemExit(f"{error_prefix} must preserve 'item_index'.")
    if review_item.get("title") != expected_item["title"]:
        raise SystemExit(f"{error_prefix} must preserve 'title'.")
    if review_item.get("link") != expected_item["link"]:
        raise SystemExit(f"{error_prefix} must preserve 'link'.")

    decision = review_item.get("decision")
    priority = review_item.get("priority")
    reason = require_non_empty_string(review_item.get("reason"), f"{error_prefix} requires a non-empty 'reason'.")
    if decision not in VALID_DECISIONS:
        raise SystemExit(f"{error_prefix} has invalid decision: {decision!r}")
    if priority not in VALID_PRIORITIES:
        raise SystemExit(f"{error_prefix} has invalid priority: {priority!r}")

    sector_tags = validate_string_list(review_item.get("sector_tags"), field_name="sector_tags", error_prefix=error_prefix)
    crime_signals = validate_string_list(
        review_item.get("crime_signals"), field_name="crime_signals", error_prefix=error_prefix
    )

    if decision == "accept":
        if not sector_tags:
            raise SystemExit(f"{error_prefix} must include at least one sector tag for accepted items.")
        if not crime_signals:
            raise SystemExit(f"{error_prefix} must include at least one crime signal for accepted items.")
        if priority == "low":
            raise SystemExit(f"{error_prefix} cannot use priority 'low' for accepted items.")
    else:
        if priority != "low":
            raise SystemExit(f"{error_prefix} must use priority 'low' for rejected items.")

    return {
        "source_file": expected_item["source_file"],
        "item_index": expected_item["item_index"],
        "title": expected_item["title"],
        "link": expected_item["link"],
        "decision": decision,
        "reason": reason,
        "sector_tags": sector_tags,
        "crime_signals": crime_signals,
        "priority": priority,
    }


def normalize_review_batch(normalized_batch: dict[str, Any], review_draft: dict[str, Any]) -> dict[str, Any]:
    source_file = require_non_empty_string(
        normalized_batch.get("source_file"), "Normalized batch requires a non-empty 'source_file'."
    )
    expected_items = normalized_batch.get("items")
    if not isinstance(expected_items, list) or not expected_items:
        raise SystemExit(f"Normalized batch {source_file} requires a non-empty 'items' array.")

    if not isinstance(review_draft, dict):
        raise SystemExit(f"Review draft for {source_file} must be a JSON object.")
    if review_draft.get("source_file") != source_file:
        raise SystemExit(f"Review draft for {source_file} must preserve 'source_file'.")

    review_items = review_draft.get("items")
    if not isinstance(review_items, list):
        raise SystemExit(f"Review draft for {source_file} requires an 'items' array.")
    if len(review_items) != len(expected_items):
        raise SystemExit(f"Review draft for {source_file} must contain one review item per input item.")

    normalized_items = [
        normalize_review_item(review_item, expected_item, error_prefix=f"{source_file} item #{index}")
        for index, (expected_item, review_item) in enumerate(
            zip(expected_items, review_items, strict=True),
            start=1,
        )
    ]

    accepted_total = sum(1 for item in normalized_items if item["decision"] == "accept")
    rejected_total = len(normalized_items) - accepted_total

    return {
        "source_file": source_file,
        "items_total": len(normalized_items),
        "accepted_total": accepted_total,
        "rejected_total": rejected_total,
        "items": normalized_items,
    }


def summarize(review_batches: list[dict[str, Any]]) -> dict[str, Any]:
    accepted_items = [item for batch in review_batches for item in batch["items"] if item["decision"] == "accept"]
    rejected_items = [item for batch in review_batches for item in batch["items"] if item["decision"] == "reject"]

    sector_counts: dict[str, int] = {}
    crime_signal_counts: dict[str, int] = {}
    for item in accepted_items:
        for sector in item["sector_tags"]:
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        for signal in item["crime_signals"]:
            crime_signal_counts[signal] = crime_signal_counts.get(signal, 0) + 1

    return {
        "files_reviewed": len(review_batches),
        "items_total": len(accepted_items) + len(rejected_items),
        "accepted_total": len(accepted_items),
        "rejected_total": len(rejected_items),
        "sector_counts": sector_counts,
        "crime_signal_counts": crime_signal_counts,
        "files": [
            {
                "source_file": batch["source_file"],
                "items_total": batch["items_total"],
                "accepted_total": batch["accepted_total"],
                "rejected_total": batch["rejected_total"],
            }
            for batch in review_batches
        ],
    }


def persist_review_directory(
    manifest_path: Path,
    *,
    review_dir: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    root = workspace_root()
    logger = ReviewLogger(root)

    resolved_manifest_path = manifest_path.expanduser().resolve()
    manifest = validate_manifest(load_json(resolved_manifest_path))

    resolved_review_dir = review_dir.expanduser().resolve() if review_dir is not None else None
    resolved_output_dir = output_dir.expanduser().resolve() if output_dir is not None else resolved_manifest_path.parent
    reviewed_dir = resolved_output_dir / "reviewed"
    reviewed_dir.mkdir(parents=True, exist_ok=True)
    logger.step(
        "Initializing review persistence "
        f"| workspace_root={root} | manifest={resolved_manifest_path} | output_dir={resolved_output_dir} "
        f"| log_dir={logger.log_dir} | log_file={logger.log_file}"
    )

    review_batches: list[dict[str, Any]] = []
    accepted_items: list[dict[str, Any]] = []
    rejected_items: list[dict[str, Any]] = []
    total_files = len(manifest["files"])

    for file_index, file_entry in enumerate(manifest["files"], start=1):
        if not isinstance(file_entry, dict):
            logger.error("Manifest file entries must be objects.")
            raise SystemExit("Manifest file entries must be objects.")

        source_file = require_non_empty_string(
            file_entry.get("source_file"), "Manifest file entry requires a non-empty 'source_file'."
        )
        normalized_file = require_non_empty_string(
            file_entry.get("normalized_file"), f"Manifest entry for {source_file} requires 'normalized_file'."
        )
        review_file = require_non_empty_string(
            file_entry.get("review_file"), f"Manifest entry for {source_file} requires 'review_file'."
        )

        normalized_path = resolve_manifest_relative_path(resolved_manifest_path, normalized_file)
        if resolved_review_dir is None:
            review_path = resolve_manifest_relative_path(resolved_manifest_path, review_file)
        else:
            review_path = resolved_review_dir / Path(review_file).name

        if not review_path.exists():
            logger.error(f"Missing review draft | source_file={source_file} | path={review_path}")
            raise SystemExit(f"Missing review draft for {source_file}: {review_path}")

        logger.info(
            f"Validating review draft | file {file_index}/{total_files} | source_file={source_file} "
            f"| normalized_path={normalized_path} | review_path={review_path}"
        )
        normalized_batch = load_json(normalized_path)
        review_draft = load_json(review_path)
        review_batch = normalize_review_batch(normalized_batch, review_draft)
        review_batches.append(review_batch)

        reviewed_path = reviewed_dir / f"{Path(source_file).stem}.reviewed.json"
        write_json(reviewed_path, review_batch)
        logger.info(
            f"Persisted reviewed batch | source_file={source_file} | items_total={review_batch['items_total']} "
            f"| accepted_total={review_batch['accepted_total']} | rejected_total={review_batch['rejected_total']} "
            f"| path={reviewed_path}"
        )

        for item in review_batch["items"]:
            if item["decision"] == "accept":
                accepted_items.append(item)
            else:
                rejected_items.append(item)

    summary = summarize(review_batches)
    summary["log_dir"] = str(logger.log_dir)
    summary["log_file"] = str(logger.log_file)
    write_json(resolved_output_dir / "accepted_candidates.json", accepted_items)
    write_json(resolved_output_dir / "rejected_candidates.json", rejected_items)
    write_json(resolved_output_dir / "summary.json", summary)
    logger.step(
        f"Persistence completed | files_total={summary['files_reviewed']} | items_total={summary['items_total']} "
        f"| accepted_total={summary['accepted_total']} | rejected_total={summary['rejected_total']}"
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate review drafts for a prepared folder run and persist review artifacts."
    )
    parser.add_argument("--manifest", required=True, help="Path to manifest.json from prepare_review_folder.py.")
    parser.add_argument(
        "--review-dir",
        help="Optional directory containing review drafts. Defaults to the manifest's drafts/ paths.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional output directory. Defaults to the manifest directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = persist_review_directory(
        Path(args.manifest),
        review_dir=Path(args.review_dir) if args.review_dir else None,
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
