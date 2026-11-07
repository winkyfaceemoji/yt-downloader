# Glossary

- **Capture**: one run for one YouTube video: metadata and comments, transcript, then any chosen audio/video (`capture()`).
- **Video folder**: `Storage\Media\YouTube\<title> [<id>]\`, holding everything from a video's captures.
- **Mode**: what media a capture downloads: `audio`, `video` or `both` (prompt answers `a`/`v`/`b`; anything else means none).
- **Transcript**: the video's original-English captions, as `transcript.txt` and `data.json`'s `transcript` field.
- **Music match**: a confident MusicBrainz identification of the song, saved as `data.json`'s `musicbrainz` and tagged into the `.m4a`.
- **Data hub**: Adam's Steam-like launcher for his data tools. It runs this tool only through `hub.cmd`.
- **Run state**: the log, lock and last-result files in `Storage\_logs` that `hub.cmd status` reports.
- **Busy**: a live process holds the run lock; a second run is refused (exit 4).
- **Interrupted**: a run that stopped before finishing (Ctrl+C, or its process died with the lock still held).
- **Needs review**: the run finished but something requested or expected is missing: no transcript, or music not tagged.
- **Attention**: the short notes in `status` saying what needs review or why a run failed.
