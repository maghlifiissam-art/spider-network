import os
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from publish_contracts import PublishJob
from publishers import meta_publisher as meta
from scripts.auth_meta import select_pages, private_json


def job(page_id=""):
    return PublishJob("job", "run", "unused.mp4", "title", "description",
                      ["facebook"], facebook_page_id=page_id)


class MetaRoutingTests(unittest.TestCase):
    def test_dry_run_never_calls_network(self):
        with patch.object(meta.requests, "post") as post:
            self.assertEqual(meta.publish_facebook(job(), True).status, "dry_run")
            post.assert_not_called()

    def test_no_implicit_page_even_with_legacy_credentials(self):
        with patch.dict(os.environ, {"META_PAGE_ID": "111", "META_PAGE_ACCESS_TOKEN": "secret"}, clear=True):
            self.assertEqual(meta.publish_facebook(job(), False).status, "failed")

    def test_explicit_routing_is_independent_of_order(self):
        env = {"META_PAGE_TOKEN_ENV_MAP": '{"222":"META_B_PAGE_TOKEN","111":"META_A_PAGE_TOKEN"}',
               "META_A_PAGE_TOKEN": "first", "META_B_PAGE_TOKEN": "second"}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(meta._facebook_destination(job("111")), ("first", "111"))
            self.assertEqual(meta._facebook_destination(job("222")), ("second", "222"))
            with self.assertRaises(ValueError):
                meta._facebook_destination(job("333"))

    def test_secret_cannot_be_used_as_mapping_variable(self):
        with patch.dict(os.environ, {"META_PAGE_TOKEN_ENV_MAP": '{"111":"raw-token"}'}, clear=True):
            with self.assertRaises(ValueError): meta._facebook_destination(job("111"))

    def test_missing_secret_and_malformed_mapping_fail_closed(self):
        for mapping in ['{"111":"META_A_PAGE_TOKEN"}', '[]', 'bad']:
            with patch.dict(os.environ, {"META_PAGE_TOKEN_ENV_MAP": mapping}, clear=True):
                with self.assertRaises(ValueError): meta._facebook_destination(job("111"))

    def test_auth_selection_requires_all_explicit_pages(self):
        pages = [{"id":"222", "tasks":["CREATE_CONTENT"], "access_token":"b"},
                 {"id":"111", "tasks":["CREATE_CONTENT"], "access_token":"a"}]
        self.assertEqual(set(select_pages(pages, {"111", "222"})), {"111", "222"})
        with self.assertRaises(ValueError): select_pages(pages, {"111", "333"})
        with self.assertRaises(ValueError): select_pages([{"id":"111"}], {"111"})

    def test_network_exception_never_leaks_token(self):
        env = {"META_PAGE_TOKEN_ENV_MAP": '{"111":"META_A_PAGE_TOKEN"}', "META_A_PAGE_TOKEN":"secret-sentinel"}
        with patch.dict(os.environ, env, clear=True), patch("builtins.open"), patch.object(meta.requests, "post", side_effect=Exception("secret-sentinel")):
            receipt = meta.publish_facebook(job("111"), False)
            self.assertEqual(receipt.status, "failed")
            self.assertNotIn("secret-sentinel", receipt.detail)

    def test_non_string_page_id_fails_closed(self):
        with self.assertRaises(ValueError): meta._facebook_destination(job(111))

    def test_private_output_never_overwrites_and_has_restricted_mode(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "credentials.json"
            private_json(path, {"fictitious": "sentinel"})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError): private_json(path, {})
