# Output layout

All output for a video goes in one folder. `video_folder.py` owns it: name templates,
the fixed data file names, overwrite rules and stale-file cleanup. It's tested in a temp
folder by `test_video_folder.py`.

```
Downloads/                         ← next to main.py (not the working directory), git-ignored
└── <title> [<id>]/
    ├── data.json                  ← metadata, comments, transcript (always)
    ├── transcript.txt             ← when English captions qualify
    ├── <title> [<id>].m4a         ← audio, if chosen (.webm when no .m4a exists)
    └── <title> [<id>].mp4         ← video, if chosen
```

```python
VideoFolder(downloads_dir, naming_opts=None)
.path(info) -> folder path
.media_opts() -> yt-dlp options for audio/video downloads (outtmpl, overwrites, naming)
.save(info, video_data, transcript_text) -> (folder path, [actions])
```

## Invariants

- **One naming config.** The folder name (`path`) and the media file names
  (`media_opts`) both come from `naming_opts`, so options that change yt-dlp's
  sanitising (e.g. `restrictfilenames`) can't make them drift into different folders.
  Illegal Windows characters become full-width look-alikes (`:` → `：`), and `/` becomes
  `⧸` so a title never creates subfolders. Don't build these paths by hand; media
  downloads must start from `media_opts()`.
- **Fixed data names, titled media.** Code can always read `<folder>/data.json`; the
  JSON's `title` and `id` identify the video. Media keep the title so they're
  recognisable outside the folder.
- **Re-runs overwrite.** `media_opts()` sets `overwrites`, `save` rewrites `data.json`,
  and a run without a transcript removes the previous `transcript.txt`. The fetch time is
  the JSON's `epoch`, not part of any name.

## Audio and video formats

The options live in `capture.py`:
- `AUDIO_OPTS`: `bestaudio[ext=m4a]/bestaudio`, no re-encoding. `writethumbnail` +
  `FFmpegMetadata` + `EmbedThumbnail` add title, artist and date tags and the thumbnail
  as cover art. yt-dlp converts the `.webp` thumbnail to `.png`, embeds it with ffmpeg
  (no mutagen/AtomicParsley needed), then deletes the image.
- `VIDEO_OPTS`: `bestvideo+bestaudio/best` merged by ffmpeg into `.mp4`.
- ffmpeg is required for both; the metadata/transcript step doesn't need it.

## Gotchas

- **Windows 260-character path limit.** The title appears in both the folder and media
  file names. With the project at `C:\Users\choua\Documents\Git\yt-downloader`
  (53 characters to `Downloads\`), media for titles longer than about 85 characters can
  fail to save. Windows long paths aren't enabled on that PC. `data.json` /
  `transcript.txt` are short, so the data step has more headroom.
- **Intermittent 403 on media**, even with yt-dlp 2026.08.19: YouTube refuses some
  download requests. Metadata and the transcript are already saved by then, so re-run.
