# 0013. Treat a run as music only when the user says so

Status: Accepted (2026-10-14)

## Context
The tool downloads all kinds of videos (talks, vlogs, music), but the user wants to be able to use any download as music. Music-only steps (MusicBrainz lookup, album tags, album art) would otherwise run on every video, and a talk titled like a song could be tagged as that song.

## Decision
When the user chooses audio, `main.py` asks a third question up front: "Treat as music? (y/n)". Only then does `capture()` look the song up and tag the audio. The question is skipped for video-only runs, because the tags go into the audio file.

Rejected: automatic detection, i.e. treating it as music when YouTube marks it as a track or MusicBrainz confidently matches (misses music videos without metadata and adds requests on every run), and a separate command run later on a folder (an extra step).

## Consequences
Non-music runs are unchanged and make no MusicBrainz requests. All three questions are still asked before the slow part (ADR 0011).
