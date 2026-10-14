"""Capture one video: one module, one call.

    capture(url, choice, *, as_music=False, ydl_factory=yt_dlp.YoutubeDL, downloads_dir,
            naming_opts=None, http_get=music.http_get, cookies_file=None)
        -> Outcome(status, folder, transcript_note, actions)

Runs one video end to end: peek at the URL (rejecting playlists), fetch metadata and
comments, fetch the English transcript, save data.json/transcript.txt, then download the
chosen audio/video. `choice` is the user's 'a'/'v'/'b' answer, taken up front so the
slow part needs no input. With `as_music` and an audio download, the song is looked up on
MusicBrainz (saved as data.json's "musicbrainz") and a confident match is tagged into the
audio. `cookies_file`, when given, is passed to every yt-dlp call. Extraction and download errors from yt-dlp propagate; caption
problems never do (see transcript.py).

Seams, each with two adapters:
  - ydl_factory(opts): the real yt_dlp.YoutubeDL in production, a fake in tests.
  - downloads_dir: the project's Downloads/ in production, a temp dir in tests.
  - http_get(url) -> bytes: music.http_get (MusicBrainz) in production, a fake in tests.
"""
from dataclasses import dataclass, field

import yt_dlp

import helpers
import music
import transcript
from video_folder import VideoFolder

JS_RUNTIMES = {'node': {}}      # Use Node to sign YouTube URLs (avoids unavailable/403 errors)

METADATA_OPTS = {
    'getcomments': True,             # Force fetching the comments list
    'skip_download': True,           # Bypass downloading the video file
    'extract_flat': False,           # Ensure complete metadata parsing
    'noplaylist': True,              # For a watch?v=...&list=... URL, take only the video
    #'sleep_interval_requests': 1,    # 1s between API requests; reduces "Incomplete data received" retries on high-comment videos
    'extractor_args': {'youtube': {'comment_sort': ['top'],      # Sort by top comments (default is newest)
                                   'max_comments': ['1000']}},   # Cap at the top 1000 comments
    'js_runtimes': JS_RUNTIMES,
    'quiet': False,                  # Show yt-dlp's progress and warnings
}

# Audio prefers YouTube's .m4a (AAC) stream, which music players handle almost everywhere,
# with no re-encoding. ffmpeg embeds the tags and cover art.
AUDIO_OPTS = {
    'format': 'bestaudio[ext=m4a]/bestaudio',               # .m4a when offered, else best audio-only; never falls back to full video
    'writethumbnail': True,                                 # Fetch the cover image so it can be embedded (deleted afterwards)
    'postprocessors': [
        {'key': 'FFmpegMetadata', 'add_metadata': True},    # Title, artist, date, etc. as tags players display
        {'key': 'EmbedThumbnail'},                          # Video thumbnail as cover art
    ],
}

# Video: best video + best audio merged by ffmpeg into one full-resolution .mp4
VIDEO_OPTS = {
    'format': 'bestvideo+bestaudio/best',                   # Best video+audio, falling back to best single file
    'merge_output_format': 'mp4',
}


@dataclass
class Outcome:
    status: str
    folder: str | None = None
    transcript_note: str = ''
    actions: list = field(default_factory=list)


def capture(url, choice, *, as_music=False, ydl_factory=yt_dlp.YoutubeDL, downloads_dir,
            naming_opts=None, http_get=music.http_get, cookies_file=None):
    want_audio, want_video = helpers.parse_choice(choice)
    cookies = {'cookiefile': cookies_file} if cookies_file else {}

    with ydl_factory({**METADATA_OPTS, **cookies}) as ydl:
        result = ydl.extract_info(url, download=False, process=False)
        if helpers.is_playlist(result):
            return Outcome('rejected: that URL is a playlist')
        info = ydl.process_ie_result(result, download=False)
        video_transcript, note = transcript.get_transcript(info, lambda u: ydl.urlopen(u).read().decode('utf-8'))

    video_data = yt_dlp.YoutubeDL.sanitize_info(info)
    video_data['comments'] = helpers.sort_comments(video_data.get('comments'))
    video_data['transcript'] = video_transcript

    # Music lookup only when it can be used: the user said "music" and wants the audio
    match, music_note = None, None
    if as_music and want_audio:
        match, music_note = music.lookup(info, http_get)
        video_data['musicbrainz'] = match

    folder = VideoFolder(downloads_dir, naming_opts)
    text = transcript.to_txt(video_transcript, info.get('duration')) if video_transcript else None
    path, actions = folder.save(info, video_data, text)
    if music_note:
        actions.append(f'MusicBrainz: {music_note}')

    # Media re-extract fresh (ADR 0003: reusing `info` gets HTTP 403)
    media_opts = {**folder.media_opts(), 'noplaylist': True, 'js_runtimes': JS_RUNTIMES, 'quiet': False, **cookies}
    if want_audio:
        with ydl_factory({**media_opts, **AUDIO_OPTS}) as ydl:
            downloaded = ydl.extract_info(url, download=True)
        actions.append('downloaded audio')
        if match:
            audio_path = downloaded['requested_downloads'][0]['filepath']
            actions.append(music.tag_audio(audio_path, match, http_get))
    if want_video:
        with ydl_factory({**media_opts, **VIDEO_OPTS}) as ydl:
            ydl.download([url])
        actions.append('downloaded video')
    if not (want_audio or want_video):
        actions.append('no media selected')
    return Outcome('saved', path, note, actions)
