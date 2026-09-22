# Publish Spider — وكيل النشر (publish.v1)

The Publish Spider is the explicit publish action that `README_MEDIA.md` keeps outside
the media module. It receives finished content from the **Media Spider** and campaign
instructions from the **Bullet / Sales / closing agents**, publishes through **official
platform APIs only**, and returns a typed `publish_receipt` per platform so the Sales
Spider and the deal-closing agent can track where every video/product is live.

Chain: `market_spy → bullet (brief) → media (video) → publish (job) → sales (follow-up)`

## Contracts

- `schemas/publish_job.schema.json` — input: content ref, caption, hashtags, target
  platforms, campaign_id, source_brief_id, schedule.
- `schemas/publish_receipt.schema.json` — output per platform: status, URL, privacy
  state, campaign_id. Receipts are appended to `data/publish_receipts.json` (gitignored)
  and to `ops_log` under the `social_publish` line.

## Platforms and honest limits

| Platform | API | Default behavior | Why |
| --- | --- | --- | --- |
| YouTube | Data API v3 `videos.insert` (scope `youtube.upload`) | uploads **private** | Unverified API projects are locked private until the free API compliance audit passes. Consent screen must be "In production" or the refresh token dies every 7 days. |
| Facebook Page | Graph API `/{page}/videos` | public | Own-business app with Standard Access: no App Review. App must be in Live mode. |
| Instagram | Graph API media + media_publish (REELS) | public | Needs a **Professional** IG account linked to the Page, and a public `video_url` (staging happens outside this module for now). |
| TikTok | Content Posting API | **draft to inbox** (`video.upload`) | Unaudited apps can only direct-post as SELF_ONLY; the draft flow lets the user tap publish in the app. `tiktok_mode: direct` stays off until TikTok approves. |

## Fail-closed by default

`config/publish.yaml` ships with `dry_run: true`. Nothing posts until credentials exist
and dry_run is flipped. Missing tokens produce a clear `failed` receipt, never an
exception, never a post. Secrets never enter this repo: they live in local `.env`
(gitignored), Replit Secrets, or the owner's credential vault.

## Setup (once per platform)

```bash
python scripts/auth_youtube.py   # Google Cloud project + OAuth, writes .env
python scripts/auth_meta.py      # Meta Business app + Page token, writes .env
python scripts/auth_tiktok.py    # TikTok developer app + OAuth, writes .env
```

Run: `python -m unittest tests/test_publish_spider.py -v`. Streamlit page: `pages/11_Publish_Spider.py`.
