# 0014. No Artist/Album library folders

Status: Accepted (2026-10-14)

## Context
Explo files music as `Artist/Album/File`. Here, one folder per video holds the data, transcript and media (ADR 0006), and many downloads aren't music at all.

## Decision
Keep only the per-video folders. The music player sorts by the embedded tags.

Rejected: replacing per-video folders with `Artist/Album/` (breaks ADR 0006 and 0007, separates audio from its data, and has nowhere for non-music), and an extra hard-linked library copy in `Music/Artist/Album/` (two places to look; the user didn't want it).

## Consequences
Library-style browsing relies on the player reading tags, which the user's player does. Revisit only together with ADR 0006.
