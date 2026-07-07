# yt-downloader

A small Python script that extracts metadata from a YouTube video — including its
comments — and saves it as a JSON file. It does **not** download the video itself; it
only pulls information about it.

Extraction is powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## What it does

`main.pyw` runs yt-dlp against a single video URL with the following options:

- `getcomments: True` — fetch the full comments list
- `skip_download: True` — never download the media file, only metadata
- `extract_flat: False` — parse the complete metadata
- `quiet: True` — suppress yt-dlp's normal console noise

The sanitized (JSON-serializable) result is written to:

```
Data/<title>_<uploader>_<YYYY-MM-DD>_data.json
```

The `Data/` folder is created automatically and is git-ignored.

## Requirements

- Python 3.12+ (developed on 3.14)
- `yt-dlp` (see `requirements.txt`)

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
python main.pyw
```

The target video is currently hard-coded via the `URL` variable near the top of
`main.py` — edit that line to fetch a different video.

## Notes

- yt-dlp may warn that no JavaScript runtime (e.g. `deno`) or `ffmpeg` is installed.
  Neither is required for metadata-only extraction, but installing them enables
  additional formats if you extend the script to download media. See the
  [yt-dlp dependencies docs](https://github.com/yt-dlp/yt-dlp#dependencies).
