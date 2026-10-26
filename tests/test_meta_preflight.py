import json
import os
import unittest
from unittest.mock import patch
from scripts import meta_preflight as preflight


class PreflightTests(unittest.TestCase):
    def environment(self):
        return {"META_APP_ID":"999", "META_USER_ACCESS_TOKEN":"user",
                "META_PAGE_TOKEN_ENV_MAP":'{"111":"META_A_PAGE_TOKEN","222":"META_B_PAGE_TOKEN"}',
                "META_A_PAGE_TOKEN":"a", "META_B_PAGE_TOKEN":"b"}

    def user_metadata(self):
        return {"data":{"is_valid":True,"app_id":"999","type":"USER",
            "granular_scopes":[{"scope":s,"target_ids":["111","222"]} for s in
                ["pages_show_list","pages_read_engagement","pages_manage_posts"]]}}

    def test_two_pages_get_only(self):
        page={"data":{"is_valid":True,"type":"PAGE","app_id":"999"}}
        with patch.dict(os.environ,self.environment(),clear=True), patch.object(preflight,"get",side_effect=[self.user_metadata(),{"id":"111"},page,{"id":"222"},page]) as get:
            result=preflight.check()
        self.assertEqual(result["http_methods"],["GET"])
        self.assertFalse(result["published"])
        self.assertEqual(get.call_count,5)

    def test_extra_page_grant_fails_before_page_reads(self):
        metadata=self.user_metadata();metadata["data"]["granular_scopes"][0]["target_ids"].append("333")
        with patch.dict(os.environ,self.environment(),clear=True), patch.object(preflight,"get",return_value=metadata) as get:
            with self.assertRaises(ValueError):preflight.check()
        self.assertEqual(get.call_count,1)

    def test_wrong_page_token_fails(self):
        with patch.dict(os.environ,self.environment(),clear=True), patch.object(preflight,"get",side_effect=[self.user_metadata(),{"id":"333"},{"data":{}}]):
            with self.assertRaises(ValueError):preflight.check()
