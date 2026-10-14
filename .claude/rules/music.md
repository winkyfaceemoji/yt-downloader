---
paths:
  - "music.py"
  - "test_music.py"
---

# Music rules

## Invariants
- The interface is `lookup(info, http_get) -> (match | None, note)` and `tag_audio(path, match, http_get) -> note`. `http_get(url) -> bytes` is the seam; tests pass a fake. Neither function raises for network, data or tagging problems: a run must never lose its download over MusicBrainz.
- **Only confident matches** (ADR 0015). The title (after `_clean`), one credited artist, and the length within `MAX_LENGTH_GAP` seconds must all match. If they don't, the result is `None`, and the audio keeps yt-dlp's tags and YouTube thumbnail.
- **Release ranking across all confident recordings** (ADR 0015): studio album, then any other non-compilation release, then a compilation; earliest date within a tier.
- `match` is stored as-is in `data.json`'s `musicbrainz` field. Other projects read it, so treat key changes as breaking.
- The production `http_get` sends the repo-URL User-Agent and waits at least 1 s between requests (ADR 0016). MusicBrainz blocks clients that skip either. Cover Art Archive calls go through the same function.
- Only `.m4a` is tagged, through mutagen, using iTunes freeform names (`MusicBrainz Track Id` = recording ID, `MusicBrainz Album Id` = release ID, and so on, as Picard writes them) (ADR 0018).

## Gotchas
- **One song can have several MusicBrainz recordings**, some only on compilations. Stopping at the first confident one tagged "Earrings" (Malcolm Todd) as *Now That's What I Call Music! 124* by Various Artists. Always rank releases across every confident recording.
- **Ordinary music videos have no YouTube music fields** (`track`, `artist` and `album` are `None`), so most lookups come from parsing "Artist - Song (Official …)" in the title. Titles in "Song - Artist" order, or with no separator, usually won't match. That's intended: no match is better than a wrong one.
- **Search results carry only the matching track.** `media[0].track[0].number` is the song's position, and it may not be a number (e.g. vinyl `A1`), in which case `track` stays `None`.
- **A missing cover (404) is normal.** Not every release has art in the Cover Art Archive; the YouTube thumbnail stays.
