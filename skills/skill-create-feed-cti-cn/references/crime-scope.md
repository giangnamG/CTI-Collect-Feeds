# Crime Scope

Use this file only when deciding whether the evidence qualifies for CTI feed creation.

## Decision Gate

Accept only when all three conditions are true:

1. There is at least one criminal behavior indicator.
2. There is at least one criminal form or modality indicator.
3. The dominant market is one of these three: `Banking/Financial`, `Securities`, `Government`.

If any of the three conditions is missing, reject the feed.

## Criminal Behavior Indicators

Require evidence of one or more of these behaviors:

- Buying
- Selling
- Exchanging
- Brokering or middleman activity
- Guarantee-market or escrow-market activity
- Operational delivery or demonstration of an in-scope criminal service

Notes:

- Mere boasting is not enough unless it clearly functions as proof for a sale, brokerage, or criminal service offering.
- Generic discussion, commentary, or reposting is not enough.

## Criminal Form Indicators

### Banking/Financial

Treat these as in-scope forms when linked to the criminal behavior gate:

- eKYC bypass, face broker, liveness bypass, biometric bypass, deepfake bank identity, relay video, mask, synthetic identity, fake identity documents
- Fake banking app, cloned app, remote app, screen-share fraud workflow
- Banker malware, banking malware, RAT, remote control, screen sharing, account takeover, safe-account fraud, forced self-transfer scams
- Mule accounts, laundering lanes, rented or sold accounts or cards, kits, cash-out, underground banking, OTC or Black U exchange, fake transfer slips
- Bank logs, data packs, credentials
- Insider access or insider tips
- Phishing aimed at banks or financial services

### Securities

Treat these as in-scope forms when linked to the criminal behavior gate:

- Fake broker, black platform, fake analyst or mentor, order-pulling scam
- Fake brokerage app, cloned app, account takeover
- Renting or selling securities accounts, paid rooms, copy trade abuse, signal abuse
- eKYC bypass, face broker, liveness bypass, biometric bypass, fake identity documents
- Price manipulation, pump and dump
- Insider tips or insider abuse
- Malware, RAT, remote control, screen share
- Credentials, logs, data packs
- Phishing aimed at brokers, exchanges, or securities accounts

### Government

Treat these as in-scope forms when linked to the criminal behavior gate:

- Fake public-service portals, fake police or case apps, fake government QR or links, fake state portals
- Impersonation of police, prosecution, courts, officials, or deepfake official voices
- Malware themed around government services or state processes
- Theft or abuse of citizen identity systems, citizen ID, tax identity, state identity
- Fake ID cards, passports, tax documents, eTax workflows
- Sale of citizen data, government logs, data packs, credentials

## Target Geography and Priority

Prioritize content tied to China and Southeast Asia, especially Vietnam.
Still accept other geographies if the activity is clearly connected to Chinese-speaking actors or Chinese Telegram criminal ecosystems.

## Strong Reject Patterns

Reject when the evidence is mainly:

- News
- Journalism
- Current-events reposting
- Arrest reports
- Incident writeups
- Breach reporting without a sale or operational criminal workflow
- Awareness content
- Policy, compliance, or security commentary
- Generic financial chat or investment discussion
- Generic crypto discussion without criminal behavior plus criminal form
- Generic promotional poster or banner without a concrete criminal transaction or operational signal
- Scoreboard, performance board, or result card without direct evidence of an in-scope criminal workflow
- Avatar, cover image, or profile decoration that does not independently establish criminal behavior plus criminal form

## Poster and Image Rule

If an image is only a promotional poster, advertisement card, logo board, slogan board, or results board, reject it unless the image itself clearly provides both:

1. criminal behavior such as selling, buying, brokering, exchange, guarantee-market activity, or operational delivery
2. criminal form tied to Banking/Financial, Securities, or Government cybercrime

Do not say "this may still be evidence" when the poster does not meet both gates.
In that case, the correct outcome is reject or insufficient evidence.

## Ambiguity Rule

When uncertain, prefer a defensible reject over a speculative accept.
