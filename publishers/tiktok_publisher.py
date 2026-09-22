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

import requests

from publish_contracts import PublishJob, PublishReceipt

API = "https://open.tiktokapis.com/v2"


def _token() -> str:
    return os.environ.get("TIKTOK_ACCESS_TOKEN", "")


def _caption(job: PublishJob) -> str:
    tags = " ".join(f"#{t}" for t in job.hashtags)
    return f"{job.title}\n{job.description}\n{tags}".strip()[:2200]


def publish(job: PublishJob, mode: str = "draft", dry_run: bool = True) -> PublishReceipt:
    """mode='draft': للمسودات (inbox). mode='direct': نشر مباشر (خاص بالحسابات المدققة)."""
    if dry_run:
        return PublishReceipt(job.job_id, "tiktok", "dry_run",
                              detail=f"dry_run ({mode}): ما تنشر والو", privacy_state=mode,
                              campaign_id=job.campaign_id)
    token = _token()
    if not token:
        return PublishReceipt(job.job_id, "tiktok", "failed",
                              detail="TIKTOK_ACCESS_TOKEN ناقص فالبيئة", campaign_id=job.campaign_id)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        size = os.path.getsize(job.video_path)
        if mode == "draft":
            init_url = f"{API}/post/publish/inbox/video/init/"
            body = {"source_info": {"source": "FILE_UPLOAD", "video_size": size,
                                    "chunk_size": size, "total_chunk_count": 1}}
        else:  # direct
            init_url = f"{API}/post/publish/video/init/"
            body = {"post_info": {"title": _caption(job), "privacy_level": "SELF_ONLY"},
                    "source_info": {"source": "FILE_UPLOAD", "video_size": size,
                                    "chunk_size": size, "total_chunk_count": 1}}
        init = requests.post(init_url, headers=headers, json=body, timeout=60).json()
        data = init.get("data", {})
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
        if mode == "draft":
            return PublishReceipt(job.job_id, "tiktok", "draft_ready",
                                  detail="الفيديو وصل لمسودات تيكتوك - كمل النشر من التطبيق",
                                  privacy_state="draft", campaign_id=job.campaign_id)
        return PublishReceipt(job.job_id, "tiktok", "pending_audit",
                              detail="direct post sent (SELF_ONLY until TikTok audit approves)",
                              privacy_state="self_only", campaign_id=job.campaign_id)
    except Exception as exc:
        return PublishReceipt(job.job_id, "tiktok", "failed", detail=str(exc)[:500],
                              campaign_id=job.campaign_id)
