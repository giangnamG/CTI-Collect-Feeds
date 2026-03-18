#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from review_logging import ReviewLogger

NUMBERED_JSON_PATTERN = re.compile(r"^\d{4,}\.json$")
ROOT_LIST_KEYS = ("items", "results", "data", "titles")
TITLE_KEYS = ("title", "name", "text", "label")
LINK_KEYS = ("link", "url", "href")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def optional_non_empty_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped if stripped else None


def first_non_empty_string(mapping: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = optional_non_empty_string(mapping.get(key))
        if value is not None:
            return value
    return None


def discover_numbered_json_files(input_dir: Path) -> list[Path]:
    discovered = [
        path
        for path in input_dir.iterdir()
        if path.is_file() and NUMBERED_JSON_PATTERN.fullmatch(path.name)
    ]
    return sorted(discovered, key=lambda path: (len(path.stem), int(path.stem), path.name))


def extract_root_items(payload: Any, *, source_file: str) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ROOT_LIST_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                return value
    raise SystemExit(
        f"{source_file} must contain a top-level array or an object with one of: "
        f"{', '.join(ROOT_LIST_KEYS)}."
    )


def normalize_candidate(raw_item: Any, *, source_file: str, item_index: int) -> dict[str, Any]:
    if isinstance(raw_item, str):
        title = optional_non_empty_string(raw_item)
        if title is None:
            raise SystemExit(f"{source_file} item #{item_index} contains an empty title string.")
        link = None
    elif isinstance(raw_item, dict):
        title = first_non_empty_string(raw_item, TITLE_KEYS)
        if title is None:
            raise SystemExit(
                f"{source_file} item #{item_index} must provide one of: {', '.join(TITLE_KEYS)}."
            )
        link = first_non_empty_string(raw_item, LINK_KEYS)
    else:
        raise SystemExit(f"{source_file} item #{item_index} must be a string or object.")

    return {
        "source_file": source_file,
        "item_index": item_index,
        "title": title,
        "link": link,
    }


def normalize_input_file(input_path: Path) -> dict[str, Any]:
    payload = load_json(input_path)
    raw_items = extract_root_items(payload, source_file=input_path.name)
    if not raw_items:
        raise SystemExit(f"{input_path.name} must contain at least one candidate item.")

    normalized_items = [
        normalize_candidate(raw_item, source_file=input_path.name, item_index=index)
        for index, raw_item in enumerate(raw_items, start=1)
    ]
    return {
        "source_file": input_path.name,
        "items_total": len(normalized_items),
        "items": normalized_items,
    }


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_run_dir(input_dir: Path) -> Path:
    return workspace_root() / "reviews" / "review-cn-sososo-search" / input_dir.name


def prepare_review_directory(input_dir: Path, output_dir: Path | None = None) -> dict[str, Any]:
    root = workspace_root()
    logger = ReviewLogger(root)

    resolved_input_dir = input_dir.expanduser().resolve()
    resolved_output_dir = output_dir.expanduser().resolve() if output_dir is not None else default_run_dir(resolved_input_dir)
    logger.step(
        "Initializing review folder preparation "
        f"| skill=review-sector-cybercrime-cn-titles | input_dir={resolved_input_dir} "
        f"| output_dir={resolved_output_dir} | log_dir={logger.log_dir} | log_file={logger.log_file}"
    )

    if not resolved_input_dir.exists() or not resolved_input_dir.is_dir():
        logger.error(f"Input directory does not exist or is not a directory | input_dir={resolved_input_dir}")
        raise SystemExit(f"Input directory does not exist or is not a directory: {resolved_input_dir}")

    numbered_files = discover_numbered_json_files(resolved_input_dir)
    if not numbered_files:
        logger.error(f"No numbered JSON files discovered | input_dir={resolved_input_dir}")
        raise SystemExit(
            f"No numbered JSON files like 0001.json were found in {resolved_input_dir}"
        )

    logger.step(
        f"Discovered numbered input files | files_total={len(numbered_files)} | input_dir={resolved_input_dir}"
    )
    (resolved_output_dir / "normalized").mkdir(parents=True, exist_ok=True)
    (resolved_output_dir / "drafts").mkdir(parents=True, exist_ok=True)
    (resolved_output_dir / "reviewed").mkdir(parents=True, exist_ok=True)

    manifest_files: list[dict[str, Any]] = []
    items_total = 0

    for file_index, input_path in enumerate(numbered_files, start=1):
        normalized_batch = normalize_input_file(input_path)
        items_total += normalized_batch["items_total"]
        normalized_rel = Path("normalized") / f"{input_path.stem}.input.json"
        review_rel = Path("drafts") / f"{input_path.stem}.review.json"
        write_json(resolved_output_dir / normalized_rel, normalized_batch)
        manifest_files.append(
            {
                "source_file": input_path.name,
                "input_file": input_path.name,
                "items_total": normalized_batch["items_total"],
                "normalized_file": normalized_rel.as_posix(),
                "review_file": review_rel.as_posix(),
            }
        )
        logger.info(
            f"Prepared normalized input | file {file_index}/{len(numbered_files)} | source_file={input_path.name} "
            f"| items_total={normalized_batch['items_total']} | path={resolved_output_dir / normalized_rel}"
        )

    manifest = {
        "skill": "review-sector-cybercrime-cn-titles",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "input_dir": str(resolved_input_dir),
        "run_dir": str(resolved_output_dir),
        "log_dir": str(logger.log_dir),
        "log_file": str(logger.log_file),
        "files_total": len(manifest_files),
        "items_total": items_total,
        "files": manifest_files,
    }
    write_json(resolved_output_dir / "manifest.json", manifest)
    logger.step(
        f"Preparation completed | files_total={len(manifest_files)} | items_total={items_total} "
        f"| manifest={resolved_output_dir / 'manifest.json'}"
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover numbered JSON files and prepare a review run directory."
    )
    parser.add_argument("--input-dir", required=True, help="Folder containing files such as 0001.json.")
    parser.add_argument(
        "--output-dir",
        help="Optional run directory. Defaults to reviews/review-cn-sososo-search/<input-folder-name>.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = prepare_review_directory(
        Path(args.input_dir),
        Path(args.output_dir) if args.output_dir else None,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
