---
paths:
  - "hub.py"
  - "hub.cmd"
  - "main.py"
  - "test_hub.py"
---

# Hub rules

## Invariants
- **The contract is shared with Adam's other tools** (ADR 0020). Don't change command names, JSON keys or exit codes alone: 0 ok, 1 failed, 3 needs review, 4 busy, 64 bad arguments, 130 interrupted. Any change goes through the data hub planning session.
- **Never prompt or pause when arguments are given.** `main.py` routes any arguments to `hub.main` before touching `input()`; with no arguments it keeps the prompts and calls `hub.run_capture`, so interactive runs share the same lock, log and state.
- **The lock is the single source of "busy".** It's created with `O_EXCL`, so two starts can't both win. It's released in `finally`, and never released by a run refused with exit 4. A lock whose PID is dead means interrupted; `acquire` logs that and clears it.
- **`needs_review` is defined here** (`_missing`): no transcript, or music requested but `music_tagged is False`. It relies on `capture()`'s `transcript_found`, `music_tagged` and `music_note`; keep those accurate.
- **Bad arguments exit 64.** `_Parser.error` raises `UsageError` instead of argparse's default `SystemExit(2)`.
- **`hub.cmd` calls siblings by full path** (`"%~dp0.venv\Scripts\python.exe" "%~dp0main.py"`). A bare call failed for the books converter even after `cd /d`. It has no `pause`, and `exit /b %errorlevel%` passes the code through.

## Gotchas
- **Never use `os.kill(pid, 0)` on Windows to test a PID: it terminates the process.** `_pid_alive` uses `OpenProcess` and `GetExitCodeProcess` (`STILL_ACTIVE` = 259). Access denied (error 5) counts as alive.
- **A reused PID** can make a dead run's lock look busy until that unrelated process exits. That's rare; deleting `Storage\_logs\yt-downloader.lock` clears it.
- **Stdout can be a cp1252 pipe** when the hub runs the tool, and printing a sanitised title (`：`) there would crash after the work is done. `main.py` sets `sys.stdout.reconfigure(errors='replace')`, and status JSON is ASCII-escaped.
- **The paths are this PC's**: `hub.STORAGE`, `DOWNLOADS_DIR` and `LOGS_DIR` (ADR 0019, 0020). Tests pass their own temp folders and must never fall back to the defaults.
