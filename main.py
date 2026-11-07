import os
import sys

import hub
from capture import capture
from helpers import parse_choice, parse_yes

HERE = os.path.dirname(os.path.abspath(__file__))
# Optional YouTube cookies (Netscape format) for "confirm you're not a bot" blocks; git-ignored
COOKIES = os.path.join(HERE, 'cookies.txt')
cookies_file = COOKIES if os.path.exists(COOKIES) else None

# Titles can hold characters a cp1252 console or pipe can't encode; print '?' rather than crash
sys.stdout.reconfigure(errors='replace')

#1. With arguments this is the data hub (hub.cmd) or a script: no prompts, see hub.py
if len(sys.argv) > 1:
    raise SystemExit(hub.main(sys.argv[1:], capture_fn=capture, cookies_file=cookies_file))

#2. Otherwise ask everything up front, so the slow metadata fetch can run unattended
url = input('Input the Youtube URL: ')
choice = input('Download (a)udio, (v)ideo, or (b)oth? ')
want_audio, _ = parse_choice(choice)
as_music = want_audio and parse_yes(input('Treat as music (MusicBrainz tags + album art)? (y/n) '))

#3. Capture under the same run lock and log the hub uses, so its status sees this run too
raise SystemExit(hub.run_capture(url, choice, as_music, capture_fn=capture, cookies_file=cookies_file))
