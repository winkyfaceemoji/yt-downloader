# 0021. hub.cmd entry point and run state, with a held Windows lock

Status: Accepted (2026-11-11). Supersedes 0020.

## Context
ADR 0020 set up `hub.cmd` and the run state. Its lock was a file made with `O_EXCL` holding the run's PID, and "busy" meant that PID was alive. The architecture review (`docs/architecture-review.md`, finding 3) found two gaps. Two runs that both cleared a dead lock could both start. And a run that read the lock while it was still empty took it for dead, then crashed trying to delete it (Windows won't delete an open file). A reused PID could also make a dead run look busy. The data hub had the same problem with its runners and solved it with a held lock (data-hub ADR 0008).

## Decision
Everything in 0020 stays except how "busy" and "interrupted" are known:
- `hub.cmd` calls the venv's Python on `main.py` by full path (`%~dp0`). With arguments, `main.py` hands off to `hub.main`; with none, it keeps the prompts.
- Commands, `status` keys and exit codes are unchanged: `run capture --url <url> --mode audio|video|both [--music]`, `status`, `log`; 0 ok, 1 failed, 3 needs review, 4 busy, 64 bad arguments, 130 interrupted.
- Run state lives in `Storage\_logs\`: `yt-downloader.log`, `yt-downloader.state.json`, and `yt-downloader.lock`.
- **Busy** means a process holds byte 0 of `yt-downloader.lock` with `msvcrt.locking`. Windows frees it when the run releases it or its process ends, however it ends. `status` checks by reading that byte, which fails while it's locked and never takes the lock. The file stays between runs.
- **Interrupted** means `state.json` shows a started run (`last_run` set, `last_result` null) and nobody holds the lock. The next run logs it.
- A second run is refused with 4; there is no queue. Interactive runs take the same lock.

Rejected: patching the PID lock (an empty lock counts as busy for a while, a lost cleanup race exits 4). It narrows the two-cleaner race but can't close it, and keeps the reused-PID gap.

## Consequences
The tool is Windows-only (`msvcrt`); it already was in practice. No PID checks remain, so the `os.kill(pid, 0)` hazard and the reused-PID case are gone. State writes retry for about 2 s, because Windows can't replace `state.json` while a `status` has it open.
