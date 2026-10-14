# 0012. Capture one video through a single capture() call

Status: Accepted (2026-10-13)

## Context
`main.py` ran its whole flow on import (`input()` plus network calls), so none of it could be tested. A data-loss bug hid in the untested calling code, and folder naming relied on two separate yt-dlp configs happening to agree.

## Decision
`main.py` only asks the questions. The work is split across four modules:
- `capture.py` runs one video behind `capture(url, choice, *, ydl_factory, downloads_dir)`.
- `video_folder.py` owns names and paths, from one naming config.
- `transcript.py` exposes only `get_transcript` and `to_txt`.
- `helpers.py` holds the small pure pieces.

Each module is tested through its interface, with a fake yt-dlp and temp folders and no network.

Rejected: keeping the flow in `main.py` and only pulling out pure helpers (the bugs stay in the untested callers), and a separate port for the filesystem (a temp folder already stands in for it). The design was validated with a throwaway prototype, deleted afterwards.

## Consequences
New behaviour belongs in a module, with a test at that module's interface. `main.py` stays prompts-only.
