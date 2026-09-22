"""
meta_publisher.py — النشر على Facebook Page + Instagram بالـ Meta Graph API
------------------------------------------------------------------
- فيسبوك: POST /{PAGE_ID}/videos (فيديو) — Page access token طويل الأمد.
- إنستغرام: جوج خطوات — إنشاء container (POST /{IG_USER_ID}/media) من بعد
  النشر (POST /{IG_USER_ID}/media_publish). Reels مدعومة (media_type=REELS).
- خاص IG يكون حساب احترافي (Creator/Business) ومربوط بالصفحة.
- الحسابات ديالنا = "business we own" بـ Standard Access: بلا App Review.
  التطبيق خاصو يكون فوضع Live (ماشي Development) باش المنشورات تبان للعموم.

الإعداد (مرة وحدة): شوف scripts/auth_meta.py — كيعطيك:
  META_PAGE_ACCESS_TOKEN / META_PAGE_ID / META_IG_USER_ID
"""
from __future__ import annotations

import os

import requests

from publish_contracts import PublishJob, PublishReceipt

GRAPH = "https://graph.facebook.com/v21.0"


def _cfg() -> tuple[str, str, str]:
    return (os.environ.get("META_PAGE_ACCESS_TOKEN", ""),
            os.environ.get("META_PAGE_ID", ""),
            os.environ.get("META_IG_USER_ID", ""))


def publish_facebook(job: PublishJob, dry_run: bool = True) -> PublishReceipt:
    token, page_id, _ = _cfg()
    if dry_run:
        return PublishReceipt(job.job_id, "facebook", "dry_run",
                              detail="dry_run: ما تنشر والو", campaign_id=job.campaign_id)
    if not (token and page_id):
        return PublishReceipt(job.job_id, "facebook", "failed",
                              detail="META_PAGE_ACCESS_TOKEN/META_PAGE_ID ناقصين فالبيئة",
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
                                  detail=str(data)[:500], campaign_id=job.campaign_id)
        return PublishReceipt(job.job_id, "facebook", "published",
                              detail="video posted to page",
                              url=f"https://www.facebook.com/{data['id']}",
                              privacy_state="public", campaign_id=job.campaign_id)
    except Exception as exc:
        return PublishReceipt(job.job_id, "facebook", "failed", detail=str(exc)[:500],
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
                                  detail=str(container)[:500], campaign_id=job.campaign_id)
        pub = requests.post(
            f"{GRAPH}/{ig_user_id}/media_publish",
            data={"access_token": token, "creation_id": container["id"]}, timeout=60).json()
        if "id" not in pub:
            return PublishReceipt(job.job_id, "instagram", "failed",
                                  detail=str(pub)[:500], campaign_id=job.campaign_id)
        return PublishReceipt(job.job_id, "instagram", "published",
                              detail="reel published", url=f"https://www.instagram.com/p/{pub['id']}/",
                              privacy_state="public", campaign_id=job.campaign_id)
    except Exception as exc:
        return PublishReceipt(job.job_id, "instagram", "failed", detail=str(exc)[:500],
                              campaign_id=job.campaign_id)
