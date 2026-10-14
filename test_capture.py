import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest

import yt_dlp
from mutagen.mp4 import MP4
from yt_dlp.networking.exceptions import RequestError

from capture import capture

SRT = '1\n00:00:01,000 --> 00:00:03,000\nAll my life I been this way.\n'
VIDEO = {
    'id': 'SONG001', 'title': 'Sins Of The Father', 'duration': 471,
    'track': 'Sins Of The Father', 'artist': 'Daniel Caesar',  # YouTube's own music fields
    'comments': [{'id': 'c1', 'like_count': 5}, {'id': 'c2', 'like_count': 812}],
    'subtitles': {}, 'automatic_captions': {'en-orig': [{'ext': 'srt', 'url': 'en-orig.srt'}]},
}
MB_RECORDING = {
    'id': 'rec-1', 'title': 'Sins Of The Father', 'length': 470000, 'isrcs': [],
    'artist-credit': [{'name': 'Daniel Caesar', 'artist': {'id': 'id-dc', 'name': 'Daniel Caesar'}}],
    'releases': [{'id': 'r1', 'title': 'Son Of Spergy', 'date': '2025-10-24', 'status': 'Official',
                  'release-group': {'id': 'rg1', 'primary-type': 'Album'},
                  'artist-credit': [{'name': 'Daniel Caesar', 'artist': {'id': 'id-dc', 'name': 'Daniel Caesar'}}],
                  'media': [{'position': 1, 'track-count': 12, 'track': [{'number': '12'}]}]}],
}


class FakeYoutubeDL:
    """Stands in for yt_dlp.YoutubeDL with the methods capture() uses; records each call and its options."""

    def __init__(self, calls, opts, *, playlist=False, captions_fail=False, audio_sample=None):
        self.calls, self.opts = calls, opts
        self.playlist, self.captions_fail, self.audio_sample = playlist, captions_fail, audio_sample
        calls.append(('opts', opts))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download=False, process=True):
        if download:
            return {**VIDEO, 'requested_downloads': [{'filepath': self.download([url])}]}
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
        # Write a stand-in file (a real .m4a when given one) where the real download would land
        ext = 'm4a' if self.opts['format'].startswith('bestaudio') else 'mp4'
        self.calls.append(f'download {ext}')
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            path = ydl.prepare_filename({**VIDEO, 'ext': ext}, outtmpl=self.opts['outtmpl'])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if ext == 'm4a' and self.audio_sample:
            shutil.copy(self.audio_sample, path)
        else:
            open(path, 'w').close()
        return path


class FakeHttp:
    # Stands in for music.http_get: MusicBrainz JSON or cover bytes; records URLs
    def __init__(self):
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        if 'coverartarchive.org' in url:
            return b'\xff\xd8\xff\xe0 album cover \xff\xd9'
        return json.dumps({'recordings': [MB_RECORDING]}).encode('utf-8')


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='test-downloads-')
        self.calls, self.http = [], FakeHttp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def capture(self, choice, *, as_music=False, cookies_file=None, **fake):
        return capture('https://www.youtube.com/watch?v=SONG001', choice, as_music=as_music,
                       downloads_dir=self.root, http_get=self.http, cookies_file=cookies_file,
                       ydl_factory=lambda opts: FakeYoutubeDL(self.calls, opts, **fake))

    def files(self):
        return {f for _, _, names in os.walk(self.root) for f in names}

    def steps(self):
        return [c for c in self.calls if isinstance(c, str)]

    def data(self, outcome):
        with open(os.path.join(outcome.folder, 'data.json')) as f:
            return json.load(f)

    def test_saves_metadata_transcript_audio_and_video_in_one_folder(self):
        outcome = self.capture('b')
        self.assertEqual(outcome.status, 'saved')
        self.assertEqual(os.listdir(self.root), ['Sins Of The Father [SONG001]'])
        self.assertEqual(self.files(), {'data.json', 'transcript.txt',
                                        'Sins Of The Father [SONG001].m4a', 'Sins Of The Father [SONG001].mp4'})

    def test_saved_comments_are_most_liked_first_and_transcript_is_included(self):
        data = self.data(self.capture('n'))
        self.assertEqual([c['like_count'] for c in data['comments']], [812, 5])
        self.assertEqual(data['transcript']['source'], 'auto')

    def test_media_downloads_re_extract_the_url_fresh(self):
        self.capture('a')
        self.assertEqual(self.steps(), ['peek', 'metadata', 'captions', 'download m4a'])

    def test_a_playlist_is_rejected_after_the_peek_without_writing_anything(self):
        outcome = self.capture('b', playlist=True)
        self.assertTrue(outcome.status.startswith('rejected'))
        self.assertEqual((self.steps(), os.listdir(self.root)), (['peek'], []))

    def test_a_failed_caption_download_still_saves_the_metadata(self):
        outcome = self.capture('n', captions_fail=True)
        self.assertIsNone(self.data(outcome)['transcript'])
        self.assertIn('network down', outcome.transcript_note)

    def test_an_unrecognised_choice_downloads_no_media(self):
        outcome = self.capture('x')
        self.assertEqual(self.files(), {'data.json', 'transcript.txt'})
        self.assertIn('no media selected', outcome.actions)

    def test_without_music_nothing_is_looked_up(self):
        data = self.data(self.capture('a'))
        self.assertNotIn('musicbrainz', data)
        self.assertEqual(self.http.urls, [])

    def test_music_without_audio_is_not_looked_up(self):
        data = self.data(self.capture('v', as_music=True))
        self.assertNotIn('musicbrainz', data)
        self.assertEqual(self.http.urls, [])

    def test_a_cookies_file_is_used_for_every_yt_dlp_call(self):
        self.capture('b', cookies_file='C:/cookies.txt')
        option_sets = [opts for kind, opts in (c for c in self.calls if isinstance(c, tuple))]
        self.assertEqual([opts.get('cookiefile') for opts in option_sets], ['C:/cookies.txt'] * 3)

    def test_no_cookies_file_means_no_cookies(self):
        self.capture('b')
        option_sets = [opts for kind, opts in (c for c in self.calls if isinstance(c, tuple))]
        self.assertTrue(all('cookiefile' not in opts for opts in option_sets))


@unittest.skipUnless(shutil.which('ffmpeg'), 'needs ffmpeg to create a sample .m4a')
class MusicCaptureTests(CaptureTests.__base__):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='test-downloads-')
        self.sample = os.path.join(self.root, 'sample.m4a')
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=duration=1', '-c:a', 'aac', self.sample], check=True)
        self.calls, self.http = [], FakeHttp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_music_saves_the_match_in_data_json_and_tags_the_audio(self):
        outcome = capture('https://www.youtube.com/watch?v=SONG001', 'a', as_music=True, downloads_dir=self.root,
                          http_get=self.http, ydl_factory=lambda opts: FakeYoutubeDL(self.calls, opts, audio_sample=self.sample))
        with open(os.path.join(outcome.folder, 'data.json')) as f:
            self.assertEqual(json.load(f)['musicbrainz']['album'], 'Son Of Spergy')
        tags = MP4(os.path.join(outcome.folder, 'Sins Of The Father [SONG001].m4a')).tags
        self.assertEqual((tags['\xa9alb'], tags['trkn']), (['Son Of Spergy'], [(12, 12)]))
        self.assertTrue(any('Son Of Spergy' in a for a in outcome.actions))


if __name__ == '__main__':
    unittest.main()
