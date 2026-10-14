import os
from capture import capture
from helpers import parse_choice, parse_yes

HERE = os.path.dirname(os.path.abspath(__file__))
# Output goes in Downloads/ next to this script (see capture.py / video_folder.py)
DOWNLOADS = os.path.join(HERE, 'Downloads')
# Optional YouTube cookies (Netscape format) for "confirm you're not a bot" blocks; git-ignored
COOKIES = os.path.join(HERE, 'cookies.txt')

#1. Ask everything up front, so the slow metadata fetch can run unattended
url = input('Input the Youtube URL: ')
choice = input('Download (a)udio, (v)ideo, or (b)oth? ')
want_audio, _ = parse_choice(choice)
as_music = want_audio and parse_yes(input('Treat as music (MusicBrainz tags + album art)? (y/n) '))

#2. Capture the video: metadata + comments, transcript, then any audio/video, all in one folder
try:
    outcome = capture(url, choice, as_music=as_music, downloads_dir=DOWNLOADS,
                      cookies_file=COOKIES if os.path.exists(COOKIES) else None)
except Exception as e:
    print(e)
    raise SystemExit(1)

#3. Report what happened
if outcome.status != 'saved':
    raise SystemExit(outcome.status)
print(f'\nSaved to: {outcome.folder}')
print(f'Transcript: {outcome.transcript_note}')
for action in outcome.actions:
    print(f'  - {action}')
