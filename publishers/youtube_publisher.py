"""
youtube_publisher.py — النشر على يوتيوب بالـ YouTube Data API v3 الرسمي
------------------------------------------------------------------
- سكوب وحيد: youtube.upload
- القناة: Nexa Stories
- مهم: طالما مشروع الـ API مازال ماشي مُدقق (compliance audit)، يوتيوب كيحبس
  أي فيديو مرفوع بالـ API فـ private بلا استئناف. علاش الافتراضي هنا
  privacy = private حتى تدوز المراجعة، وبعدها كنبدلو config/publish.yaml.
- الحصة (2026): bucket خاص بـ videos.insert — 100 مكالمة/اليوم افتراضياً.

الإعداد (مرة وحدة): شوف scripts/auth_youtube.py — كيعطيك:
  YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN
"""
from __future__ import annotations

import os

from publish_contracts import PublishJob, PublishReceipt

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _credentials():
    """يبني credentials من الـ refresh token. كيرجع None إلا كان شي متغير ناقص."""
    client_id = os.environ.get("YOUTUBE_CLIENT_ID", "")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
    if not (client_id and client_secret and refresh_token):
        return None
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError:
        return None
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def publish(job: PublishJob, privacy: str = "private", dry_run: bool = True) -> PublishReceipt:
    """كيرفع الفيديو ليوتيوب. dry_run=True كيرجع إيصال بلا أي شبكة."""
    if dry_run:
        return PublishReceipt(job.job_id, "youtube", "dry_run",
                              detail="dry_run: ما تنشر والو", privacy_state=privacy,
                              campaign_id=job.campaign_id)
    try:
        creds = _credentials()
    except Exception as exc:  # token expired / network
        return PublishReceipt(job.job_id, "youtube", "failed",
                              detail=f"auth failed: {exc}", campaign_id=job.campaign_id)
    if creds is None:
        return PublishReceipt(job.job_id, "youtube", "failed",
                              detail="YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN ناقصين فالبيئة",
                              campaign_id=job.campaign_id)
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
        body = {
            "snippet": {
                "title": job.title,
                "description": job.description,
                "tags": job.hashtags,
                "categoryId": "24",  # Entertainment
            },
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
        }
        media = MediaFileUpload(job.video_path, chunksize=-1, resumable=True)
        resp = youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        video_id = resp.get("id", "")
        status = "pending_audit" if privacy == "private" else "published"
        return PublishReceipt(
            job.job_id, "youtube", status,
            detail="uploaded" if privacy != "private" else "uploaded private (API audit pending)",
            url=f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
            privacy_state=privacy, campaign_id=job.campaign_id)
    except Exception as exc:
        return PublishReceipt(job.job_id, "youtube", "failed", detail=str(exc)[:500],
                              campaign_id=job.campaign_id)
