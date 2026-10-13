"""Capture one video: one module, one call.

    capture(url, choice, *, ydl_factory=yt_dlp.YoutubeDL, downloads_dir, naming_opts=None)
        -> Outcome(status, folder, transcript_note, actions)

Runs one video end to end: peek at the URL (rejecting playlists), fetch metadata and
comments, fetch the English transcript, save data.json/transcript.txt, then download the
chosen audio/video. `choice` is the user's 'a'/'v'/'b' answer, taken up front so the
slow part needs no input. Extraction and download errors from yt-dlp propagate; caption
problems never do (see transcript.py).

Two seams, each with two adapters:
  - ydl_factory(opts): the real yt_dlp.YoutubeDL in production, a fake in tests.
  - downloads_dir: the project's Downloads/ in production, a temp dir in tests.
"""
from dataclasses import dataclass, field

import yt_dlp

import helpers
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


def capture(url, choice, *, ydl_factory=yt_dlp.YoutubeDL, downloads_dir, naming_opts=None):
    want_audio, want_video = helpers.parse_choice(choice)

    with ydl_factory(METADATA_OPTS) as ydl:
        result = ydl.extract_info(url, download=False, process=False)
        if helpers.is_playlist(result):
            return Outcome('rejected: that URL is a playlist')
        info = ydl.process_ie_result(result, download=False)
        video_transcript, note = transcript.get_transcript(info, lambda u: ydl.urlopen(u).read().decode('utf-8'))

    video_data = yt_dlp.YoutubeDL.sanitize_info(info)
    video_data['comments'] = helpers.sort_comments(video_data.get('comments'))
    video_data['transcript'] = video_transcript

    folder = VideoFolder(downloads_dir, naming_opts)
    text = transcript.to_txt(video_transcript, info.get('duration')) if video_transcript else None
    path, actions = folder.save(info, video_data, text)

    # Media re-extract fresh (docs/DECISIONS.md: reusing `info` gets HTTP 403)
    for wanted, extra, label in ((want_audio, AUDIO_OPTS, 'audio'), (want_video, VIDEO_OPTS, 'video')):
        if wanted:
            opts = {**folder.media_opts(), 'noplaylist': True, 'js_runtimes': JS_RUNTIMES, 'quiet': False, **extra}
            with ydl_factory(opts) as ydl:
                ydl.download([url])
            actions.append(f'downloaded {label}')
    if not (want_audio or want_video):
        actions.append('no media selected')
    return Outcome('saved', path, note, actions)
