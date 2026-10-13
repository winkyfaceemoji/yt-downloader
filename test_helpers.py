import unittest

import helpers


class SortCommentsTests(unittest.TestCase):
    def test_orders_most_liked_first_with_missing_likes_last(self):
        comments = [{'like_count': 5}, {'like_count': None}, {'like_count': 812}, {}]
        self.assertEqual([c.get('like_count') for c in helpers.sort_comments(comments)], [812, 5, None, None])

    def test_no_comments_gives_an_empty_list(self):
        self.assertEqual(helpers.sort_comments(None), [])


class ParseChoiceTests(unittest.TestCase):
    def test_reads_letters_and_words_in_any_case_or_spacing(self):
        cases = {'a': (True, False), 'Audio': (True, False), 'v': (False, True), ' VIDEO ': (False, True),
                 'b': (True, True), 'both': (True, True)}
        for answer, expected in cases.items():
            self.assertEqual(helpers.parse_choice(answer), expected, answer)

    def test_anything_else_downloads_nothing(self):
        for answer in ('', 'x', 'yes', 'n'):
            self.assertEqual(helpers.parse_choice(answer), (False, False), answer)


class IsPlaylistTests(unittest.TestCase):
    def test_playlists_and_multi_video_results_count(self):
        self.assertTrue(helpers.is_playlist({'_type': 'playlist'}))
        self.assertTrue(helpers.is_playlist({'_type': 'multi_video'}))

    def test_a_single_video_does_not(self):
        self.assertFalse(helpers.is_playlist({'_type': 'url'}))
        self.assertFalse(helpers.is_playlist({'id': 'abc'}))


if __name__ == '__main__':
    unittest.main()
