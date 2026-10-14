# 0005. Transcript stored as JSON segments plus a sentence-per-line .txt

Status: Accepted (2026-10-13)

## Context
Transcripts serve code and AI tools, which need timings, and people, who need readable text. Raw caption pieces are only 2–5 words long and overlap in time.

## Decision
Keep the original cues, with start and end seconds, in `data.json`'s `transcript` field. Also write `transcript.txt` with one timestamped line per sentence or pause.

Rejected: saving `.srt`/`.vtt` files (cue numbers and timing noise, and YouTube's `.vtt` repeats rolling lines) and `.json3` (hard to read).

## Consequences
The transcript is stored twice, about 10 KB per video. The line-breaking rules (sentence punctuation, 1.5 s pauses, abbreviations) live in `transcript.py`.
