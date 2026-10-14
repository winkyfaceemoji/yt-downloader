# 0007. Fixed data file names, titled media file names

Status: Accepted (2026-10-13)

## Context
Repeating the title in both the folder and file names hit Windows' 260-character path limit for long titles. The audio is also meant for music players.

## Decision
`data.json` and `transcript.txt` have fixed names, so code can read any folder the same way. Audio and video keep `<title> [<id>].<ext>`, so they're recognisable when copied out of the folder.

Rejected: fixed names for media too (every track called `audio.m4a` collides and shows no name on a player), trimming titles, and relying on Windows long paths (works on one PC only, and many tools ignore the setting).

## Consequences
Media files for titles over about 85 characters can still fail to save on this machine.
