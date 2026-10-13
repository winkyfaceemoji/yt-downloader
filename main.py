import os
from capture import capture

# Output goes in Downloads/ next to this script (see capture.py / video_folder.py)
DOWNLOADS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Downloads')

#1. Ask everything up front, so the slow metadata fetch can run unattended
url = input('Input the Youtube URL: ')
choice = input('Download (a)udio, (v)ideo, or (b)oth? ')

#2. Capture the video: metadata + comments, transcript, then any audio/video, all in one folder
try:
    outcome = capture(url, choice, downloads_dir=DOWNLOADS)
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
