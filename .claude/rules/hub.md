---
paths:
  - "hub.py"
  - "hub.cmd"
  - "main.py"
  - "test_hub.py"
---

# Hub rules

## Invariants
- **The contract is shared with Adam's other tools** (ADR 0021). Don't change command names, JSON keys or exit codes alone: 0 ok, 1 failed, 3 needs review, 4 busy, 64 bad arguments, 130 interrupted. Any change goes through the data hub planning session.
- **Never prompt or pause when arguments are given.** `main.py` routes any arguments to `hub.main` before touching `input()`; with no arguments it keeps the prompts and calls `hub.run_capture`, so interactive runs share the same lock, log and state.
- **The held lock is the single source of "busy"** (ADR 0021). `acquire` locks byte 0 of `yt-downloader.lock` with `msvcrt.locking`; Windows frees it on `release` (in `finally`) or when the process ends, however it ends. A run refused with exit 4 never releases. The file stays between runs.
- **Interrupted comes from the state file**: `last_run` set, `last_result` null and nobody holding the lock. `start` writes the null and `finish` fills it, so every path out of a run must call `finish` or die.
- **`needs_review` is defined here** (`_missing`): no transcript, or music requested but `music_tagged is False`. It relies on `capture()`'s `transcript_found`, `music_tagged` and `music_note`; keep those accurate.
- **`main.py` must not import `capture` at the top.** Its `capture` wrapper loads it only when a capture runs, so `status` and `log` skip yt-dlp (about 1.3 s). `MainTests` checks yt-dlp isn't loaded.
- **Bad arguments exit 64.** `_Parser.error` raises `UsageError` instead of argparse's default `SystemExit(2)`.
- **`hub.cmd` calls siblings by full path** (`"%~dp0.venv\Scripts\python.exe" "%~dp0main.py"`). A bare call failed for the books converter even after `cd /d`. It has no `pause`, and `exit /b %errorlevel%` passes the code through.

## Gotchas
- **Don't go back to PID checks** (ADR 0021): PIDs get reused, and `os.kill(pid, 0)` terminates the process on Windows.
- **`status` must never take the lock.** It reads byte 0 instead: the read fails (`PermissionError`) while a run holds it. Taking the lock, even briefly, could refuse a run starting at that instant.
- **Windows can't replace or delete a file another process has open.** A `status` reading `state.json` blocks a run's `os.replace`, so `_write_state` retries for about 2 s.
- **Callers must quote `--url`.** `cmd` splits an unquoted `&` (`watch?v=…&list=…`) before `hub.cmd` starts, and `hub.cmd` can't fix that. The data hub quotes every argument (`core.command_line`).
- **Stop a run by killing its process, not Ctrl+C.** Under a batch file, Ctrl+C makes `cmd` ask "Terminate batch job (Y/N)?". The data hub plans a process kill (data-hub ADR 0004); a killed run reads as interrupted.
- **Stdout can be a cp1252 pipe** when the hub runs the tool, and printing a sanitised title (`：`) there would crash after the work is done. `main.py` sets `sys.stdout.reconfigure(errors='replace')`, and status JSON is ASCII-escaped.
- **The paths are this PC's**: `hub.STORAGE`, `DOWNLOADS_DIR` and `LOGS_DIR` (ADR 0021, 0022). `hub.main` and `run_capture` take the folders as required arguments, and only `main.py` passes the real ones, so a test that forgets them fails instead of writing to Storage.
