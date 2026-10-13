"""English transcripts for one video.

The whole interface:
    get_transcript(info, fetch) -> (transcript | None, note)
    to_txt(transcript, duration) -> str

`info` is yt-dlp's info dict; `fetch(url) -> str` downloads a caption file (yt-dlp's
urlopen in production, a stand-in in tests). Caption problems never raise: a missing,
failed or empty caption file gives (None, note), where the note says why.
`transcript` is {'source': 'manual' | 'auto', 'segments': [{'start', 'end', 'text'}]}.
"""
import re
from typing import NamedTuple

__all__ = ['get_transcript', 'to_txt']

# Creator-uploaded English: 'en' or a regional variant like 'en-US'. Lowercase suffixes
# ('en-ja') are machine translations of another language's subtitles, so they're excluded.
MANUAL_ENGLISH = re.compile(r'en(-[A-Z]{2})?')
SENTENCE_END = ('.', '!', '?', '…')
# Words ending in '.' that don't end a sentence
ABBREVIATIONS = {'mr.', 'mrs.', 'ms.', 'dr.', 'st.', 'jr.', 'sr.', 'vs.', 'e.g.', 'i.e.'}
PAUSE_SECONDS = 1.5


class Track(NamedTuple):
    source: str  # 'manual' (creator-uploaded) or 'auto' (YouTube speech recognition)
    url: str     # .srt download URL


class Line(NamedTuple):
    start: float  # seconds
    text: str


def get_transcript(info, fetch):
    """Fetch the English transcript for an extracted video: (transcript | None, note)."""
    track = _pick_track(info.get('subtitles') or {}, info.get('automatic_captions') or {})
    if not track:
        return None, 'no English captions'
    try:
        srt = fetch(track.url)
    except Exception as e:  # any download failure: the run must still save its metadata
        return None, f'caption download failed ({e})'
    segments = _parse_srt(srt)
    if not segments:
        return None, 'caption file was empty'
    return {'source': track.source, 'segments': segments}, f'{len(segments)} caption pieces from {track.source} captions'


def to_txt(transcript, duration):
    """Render a transcript as readable timestamped lines, one per sentence or pause."""
    return _format_txt(_to_lines(transcript['segments']), duration)


def _pick_track(subtitles, automatic_captions):
    # Creator-uploaded English wins. Otherwise auto-captions only when the speech itself
    # is English ('en-orig'); auto 'en' without it is machine-translated. A candidate
    # without an .srt download is skipped in favour of the next one.
    # sorted() puts plain 'en' ahead of regional variants
    candidates = [('manual', subtitles[lang]) for lang in sorted(subtitles) if MANUAL_ENGLISH.fullmatch(lang)]
    if 'en-orig' in automatic_captions:
        candidates.append(('auto', automatic_captions['en-orig']))
    for source, formats in candidates:
        url = next((f['url'] for f in formats if f.get('ext') == 'srt'), None)
        if url:
            return Track(source, url)
    return None


def _parse_srt(text):
    # A cue is any block with a 'start --> end' line; the text follows it. Blocks without
    # one, or with a garbled time, are skipped: a blank cue in YouTube's .srt leaves such
    # a block behind, and it must not lose the rest of the transcript.
    segments = []
    for block in text.replace('\r\n', '\n').strip().split('\n\n'):
        lines = block.strip('\n').split('\n')
        timing = next((i for i, line in enumerate(lines) if ' --> ' in line), None)
        if timing is None:
            continue
        try:
            start, end = (_seconds(t) for t in lines[timing].split(' --> '))
        except ValueError:
            continue
        segments.append({'start': start, 'end': end, 'text': ' '.join(lines[timing + 1:]).strip()})
    return segments


def _to_lines(segments):
    # A line ends after a word with sentence-ending punctuation (even mid-piece), or
    # before a piece that starts more than PAUSE_SECONDS after the previous speech ended.
    # Auto-caption pieces overlap while speech is continuous, so a positive gap only
    # shows up at a real pause. A line split mid-piece starts at that piece's start time.
    lines, words, start, last_end = [], [], None, None
    for s in segments:
        if words and s['start'] - last_end > PAUSE_SECONDS:
            lines.append(Line(start, ' '.join(words)))
            words = []
        for word in s['text'].split():
            if not words:
                start = s['start']
            words.append(word)
            if _ends_sentence(word):
                lines.append(Line(start, ' '.join(words)))
                words = []
        last_end = s['end'] if last_end is None else max(last_end, s['end'])
    if words:
        lines.append(Line(start, ' '.join(words)))
    return lines


def _ends_sentence(word):
    return word.rstrip('"\')]').endswith(SENTENCE_END) and word.lower() not in ABBREVIATIONS


def _format_txt(lines, duration):
    # '[mm:ss] text', or '[h:mm:ss] text' once the video reaches an hour; the video's
    # duration decides, falling back to the last line's time when it's missing.
    last_start = lines[-1].start if lines else 0
    show_hours = max(duration or 0, last_start) >= 3600
    out = []
    for start, text in lines:
        h, rest = divmod(int(start), 3600)
        m, s = divmod(rest, 60)
        stamp = f'{h}:{m:02d}:{s:02d}' if show_hours else f'{m:02d}:{s:02d}'
        out.append(f'[{stamp}] {text}\n')
    return ''.join(out)


def _seconds(stamp):
    # 'HH:MM:SS,mmm' -> float seconds
    hms, ms = stamp.strip().split(',')
    h, m, s = (int(part) for part in hms.split(':'))
    return round(h * 3600 + m * 60 + s + int(ms) / 1000, 3)
