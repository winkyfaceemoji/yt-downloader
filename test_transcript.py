import io
import unittest

import transcript
from transcript import Line


def track(lang):
    # Caption list as yt-dlp reports it: several formats per language
    return [{'ext': 'json3', 'url': f'{lang}.json3'}, {'ext': 'srt', 'url': f'{lang}.srt'}]


class PickTrackTests(unittest.TestCase):
    def test_prefers_creator_english_over_auto_captions(self):
        result = transcript.pick_track({'en': track('en')}, {'en-orig': track('en-orig')})
        self.assertEqual(result, ('manual', 'en.srt'))

    def test_accepts_creator_english_with_region(self):
        result = transcript.pick_track({'fr': track('fr'), 'en-GB': track('en-GB')}, {})
        self.assertEqual(result, ('manual', 'en-GB.srt'))

    def test_uses_auto_captions_only_when_speech_is_english(self):
        result = transcript.pick_track({}, {'en-orig': track('en-orig'), 'en': track('en')})
        self.assertEqual(result, ('auto', 'en-orig.srt'))

    def test_rejects_machine_translated_english(self):
        # 'en' auto-captions without 'en-orig' are translated from another language;
        # 'en-ja' is a machine translation of creator Japanese subtitles
        result = transcript.pick_track({'en-ja': track('en-ja')}, {'en': track('en'), 'ja-orig': track('ja-orig')})
        self.assertIsNone(result)

    def test_falls_back_to_auto_captions_when_creator_track_has_no_srt(self):
        no_srt = [{'ext': 'vtt', 'url': 'en.vtt'}]
        result = transcript.pick_track({'en': no_srt}, {'en-orig': track('en-orig')})
        self.assertEqual(result, ('auto', 'en-orig.srt'))


class ParseSrtTests(unittest.TestCase):
    def test_reads_cues_into_timed_segments(self):
        srt = ('1\n00:00:17,520 --> 00:00:21,520\nAll my\n\n'
               '2\n01:02:03,004 --> 01:02:05,000\nlife I been\n')
        self.assertEqual(transcript.parse_srt(srt), [
            {'start': 17.52, 'end': 21.52, 'text': 'All my'},
            {'start': 3723.004, 'end': 3725.0, 'text': 'life I been'},
        ])

    def test_joins_multiline_cue_text_and_handles_windows_newlines(self):
        srt = '1\r\n00:00:01,000 --> 00:00:02,000\r\nfirst line\r\nsecond line\r\n'
        self.assertEqual(transcript.parse_srt(srt),
                         [{'start': 1.0, 'end': 2.0, 'text': 'first line second line'}])


def seg(start, end, text):
    return {'start': start, 'end': end, 'text': text}


class ToLinesTests(unittest.TestCase):
    def test_joins_overlapping_pieces_until_a_sentence_ends(self):
        # Real auto-captions overlap while speech is continuous
        segments = [seg(17.52, 21.52, 'All my'), seg(19.60, 24.00, 'life I been'),
                    seg(21.52, 27.80, 'this way.'), seg(24.00, 27.80, 'My mom and my daddy,')]
        self.assertEqual(transcript.to_lines(segments), [
            (17.52, 'All my life I been this way.'),
            (24.00, 'My mom and my daddy,'),
        ])

    def test_starts_a_new_line_after_a_pause_longer_than_1_5_seconds(self):
        segments = [seg(70.0, 73.0, 'hopefully'), seg(73.2, 75.4, 'place'),
                    seg(78.0, 81.5, 'father you said')]  # 2.6s of silence before this
        self.assertEqual(transcript.to_lines(segments), [
            (70.0, 'hopefully place'),
            (78.0, 'father you said'),
        ])

    def test_keeps_going_through_a_short_pause(self):
        segments = [seg(0.0, 1.0, 'one'), seg(2.5, 3.0, 'two')]  # exactly 1.5s
        self.assertEqual(transcript.to_lines(segments), [(0.0, 'one two')])

    def test_splits_two_sentences_inside_one_piece(self):
        # Creator subtitles often put two sentences in one cue
        segments = [seg(5.0, 8.0, 'Hi there. How are you?')]
        self.assertEqual(transcript.to_lines(segments), [(5.0, 'Hi there.'), (5.0, 'How are you?')])

    def test_does_not_end_a_line_after_a_title_abbreviation(self):
        segments = [seg(0.0, 1.0, 'Mr.'), seg(0.5, 2.0, 'Smith said hi.')]
        self.assertEqual(transcript.to_lines(segments), [(0.0, 'Mr. Smith said hi.')])


class FormatTxtTests(unittest.TestCase):
    def test_uses_minutes_and_seconds_for_videos_under_an_hour(self):
        lines = [Line(17.52, 'All my life I been this way.'), Line(65.9, 'Next line')]
        self.assertEqual(transcript.format_txt(lines, duration=471),
                         '[00:17] All my life I been this way.\n[01:05] Next line\n')

    def test_adds_hours_for_videos_an_hour_or_longer(self):
        lines = [Line(17.0, 'start'), Line(3723.4, 'later')]
        self.assertEqual(transcript.format_txt(lines, duration=3600),
                         '[0:00:17] start\n[1:02:03] later\n')

    def test_adds_hours_when_a_line_passes_an_hour_even_without_a_duration(self):
        self.assertEqual(transcript.format_txt([Line(4000, 'x')], duration=None), '[1:06:40] x\n')


class ToTxtTests(unittest.TestCase):
    def test_renders_a_transcript_as_timestamped_sentences(self):
        t = {'source': 'auto', 'segments': [seg(17.52, 21.52, 'All my'), seg(19.6, 24.0, 'life.')]}
        self.assertEqual(transcript.to_txt(t, duration=60), '[00:17] All my life.\n')


class FakeYDL:
    # Stands in for yt_dlp.YoutubeDL: serves a fixed .srt body and records requests
    def __init__(self, body):
        self.body = body
        self.requested = []

    def urlopen(self, url):
        self.requested.append(url)
        return io.BytesIO(self.body.encode('utf-8'))


class GetTranscriptTests(unittest.TestCase):
    def test_fetches_the_chosen_track_and_returns_source_and_segments(self):
        ydl = FakeYDL('1\n00:00:01,000 --> 00:00:02,500\nHello there.\n')
        info = {'subtitles': {}, 'automatic_captions': {'en-orig': track('en-orig')}}
        result = transcript.get_transcript(ydl, info)
        self.assertEqual(ydl.requested, ['en-orig.srt'])
        self.assertEqual(result, {'source': 'auto',
                                  'segments': [{'start': 1.0, 'end': 2.5, 'text': 'Hello there.'}]})

    def test_returns_none_without_fetching_when_no_english_track(self):
        ydl = FakeYDL('')
        info = {'automatic_captions': {'ja-orig': track('ja-orig')}}
        self.assertIsNone(transcript.get_transcript(ydl, info))
        self.assertEqual(ydl.requested, [])


if __name__ == '__main__':
    unittest.main()
