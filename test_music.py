import json
import os
import shutil
import subprocess
import tempfile
import unittest
import urllib.parse

from mutagen.mp4 import MP4

import music

JPEG = b'\xff\xd8\xff\xe0 fake cover \xff\xd9'


def release(rid, title, date, *, status='Official', primary='Album', secondary=None, track='12', track_count=12,
            position=1, artist='Daniel Caesar'):
    group = {'id': f'rg-{rid}', 'primary-type': primary}
    if secondary:
        group['secondary-types'] = secondary
    return {'id': rid, 'title': title, 'date': date, 'status': status, 'release-group': group,
            'artist-credit': [{'name': artist, 'artist': {'id': 'id-dc', 'name': artist}}],
            'media': [{'position': position, 'track-count': track_count, 'track': [{'id': f't-{rid}', 'number': track}]}]}


def recording(releases, *, title='Sins Of The Father', length=470000):
    return {'id': 'rec-1', 'score': 100, 'title': title, 'length': length, 'isrcs': ['USUM72512345'],
            'artist-credit': [{'name': 'Daniel Caesar', 'joinphrase': ' & ', 'artist': {'id': 'id-dc', 'name': 'Daniel Caesar'}},
                              {'name': 'Bon Iver', 'artist': {'id': 'id-bi', 'name': 'Bon Iver'}}],
            'releases': releases}


class FakeHttp:
    # The http_get(url) -> bytes seam: serves MusicBrainz JSON and cover bytes, records URLs
    def __init__(self, recordings=(), cover=JPEG, error=None):
        self.recordings, self.cover, self.error, self.urls = list(recordings), cover, error, []

    def __call__(self, url):
        self.urls.append(url)
        if self.error:
            raise self.error
        if 'coverartarchive.org' in url:
            if isinstance(self.cover, Exception):
                raise self.cover
            return self.cover
        return json.dumps({'recordings': self.recordings}).encode('utf-8')

    def query(self):
        return urllib.parse.unquote_plus(self.urls[0])


VIDEO = {'title': 'Daniel Caesar - Sins Of The Father feat. Bon Iver (Official Lyric Video)',
         'uploader': 'Daniel Caesar', 'duration': 471}


class LookupTests(unittest.TestCase):
    def test_reads_artist_and_song_from_the_video_title(self):
        http = FakeHttp([recording([release('r1', 'Son Of Spergy', '2025-10-24')])])
        music.lookup(VIDEO, http)
        self.assertIn('recording:"Sins Of The Father"', http.query())
        self.assertIn('artist:"Daniel Caesar"', http.query())

    def test_prefers_youtubes_own_track_and_artist_fields(self):
        http = FakeHttp([recording([release('r1', 'Son Of Spergy', '2025-10-24')])])
        music.lookup({**VIDEO, 'title': 'something else entirely', 'track': 'Sins Of The Father',
                      'artists': ['Daniel Caesar', 'Bon Iver']}, http)
        self.assertIn('recording:"Sins Of The Father"', http.query())

    def test_a_confident_match_gives_album_track_and_ids(self):
        match, note = music.lookup(VIDEO, FakeHttp([recording([release('r1', 'Son Of Spergy', '2025-10-24')])]))
        self.assertEqual(match, {
            'recording_id': 'rec-1', 'title': 'Sins Of The Father', 'artist': 'Daniel Caesar & Bon Iver',
            'artist_ids': ['id-dc', 'id-bi'], 'isrcs': ['USUM72512345'],
            'release_id': 'r1', 'release_group_id': 'rg-r1', 'album': 'Son Of Spergy', 'album_artist': 'Daniel Caesar',
            'album_artist_ids': ['id-dc'], 'date': '2025-10-24', 'track': 12, 'track_count': 12, 'disc': 1,
        })
        self.assertIn('Son Of Spergy', note)

    def test_a_length_more_than_10_seconds_off_is_not_confident(self):
        match, note = music.lookup(VIDEO, FakeHttp([recording([release('r1', 'A', '2025')], length=482000)]))
        self.assertIsNone(match)
        self.assertIn('no confident', note)

    def test_a_different_song_title_is_not_confident(self):
        match, _ = music.lookup(VIDEO, FakeHttp([recording([release('r1', 'A', '2025')], title='Sins Of The Mother')]))
        self.assertIsNone(match)

    def test_picks_the_earliest_official_album_over_an_earlier_single_and_compilations(self):
        releases = [release('single', 'Sins Of The Father', '2025-06-01', primary='Single'),
                    release('comp', 'Hits 2026', '2025-01-01', secondary=['Compilation']),
                    release('deluxe', 'Son Of Spergy (Deluxe)', '2026-02-01'),
                    release('album', 'Son Of Spergy', '2025-10-24'),
                    release('bootleg', 'Live', '2024-01-01', status='Bootleg')]
        match, _ = music.lookup(VIDEO, FakeHttp([recording(releases)]))
        self.assertEqual(match['release_id'], 'album')

    def test_without_an_album_uses_the_earliest_official_release(self):
        releases = [release('later', 'Sins (Remixes)', '2025-09-01', primary='EP'),
                    release('single', 'Sins Of The Father', '2025-06-01', primary='Single')]
        match, _ = music.lookup(VIDEO, FakeHttp([recording(releases)]))
        self.assertEqual(match['release_id'], 'single')

    def test_without_an_album_a_single_beats_an_earlier_compilation(self):
        releases = [release('comp', 'Hits 2025', '2025-01-01', secondary=['Compilation']),
                    release('single', 'Sins Of The Father', '2025-06-01', primary='Single')]
        match, _ = music.lookup(VIDEO, FakeHttp([recording(releases)]))
        self.assertEqual(match['release_id'], 'single')

    def test_looks_past_a_recording_that_only_appears_on_compilations(self):
        # Real case ("Earrings" by Malcolm Todd): the first confident recording is only on a
        # "Now That's What I Call Music!" compilation; the second is on the artist's own mixtape
        on_compilation = {**recording([release('comp', 'Now 124', '2026-07-31', secondary=['Compilation'])]), 'id': 'rec-comp'}
        on_mixtape = {**recording([release('mix', 'Sweet Boy', '2024-04-05', secondary=['Mixtape/Street'])]), 'id': 'rec-mix'}
        match, _ = music.lookup(VIDEO, FakeHttp([on_compilation, on_mixtape]))
        self.assertEqual((match['release_id'], match['recording_id']), ('mix', 'rec-mix'))

    def test_a_failed_lookup_means_no_match_instead_of_an_error(self):
        match, note = music.lookup(VIDEO, FakeHttp(error=OSError('network down')))
        self.assertIsNone(match)
        self.assertIn('network down', note)


@unittest.skipUnless(shutil.which('ffmpeg'), 'needs ffmpeg to create a sample .m4a')
class TagAudioTests(unittest.TestCase):
    MATCH = {'recording_id': 'rec-1', 'title': 'Sins Of The Father', 'artist': 'Daniel Caesar & Bon Iver',
             'artist_ids': ['id-dc', 'id-bi'], 'isrcs': ['USUM72512345'], 'release_id': 'r1',
             'release_group_id': 'rg-r1', 'album': 'Son Of Spergy', 'album_artist': 'Daniel Caesar',
             'album_artist_ids': ['id-dc'], 'date': '2025-10-24', 'track': 12, 'track_count': 12, 'disc': 1}

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='test-music-')
        self.path = os.path.join(self.dir, 'song.m4a')
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=duration=1', '-c:a', 'aac', self.path], check=True)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def freeform(self, tags, name):
        return [bytes(v).decode('utf-8') for v in tags[f'----:com.apple.iTunes:{name}']]

    def test_writes_song_album_numbers_and_musicbrainz_ids(self):
        music.tag_audio(self.path, self.MATCH, FakeHttp())
        tags = MP4(self.path).tags
        self.assertEqual((tags['\xa9nam'], tags['\xa9ART'], tags['\xa9alb'], tags['aART'], tags['\xa9day']),
                         (['Sins Of The Father'], ['Daniel Caesar & Bon Iver'], ['Son Of Spergy'], ['Daniel Caesar'], ['2025-10-24']))
        self.assertEqual((tags['trkn'], tags['disk']), ([(12, 12)], [(1, 0)]))
        self.assertEqual(self.freeform(tags, 'MusicBrainz Track Id'), ['rec-1'])
        self.assertEqual(self.freeform(tags, 'MusicBrainz Album Id'), ['r1'])
        self.assertEqual(self.freeform(tags, 'MusicBrainz Artist Id'), ['id-dc', 'id-bi'])
        self.assertEqual(self.freeform(tags, 'ISRC'), ['USUM72512345'])

    def test_replaces_the_cover_with_the_album_art(self):
        http = FakeHttp()
        music.tag_audio(self.path, self.MATCH, http)
        self.assertEqual(bytes(MP4(self.path).tags['covr'][0]), JPEG)
        self.assertIn('coverartarchive.org/release/r1/front-500', http.urls[0])

    def test_keeps_the_tags_when_no_album_art_is_available(self):
        note = music.tag_audio(self.path, self.MATCH, FakeHttp(cover=OSError('404')))
        tags = MP4(self.path).tags
        self.assertEqual(tags['\xa9alb'], ['Son Of Spergy'])
        self.assertNotIn('covr', tags)
        self.assertIn('no album art', note)

    def test_leaves_other_formats_alone(self):
        path = os.path.join(self.dir, 'song.webm')
        with open(path, 'wb') as f:
            f.write(b'not an m4a')
        note = music.tag_audio(path, self.MATCH, FakeHttp())
        with open(path, 'rb') as f:
            self.assertEqual(f.read(), b'not an m4a')
        self.assertIn('.m4a', note)


if __name__ == '__main__':
    unittest.main()
