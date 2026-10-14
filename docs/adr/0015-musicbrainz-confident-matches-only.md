# 0015. MusicBrainz: confident matches only, best non-compilation release

Status: Accepted (2026-10-14)

## Context
For a song, MusicBrainz can return several recordings, each on several releases (studio albums, singles, mixtapes, compilations). Explo takes the first search hit that passes a keyword blocklist, with no length check, and its issue #163 reports wrong versions.

In testing, "Earrings" by Malcolm Todd had two confident recordings. The first appeared only on a "Now That's What I Call Music!" compilation, so taking the first recording tagged the song as a Various Artists compilation.

## Decision
A recording is used only when the song title and one credited artist match the video (after removing "(Official Video)", "feat. …" and so on), and its length is within 10 s of the video. Across all confident recordings, pick the official release ranked best: (1) a studio album, (2) any other non-compilation release (mixtape, single, EP), (3) a compilation. Within a tier, the earliest date wins. Otherwise keep YouTube's tags.

Rejected: always using the best search hit (more albums filled, but sometimes wrong), stopping at the first confident recording, and the earliest release of any kind (it picks singles' and compilations' covers).

## Consequences
Unsure or unknown songs keep YouTube's tags and thumbnail. `data.json`'s `musicbrainz` is then `null`.
