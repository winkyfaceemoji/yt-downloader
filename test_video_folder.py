import json
import os
import tempfile
import unittest

import yt_dlp

from video_folder import VideoFolder

INFO = {'id': 'ZVeQQHEkcAk', 'title': 'Sins Of The Father'}


class VideoFolderTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='test-downloads-')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.root, ignore_errors=True)

    def media_path(self, folder, info, ext):
        # Where yt-dlp would save a download made with folder.media_opts()
        opts = folder.media_opts()
        with yt_dlp.YoutubeDL({**opts, 'quiet': True}) as ydl:
            return ydl.prepare_filename({**info, 'ext': ext}, outtmpl=opts['outtmpl'])

    def test_saves_data_and_transcript_in_a_folder_named_after_the_video(self):
        path, actions = VideoFolder(self.root).save(INFO, {'id': INFO['id']}, '[00:01] Hello.\n')
        self.assertEqual(path, os.path.join(self.root, 'Sins Of The Father [ZVeQQHEkcAk]'))
        with open(os.path.join(path, 'data.json')) as f:
            self.assertEqual(json.load(f), {'id': INFO['id']})
        with open(os.path.join(path, 'transcript.txt'), encoding='utf-8') as f:
            self.assertEqual(f.read(), '[00:01] Hello.\n')
        self.assertEqual(actions, ['wrote data.json', 'wrote transcript.txt'])

    def test_a_run_without_a_transcript_removes_the_old_one(self):
        folder = VideoFolder(self.root)
        folder.save(INFO, {}, '[00:01] Hello.\n')
        path, actions = folder.save(INFO, {}, None)
        self.assertFalse(os.path.exists(os.path.join(path, 'transcript.txt')))
        self.assertEqual(actions, ['wrote data.json', 'removed stale transcript.txt'])

    def test_illegal_characters_and_slashes_never_create_subfolders(self):
        path = VideoFolder(self.root).path({'id': 'AWK0007', 'title': 'Q&A: how? | part 1/2'})
        self.assertEqual(os.path.dirname(path), self.root)

    def test_media_lands_in_the_same_folder_as_the_data_under_any_naming_config(self):
        info = {'id': 'AWK0007', 'title': 'Q&A: how? | part 1/2'}
        for naming in (None, {'restrictfilenames': True}):
            folder = VideoFolder(self.root, naming)
            self.assertEqual(os.path.dirname(self.media_path(folder, info, 'm4a')), folder.path(info), naming)

    def test_a_renamed_video_moves_its_old_folder_to_the_new_title(self):
        folder = VideoFolder(self.root)
        old, _ = folder.save(INFO, {}, None)
        open(os.path.join(old, 'Sins Of The Father [ZVeQQHEkcAk].m4a'), 'w').close()
        new, actions = folder.save({**INFO, 'title': 'Sins of the Father (Remastered)'}, {}, None)
        self.assertEqual(os.listdir(self.root), ['Sins of the Father (Remastered) [ZVeQQHEkcAk]'])
        self.assertTrue(os.path.exists(os.path.join(new, 'Sins Of The Father [ZVeQQHEkcAk].m4a')))
        self.assertEqual(actions[0], 'renamed folder from "Sins Of The Father [ZVeQQHEkcAk]"')

    def test_a_renamed_video_with_two_folders_already_leaves_both(self):
        folder = VideoFolder(self.root)
        folder.save(INFO, {}, None)
        os.makedirs(os.path.join(self.root, 'Older Title [ZVeQQHEkcAk]'))
        folder.save({**INFO, 'title': 'New Title'}, {}, None)
        self.assertEqual(sorted(os.listdir(self.root)), ['New Title [ZVeQQHEkcAk]', 'Older Title [ZVeQQHEkcAk]',
                                                          'Sins Of The Father [ZVeQQHEkcAk]'])

    def test_media_downloads_overwrite_on_a_re_run(self):
        self.assertTrue(VideoFolder(self.root).media_opts()['overwrites'])


if __name__ == '__main__':
    unittest.main()
