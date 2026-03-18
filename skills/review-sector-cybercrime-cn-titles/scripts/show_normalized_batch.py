#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def require_string(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"Manifest requires a non-empty '{field_name}'.")
    return value


def resolve_manifest_relative_path(manifest_path: Path, relative_path: str) -> Path:
    return (manifest_path.parent / relative_path).resolve()


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise SystemExit("Manifest must be a JSON object.")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise SystemExit("Manifest requires a non-empty 'files' array.")
    manifest["files"] = files
    return manifest


def list_files(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for file_entry in manifest["files"]:
        if not isinstance(file_entry, dict):
            raise SystemExit("Manifest file entries must be objects.")
        files.append(
            {
                "source_file": require_string(file_entry.get("source_file"), field_name="source_file"),
                "items_total": file_entry.get("items_total"),
                "normalized_file": require_string(file_entry.get("normalized_file"), field_name="normalized_file"),
                "review_file": require_string(file_entry.get("review_file"), field_name="review_file"),
            }
        )
    return files


def print_file_index(manifest: dict[str, Any]) -> None:
    files = list_files(manifest)
    summary = {
        "run_dir": manifest.get("run_dir"),
        "files_total": len(files),
        "items_total": manifest.get("items_total"),
        "files": [
            {
                "source_file": file_entry["source_file"],
                "items_total": file_entry["items_total"],
            }
            for file_entry in files
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def print_normalized_batch(manifest_path: Path, manifest: dict[str, Any], source_file: str) -> None:
    files = list_files(manifest)
    matches = [file_entry for file_entry in files if file_entry["source_file"] == source_file]
    if not matches:
        available = ", ".join(file_entry["source_file"] for file_entry in files)
        raise SystemExit(f"No manifest entry found for {source_file!r}. Available files: {available}")

    file_entry = matches[0]
    normalized_path = resolve_manifest_relative_path(manifest_path, file_entry["normalized_file"])
    payload = load_json(normalized_path)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect prepared normalized batches without ad-hoc shell one-liners."
    )
    parser.add_argument("--manifest", required=True, help="Path to manifest.json from prepare_review_folder.py.")
    parser.add_argument("--list-files", action="store_true", help="Print the file index from the manifest.")
    parser.add_argument("--source-file", help="Print one normalized batch such as 0001.json.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.list_files and not args.source_file:
        raise SystemExit("Use --list-files or --source-file.")

    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest = load_manifest(manifest_path)

    if args.list_files:
        print_file_index(manifest)
    else:
        print_normalized_batch(manifest_path, manifest, args.source_file)


if __name__ == "__main__":
    main()
