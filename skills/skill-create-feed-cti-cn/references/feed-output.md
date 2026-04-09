# Feed Output

Use this file when the scope gate passes and a CTI feed must be produced.
This file defines both the feed format and the default save target.
Accepted feeds must be saved under `Output-CTI-Feeds/`.

## Required Output Order

### 1. Translation

Include:

- Group name translation if present
- Account or handle display name translation if present
- Caption or post translation in order
- Chat-context translation in order
- Video or image notes from files staged inside the local conversation snapshot when such media belongs to the approved reviewed window
- Structured translation for screenshots that show payment proof, app UI, profile cards, or transaction history

Use explicit subheaders so the translation section is readable.
Do not output one long unlabeled block of translated lines.
Use these subheaders when applicable:

- `### Tên nhóm / kênh / account`
- `### Nội dung dịch từ message context`
- `### Nội dung ảnh / media`
- `### Ghi chú media không có OCR`

For `Nội dung dịch từ message context`, format each entry so the reader can tell it is a translated evidence excerpt, for example:

```markdown
- 原文: 港美股出货
  Dịch nghĩa: Xuất hàng cổ phiếu Mỹ/Hong Kong.
```

For media that appears in the reviewed context but does not expose OCR text, do not leave the note floating inline with other translations.
Place it under `### Ghi chú media không có OCR`.

### 2. Analysis

Produce two aligned versions:

- Vietnamese analysis
- English analysis

Cover:

- What criminal field the group or post most likely operates in
- What the actor is selling, buying, exchanging, brokering, or demonstrating
- Which organization type or target market is implicated

### 3. Scope Decision

State one of:

- `Tạo Feed CTI`
- `Bỏ qua, không tạo Feed CTI`

Briefly justify the decision against the behavior and form gate.

### 4. CTI Feed

When accepted, emit a complete feed with this structure directly in the response:

```markdown
**Platform / Market / Country**

[Telegram] | [Banking/Financial] | [Việt Nam]

**Threat actor name**

Group: https://t.me/example_group

**Description (VI)**

2-5 câu, chỉ tổng hợp các hoạt động thực sự xuất hiện trong input.

**Description (EN)**

2-5 sentences with the same meaning as the Vietnamese version.

**Screenshot Evidence**

- Ảnh 1 - (link ảnh hoặc URL tương ứng) - mô tả ngắn bằng tiếng Việt về bằng chứng trong ảnh.
- Ảnh 2 - (link ảnh hoặc URL tương ứng) - mô tả ngắn bằng tiếng Việt về bằng chứng trong ảnh.

**Glossary**

- raw term: diễn giải ngắn bằng tiếng Việt
- raw term: diễn giải ngắn bằng tiếng Việt

**Links / IOC / Dedup**

- Message link:
- Group/channel/account link:
- Other URLs:

**Representative Evidence Messages**

- 1. <message link> - short Vietnamese reason why this message is key evidence
- 2. <message link> - short Vietnamese reason why this message is key evidence
- 3. <message link> - short Vietnamese reason why this message is key evidence
- 4. <message link> - short Vietnamese reason why this message is key evidence
- 5. <message link> - short Vietnamese reason why this message is key evidence
```

### 5. Save Location

Save the feed as:

```text
Output-CTI-Feeds/yymmdd-actor-name.md
```

Use the strongest observable username from the evidence as `actor-name` whenever available.
Prefer the group or channel username from the Telegram link or chat metadata.
If the group username is unavailable, use the strongest observable actor username or handle from the evidence.

## IOC Definition

For this skill, treat IOC as any observable identifier that appears directly in the evidence, including:

- usernames
- phone numbers
- wallet addresses
- bank account numbers
- residential addresses or stated physical addresses
- websites or domains
- other Telegram accounts, groups, channels, or handles

Only list IOCs that are actually present in the observed Telegram context, screenshots, captions, or pasted text.
Do not invent or normalize an IOC beyond what the evidence supports.
If a value is partially masked in the evidence, preserve that masking rather than guessing the hidden portion.

## Feed Field Rules

### Threat actor

Use the strongest observable identity from the evidence:

- actor name
- alias
- username
- group name
- channel name
- vendor name

If a personal identity is unclear, a handle or group is still acceptable.

### Description

Keep both language versions aligned.
Include:

- what the actor is doing
- what they are selling or buying
- what target market they affect
- what risk signal matters

Do not add unsupported campaign claims or victim claims.

### Screenshot Evidence

List each screenshot separately.
Tie each line to a concrete message link, image reference, or local snapshot media path when available.
Describe only what the image actually evidences.

### Glossary

Only include raw terms, slang, or native wording that appear in the observed evidence.
Do not invent glossary entries.

### Market

Choose exactly one:

- `Banking/Financial`
- `Securities`
- `Government`

### Country

Record the most defensible geography:

- target country
- actor country
- operational country

If geography is unclear, say so explicitly instead of guessing.

### Links / IOC / Dedup

Use this section to collect both source links and extracted IOCs from the evidence.
At minimum, include the message link and any directly observable Telegram entity link when available.
Also include any IOC that matches the IOC definition above.
Keep the raw observable value.
If the same IOC appears multiple times, deduplicate it instead of repeating it.

### Representative Evidence Messages

This section must appear at the very end of every accepted CTI feed.
List exactly 5 Telegram message links when 5 or more relevant message links are available from the reviewed context.
Choose the strongest 5 links that demonstrate criminal behavior, criminal form, actor identity, target discussion, transaction coordination, or delivery proof.
For each link, add one short Vietnamese explanation describing why it is evidentiary.
If fewer than 5 valid message links are available, list all available message links and explicitly state that the reviewed context did not contain enough message links to reach 5.

## Non-Goals

Do not:

- inspect repo storage layout
- search for batch JSON formats
- infer a persistence schema
- mention git cleanliness or workspace dirtiness

Those actions are outside the default scope of this skill except for saving the accepted feed to the fixed location `Output-CTI-Feeds/`.
