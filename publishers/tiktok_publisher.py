"""
tiktok_publisher.py — النشر على تيكتوك بالـ Content Posting API الرسمي
------------------------------------------------------------------
- الوضع الافتراضي "draft": كيصيفط الفيديو + النص لمسودات/inbox ديال تيكتوك،
  وعصام كيكمل بالنشر من التطبيق بضغطة وحدة. هاد المسار كيخدم بلا audit.
- الوضع "direct": نشر مباشر، ولكن طالما التطبيق ماشي مُدقق TikTok كيحبس
  المحتوى فـ SELF_ONLY (خاص). كنفعلوه غير ملي توافق TikTok على الـ audit.
  بدلو فـ config/publish.yaml (tiktok_mode).

الإعداد (مرة وحدة): شوف scripts/auth_tiktok.py — كيعطيك:
  TIKTOK_ACCESS_TOKEN / TIKTOK_REFRESH_TOKEN
"""
from __future__ import annotations

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
    """mode='draft': للمسودات (inbox). mode='direct': نشر مباشر (خاص بالحسابات المدققة)."""
    if dry_run:
        return PublishReceipt(job.job_id, "tiktok", "dry_run",
                              detail=f"dry_run ({mode}): ما تنشر والو", privacy_state=mode,
                              campaign_id=job.campaign_id)
    try:
        token = _token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        size = os.path.getsize(job.video_path)
        if mode not in ("draft", "direct"):
            return PublishReceipt(job.job_id, "tiktok", "failed", detail="unknown TikTok mode", campaign_id=job.campaign_id)
        if mode == "draft":
            init_url = f"{API}/post/publish/inbox/video/init/"
            body = {"source_info": {"source": "FILE_UPLOAD", "video_size": size,
                                    "chunk_size": size, "total_chunk_count": 1}}
        else:  # direct
            init_url = f"{API}/post/publish/video/init/"
            body = {"post_info": {"title": _caption(job), "privacy_level": "SELF_ONLY"},
                    "source_info": {"source": "FILE_UPLOAD", "video_size": size,
                                    "chunk_size": size, "total_chunk_count": 1}}
        init_response = requests.post(init_url, headers=headers, json=body, timeout=60)
        init_response.raise_for_status()
        init = init_response.json()
        data = init.get("data", {})
        if init.get("error", {}).get("code") != "ok":
            return PublishReceipt(job.job_id, "tiktok", "failed", detail=str(init.get("error", {}))[:500],
                                  campaign_id=job.campaign_id)
        upload_url = data.get("upload_url", "")
        if not upload_url:
            return PublishReceipt(job.job_id, "tiktok", "failed", detail=str(init)[:500],
                                  campaign_id=job.campaign_id)
        with open(job.video_path, "rb") as fh:
            up = requests.put(upload_url, data=fh.read(), timeout=600,
                              headers={"Content-Type": "video/mp4",
                                       "Content-Length": str(size),
                                       "Content-Range": f"bytes 0-{size - 1}/{size}"})
        if up.status_code not in (200, 201):
            return PublishReceipt(job.job_id, "tiktok", "failed",
                                  detail=f"upload http {up.status_code}", campaign_id=job.campaign_id)
        publish_id = data.get("publish_id", "")
        # A successful upload is processing, not a post. Caller tracks status by publish_id.
        if mode == "draft":
            return PublishReceipt(job.job_id, "tiktok", "draft_ready",
                                  detail=f"inbox upload submitted; publish_id={publish_id}; creator must finish in app",
                                  privacy_state="draft", campaign_id=job.campaign_id)
        return PublishReceipt(job.job_id, "tiktok", "pending_audit",
                              detail=f"private direct upload submitted; publish_id={publish_id}; confirm via status endpoint",
                              privacy_state="self_only", campaign_id=job.campaign_id)
    except Exception as exc:
        return PublishReceipt(job.job_id, "tiktok", "failed", detail=str(exc)[:500],
                              campaign_id=job.campaign_id)
