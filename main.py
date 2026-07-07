import json
import os
import yt_dlp
from yt_dlp.utils import sanitize_filename
from datetime import date

def download_metadata_only(info : dict):
    # Save data under a Data/ folder (created if missing)
    video_data = yt_dlp.YoutubeDL.sanitize_info(info) #sanitize info and make it json-serializable
    
    #Grab identifiers, i.e. when the data was grabbed, what the video is called and who made it
    today = date.today()
    uploader = video_data["uploader"] or "unknown"
    video_Title = video_data["title"] or "unknown"
    file_id = sanitize_filename(f"{video_Title}_{uploader}_{today}_data")

    #Write metadata JSON to Data/<file_id>.json
    directory = os.path.join(os.getcwd(),"Data")
    os.makedirs(directory, exist_ok=True)
    file_path = os.path.join(directory,f"{file_id}.json")
    
    with open(file_path, "w") as json_file:
        json.dump(video_data, json_file, indent=4)

def download_audio_only(url : str):
    # Save audio under an Audio/ folder (created if missing)
    os.makedirs("Audio", exist_ok=True)

    # Audio download settings. Downloads the best native audio-only stream
    # (usually .webm/opus or .m4a) with no re-encoding, so ffmpeg is not required.
    audio_opts = {
        'format': 'bestaudio',                                  # Audio-only stream; error out rather than fall back to full video
        'outtmpl': os.path.join('Audio', '%(title)s.%(ext)s'),  # Save under Audio/ with the video title
        'noplaylist': True,                                     # Same as the metadata pass: a watch?v=...&list=... URL is just the video
        'js_runtimes': JS_RUNTIMES,
        'quiet': False,                                         # Keep False to see download logs in stdout
    }

    # Re-extract fresh for the download. Reusing the metadata info dict fails with
    # HTTP 403 because its format URLs come from a client whose URLs now require a
    # PO token; a fresh download lets yt-dlp pick a client that yields a usable URL.
    with yt_dlp.YoutubeDL(audio_opts) as ydl:
        ydl.download([url])


#1. initiate variables
URL = ''
JS_RUNTIMES = {'node': {}}

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

#3. Download Metadata
download_metadata_only(m_data)

#4. Download the audio (re-extracts fresh from the URL to get a downloadable format)
download_audio_only(URL)

