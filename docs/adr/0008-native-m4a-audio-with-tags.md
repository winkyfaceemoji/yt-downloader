# 0008. Audio is native .m4a with embedded tags and cover art

Status: Accepted (2026-10-13)

## Context
The audio is meant for ordinary music players. YouTube's best audio is often `.webm`/Opus, which many players and Apple Music can't play.

## Decision
Download `bestaudio[ext=m4a]/bestaudio` with no re-encoding. `FFmpegMetadata` and `EmbedThumbnail` add title, artist and date tags plus cover art, so players show proper names.

Rejected: native `.webm`/Opus only, and converting to `.mp3` (a lossy re-encode of an already-lossy stream).

## Consequences
ffmpeg is now required for audio as well as video. `.webm` still appears when YouTube offers no `.m4a`.
