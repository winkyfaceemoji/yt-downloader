---
paths:
  - "video_folder.py"
  - "test_video_folder.py"
---

# Video folder rules

## Invariants
- **One naming config.** The folder name (`path`) and the media file names (`media_opts`) both come from `naming_opts`, so a sanitising option such as `restrictfilenames` can't split one video across two folders (ADR 0012). Never build these paths by hand.
- **Fixed data names, titled media** (ADR 0007). Code reads `<folder>/data.json`, and the JSON's `title` and `id` identify the video. Media keep `<title> [<id>].<ext>` so they're recognisable outside the folder, e.g. on a music player.
- **Re-runs overwrite** (ADR 0006). `media_opts()` sets `overwrites`, `save` rewrites `data.json`, and a run with no transcript removes the old `transcript.txt` so the folder matches `data.json`.
- `Downloads/` sits next to `main.py`, not the working directory. `main.py` sets it, and it's git-ignored.

## Gotchas
- **Folder names go through yt-dlp's sanitising.** Illegal Windows characters become full-width look-alikes (`:` → `：`), and `/` becomes `⧸`, so a title never creates subfolders. Printing these names on a cp1252 Windows console can raise `UnicodeEncodeError`; use `ascii()` or UTF-8 output.
- **Windows 260-character path limit.** The title is in both the folder and media names. With the project at `C:\Users\choua\Documents\Git\yt-downloader`, media for titles over about 85 characters can fail to save, and long paths are off on this PC. Deep temp paths (like Claude's scratchpad) hit the limit much sooner.
