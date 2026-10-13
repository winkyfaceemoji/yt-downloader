import re
from typing import NamedTuple

# Creator-uploaded English: 'en' or a regional variant like 'en-US'. Lowercase suffixes
# ('en-ja') are machine translations of another language's subtitles, so they're excluded.
MANUAL_ENGLISH = re.compile(r'en(-[A-Z]{2})?')


class Track(NamedTuple):
    source: str  # 'manual' (creator-uploaded) or 'auto' (YouTube speech recognition)
    url: str     # .srt download URL


class Line(NamedTuple):
    start: float  # seconds
    text: str


def pick_track(subtitles, automatic_captions):
    """Return the Track for the English captions to use, or None.

    Creator-uploaded English wins. Otherwise use auto-captions only when the speech
    itself is English ('en-orig'); auto 'en' without it is machine-translated.
    A candidate without an .srt download is skipped in favour of the next one.
    """
    # sorted() puts plain 'en' ahead of regional variants
    candidates = [('manual', subtitles[lang]) for lang in sorted(subtitles) if MANUAL_ENGLISH.fullmatch(lang)]
    if 'en-orig' in automatic_captions:
        candidates.append(('auto', automatic_captions['en-orig']))
    for source, formats in candidates:
        url = _srt_url(formats)
        if url:
            return Track(source, url)
    return None


def get_transcript(ydl, info):
    """Fetch the English transcript for an extracted video: {'source', 'segments'} or None."""
    track = pick_track(info.get('subtitles') or {}, info.get('automatic_captions') or {})
    if not track:
        return None
    srt = ydl.urlopen(track.url).read().decode('utf-8')
    return {'source': track.source, 'segments': parse_srt(srt)}


def to_txt(transcript, duration):
    """Render a transcript from get_transcript() as the readable timestamped .txt."""
    return format_txt(to_lines(transcript['segments']), duration)


def _srt_url(formats):
    return next((f['url'] for f in formats if f.get('ext') == 'srt'), None)


def parse_srt(text):
    """Turn .srt text into [{'start', 'end', 'text'}] with times in seconds."""
    segments = []
    for block in text.replace('\r\n', '\n').strip().split('\n\n'):
        lines = block.split('\n')
        start, end = lines[1].split(' --> ')
        segments.append({'start': _seconds(start), 'end': _seconds(end), 'text': ' '.join(lines[2:])})
    return segments


SENTENCE_END = ('.', '!', '?', '…')
# Words ending in '.' that don't end a sentence
ABBREVIATIONS = {'mr.', 'mrs.', 'ms.', 'dr.', 'st.', 'jr.', 'sr.', 'vs.', 'e.g.', 'i.e.'}
PAUSE_SECONDS = 1.5


def to_lines(segments):
    """Join caption pieces into readable lines: [Line(start_seconds, text)].

    A line ends after a word with sentence-ending punctuation (even mid-piece), or
    before a piece that starts more than PAUSE_SECONDS after the previous speech ended.
    Auto-caption pieces overlap while speech is continuous, so a positive gap only
    shows up at a real pause. A line split mid-piece starts at that piece's start time.
    """
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


def format_txt(lines, duration):
    """Render lines as '[mm:ss] text', or '[h:mm:ss] text' once the video reaches an hour.

    The video's duration decides, falling back to the last line's time when it's missing.
    """
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
