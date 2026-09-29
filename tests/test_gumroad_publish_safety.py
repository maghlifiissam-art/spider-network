import os
import unittest
from unittest.mock import patch
import gumroad_publish as g

class Response:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): pass
    def json(self): return self.payload

class GumroadSafetyTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    @patch.object(g.requests, 'post')
    def test_missing_token_fails_closed(self, post):
        self.assertFalse(g.publish_product('123')['success'])
        post.assert_not_called()

    @patch.dict(os.environ, {'GUMROAD_ACCESS_TOKEN': 'fake'})
    @patch.object(g.requests, 'get')
    @patch.object(g.requests, 'post')
    def test_documented_post_and_readback(self, post, get):
        post.return_value = Response({'success': True, 'product': {'id': '123'}})
        get.return_value = Response({'success': True, 'product': {'id': '123', 'published': True, 'files': [{'id': 'f'}]}})
        self.assertTrue(g.publish_product('123')['success'])
        self.assertEqual(post.call_args.args[0], g.API_BASE + '/products/123/enable')

    @patch.dict(os.environ, {'GUMROAD_ACCESS_TOKEN': 'fake'})
    @patch.object(g.requests, 'post')
    def test_create_is_draft(self, post):
        post.return_value = Response({'success': True, 'product': {'id': '123', 'published': False}})
        self.assertTrue(g.create_product('Test', 900, 'https://example.org/file')['success'])
        self.assertEqual(post.call_args.kwargs['data']['draft'], 'true')
