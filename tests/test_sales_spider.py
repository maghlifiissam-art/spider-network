import tempfile
import unittest
from pathlib import Path

from sales_contracts import (BANNED_PHRASES, CommissionRecord, DealOutcome, Lead,
                             ObjectionScript, ReplyDraft)
from sales_spider import OfflineAdapter, SalesSpider

ROOT = Path(__file__).resolve().parents[1]


class SalesContractTests(unittest.TestCase):
    def test_lead_requires_source_ref(self):
        with self.assertRaises(ValueError):
            Lead("l1", "whatsapp", "", "labor-book-2026", "2026-09-21T00:00:00Z").validate()

    def test_lead_requires_valid_timestamp(self):
        with self.assertRaises(ValueError):
            Lead("l1", "whatsapp", "utm_campaign=x", "labor-book-2026", "not-a-date").validate()

    def test_draft_never_preapproved(self):
        with self.assertRaises(ValueError):
            ReplyDraft("d1", "l1", "مرحبا", approved=True).validate()

    def test_draft_never_sendable(self):
        with self.assertRaises(ValueError):
            ReplyDraft("d1", "l1", "مرحبا", send_allowed=True).validate()

    def test_won_requires_payment_verified(self):
        with self.assertRaises(ValueError):
            DealOutcome("l1", "labor-book-2026", "won", 30, payment_verified=False).validate()

    def test_hype_rejected(self):
        with self.assertRaises(ValueError):
            ObjectionScript("o1", ("ثمن",), f"المنتج فيه {BANNED_PHRASES[0]}").validate()

    def test_commission_within_gross(self):
        with self.assertRaises(ValueError):
            CommissionRecord("c1", "l1", "sku", 30, 31, "owner").validate()


class SalesSpiderTests(unittest.TestCase):
    def run_pilot(self, tmp):
        return SalesSpider(OfflineAdapter(ROOT / "fixtures"), tmp).run_pilot()

    def test_offline_pilot_is_deterministic_and_safe(self):
        with tempfile.TemporaryDirectory() as d:
            a = self.run_pilot(d)
            b = self.run_pilot(d)
        self.assertEqual(a, b)
        self.assertEqual(a["contract_version"], "sales.v1")
        self.assertEqual(a["qa_decision"], "go_draft")
        self.assertFalse(a["send_allowed"])
        self.assertFalse(a["publish_allowed"])
        self.assertTrue(a["zero_cost"])

    def test_invalid_and_inactive_leads_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            result = self.run_pilot(d)
        reasons = {r["lead"]: r["reason"] for r in result["rejected_leads"]}
        self.assertIn("lead-004", reasons)  # missing source_ref
        self.assertIn("lead-005", reasons)  # inactive product (Oranuss pending)
        self.assertEqual(result["qualified_leads"], ["lead-001", "lead-002", "lead-003"])

    def test_objection_matching(self):
        with tempfile.TemporaryDirectory() as d:
            result = self.run_pilot(d)
        by_lead = {dr["lead_id"]: dr for dr in result["reply_drafts"]}
        self.assertEqual(by_lead["lead-001"]["objection_id"], "price-objection")
        self.assertEqual(by_lead["lead-002"]["objection_id"], "delivery-question")
        self.assertEqual(by_lead["lead-003"]["objection_id"], "trust-objection")
        for dr in result["reply_drafts"]:
            self.assertFalse(dr["approved"])
            self.assertFalse(dr["send_allowed"])

    def test_won_deal_commission_and_attribution(self):
        with tempfile.TemporaryDirectory() as d:
            result = self.run_pilot(d)
        self.assertEqual(len(result["commissions"]), 1)
        comm = result["commissions"][0]
        self.assertEqual(comm["lead_id"], "lead-001")
        self.assertEqual(comm["gross_mad"], 30)
        self.assertEqual(comm["commission_mad"], 30)
        campaigns = {a["lead_id"]: a["campaign"] for a in result["attribution"]}
        self.assertEqual(campaigns["lead-001"], "labor-book-fb-week1")
        self.assertEqual(campaigns["lead-003"], "permis-b-tiktok-week1")


if __name__ == "__main__":
    unittest.main()
