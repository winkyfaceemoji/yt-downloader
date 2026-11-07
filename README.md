# yt-downloader

A small Python script built on [yt-dlp](https://github.com/yt-dlp/yt-dlp). For one YouTube video at a time it saves:

- **Metadata** plus the top 1000 comments, most-liked first, as `data.json`.
- The **English transcript**, when the video has English captions: as `transcript.txt` (one timestamped line per sentence) and inside `data.json`. It never uses machine-translated English.
- Optionally the **audio** (`.m4a`, with title, artist and cover art for music players) and/or the **video** (full-resolution `.mp4`).
- If you say the audio is **music**, it looks the song up on [MusicBrainz](https://musicbrainz.org) and tags the `.m4a` with the album, track number and album art, so it files properly in your music player. It only does this when it's confident of the match; otherwise the audio keeps YouTube's title and thumbnail.

Everything for a video lands in one folder:

```
C:\Users\choua\Documents\Storage\Media\YouTube\     ← backed up by the server sync
└── <title> [<id>]/
    ├── data.json
    ├── transcript.txt             ← when English captions exist
    ├── <title> [<id>].m4a         ← if you chose audio (.webm if YouTube has no .m4a)
    └── <title> [<id>].mp4         ← if you chose video
```

Running the same video again replaces its folder's contents. Playlist links are rejected; a link to a video inside a playlist or mix downloads just that video.

## Setup

You need Python 3.12+, plus **Node.js** and **ffmpeg** on your PATH. Node lets yt-dlp handle YouTube's signature checks; ffmpeg adds the audio tags and cover art and merges video. From the project folder (PowerShell):

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

1. Paste a YouTube video URL at `Input the Youtube URL`.
2. Answer `Download (a)udio, (v)ideo, or (b)oth?` with `a`, `v` or `b`. Anything else saves only the metadata and transcript.
3. If you chose audio: answer `Treat as music?` with `y` to add MusicBrainz tags and album art.

After that it runs unattended and ends with a summary: the folder, the transcript status, what was written or downloaded, and anything that needs review.

### From the data hub (or any script)

The data hub runs the same thing with no questions through `hub.cmd`:

```
hub.cmd run capture --url <url> --mode audio|video|both [--music]
hub.cmd status     ← is it running, when it last ran, how that went, anything to look at
hub.cmd log        ← where the log is: C:\Users\choua\Documents\Storage\_logs\yt-downloader.log
```

The exit code is the result:

| Code | Meaning |
|---|---|
| 0 | everything saved |
| 1 | failed |
| 3 | finished, but something needs review (no transcript, or music asked for but not tagged) |
| 4 | another run is in progress |
| 64 | bad arguments (e.g. `--music` with `--mode video`) |
| 130 | stopped with Ctrl+C |

Runs from `python main.py` share the same log and status, so only one run happens at a time.

Tests (offline, no YouTube needed): `python -m unittest -v`

## If something goes wrong

- **`HTTP Error 403: Forbidden` on audio/video**: YouTube refuses some download requests. The metadata and transcript are already saved, so just run it again.
- **"Sign in to confirm you're not a bot"**: export your YouTube cookies in Netscape format (e.g. with a "cookies.txt" browser extension) to a file named `cookies.txt` next to `main.py`. It's used automatically and is git-ignored. It's a login secret, so don't share it; downloads are tied to that account.
- **A song got no album tags**: the MusicBrainz match wasn't confident (e.g. the title isn't "Artist - Song"). That's on purpose, so you never get a wrong album.
- **`Incomplete data received … Giving up after 3 retries`**: harmless. YouTube sent an incomplete page of comments, so you may get slightly fewer than 1000.
- **`n challenge solving failed: Some formats may be missing`**: harmless; the audio still downloads.
- **A very long title fails to save**: Windows limits paths to 260 characters, and the title appears in both the folder and file names. Titles over about 88 characters can hit it.
- **"Another yt-downloader run is in progress"** when nothing is running: the last run's process was killed while it held its lock, and a new process happens to have reused its ID. Delete `Storage\_logs\yt-downloader.lock`.
- **Audio/video fails after downloading**: ffmpeg isn't on your PATH.

Design decisions are recorded in [docs/adr/](docs/adr/).
