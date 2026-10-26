"""Meta adapters. Facebook uses an explicit per-job Page destination.

Credential presence is not publication approval. Keep the policy dry-run until
an individually approved job and endpoint eligibility have been verified.
Instagram remains separately configured and is not enabled by a Pages grant.
"""
from __future__ import annotations

import os
import json
import re

import requests

from publish_contracts import PublishJob, PublishReceipt

GRAPH = "https://graph.facebook.com/v26.0"


def _cfg() -> tuple[str, str, str]:
    return (os.environ.get("META_PAGE_ACCESS_TOKEN", ""),
            os.environ.get("META_PAGE_ID", ""),
            os.environ.get("META_IG_USER_ID", ""))


def _facebook_destination(job: PublishJob) -> tuple[str, str]:
    """Map Page ID -> secret environment variable. Never use the first Page.

    META_PAGE_TOKEN_ENV_MAP is non-secret JSON, for example
    {"123": "META_BRAND_A_PAGE_TOKEN", "456": "META_BRAND_B_PAGE_TOKEN"}.
    Tokens themselves must not be embedded in that JSON.
    """
    page_id = job.facebook_page_id
    if not isinstance(page_id, str) or not page_id or not page_id.isdecimal():
        raise ValueError("explicit facebook_page_id required")
    try:
        mapping = json.loads(os.environ.get("META_PAGE_TOKEN_ENV_MAP", "{}"))
    except (ValueError, TypeError):
        raise ValueError("invalid Page credential mapping") from None
    if not isinstance(mapping, dict):
        raise ValueError("invalid Page credential mapping")
    env_name = mapping.get(page_id, "")
    if not isinstance(env_name, str) or not re.fullmatch(r"META_[A-Z0-9_]+_PAGE_TOKEN", env_name):
        raise ValueError("Page destination not configured")
    token = os.environ.get(env_name, "")
    if not token:
        raise ValueError("Page credential missing")
    return token, page_id


def publish_facebook(job: PublishJob, dry_run: bool = True) -> PublishReceipt:
    if dry_run:
        return PublishReceipt(job.job_id, "facebook", "dry_run",
                              detail="dry_run: ما تنشر والو", campaign_id=job.campaign_id)
    try:
        token, page_id = _facebook_destination(job)
    except ValueError as exc:
        return PublishReceipt(job.job_id, "facebook", "failed", detail=str(exc),
                              campaign_id=job.campaign_id)
    try:
        with open(job.video_path, "rb") as fh:
            resp = requests.post(
                f"{GRAPH}/{page_id}/videos",
                data={"access_token": token, "title": job.title,
                      "description": job.description},
                files={"source": fh}, timeout=600)
        data = resp.json()
        if "id" not in data:
            return PublishReceipt(job.job_id, "facebook", "failed",
                                  detail="Meta request rejected; inspect redacted error metadata", campaign_id=job.campaign_id)
        return PublishReceipt(job.job_id, "facebook", "published",
                              detail="video posted to page",
                              url=f"https://www.facebook.com/{data['id']}",
                              privacy_state="public", campaign_id=job.campaign_id)
    except Exception as exc:
        return PublishReceipt(job.job_id, "facebook", "failed", detail="Meta request failed (credentials redacted)",
                              campaign_id=job.campaign_id)


def publish_instagram(job: PublishJob, video_url: str = "", dry_run: bool = True) -> PublishReceipt:
    """IG كيحتاج الفيديو يكون مستضاف فـ URL عمومي (video_url). إلا ماكانش،
    كنرجعو failed باش يتدار staging (رفع مؤقت) قبل — ماكانحضروش محلياً."""
    token, _, ig_user_id = _cfg()
    if dry_run:
        return PublishReceipt(job.job_id, "instagram", "dry_run",
                              detail="dry_run: ما تنشر والو", campaign_id=job.campaign_id)
    if not (token and ig_user_id):
        return PublishReceipt(job.job_id, "instagram", "failed",
                              detail="META_PAGE_ACCESS_TOKEN/META_IG_USER_ID ناقصين فالبيئة",
                              campaign_id=job.campaign_id)
    if not video_url:
        return PublishReceipt(job.job_id, "instagram", "failed",
                              detail="IG كيحتاج video_url عمومي للفيديو (staging ناقص)",
                              campaign_id=job.campaign_id)
    try:
        caption = job.description + ("\n\n" + " ".join(f"#{t}" for t in job.hashtags) if job.hashtags else "")
        container = requests.post(
            f"{GRAPH}/{ig_user_id}/media",
            data={"access_token": token, "media_type": "REELS",
                  "video_url": video_url, "caption": caption}, timeout=60).json()
        if "id" not in container:
            return PublishReceipt(job.job_id, "instagram", "failed",
                                  detail="Meta container request rejected", campaign_id=job.campaign_id)
        pub = requests.post(
            f"{GRAPH}/{ig_user_id}/media_publish",
            data={"access_token": token, "creation_id": container["id"]}, timeout=60).json()
        if "id" not in pub:
            return PublishReceipt(job.job_id, "instagram", "failed",
                                  detail="Meta publish request rejected", campaign_id=job.campaign_id)
        return PublishReceipt(job.job_id, "instagram", "published",
                              detail="reel published", url=f"https://www.instagram.com/p/{pub['id']}/",
                              privacy_state="public", campaign_id=job.campaign_id)
    except Exception as exc:
        return PublishReceipt(job.job_id, "instagram", "failed", detail="Meta request failed (credentials redacted)",
                              campaign_id=job.campaign_id)
