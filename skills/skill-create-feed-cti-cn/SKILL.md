---
name: skill-create-feed-cti-cn
description: Review one Telegram message link centered on one specified message, fetch about 20 messages before and 20 after, read Chinese-language screenshots and text with native-level semantic judgment, and decide whether the material supports an in-scope CTI feed for Banking/Financial, Securities, or Government cybercrime. Use when the user invokes `$skill-create-feed-cti-cn` with exactly one Telegram message link argument such as `https://t.me/chat/12345`, and Codex must translate the evidence into Vietnamese, produce short bilingual analysis in Vietnamese and English, reject news-only or commentary-only content, and create a complete CTI feed only when both criminal behavior and criminal form are present.
---

# Create Feed CTI CN

## Overview

Use this skill for proactive or advanced threat hunting on Chinese-language Telegram activity.
Treat the task as evidence review around one target message, not as generic summarization.
By default, accepted feeds must be saved as Markdown files under `Output-CTI-Feeds/`.

## Input Contract

Invoke this skill only in this fixed form:

```text
$skill-create-feed-cti-cn <telegram-message-link>
```

Accept exactly one argument after the skill name.
That argument must be a Telegram message link in one of these forms:

- `https://t.me/<chat>/<message_id>`
- `https://t.me/c/<internal_id>/<message_id>`

Treat any extra free-text selector, missing link, non-Telegram URL, or malformed Telegram URL as invalid input.
When the input is invalid, stop immediately and tell the user to use this exact syntax:

```text
$skill-create-feed-cti-cn https://t.me/<chat>/<message_id>
```

Also mention that private-style links such as `https://t.me/c/<internal_id>/<message_id>` are acceptable.
Only after the Telegram link is valid should you use any additional screenshots, image URLs, captions, profile screenshots, or pasted text as supporting evidence.
Treat the specified message as the center of review and gather roughly 20 messages above plus 20 messages below when Telegram context is accessible.

## Execution Boundaries

Do not treat this skill as a repo-orchestration workflow.
Do not inspect the local repository, local `batches/` folders, git status, or storage schema.
Do not search for output folders, dedupe stores, JSON schemas, or prior batch formats.
Do not read unrelated workspace files just to decide where a CTI feed should live.
Only read:

- the Telegram evidence
- the supporting screenshots or pasted text supplied with the task
- this skill's own reference files when needed

If the material is accepted for feed creation, save the feed only to the fixed folder `Output-CTI-Feeds/`.

## Workflow

### 1. Resolve the Telegram evidence

If the input is a public Telegram message link such as `https://t.me/<chat>/<message_id>`, extract the chat handle and message id directly.
If the input is a private-style link such as `https://t.me/c/<internal_id>/<message_id>`, derive the numeric chat id as `-100<internal_id>` when needed.
Use Telegram tools to gather context around the target message.
Use only `get_message_context` with `context_size=20` as the default evidence source.
Do not call `get_chat`, `get_history`, or other broader chat inspection tools for this skill's default review flow.
Do not read messages outside the reviewed target window.
Treat the target window as the only admissible Telegram text evidence unless the user explicitly supplies extra screenshots or pasted text.
If the Telegram link cannot be resolved because the chat is inaccessible, state that limitation clearly and continue with the screenshots or pasted text that are available.
Do not do any repo exploration before or after these Telegram calls.

### 2. Read the material like a native Chinese speaker

Interpret every Chinese string through native semantics, slang, euphemism, underworld phrasing, marketplace wording, shorthand, and mixed Chinese-English expressions.
Do not flatten the task into keyword matching.
Read screenshots structurally. If an image shows chat lines, payment proof, transaction history, an app interface, a fake portal, or account profile metadata, preserve that structure in translation and analysis.
Do not pull extra profile media, avatars, unrelated gallery images, or other off-target visuals unless the user explicitly attached them as task evidence.

### 3. Apply the scope gate before creating a feed

Create a CTI feed only when the evidence shows both:

- a criminal behavior signal
- a criminal form or modality signal

Read [crime-scope.md](./references/crime-scope.md) before making the accept or reject decision.
Reject if the post is only news, commentary, awareness content, policy reporting, breach reporting, or general discussion without an in-scope criminal offer, request, exchange, brokerage, guarantee-market role, or operational crime activity.
Reject if the evidence is only a poster, banner, flyer, scoreboard, results board, or promotional image that does not itself show enough in-scope criminal behavior plus criminal form.

### 4. Translate and analyze first

Before drafting the CTI feed, produce these sections:

1. Full Vietnamese translation of the observed evidence.
2. Short analysis in Vietnamese.
3. Short analysis in English.

For translation:

- Show Chinese on the left and Vietnamese meaning on the right when practical.
- Translate the group name if present.
- Translate the account or handle display name if present.
- Translate every caption, chat line, overlay text, UI string, or payment detail in order.
- If multiple images exist, label them `Ảnh 1`, `Ảnh 2`, and so on.
- Do not emit a flat block of translations without labels.
- Always add clear subheaders so the reader knows what each translation block means.
- Separate at least these cases when they exist:
  - translated identities such as group name or account name
  - translated message excerpts or post excerpts
  - media or image notes where no OCR text was available

For analysis:

- State the likely criminal field of activity.
- State what the poster is trying to sell, buy, exchange, broker, guarantee, or demonstrate.
- State which target organization type or target market is implicated.
- Keep one Vietnamese version and one English version with the same meaning.

### 5. Build the feed only if the scope gate passes

If the material does not satisfy both criminal behavior and criminal form, stop after the translation and bilingual analysis and state that no CTI feed should be created.
If the scope gate passes, build the CTI feed using [feed-output.md](./references/feed-output.md).
Save the accepted CTI feed as a Markdown file in `Output-CTI-Feeds/`.
Use this filename pattern:

```text
yymmdd-actor-name.md
```

Use the local current date for `yymmdd`.
Derive `actor-name` from the strongest observable username in the input evidence, preferably:

1. group or channel username from the Telegram link or chat metadata
2. account username of the posting actor if stronger than the group
3. other stable Telegram handle directly present in the evidence

Normalize the actor name for filenames by using lowercase ASCII where practical and replacing unsafe filename characters with hyphens.
If no username is available, fall back to the strongest observable handle or channel title slug supported by the evidence.
Create the folder if it does not already exist.
After saving, return both the CTI feed content and the saved file path in the response.
At the end of the CTI feed, select 5 representative Telegram message links from the reviewed context as criminal evidence for the actor being profiled.
Choose the 5 links that best support the feed narrative, such as sale offers, broker coordination, guarantee-market behavior, operational demos, victim targeting, or proof-of-service messages.

## Core Rules

- Think like a native Chinese analyst, not a machine translator.
- Prefer evidence-based interpretation over imaginative escalation.
- Do not confuse a criminal sale or brokerage post with a news report about crime.
- Do not infer a target bank, country, or actor name unless the evidence supports it.
- Do not accept alternate invocation formats; require exactly `$skill-create-feed-cti-cn <telegram-message-link>`.
- Do not run `git status`, `rg --files`, inspect `batches/`, or search the workspace for feed schemas.
- Do not read any Telegram messages outside the target context window centered on the input message.
- Do not use unrelated last-message previews, chat-wide history, profile chatter, or off-target media as evidence.
- If the actor identity is unclear, still use the strongest observable handle, username, group, channel, or vendor name.
- Keep Vietnamese and English descriptions aligned in meaning.
- Build the glossary only from raw terms that actually appear in the evidence.
- Do not add glossary terms that are absent from the post, screenshot, caption, or chat context.
- Select exactly one primary market label for the final feed: `Banking/Financial`, `Securities`, or `Government`.
- If multiple markets appear, choose the dominant one first and mention the overlap in the description instead of adding extra market labels.
- End every accepted feed with exactly 5 representative message links when at least 5 in-scope message links are available in the reviewed context.

## Output Discipline

Return the work in this order:

1. Translation section.
2. Bilingual analysis section.
3. Scope decision.
4. Full CTI feed only if accepted.
5. Saved file path when a feed is created.

Keep the final CTI feed concise, defensible, and deduplicated.
Do not append repository workflow notes, storage exploration, or implementation chatter to the final answer.
