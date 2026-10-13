# yt-downloader

A small Python script that, for a single YouTube video:

1. **Extracts metadata** — including the top comments (most-liked first) — and saves it as JSON.
2. **Saves the English transcript**, when the video has English captions.
3. **Downloads the audio and/or video** — you choose which at runtime.

Everything for one video lands in a single folder under `Downloads/`.

Deeper docs: [docs/features/](docs/features/README.md) describes each feature's current
design; [docs/DECISIONS.md](docs/DECISIONS.md) records why things are the way they are.

Extraction and downloads are powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## What it does

`main.py` asks two questions up front (the video URL, then audio/video/both) and hands
both to `capture()` in `capture.py`, which runs the rest without further input:

| Module | Owns |
|---|---|
| `capture.py` | One video end to end (`capture(url, choice, ...)`) and the yt-dlp option sets |
| `transcript.py` | Choosing and parsing English captions (`get_transcript`, `to_txt`) |
| `video_folder.py` | The video's folder: names, `data.json` / `transcript.txt`, overwrite rules |
| `helpers.py` | Comment sorting, reading the audio/video answer, spotting playlists |

**1. Extract once** — a single yt-dlp call (`METADATA_OPTS` in `capture.py`) pulls the
full metadata, including the comments list, without downloading the media:

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

**2. Save metadata and transcript** — writes the sanitized, JSON-serializable info to
`data.json` in the video's folder (`video_folder.py`). Before
saving, the fetched comments are re-ordered **most-liked first** (by `like_count`).

The English transcript (built by `transcript.py`) is saved two ways:

- In the JSON, as a `transcript` field for code and AI tools:
  `{"source": "manual" | "auto", "segments": [{"start", "end", "text"}, …]}` — the
  original caption pieces with their times in seconds.
- As `transcript.txt` for reading: one line per sentence, starting a
  new line after sentence-ending punctuation (even mid-caption; not after titles like
  `Mr.` or `Dr.`) or after a pause of more than 1.5 seconds,
  e.g. `[00:17] All my life I been this way.` (`[h:mm:ss]` for videos an hour or longer).

Which captions count as English:

- **Creator-uploaded English** (`en`, or a regional variant like `en-US`) is used
  first, on any video — `source: "manual"`.
- Otherwise, YouTube's **auto-captions only when the speech itself is English**
  (`en-orig`) — `source: "auto"`.
- Machine-translated English is never used. If nothing qualifies, `transcript` is
  `null`, no `.txt` is written, and the console says so.
- If a creator track has no `.srt` download, the auto-captions are tried next.
- Caption problems never stop a run: if the caption download fails, the file is empty,
  or nothing qualifies, the metadata is still saved with `transcript: null`, and the
  summary says why. A partly broken caption file (e.g. a blank caption) keeps its
  readable parts.

**3. Download media** — runs the download(s) you chose at the start. Each does its own
fresh re-extraction of the URL:

- **Audio** (`AUDIO_OPTS`) — `format: 'bestaudio[ext=m4a]/bestaudio'`: YouTube's
  `.m4a` (AAC) stream, which music players handle almost everywhere, falling back to the
  best other audio-only stream (usually `.webm`/Opus) when there's no `.m4a`. No
  re-encoding. ffmpeg embeds **tags** (title, artist, date) and the video thumbnail as
  **cover art**, so players show proper names. Saved as `<title> [<id>].m4a`.
- **Video** (`VIDEO_OPTS`) — `format: 'bestvideo+bestaudio/best'`, merged by
  ffmpeg into a single full-resolution `<title> [<id>].mp4`. **Requires ffmpeg.**

Each step re-extracts fresh instead of reusing step 1's data: those metadata format
URLs now require a PO token and fail the download with `HTTP 403`, whereas a fresh
extraction lets yt-dlp negotiate a client that yields a usable URL.

### Output layout

```
Downloads/                                  ← next to main.py, git-ignored
└── <title> [<id>]/
    ├── data.json
    ├── transcript.txt                      ← when English captions exist
    ├── <title> [<id>].m4a                  ← if you chose audio (.webm if no .m4a)
    └── <title> [<id>].mp4                  ← if you chose video
```

The data files have fixed names so other code can read any folder the same way
(`<folder>/data.json`); the JSON itself holds the title and `id`. Audio and video keep
the title in their names so they're still recognisable when copied out, e.g. onto a
music player. The video ID keeps folder names unique and makes it easy to find the
video on YouTube (`youtube.com/watch?v=<id>`). Running the same video again overwrites everything in
its folder, re-downloading any audio/video, and removes an old `transcript.txt` if the
new run has no transcript; the JSON's `epoch` field records when the metadata was
fetched.

## Requirements

- Python 3.12+ (developed on 3.14)
- `yt-dlp` (see `requirements.txt`)
- **Node.js** on your PATH — yt-dlp uses it to solve YouTube's signature challenge.
  Without a JavaScript runtime, downloads fail with `HTTP 403` / "Video unavailable".
- **ffmpeg** on your PATH — required for **audio and video** downloads: it embeds the
  audio's tags and cover art, and merges the separate video and audio streams. The
  metadata and transcript don't need it.

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

The script asks `Input the Youtube URL` — paste a YouTube video URL and press Enter —
then `Download (a)udio, (v)ideo, or (b)oth?` — enter `a`, `v`, or `b` (anything else
downloads no media). After that it runs unattended and ends with a short summary: the
folder, the transcript status, and what was written or downloaded. The metadata JSON
and transcript are always saved regardless of the audio/video choice.

## Tests

Each module is tested through its interface with Python's built-in `unittest`, offline:
`capture()` against a fake yt-dlp and a temp folder, `video_folder.py` in a temp folder,
and `transcript.py` with a stand-in caption download:

```powershell
python -m unittest -v
```

## Notes

- Windows limits full paths to 260 characters, and audio/video file names repeat the
  title already in the folder name. Titles longer than about 85 characters can fail to
  save unless Windows long paths are enabled.
- On videos with many comments you may see repeated `Incomplete data received …
  Giving up after 3 retries` warnings. These are **non-fatal** — YouTube occasionally
  returns an incomplete comment page, so yt-dlp skips that page and continues (you may
  end up with slightly fewer comments than the true total). Uncommenting
  `sleep_interval_requests` in `METADATA_OPTS` in `capture.py` (1s between requests) reduces how often this
  happens, at the cost of a slower run.
- Audio/video downloads can still fail with `HTTP Error 403: Forbidden` — YouTube
  refuses some download requests (about half in testing on yt-dlp 2026.08.19; every
  one on the older 2026.07.04). It's per-request, so re-running usually works; the
  metadata and transcript are already saved by then. Keeping yt-dlp up to date
  (`requirements.txt` pins the version) helps most.
- You may see a warning like `n challenge solving failed: Some formats may be
  missing`. It is non-fatal — the best audio stream still downloads. Resolving it
  fully requires yt-dlp's EJS challenge-solver distribution; see the
  [EJS wiki](https://github.com/yt-dlp/yt-dlp/wiki/EJS).
- Audio and video downloads require `ffmpeg` (tags and cover art for audio, merging
  the streams for video). If it isn't on your PATH they fail after downloading. See the
  [yt-dlp dependencies docs](https://github.com/yt-dlp/yt-dlp#dependencies).
