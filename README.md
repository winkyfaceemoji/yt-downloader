# yt-downloader

A small Python script that, for a single YouTube video, does two things:

1. **Extracts metadata** — including the full comments list — and saves it as JSON.
2. **Downloads the audio** track as a standalone file.

It does not download the video itself. Extraction and download are powered by
[yt-dlp](https://github.com/yt-dlp/yt-dlp).

## What it does

`main.py` targets a single video URL (the `URL` variable near the top of the file) and
runs in three steps:

**1. Extract once** — a single yt-dlp call (`ydl_opts`) pulls the full metadata,
including the comments list, without downloading the media:

- `getcomments: True` — fetch the full comments list
- `skip_download: True` — read metadata only, don't download the video
- `extract_flat: False` — parse the complete metadata
- `js_runtimes: {'node': {}}` — use Node to sign YouTube requests (see Requirements)
- `quiet: True` — suppress yt-dlp's normal console noise

**2. Save metadata** (`download_metadata_only`) — writes the sanitized,
JSON-serializable info to:

```
Data/<title>_<uploader>_<YYYY-MM-DD>_data.json
```

The title and uploader are passed through yt-dlp's `sanitize_filename`, so values
with characters illegal on Windows (`:`, `?`, `|`, …) are handled safely; a missing
title or uploader falls back to `unknown`.

**3. Download audio** (`download_audio_only`) — reuses the info dict from step 1 (no
second network fetch) and downloads:

- `format: 'bestaudio'` — best audio-only stream (errors out rather than falling
  back to a full video download)
- native container (usually `.webm`/opus or `.m4a`), with **no re-encoding**, so
  ffmpeg is not required
- saved to `Audio/<title>.<ext>`

Both `Data/` and `Audio/` are created automatically and are git-ignored.

## Requirements

- Python 3.12+ (developed on 3.14)
- `yt-dlp` (see `requirements.txt`)
- **Node.js** on your PATH — yt-dlp uses it to solve YouTube's signature challenge.
  Without a JavaScript runtime, downloads fail with `HTTP 403` / "Video unavailable".

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

Edit the `URL` variable near the top of `main.py` to target a different video.

## Notes

- You may see a warning like `n challenge solving failed: Some formats may be
  missing`. It is non-fatal — the best audio stream still downloads. Resolving it
  fully requires yt-dlp's EJS challenge-solver distribution; see the
  [EJS wiki](https://github.com/yt-dlp/yt-dlp/wiki/EJS).
- yt-dlp may also note that `ffmpeg` is not installed. It isn't needed here because
  the audio is saved in its native format without conversion. Install it only if you
  later add format conversion (e.g. to `.mp3`). See the
  [yt-dlp dependencies docs](https://github.com/yt-dlp/yt-dlp#dependencies).
