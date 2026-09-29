import os
import tempfile
import time
import unittest
from unittest.mock import patch

from tiktok_token_store import load_tokens, save_tokens
from publishers import tiktok_publisher

class Resp:
    def raise_for_status(self): pass
    def json(self): return {"access_token": "fresh", "refresh_token": "rotated", "open_id": "creator-1", "expires_in": 86400}

class TikTokTokenTests(unittest.TestCase):
    def test_refresh_rotates_and_persists_privately(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.dict(os.environ, {"TIKTOK_TOKEN_FILE": d + "/token.json", "TIKTOK_CLIENT_KEY": "key", "TIKTOK_CLIENT_SECRET": "secret", "TIKTOK_EXPECTED_OPEN_ID": "creator-1"}):
                save_tokens({"open_id": "creator-1", "access_token": "old", "refresh_token": "old-refresh", "expires_at": time.time() - 1})
                with patch.object(tiktok_publisher.requests, "post", return_value=Resp()) as post:
                    self.assertEqual(tiktok_publisher._token(), "fresh")
                    self.assertEqual(post.call_args.kwargs["data"]["refresh_token"], "old-refresh")
                self.assertEqual(load_tokens()["refresh_token"], "rotated")
                self.assertEqual(os.stat(d + "/token.json").st_mode & 0o777, 0o600)

    def test_wrong_account_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.dict(os.environ, {"TIKTOK_TOKEN_FILE": d + "/token.json", "TIKTOK_EXPECTED_OPEN_ID": "different"}):
                save_tokens({"open_id": "creator-1", "access_token": "old", "refresh_token": "old-refresh", "expires_at": time.time() + 86400})
                with self.assertRaises(RuntimeError):
                    tiktok_publisher._token()

    def test_no_legacy_static_token_fallback(self):
        with patch.dict(os.environ, {"TIKTOK_ACCESS_TOKEN": "stale"}, clear=True):
            with self.assertRaises(RuntimeError):
                tiktok_publisher._token()
