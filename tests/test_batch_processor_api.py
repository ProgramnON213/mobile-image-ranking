#!/usr/bin/env python3
import os
import sys
import json
import time
import urllib.request
import urllib.error
import urllib.parse
import tempfile
import shutil
import threading
from pathlib import Path
import unittest

ROOT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "gallery-dl"))

from batchManualProcessing7 import ThreadingHTTPServer, BatchProcessorHandler, find_free_port
import batchManualProcessing7


class TestBatchProcessorAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="gallery_dl_api_test_")
        cls.root = Path(cls.test_dir) / "images"
        cls.root.mkdir()
        cls.outside = Path(cls.test_dir) / "outside"
        cls.outside.mkdir()

        cls.test_img = cls.root / "sample.jpg"
        cls.test_img.write_bytes(b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB")
        cls.outside_img = cls.outside / "forbidden.jpg"
        cls.outside_img.write_text("protected")

        batchManualProcessing7.ACTIVE_ROOT_FOLDER = str(cls.root)
        batchManualProcessing7.INITIAL_FOLDER = str(cls.root)

        cls.port = find_free_port(8910)
        cls.server = ThreadingHTTPServer(("localhost", cls.port), BatchProcessorHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://localhost:{cls.port}"
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_cors_header_restricts_external_origins(self):
        """Verifies untrusted origins do not receive permissive Access-Control-Allow-Origin."""
        req = urllib.request.Request(f"{self.base_url}/api/init_info", headers={"Origin": "https://malicious-site.com"})
        with urllib.request.urlopen(req) as resp:
            cors_header = resp.headers.get("Access-Control-Allow-Origin")
            self.assertNotEqual(cors_header, "*")
            self.assertNotEqual(cors_header, "https://malicious-site.com")

    def test_cors_header_allows_local_origin(self):
        """Verifies localhost origin receives proper Access-Control-Allow-Origin."""
        req = urllib.request.Request(f"{self.base_url}/api/init_info", headers={"Origin": f"http://localhost:{self.port}"})
        with urllib.request.urlopen(req) as resp:
            cors_header = resp.headers.get("Access-Control-Allow-Origin")
            self.assertEqual(cors_header, f"http://localhost:{self.port}")

    def test_raw_image_inside_boundary_returns_200(self):
        """Verifies requesting an image inside the active root streams successfully."""
        url = f"{self.base_url}/api/raw_image?path={urllib.parse.quote(str(self.test_img))}"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = resp.read()
            self.assertTrue(len(data) > 0)

    def test_raw_image_outside_boundary_returns_403(self):
        """Verifies requesting an image outside the active root returns 403 Forbidden."""
        url = f"{self.base_url}/api/raw_image?path={urllib.parse.quote(str(self.outside_img))}"
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(url)
        self.assertEqual(ctx.exception.code, 403)

    def test_delete_endpoint_rejects_out_of_boundary_paths(self):
        """Verifies /api/delete will NOT delete files outside the active directory."""
        payload = json.dumps({"paths": [str(self.outside_img)], "recycle": False}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/delete",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["deleted"], 0)
            self.assertTrue(len(data["errors"]) > 0)
            self.assertTrue(self.outside_img.exists(), "Outside file must not be deleted!")

    def test_delete_endpoint_allows_in_boundary_paths(self):
        """Verifies /api/delete deletes files inside the active directory."""
        to_del = self.root / "delete_me.jpg"
        to_del.write_text("delete me")
        payload = json.dumps({"paths": [str(to_del)], "recycle": False}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/delete",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["deleted"], 1)
            self.assertFalse(to_del.exists(), "Target file must be deleted.")


if __name__ == "__main__":
    unittest.main()
