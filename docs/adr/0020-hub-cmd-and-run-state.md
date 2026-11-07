# 0020. hub.cmd entry point and run state in Storage\_logs

Status: Accepted (2026-11-07)

## Context
Adam's data hub (a Steam-like library of his tools) launches every tool through that tool's own `hub.cmd`, under one shared contract:
- `status` prints one JSON object: `tool`, `busy`, `last_run`, `last_result`, `attention`, `log`.
- `run <action>` runs with no prompts and no pause, and its exit code is the result.
- `log` prints the latest log's path.

The tool had no run state, and its only entry point was interactive prompts.

## Decision
- `hub.cmd` calls the venv's Python on `main.py` by full path (`%~dp0`). With arguments, `main.py` hands off to `hub.main`; with none, it keeps the prompts.
- Commands: `run capture --url <url> --mode audio|video|both [--music]`, `status`, `log`. `--music` with `--mode video` is a bad-arguments error.
- Shared exit codes: 0 ok, 1 failed, 3 needs review, 4 busy/refused, 64 bad arguments, 130 interrupted (Ctrl+C).
- Run state lives in `Storage\_logs\`, next to the other tools' logs:
  - `yt-downloader.log`: one line per event
  - `yt-downloader.lock`: `<pid> <start>`, created atomically (`O_EXCL`)
  - `yt-downloader.state.json`: last run, result and attention
- `busy` means the lock's PID is alive. A second run is refused with 4; there is no queue. A lock whose PID is dead reads as `interrupted`, and the next run clears it.
- `needs_review` means the run finished but something requested or expected is missing: no transcript, or music requested but not tagged. `failed` means it didn't finish (an error, HTTP 403, or a playlist).
- Interactive runs take the same lock and write the same log and state, so the hub's status reflects them too.

Rejected: queueing a second run, an interactive path outside the lock (status would miss it), argparse's default exit code 2 for bad arguments, and probing PIDs with `os.kill(pid, 0)` (on Windows that kills the process).

## Consequences
A reused PID can make a dead run's lock look busy until that unrelated process exits; it's rare and documented in the hub rule. Media output is unchanged (ADR 0019).
