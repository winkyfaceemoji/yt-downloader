# 0004. Transcripts use only original English captions

Status: Accepted (2026-10-13)

## Context
YouTube offers creator-uploaded subtitles, its own speech-recognition captions, and machine translations of either into many languages.

## Decision
Use creator-uploaded English first (`en` or `en-XX`, including human translations on non-English videos). Otherwise use auto-captions only when the speech itself is English (`en-orig`).

Rejected: YouTube's machine-translated English (auto `en` without `en-orig`, or `en-ja`-style translated subtitles). It stacks translation errors on top of speech-recognition errors.

## Consequences
Non-English videos without creator English get `transcript: null`. `data.json` records whether the transcript came from `manual` or `auto` captions.
