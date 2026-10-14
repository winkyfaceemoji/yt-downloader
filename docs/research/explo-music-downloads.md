# What yt-downloader can borrow from Explo for music downloads

Researched 2026-10-14. Source read: Explo default branch `dev` at commit
[`51449865`](https://github.com/LumePart/Explo/tree/51449865c526c88f05b246b4d2447efc204854d2)
(2026-09-09, matches release v1.2.0), plus the wiki and issues on GitHub. `E/` below means
`https://github.com/LumePart/Explo/blob/51449865c526c88f05b246b4d2447efc204854d2/`.

## Summary

| Idea | What a music-player user gets | Module | Conflicts? | Effort |
|---|---|---|---|---|
| A. Optional cookies file | Gets past "Sign in to confirm you're not a bot" | `capture.py` | Close to the "keep it simple, no PO-token plugin" decision | Small |
| B. Search by "Title - Artist" via YouTube Music, keyword blocklist | Paste a song name, not a URL; skips live/remix/cover | new module + `main.py` | Changes the input model (still one track per run) | Medium |
| C. Richer tags (album, album artist, track no., `; `-joined artists) | Album grouping and sorting in the player | `capture.py` | None | Small–Medium |
| D. MusicBrainz IDs + Cover Art Archive front cover | Square album art, IDs that Picard/Jellyfin/Navidrome match on | new module | None; adds a network dependency | Large |
| E. `Artist/Album/File` path template | Library-style folders | `video_folder.py` | **Yes**: per-video `<title> [<id>]` folders | Medium |
| F. Append to an `.m3u` | One playlist of everything downloaded | `video_folder.py` | Cross-run state; nothing recorded against it | Small |
| Not borrowable | Re-encode to mp3; media-server APIs; slskd/Lidarr; ListenBrainz discovery | — | mp3 conflicts with the no-re-encode decision; the rest is out of scope | — |

## Observed facts (Explo)

**Language and licence.** Explo is Go (`go.mod`, `src/**/*.go`). The only Python is the
24-line `E/src/downloader/youtube_music/search_ytmusic.py`. The licence is MIT, © 2023 Markus
Kuuse (`E/LICENSE`). yt-downloader is MIT too (`LICENSE`, © 2026 winkyfaceemoji). Copying
code is allowed if Explo's copyright and permission notice are kept, but almost nothing is
liftable as-is: in practice you re-implement the ideas.

**Finding a track.**
- The query is `"<Title> - <Artist>"` (`E/src/downloader/youtube.go#L79`).
- With no API key, it shells out to `ytmusicapi`'s `YTMusic().search(query, limit=10)`, with
  no `filter`, so results can be any type (`search_ytmusic.py#L16-L17`, `youtube.go#L110`).
  The first result that has a `videoId` and passes the keyword filter wins
  (`youtube.go#L137-L150`).
- With a YouTube Data API key, it searches `type=video&videoCategoryId=10` (Music). It prefers
  a channel whose name contains `- Topic` or equals the main artist, then falls back to the
  first result that passes the filter (`youtube.go#L86`, `#L171-L179`, `#L286-L301`).
- Keyword filter: the default is `live,remix,instrumental,extended,clean,acapella`. A keyword
  is skipped when the wanted title or artist itself contains it (`E/src/downloader/downloader.go#L192-L207`,
  `E/src/config/config.go#L117`).
- **YouTube has no duration check.** The ±10 s duration match exists only for Soulseek
  (`E/src/downloader/slskd.go#L296`).

**Download and format.**
- `goutubedl` (a yt-dlp wrapper) downloads format `bestaudio` to `<file>.tmp`
  (`youtube.go#L182-L196`, `#L206`).
- ffmpeg then writes `TRACK_EXTENSION`, default `mp3` (`config.go#L124`), with `-map 0:a` and
  `-metadata` but no `-c copy` (`youtube.go#L254-L281`). Issue
  [#228](https://github.com/LumePart/Explo/issues/228) shows the compiled command has no codec
  flag.
- The Docker image runs `pip install ytmusicapi yt-dlp`, unpinned (`E/Dockerfile#L36`). The
  maintainer says Explo "should try to update yt-dlp every scheduled job run"
  ([#233](https://github.com/LumePart/Explo/issues/233)).

**Tags.**
- `E/src/util/metadata.go` maps title, album, artist (multiple artists joined with `"; "`, `#L62-L65`),
  album_artist, artist-sort, date, genre, track/disc numbers and totals, ISRC, and six
  MusicBrainz IDs.
- There are per-container key sets for mp3 (ID3), flac/opus (Vorbis) and ape. **Every other
  extension, m4a included, gets the "basic" set**: title, album, artist, album_artist,
  artist-sort, date, track, disc, plus genre and ISRC. No MusicBrainz IDs (`#L99-L110`, `#L186-L203`).
- The metadata comes from ListenBrainz/MusicBrainz, not YouTube. MusicBrainz calls sleep 2 s
  and retry 3 times (`E/src/discovery/listenbrainz.go#L396-L497`). Titles become
  `Title (feat. A & B)` (`#L751-L770`).

**Cover art.**
- Comes from the Cover Art Archive (`coverartarchive.org/release/<mbid>/...-<250|500|1000>`,
  `listenbrainz.go#L311`, `#L704-L706`).
- Embedded as an `mjpeg` `attached_pic` with `comment=Cover (front)` (`youtube.go#L257-L268`).
- Off by default (`EMBED_COVER_ART=false`, `config.go#L125`). The maintainer's reason: "most
  systems can fetch cover art themselves (incl Navidrome)" (#233).

**Paths and playlists.**
- The default name is `<title>-<artist>.<ext>`, truncated to 240 bytes (`downloader.go#L175-L189`).
- `PATH_TEMPLATE` (e.g. `{{Artist}}/{{Album}}/{{File}}`) substitutes sanitized fields and
  rejects non-local paths with `filepath.IsLocal` (`downloader.go#L242-L279`; `E/sample.env#L55-L56`).
- The `.m3u` holds bare file names, one per line, and is written only for MPD
  (`E/src/client/mpd.go#L66-L74`). Other servers get playlists through their APIs
  (`E/src/client/{jellyfin,plex,emby,subsonic}.go`).

**403s and rate limits.**
- `COOKIES_PATH` (default `./cookies.txt`) is passed to yt-dlp when the file exists
  (`youtube.go#L62-L64`). It was added in v0.11.3 after a "Sign in to confirm you're not a
  bot" report ([#78](https://github.com/LumePart/Explo/issues/78)).
- Downloads run at most 3 at a time, with `DOWNLOAD_LIMITER` (default 1) operations per second
  (`downloader.go#L77-L80`, `config.go#L104`). There is no retry for a failed YouTube download
  (`youtube.go#L303-L316`).
- In #233 the maintainer first called the 403s rate limiting, then traced them to an outdated
  yt-dlp. Updating yt-dlp fixed it for the reporter.

## Contrary evidence

- [#163](https://github.com/LumePart/Explo/issues/163) (open): users get "random versions of
  songs that are too different". Explo doesn't check a download against the wanted track or
  try the next candidate. **Explo's matching is not a proven reference.**
- [#212](https://github.com/LumePart/Explo/issues/212) (open): the slskd search and download
  path is being reworked for reliability.
- The wiki documents no YouTube matching logic or rate limits
  ([Configuration Parameters](https://github.com/LumePart/Explo/wiki/4.-Configuration-Parameters),
  [System Notes](https://github.com/LumePart/Explo/wiki/6.-System-Notes)). The code is the only spec.

## Inferences

- Explo's YouTube path re-encodes (ffmpeg's default encoder for `.mp3`, a lossy-to-lossy step).
  yt-downloader's native m4a is already the better choice for quality.
- For m4a, yt-downloader's `FFmpegMetadata` already covers most of Explo's "basic" set *when
  yt-dlp has the fields*. Installed yt-dlp maps `title` from `track` then `title`, `artist` from
  `artist`/`artists`/…/`uploader`, plus `album`, `album_artist`, `track`, `disc` and `genre`
  (`yt_dlp/postprocessor/ffmpeg.py` L746-L757, read from locally installed 2026.07.04, not the
  pinned 2026.08.19). For an ordinary video, `artist` falls back to the uploader, and album is
  empty.
- Explo's own matching is weak (first filtered hit, no duration check, #163), so idea B should
  add the duration check that Explo only has for slskd, not copy Explo as-is.
- #233 is outside evidence that a stale yt-dlp causes 403s. That's relevant to the pin
  decision, but doesn't overturn it: your measurements were on a pinned, newer build.

## Recommendations

1. **A. Cookies (small, `capture.py`).** Add `cookiefile` to the media and metadata opts only
   when a `cookies.txt` exists, as Explo does. It doesn't contradict a decision, but extends the
   403 story; record it as an ADR if adopted.
2. **C. Tag mapping (small–medium, `capture.py`).** Use yt-dlp's `meta_<field>` override
   (supported by the mapping above) or `parse_metadata` to fill `album`/`album_artist` and join
   multiple artists with `; `, as Explo does. The value depends on open question 1.
3. **B. Search mode (medium).** If wanted: a `ytmusicapi` search with `filter="songs"` (Explo
   doesn't filter), the keyword blocklist with Explo's "skip if the wanted title contains it"
   rule, and a ±10 s duration check. Then pass the chosen `videoId` to `capture()` unchanged:
   one track per run holds. Adds a dependency (MIT).
4. **D, E, F: only on request.** D is a MusicBrainz client with 1 req/s pacing. E conflicts
   with the per-video folder decision; an "export copy" step would avoid the conflict. F has
   little value for one track per run.
5. **Don't borrow** the mp3 re-encode, the media-server APIs, slskd/Lidarr or ListenBrainz
   discovery.

## What the evidence can't establish / open questions

1. Do your typical links point at "- Topic" / "Provided to YouTube" uploads (where yt-dlp fills
   `track`/`artist`/`album`) or at music videos? That decides how much C adds.
2. Does your music player read tags from m4a, or use its own lookup (as Navidrome/Jellyfin do)?
   If it uses its own lookup, C and D matter less.
3. Explo's matching accuracy is not measured anywhere; #163 suggests it is mediocre.
4. Cookie use and account risk: not covered by Explo's docs. Check yt-dlp's own guidance before
   adopting A.
