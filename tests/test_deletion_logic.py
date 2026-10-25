#!/usr/bin/env python3
import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

from delete_discarded import find_file


class TestDeletionLogic(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="gallery_dl_del_test_")
        self.root = Path(self.temp_dir)
        
        (self.root / "album_a").mkdir()
        (self.root / "album_b").mkdir()

        self.file_a = self.root / "album_a" / "photo.jpg"
        self.file_b = self.root / "album_b" / "photo.jpg"
        self.file_unique = self.root / "album_a" / "unique.jpg"

        self.file_a.write_text("photo A")
        self.file_b.write_text("photo B")
        self.file_unique.write_text("unique")

        self.dir_map = {}
        for dirpath, _, filenames in os.walk(str(self.root)):
            for f in filenames:
                f_lower = f.lower()
                self.dir_map.setdefault(f_lower, []).append(os.path.join(dirpath, f))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_direct_relative_path_match(self):
        """Verifies exact relative path correctly resolves to target file."""
        found = find_file(str(self.root), "album_a/photo.jpg", self.dir_map)
        self.assertIsNotNone(found)
        self.assertEqual(Path(found).resolve(), self.file_a.resolve())

    def test_unique_basename_fallback(self):
        """Verifies basename fallback works when there is no duplicate collision."""
        found = find_file(str(self.root), "unique.jpg", self.dir_map)
        self.assertIsNotNone(found)
        self.assertEqual(Path(found).resolve(), self.file_unique.resolve())

    def test_duplicate_basename_collision_is_safely_skipped(self):
        """
        Critical Safety Test:
        When two files share 'photo.jpg' and no relative directory is specified,
        find_file must NOT delete an arbitrary match. It must return None.
        """
        found = find_file(str(self.root), "photo.jpg", self.dir_map)
        self.assertIsNone(found, "Collision must return None to prevent deleting the wrong file.")

    def test_relative_suffix_resolves_duplicate_collision(self):
        """Verifies if relative suffix matches one of the duplicates, it resolves correctly."""
        found = find_file(str(self.root), "album_b/photo.jpg", self.dir_map)
        self.assertIsNotNone(found)
        self.assertEqual(Path(found).resolve(), self.file_b.resolve())

    def test_path_traversal_in_json_is_rejected(self):
        """Verifies candidate paths attempting to break out of root return None."""
        found = find_file(str(self.root), "../../../outside_secret.jpg", self.dir_map)
        self.assertIsNone(found)


if __name__ == "__main__":
    unittest.main()
