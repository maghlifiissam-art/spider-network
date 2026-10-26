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
    # Official uploaded-file-handle flow. A live upload remains a separately
    # approved action; this function does not start sessions during dry-run.
    user_token = os.environ.get("META_USER_ACCESS_TOKEN", "")
    app_id = os.environ.get("META_APP_ID", "")
    if not user_token or not app_id.isdecimal():
        return PublishReceipt(job.job_id, "facebook", "failed",
                              detail="Meta app/user upload credentials missing",
                              campaign_id=job.campaign_id)
    try:
        from pathlib import Path
        source = Path(job.video_path)
        if source.suffix.lower() != ".mp4" or not source.is_file() or not source.stat().st_size:
            raise ValueError("invalid MP4 input")
        # No automatic retry: an interrupted write needs reconciliation first.
        session_response = requests.post(f"{GRAPH}/{app_id}/uploads",
            headers={"Authorization": "Bearer " + user_token},
            params={"file_name": source.name, "file_length": source.stat().st_size,
                    "file_type": "video/mp4"}, timeout=60)
        session = session_response.json().get("id", "")
        if not session_response.ok or not isinstance(session, str) or not re.fullmatch(r"upload:[A-Za-z0-9_:.?=&%+~-]+", session):
            raise ValueError("upload session rejected")
        with source.open("rb") as fh:
            upload_response = requests.post(f"{GRAPH}/{session}",
                headers={"Authorization": "OAuth " + user_token, "file_offset": "0"},
                data=fh, timeout=600)
        handle = upload_response.json().get("h", "")
        if not upload_response.ok or not isinstance(handle, str) or not handle:
            raise ValueError("upload did not return handle")
        response = requests.post(f"https://graph-video.facebook.com/v26.0/{page_id}/videos",
            headers={"Authorization": "Bearer " + token},
            data={"title": job.title, "description": job.description,
                  "fbuploader_video_file_chunk": handle}, timeout=600)
        video_id = response.json().get("id", "")
        if not response.ok or not isinstance(video_id, str) or not video_id.isdecimal():
            raise ValueError("publish receipt unconfirmed")
        return PublishReceipt(job.job_id, "facebook", "published",
            detail="Meta returned video ID " + video_id + "; public visibility not verified",
            privacy_state="unverified", campaign_id=job.campaign_id)
    except Exception:
        return PublishReceipt(job.job_id, "facebook", "failed",
            detail="Meta write unconfirmed; reconcile before retry (credentials redacted)",
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
