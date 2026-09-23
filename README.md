
### Market Spy -> Bullet contract

Market Spy emits a versioned `market_spy_handoff.v1` envelope. Bullet accepts it through `MarketSpyHandoffAdapter`, preserves `observed_at`, `profit_evidence_gate`, and `category_scorecard`, and normalizes `no-go` to `no_go` without weakening the rejection. Supported Market Spy families map as follows: `ebook` -> `digital_book`, `design_asset` -> `product_design`, `wall_art_decor` -> `decor_art`; stickers, logos, children's coloring books, illustrated stories, and physical products remain distinct categories with specialist routes. Category checks block drafts when required trademark/IP, child-safety, print-economics, rights/licensing, or user-supplied illustrated-story topic/message evidence is missing.

The allowed automation is limited to public-signal monitoring, scoring, rejection, and brief/listing drafts. Publishing, spending, account creation, and messaging as the user are forbidden. Both envelopes are drafts-only and keep human publish approval as a review gate.

# Spider Network

Spider Network is a Python workspace for a group of specialized assistants. It includes a Streamlit interface, a Boss Spider router, content and digital-product pipelines, engineering and electronics helpers, reporting, a WhatsApp bot, and Shopify/Gumroad integrations.

This repository is an early, untested integration workspace. Start with the local Streamlit interface. Keep every publishing workflow and webhook disabled until its account, secret, and dry-run behavior have been checked.

## What is included

- `app.py`: Streamlit interface for Affiliate, Media, and Digital Products spiders.
- `boss_spider.py`: command classification and routing across the specialist modules.
- `pages/`: Streamlit pages for books, Boss Spider, dashboard, and engineering.
- `book_spider.py`, `comic_spider.py`, `visual_spider.py`: content generation helpers.
- `engineering_spider.py`, `electronics_spider.py`, `cloud_architect_spider.py`: technical design helpers.
- `bullet_spider.py`: offline-first demand-capture scoring and draft production briefs from public/aggregate signals.
- `publish_spider.py` + `publishers/`: fail-closed social publishing via official APIs (YouTube Data, Meta Graph, TikTok Content Posting). See `README_PUBLISH.md`.
- `schemas/bullet_*.schema.json`: source-backed opportunity and production-brief contracts.
- `catalog.py`, `ops_log.py`: local JSON catalog and operation log.
- `webhook_server.py`: Shopify paid-order webhook and email delivery service.
- `whatsapp_bot.py`: WhatsApp Cloud API webhook and reply service.
- `.github/workflows/`: manual/scheduled publishing and monitoring jobs. Review them before enabling.
- `tests/`: local tests that do not call paid APIs or external services.

## Bullet Spider (Demand Capture)

Bullet Spider accepts Market Spy opportunity-shaped records or other **public, aggregate, authorized** demand signals. Every input must include an absolute source URL, a timezone-aware `observed_at`, geography, a named metric/proxy, confidence, and limitations. It scores purchase intent, urgency, competition, supply gap, producibility, margin and risk, then chooses one draft response. Affiliate recommendations are never random: a separate affiliate score requires demand, momentum, specific geography, competition, current price and currency, commission, freshness, provenance, confidence and risk. No selection is random. Every production brief requires source-backed demand/purchase-intent, momentum, specific geography, competition, current price/margin potential, freshness, production cost and time, confidence, and acceptable risk. Missing data, weak velocity, stale evidence, poor margin, high cost/time, low confidence or high risk returns `no_go` with explicit blockers and no brief. This discipline aims to improve the chance of profit but never guarantees profit:

- new product
- localization
- bundle
- service offer
- pricing/listing update

Supported opportunity categories include affiliate offers, general digital products, digital books/ebooks, product/design packs, and illustrated decor wall art (`decor_art`). Each category routes to its specialist plus QA; all keep the same provenance, score, review and no-auto-publish gates.

The result is a source-backed opportunity plus a production brief for specialist spiders. Every brief contains provenance, review gates, and SEO, listing, and pricing drafts. Search visibility is always labeled as a proposal/proxy, never a ranking guarantee.

Safe defaults are deliberate: without an adapter it returns no opportunities; the included fixture adapter has no network access. Future adapters must use sources that permit the access, preserve source URLs and observation times, use a conservative cadence, and stop on throttling or challenges. Do not feed it private search histories, individual profiles, inferred personal interests, or covert tracking data.

Bullet Spider never publishes, buys ads, sends messages, or changes listings. `publish=true` is refused at the Boss route. Human approval remains a mandatory review gate after quality, IP/license, privacy, claims, source recency, and pricing checks.

Programmatic use:

```python
from bullet_spider import OfflineFixtureAdapter, run_bullet_spider

result = run_bullet_spider(
    {"geography": "MA", "language": "ar"},
    adapters=[OfflineFixtureAdapter(rows)],
)
```

The Market Spy integration boundary is mapping-based and accepts fields such as `opportunity_id`, `topic`, `geography`, `observed_at`, `source_urls`, `metric`/`value`, `evidence_type`, `confidence`, `competition_score`, and `limitations`. Missing provenance is rejected rather than invented.

## Local setup

Python 3.10 or newer is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

The app opens locally at the address printed by Streamlit. The main UI needs a Groq API key before it can generate content.

## Secrets and environment variables

Never commit real values. Use local environment variables, `.streamlit/secrets.toml` for local Streamlit use, and GitHub Actions repository secrets for workflows.

| Variable | Used by | Required when |
| --- | --- | --- |
| `GROQ_API_KEY` | generation, routing, monitoring, WhatsApp | Running AI generation |
| `GUMROAD_ACCESS_TOKEN` | Gumroad publishing/reports | Publishing or reading Gumroad data |
| `POLLINATIONS_TOKEN` | visual generation | Using authenticated visual generation |
| `NEWSAPI_KEY` | news spider | Using NewsAPI-based discovery |
| `SHOPIFY_STORE_DOMAIN` | Shopify helpers | Connecting Shopify |
| `SHOPIFY_ADMIN_TOKEN` | Shopify helpers | Calling Shopify Admin API |
| `SHOPIFY_WEBHOOK_SECRET` | `webhook_server.py` | Verifying Shopify webhooks |
| `GMAIL_USER` | notifications/delivery | Sending mail through Gmail SMTP |
| `GMAIL_APP_PASSWORD` | notifications/delivery | Sending mail through Gmail SMTP |
| `RECIPIENT_EMAIL` | publishing/monitoring | Overriding the report recipient |
| `WHATSAPP_ACCESS_TOKEN` | `whatsapp_bot.py` | Calling WhatsApp Cloud API |
| `WHATSAPP_PHONE_NUMBER_ID` | `whatsapp_bot.py` | Sending WhatsApp replies |
| `WHATSAPP_VERIFY_TOKEN` | `whatsapp_bot.py` | Verifying the webhook subscription |
| `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` | `publishers/youtube_publisher.py` | Publishing to YouTube via Data API |
| `META_PAGE_ACCESS_TOKEN`, `META_PAGE_ID`, `META_IG_USER_ID` | `publishers/meta_publisher.py` | Posting to the Facebook Page / Instagram |
| `TIKTOK_ACCESS_TOKEN`, `TIKTOK_REFRESH_TOKEN` | `publishers/tiktok_publisher.py` | Sending videos to TikTok drafts/inbox |
| `ALIEXPRESS_APP_KEY`, `ALIEXPRESS_APP_SECRET` | `connectors/aliexpress_connector.py` | Market Spy best sellers via the AliExpress Affiliate API |
| `ALIEXPRESS_TRACKING_ID` | `connectors/aliexpress_connector.py` | Tagging generated affiliate links (Portals tracking ID) |
| `MARKET_SPY_FX_OVERRIDE` | `connectors/fx.py` | Optional pinned rate for offline runs, e.g. `USD:MAD=10.0` |

The publishing workflows also read non-secret configuration such as `BOOK_TOPIC`, `BOOK_GENRE`, `BOOK_LANGUAGE`, `BOOK_CHAPTERS`, `BOOK_PRICE_CENTS`, `COMIC_TOPIC`, `COMIC_MODE`, `COMIC_LANGUAGE`, `COMIC_PANELS`, `COMIC_PRICE_CENTS`, `COLORING_THEME`, `COLORING_PAGES`, `COLORING_PRICE_CENTS`, `VISUAL_TYPE`, `VISUAL_TOPIC`, `VISUAL_STYLE`, `VISUAL_BRAND_NAME`, `VISUAL_STYLE_KEYWORDS`, and `VISUAL_PRICE_CENTS`.

For local Streamlit use, create `.streamlit/secrets.toml` only on your machine:

```toml
GROQ_API_KEY = "replace-with-your-own-key"
```

## Market Spy: AliExpress connector and Top N mode

`connectors/aliexpress_connector.py` reads the official AliExpress Affiliate API
(`aliexpress.affiliate.hotproduct.query`, `aliexpress.affiliate.product.query`,
`aliexpress.affiliate.link.generate`) through the signed `/sync` gateway. It is read-only:
no purchases, publishing or account changes. Credentials come only from environment
variables; without them the source is reported as missing and no numbers are invented.

Each product carries price (converted to MAD with the rate and source shown), recent
sales volume, positive-feedback rating, published commission rate and affiliate link.
`_affiliate_scorecard` scores commission, risk (rating weighted by sales depth) and price fit.

Top N best sellers per country:

```bash
export ALIEXPRESS_APP_KEY=...  ALIEXPRESS_APP_SECRET=...  ALIEXPRESS_TRACKING_ID=...
python3 market_spy_spider.py --geography MA --top 10
```

Boss route: `{"action": "market_intelligence", "params": {"geography": "MA", "top_n": 10}}`.
Tests use mock data only: `python3 -m pytest tests/test_aliexpress_connector.py`.

## Safe validation

These checks stay local and make no paid or external API calls:

```bash
python -m compileall -q .
python -m unittest discover -s tests -v
```

A dependency import check can be run after installation:

```bash
python - <<'PY'
import arabic_reshaper, bidi, flask, groq, reportlab, requests, streamlit
print("runtime dependencies import successfully")
PY
```

## Running optional services

Only run these after configuring their secrets and reviewing their side effects.

```bash
# Shopify order webhook
gunicorn webhook_server:app

# WhatsApp webhook
gunicorn --bind 0.0.0.0:5001 whatsapp_bot:app
```

Do not expose either webhook publicly until signature/token verification and account configuration have been tested in a non-production environment.

## Known limitations

- The workspace has no database, migrations, authentication layer, deployment manifest, or end-to-end test suite.
- Most AI and commerce paths need external accounts and can have usage or transaction costs.
- Tests cover local catalog/log behavior, deterministic engineering/electronics calculations, and offline Bullet Spider scoring.
- OpenSCAD rendering requires the separate `openscad` system executable. It is not installed by `requirements.txt`.
- Arabic comic PDF output may need a readable Arabic font. `compile_comic_pdf.py` can use `ARABIC_FONT_PATH`; review font licensing before distribution.
- The free NewsAPI plan may not permit the intended commercial use. Check current provider terms before enabling it.
- The GitHub Actions workflows can create and publish products. Keep them disabled or manual until each destination, secret, price, and rollback path is confirmed.

## Recommended next steps

1. Run the local checks and review each failing path.
2. Add mocked tests around Groq, Shopify, Gumroad, WhatsApp, and email boundaries.
3. Add structured configuration validation so missing secrets fail with clear messages.
4. Enable one workflow at a time in a test account.
5. Add CI for syntax, tests, and secret scanning before any deployment.

No application deployment is performed by this branch.
# Media Spider — Nexa Stories

`media.v1` is an independent, fail-closed story/film subnetwork routed by `domain: media`. Its leaders are Trend Scout, Story Writer, independent Continuity/Fact Checker, Visual Director, Voice & Sound, Editor, and rights/quality QA. Handoffs are typed and versioned; trend/history claims require `source_url`, `confidence`, and `observed_at`.

Defaults are offline, deterministic and zero-cost. Provider adapters are replaceable; no phone app is a dependency. Missing rights, evidence or visual continuity returns `no_go`. The spider never enables publishing: first-user review and a later explicit publish action stay outside this module.

Run: `python -m unittest tests/test_media_spider.py -v`. Streamlit page: `pages/9_Media_Spider.py`.


## Sales Spider (draft-only sales handling)

Sales Spider (`sales_pipeline` Boss route) qualifies leads, prepares persuasion
reply drafts, records attribution and commission records, and hands confirmed,
payment-verified orders to the secure delivery flow. It is offline-first and
fail-closed like Bullet and Media: automatic sending is disabled in code
(`send_allowed=False`), drafts are never pre-approved, deals can only be `won`
after payment verification, and leads without an attribution source are
rejected. Review drafts in the `Sales Spider` Streamlit page; nothing is sent,
published, or spent from this pipeline. See `README_SALES.md`.
