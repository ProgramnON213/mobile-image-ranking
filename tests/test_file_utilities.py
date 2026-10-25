#!/usr/bin/env python3
import os
import sys
import tempfile
import shutil
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "gallery-dl"))

from dumpFile import flat_copy
from findNonImageFile import copy_non_images
from imageToVector import load_existing_data, save_data, extract_features
import numpy as np


class TestDumpFile(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="gallery_dl_dump_test_")
        self.src = Path(self.temp_dir) / "source"
        self.src.mkdir()
        (self.src / "sub1").mkdir()
        (self.src / "sub2").mkdir()

        (self.src / "sub1" / "pic.jpg").write_text("photo 1")
        (self.src / "sub2" / "pic.jpg").write_text("photo 2")
        (self.src / "other.txt").write_text("text")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_flat_copy_basic_and_collision_renaming(self):
        """Verifies files are flattened and duplicate names are safely renamed."""
        dst = Path(self.temp_dir) / "flat_output"
        copied, renamed, _ = flat_copy(self.src, dst)

        self.assertEqual(copied, 3)
        self.assertEqual(renamed, 1)

        # Output should contain pic.jpg, pic_1.jpg, and other.txt
        out_files = sorted([p.name for p in dst.iterdir()])
        self.assertIn("pic.jpg", out_files)
        self.assertIn("pic_1.jpg", out_files)
        self.assertIn("other.txt", out_files)

    def test_flat_copy_rejects_identical_directories(self):
        """Verifies flat_copy raises ValueError if destination matches source."""
        with self.assertRaises(ValueError):
            flat_copy(self.src, self.src)

    def test_flat_copy_prevents_infinite_recursion(self):
        """Verifies destination folder inside source does not trigger an infinite loop."""
        nested_dst = self.src / "dumped_flat"
        nested_dst.mkdir()

        copied, _, _ = flat_copy(self.src, nested_dst)
        # Should only copy the original 3 files and NOT recurse into dumped_flat
        self.assertEqual(copied, 3)
        out_files = [p.name for p in nested_dst.iterdir()]
        self.assertEqual(len(out_files), 3)


class TestDeleteByFilenameLogic(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="gallery_dl_del_fn_test_")
        self.dir_a = Path(self.temp_dir) / "target_a"
        self.dir_b = Path(self.temp_dir) / "ref_b"
        self.dir_a.mkdir()
        self.dir_b.mkdir()

        # Same name, SAME size (Exact duplicate -> should delete)
        (self.dir_a / "duplicate.jpg").write_bytes(b"exact content 1234")
        (self.dir_b / "duplicate.jpg").write_bytes(b"exact content 1234")

        # Same name, DIFFERENT size (Different image -> MUST NOT delete)
        (self.dir_a / "different.jpg").write_bytes(b"small")
        (self.dir_b / "different.jpg").write_bytes(b"much larger file content here")

        # Unique file in A
        (self.dir_a / "unique_a.jpg").write_bytes(b"unique")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_size_guard_protects_unrelated_files(self):
        """Verifies files matching by filename but with differing sizes are spared from deletion."""
        # Simulate step 3 & 4 of delete_by_filename logic
        files_b = {}
        for f in os.listdir(self.dir_b):
            p = self.dir_b / f
            if p.is_file():
                files_b[f.lower()] = os.path.getsize(p)

        matches = []
        skipped_size_mismatch = 0
        for f in os.listdir(self.dir_a):
            p = self.dir_a / f
            if p.is_file():
                f_lower = f.lower()
                if f_lower in files_b:
                    size = os.path.getsize(p)
                    if size == files_b[f_lower]:
                        matches.append(f)
                    else:
                        skipped_size_mismatch += 1

        self.assertEqual(matches, ["duplicate.jpg"])
        self.assertEqual(skipped_size_mismatch, 1)
        self.assertNotIn("different.jpg", matches, "Files with different sizes must not be marked for deletion!")


class TestFindNonImageFile(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="gallery_dl_non_img_test_")
        self.src = Path(self.temp_dir) / "src"
        self.src.mkdir()
        (self.src / "img.jpg").write_bytes(b"img")
        (self.src / "img.png").write_bytes(b"png")
        (self.src / "notes.txt").write_bytes(b"notes")
        (self.src / "metadata.json").write_bytes(b"json")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_copies_only_non_images(self):
        """Verifies only non-image files are copied."""
        dst = Path(self.temp_dir) / "output"
        copy_non_images(self.src, dst)

        out_files = sorted([p.name for p in dst.iterdir()])
        self.assertEqual(out_files, ["metadata.json", "notes.txt"])

    def test_prevents_infinite_recursion_into_nested_destination(self):
        """Verifies non-image copy terminates safely when destination is inside source."""
        nested_dst = self.src / "non_images_backup"
        copy_non_images(self.src, nested_dst)

        out_files = sorted([p.name for p in nested_dst.iterdir()])
        self.assertEqual(out_files, ["metadata.json", "notes.txt"])


class TestImageToVectorPyTorch(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="gallery_dl_vec_test_")
        self.src = Path(self.temp_dir) / "images"
        self.src.mkdir()
        self.out_npz = Path(self.temp_dir) / "features.npz"

        # Create two simple dummy images using Pillow
        from PIL import Image
        img1 = Image.new("RGB", (64, 64), color="blue")
        img1.save(self.src / "blue.jpg")
        img2 = Image.new("RGB", (64, 64), color="green")
        img2.save(self.src / "green.png")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_pytorch_mobilenet_extraction_and_incremental_cache(self):
        """Verifies PyTorch MobileNetV2 extracts 1280-dim unit vectors and caches to .npz."""
        extract_features(str(self.src), str(self.out_npz), batch_size=2)
        self.assertTrue(self.out_npz.exists())

        filenames, vectors = load_existing_data(str(self.out_npz))
        self.assertEqual(len(filenames), 2)
        self.assertEqual(vectors.shape, (2, 1280))

        # Check unit L2 norm
        norms = np.linalg.norm(vectors, axis=1)
        np.testing.assert_allclose(norms, [1.0, 1.0], rtol=1e-5)

        # Test incremental addition of a 3rd image
        from PIL import Image
        img3 = Image.new("RGB", (64, 64), color="red")
        img3.save(self.src / "red.jpg")

        extract_features(str(self.src), str(self.out_npz), batch_size=2)
        filenames_inc, vectors_inc = load_existing_data(str(self.out_npz))
        self.assertEqual(len(filenames_inc), 3)
        self.assertEqual(vectors_inc.shape, (3, 1280))


if __name__ == "__main__":
    unittest.main()
