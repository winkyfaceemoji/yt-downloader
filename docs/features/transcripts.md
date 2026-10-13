# English transcripts

Every run saves the video's English transcript (when one qualifies) alongside the
metadata. `transcript.py` owns it, behind a two-function interface; it's tested only
through that interface in `test_transcript.py`.

```python
get_transcript(info, fetch) -> (transcript | None, note)
to_txt(transcript, duration) -> str
```

- `info` is yt-dlp's info dict. `fetch(url) -> str` downloads a caption file: `capture.py`
  passes yt-dlp's `urlopen`, and tests pass a stand-in. That's the module's seam.
- **Caption problems never raise.** A missing, failed or empty caption file returns
  `(None, note)`, so a run always keeps its metadata. The note says why, e.g.
  `no English captions`, `caption download failed (…)`, `caption file was empty`, or
  `86 caption pieces from auto captions`.

## Which captions are used

yt-dlp lists creator-uploaded tracks in `info['subtitles']` and YouTube's auto-captions
in `info['automatic_captions']`. Candidates, in order:

1. Creator-uploaded English: keys matching `en` or `en-XX` (uppercase region, e.g.
   `en-US`); plain `en` sorts first. `source = "manual"`.
2. Auto-captions only under `en-orig`, which yt-dlp adds only for the language YouTube's
   speech recognition heard. `source = "auto"`.

The first candidate that offers an `.srt` download wins. Never used: auto `en` without
`en-orig` (machine-translated from another language) and lowercase-suffixed keys like
`en-ja` (machine translations of creator subtitles). See DECISIONS.md.

## Data shape (`data.json`)

```json
"transcript": {
  "source": "auto",
  "segments": [{"start": 17.52, "end": 21.52, "text": "All my"}, ...]
}
```

- `segments` are the original `.srt` cues, with times in seconds (millisecond precision).
- `null` when nothing qualifies, when the caption download fails, or when the file has
  no cues.

## Readable `.txt` (`to_txt`)

```
[00:17] All my life I been this way.
[00:24] My mom and my daddy, upon me they prayed.
```

- Pieces are joined word by word. A line ends after a word with `.`, `!`, `?` or `…`
  (ignoring trailing quotes/brackets), including mid-piece, except title abbreviations
  in `ABBREVIATIONS` (`Mr.`, `Dr.`, `e.g.`, …).
- A line also ends before a piece starting more than `PAUSE_SECONDS` (1.5 s) after the
  latest end time so far.
- A line's timestamp is the start of the piece its first word came from.
- `[mm:ss]` normally; `[h:mm:ss]` when the video's duration (or, if missing, the last
  line's start) is an hour or more.

## Gotchas

- **The `.srt` parser is deliberately tolerant.** A cue is any block with a
  `start --> end` line; blocks without one, or with a garbled time, are skipped. A blank
  caption in YouTube's `.srt` leaves exactly such a block (blank line, blank line, then
  the next cue number). A strict parser crashed there and lost the run's metadata, so
  don't "simplify" this back.
- **Auto-caption cues overlap.** During continuous speech each cue's end runs past the
  next cue's start (rolling captions), so "next start − previous end" is negative, and a
  positive gap only appears at a real pause. That's why the pause rule uses the latest
  end seen rather than cue-to-cue start spacing (~2 s, which would break every line).
- **Unpunctuated, pause-free speech never breaks**, so such a transcript can produce
  very long lines.
- **Caption URLs in a saved JSON expire.** To backfill an old video, re-extract it for
  fresh `subtitles` / `automatic_captions`.
