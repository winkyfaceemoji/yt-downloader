# yt-downloader

A small Python script that, for a single YouTube video:

1. **Extracts metadata** — including the top comments (most-liked first) — and saves it as JSON.
2. **Downloads the audio and/or video** — you choose which at runtime.

Extraction and downloads are powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## What it does

`main.py` prompts for a single YouTube video URL when run, then processes it in three
steps:

**1. Extract once** — a single yt-dlp call (`ydl_opts`) pulls the full metadata,
including the comments list, without downloading the media:

- `getcomments: True` — fetch the comments list
- `skip_download: True` — read metadata only, don't download the video
- `extract_flat: False` — parse the complete metadata
- `noplaylist: True` — for a `watch?v=…&list=…` URL, process only the video
- `extractor_args: {youtube: {comment_sort: [top], max_comments: [1000]}}` — fetch at
  most the top 1000 comments using YouTube's "top" (like-weighted) sort
- `js_runtimes: {'node': {}}` — use Node to sign YouTube requests (see Requirements)
- `quiet: False` — show yt-dlp's progress and warnings in the console

(`sleep_interval_requests: 1` is present but commented out — see Notes.)

This tool handles **one video at a time**. If you paste a playlist URL, the script
detects it up front (before any heavy extraction) and exits with a message rather than
bulk-processing every video. A `watch?v=…&list=…` link is treated as just the single
video.

**2. Save metadata** (`download_metadata_only`) — writes the sanitized,
JSON-serializable info to:

```
Data/<title>_<uploader>_<YYYY-MM-DD>_data.json
```

The title and uploader are passed through yt-dlp's `sanitize_filename`, so values
with characters illegal on Windows (`:`, `?`, `|`, …) are handled safely; a missing
title or uploader falls back to `unknown`. Before saving, the fetched comments are
re-ordered **most-liked first** (by `like_count`).

**3. Download media** — prompts `Download (a)udio, (v)ideo, or (b)oth?` and runs the
matching download(s). Each does its own fresh re-extraction of the URL:

- **Audio** (`download_audio_only`) — `format: 'bestaudio'`, saved in its native
  container (usually `.webm`/opus or `.m4a`) with **no re-encoding**, to
  `Audio/<title>.<ext>`. Does not need ffmpeg.
- **Video** (`download_video`) — `format: 'bestvideo+bestaudio/best'`, merged by
  ffmpeg into a single full-resolution `.mp4` at `Video/<title>.mp4`. **Requires
  ffmpeg.**

Each step re-extracts fresh instead of reusing step 1's data: those metadata format
URLs now require a PO token and fail the download with `HTTP 403`, whereas a fresh
extraction lets yt-dlp negotiate a client that yields a usable URL.

`Data/`, `Audio/`, and `Video/` are created automatically and are git-ignored.

## Requirements

- Python 3.12+ (developed on 3.14)
- `yt-dlp` (see `requirements.txt`)
- **Node.js** on your PATH — yt-dlp uses it to solve YouTube's signature challenge.
  Without a JavaScript runtime, downloads fail with `HTTP 403` / "Video unavailable".
- **ffmpeg** on your PATH — required only for **video** downloads (it merges the
  separate video and audio streams). Audio-only downloads don't need it.

## Setup

From the project root (Windows / PowerShell):

```powershell
python -m venv .venv          # only if .venv doesn't exist yet
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

On CMD, activate with `.venv\Scripts\activate` instead.

## Running

```powershell
python main.py
```

The script prompts `Input the Youtube URL` — paste a YouTube video URL and press Enter.
It then asks `Download (a)udio, (v)ideo, or (b)oth?` — enter `a`, `v`, or `b`. The
metadata JSON is always saved regardless of that choice.

## Notes

- On videos with many comments you may see repeated `Incomplete data received …
  Giving up after 3 retries` warnings. These are **non-fatal** — YouTube occasionally
  returns an incomplete comment page, so yt-dlp skips that page and continues (you may
  end up with slightly fewer comments than the true total). Uncommenting
  `sleep_interval_requests` in `ydl_opts` (1s between requests) reduces how often this
  happens, at the cost of a slower run.
- You may see a warning like `n challenge solving failed: Some formats may be
  missing`. It is non-fatal — the best audio stream still downloads. Resolving it
  fully requires yt-dlp's EJS challenge-solver distribution; see the
  [EJS wiki](https://github.com/yt-dlp/yt-dlp/wiki/EJS).
- **Video** downloads require `ffmpeg` to merge the separate video and audio streams
  into the `.mp4`. If it isn't on your PATH, video downloads fail (or fall back to a
  lower-quality single stream). Audio-only downloads keep the native format and don't
  need it. See the
  [yt-dlp dependencies docs](https://github.com/yt-dlp/yt-dlp#dependencies).
