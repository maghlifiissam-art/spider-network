"""TikTok inbox upload prototype; public direct posting is disabled pending review.

See TIKTOK_SETUP.md. An API upload is not a verified public post.
"""
from __future__ import annotations

from urllib.parse import urlparse

import os
import time

import requests
from tiktok_token_store import load_tokens, save_tokens

from publish_contracts import PublishJob, PublishReceipt

API = "https://open.tiktokapis.com/v2"


def _token() -> str:
    """Refresh before expiry and atomically persist a rotated refresh token."""
    state = load_tokens()
    if state.get("open_id") != os.environ.get("TIKTOK_EXPECTED_OPEN_ID", ""):
        raise RuntimeError("TikTok account binding missing or does not match the authorized creator")
    if state.get("expires_at", 0) > time.time() + 1800:
        return state["access_token"]
    key, secret = os.environ.get("TIKTOK_CLIENT_KEY"), os.environ.get("TIKTOK_CLIENT_SECRET")
    if not key or not secret:
        raise RuntimeError("TikTok client credentials missing; cannot refresh")
    resp = requests.post(f"{API}/oauth/token/", data={
        "client_key": key, "client_secret": secret, "grant_type": "refresh_token",
        "refresh_token": state["refresh_token"],
    }, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("access_token") or not data.get("refresh_token") or data.get("open_id") != state["open_id"]:
        raise RuntimeError("TikTok refresh failed or returned a different creator")
    state.update(access_token=data["access_token"], refresh_token=data["refresh_token"],
                 expires_at=time.time() + int(data.get("expires_in", 0)))
    save_tokens(state)
    return data["access_token"]


def _caption(job: PublishJob) -> str:
    tags = " ".join(f"#{t}" for t in job.hashtags)
    return f"{job.title}\n{job.description}\n{tags}".strip()[:2200]


def publish(job: PublishJob, mode: str = "draft", dry_run: bool = True) -> PublishReceipt:
    """Only inbox uploads are implemented; direct public publishing is disabled."""
    if dry_run:
        return PublishReceipt(job.job_id, "tiktok", "dry_run",
                              detail=f"dry_run ({mode}): ما تنشر والو", privacy_state=mode,
                              campaign_id=job.campaign_id)
    if mode != "draft":
        return PublishReceipt(job.job_id, "tiktok", "failed",
                              detail="direct publishing disabled pending TikTok audit, creator privacy selection and status verification",
                              campaign_id=job.campaign_id)
    try:
        token = _token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        if not job.video_path.lower().endswith(".mp4"):
            return PublishReceipt(job.job_id, "tiktok", "failed", detail="only MP4 is supported by this adapter",
                                  campaign_id=job.campaign_id)
        size = os.path.getsize(job.video_path)
        if size <= 0 or size > 64 * 1024 * 1024:
            return PublishReceipt(job.job_id, "tiktok", "failed",
                                  detail="single-chunk prototype supports only 1-64 MiB; no upload attempted",
                                  campaign_id=job.campaign_id)
        init_url = f"{API}/post/publish/inbox/video/init/"
        body = {"source_info": {"source": "FILE_UPLOAD", "video_size": size,
                                "chunk_size": size, "total_chunk_count": 1}}
        init_response = requests.post(init_url, headers=headers, json=body, timeout=60)
        init_response.raise_for_status()
        init = init_response.json()
        data = init.get("data", {})
        if init.get("error", {}).get("code") != "ok":
            return PublishReceipt(job.job_id, "tiktok", "failed", detail=str(init.get("error", {}))[:500],
                                  campaign_id=job.campaign_id)
        upload_url = data.get("upload_url", "")
        publish_id = data.get("publish_id", "")
        if not publish_id:
            return PublishReceipt(job.job_id, "tiktok", "failed", detail="missing publish_id; no upload attempted",
                                  campaign_id=job.campaign_id)
        parsed = urlparse(upload_url)
        if parsed.scheme != "https" or parsed.hostname not in ("open-upload.tiktokapis.com", "upload.us.tiktokapis.com"):
            return PublishReceipt(job.job_id, "tiktok", "failed", detail="unexpected TikTok upload host",
                                  campaign_id=job.campaign_id)
        with open(job.video_path, "rb") as fh:
            up = requests.put(upload_url, data=fh.read(), timeout=600,
                              headers={"Content-Type": "video/mp4",
                                       "Content-Length": str(size),
                                       "Content-Range": f"bytes 0-{size - 1}/{size}"})
        if up.status_code not in (200, 201):
            return PublishReceipt(job.job_id, "tiktok", "failed",
                                  detail=f"upload http {up.status_code}", campaign_id=job.campaign_id)
        # A successful upload is processing, not a post. Caller tracks status by publish_id.
        return PublishReceipt(job.job_id, "tiktok", "draft_ready",
                              detail=f"inbox upload submitted; publish_id={publish_id}; creator must finish in app",
                              privacy_state="draft", campaign_id=job.campaign_id)
    except Exception as exc:
        return PublishReceipt(job.job_id, "tiktok", "failed", detail=f"upload outcome uncertain: {type(exc).__name__}; do not retry blindly",
                              campaign_id=job.campaign_id)
