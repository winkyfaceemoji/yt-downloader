# 0003. Reverted: reusing the metadata extraction for media downloads

Status: Accepted (2026-07-07)

## Context
To avoid a second extraction, the audio download passed the metadata `info` dict to `process_ie_result(download=True)`.

## Decision
Reverted. Audio and video downloads re-extract the URL fresh with `ydl.download([url])`. The reused format URLs come from a client that now needs a PO token, so the download failed with `HTTP 403`. A fresh extraction lets yt-dlp negotiate a client that yields a usable URL.

## Consequences
One extra extraction per media download. Comments aren't re-fetched, so the cost is small. Don't reintroduce the reuse to save a request.
