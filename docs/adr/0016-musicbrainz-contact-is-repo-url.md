# 0016. Identify the project to MusicBrainz by its repo URL

Status: Accepted (2026-10-14)

## Context
MusicBrainz requires every client to send a User-Agent with an app name, version and contact, and allows at most 1 request per second.

## Decision
Send `yt-downloader/1.0 ( https://github.com/winkyfaceemoji/yt-downloader )`, and space requests at least 1 s apart (`music.http_get`). This also covers Cover Art Archive requests.

Rejected: the user's email address as the contact, so no personal data goes to MusicBrainz.

## Consequences
If MusicBrainz ever needs to reach the project, it has to go through the GitHub repo.
