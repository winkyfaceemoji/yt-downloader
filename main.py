import json
import os
import yt_dlp
from datetime import date

#2. initiate variables
URL = 'https://www.youtube.com/watch?v=ZVeQQHEkcAk'
id = ''
data = {}

#3. Opt out list ℹ️ See help(yt_dlp.YoutubeDL) for a list of available options and public functions
ydl_opts = {
    'getcomments': True,         # Force fetching the comments list
    'skip_download': True,       # Bypass downloading the video file
    'extract_flat': False,       # Ensure complete metadata parsing
    'quiet': True,               # Keep the console output clean
}

#4. Extraction list
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    #4a. extract the video metadata
    info = ydl.extract_info(URL, download=False)
    video_data = ydl.sanitize_info(info) #sanitize info and make it json-serializable
    
    #4b. grab identifiers, i.e. when the data was grabbed, what the video is called and who made it
    today = date.today()
    id = f"{video_data["title"]}_{video_data["uploader"]}_{today}_data"

    #4c. get 
    directory = os.path.join(os.getcwd(),"Data")
    os.makedirs(directory, exist_ok=True)
    file_path = os.path.join(directory,f"{id}.json")
    
    with open(file_path, "w") as json_file:
        json.dump(video_data, json_file, indent=4)


