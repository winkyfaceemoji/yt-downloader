# Output layout

All output for a video goes in one folder, built from yt-dlp output templates in
`main.py` (`DOWNLOADS`, `NAME_TEMPLATE`, `FOLDER_TEMPLATE`, `MEDIA_TEMPLATE`).

```
Downloads/                         ← next to main.py (not the working directory), git-ignored
└── <title> [<id>]/
    ├── data.json                  ← metadata, comments, transcript (always)
    ├── transcript.txt             ← when English captions qualify
    ├── <title> [<id>].m4a         ← audio, if chosen (.webm when no .m4a exists)
    └── <title> [<id>].mp4         ← video, if chosen
```

## Invariants

- **One naming source.** The metadata step gets its folder from
  `YoutubeDL.prepare_filename(info, outtmpl=FOLDER_TEMPLATE)`, and the media downloads
  use `MEDIA_TEMPLATE`. Both go through yt-dlp's filename sanitising, so the folder
  names always match. Illegal Windows characters become full-width look-alikes (`:` →
  `：`), and `/` becomes `⧸` so a title never creates subfolders. Don't build these
  paths by hand.
- **Fixed data names, titled media.** Code can always read `<folder>/data.json`; the
  JSON's `title` and `id` identify the video. Media keep the title so they're
  recognisable outside the folder.
- **Re-runs overwrite.** `MEDIA_OPTS['overwrites']` re-downloads audio/video;
  `data.json` is rewritten; a stale `transcript.txt` is removed. The fetch time is the
  JSON's `epoch`, not part of any name.

## Audio and video

- Audio (`download_audio_only`): `bestaudio[ext=m4a]/bestaudio`, no re-encoding.
  `writethumbnail` + `FFmpegMetadata` + `EmbedThumbnail` add title, artist and date
  tags and the thumbnail as cover art. yt-dlp converts the `.webp` thumbnail to `.png`,
  embeds it with ffmpeg (no mutagen/AtomicParsley needed), then deletes the image.
- Video (`download_video`): `bestvideo+bestaudio/best` merged by ffmpeg into `.mp4`.
- Both re-extract the URL fresh rather than reusing the metadata extraction (see
  DECISIONS.md: reused format URLs return 403). Shared settings live in `MEDIA_OPTS`.
- ffmpeg is required for both; the metadata/transcript step doesn't need it.

## Gotchas

- **Windows 260-character path limit.** The title appears in both the folder and
  media file names. With the project at `C:\Users\choua\Documents\Git\yt-downloader`
  (53 characters to `Downloads\`), media for titles longer than about 85 characters
  can fail to save. Windows long paths aren't enabled on that PC. `data.json` /
  `transcript.txt` are short, so the data step has more headroom.
- **Intermittent 403 on media** even with yt-dlp 2026.08.19: YouTube refuses some
  download requests. Metadata and the transcript are already saved by then, so re-run.
