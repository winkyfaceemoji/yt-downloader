import json
import os
import yt_dlp
from yt_dlp.networking.exceptions import RequestError
import transcript

def save_metadata_and_transcript(info : dict):
    # Save Downloads/<title> [<id>]/data.json, plus transcript.txt when available
    video_data = yt_dlp.YoutubeDL.sanitize_info(info) #sanitize info and make it json-serializable

    #Sort the fetched comments most-liked first (like_count may be None -> treat as 0)
    comments = video_data.get("comments") or []
    comments.sort(key=lambda c: int(c.get("like_count") or 0), reverse=True)
    video_data["comments"] = comments

    #Fetch the English transcript (None when no usable English captions) and work out
    #the video's folder with yt-dlp, so it matches the one the audio/video go into.
    #A failed caption download shouldn't cost the metadata, so it's saved without one.
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        try:
            video_data["transcript"] = transcript.get_transcript(ydl, info)
            if not video_data["transcript"]:
                print("No English captions found; skipping transcript.")
        except RequestError as e:
            video_data["transcript"] = None
            print(f"Couldn't download the transcript ({e}); saving metadata without it.")
        folder = ydl.prepare_filename(info, outtmpl=FOLDER_TEMPLATE)
    os.makedirs(folder, exist_ok=True)

    with open(os.path.join(folder, "data.json"), "w") as json_file:
        json.dump(video_data, json_file, indent=4)

    #Readable transcript next to the JSON: one timestamped line per sentence/pause.
    #Without one, remove any .txt an earlier run left so the folder matches this run.
    txt_path = os.path.join(folder, "transcript.txt")
    if video_data["transcript"]:
        with open(txt_path, "w", encoding="utf-8") as txt_file:
            txt_file.write(transcript.to_txt(video_data["transcript"], info.get("duration")))
    elif os.path.exists(txt_path):
        os.remove(txt_path)

def download_audio_only(url : str):
    # Audio download settings. Prefers YouTube's .m4a (AAC) stream, which music players
    # handle almost everywhere, with no re-encoding. ffmpeg embeds the tags and cover art.
    audio_opts = {
        **MEDIA_OPTS,
        'format': 'bestaudio[ext=m4a]/bestaudio',               # .m4a when offered, else best audio-only; never falls back to full video
        'writethumbnail': True,                                 # Fetch the cover image so it can be embedded (deleted afterwards)
        'postprocessors': [
            {'key': 'FFmpegMetadata', 'add_metadata': True},    # Title, artist, date, etc. as tags players display
            {'key': 'EmbedThumbnail'},                          # Video thumbnail as cover art
        ],
    }

    # Re-extract fresh for the download. Reusing the metadata info dict fails with
    # HTTP 403 because its format URLs come from a client whose URLs now require a
    # PO token; a fresh download lets yt-dlp pick a client that yields a usable URL.
    with yt_dlp.YoutubeDL(audio_opts) as ydl:
        ydl.download([url])

def download_video(url : str):
    # Video download settings. Grabs the best video + best audio and merges them
    # with ffmpeg into a single .mp4 (full resolution; ffmpeg is required here).
    video_opts = {
        **MEDIA_OPTS,
        'format': 'bestvideo+bestaudio/best',                   # Best video+audio, falling back to best single file
        'merge_output_format': 'mp4',                           # Merge the streams into one .mp4
    }

    # Fresh extraction for the same 403 reason as the audio download above.
    with yt_dlp.YoutubeDL(video_opts) as ydl:
        ydl.download([url])


#1. initiate variables
URL = ''
JS_RUNTIMES = {'node': {}}

# Everything for one video goes in Downloads/<title> [<id>]/, next to this script:
# data.json and transcript.txt, plus audio/video named <title> [<id>].<ext> so they stay
# recognisable when copied out (e.g. to a music player). These are yt-dlp output
# templates; yt-dlp fills in the title and id.
DOWNLOADS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Downloads')
NAME_TEMPLATE = '%(title)s [%(id)s]'
FOLDER_TEMPLATE = os.path.join(DOWNLOADS, NAME_TEMPLATE)
MEDIA_TEMPLATE = os.path.join(FOLDER_TEMPLATE, NAME_TEMPLATE + '.%(ext)s')

# Settings shared by the audio and video downloads
MEDIA_OPTS = {
    'outtmpl': MEDIA_TEMPLATE,                  # Save in the video's folder: <title> [<id>].<ext>
    'overwrites': True,                         # Re-download and replace on a re-run
    'noplaylist': True,                         # Same as the metadata pass: a watch?v=...&list=... URL is just the video
    'js_runtimes': JS_RUNTIMES,
    'quiet': False,                             # Keep False to see download logs in stdout
}

ydl_opts = {
    'getcomments': True,             # Force fetching the comments list
    'skip_download': True,           # Bypass downloading the video file
    'extract_flat': False,           # Ensure complete metadata parsing
    'noplaylist': True,              # For a watch?v=...&list=... URL, take only the video
    #'sleep_interval_requests': 1,    # 1s between API requests; reduces "Incomplete data received" retries on high-comment videos
    'extractor_args': {'youtube': {'comment_sort': ['top'],      # Sort by top comments (default is newest)
                                   'max_comments': ['1000']}},   # Cap at the top 1000 comments
    'js_runtimes': JS_RUNTIMES,    # Use Node to sign YouTube URLs (avoids unavailable/403 errors); shared by both configs
    'quiet': False,                   # Keep the console output clean
}

try:
    #2. Grab the Youtube URL
    URL = input('Input the Youtube URL: ')

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        #2a. Peek at the result type first. process=False skips the expensive
        #    per-video extraction and comment fetching, so a playlist is rejected
        #    up front instead of after minutes of work.
        result = ydl.extract_info(URL, download=False, process=False)

        #2b. Guard: this tool handles one video at a time, not playlists
        if result.get('_type') in ('playlist', 'multi_video'):
            raise SystemExit('That URL is a playlist. Please provide a single video URL.')

        #2c. Fully process the single video (fetches comments, resolves formats)
        m_data = ydl.process_ie_result(result, download=False)

except Exception as e:
    print(e)
    raise SystemExit(1)

#3. Save metadata and transcript
save_metadata_and_transcript(m_data)

#4. Ask what media to download, then fetch it (each does a fresh extraction)
choice = input('Download (a)udio, (v)ideo, or (b)oth? ').strip().lower()
want_audio = choice in ('a', 'audio', 'b', 'both')
want_video = choice in ('v', 'video', 'b', 'both')

if want_audio:
    download_audio_only(URL)
if want_video:
    download_video(URL)
if not (want_audio or want_video):
    print('No media selected; saved metadata only.')

