"""The video folder has one owner.

Everything about Downloads/<title> [<id>]/ lives here: the name templates, the fixed
data file names, overwrite rules and stale-file cleanup. The folder name and the media
file names come from ONE naming config, so they can't drift apart.

Interface:
    VideoFolder(downloads_dir, naming_opts=None)
    .path(info) -> folder path
    .media_opts() -> yt-dlp options for audio/video downloads (outtmpl, overwrites, naming)
    .save(info, video_data, transcript_text) -> (folder path, [actions])
"""
import json
import os

import yt_dlp

NAME = '%(title)s [%(id)s]'


class VideoFolder:
    def __init__(self, downloads_dir, naming_opts=None):
        self.downloads_dir = downloads_dir
        # Options that change how yt-dlp sanitises names, e.g. {'restrictfilenames': True}
        self.naming_opts = dict(naming_opts or {})

    def path(self, info):
        with yt_dlp.YoutubeDL({**self.naming_opts, 'quiet': True}) as ydl:
            return ydl.prepare_filename(info, outtmpl=os.path.join(self.downloads_dir, NAME))

    def media_opts(self):
        return {
            **self.naming_opts,
            'outtmpl': os.path.join(self.downloads_dir, NAME, NAME + '.%(ext)s'),
            'overwrites': True,
        }

    def save(self, info, video_data, transcript_text):
        folder = self.path(info)
        os.makedirs(folder, exist_ok=True)
        actions = []
        with open(os.path.join(folder, 'data.json'), 'w') as f:
            json.dump(video_data, f, indent=4)
        actions.append('wrote data.json')
        txt = os.path.join(folder, 'transcript.txt')
        if transcript_text:
            with open(txt, 'w', encoding='utf-8') as f:
                f.write(transcript_text)
            actions.append('wrote transcript.txt')
        elif os.path.exists(txt):
            os.remove(txt)
            actions.append('removed stale transcript.txt')
        return folder, actions
