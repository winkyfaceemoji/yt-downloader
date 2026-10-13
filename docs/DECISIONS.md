# Decisions

Append-only log of the "why" that lives in no other file: rejected alternatives,
reverted experiments, and cross-cutting choices. Newest first. Read this before
editing; don't undo an entry without raising it first.

## 2026-10-13 — Pin yt-dlp 2026.08.19 to cut media-download 403s
- On 2026.07.04, audio/video downloads failed with `HTTP 403` 9/9 times; on 2026.08.19 about half succeed. Failing and passing runs used the same client, format and server, so the refusal is YouTube-side and per-request.
- Rejected: a retry loop on 403 and a PO-token provider plugin, to keep the tool simple. Re-running usually works.
- Files: `requirements.txt`, README Notes.

## 2026-10-13 — Audio prefers `.m4a` and embeds tags + cover art
- `bestaudio[ext=m4a]/bestaudio` with `FFmpegMetadata` + `EmbedThumbnail`, so the files work in ordinary music players and show a title and artist.
- Rejected: native `.webm`/Opus only (many players and Apple Music can't play it) and converting to `.mp3` (lossy re-encode of an already-lossy stream).
- Consequence: ffmpeg is now required for audio as well as video.
- Files: `main.py` (`download_audio_only`).

## 2026-10-13 — Per-video folders under `Downloads/`, anchored to `main.py`
- Output moved from per-type `Data/`, `Audio/`, `Video/` folders (relative to the working directory) to `Downloads/<title> [<id>]/` next to `main.py`. The data is meant to be reused in other projects, so everything for a video sits in one place.
- Rejected: one flat shared folder (long names, files grouped only by sort order) and keeping per-type folders (one video spread over four places).
- The video id in the folder name keeps it unique. Re-runs overwrite everything, and the JSON's `epoch` records the fetch time instead of a date in the name.
- Files: `main.py`, `.gitignore`.

## 2026-10-13 — Fixed data file names, titled media file names
- `data.json` / `transcript.txt` are fixed so other code can read any folder the same way; audio/video keep `<title> [<id>].<ext>` so they're recognisable when copied out (e.g. onto a music player).
- Why the split: the title appears in both folder and file names, which hit Windows' 260-character path limit for long titles.
- Rejected: fixed names for media too (every track called `audio.m4a`, which collides and is unlabeled on players), trimming titles, and relying on Windows long paths (one PC only; many tools ignore the setting).
- Files: `main.py`.

## 2026-10-13 — Transcripts use only original English captions
- Order: creator-uploaded English (`en` / `en-XX`, including human translations), then YouTube auto-captions only when the speech itself is English (`en-orig`).
- Rejected: YouTube's machine-translated English (auto `en` without `en-orig`, or `en-ja`-style translated subtitles). It stacks translation errors on top of speech-recognition errors.
- Files: `transcript.py` (`pick_track`).

## 2026-10-13 — Transcript stored as JSON segments plus a sentence-per-line `.txt`
- The JSON keeps the original caption pieces and timings for code. The `.txt` joins pieces into sentences for people and chat AIs.
- Rejected: `.srt`/`.vtt` files (cue numbers and timing noise; YouTube's `.vtt` repeats rolling lines) and `.json3` (hard to read).
- Files: `transcript.py`, `main.py`.

## 2026-07-07 — Reverted: reusing the metadata extraction for the audio download
- Passing the metadata `info` dict to `process_ie_result(download=True)` saved a second extraction, but the download failed with `HTTP 403`: those format URLs come from a client that now needs a PO token.
- Audio and video downloads re-extract fresh instead. They don't re-fetch comments, so the extra cost is small.
- Files: `main.py` (`download_audio_only`, `download_video`).

## 2026-07-07 — Top 1000 comments via YouTube's "top" sort, then re-sorted by likes
- YouTube has no "most liked" sort, so the true 1000 most-liked would mean fetching every comment.
- Rejected that for speed and fewer "Incomplete data received" retries. The "top" sort is already like-weighted.
- Side effect: yt-dlp sets `comment_count` to the number fetched, so the JSON doesn't keep the video's real total.
- Files: `main.py` (`ydl_opts`, `save_metadata_and_transcript`).

## 2026-07-07 — One video per run; playlists are rejected up front
- A `process=False` peek rejects playlist URLs before the expensive extraction. `noplaylist` makes `watch?v=…&list=…` links (including radio mixes) download just that video.
- Rejected: bulk-processing playlists, and rejecting every `list=` URL (that would force hand-editing shared links).
- Files: `main.py`.
