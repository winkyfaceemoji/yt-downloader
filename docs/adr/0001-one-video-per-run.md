# 0001. One video per run; playlists rejected up front

Status: Accepted (2026-07-07)

## Context
Each run fetches full metadata and up to 1000 comments, which is slow. Given a playlist URL, yt-dlp would extract every video and its comments before writing anything, then download media for every entry.

## Decision
Handle one video per run. A cheap `extract_info(..., process=False)` peek rejects playlist and multi-video results before the expensive extraction. `noplaylist` makes `watch?v=…&list=…` links (including radio mixes) resolve to just that video.

Rejected: bulk-processing playlists, and rejecting every `list=` URL (that would force hand-editing shared links).

## Consequences
Playlist URLs exit with a message in about a second; links copied from a playlist or mix still work. Implemented in `capture.py` with `helpers.is_playlist`.
