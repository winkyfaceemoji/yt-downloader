import unittest

import transcript


def track(lang):
    # Caption list as yt-dlp reports it: several formats per language
    return [{'ext': 'json3', 'url': f'{lang}.json3'}, {'ext': 'srt', 'url': f'{lang}.srt'}]


def info(subtitles=None, automatic_captions=None):
    return {'subtitles': subtitles or {}, 'automatic_captions': automatic_captions or {}}


class Fetch:
    # The fetch(url) -> str seam: serves fixed .srt text (or raises) and records requests
    def __init__(self, text='1\n00:00:01,000 --> 00:00:02,000\nHello.\n', error=None):
        self.text, self.error, self.requested = text, error, []

    def __call__(self, url):
        self.requested.append(url)
        if self.error:
            raise self.error
        return self.text


class WhichCaptionsTests(unittest.TestCase):
    def test_prefers_creator_english_over_auto_captions(self):
        fetch = Fetch()
        result, _ = transcript.get_transcript(info({'en': track('en')}, {'en-orig': track('en-orig')}), fetch)
        self.assertEqual((result['source'], fetch.requested), ('manual', ['en.srt']))

    def test_accepts_creator_english_with_region(self):
        fetch = Fetch()
        result, _ = transcript.get_transcript(info({'fr': track('fr'), 'en-GB': track('en-GB')}), fetch)
        self.assertEqual((result['source'], fetch.requested), ('manual', ['en-GB.srt']))

    def test_uses_auto_captions_only_when_speech_is_english(self):
        fetch = Fetch()
        result, _ = transcript.get_transcript(info(automatic_captions={'en-orig': track('en-orig'), 'en': track('en')}), fetch)
        self.assertEqual((result['source'], fetch.requested), ('auto', ['en-orig.srt']))

    def test_rejects_machine_translated_english_without_fetching(self):
        # 'en' auto-captions without 'en-orig' are translated from another language;
        # 'en-ja' is a machine translation of creator Japanese subtitles
        fetch = Fetch()
        result, note = transcript.get_transcript(
            info({'en-ja': track('en-ja')}, {'en': track('en'), 'ja-orig': track('ja-orig')}), fetch)
        self.assertEqual((result, fetch.requested), (None, []))
        self.assertIn('no English captions', note)

    def test_falls_back_to_auto_captions_when_creator_track_has_no_srt(self):
        fetch = Fetch()
        no_srt = [{'ext': 'vtt', 'url': 'en.vtt'}]
        result, _ = transcript.get_transcript(info({'en': no_srt}, {'en-orig': track('en-orig')}), fetch)
        self.assertEqual((result['source'], fetch.requested), ('auto', ['en-orig.srt']))


class CaptionFileTests(unittest.TestCase):
    def english(self):
        return info(automatic_captions={'en-orig': track('en-orig')})

    def test_reads_cues_into_timed_segments(self):
        srt = ('1\r\n00:00:17,520 --> 00:00:21,520\r\nAll my\r\n\r\n'
               '2\r\n01:02:03,004 --> 01:02:05,000\r\nlife I been\r\nthis way\r\n')
        result, _ = transcript.get_transcript(self.english(), Fetch(srt))
        self.assertEqual(result['segments'], [
            {'start': 17.52, 'end': 21.52, 'text': 'All my'},
            {'start': 3723.004, 'end': 3725.0, 'text': 'life I been this way'},
        ])

    def test_keeps_the_readable_cues_when_one_cue_is_blank(self):
        # A blank cue in YouTube's .srt leaves a block with no timing line after it
        srt = ('1\n00:00:01,000 --> 00:00:03,000\nAll my life\n\n'
               '2\n00:00:03,000 --> 00:00:04,000\n\n\n'
               '3\n00:00:04,500 --> 00:00:06,000\nI been this way.\n')
        result, _ = transcript.get_transcript(self.english(), Fetch(srt))
        self.assertEqual([s['text'] for s in result['segments']], ['All my life', '', 'I been this way.'])

    def test_empty_caption_file_means_no_transcript(self):
        result, note = transcript.get_transcript(self.english(), Fetch(''))
        self.assertIsNone(result)
        self.assertIn('empty', note)

    def test_failed_caption_download_means_no_transcript_instead_of_an_error(self):
        result, note = transcript.get_transcript(self.english(), Fetch(error=OSError('network down')))
        self.assertIsNone(result)
        self.assertIn('network down', note)


def seg(start, end, text):
    return {'start': start, 'end': end, 'text': text}


def txt(*segments, duration=60):
    return transcript.to_txt({'source': 'auto', 'segments': list(segments)}, duration)


class ReadableTextTests(unittest.TestCase):
    def test_joins_overlapping_pieces_until_a_sentence_ends(self):
        # Real auto-captions overlap while speech is continuous
        self.assertEqual(txt(seg(17.52, 21.52, 'All my'), seg(19.60, 24.00, 'life I been'),
                             seg(21.52, 27.80, 'this way.'), seg(24.00, 27.80, 'My mom and my daddy,')),
                         '[00:17] All my life I been this way.\n[00:24] My mom and my daddy,\n')

    def test_starts_a_new_line_after_a_pause_longer_than_1_5_seconds(self):
        self.assertEqual(txt(seg(70.0, 73.0, 'hopefully'), seg(73.2, 75.4, 'place'),
                             seg(78.0, 81.5, 'father you said')),  # 2.6s of silence before this
                         '[01:10] hopefully place\n[01:18] father you said\n')

    def test_keeps_going_through_a_short_pause(self):
        self.assertEqual(txt(seg(0.0, 1.0, 'one'), seg(2.5, 3.0, 'two')), '[00:00] one two\n')  # exactly 1.5s

    def test_splits_two_sentences_inside_one_piece(self):
        # Creator subtitles often put two sentences in one cue
        self.assertEqual(txt(seg(5.0, 8.0, 'Hi there. How are you?')), '[00:05] Hi there.\n[00:05] How are you?\n')

    def test_does_not_end_a_line_after_a_title_abbreviation(self):
        self.assertEqual(txt(seg(0.0, 1.0, 'Mr.'), seg(0.5, 2.0, 'Smith said hi.')), '[00:00] Mr. Smith said hi.\n')

    def test_adds_hours_for_videos_an_hour_or_longer(self):
        self.assertEqual(txt(seg(17.0, 18.0, 'start.'), seg(3723.4, 3725.0, 'later.'), duration=3600),
                         '[0:00:17] start.\n[1:02:03] later.\n')

    def test_adds_hours_when_a_line_passes_an_hour_even_without_a_duration(self):
        self.assertEqual(txt(seg(4000, 4001, 'x'), duration=None), '[1:06:40] x\n')


if __name__ == '__main__':
    unittest.main()
