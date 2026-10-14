# 0010. Reverted: strict .srt parsing

Status: Accepted (2026-10-13)

## Context
A code review removed `parse_srt`'s malformed-block guard as "handling for an impossible case".

## Decision
Reverted. The case isn't impossible: a blank caption cue leaves a block with no timing line, and an empty file has no blocks at all. The resulting `IndexError`/`ValueError` escaped the caption-error handling, so `data.json` was never written. The parser now skips blocks without a valid timing line, and `get_transcript` never raises for caption problems.

## Consequences
A partly broken caption file keeps its readable cues. Don't remove the tolerance to make the parser look simpler.
