# yt-downloader

Python script around yt-dlp. For one YouTube video it saves metadata, the top comments, the English transcript, and optionally the audio (.m4a) and video (.mp4) into `Downloads/<title> [<id>]/`. When asked to treat the audio as music, it tags it from MusicBrainz, with album art from the Cover Art Archive.

## Commands
Windows. Use the project venv's Python: the system Python has its own, older yt-dlp.

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt   # setup
python main.py                 # asks: URL, (a)udio/(v)ideo/(b)oth, and (if audio) treat as music; needs the network
python -m unittest -v          # offline tests (fake yt-dlp + temp folders)
```

Outside requirements.txt: **Node.js** (yt-dlp's JS runtime, for YouTube's signature challenge) and **ffmpeg** (audio tags and cover art, video merging) must be on PATH.

## Conventions
- Modules:
  - `main.py` holds only the prompts.
  - `capture.py` runs one video end to end and holds the yt-dlp option sets.
  - `transcript.py` chooses and parses English captions.
  - `video_folder.py` owns names, paths and file writing.
  - `music.py` matches the song on MusicBrainz and tags the `.m4a`.
  - `helpers.py` holds small pure functions.

  Area rules in `.claude/rules/` load when you touch these files.
- Test each module only through its interface, with no network. yt-dlp comes in through `capture(..., ydl_factory=...)`, HTTP through `http_get`, and output through `downloads_dir`, so tests use fakes and temp folders. Write the failing test first.
- Python 3.12+ syntax (nested quotes in f-strings). `requirements.txt` pins yt-dlp and mutagen; upgrade them on purpose (ADR 0009, 0018), and vet any new dependency against its upstream docs first.
- `Downloads/` is user data and git-ignored. Don't write test output into it; for real end-to-end runs, copy the modules to a short temp path. `cookies.txt` is a login secret, git-ignored, and must never be committed.
- Commit messages carry no Claude/Anthropic attribution trailers.

## Project-wide gotchas
- **Intermittent `HTTP 403` on media downloads** comes from YouTube, varies by request, and is worse on older yt-dlp. The metadata is saved before any download, so re-running is the fix (ADR 0003, 0009).
- **Windows path limit**: the title appears in both the folder and media names, so very long titles (over ~85 characters here) can fail to save, and deep temp folders fail sooner.
- **MusicBrainz** needs the repo-URL User-Agent and at most 1 request/second (`music.http_get`). Don't loop lookups without that pacing.
- **Console encoding**: sanitised titles contain full-width characters (`：`, `？`, `⧸`), so printing them to a cp1252 pipe raises `UnicodeEncodeError`.

## ADR index
- [0001. One video per run; playlists rejected up front](docs/adr/0001-one-video-per-run.md)
- [0002. Top 1000 comments via YouTube's "top" sort, re-sorted by likes](docs/adr/0002-top-1000-comments-resorted-by-likes.md)
- [0003. Reverted: reusing the metadata extraction for media downloads](docs/adr/0003-reverted-reusing-metadata-for-media-downloads.md)
- [0004. Transcripts use only original English captions](docs/adr/0004-original-english-captions-only.md)
- [0005. Transcript stored as JSON segments plus a sentence-per-line .txt](docs/adr/0005-transcript-json-segments-plus-txt.md)
- [0006. Per-video folders under Downloads/, anchored to main.py](docs/adr/0006-per-video-folders-under-downloads.md)
- [0007. Fixed data file names, titled media file names](docs/adr/0007-fixed-data-names-titled-media.md)
- [0008. Audio is native .m4a with embedded tags and cover art](docs/adr/0008-native-m4a-audio-with-tags.md)
- [0009. Pin yt-dlp 2026.08.19 to cut media-download 403s](docs/adr/0009-pin-yt-dlp-2026-08-19.md)
- [0010. Reverted: strict .srt parsing](docs/adr/0010-reverted-strict-srt-parsing.md)
- [0011. Ask the audio/video question before the metadata fetch](docs/adr/0011-ask-audio-video-question-up-front.md)
- [0012. Capture one video through a single capture() call](docs/adr/0012-capture-one-video-through-capture.md)
- [0013. Treat a run as music only when the user says so](docs/adr/0013-music-is-opt-in-per-run.md)
- [0014. No Artist/Album library folders](docs/adr/0014-no-artist-album-library-folders.md)
- [0015. MusicBrainz: confident matches only, best non-compilation release](docs/adr/0015-musicbrainz-confident-matches-only.md)
- [0016. Identify the project to MusicBrainz by its repo URL](docs/adr/0016-musicbrainz-contact-is-repo-url.md)
- [0017. Optional cookies.txt for every yt-dlp call](docs/adr/0017-optional-cookies-file.md)
- [0018. mutagen writes the MusicBrainz tags](docs/adr/0018-mutagen-writes-musicbrainz-tags.md)
