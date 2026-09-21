# Sales Spider (sales.v1)

Draft-only sales agent for Spider Network: qualifies leads, prepares persuasion
replies in Darija/Arabic, closes only payment-verified deals, and records
attribution and commissions. Built on the same offline-first, fail-closed
pattern as Media Spider and Bullet Spider.

## Hard gates (enforced in code, not config)

- `ReplyDraft.send_allowed` is always `False`: the agent never messages a customer.
- Drafts are never pre-approved; a human flips the decision in the review page.
- A deal can only be `won` when `payment_verified` is `True`.
- A lead without `source_ref` is rejected: attribution is mandatory.
- Hype phrases (`BANNED_PHRASES`) fail validation everywhere they appear.
- No publishing, no spending, no new secrets or API keys.

## Pipeline stages

`lead_intake → qualify → reply_draft → close_check → confirm_order → attribution → commission_log → handoff`

Handoff target: `secure_delivery_flow` (payment verification, then email
delivery within 24h). Customer messaging stays a human-approved relay.

## Files

- `sales_contracts.py` — versioned fail-closed contracts (Product, Lead,
  ObjectionScript, ReplyDraft, DealOutcome, AttributionEvent, CommissionRecord)
- `sales_spider.py` — deterministic orchestrator + `OfflineAdapter`
- `config/sales.yaml` — human-edited ops config: products, prices, gates
- `pages/10_Sales_Spider.py` — Streamlit review page (queue, drafts, deals,
  attribution, commissions)
- `schemas/sales_*.schema.json` — lead, reply draft, deal, commission contracts
- `fixtures/sales_pilot.json` — offline pilot scenario
- `tests/test_sales_spider.py`, `tests/fixtures_sales_leads.json` — 11 tests
- Boss route: `sales_pipeline` in `boss_spider.py` (drafts only)

## Run

```bash
python -m unittest tests.test_sales_spider -v
streamlit run app.py   # then open the "Sales Spider" page
```

## Integration points (future, each behind its own approval)

- Tally order submissions → lead intake
- WhatsApp conversations → reply drafts (via human-approved relay only)
- Campaign links (UTM) → attribution and per-ad performance
- Oranuss affiliate program → stays inactive until official link, products
  and commission terms arrive
