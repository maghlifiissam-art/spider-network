# Spider Network

Spider Network is a Python workspace for a group of specialized assistants. It includes a Streamlit interface, a Boss Spider router, content and digital-product pipelines, engineering and electronics helpers, reporting, a WhatsApp bot, and Shopify/Gumroad integrations.

This repository is an early, untested integration workspace. Start with the local Streamlit interface. Keep every publishing workflow and webhook disabled until its account, secret, and dry-run behavior have been checked.

## What is included

- `app.py`: Streamlit interface for Affiliate, Media, and Digital Products spiders.
- `boss_spider.py`: command classification and routing across the specialist modules.
- `pages/`: Streamlit pages for books, Boss Spider, dashboard, and engineering.
- `book_spider.py`, `comic_spider.py`, `visual_spider.py`: content generation helpers.
- `engineering_spider.py`, `electronics_spider.py`, `cloud_architect_spider.py`: technical design helpers.
- `catalog.py`, `ops_log.py`: local JSON catalog and operation log.
- `webhook_server.py`: Shopify paid-order webhook and email delivery service.
- `whatsapp_bot.py`: WhatsApp Cloud API webhook and reply service.
- `.github/workflows/`: manual/scheduled publishing and monitoring jobs. Review them before enabling.
- `tests/`: local tests that do not call paid APIs or external services.

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

The publishing workflows also read non-secret configuration such as `BOOK_TOPIC`, `BOOK_GENRE`, `BOOK_LANGUAGE`, `BOOK_CHAPTERS`, `BOOK_PRICE_CENTS`, `COMIC_TOPIC`, `COMIC_MODE`, `COMIC_LANGUAGE`, `COMIC_PANELS`, `COMIC_PRICE_CENTS`, `COLORING_THEME`, `COLORING_PAGES`, `COLORING_PRICE_CENTS`, `VISUAL_TYPE`, `VISUAL_TOPIC`, `VISUAL_STYLE`, `VISUAL_BRAND_NAME`, `VISUAL_STYLE_KEYWORDS`, and `VISUAL_PRICE_CENTS`.

For local Streamlit use, create `.streamlit/secrets.toml` only on your machine:

```toml
GROQ_API_KEY = "replace-with-your-own-key"
```

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
- Tests currently cover local catalog/log behavior and deterministic engineering/electronics calculations only.
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
