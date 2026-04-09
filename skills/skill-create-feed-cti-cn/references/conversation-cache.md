# Conversation Cache

Use this file when acquiring and staging the reviewed Telegram evidence locally before analysis.

## Purpose

Create a local temp snapshot so the review can proceed from a stable evidence folder instead of repeatedly reading the live chat.
Treat this folder as a disposable local working cache for the current review.

## Folder Pattern

Save the reviewed conversation under:

```text
conversation/<threat_actor>/
```

Where `threat_actor` is derived from the strongest observable username or handle from the input:

1. group or channel username from the input link
2. posting actor username if stronger and directly supported by the evidence
3. other stable Telegram handle directly present in the reviewed window

Normalize the folder name for filesystem safety.
If the input is a group or channel link, prefer that chat username for `threat_actor`.

## Required Contents

At minimum, create:

```text
conversation/<threat_actor>/manifest.json
conversation/<threat_actor>/messages/
conversation/<threat_actor>/media/
```

Recommended message files:

- `messages/<message_id>.md` for human-readable review
- and/or `messages/<message_id>.json` for structured fields

Use `media/` for downloaded images and video files that belong to messages inside the reviewed set.
Name media files so the source message id is still visible, for example `media/<message_id>-<original_name>`.

## Acquisition Rules

### Message-link input

- Anchor on the supplied target message.
- Expand to roughly 100 surrounding messages.
- Preserve the target message id in the snapshot metadata.
- Trim the final reviewed set to at most 100 messages.
- Prefer a balanced window around the target message when the tool can provide both earlier and later messages.

### Group/channel-link input

- Anchor on the newest available message in that target chat.
- Include that newest message plus up to 100 earlier messages above it.
- Do not read unrelated chats or profile previews.
- Use only target-chat message listing calls such as `list_messages(chat_id=<target>, limit=101)`.

## Manifest Fields

Include at least:

- `input_link`
- `input_type` as `message_link` or `chat_link`
- `chat_id`
- `anchor_message_id`
- `messages_total`
- `message_ids`
- `downloaded_media_files`
- `snapshot_dir`
- `messages_dir`
- `media_dir`
- `source_message_links`

## Review Rule

Once the snapshot is created, use the files under `conversation/<threat_actor>/` as the primary evidence base for translation, analysis, IOC extraction, and feed creation.
Do not continue broad Telegram exploration beyond the approved reviewed window unless the user explicitly expands scope.
If a reviewed message contains downloadable image or video media, download it before analysis whenever access is available.
