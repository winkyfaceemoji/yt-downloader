# 0022. Captures go to Storage\Media\YouTube; re-runs keep old media and follow renamed titles

Status: Accepted (2026-11-11). Supersedes 0019.

## Context
ADR 0019 said a re-run "overwrites everything" in a video's folder. The code only overwrote files with the same name, so media a re-run didn't download stayed (review finding 4). The folder name also holds the title, so a renamed video got a second folder (finding 5).

## Decision
From 0019, unchanged:
- Captures go to `C:\Users\choua\Documents\Storage\Media\YouTube\` (`hub.DOWNLOADS_DIR`), for both `hub.cmd` and the prompts.
- One folder per video, `<title> [<id>]/`. The fetch time is the JSON's `epoch`, not part of a name.

Changed:
- **A re-run keeps media it doesn't download again.** It rewrites `data.json` and `transcript.txt` (or removes a stale one) and overwrites the media it downloads. An audio-only re-run keeps the old `.mp4`; a `.webm` and a later `.m4a` both stay.
- **A renamed video keeps one folder.** When the folder for the current title doesn't exist and exactly one other folder ends in `[<id>]`, the re-run renames it to the current title. Media inside keep their old names, so a new download under the new title sits next to the old file rather than replacing it. If Windows refuses the rename (a file in it is open), the run notes that and saves to a new folder instead of failing.

Rejected: deleting media a re-run didn't download (the folder always matches the last capture, but a metadata-only refresh would delete the audio from the backed-up library), and naming folders by ID only (breaks the readable `<title> [<id>]` name).

## Consequences
- The folder can hold media older than `data.json`; its file times say which run made it.
- With two or more old folders for one ID, nothing is renamed and a new folder appears.
- The path limit is as in 0019: titles up to about 88 characters.
