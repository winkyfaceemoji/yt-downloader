"""The video folder has one owner.

Everything about <downloads_dir>/<title> [<id>]/ lives here: the name templates, the fixed
data file names, overwrite rules and stale-file cleanup. The folder name and the media
file names come from ONE naming config, so they can't drift apart.

Interface:
    VideoFolder(downloads_dir, naming_opts=None)
    .path(info) -> folder path
    .media_opts() -> yt-dlp options for audio/video downloads (outtmpl, overwrites, naming)
    .save(info, video_data, transcript_text) -> (folder path, [actions])
        A video renamed since its last capture gets its old folder renamed to the new title.
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
        actions = []
        old = self._renamed_from(info, folder)
        if old:
            try:
                os.rename(old, folder)
                actions.append(f'renamed folder from "{os.path.basename(old)}"')
            except OSError as e:  # e.g. a file in it is open; never lose this run's data over it
                actions.append(f'could not rename folder "{os.path.basename(old)}": {e.strerror}')
        os.makedirs(folder, exist_ok=True)
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

    def _renamed_from(self, info, folder):
        # The video's one existing folder under an older title, if it has exactly one (ADR 0022)
        if os.path.exists(folder) or not os.path.isdir(self.downloads_dir):
            return None
        found = [os.path.join(self.downloads_dir, name) for name in os.listdir(self.downloads_dir)
                 if name.endswith(f'[{info["id"]}]')]
        found = [path for path in found if os.path.isdir(path)]
        return found[0] if len(found) == 1 else None
