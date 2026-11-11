# Architecture review

Date: 2026-11-11. Branch: `auto/architecture-review` (from `aa7d5d6`).
Scope: general health, report only. Covers module boundaries, seams and tests, data contracts (`data.json`, `hub.cmd status`, exit codes), error handling and run state, and docs drift. No code, test, rule, ADR or doc was changed.

Baseline: `.venv\Scripts\python.exe -m unittest -v` runs 69 tests in about 3 s, all pass, none skipped.

How findings were checked: each one was read in the code. The Windows behaviour behind findings 1, 2 and 3 was also reproduced with a throwaway script in a temp folder, never against `hub.cmd`, `Storage\Media\YouTube` or `Storage\_logs`.

## Findings

| # | Severity | Title |
|---|---|---|
| 1 | High | A URL with `&` breaks a `hub.cmd run capture` call |
| 2 | Medium | `hub.cmd status` can crash a run that is finishing |
| 3 | Medium | Two runs starting together can both get the lock, or the refused one crashes |
| 4 | Medium | Re-runs leave old media in the folder |
| 5 | Low | A changed title starts a second folder for the same video |
| 6 | Low | Some run-state errors escape as tracebacks with exit 1 |
| 7 | Low | `hub.cmd status` takes over a second because it loads yt-dlp |
| 8 | Low | Ctrl+C under `hub.cmd` can ask "Terminate batch job (Y/N)?" |
| 9 | Low | `main.py`'s routing has no test |
| 10 | Low | `hub.main` and `run_capture` default to the real Storage folders |
| 11 | Low | `data.json`'s `musicbrainz` field has an undocumented third state |
| 12 | Low | Docs drift in a rule, a docstring and an ADR reference |

### 1. A URL with `&` breaks a `hub.cmd run capture` call
- **Severity:** high
- **Where:** `hub.cmd:4`; ADR 0001 (links with `&list=` must work); ADR 0020 (exit codes).
- **What's wrong:** `hub.cmd` is a batch file, so Windows runs it through `cmd.exe`, and `cmd` treats an unquoted `&` as "run the next command". Many YouTube links have one (`watch?v=…&list=…`, `&t=…`, `&pp=…`). A caller that passes the arguments as a list doesn't add quotes for `&`: Python's `subprocess` only quotes arguments that contain spaces.
- **Why it matters:** reproduced with a stand-in `.cmd` file built the same way as `hub.cmd` and called from Python 3.14 as `[cmd, 'run', 'capture', '--url', 'https://www.youtube.com/watch?v=abc&list=PLxyz', '--mode', 'audio']`. Python received only `['run', 'capture', '--url', 'https://www.youtube.com/watch?v=abc']`, and `cmd` then tried to run `list=PLxyz --mode audio` as a command ("'list' is not recognized"). The call exited 1. With the real `hub.cmd`, `main.py` would exit 64 (no `--mode`), and the stray command would then end the call with 1 ("failed"). Nothing ran, and `status` still shows the previous run. If `--url` comes last, the URL is cut at the `&` instead. That usually still captures the right video.
- **ADR conflict:** none with the ADR text, but any fix touches the `hub.cmd` contract. Per the hub rule, that goes through the data hub planning session.
- **Direction:** decide on one side of the boundary who quotes the URL (the data hub, or the contract), and add it to the contract.
- **Not verified:** how the data hub actually builds the command line. If it already quotes the URL, this can't happen.

### 2. `hub.cmd status` can crash a run that is finishing
- **Severity:** medium
- **Where:** `hub.py:197` (`os.replace` in `_write_state`), `hub.py:180` (`os.remove` in `release`), `hub.py:172` and `hub.py:188` (`status` opens the lock and state files); `hub.py:57` (`start` sits outside the `try`).
- **What's wrong:** on Windows, a file another process has open (through Python's `open()`) can't be replaced or deleted. While `status` has `yt-downloader.state.json` or `yt-downloader.lock` open, a run's `os.replace` fails with `PermissionError` (WinError 5) and its `os.remove` fails with WinError 32. Both were reproduced in a temp folder.
- **Why it matters:** the window is short, but the hub probably polls `status` while a run is busy, and the end of a run is when both writes happen.
  - If `finish` hits it (`hub.py:81`, `83`), the exception escapes. The exit code becomes 1, the "OK"/"NEEDS REVIEW" log line is never written, and `status` shows `last_result: null` with no attention: a run that looks unfinished but not interrupted.
  - If `release` hits it (`hub.py:86`), the error in `finally` replaces a 0 or 3 with exit 1. The lock is left behind, so the next `status` reports `interrupted` for a run that finished.
  - If `start` hits it (`hub.py:57`), the lock is never released by this process. The next status reads "interrupted".
- **ADR conflict:** none. ADR 0020 asks for atomic state writes, and they stay atomic. They just aren't safe against a reader on Windows.
- **Direction:** make the run-state writes retry briefly or tolerate a sharing error, and add a test that holds the file open.

### 3. Two runs starting together can both get the lock, or the refused one crashes
- **Severity:** medium
- **Where:** `hub.py:148-159` (`acquire`), `hub.py:174` (`_lock_owner_alive`); `.claude/rules/hub.md:14` ("two starts can't both win"); ADR 0020.
- **What's wrong:** two gaps.
  - When two runs both find a dead lock, both delete it (`hub.py:153`). If the faster run has already made and closed its new lock, the slower one deletes it and makes its own (`hub.py:155`). Both runs carry on. If the faster run hasn't made it yet, the slower one gets `FileNotFoundError`, which isn't caught: a traceback and exit 1 instead of 4.
  - `acquire` creates the lock file at `hub.py:148` and writes the PID only at `hub.py:159`. In between, the file is empty. A second run that reads it then gets `IndexError`, which `_lock_owner_alive` treats as "dead" (`hub.py:174`). It logs a false `INTERRUPTED` (`hub.py:152`) and tries to delete the lock (`hub.py:153`). On Windows that delete fails with `PermissionError` (WinError 32, reproduced in a temp folder) because the first run still has the file open, so the second run crashes with exit 1 instead of 4. `status` in the same window reports `interrupted` (`hub.py:138`).
- **Why it matters:** in the first gap, two captures of the same video write the same folder and the same state file at once. In the second, the log gets a false "interrupted" line and the refused run reports "failed" rather than "busy". Both windows are tiny, so they need two starts at nearly the same moment, for example a hub run and an interactive run.
- **ADR conflict:** none. A fix restores what ADR 0020 and the hub rule already claim.
- **Direction:** treat an empty or unreadable lock as busy, not dead, and make the stale-lock cleanup safe for two cleaners.

### 4. Re-runs leave old media in the folder
- **Severity:** medium
- **Where:** `video_folder.py:38-53` (`save` only cleans up `transcript.txt`); `README.md:21` ("Running the same video again replaces its folder's contents"); ADR 0019 line 11 ("re-runs overwrite everything in it").
- **What's wrong:** `overwrites` only replaces files with the same name, and `save` only removes a stale `transcript.txt`. Media the new run doesn't download stays.
- **Why it matters:** run `both`, then re-run the same video with `audio`. The folder still has the old `.mp4`, now older than `data.json`. Likewise, a first run that got `.webm` and a later one that got `.m4a` leaves both files. Code that reads the folder as "what the last capture produced" gets the wrong answer. The video-folder rule's goal ("so the folder matches `data.json`") only holds for the transcript.
- **ADR conflict:** none. Either the code or the docs can move; ADR 0019 says the code should.
- **Direction:** decide whether a re-run clears media it didn't download, then align the code or the README and rule.

### 5. A changed title starts a second folder for the same video
- **Severity:** low
- **Where:** `video_folder.py:18` (`NAME = '%(title)s [%(id)s]'`), `video_folder.py:29`; ADR 0006 line 14 ("The video ID keeps folder names unique"), carried into ADR 0019.
- **What's wrong:** the folder name holds the current title. If the uploader renames the video, a re-run writes to a new folder, and the old one stays with its own `data.json` and media.
- **Why it matters:** "one folder per video" stops holding. A reader looking up a video by ID has to search for `* [<id>]` and pick between two folders.
- **ADR conflict:** yes, partly. Naming folders by ID only would undo ADR 0019's `<title> [<id>]` folder name. Finding the existing folder by ID before saving would not.
- **Direction:** decide whether a renamed video should reuse its old folder.

### 6. Some run-state errors escape as tracebacks with exit 1
- **Severity:** low
- **Where:** `hub.py:148` (lock created in `logs_dir` without making the folder), `hub.py:186-191` (`_read_state` catches only `FileNotFoundError`), `hub.py:57`.
- **What's wrong:** if `Storage\_logs` is missing, `acquire` raises `FileNotFoundError`. If `yt-downloader.state.json` holds invalid JSON (a hand edit, a disk error), `status` raises `JSONDecodeError`. Neither is caught.
- **Why it matters:** the hub gets exit 1 ("failed") and a Python traceback instead of JSON from `status`, so it can't show the tool's state at all. A bad state file keeps `status` broken until a new run overwrites it.
- **ADR conflict:** none.
- **Direction:** decide what `status` reports when its own files are missing or unreadable.

### 7. `hub.cmd status` takes over a second because it loads yt-dlp
- **Severity:** low
- **Where:** `main.py:4-5` (imports `capture`, and so yt-dlp and mutagen, before routing at `main.py:17-18`).
- **What's wrong:** `status` and `log` only read small files, but every call imports the whole capture stack first. Measured here: `import hub` 0.02 s, `import capture` 1.3 s.
- **Why it matters:** if the hub polls `status` for a live view, each poll costs about 1.3 s of CPU and delay. It also widens the window in finding 2.
- **ADR conflict:** none. ADR 0012 keeps `main.py` small, and this doesn't change that.
- **Direction:** import `capture` only on the paths that run a capture.

### 8. Ctrl+C under `hub.cmd` can ask "Terminate batch job (Y/N)?"
- **Severity:** low
- **Where:** `hub.cmd:4-5`; ADR 0020 ("no prompts and no pause", exit 130 for Ctrl+C).
- **What's wrong:** when Ctrl+C reaches a console running a batch file, `cmd` asks "Terminate batch job (Y/N)?" after the child process ends. That's a prompt the contract rules out, and the final exit code then depends on the answer, not on `main.py`'s 130.
- **Why it matters:** only if the hub stops runs by sending Ctrl+C to a console. If it kills the process instead, the lock is left behind and the status reads "interrupted" (ADR 0020).
- **ADR conflict:** none, but a fix touches `hub.cmd` (the contract).
- **Not verified:** not reproduced here; this is standard `cmd` behaviour, and how the hub stops runs isn't known.
- **Direction:** confirm how the hub stops a run.

### 9. `main.py`'s routing has no test
- **Severity:** low
- **Where:** `main.py:17-18` and `main.py:21-27`; `.claude/rules/hub.md` invariant "Never prompt or pause when arguments are given".
- **What's wrong:** no test imports or runs `main.py`. The rule that any arguments skip `input()`, and that cookies come from `cookies.txt` next to `main.py` (ADR 0017), are only checked by reading. `main.py` runs on import, so it can't be tested without a subprocess.
- **Why it matters:** a change that moves an `input()` above line 17 would hang the hub (no console input) and pass every test.
- **ADR conflict:** none. ADR 0012 accepted an untested `main.py` when it held only prompts. It now also routes to the hub.
- **Direction:** add one subprocess test that runs `main.py status` with stdin closed.

### 10. `hub.main` and `run_capture` default to the real Storage folders
- **Severity:** low
- **Where:** `hub.py:29`, `hub.py:48` (`logs_dir=LOGS_DIR`, `downloads_dir=DOWNLOADS_DIR`); `.claude/rules/hub.md` ("Tests … must never fall back to the defaults"); ADR 0019, 0020.
- **What's wrong:** forgetting one keyword argument in a test writes to `Storage\_logs` (backed up) rather than failing. `capture()` does the opposite: `downloads_dir` is required (`capture.py:72`).
- **Why it matters:** the rule is enforced only by care. Every current test passes its own folders.
- **ADR conflict:** none.
- **Direction:** consider making the folders required, as in `capture()`, with `main.py` passing the real ones.

### 11. `data.json`'s `musicbrainz` field has an undocumented third state
- **Severity:** low
- **Where:** `capture.py:90-92`; ADR 0015 ("`musicbrainz` is then `null`"); `.claude/rules/music.md` ("Other projects read it").
- **What's wrong:** the field is missing when music wasn't requested or no audio was chosen, `null` when there was no confident match, and a match object otherwise. The docs only describe `null` and the object. `test_capture.py:146-161` tests the missing case, so it's on purpose.
- **Why it matters:** another project reading `data["musicbrainz"]` crashes on non-music captures. "Missing" (never asked) and `null` (asked, no match) also mean different things to a reader.
- **ADR conflict:** none. The music rule treats key changes as breaking, so the cheap fix is to document it.
- **Direction:** document the three states where other projects will look, for example `CONTEXT.md`'s "Music match".

### 12. Docs drift in a rule, a docstring and an ADR reference
- **Severity:** low
- **Where:**
  - `.claude/rules/capture.md:17` says yt-dlp errors "propagate to `main.py`, which prints them and exits 1". Since ADR 0020 they stop in `hub.run_capture` (`hub.py:64-68`), which logs them and records `failed`.
  - `capture.py:5`'s docstring gives `Outcome(status, folder, transcript_note, actions)`. It leaves out `transcript_found`, `music_tagged` and `music_note` (`capture.py:67-69`), the three fields the hub relies on for `needs_review`.
  - `.claude/rules/video-folder.md:12` cites ADR 0006 for re-runs overwriting. ADR 0006 is superseded by 0019.
- **Why it matters:** these are the first places someone reads before changing the error path or the `Outcome` fields, and they point the wrong way.
- **ADR conflict:** none. Rules and docstrings can change; ADRs stay as written (ADR 0014's references to 0006 are history and fine).
- **Direction:** update the rule, the docstring and the ADR reference.

## What's working
- **Seams are real.** `hub` gets `capture_fn` injected (`hub.py:29`), and `capture()` takes `ydl_factory`, `http_get` and `downloads_dir` (`capture.py:72-73`). All 69 tests run offline in about 3 s.
- **Save before download.** `data.json` and the transcript are written before any media (`capture.py:95-102`), so a 403 never loses metadata (ADR 0003, 0009).
- **One naming config.** Folder and media names share `NAME` and `naming_opts` (`video_folder.py:18`, `27-36`), and a test checks it under `restrictfilenames`.
- **Side steps can't sink a run.** Caption and MusicBrainz problems return notes, not errors (`transcript.py:41-47`, `music.py:41-44`, `music.py:57-65`), as ADR 0010 and the music rule require.
- **Hub contract matches ADR 0020.** `status` keys, exit codes, the `argparse` exit-64 override (`hub.py:103-106`) and the Windows-safe PID probe (`hub.py:200-217`) all match, and `test_hub.py` covers each exit code.

## Out of scope / not checked
- Real network runs and real `hub.cmd` calls (they write to the backed-up `Storage` folders).
- How the data hub calls `hub.cmd`: argument quoting, how often it polls, how it stops runs. That project wasn't read; findings 1, 2 and 8 depend on it.
- yt-dlp and mutagen behaviour and versions (`requirements.txt`, ADR 0009, 0018), and the shape of yt-dlp's own `data.json` fields.
- Transcript line-breaking quality and MusicBrainz match quality on real videos.
- The Windows path limit (already recorded in ADR 0007 and 0019) and `cookies.txt` (not opened).
- A security review.
