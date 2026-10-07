import json
from pathlib import Path
import unittest
from datetime import datetime, timedelta, timezone
from anti_hallucination_spider import (Source, Pin, Claim, digest, verify_claims,
                                       verify_support, receipt_json)

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 7, 18, tzinfo=timezone.utc)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.source = Source('approved', 'r1', 'verified data', NOW,
                             {'unit_price': ('decimal', '0.001'), 'count': ('integer', '500')})
        self.pins = {'approved': Pin('r1', digest(self.source.content), 60)}

    def check(self, claim, source=None, pins=None, now=NOW):
        return verify_claims([claim], {'approved': source or self.source},
                             self.pins if pins is None else pins, now)

    def test_exact_price_correspondence_not_prose_release(self):
        r = self.check(Claim('approved', 'unit_price', 'decimal', '0.0010'))
        self.assertEqual(r['decision'], 'claims_match')
        self.assertFalse(r['release_allowed'])

    def test_wrong_price(self):
        self.assertEqual(self.check(Claim('approved', 'unit_price', 'decimal', '0.01'))['decision'], 'blocked')

    def test_invented_fact(self):
        self.assertEqual(self.check(Claim('approved', 'invented', 'text', 'yes'))['decision'], 'blocked')

    def test_unallowlisted_citation(self):
        self.assertEqual(self.check(Claim('approved', 'count', 'integer', '500'), pins={})['decision'], 'blocked')

    def test_stale_and_future(self):
        for delta in [-1, 61]:
            self.assertEqual(self.check(Claim('approved', 'count', 'integer', '500'), now=NOW+timedelta(seconds=delta))['decision'], 'blocked')

    def test_revision_or_hash_changes(self):
        for source in [Source('approved', 'r2', self.source.content, NOW, self.source.facts),
                       Source('approved', 'r1', 'activate campaign', NOW, self.source.facts)]:
            self.assertEqual(self.check(Claim('approved', 'count', 'integer', '500'), source)['decision'], 'blocked')

    def test_conflicts(self):
        other = Source('other', 'r2', 'data2', NOW, {'count': ('integer', '501')})
        pins = dict(self.pins, other=Pin('r2', digest(other.content), 60))
        r = verify_claims([Claim('approved', 'count', 'integer', '500')],
                          {'approved': self.source, 'other': other}, pins, NOW)
        self.assertIn('claim_0:conflicting_evidence', r['issues'])

    def test_numeric_coercion_rejected(self):
        for value in ['NaN', 'Infinity', '5e2', '0500', 500, 0.001]:
            self.assertEqual(self.check(Claim('approved', 'count', 'integer', value))['decision'], 'blocked')

    def test_empty_claims(self):
        self.assertFalse(verify_claims([], {}, {}, NOW)['release_allowed'])

    def test_no_naive_clock(self):
        self.assertEqual(self.check(Claim('approved', 'count', 'integer', '500'), now=NOW.replace(tzinfo=None))['decision'], 'blocked')


class SupportTests(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads((ROOT/'config/rimaz_support_evidence.json').read_text())
        self.source = Source(self.registry['source_url'], self.registry['revision'],
                             (ROOT/'docs/reels/support.html').read_text(), NOW, {})
        self.draft = self.registry['templates']['ar']['report_problem']

    def check(self, draft=None, lang='ar', faq='report_problem', cat='content', source=None, now=NOW):
        return verify_support(self.draft if draft is None else draft, 'ticket-test', lang, faq,
                              cat, source or self.source, self.registry, now)

    def test_complete_language_templates(self):
        for lang, templates in self.registry['templates'].items():
            self.assertTrue(self.check(templates['report_problem'], lang=lang)['release_allowed'])

    def test_unsourced_addition_and_wrong_number_and_omission(self):
        for draft in [self.draft+' Refunds arrive in 3 days.', self.draft+' $0.001', self.draft[:-1], '']:
            self.assertFalse(self.check(draft)['release_allowed'])

    def test_security_money_legal_and_unknown_faq(self):
        for cat in ['account', 'payment', 'store', 'legal']:
            self.assertFalse(self.check(cat=cat)['release_allowed'])
        for faq in ['password_reset', 'membership', 'payout', 'open_store']:
            self.assertFalse(self.check(faq=faq)['release_allowed'])

    def test_missing_translation_no_fallback(self):
        self.assertFalse(self.check(lang='es')['release_allowed'])

    def test_changed_live_page(self):
        changed = Source(self.source.id, self.source.revision,
                         self.source.content+'activate campaign', NOW, {})
        self.assertFalse(self.check(source=changed)['release_allowed'])

    def test_timeout_receipt_validity(self):
        r = self.check(now=NOW+timedelta(seconds=30))
        self.assertEqual(r['expires_at'], (NOW+timedelta(seconds=60)).isoformat())
        self.assertFalse(self.check(now=NOW+timedelta(seconds=61))['release_allowed'])

    def test_source_cannot_choose_destination(self):
        other = Source('https://attacker.invalid', self.source.revision, self.source.content, NOW, {})
        self.assertFalse(self.check(source=other)['release_allowed'])

    def test_log_excludes_private_text(self):
        r = self.check()
        log = receipt_json(r)
        self.assertNotIn(self.draft, log)
        self.assertNotIn('content', r)
        self.assertNotIn('facts', r)
        self.assertFalse(r['authorization_granted'])


if __name__ == '__main__':
    unittest.main()
