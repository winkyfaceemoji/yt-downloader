# 0017. Optional cookies.txt for every yt-dlp call

Status: Accepted (2026-10-14)

## Context
YouTube sometimes demands "Sign in to confirm you're not a bot". Explo handles this with an optional `cookies.txt` passed to yt-dlp (its issue #78). ADR 0009 rejected a retry loop and PO-token plugins as too much machinery.

## Decision
If a `cookies.txt` (Netscape format) exists next to `main.py`, `capture()` passes it as yt-dlp's `cookiefile` to every call (metadata, audio, video). Otherwise nothing changes. The file is git-ignored.

Rejected: a prompt or setting for a cookies path (more questions for a rare need).

## Consequences
Using an account's cookies ties downloads to that account, which is the user's risk to take. The file is a login secret and must never be committed.
