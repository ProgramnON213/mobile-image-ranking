#!/usr/bin/env python3
import os
import sys
import unittest
import tempfile
import shutil
import pickle
from pathlib import Path

# Add project root and gallery-dl to python path
ROOT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "gallery-dl"))

from batchManualProcessing7 import is_safe_subpath
from pickWallpaper_ui import load_safe_cache, save_safe_cache


class MaliciousExploit:
    """Simulates an arbitrary bytecode execution payload via pickle."""
    def __reduce__(self):
        return (os.system, ("echo VULNERABLE",))


class TestSecurityAndContainment(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="gallery_dl_sec_test_")
        self.root_folder = Path(self.test_dir) / "safe_album"
        self.root_folder.mkdir(parents=True)
        self.outside_folder = Path(self.test_dir) / "outside_dir"
        self.outside_folder.mkdir(parents=True)

        self.safe_file = self.root_folder / "img1.jpg"
        self.safe_file.write_text("dummy")

        self.outside_file = self.outside_folder / "secret.txt"
        self.outside_file.write_text("secret_data")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_safe_path_inside_root(self):
        """Verifies legitimate files inside the active folder pass containment check."""
        self.assertTrue(is_safe_subpath(str(self.safe_file), str(self.root_folder)))

    def test_rejection_of_outside_path(self):
        """Verifies attempts to access files outside active directory are blocked."""
        self.assertFalse(is_safe_subpath(str(self.outside_file), str(self.root_folder)))

    def test_rejection_of_path_traversal_dotdot(self):
        """Verifies ../ path traversal sequences are resolved and rejected."""
        traversal_path = str(self.root_folder / ".." / "outside_dir" / "secret.txt")
        self.assertFalse(is_safe_subpath(traversal_path, str(self.root_folder)))

    def test_rejection_of_empty_or_none_inputs(self):
        """Verifies defensive handling of None, empty strings, and malformed inputs."""
        self.assertFalse(is_safe_subpath(None, str(self.root_folder)))
        self.assertFalse(is_safe_subpath("", str(self.root_folder)))
        self.assertFalse(is_safe_subpath(str(self.safe_file), None))
        self.assertFalse(is_safe_subpath(str(self.safe_file), ""))

    def test_subfolder_containment(self):
        """Verifies files in nested subfolders inside root pass containment check."""
        nested = self.root_folder / "sub" / "deep"
        nested.mkdir(parents=True)
        nested_file = nested / "nested.png"
        nested_file.write_text("nested")
        self.assertTrue(is_safe_subpath(str(nested_file), str(self.root_folder)))

    def test_safe_cache_serialization_and_rce_blocking(self):
        """Verifies safe cache serialization saves/loads cleanly and blocks malicious pickle payloads."""
        cache_file = self.root_folder / "test_cache.pkl"
        test_data = {"phone_width": 1080, "phone_height": 2460, "entries": {}}

        save_safe_cache(cache_file, test_data)
        self.assertTrue(cache_file.exists())

        loaded = load_safe_cache(cache_file)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.get("phone_width"), 1080)

        # Now test malicious pickle payload rejection
        exploit_file = self.root_folder / "exploit.pkl"
        with open(exploit_file, "wb") as f:
            pickle.dump(MaliciousExploit(), f)

        # load_safe_cache must refuse to execute the exploit and return None
        result = load_safe_cache(exploit_file)
        self.assertIsNone(result, "Malicious pickle payload must be rejected!")


if __name__ == "__main__":
    unittest.main()
