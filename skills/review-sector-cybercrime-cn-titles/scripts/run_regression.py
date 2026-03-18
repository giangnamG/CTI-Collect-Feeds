#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

WORKSPACE_ROOT_ENV = "REVIEW_SECTOR_CYBERCRIME_CN_ROOT"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def workspace_root() -> Path:
    override = os.environ.get(WORKSPACE_ROOT_ENV)
    if override:
        return Path(override).expanduser().resolve()

    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "skills").exists():
            return candidate
    return current


def run_python(script_path: Path, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script_path), *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd),
    )


def require_success(result: subprocess.CompletedProcess[str], *, context: str) -> None:
    if result.returncode != 0:
        raise SystemExit(
            f"{context} failed with exit code {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def list_log_files(log_dir: Path) -> set[Path]:
    if not log_dir.exists():
        return set()
    return {path.resolve() for path in log_dir.glob("*.log")}


def main() -> None:
    scripts_dir = Path(__file__).resolve().parent
    prepare_script = scripts_dir / "prepare_review_folder.py"
    inspect_script = scripts_dir / "show_normalized_batch.py"
    persist_script = scripts_dir / "persist_review_folder.py"

    root = workspace_root()
    log_dir = root / "logs" / "review-cn-sososo-search_logs"
    before_logs = list_log_files(log_dir)

    tmp_root = scripts_dir.parent / "_tmp_tests"
    tmp_root.mkdir(parents=True, exist_ok=True)
    temp_dir = tmp_root / f"review-sector-cybercrime-cn-{uuid.uuid4().hex[:8]}"
    temp_dir.mkdir(parents=True, exist_ok=False)

    batch_token = f"review-sector-cybercrime-cn-{uuid.uuid4().hex[:8]}"
    input_dir = root / "batches" / batch_token
    run_dir = (root / "reviews" / "review-cn-sososo-search" / batch_token).resolve()

    try:
        input_dir.mkdir(parents=True, exist_ok=False)

        write_json(
            input_dir / "0001.json",
            [
                {"title": "工商银行钓鱼登录页", "link": "https://t.me/example/1"},
                {"title": "银行官方维护通知", "link": "https://t.me/example/2"},
                "政务平台仿站源码",
            ],
        )
        write_json(
            input_dir / "0002.json",
            {
                "items": [
                    {"text": "股票交流学习群"},
                    {"name": "税务账号料出售", "url": "https://t.me/example/3"},
                ]
            },
        )
        write_json(input_dir / "notes.json", [{"title": "Ignored because the file name is not numeric"}])

        prepare_result = run_python(prepare_script, "--input-dir", batch_token, cwd=root)
        require_success(prepare_result, context="prepare_review_folder.py")
        manifest = json.loads(prepare_result.stdout)

        if manifest["requested_input"] != batch_token:
            raise SystemExit(f"Expected requested_input to preserve the batch token, got {manifest['requested_input']}")
        if Path(manifest["workspace_root"]).resolve() != root.resolve():
            raise SystemExit(f"Expected workspace_root to resolve to {root}, got {manifest['workspace_root']}")
        if Path(manifest["input_dir"]).resolve() != input_dir.resolve():
            raise SystemExit(f"Expected input_dir to resolve under batches, got {manifest['input_dir']}")
        if manifest["files_total"] != 2:
            raise SystemExit(f"Expected 2 numbered files, got {manifest['files_total']}")
        if manifest["items_total"] != 5:
            raise SystemExit(f"Expected 5 total items, got {manifest['items_total']}")
        if Path(manifest["log_dir"]).resolve() != log_dir.resolve():
            raise SystemExit(f"Unexpected manifest log_dir: {manifest['log_dir']}")
        prepare_log_file = Path(manifest["log_file"]).resolve()
        if not prepare_log_file.exists():
            raise SystemExit(f"Prepare log file was not created: {prepare_log_file}")

        after_prepare_logs = list_log_files(log_dir)
        if prepare_log_file not in after_prepare_logs or len(after_prepare_logs) <= len(before_logs):
            raise SystemExit("Expected a new prepare log file in logs/review-cn-sososo-search_logs")

        manifest_run_dir = Path(manifest["run_dir"]).resolve()
        if manifest_run_dir != run_dir:
            raise SystemExit(f"Unexpected run_dir: {manifest_run_dir} != {run_dir}")

        inspect_result = run_python(
            inspect_script,
            "--manifest",
            str(run_dir / "manifest.json"),
            "--list-files",
            cwd=root,
        )
        require_success(inspect_result, context="show_normalized_batch.py --list-files")
        inspect_summary = json.loads(inspect_result.stdout)
        if inspect_summary["files_total"] != 2:
            raise SystemExit(f"Expected 2 indexed files, got {inspect_summary['files_total']}")

        show_batch_result = run_python(
            inspect_script,
            "--manifest",
            str(run_dir / "manifest.json"),
            "--source-file",
            "0001.json",
            cwd=root,
        )
        require_success(show_batch_result, context="show_normalized_batch.py --source-file")
        shown_batch = json.loads(show_batch_result.stdout)
        if shown_batch["source_file"] != "0001.json":
            raise SystemExit(f"Unexpected normalized batch source_file: {shown_batch['source_file']}")

        drafts_dir = run_dir / "drafts"

        write_json(
            drafts_dir / "0001.review.json",
            {
                "source_file": "0001.json",
                "items": [
                    {
                        "source_file": "0001.json",
                        "item_index": 1,
                        "title": "工商银行钓鱼登录页",
                        "link": "https://t.me/example/1",
                        "decision": "accept",
                        "reason": "标题明确指向银行钓鱼登录场景。",
                        "sector_tags": ["banking"],
                        "crime_signals": ["phishing", "credential-theft"],
                        "priority": "high",
                    },
                    {
                        "source_file": "0001.json",
                        "item_index": 2,
                        "title": "银行官方维护通知",
                        "link": "https://t.me/example/2",
                        "decision": "reject",
                        "reason": "更像正常银行公告，没有明确犯罪含义。",
                        "sector_tags": [],
                        "crime_signals": [],
                        "priority": "low",
                    },
                    {
                        "source_file": "0001.json",
                        "item_index": 3,
                        "title": "政务平台仿站源码",
                        "link": None,
                        "decision": "accept",
                        "reason": "指向仿冒政务平台的钓鱼基础设施。",
                        "sector_tags": ["government"],
                        "crime_signals": ["phishing", "impersonation"],
                        "priority": "high",
                    },
                ],
            },
        )
        write_json(
            drafts_dir / "0002.review.json",
            {
                "source_file": "0002.json",
                "items": [
                    {
                        "source_file": "0002.json",
                        "item_index": 1,
                        "title": "股票交流学习群",
                        "link": None,
                        "decision": "reject",
                        "reason": "只是普通证券交流，没有明确网络犯罪语义。",
                        "sector_tags": [],
                        "crime_signals": [],
                        "priority": "low",
                    },
                    {
                        "source_file": "0002.json",
                        "item_index": 2,
                        "title": "税务账号料出售",
                        "link": "https://t.me/example/3",
                        "decision": "accept",
                        "reason": "直接表达政府税务账号资料出售。",
                        "sector_tags": ["government"],
                        "crime_signals": ["credential-theft", "access-sale"],
                        "priority": "high",
                    },
                ],
            },
        )

        persist_result = run_python(persist_script, "--manifest", str(run_dir / "manifest.json"), cwd=root)
        require_success(persist_result, context="persist_review_folder.py")
        summary = json.loads(persist_result.stdout)

        if summary["accepted_total"] != 3:
            raise SystemExit(f"Expected 3 accepted items, got {summary['accepted_total']}")
        if summary["rejected_total"] != 2:
            raise SystemExit(f"Expected 2 rejected items, got {summary['rejected_total']}")
        if summary["sector_counts"] != {"banking": 1, "government": 2}:
            raise SystemExit(f"Unexpected sector counts: {summary['sector_counts']}")
        if Path(summary["log_dir"]).resolve() != log_dir.resolve():
            raise SystemExit(f"Unexpected summary log_dir: {summary['log_dir']}")
        persist_log_file = Path(summary["log_file"]).resolve()
        if not persist_log_file.exists():
            raise SystemExit(f"Persist log file was not created: {persist_log_file}")
        if persist_log_file == prepare_log_file:
            raise SystemExit("Prepare and persist should use distinct log files.")

        after_persist_logs = list_log_files(log_dir)
        if persist_log_file not in after_persist_logs or len(after_persist_logs) <= len(after_prepare_logs):
            raise SystemExit("Expected a new persist log file in logs/review-cn-sososo-search_logs")

        bad_review_dir = temp_dir / "bad-drafts"
        bad_review_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            bad_review_dir / "0001.review.json",
            {
                "source_file": "0001.json",
                "items": [
                    {
                        "source_file": "0001.json",
                        "item_index": 1,
                        "title": "被篡改的标题",
                        "link": "https://t.me/example/1",
                        "decision": "accept",
                        "reason": "Should fail because the title changed.",
                        "sector_tags": ["banking"],
                        "crime_signals": ["phishing"],
                        "priority": "high",
                    },
                    {
                        "source_file": "0001.json",
                        "item_index": 2,
                        "title": "银行官方维护通知",
                        "link": "https://t.me/example/2",
                        "decision": "reject",
                        "reason": "Still a reject.",
                        "sector_tags": [],
                        "crime_signals": [],
                        "priority": "low",
                    },
                    {
                        "source_file": "0001.json",
                        "item_index": 3,
                        "title": "政务平台仿站源码",
                        "link": None,
                        "decision": "accept",
                        "reason": "Still an accept.",
                        "sector_tags": ["government"],
                        "crime_signals": ["phishing"],
                        "priority": "high",
                    },
                ],
            },
        )
        write_json(bad_review_dir / "0002.review.json", load_json(drafts_dir / "0002.review.json"))

        bad_result = run_python(
            persist_script,
            "--manifest",
            str(run_dir / "manifest.json"),
            "--review-dir",
            str(bad_review_dir),
            cwd=root,
        )
        if bad_result.returncode == 0:
            raise SystemExit("Expected persist_review_folder.py to fail on a mutated title.")

        print(f"Regression checks passed. Artifacts: {temp_dir}")
    finally:
        shutil.rmtree(input_dir, ignore_errors=True)
        shutil.rmtree(run_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
