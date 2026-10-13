import io
import json
import os
import shutil
import tempfile
import unittest

import yt_dlp
from yt_dlp.networking.exceptions import RequestError

from capture import capture

SRT = '1\n00:00:01,000 --> 00:00:03,000\nAll my life I been this way.\n'
VIDEO = {
    'id': 'SONG001', 'title': 'Sins Of The Father', 'duration': 471,
    'comments': [{'id': 'c1', 'like_count': 5}, {'id': 'c2', 'like_count': 812}],
    'subtitles': {}, 'automatic_captions': {'en-orig': [{'ext': 'srt', 'url': 'en-orig.srt'}]},
}


class FakeYoutubeDL:
    """Stands in for yt_dlp.YoutubeDL with the methods capture() uses; records each call."""

    def __init__(self, calls, opts, *, playlist=False, captions_fail=False):
        self.calls, self.opts = calls, opts
        self.playlist, self.captions_fail = playlist, captions_fail

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download=False, process=True):
        self.calls.append('peek')
        return {'_type': 'playlist'} if self.playlist else {'_type': 'url', 'id': VIDEO['id']}

    def process_ie_result(self, result, download=False):
        self.calls.append('metadata')
        return json.loads(json.dumps(VIDEO))

    def urlopen(self, url):
        self.calls.append('captions')
        if self.captions_fail:
            raise RequestError('network down')
        return io.BytesIO(SRT.encode('utf-8'))

    def download(self, urls):
        # Write a stand-in file where the real download would land
        ext = 'm4a' if self.opts['format'].startswith('bestaudio') else 'mp4'
        self.calls.append(f'download {ext}')
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            path = ydl.prepare_filename({**VIDEO, 'ext': ext}, outtmpl=self.opts['outtmpl'])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'w').close()


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='test-downloads-')
        self.calls = []

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def capture(self, choice, **fake):
        return capture('https://www.youtube.com/watch?v=SONG001', choice, downloads_dir=self.root,
                       ydl_factory=lambda opts: FakeYoutubeDL(self.calls, opts, **fake))

    def files(self):
        return {f for _, _, names in os.walk(self.root) for f in names}

    def test_saves_metadata_transcript_audio_and_video_in_one_folder(self):
        outcome = self.capture('b')
        self.assertEqual(outcome.status, 'saved')
        self.assertEqual(os.listdir(self.root), ['Sins Of The Father [SONG001]'])
        self.assertEqual(self.files(), {'data.json', 'transcript.txt',
                                        'Sins Of The Father [SONG001].m4a', 'Sins Of The Father [SONG001].mp4'})

    def test_saved_comments_are_most_liked_first_and_transcript_is_included(self):
        outcome = self.capture('n')
        data = json.load(open(os.path.join(outcome.folder, 'data.json')))
        self.assertEqual([c['like_count'] for c in data['comments']], [812, 5])
        self.assertEqual(data['transcript']['source'], 'auto')

    def test_media_downloads_re_extract_the_url_fresh(self):
        self.capture('a')
        self.assertEqual(self.calls, ['peek', 'metadata', 'captions', 'download m4a'])

    def test_a_playlist_is_rejected_after_the_peek_without_writing_anything(self):
        outcome = self.capture('b', playlist=True)
        self.assertTrue(outcome.status.startswith('rejected'))
        self.assertEqual((self.calls, os.listdir(self.root)), (['peek'], []))

    def test_a_failed_caption_download_still_saves_the_metadata(self):
        outcome = self.capture('n', captions_fail=True)
        data = json.load(open(os.path.join(outcome.folder, 'data.json')))
        self.assertIsNone(data['transcript'])
        self.assertIn('network down', outcome.transcript_note)

    def test_an_unrecognised_choice_downloads_no_media(self):
        outcome = self.capture('x')
        self.assertEqual(self.files(), {'data.json', 'transcript.txt'})
        self.assertIn('no media selected', outcome.actions)


if __name__ == '__main__':
    unittest.main()
