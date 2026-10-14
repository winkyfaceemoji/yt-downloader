"""Identify a downloaded video as a song on MusicBrainz, and tag its audio file.

The whole interface:
    lookup(info, http_get) -> (match | None, note)
    tag_audio(path, match, http_get) -> note
    http_get(url) -> bytes      # production adapter: MusicBrainz User-Agent, 1 request/second

`http_get` is the seam: tests pass a stand-in. Neither function raises for network or
data problems: a failed or unsure lookup is "no match", and a failed tag/cover step
leaves the file as yt-dlp wrote it. Only confident matches are used: the song title and
an artist must match, and the length must be within MAX_LENGTH_GAP seconds.
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

from mutagen.mp4 import MP4, MP4Cover, MP4FreeForm

__all__ = ['lookup', 'tag_audio', 'http_get']

# MusicBrainz asks every client for a name, version and contact; the repo URL is the contact.
USER_AGENT = 'yt-downloader/1.0 ( https://github.com/winkyfaceemoji/yt-downloader )'
MAX_LENGTH_GAP = 10  # seconds between the video and the MusicBrainz recording

_BRACKETS = re.compile(r'\s*[\(\[][^)\]]*[\)\]]')                  # "(Official Video)", "[4K]"
_FEATURING = re.compile(r'\s+(feat\.?|ft\.?|featuring)\s.*$', re.IGNORECASE)
_UPLOADER_NOISE = re.compile(r'(\s*-\s*topic|vevo)$', re.IGNORECASE)
_last_request = 0.0


def lookup(info, http_get):
    """Find the song on MusicBrainz: (match dict | None, note)."""
    artist, song = _artist_and_song(info)
    if not (artist and song):
        return None, "couldn't tell the artist and song from the video"
    query = f'recording:"{_quote(song)}" AND artist:"{_quote(artist)}"'
    url = 'https://musicbrainz.org/ws/2/recording?fmt=json&limit=5&query=' + urllib.parse.quote(query)
    try:
        recordings = json.loads(http_get(url))['recordings']
    except Exception as e:  # network, HTTP or JSON trouble: the run carries on without it
        return None, f'MusicBrainz lookup failed ({e})'
    confident = [r for r in recordings if _confident(r, artist, song, info.get('duration'))]
    if not confident:
        return None, f'no confident MusicBrainz match for "{song}" by {artist}'
    match = _match(*_pick_release(confident))
    on = f' on {match["album"]}' if match['album'] else ''
    return match, f'matched "{match["title"]}" by {match["artist"]}{on}'


def tag_audio(path, match, http_get):
    """Write the match into an .m4a's tags, with album art when available. Returns a note."""
    if not path.lower().endswith('.m4a'):
        return f'MusicBrainz tags need an .m4a file; left {os.path.basename(path)} as is'
    try:
        audio = MP4(path)
        if audio.tags is None:
            audio.add_tags()
        _write_tags(audio.tags, match)
        cover_note = _write_cover(audio.tags, match, http_get)
        audio.save()
    except Exception as e:  # a tagging problem must not cost the download
        return f"couldn't tag the audio ({e})"
    return 'tagged with MusicBrainz data' + cover_note


def http_get(url):
    """Production adapter: GET with MusicBrainz's required User-Agent, at most 1 request/second."""
    global _last_request
    wait = 1.0 - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def _artist_and_song(info):
    # YouTube's own music fields win (official uploads); otherwise "Artist - Song" in the title;
    # otherwise the channel name and the whole title.
    if info.get('track') and (info.get('artists') or info.get('artist')):
        return (info.get('artists') or [info['artist']])[0], _clean(info['track'])
    title = info.get('title') or ''
    if ' - ' in title:
        artist, song = title.split(' - ', 1)
        return _clean(artist), _clean(song)
    return _UPLOADER_NOISE.sub('', info.get('uploader') or '').strip(), _clean(title)


def _clean(text):
    return _FEATURING.sub('', _BRACKETS.sub('', text)).strip(' -')


def _norm(text):
    text = re.sub(r'[^\w\s]', '', text.casefold().replace('&', 'and'))
    return ' '.join(text.split())


def _quote(text):
    return text.replace('\\', '\\\\').replace('"', '\\"')


def _confident(recording, artist, song, duration):
    credited = {_norm(c['name']) for c in recording.get('artist-credit', [])}
    length = recording.get('length')
    return (_norm(_clean(recording.get('title', ''))) == _norm(song)
            and _norm(artist) in credited
            and duration is not None and length is not None
            and abs(length / 1000 - duration) <= MAX_LENGTH_GAP)


def _credit(credits):
    return ''.join(c['name'] + (c.get('joinphrase') or '') for c in credits)


def _pick_release(recordings):
    # Across every confident recording (one song can have several, e.g. the album version
    # and a compilation's copy), pick the official release ranked best, earliest first:
    #   1. a studio album (album type, no secondary type like Compilation, Live, Mixtape)
    #   2. any other release that isn't a compilation (mixtape, single, EP, ...)
    #   3. a compilation
    # Returns (recording, release); release is None when nothing official exists.
    def rank(candidate):
        group = candidate[1].get('release-group') or {}
        secondary = group.get('secondary-types') or []
        tier = 0 if group.get('primary-type') == 'Album' and not secondary else 1 if 'Compilation' not in secondary else 2
        return tier, candidate[1].get('date') or '9999'
    candidates = [(rec, rel) for rec in recordings for rel in rec.get('releases', []) if rel.get('status') == 'Official']
    return min(candidates, key=rank) if candidates else (recordings[0], None)


def _match(recording, release):
    credits = recording.get('artist-credit', [])
    match = {'recording_id': recording['id'], 'title': recording['title'], 'artist': _credit(credits),
             'artist_ids': [c['artist']['id'] for c in credits], 'isrcs': recording.get('isrcs', []),
             'release_id': None, 'release_group_id': None, 'album': None, 'album_artist': None,
             'album_artist_ids': [], 'date': None, 'track': None, 'track_count': None, 'disc': None}
    if release:
        medium = (release.get('media') or [{}])[0]
        number = ((medium.get('track') or [{}])[0]).get('number', '')
        album_credits = release.get('artist-credit', [])
        match.update({'release_id': release['id'], 'release_group_id': (release.get('release-group') or {}).get('id'),
                      'album': release.get('title'), 'album_artist': _credit(album_credits),
                      'album_artist_ids': [c['artist']['id'] for c in album_credits], 'date': release.get('date'),
                      'track': int(number) if str(number).isdigit() else None,
                      'track_count': medium.get('track-count'), 'disc': medium.get('position')})
    return match


def _write_tags(tags, match):
    simple = {'\xa9nam': match['title'], '\xa9ART': match['artist'], '\xa9alb': match['album'],
              'aART': match['album_artist'], '\xa9day': match['date']}
    for key, value in simple.items():
        if value:
            tags[key] = [value]
    if match['track']:
        tags['trkn'] = [(match['track'], match['track_count'] or 0)]
    if match['disc']:
        tags['disk'] = [(match['disc'], 0)]
    freeform = {'MusicBrainz Track Id': [match['recording_id']], 'MusicBrainz Album Id': [match['release_id']],
                'MusicBrainz Release Group Id': [match['release_group_id']],
                'MusicBrainz Artist Id': match['artist_ids'], 'MusicBrainz Album Artist Id': match['album_artist_ids'],
                'ISRC': match['isrcs']}
    for name, values in freeform.items():
        values = [v for v in values if v]
        if values:
            tags[f'----:com.apple.iTunes:{name}'] = [MP4FreeForm(v.encode('utf-8')) for v in values]


def _write_cover(tags, match, http_get):
    if not match['release_id']:
        return '; no album art (no release)'
    try:
        image = http_get(f'https://coverartarchive.org/release/{match["release_id"]}/front-500')
    except Exception as e:  # no art in the archive (404) or network trouble: keep the thumbnail
        return f'; no album art ({e})'
    fmt = MP4Cover.FORMAT_PNG if image.startswith(b'\x89PNG') else MP4Cover.FORMAT_JPEG
    tags['covr'] = [MP4Cover(image, imageformat=fmt)]
    return ' and album art'
