import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import hub
from capture import Outcome


class FakeCapture:
    # Stands in for capture.capture: returns a preset Outcome (or raises) and records each call
    def __init__(self, outcome=None, error=None):
        self.outcome = outcome or Outcome('saved', 'C:/x/Song [ID]', '12 caption pieces', ['wrote data.json'],
                                          transcript_found=True)
        self.error, self.calls = error, []

    def __call__(self, url, choice, **kwargs):
        self.calls.append((url, choice, kwargs))
        if self.error:
            raise self.error
        return self.outcome


class HubTests(unittest.TestCase):
    def setUp(self):
        self.logs = tempfile.mkdtemp(prefix='test-logs-')
        self.capture = FakeCapture()

    def tearDown(self):
        shutil.rmtree(self.logs, ignore_errors=True)

    def hub(self, *argv):
        out = io.StringIO()
        code = hub.main(list(argv), capture_fn=self.capture, logs_dir=self.logs,
                        downloads_dir='C:/downloads', cookies_file=None, out=out)
        return code, out.getvalue()

    def status(self):
        code, text = self.hub('status')
        self.assertEqual(code, 0)
        return json.loads(text)

    def test_status_before_any_run(self):
        self.assertEqual(self.status(), {'tool': 'yt-downloader', 'busy': False, 'last_run': None,
                                         'last_result': None, 'attention': [], 'log': None})

    def test_a_complete_run_exits_0_and_status_shows_ok(self):
        code, _ = self.hub('run', 'capture', '--url', 'https://youtu.be/x', '--mode', 'both', '--music')
        self.assertEqual(code, 0)
        self.assertEqual(self.capture.calls, [('https://youtu.be/x', 'b', {'as_music': True, 'downloads_dir': 'C:/downloads',
                                                                           'cookies_file': None})])
        status = self.status()
        self.assertEqual((status['busy'], status['last_result'], status['attention']), (False, 'ok', []))
        self.assertTrue(status['last_run'])
        self.assertEqual(status['log'], os.path.join(self.logs, 'yt-downloader.log'))
        with open(status['log'], encoding='utf-8') as f:
            lines = f.read().splitlines()
        self.assertIn('started capture https://youtu.be/x mode=both music=yes', lines[0])
        self.assertIn('OK capture', lines[-1])
        self.assertFalse(os.path.exists(os.path.join(self.logs, 'yt-downloader.lock')))

    def test_a_missing_transcript_needs_review(self):
        self.capture = FakeCapture(Outcome('saved', 'C:/x/Song [ID]', 'no English captions', [], transcript_found=False))
        code, _ = self.hub('run', 'capture', '--url', 'u', '--mode', 'audio')
        self.assertEqual(code, 3)
        status = self.status()
        self.assertEqual(status['last_result'], 'needs_review')
        self.assertEqual(status['attention'], ['no transcript: no English captions'])

    def test_music_that_was_not_tagged_needs_review(self):
        self.capture = FakeCapture(Outcome('saved', 'C:/x/Song [ID]', '12 caption pieces', [], transcript_found=True,
                                           music_tagged=False,
                                           music_note='no confident MusicBrainz match for "Song" by X'))
        code, _ = self.hub('run', 'capture', '--url', 'u', '--mode', 'audio', '--music')
        self.assertEqual(code, 3)
        self.assertEqual(self.status()['attention'],
                         ['music not tagged: no confident MusicBrainz match for "Song" by X'])


    def test_an_error_fails_the_run_with_the_reason_and_releases_the_lock(self):
        self.capture = FakeCapture(error=RuntimeError('ERROR: unable to download video data: HTTP Error 403: Forbidden\nmore detail'))
        code, _ = self.hub('run', 'capture', '--url', 'u', '--mode', 'audio')
        self.assertEqual(code, 1)
        status = self.status()
        self.assertEqual((status['last_result'], status['busy']), ('failed', False))
        self.assertEqual(status['attention'], ['ERROR: unable to download video data: HTTP Error 403: Forbidden'])
        self.assertFalse(os.path.exists(os.path.join(self.logs, 'yt-downloader.lock')))
        with open(status['log'], encoding='utf-8') as f:
            self.assertIn('FAILED capture u: ERROR: unable to download video data', f.read().splitlines()[-1])

    def test_a_rejected_playlist_fails_the_run(self):
        self.capture = FakeCapture(Outcome('rejected: that URL is a playlist'))
        code, _ = self.hub('run', 'capture', '--url', 'u', '--mode', 'both')
        self.assertEqual(code, 1)
        self.assertEqual(self.status()['attention'], ['rejected: that URL is a playlist'])


    def lock_held_by(self, pid):
        with open(os.path.join(self.logs, 'yt-downloader.lock'), 'w') as f:
            f.write(f'{pid} 2026-11-07T10:00:00-05:00')

    def test_a_second_run_during_a_live_one_is_refused_with_4(self):
        self.lock_held_by(os.getpid())  # this test process is alive
        self.assertTrue(self.status()['busy'])
        code, _ = self.hub('run', 'capture', '--url', 'u', '--mode', 'audio')
        self.assertEqual((code, self.capture.calls), (4, []))
        self.assertTrue(os.path.exists(os.path.join(self.logs, 'yt-downloader.lock')))


    def dead_pid(self):
        process = subprocess.Popen([sys.executable, '-c', 'pass'])
        process.wait()
        return process.pid

    def test_a_lock_left_by_a_dead_process_means_interrupted(self):
        self.hub('run', 'capture', '--url', 'u', '--mode', 'audio')  # an earlier run that finished
        self.lock_held_by(self.dead_pid())                             # then one that was killed
        status = self.status()
        self.assertEqual((status['busy'], status['last_result']), (False, 'interrupted'))
        self.assertEqual(status['attention'], ['the last run stopped before finishing'])

    def test_a_new_run_clears_a_dead_process_lock(self):
        self.lock_held_by(self.dead_pid())
        code, _ = self.hub('run', 'capture', '--url', 'u', '--mode', 'audio')
        self.assertEqual(code, 0)
        self.assertEqual(self.status()['last_result'], 'ok')


    def test_ctrl_c_during_a_run_exits_130_and_records_interrupted(self):
        self.capture = FakeCapture(error=KeyboardInterrupt())
        code, _ = self.hub('run', 'capture', '--url', 'u', '--mode', 'audio')
        self.assertEqual(code, 130)
        status = self.status()
        self.assertEqual((status['busy'], status['last_result']), (False, 'interrupted'))
        self.assertFalse(os.path.exists(os.path.join(self.logs, 'yt-downloader.lock')))


    def test_bad_arguments_exit_64_without_running(self):
        for argv in (['run', 'capture', '--mode', 'audio'],                       # no --url
                     ['run', 'capture', '--url', 'u', '--mode', 'mp3'],           # unknown mode
                     ['run', 'capture', '--url', 'u', '--mode', 'video', '--music'],  # music needs audio
                     ['run', 'transcode', '--url', 'u'],                          # unknown action
                     ['frobnicate']):
            with self.subTest(argv=argv):
                code, _ = self.hub(*argv)
                self.assertEqual(code, 64)
        self.assertEqual(self.capture.calls, [])


    def test_log_prints_nothing_before_any_run_then_the_log_path(self):
        self.assertEqual(self.hub('log'), (0, ''))
        self.hub('run', 'capture', '--url', 'u', '--mode', 'audio')
        self.assertEqual(self.hub('log'), (0, os.path.join(self.logs, 'yt-downloader.log') + '\n'))


    def test_a_run_prints_a_summary_for_terminal_use(self):
        self.capture = FakeCapture(Outcome('saved', 'C:/x/Song [ID]', 'no English captions', ['wrote data.json'],
                                           transcript_found=False))
        _, text = self.hub('run', 'capture', '--url', 'u', '--mode', 'audio')
        self.assertEqual(text.splitlines()[-4:], ['Saved to: C:/x/Song [ID]', 'Transcript: no English captions',
                                                  '  - wrote data.json', 'Needs review: no transcript: no English captions'])


if __name__ == '__main__':
    unittest.main()
