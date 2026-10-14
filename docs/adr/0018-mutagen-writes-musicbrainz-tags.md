# 0018. mutagen writes the MusicBrainz tags

Status: Accepted (2026-10-14)

## Context
Music players and tools like Picard read MusicBrainz IDs from iTunes "freeform" atoms (`----:com.apple.iTunes:MusicBrainz Track Id`, etc.) in .m4a files. ffmpeg, which already writes the basic tags and thumbnail via yt-dlp, can't write those atoms.

## Decision
Add `mutagen` (pinned 1.48.1; vetted against its upstream docs and repo, github.com/quodlibet/mutagen) and use it after the download to write the matched title, artist, album, album artist, date, track/disc numbers, MusicBrainz IDs and ISRC, and to replace the cover with the album art.

Rejected: ffmpeg-only tagging (no MusicBrainz IDs), and AtomicParsley (an extra executable outside pip).

## Consequences
Only `.m4a` files are tagged. A `.webm` fallback keeps yt-dlp's tags. yt-dlp's EmbedThumbnail also uses mutagen now that it's installed.
