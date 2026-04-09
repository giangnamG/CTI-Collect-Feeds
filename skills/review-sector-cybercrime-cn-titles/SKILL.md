---
name: review-sector-cybercrime-cn-titles
description: Review one folder that contains numbered JSON files such as `0001.json` through `xxxx.json` and decide, title by title, which Chinese-language entries semantically indicate cybercrime activity targeting banking, securities, financial, or government sectors. Use when the user invokes `$review-sector-cybercrime-cn-titles` with a batch folder token like `260318-233535` or an explicit folder path and wants the whole review flow to run automatically without extra prompting. Trigger only for folder-based Chinese JSON title review; do not use this skill for Telegram collection, regex-only filtering, multilingual generic triage, or full CTI extraction.
---

# Review Sector Cybercrime CN Titles

## Overview

Act as a folder-level semantic review layer for numbered JSON files whose titles are primarily in Chinese.
Codex is the reviewer. The bundled scripts only discover files, normalize inputs, inspect prepared batches, validate the review contract, persist artifacts, and log execution details.

## Invocation Contract

If the user invokes `$review-sector-cybercrime-cn-titles` and provides one value, treat it as the input selector immediately.
If the value is a bare token such as `260318-233535`, resolve it by default to `<workspace>\batches\260318-233535`.
If the value is an existing absolute or relative folder path, use that folder directly.
Do not ask follow-up questions if the resolved folder exists and contains numbered JSON files.
Ask only when the resolved folder does not exist, the files are unreadable, or the JSON shape is irrecoverably invalid.

## Workspace Root

The artifact root is the active project workspace, not the installed skill directory.
By default the scripts walk upward from the current working directory until they find a folder that contains `batches/`.
If needed, override the workspace root with the environment variable `REVIEW_SECTOR_CYBERCRIME_CN_ROOT`.

## Language Scope

Assume the titles are Chinese by default.
Review them through Chinese semantics, Chinese slang, abbreviations, euphemisms, mixed Chinese-English wording, and criminal marketplace phrasing.
Do not downgrade a title just because it uses shorthand, homophones, transliterated jargon, or partial English fragments inside otherwise Chinese text.
Write `reason` in concise Vietnamese.
Add a concise Vietnamese rendering in `title_vi` for every review item.

## Hard Boundaries

- Never decide relevance with regex, keyword allowlists, or script-side scoring.
- Never treat `references/semantic-signals.md` as a rule engine.
- Never modify the source JSON files in place.
- Never skip files that match the numbered-file contract.
- Never reorder items inside a file.
- Never rewrite `title`, `link`, `source_file`, or `item_index` values in review outputs.
- Never translate or paraphrase the preserved source `title`; put the Vietnamese rendering only in `title_vi`.
- Use the helper scripts only for discovery, normalization, prepared-batch inspection, validation, artifact persistence, and workflow logging.
- Never use ad-hoc `python -c`, shell one-liners, or quoting-sensitive inline scripts to inspect normalized inputs when `show_normalized_batch.py` can read them directly.

## Accepted Input Shapes

Discover only files named like `0001.json`, `0002.json`, or `123456.json` in the target folder.
Ignore non-numbered JSON files.

Each numbered file may contain:

- a top-level JSON array of candidates
- a top-level object with one of these list fields: `items`, `results`, `data`, `titles`

Each candidate may be:

- a string, treated as the `title`
- an object with one of `title`, `name`, `text`, or `label`

Optional link fields:

- `link`
- `url`
- `href`

## Workflow

### 1. Prepare a review run

Run:

```powershell
python scripts/prepare_review_folder.py --input-dir "260318-233535"
```

You may also pass an explicit folder path, but a bare token is resolved under `<workspace>\batches\<token>` by default.

If `--output-dir` is omitted, the script creates:

- `reviews\review-cn-sososo-search\<input-folder-name>\manifest.json`
- normalized input files under `normalized/`
- empty working folders such as `drafts/` and `reviewed/`

The manifest is the system of record for the run. When no custom output path is provided, the whole review result is stored under `reviews\review-cn-sososo-search\<input-folder-name>`.
The workflow also writes execution logs to `logs\review-cn-sososo-search_logs\`.

### 2. Inspect normalized files safely

Read `manifest.json`.
List the prepared files with:

```powershell
python scripts/show_normalized_batch.py --manifest "<run-dir>\manifest.json" --list-files
```

Then inspect each normalized file with:

```powershell
python scripts/show_normalized_batch.py --manifest "<run-dir>\manifest.json" --source-file "0001.json"
```

Use the helper script instead of ad-hoc shell snippets so the review flow stays stable on PowerShell.

### 3. Review each normalized file semantically

Review every normalized input file listed in `manifest.files`.
Make decisions from Chinese meaning, intent, implied criminal workflow, victim sector, and monetization pattern.
Prioritize titles that indicate criminal trading, brokering, exchanging, facilitating, hacking, phishing, compromise, access sales, stolen data, fraud infrastructure, or adjacent monetized cybercrime operations.
Treat news headlines, official bulletins, general incident reporting, commentary, and educational or observational posts as rejects unless the title itself is advertising or enabling a concrete criminal service, commodity, or operation.
Do not reduce the task to literal word matching.

For each normalized input file, create the matching draft file under `drafts/` with this shape:

```json
{
  "source_file": "0001.json",
  "items": [
    {
      "source_file": "0001.json",
      "item_index": 1,
      "title": "工商银行钓鱼登录页",
      "title_vi": "Trang đăng nhập giả mạo của Ngân hàng Công Thương",
      "link": "https://t.me/example/1",
      "decision": "accept",
      "reason": "Tiêu đề cho thấy đây là trang đăng nhập giả mạo để lừa lấy thông tin truy cập ngân hàng.",
      "sector_tags": ["banking"],
      "crime_signals": ["phishing", "credential-theft"],
      "priority": "high"
    }
  ]
}
```

Rules:

- Emit one review item for every normalized input item.
- Preserve the exact order from the normalized file.
- Keep `title`, `link`, `source_file`, and `item_index` identical to the normalized input.
- Always include `title_vi`, `decision`, `reason`, `sector_tags`, `crime_signals`, and `priority`.
- Use empty arrays for `sector_tags` and `crime_signals` only when the item is rejected.
- Use `priority = low` for rejects.
- Use `priority = medium` or `high` for accepts.
- Write `title_vi` and `reason` in Vietnamese.

### 4. Persist the reviewed outputs

Run:

```powershell
python scripts/persist_review_folder.py --manifest "<run-dir>\manifest.json"
```

The persistence script validates the review drafts and writes:

- `reviewed/<file>.reviewed.json`
- `accepted_candidates.json`
- `rejected_candidates.json`
- `summary.json`

The script does not decide `accept` or `reject`.
It only locks the contract, aggregates artifacts, and logs progress.

### 5. Run regression checks after script changes

Run:

```powershell
python scripts/run_regression.py
```

Use this whenever `prepare_review_folder.py`, `show_normalized_batch.py`, `persist_review_folder.py`, or `review_logging.py` changes.

## Semantic Decision Guidance

- Accept titles that clearly advertise or strongly imply Chinese-language phishing, credential theft, account takeover, impersonation, malware delivery, illicit access sales, fraud operations, laundering flows, fake investment platforms, stolen-data trading, brokered transactions, exchange services for illicit assets, or similar cybercrime behavior.
- Accept only when the victim or abused ecosystem is credibly tied to banking, securities, broader financial infrastructure, or government services.
- Reject generic finance chatter, investment education, ordinary broker communities, official notices, policy news, straight news headlines, breach reporting, market commentary, or sector mentions without a defensible cybercrime implication.
- Reject titles that merely report an incident or discuss a topic, even if the incident involves hacking, unless the title itself is offering, requesting, exchanging, brokering, or operationalizing cybercrime activity.
- Favor a defensible reject over an imaginative accept when the title is ambiguous.
- Keep the reason short, concrete, evidence-based, and in Vietnamese.
- Read `references/semantic-signals.md` only as optional recall support.

## Stored Artifacts

Each run directory contains:

- `manifest.json`
- `normalized/*.input.json`
- `drafts/*.review.json`
- `reviewed/*.reviewed.json`
- `accepted_candidates.json`
- `rejected_candidates.json`
- `summary.json`
- logs under `logs\review-cn-sososo-search_logs\`

Return the artifact paths, summary counts, and relevant log file paths once the run is complete.
