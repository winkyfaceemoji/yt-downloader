---
paths:
  - "capture.py"
  - "main.py"
  - "helpers.py"
  - "test_capture.py"
  - "test_helpers.py"
---

# Capture rules

## Invariants
- `main.py` asks all questions up front and only then calls `capture()` (ADR 0011, 0012): the URL, the audio/video choice, and "Treat as music?" (asked only when audio is chosen, ADR 0013). New behaviour goes in a module with a test at its interface, not in `main.py`.
- Order matters. Peek with `extract_info(..., process=False)` and reject playlists first (ADR 0001). Then fetch metadata and comments, then the transcript, then save. Only after that, download media. That's why a media failure never loses `data.json` or the transcript.
- Media downloads re-extract the URL fresh (`ydl.download([url])` for video, `extract_info(url, download=True)` for audio, so its file path comes back). Never pass the metadata `info` dict to `process_ie_result(download=True)`; its format URLs need a PO token and fail with 403 (ADR 0003).
- `noplaylist` must be on both the metadata pass and the media passes, or a `watch?v=…&list=…` link can pull a whole playlist or radio mix.
- yt-dlp extraction and download errors propagate to `main.py`, which prints them and exits 1. Caption problems never propagate (see the transcript rules).
- Media options must start from `VideoFolder.media_opts()`, so names come from the single naming config.
- The MusicBrainz lookup runs only with `as_music` and an audio download, and before `save`, so `data.json` gets its `musicbrainz` field. Tagging runs after the audio download, on the path yt-dlp reports (`extract_info(download=True)` → `requested_downloads[0].filepath`). The final name can be `.m4a` or `.webm`, so don't guess it.
- `cookies_file`, when given, goes into every yt-dlp option set: metadata, audio and video (ADR 0017).

## Gotchas
- **The comment cap is load-bearing for speed** (ADR 0002). Without `max_comments`, an 11k-comment video takes minutes and logs many "Incomplete data received … Giving up after 3 retries" warnings. Those are non-fatal skipped pages. `sleep_interval_requests` (commented out in `METADATA_OPTS`) cuts them down at the cost of speed.
- **`comment_count` in `data.json` is the number fetched**, not the video's real total, because yt-dlp overwrites it when `getcomments` is on.
- **Media 403s are intermittent and come from YouTube's side** (ADR 0009). Retry and PO-token plugins were rejected; re-running works, and upgrading yt-dlp is the main fix.
- **Tests never touch the network.** `test_capture.py` drives `capture()` with `FakeYoutubeDL`, a fake `http_get` and a temp folder. Music tests need ffmpeg to create a sample `.m4a`, and are skipped without it. Running `main.py` prompts for input and needs the network, so don't run it from automated checks. For a real end-to-end run, copy the modules to a short temp path so your real `Downloads/` isn't overwritten.
