---
paths:
  - "transcript.py"
  - "test_transcript.py"
---

# Transcript rules

## Invariants
- The interface is `get_transcript(info, fetch) -> (transcript | None, note)` and `to_txt(transcript, duration)`. Everything else is private. Tests go through these two functions only (ADR 0012), so internals can change without breaking tests.
- Caption problems never raise. Missing, failed, empty or partly broken captions return `(None, note)` or the readable part, so `capture()` always keeps `data.json` (ADR 0010).
- `data.json`'s `transcript` is `{"source": "manual" | "auto", "segments": [{"start", "end", "text"}]}`, or `null`. Other projects read this shape, so changing it is a breaking change.
- Only original English is used (ADR 0004). Creator tracks match `en` or `en-XX` with an uppercase region. A lowercase suffix like `en-ja` is a machine translation. Auto-captions count only under `en-orig`, which yt-dlp adds only for the language YouTube's speech recognition heard; auto `en` without it is machine-translated.

## Gotchas
- **Keep `.srt` parsing tolerant.** A blank caption cue in YouTube's `.srt` leaves a block with no timing line ("blank line, blank line, next cue number"). A strict parser crashed there and lost the run's metadata (ADR 0010).
- **Auto-caption cues overlap.** During continuous speech, each cue's end runs past the next cue's start (rolling captions), so a positive gap between "latest end so far" and the next start only appears at a real pause. Spacing between cue starts is about 2 s and is not a pause signal; using it breaks every line.
- **Speech with no punctuation and no pauses never breaks**, so the `.txt` can get very long lines.
- **Caption URLs in a saved JSON expire.** Backfilling an old video needs a fresh extraction to get new `subtitles` / `automatic_captions`.
