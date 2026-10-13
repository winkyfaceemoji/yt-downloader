# Capturing a video

`capture.py` runs one video end to end behind a single call. `main.py` only asks the two
questions and prints the result. Tested against a fake yt-dlp and a temp folder by
`test_capture.py`.

```python
capture(url, choice, *, ydl_factory=yt_dlp.YoutubeDL, downloads_dir, naming_opts=None)
    -> Outcome(status, folder, transcript_note, actions)
```

- `choice` is the raw answer to "Download (a)udio, (v)ideo, or (b)oth?", read by
  `helpers.parse_choice`; anything unrecognised downloads no media. It's asked **up
  front**, so the slow part runs unattended.
- `status` is `'saved'`, or `'rejected: that URL is a playlist'` (nothing written).
  `actions` lists what happened, e.g. `wrote data.json`, `removed stale transcript.txt`,
  `downloaded audio`, `no media selected`.

## Steps

1. **Peek**: `extract_info(url, process=False)`. A playlist (`helpers.is_playlist`) is
   rejected here, before any slow work. `noplaylist` makes `watch?v=…&list=…` links just
   the video.
2. **Metadata + comments**: `process_ie_result`, with `METADATA_OPTS` (top 1000
   comments, "top" sort).
3. **Transcript**: `transcript.get_transcript(info, fetch)`, using the same yt-dlp
   instance's `urlopen` as `fetch`. Never raises; see transcripts.md.
4. **Save**: comments sorted most-liked first (`helpers.sort_comments`), then
   `VideoFolder.save` writes `data.json` / `transcript.txt`.
5. **Media**: each chosen download is a fresh `ydl.download([url])` built from
   `VideoFolder.media_opts()` plus `AUDIO_OPTS` / `VIDEO_OPTS`.

## Seams

| Seam | Production adapter | Test adapter |
|---|---|---|
| `ydl_factory(opts)` | `yt_dlp.YoutubeDL` | `FakeYoutubeDL` in `test_capture.py` |
| `downloads_dir` | `Downloads/` next to `main.py` | a temp folder |

## Error modes

- Extraction or download errors from yt-dlp (bad URL, `HTTP 403`, missing ffmpeg)
  propagate. `main.py` prints them and exits 1.
- Media downloads happen after `data.json` is saved, so a media failure never loses the
  metadata or transcript.
