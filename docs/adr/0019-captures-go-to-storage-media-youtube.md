# 0019. Captures go to Storage\Media\YouTube

Status: Superseded by 0022

## Context
ADR 0006 put each video's folder in `Downloads/` next to `main.py`. That folder is outside `C:\Users\choua\Documents\Storage`, so the server sync never backed it up. The data hub now launches this tool; the hub never chooses folders, so each tool decides where its output goes.

## Decision
Captures go to `C:\Users\choua\Documents\Storage\Media\YouTube\` (`hub.DOWNLOADS_DIR`), for both `hub.cmd` and the interactive prompts. Everything else from 0006 still holds:
- one folder per video, `<title> [<id>]/`
- re-runs overwrite everything in it, re-downloading any media
- the fetch time is the JSON's `epoch`, not part of a name

The two videos already captured were moved there. The repo's `Downloads/` is gone, along with its `.gitignore` entry.

Rejected: keeping `Downloads/` in the repo (never backed up), and letting the hub pass a folder (the contract keeps folders inside each tool).

## Consequences
- The path is fixed to this PC's Storage folder. Tests pass their own temp folder and never write there.
- The base path is 47 characters (the repo's was 53), so the Windows path limit allows titles up to about 88 characters, up from about 85.
- Real end-to-end runs write to Adam's backed-up library: use a throwaway video and expect it to stay there.
