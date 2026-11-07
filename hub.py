"""Command line for the data hub: `hub.cmd run capture ...`, `hub.cmd status`, `hub.cmd log`.

    main(argv, *, capture_fn, logs_dir, downloads_dir, cookies_file, out) -> exit code
    run_capture(url, choice, as_music, *, ...) -> exit code   # also used by main.py's prompts

Run state lives in logs_dir (Storage/_logs, like Adam's other tools):
    yt-downloader.log         one line per event
    yt-downloader.lock        while a run is active: "<pid> <start time>"
    yt-downloader.state.json  {"last_run", "last_result", "attention"}
"""
import argparse
import datetime
import json
import os
import sys

TOOL = 'yt-downloader'

STORAGE = r'C:\Users\choua\Documents\Storage'
DOWNLOADS_DIR = os.path.join(STORAGE, 'Media', 'YouTube')
LOGS_DIR = os.path.join(STORAGE, '_logs')

# Exit codes shared by every tool the hub launches
EXIT_OK, EXIT_FAILED, EXIT_NEEDS_REVIEW, EXIT_BUSY, EXIT_USAGE, EXIT_INTERRUPTED = 0, 1, 3, 4, 64, 130

MODES = {'audio': 'a', 'video': 'v', 'both': 'b'}


def main(argv, *, capture_fn, logs_dir=LOGS_DIR, downloads_dir=DOWNLOADS_DIR, cookies_file=None, out=None):
    out = out or sys.stdout
    try:
        args = _Parser(prog='hub.cmd').parse(argv)
    except UsageError as e:
        print(f'hub.cmd: {e}', file=sys.stderr)
        return EXIT_USAGE
    state = RunState(logs_dir)
    if args.command == 'status':
        print(json.dumps(state.status()), file=out)
        return EXIT_OK
    if args.command == 'log':
        if os.path.exists(state.log_path):
            print(state.log_path, file=out)
        return EXIT_OK
    return run_capture(args.url, MODES[args.mode], args.music, capture_fn=capture_fn, logs_dir=logs_dir,
                       downloads_dir=downloads_dir, cookies_file=cookies_file, out=out)


def run_capture(url, choice, as_music, *, capture_fn, logs_dir=LOGS_DIR, downloads_dir=DOWNLOADS_DIR,
                cookies_file=None, out=None):
    """Capture one video under the run lock, recording the result. Returns an exit code."""
    out = out or sys.stdout
    state = RunState(logs_dir)
    mode = {v: k for k, v in MODES.items()}.get(choice, 'none')
    if not state.acquire():
        print('Another yt-downloader run is in progress; try again when it finishes.', file=out)
        return EXIT_BUSY
    state.start(f'started capture {url} mode={mode} music={"yes" if as_music else "no"}')
    try:
        try:
            outcome = capture_fn(url, choice, as_music=as_music, downloads_dir=downloads_dir, cookies_file=cookies_file)
        except KeyboardInterrupt:  # Ctrl+C
            state.finish('interrupted', ['the run was stopped with Ctrl+C'], f'INTERRUPTED capture {url}')
            return EXIT_INTERRUPTED
        except Exception as e:  # yt-dlp extraction/download errors: the run didn't finish
            reason = (str(e).strip().splitlines() or [type(e).__name__])[0][:300]
            print(f'Failed: {reason}', file=out)
            state.finish('failed', [reason], f'FAILED capture {url}: {reason}')
            return EXIT_FAILED
        if outcome.status != 'saved':
            print(f'Failed: {outcome.status}', file=out)
            state.finish('failed', [outcome.status], f'FAILED capture {url}: {outcome.status}')
            return EXIT_FAILED
        attention = _missing(outcome)
        name = os.path.basename(outcome.folder)
        print(f'\nSaved to: {outcome.folder}\nTranscript: {outcome.transcript_note}', file=out)
        for action in outcome.actions:
            print(f'  - {action}', file=out)
        for item in attention:
            print(f'Needs review: {item}', file=out)
        if attention:
            state.finish('needs_review', attention, f'NEEDS REVIEW capture {name}: {"; ".join(attention)}')
            return EXIT_NEEDS_REVIEW
        state.finish('ok', [], f'OK capture {name}')
        return EXIT_OK
    finally:
        state.release()


def _missing(outcome):
    # "needs review" = the run finished but something requested or expected is missing
    attention = []
    if not outcome.transcript_found:
        attention.append(f'no transcript: {outcome.transcript_note}')
    if outcome.music_tagged is False:
        attention.append(f'music not tagged: {outcome.music_note}')
    return attention


class UsageError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    # argparse normally exits with code 2 on bad arguments; the hub contract says 64
    def error(self, message):
        raise UsageError(message)

    def parse(self, argv):
        commands = self.add_subparsers(dest='command', required=True)
        commands.add_parser('status')
        commands.add_parser('log')
        run = commands.add_parser('run')
        actions = run.add_subparsers(dest='action', required=True)
        capture = actions.add_parser('capture')
        capture.add_argument('--url', required=True)
        capture.add_argument('--mode', required=True, choices=sorted(MODES))
        capture.add_argument('--music', action='store_true', help='tag the audio from MusicBrainz')
        args = self.parse_args(argv)
        if args.command == 'run' and args.music and args.mode == 'video':
            raise UsageError('--music needs --mode audio or both')
        return args


def _now():
    return datetime.datetime.now().astimezone()


class RunState:
    def __init__(self, logs_dir):
        self.log_path = os.path.join(logs_dir, f'{TOOL}.log')
        self.lock_path = os.path.join(logs_dir, f'{TOOL}.lock')
        self.state_path = os.path.join(logs_dir, f'{TOOL}.state.json')

    def status(self):
        saved = self._read_state()
        busy = self._lock_owner_alive()
        result, attention = saved.get('last_result'), saved.get('attention', [])
        if os.path.exists(self.lock_path) and not busy:  # the run's process died without finishing
            result, attention = 'interrupted', ['the last run stopped before finishing']
        return {'tool': TOOL, 'busy': busy, 'last_run': saved.get('last_run'),
                'last_result': result, 'attention': attention,
                'log': self.log_path if os.path.exists(self.log_path) else None}

    def acquire(self):
        # Create the lock atomically, so two runs starting together can't both get it.
        # False when another live process holds it; a dead process's lock is cleared first.
        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if self._lock_owner_alive():
                return False
            self.log('INTERRUPTED the previous run stopped before finishing')
            os.remove(self.lock_path)
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:  # another run grabbed it in between
                return False
        with os.fdopen(fd, 'w') as f:
            f.write(f'{os.getpid()} {_now().isoformat(timespec="seconds")}')
        return True

    def start(self, message):
        self._write_state({'last_run': _now().isoformat(timespec='seconds'), 'last_result': None, 'attention': []})
        self.log(message)

    def finish(self, result, attention, message):
        self._write_state({**self._read_state(), 'last_result': result, 'attention': attention})
        self.log(message)

    def _lock_owner_alive(self):
        try:
            with open(self.lock_path, encoding='utf-8') as f:
                pid = int(f.read().split()[0])
        except (FileNotFoundError, ValueError, IndexError):
            return False
        return _pid_alive(pid)

    def release(self):
        if os.path.exists(self.lock_path):
            os.remove(self.lock_path)

    def log(self, message):
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(f'{_now():%Y-%m-%d %H:%M:%S} {message}\n')

    def _read_state(self):
        try:
            with open(self.state_path, encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def _write_state(self, state):
        tmp = self.state_path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(state, f)
        os.replace(tmp, self.state_path)


def _pid_alive(pid):
    # Never os.kill(pid, 0) on Windows: there it terminates the process instead of probing it.
    if os.name != 'nt':
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    import ctypes
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return ctypes.get_last_error() == 5  # access denied: it exists, owned by someone else
    try:
        code = ctypes.c_ulong()
        return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259  # STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)
